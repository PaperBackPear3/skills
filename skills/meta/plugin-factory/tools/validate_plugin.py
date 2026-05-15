#!/usr/bin/env python3
"""Validate a plugin directory structure, configuration files, and symlinks."""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Validate a plugin directory.")
    parser.add_argument("--path", required=True, help="Path to plugin directory")
    args = parser.parse_args()

    plugin_dir = Path(args.path)
    errors = []
    warnings = []

    if not plugin_dir.is_dir():
        print(json.dumps({"valid": False, "errors": [f"Not a directory: {args.path}"], "warnings": []}))
        sys.exit(1)

    # .claude-plugin/plugin.json
    claude_plugin = plugin_dir / ".claude-plugin" / "plugin.json"
    if not claude_plugin.exists():
        errors.append(".claude-plugin/plugin.json missing")
    else:
        try:
            data = json.loads(claude_plugin.read_text())
            for key in ("name", "version", "description"):
                if key not in data:
                    errors.append(f".claude-plugin/plugin.json missing key: {key}")
        except json.JSONDecodeError as e:
            errors.append(f".claude-plugin/plugin.json invalid JSON: {e}")

    # .codex-plugin/plugin.json
    codex_plugin = plugin_dir / ".codex-plugin" / "plugin.json"
    if not codex_plugin.exists():
        errors.append(".codex-plugin/plugin.json missing")
    else:
        try:
            json.loads(codex_plugin.read_text())
        except json.JSONDecodeError as e:
            errors.append(f".codex-plugin/plugin.json invalid JSON: {e}")

    # .mcp.json
    mcp_json = plugin_dir / ".mcp.json"
    if not mcp_json.exists():
        errors.append(".mcp.json missing")
    else:
        try:
            data = json.loads(mcp_json.read_text())
            if "mcpServers" not in data:
                errors.append(".mcp.json missing 'mcpServers' key")
            elif "skills-mcp" not in data.get("mcpServers", {}):
                warnings.append(".mcp.json server key is not 'skills-mcp'")
        except json.JSONDecodeError as e:
            errors.append(f".mcp.json invalid JSON: {e}")

    # skills/ directory
    skills_dir = plugin_dir / "skills"
    if not skills_dir.is_dir():
        errors.append("skills/ directory missing")
    else:
        for entry in skills_dir.iterdir():
            if entry.is_symlink():
                if not entry.resolve().exists():
                    errors.append(f"Broken symlink: skills/{entry.name}")
            else:
                warnings.append(f"skills/{entry.name} is not a symlink")

    # README.md
    if not (plugin_dir / "README.md").exists():
        errors.append("README.md missing")

    valid = len(errors) == 0
    print(json.dumps({"valid": valid, "errors": errors, "warnings": warnings}))
    if not valid:
        sys.exit(1)


if __name__ == "__main__":
    main()
