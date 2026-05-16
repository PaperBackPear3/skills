#!/usr/bin/env python3
"""Verify that skills installed in a directory are valid.

For each subdirectory (or symlink to a directory) in the target, checks:
- SKILL.md exists
- SKILL.md frontmatter has name and description fields
- All tool scripts declared in tools/mcp_tools.json are present

Outputs a JSON summary with per-skill pass/fail results.
"""

import argparse
import json
import sys
from pathlib import Path


def _check_skill(skill_dir: Path) -> dict:
    result: dict = {"name": skill_dir.name, "path": str(skill_dir), "checks": [], "valid": True}
    checks: list[dict] = result["checks"]

    def record(check: str, passed: bool, detail: str = "") -> None:
        entry: dict = {"check": check, "status": "pass" if passed else "fail"}
        if detail:
            entry["detail"] = detail
        checks.append(entry)
        if not passed:
            result["valid"] = False

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        record("SKILL.md exists", False)
        return result  # remaining checks are meaningless
    record("SKILL.md exists", True)

    content = skill_md.read_text()
    if content.startswith("---"):
        try:
            end = content.index("---", 3)
            frontmatter = content[3:end]
            record("frontmatter.name", "name:" in frontmatter)
            record("frontmatter.description", "description:" in frontmatter)
        except ValueError:
            record("frontmatter parseable", False, "Missing closing '---'")
    else:
        record("frontmatter present", False, "SKILL.md does not start with '---'")

    tools_json = skill_dir / "tools" / "mcp_tools.json"
    if tools_json.exists():
        try:
            data = json.loads(tools_json.read_text())
            for tool in data.get("tools", []):
                script_name = tool.get("script", "")
                script = skill_dir / "tools" / script_name
                record(f"script:{tool.get('name', script_name)}", script.is_file())
        except json.JSONDecodeError as exc:
            record("mcp_tools.json parseable", False, str(exc))

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify installed skills")
    parser.add_argument("--target", required=True, help="Directory containing installed skills")
    args = parser.parse_args()

    target = Path(args.target).expanduser()
    if not target.is_dir():
        print(json.dumps({"error": True, "message": f"'{target}' is not a directory"}))
        sys.exit(1)

    results = []
    for entry in sorted(target.iterdir()):
        resolved = entry.resolve() if entry.is_symlink() else entry
        if resolved.is_dir():
            results.append(_check_skill(resolved))

    summary = {
        "target": str(target),
        "total": len(results),
        "valid": sum(1 for r in results if r["valid"]),
        "invalid": sum(1 for r in results if not r["valid"]),
        "skills": results,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
