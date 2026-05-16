"""Filesystem scanning and manifest parsing for skill auto-discovery.

Pure functions only — no side effects, no server imports.
Returns iterators of typed dataclasses that the server uses for registration.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ToolDef:
    name: str
    script: str
    description: str
    params: list[dict] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)


@dataclass
class PromptDef:
    name: str
    description: str
    template: str
    params: list[dict] = field(default_factory=list)


@dataclass
class ResourceDef:
    uri: str
    file_path: Path


@dataclass
class SkillInfo:
    name: str
    category: str
    path: str
    description: str | None = None


# ---------------------------------------------------------------------------
# Public iterators
# ---------------------------------------------------------------------------

_RESOURCE_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".txt"}


def iter_skill_infos(skills_dir: Path) -> Iterator[SkillInfo]:
    """Yield SkillInfo for every valid SKILL.md found under skills_dir."""
    if not skills_dir.is_dir():
        return
    for skill_path in skills_dir.rglob("SKILL.md"):
        info = _parse_skill_info(skill_path, skills_dir)
        if info:
            yield info


def iter_skill_tools(skills_dir: Path) -> Iterator[tuple[str, Path, ToolDef]]:
    """Yield (category, script_path, ToolDef) for every tool in mcp_tools.json files."""
    if not skills_dir.is_dir():
        return
    seen: set[str] = set()
    for manifest_path in skills_dir.rglob("tools/mcp_tools.json"):
        skill_dir = manifest_path.parent.parent
        rel = skill_dir.relative_to(skills_dir)
        category = rel.parts[0] if len(rel.parts) > 1 else "general"
        yield from _parse_tool_manifest(manifest_path, category, seen)


def iter_skill_prompts(skills_dir: Path) -> Iterator[tuple[str, PromptDef]]:
    """Yield (category, PromptDef) for every prompt in mcp_prompts.json files."""
    if not skills_dir.is_dir():
        return
    seen: set[str] = set()
    for manifest_path in skills_dir.rglob("tools/mcp_prompts.json"):
        skill_dir = manifest_path.parent.parent
        rel = skill_dir.relative_to(skills_dir)
        category = rel.parts[0] if len(rel.parts) > 1 else "general"
        yield from _parse_prompt_manifest(manifest_path, category, seen)


def iter_skill_resources(skills_dir: Path) -> Iterator[ResourceDef]:
    """Yield ResourceDef for every reference/asset file under each skill."""
    if not skills_dir.is_dir():
        return
    for skill_path in skills_dir.rglob("SKILL.md"):
        skill_dir = skill_path.parent
        rel = skill_dir.relative_to(skills_dir)
        category = rel.parts[0] if len(rel.parts) > 1 else "general"
        skill_name = rel.parts[-1] if len(rel.parts) > 1 else rel.parts[0]
        yield from _iter_dir_resources(skill_dir / "references", category, skill_name, "references")
        yield from _iter_dir_resources(skill_dir / "assets", category, skill_name, "assets")


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _parse_skill_info(skill_path: Path, skills_dir: Path) -> SkillInfo | None:
    content = skill_path.read_text()
    if not content.startswith("---"):
        return None
    try:
        end = content.index("---", 3)
        frontmatter = content[3:end]
    except ValueError:
        return None

    name_match = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
    if not name_match:
        return None
    desc_match = re.search(r"description:\s*>?\s*\n?((?:\s+.+\n?)+)", frontmatter)

    rel = skill_path.relative_to(skills_dir)
    return SkillInfo(
        name=name_match.group(1).strip(),
        category=rel.parts[0] if len(rel.parts) > 2 else "general",
        path=str(rel.parent),
        description=" ".join(desc_match.group(1).split()) if desc_match else None,
    )


def _parse_tool_manifest(
    manifest_path: Path, category: str, seen: set[str]
) -> Iterator[tuple[str, Path, ToolDef]]:
    try:
        data = json.loads(manifest_path.read_text())
    except (json.JSONDecodeError, OSError):
        return
    for raw in data.get("tools", []):
        canonical = f"{category}__{raw['name']}"
        if canonical in seen:
            continue
        seen.add(canonical)
        tool_def = ToolDef(
            name=raw["name"],
            script=raw["script"],
            description=raw.get("description", f"Run {raw['script']}"),
            params=raw.get("params", []),
            aliases=raw.get("aliases", []),
        )
        yield category, manifest_path.parent / raw["script"], tool_def


def _parse_prompt_manifest(
    manifest_path: Path, category: str, seen: set[str]
) -> Iterator[tuple[str, PromptDef]]:
    try:
        data = json.loads(manifest_path.read_text())
    except (json.JSONDecodeError, OSError):
        return
    for raw in data.get("prompts", []):
        canonical = f"{category}__{raw['name']}"
        if canonical in seen:
            continue
        seen.add(canonical)
        yield category, PromptDef(
            name=raw["name"],
            description=raw.get("description", raw["name"]),
            template=raw.get("template", ""),
            params=raw.get("params", []),
        )


def _iter_dir_resources(
    directory: Path, category: str, skill_name: str, subfolder: str
) -> Iterator[ResourceDef]:
    if not directory.is_dir():
        return
    for f in directory.iterdir():
        if not f.is_file():
            continue
        if subfolder == "references" and f.suffix not in _RESOURCE_SUFFIXES:
            continue
        yield ResourceDef(
            uri=f"skills://{category}/{skill_name}/{subfolder}/{f.name}",
            file_path=f,
        )
