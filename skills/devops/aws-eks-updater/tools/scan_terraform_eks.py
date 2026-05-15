#!/usr/bin/env python3
"""scan_terraform_eks.py — extract declared EKS resources from a Terraform root.

Handles three styles of declaration:
  1. Raw `aws_eks_cluster` / `aws_eks_node_group` / `aws_eks_addon` resources.
  2. Module calls whose source references EKS (e.g. `terraform-aws-modules/eks/aws`,
     a private registry module, or a local `./modules/eks` path). Extracts:
       - cluster_version / kubernetes_version
       - cluster_addons (block / map)
       - eks_managed_node_groups, self_managed_node_groups, fargate_profiles (block names + versions)
       - any *version* attribute inside the module call
  3. Local modules: emits the resolved path so the skill can recurse with the
     Terraform MCP (get_module_details / get_private_module_details) or scan
     the local folder.

Output is JSON suitable for further enrichment by the skill via the Terraform MCP.

Usage:
    ./scan_terraform_eks.py <terraform-root-dir>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


# Public/private registry source patterns that indicate an EKS module.
EKS_HINT_RE = re.compile(r"(?i)(^|[/.-])eks([/.-]|$)")


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
    """Find nested labelled blocks like  cluster_addons "coredns" { ... }  or
    eks_managed_node_groups = { name = {...} }. Returns (label, inner_body) tuples."""
    out: list[tuple[str, str]] = []
    # Form A: kind "label" { ... }
    out += find_blocks(body, rf'{re.escape(kind)}\s+"([^"]+)"')
    # Form B: kind = { label = { ... } }  (very common in EKS modules)
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
        "node_groups": [],
        "addons": [],
        "eks_module_calls": [],
        "investigation_hints": [],
    }

    # ── Raw aws_eks_* resources ───────────────────────────────────────────────
    for name, body in find_blocks(blob, r'resource\s+"aws_eks_cluster"\s+"([^"]+)"'):
        result["clusters"].append({
            "name": name,
            "cluster_name": attr(body, "name"),
            "version": attr(body, "version"),
        })

    for name, body in find_blocks(blob, r'resource\s+"aws_eks_node_group"\s+"([^"]+)"'):
        result["node_groups"].append({
            "name": name,
            "version": attr(body, "version"),
            "ami_type": attr(body, "ami_type"),
            "release_version": attr(body, "release_version"),
        })

    for name, body in find_blocks(blob, r'resource\s+"aws_eks_addon"\s+"([^"]+)"'):
        result["addons"].append({
            "name": name,
            "addon_name": attr(body, "addon_name"),
            "addon_version": attr(body, "addon_version"),
        })

    # ── Module calls referencing EKS ──────────────────────────────────────────
    for mod_name, body in find_blocks(blob, r'module\s+"([^"]+)"'):
        source = attr(body, "source")
        if not source or not EKS_HINT_RE.search(source):
            continue

        call: dict = {
            "name": mod_name,
            "source": source,
            "version": attr(body, "version"),
            "cluster_version": attr(body, "cluster_version") or attr(body, "kubernetes_version"),
            "cluster_addons": [],
            "managed_node_groups": [],
            "self_managed_node_groups": [],
            "fargate_profiles": [],
            "kind": _classify_source(source),
        }

        # cluster_addons = { vpc-cni = { addon_version = "v1.x" }, ... }
        for label, inner in find_nested_blocks(body, "cluster_addons"):
            call["cluster_addons"].append({
                "name": label,
                "addon_version": attr(inner, "addon_version"),
                "most_recent": attr(inner, "most_recent"),
            })

        # node groups (managed / self) and fargate profiles
        for label, inner in find_nested_blocks(body, "eks_managed_node_groups"):
            call["managed_node_groups"].append({
                "name": label,
                "ami_type": attr(inner, "ami_type"),
                "version": attr(inner, "version") or attr(inner, "cluster_version"),
                "release_version": attr(inner, "release_version"),
            })
        for label, inner in find_nested_blocks(body, "self_managed_node_groups"):
            call["self_managed_node_groups"].append({
                "name": label,
                "ami_id": attr(inner, "ami_id"),
                "version": attr(inner, "version"),
            })
        for label, _ in find_nested_blocks(body, "fargate_profiles"):
            call["fargate_profiles"].append({"name": label})

        # Investigation hint — tells the skill where to look next.
        call["investigation"] = _investigation_hint(source, root)

        result["eks_module_calls"].append(call)

    # Build top-level hints summarising what the skill should follow up on.
    for call in result["eks_module_calls"]:
        result["investigation_hints"].append(call["investigation"])

    # ── Detect addons declared in two places (standalone + module-managed) ────
    # If the same addon_name appears as both an `aws_eks_addon` resource AND
    # inside a module's `cluster_addons`, Terraform will fight itself.
    warnings: list[dict] = []
    standalone = {a.get("addon_name"): f"aws_eks_addon.{a['name']}"
                  for a in result["addons"] if a.get("addon_name")}
    module_addons: dict[str, list[str]] = {}
    for call in result["eks_module_calls"]:
        for ca in call.get("cluster_addons", []):
            if ca.get("name"):
                module_addons.setdefault(ca["name"], []).append(
                    f"module.{call['name']}.cluster_addons"
                )
    for addon_name, source in standalone.items():
        if addon_name in module_addons:
            warnings.append({
                "type": "addon_double_management",
                "addon": addon_name,
                "declared_in": [source, *module_addons[addon_name]],
                "message": (
                    f"'{addon_name}' is declared both as a standalone aws_eks_addon "
                    "and inside a module's cluster_addons. Terraform will flip it on "
                    "every apply. Remove one declaration."
                ),
            })
    result["warnings"] = warnings

    return result


def _classify_source(source: str) -> str:
    """Best-effort classification of a module source string."""
    s = source.strip()
    if s.startswith((".", "/")):
        return "local"
    if s.startswith(("git::", "git@", "https://github.com", "github.com")):
        return "git"
    if s.count("/") == 2:  # public Terraform Registry: namespace/name/provider
        return "public_registry"
    if "/" in s and "." in s.split("/", 1)[0]:  # host/org/name/provider — private registry
        return "private_registry"
    return "unknown"


def _investigation_hint(source: str, root: Path) -> dict:
    """How the skill should look up the module's schema/versions."""
    kind = _classify_source(source)
    base = {"source": source, "kind": kind}

    if kind == "local":
        local_path = (root / source).resolve() if not Path(source).is_absolute() else Path(source)
        base["local_path"] = str(local_path)
        base["next_step"] = (
            f"Re-run scan_terraform_eks.py on {local_path} to inspect the local module's resources."
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
        print("Usage: scan_terraform_eks.py <tf-root>", file=sys.stderr)
        sys.exit(1)
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"Directory not found: {root}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(scan(root), indent=2))


if __name__ == "__main__":
    main()
