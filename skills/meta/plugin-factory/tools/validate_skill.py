#!/usr/bin/env python3
"""Validate a skill directory: SKILL.md frontmatter, tools declarations, and structure."""

import argparse
import json
import re
import sys
from pathlib import Path


def parse_frontmatter(text):
    """Extract YAML frontmatter as raw text between --- markers."""
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    return parts[1]


def main():
    parser = argparse.ArgumentParser(description="Validate a skill directory.")
    parser.add_argument("--path", required=True, help="Path to skill directory")
    args = parser.parse_args()

    skill_dir = Path(args.path)
    errors = []
    warnings = []

    if not skill_dir.is_dir():
        print(json.dumps({"valid": False, "errors": [f"Not a directory: {args.path}"], "warnings": []}))
        sys.exit(1)

    # SKILL.md
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        errors.append("SKILL.md missing")
    else:
        content = skill_md.read_text()
        fm = parse_frontmatter(content)
        if fm is None:
            errors.append("SKILL.md missing valid frontmatter (--- delimiters)")
        else:
            # Check name field
            name_match = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
            if not name_match:
                errors.append("Frontmatter missing 'name' field")
            else:
                name = name_match.group(1).strip()
                if not re.match(r"^[a-z][a-z0-9-]*$", name):
                    errors.append(f"Name '{name}' is not valid kebab-case (lowercase, hyphens, no spaces)")

            # Check description field
            desc_match = re.search(r"^description:", fm, re.MULTILINE)
            if not desc_match:
                errors.append("Frontmatter missing 'description' field")
            else:
                # Get full description (may be multiline with >)
                desc_text = fm[desc_match.start():]
                desc_lower = desc_text.lower()
                if "use when" not in desc_lower:
                    warnings.append("Description should contain 'Use when...' trigger guidance")
                if "do not use" not in desc_lower:
                    warnings.append("Description should contain 'Do NOT use...' exclusion guidance")

    # tools/mcp_tools.json
    tools_json = skill_dir / "tools" / "mcp_tools.json"
    if tools_json.exists():
        try:
            data = json.loads(tools_json.read_text())
            if "tools" not in data or not isinstance(data["tools"], list):
                errors.append("mcp_tools.json must have a 'tools' array")
            else:
                for i, tool in enumerate(data["tools"]):
                    for key in ("name", "script", "description"):
                        if key not in tool:
                            errors.append(f"mcp_tools.json tools[{i}] missing '{key}'")
                    if "script" in tool:
                        script_path = skill_dir / "tools" / tool["script"]
                        if not script_path.exists():
                            errors.append(f"Referenced script not found: tools/{tool['script']}")
        except json.JSONDecodeError as e:
            errors.append(f"tools/mcp_tools.json invalid JSON: {e}")

    valid = len(errors) == 0
    print(json.dumps({"valid": valid, "errors": errors, "warnings": warnings}))
    if not valid:
        sys.exit(1)


if __name__ == "__main__":
    main()
