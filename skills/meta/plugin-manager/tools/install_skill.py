#!/usr/bin/env python3
"""Install a skill into a target directory via symlink or copy.

Supports --dry-run to preview the operation without writing anything.
Exits non-zero if the skill cannot be found or the install fails.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path


def _find_repo_root(start: Path) -> Path | None:
    """Walk up from start until a directory containing skills/ is found."""
    current = start
    for _ in range(10):
        if (current / "skills").is_dir():
            return current
        if current.parent == current:
            break
        current = current.parent
    return None


def _resolve_skill_source(name_or_path: str, skills_dir: Path | None) -> Path | None:
    """Resolve a skill name or path to its source directory."""
    # Treat as an explicit path first
    candidate = Path(name_or_path).expanduser()
    if candidate.is_dir() and (candidate / "SKILL.md").exists():
        return candidate

    # Search under skills_dir by directory name
    if skills_dir and skills_dir.is_dir():
        for skill_md in skills_dir.rglob("SKILL.md"):
            if skill_md.parent.name == name_or_path:
                return skill_md.parent

    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Install a skill into a target directory")
    parser.add_argument("--skill", required=True, help="Skill name or path")
    parser.add_argument("--target", required=True, help="Target directory (e.g. ~/.agents/skills)")
    parser.add_argument("--skills-dir", help="Root skills directory to search in")
    parser.add_argument(
        "--method",
        choices=["symlink", "copy"],
        default="symlink",
        help="Install method: symlink (default) or copy",
    )
    parser.add_argument(
        "--dry-run",
        default="false",
        help="Set to 'true' to preview without writing anything",
    )
    args = parser.parse_args()

    dry_run = args.dry_run.lower() not in ("0", "false", "no", "")

    # Resolve skills directory: explicit arg → auto-detect from script location
    if args.skills_dir:
        skills_dir: Path | None = Path(args.skills_dir)
    else:
        repo_root = _find_repo_root(Path(__file__).resolve())
        skills_dir = (repo_root / "skills") if repo_root else None

    source = _resolve_skill_source(args.skill, skills_dir)
    if source is None:
        print(json.dumps({"error": True, "message": f"Skill '{args.skill}' not found"}))
        sys.exit(1)

    target_dir = Path(args.target).expanduser()
    dest = target_dir / source.name

    result: dict = {
        "skill": source.name,
        "source": str(source),
        "destination": str(dest),
        "method": args.method,
        "dry_run": dry_run,
    }

    if dest.exists() or dest.is_symlink():
        result["status"] = "already_exists"
        result["message"] = f"'{dest}' already exists. Remove it first to reinstall."
        print(json.dumps(result, indent=2))
        return

    if dry_run:
        verb = "symlink" if args.method == "symlink" else "copy"
        result["status"] = "dry_run"
        result["message"] = f"Would {verb} '{source}' → '{dest}'"
        print(json.dumps(result, indent=2))
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        if args.method == "symlink":
            dest.symlink_to(source.resolve())
        else:
            shutil.copytree(source, dest)
        result["status"] = "installed"
        result["message"] = f"Installed '{source.name}' to '{dest}'"
    except OSError as exc:
        result["status"] = "error"
        result["error"] = True
        result["message"] = str(exc)
        print(json.dumps(result, indent=2))
        sys.exit(1)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
