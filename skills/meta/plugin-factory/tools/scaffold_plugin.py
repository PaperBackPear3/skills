#!/usr/bin/env python3
"""Create a complete plugin directory structure with all required configuration files."""

import argparse
import json
import os
import sys
from pathlib import Path


def find_repo_root(start=None):
    """Walk up from start looking for skills/manifest.json."""
    current = Path(start) if start else Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "skills" / "manifest.json").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def main():
    parser = argparse.ArgumentParser(description="Scaffold a plugin directory.")
    parser.add_argument("--name", required=True, help="Plugin name (kebab-case)")
    parser.add_argument("--description", required=True, help="Plugin description")
    parser.add_argument("--author", default="PaperBackPear3", help="Author name")
    parser.add_argument("--skills", default="", help="Comma-separated skill names to symlink")
    parser.add_argument("--repo-root", default=None, help="Repository root path")
    args = parser.parse_args()

    repo_root = Path(args.repo_root) if args.repo_root else find_repo_root()
    if not repo_root:
        print(json.dumps({"error": True, "message": "Cannot find repo root (no skills/manifest.json found)"}))
        sys.exit(1)

    plugin_dir = repo_root / "plugins" / args.name
    if plugin_dir.exists():
        print(json.dumps({"error": True, "message": f"Directory already exists: plugins/{args.name}"}))
        sys.exit(1)

    metadata = {
        "name": args.name,
        "version": "1.0.0",
        "description": args.description,
        "author": args.author
    }

    mcp_json = {
        "mcpServers": {
            "awesome-agent-toolkits-mcp": {
                "command": "uvx",
                "args": ["awesome-agent-toolkits-mcp-server@latest"]
            }
        }
    }

    created_files = []

    # Create directories
    (plugin_dir / ".claude-plugin").mkdir(parents=True)
    (plugin_dir / ".codex-plugin").mkdir(parents=True)
    (plugin_dir / "skills").mkdir(parents=True)

    # .claude-plugin/plugin.json
    p = plugin_dir / ".claude-plugin" / "plugin.json"
    p.write_text(json.dumps(metadata, indent=2) + "\n")
    created_files.append(".claude-plugin/plugin.json")

    # .codex-plugin/plugin.json
    p = plugin_dir / ".codex-plugin" / "plugin.json"
    p.write_text(json.dumps(metadata, indent=2) + "\n")
    created_files.append(".codex-plugin/plugin.json")

    # .mcp.json
    p = plugin_dir / ".mcp.json"
    p.write_text(json.dumps(mcp_json, indent=2) + "\n")
    created_files.append(".mcp.json")

    # README.md
    p = plugin_dir / "README.md"
    p.write_text(f"# {args.name}\n\n{args.description}\n")
    created_files.append("README.md")

    created_files.append("skills/")

    print(json.dumps({"created": True, "path": f"plugins/{args.name}", "files": created_files}))


if __name__ == "__main__":
    main()
