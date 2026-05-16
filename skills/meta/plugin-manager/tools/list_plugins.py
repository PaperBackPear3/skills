#!/usr/bin/env python3
"""List available plugins from a plugins directory or marketplace JSON file.

Outputs a JSON array where each entry contains at minimum: name, path.
Additional fields (description, version, author, category) are included when
found in the plugin's manifest files.

Auto-detection order (when no flags are given):
  1. .agents/plugins/marketplace.json  (Codex / general marketplace)
  2. .claude-plugin/marketplace.json   (Claude Code marketplace)
  3. plugins/                          (walk the directory directly)
"""

import argparse
import json
import sys
from pathlib import Path

# Known marketplace file locations, in preference order
_MARKETPLACE_CANDIDATES = [
    ".agents/plugins/marketplace.json",
    ".claude-plugin/marketplace.json",
]


def _find_repo_root(start: Path) -> Path | None:
    """Walk up from start until a repo root is found (contains skills/ or plugins/)."""
    current = start
    for _ in range(10):
        if (current / "skills").is_dir() or (current / "plugins").is_dir():
            return current
        if current.parent == current:
            break
        current = current.parent
    return None


def _read_plugin_manifest(plugin_dir: Path) -> dict:
    """Read the best available plugin manifest and return its fields."""
    for manifest_rel in (".codex-plugin/plugin.json", ".claude-plugin/plugin.json"):
        manifest = plugin_dir / manifest_rel
        if manifest.exists():
            try:
                return json.loads(manifest.read_text())
            except (json.JSONDecodeError, OSError):
                pass
    return {}


def _list_from_plugins_dir(plugins_dir: Path) -> list[dict]:
    plugins = []
    for entry in sorted(plugins_dir.iterdir()):
        if not entry.is_dir():
            continue
        plugin_info: dict = {"name": entry.name, "path": str(entry)}
        manifest = _read_plugin_manifest(entry)
        for field in ("description", "version", "author"):
            if field in manifest:
                plugin_info[field] = manifest[field]
        if "interface" in manifest:
            plugin_info["category"] = manifest["interface"].get("category", "")
        plugins.append(plugin_info)
    return plugins


def _list_from_marketplace(marketplace_path: Path) -> list[dict]:
    try:
        data = json.loads(marketplace_path.read_text())
        return data if isinstance(data, list) else data.get("plugins", [])
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Error reading marketplace file: {exc}", file=sys.stderr)
        return []


def _autodetect(start: Path) -> list[dict]:
    """Try known marketplace files first, then fall back to walking plugins/."""
    repo_root = _find_repo_root(start)
    if repo_root is None:
        print(
            "No repo root found. Use --plugins-dir or --marketplace.", file=sys.stderr
        )
        return []

    # Prefer curated marketplace files (they have richer metadata)
    for rel in _MARKETPLACE_CANDIDATES:
        candidate = repo_root / rel
        if candidate.exists():
            return _list_from_marketplace(candidate)

    # Fall back to walking the plugins directory
    plugins_dir = repo_root / "plugins"
    if plugins_dir.is_dir():
        return _list_from_plugins_dir(plugins_dir)

    print("No marketplace file or plugins/ directory found.", file=sys.stderr)
    return []


def main() -> None:
    parser = argparse.ArgumentParser(description="List available plugins")
    parser.add_argument("--plugins-dir", help="Path to plugins directory")
    parser.add_argument("--marketplace", help="Path to marketplace.json file")
    args = parser.parse_args()

    if args.marketplace:
        plugins = _list_from_marketplace(Path(args.marketplace))
    elif args.plugins_dir:
        plugins = _list_from_plugins_dir(Path(args.plugins_dir))
    else:
        plugins = _autodetect(Path(__file__).resolve())

    print(json.dumps(plugins, indent=2))


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
