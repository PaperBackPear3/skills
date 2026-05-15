#!/usr/bin/env python3
"""scan_terraform_aks.py — extract declared AKS resources from a Terraform root.

Handles three styles of declaration:
  1. Raw `azurerm_kubernetes_cluster` / `azurerm_kubernetes_cluster_node_pool` resources.
     Also reads `addon_profile` / `oms_agent`, `azure_policy`, `ingress_application_gateway`,
     `key_vault_secrets_provider`, `open_service_mesh`, and `http_application_routing` blocks.
  2. Module calls whose source references AKS (e.g. `Azure/aks/azurerm`,
     a private registry module, or a local `./modules/aks` path). Extracts:
       - kubernetes_version
       - addons map (with per-add-on settings)
       - node_pools / default_node_pool blocks (names + versions)
       - any *version* attribute inside the module call
  3. Local modules: emits the resolved path so the skill can recurse with the
     Terraform MCP (get_module_details / get_private_module_details) or scan
     the local folder.

Output is JSON suitable for further enrichment by the skill via the Terraform MCP.

Usage:
    ./scan_terraform_aks.py <terraform-root-dir>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


AKS_HINT_RE = re.compile(r"(?i)(^|[/.-])aks([/.-]|$)|kubernetes_cluster")

KNOWN_ADDONS = [
    "oms_agent",
    "azure_policy",
    "ingress_application_gateway",
    "key_vault_secrets_provider",
    "open_service_mesh",
    "http_application_routing",
    "azure_keyvault_secrets_provider",
]


def find_blocks(text: str, head_re: str) -> list[tuple[str, str]]:
    """Find top-level HCL blocks. Supports two levels of nested braces in body."""
    pat = re.compile(
        head_re + r"\s*\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}",
        re.DOTALL,
    )
    return [(m.group(1), m.group(2)) for m in pat.finditer(text)]


def attr(body: str, name: str) -> str | None:
    m = re.search(rf'^\s*{re.escape(name)}\s*=\s*"?([^"\n#]+?)"?\s*(?:#.*)?$', body, re.MULTILINE)
    return m.group(1).strip() if m else None


def find_nested_blocks(body: str, kind: str) -> list[tuple[str, str]]:
    """Find nested labelled blocks. Returns (label, inner_body) tuples."""
    out: list[tuple[str, str]] = []
    # Form A: kind "label" { ... }
    out += find_blocks(body, rf'{re.escape(kind)}\s+"([^"]+)"')
    # Form B: kind = { label = { ... } }
    m = re.search(rf'{re.escape(kind)}\s*=\s*\{{', body)
    if m:
        depth, i = 1, m.end()
        while i < len(body) and depth > 0:
            if body[i] == "{":
                depth += 1
            elif body[i] == "}":
                depth -= 1
            i += 1
        inner = body[m.end():i - 1]
        for label_m in re.finditer(r'(?m)^\s*"?([A-Za-z0-9_.-]+)"?\s*=\s*\{', inner):
            start = label_m.end()
            d = 1
            j = start
            while j < len(inner) and d > 0:
                if inner[j] == "{":
                    d += 1
                elif inner[j] == "}":
                    d -= 1
                j += 1
            out.append((label_m.group(1), inner[start:j - 1]))
    return out


def extract_addon_block(body: str, addon_name: str) -> dict | None:
    """Extract a named addon block (unlabelled) from an addon_profile or resource body."""
    m = re.search(rf'{re.escape(addon_name)}\s*\{{((?:[^{{}}]|\{{[^{{}}]*\}})*)\}}', body, re.DOTALL)
    if not m:
        return None
    inner = m.group(1)
    return {
        "name": addon_name,
        "enabled": attr(inner, "enabled"),
        "version": attr(inner, "version") or attr(inner, "chart_version"),
    }


def scan(root: Path) -> dict:
    blob_parts: list[str] = []
    file_count = 0
    for tf_file in root.rglob("*.tf"):
        if ".terraform" in tf_file.parts:
            continue
        try:
            blob_parts.append(tf_file.read_text())
            file_count += 1
        except OSError:
            continue
    blob = "\n".join(blob_parts)

    result: dict = {
        "scanned_root": str(root),
        "tf_files_scanned": file_count,
        "clusters": [],
        "node_pools": [],
        "addons": [],
        "aks_module_calls": [],
        "investigation_hints": [],
        "warnings": [],
    }

    # ── Raw azurerm_kubernetes_cluster resources ──────────────────────────────
    for name, body in find_blocks(blob, r'resource\s+"azurerm_kubernetes_cluster"\s+"([^"]+)"'):
        cluster: dict = {
            "name": name,
            "cluster_name": attr(body, "name"),
            "kubernetes_version": attr(body, "kubernetes_version"),
            "sku_tier": attr(body, "sku_tier"),
            "addons": [],
        }

        # default_node_pool embedded in the cluster resource
        for _, np_body in find_blocks(body, r"(default_node_pool)"):
            cluster["default_node_pool"] = {
                "orchestrator_version": attr(np_body, "orchestrator_version"),
                "vm_size": attr(np_body, "vm_size"),
            }

        # addon_profile (legacy ≤ provider 3.x) and individual inline add-ons
        for addon in KNOWN_ADDONS:
            addon_info = extract_addon_block(body, addon)
            if addon_info:
                cluster["addons"].append(addon_info)

        result["clusters"].append(cluster)

    # ── Raw azurerm_kubernetes_cluster_node_pool resources ────────────────────
    for name, body in find_blocks(blob, r'resource\s+"azurerm_kubernetes_cluster_node_pool"\s+"([^"]+)"'):
        result["node_pools"].append({
            "name": name,
            "pool_name": attr(body, "name"),
            "orchestrator_version": attr(body, "orchestrator_version"),
            "vm_size": attr(body, "vm_size"),
            "cluster_id_ref": attr(body, "kubernetes_cluster_id"),
        })

    # ── Module calls referencing AKS ─────────────────────────────────────────
    for mod_name, body in find_blocks(blob, r'module\s+"([^"]+)"'):
        source = attr(body, "source")
        if not source or not AKS_HINT_RE.search(source):
            continue

        call: dict = {
            "name": mod_name,
            "source": source,
            "version": attr(body, "version"),
            "kubernetes_version": attr(body, "kubernetes_version"),
            "addons": [],
            "node_pools": [],
            "kind": _classify_source(source),
        }

        # addons = { oms_agent = { enabled = true }, ... }
        for label, inner in find_nested_blocks(body, "addons"):
            call["addons"].append({
                "name": label,
                "enabled": attr(inner, "enabled"),
                "version": attr(inner, "version") or attr(inner, "chart_version"),
            })

        # node_pools / agents_pools = { name = {...}, ... }
        for ng_key in ("node_pools", "agents_pools", "node_pool"):
            for label, inner in find_nested_blocks(body, ng_key):
                call["node_pools"].append({
                    "name": label,
                    "orchestrator_version": attr(inner, "orchestrator_version"),
                    "vm_size": attr(inner, "vm_size"),
                })

        call["investigation"] = _investigation_hint(source, root)
        result["aks_module_calls"].append(call)

    for call in result["aks_module_calls"]:
        result["investigation_hints"].append(call["investigation"])

    # ── Detect addons declared in two places ──────────────────────────────────
    standalone_addons: dict[str, str] = {}
    for cluster in result["clusters"]:
        for addon in cluster.get("addons", []):
            if addon.get("name"):
                standalone_addons[addon["name"]] = f"azurerm_kubernetes_cluster.{cluster['name']}"

    module_addons: dict[str, list[str]] = {}
    for call in result["aks_module_calls"]:
        for addon in call.get("addons", []):
            if addon.get("name"):
                module_addons.setdefault(addon["name"], []).append(
                    f"module.{call['name']}.addons"
                )

    for addon_name, source in standalone_addons.items():
        if addon_name in module_addons:
            result["warnings"].append({
                "type": "addon_double_management",
                "addon": addon_name,
                "declared_in": [source, *module_addons[addon_name]],
                "message": (
                    f"'{addon_name}' is declared both inside azurerm_kubernetes_cluster "
                    "and inside a module's addons block. Remove one declaration."
                ),
            })

    return result


def _classify_source(source: str) -> str:
    s = source.strip()
    if s.startswith((".", "/")):
        return "local"
    if s.startswith(("git::", "git@", "https://github.com", "github.com")):
        return "git"
    if s.count("/") == 2:
        return "public_registry"
    if "/" in s and "." in s.split("/", 1)[0]:
        return "private_registry"
    return "unknown"


def _investigation_hint(source: str, root: Path) -> dict:
    kind = _classify_source(source)
    base = {"source": source, "kind": kind}

    if kind == "local":
        local_path = (root / source).resolve() if not Path(source).is_absolute() else Path(source)
        base["local_path"] = str(local_path)
        base["next_step"] = (
            f"Re-run scan_terraform_aks.py on {local_path} to inspect the local module's resources."
        )
    elif kind == "public_registry":
        base["next_step"] = (
            f"Use Terraform MCP: get_latest_module_version + get_module_details for '{source}' "
            "to confirm the latest version and locate variables that control K8s/addon versions."
        )
    elif kind == "private_registry":
        base["next_step"] = (
            f"Use Terraform MCP: get_private_module_details for '{source}' (requires HCP "
            "Terraform/TFE token). Falls back to search_private_modules if details fail."
        )
    elif kind == "git":
        base["next_step"] = (
            "Module is sourced from Git. Resolve the ref/tag in the source URL and inspect the "
            "repo on GitHub via the GitHub MCP if needed."
        )
    else:
        base["next_step"] = "Unknown source kind — ask the user how to inspect this module."

    return base


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: scan_terraform_aks.py <tf-root>", file=sys.stderr)
        sys.exit(1)
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"Directory not found: {root}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(scan(root), indent=2))


if __name__ == "__main__":
    main()
