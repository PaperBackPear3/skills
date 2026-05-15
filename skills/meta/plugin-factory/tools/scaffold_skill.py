#!/usr/bin/env python3
"""Create a skill directory with SKILL.md template and optional subdirectories."""

import argparse
import json
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


def name_to_title(name):
    """Convert kebab-case name to Title Case."""
    return " ".join(word.capitalize() for word in name.split("-"))


def main():
    parser = argparse.ArgumentParser(description="Scaffold a skill directory.")
    parser.add_argument("--name", required=True, help="Skill name (kebab-case)")
    parser.add_argument("--category", required=True, help="Skill category")
    parser.add_argument("--description", required=True, help="Skill description")
    parser.add_argument("--with-tools", action="store_true", help="Create tools/ directory")
    parser.add_argument("--with-references", action="store_true", help="Create references/ directory")
    parser.add_argument("--with-agents", action="store_true", help="Create agents/ directory")
    parser.add_argument("--repo-root", default=None, help="Repository root path")
    args = parser.parse_args()

    repo_root = Path(args.repo_root) if args.repo_root else find_repo_root()
    if not repo_root:
        print(json.dumps({"error": True, "message": "Cannot find repo root (no skills/manifest.json found)"}))
        sys.exit(1)

    skill_dir = repo_root / "skills" / args.category / args.name
    if skill_dir.exists():
        print(json.dumps({"error": True, "message": f"Directory already exists: skills/{args.category}/{args.name}"}))
        sys.exit(1)

    skill_dir.mkdir(parents=True)
    created_files = []

    # SKILL.md
    title = name_to_title(args.name)
    skill_md = f"""---
name: {args.name}
description: >
  {args.description}
version: 1
requires_tools: []
requires_mcp: []
tags: []
---

# {title}

## Overview

[Describe what this skill accomplishes]

## Hard Rules

- Never apply changes without user confirmation.

## Phase 1: [First Phase]

[Steps...]
"""
    (skill_dir / "SKILL.md").write_text(skill_md)
    created_files.append("SKILL.md")

    if args.with_tools:
        (skill_dir / "tools").mkdir()
        created_files.append("tools/")

    if args.with_references:
        (skill_dir / "references").mkdir()
        created_files.append("references/")

    if args.with_agents:
        (skill_dir / "agents").mkdir()
        created_files.append("agents/")

    print(json.dumps({"created": True, "path": f"skills/{args.category}/{args.name}", "files": created_files}))


if __name__ == "__main__":
    main()
