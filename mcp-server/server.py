"""
MCP server for awesome-agent-toolkits.

Discovers tools, prompts, and resources from skill directories and registers
them with FastMCP. Built-in tools (list_skills, retrieve_skill) are always
available regardless of which skills directory is loaded.

Discovery logic:   _discovery.py
Registration logic: _registration.py
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from _discovery import iter_skill_infos, iter_skill_prompts, iter_skill_resources, iter_skill_tools
from _registration import register_prompt, register_resource, register_tool

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR: Path | None = None  # Set in main()

server = FastMCP("awesome-agent-toolkits-mcp-server")


# ---------------------------------------------------------------------------
# Built-in tools (always present, no mcp_tools.json required)
# ---------------------------------------------------------------------------


@server.tool()
async def list_skills() -> str:
    """List all available skills with their names, categories, and descriptions."""
    skills = [
        {k: v for k, v in vars(s).items() if v is not None}
        for s in iter_skill_infos(SKILLS_DIR)
    ]
    return json.dumps(skills, indent=2)


@server.tool()
async def retrieve_skill(name: str) -> str:
    """Retrieve a skill's full SKILL.md content by name."""
    for skill_path in SKILLS_DIR.rglob("SKILL.md"):
        content = skill_path.read_text()
        if _frontmatter_name_matches(content, name):
            return content
    return json.dumps({"error": True, "message": f"Skill '{name}' not found"})


def _frontmatter_name_matches(content: str, name: str) -> bool:
    if not content.startswith("---"):
        return False
    try:
        end = content.index("---", 3)
        frontmatter = content[3:end]
        return bool(re.search(rf"^name:\s*{re.escape(name)}\s*$", frontmatter, re.MULTILINE))
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------


def _bootstrap(skills_dir: Path) -> None:
    """Discover and register all tools, resources, and prompts from skills_dir."""
    for category, script, tool_def in iter_skill_tools(skills_dir):
        register_tool(server, category, tool_def, script)
    for resource_def in iter_skill_resources(skills_dir):
        register_resource(server, resource_def)
    for category, prompt_def in iter_skill_prompts(skills_dir):
        register_prompt(server, category, prompt_def)


def _resolve_skills_dir(args: argparse.Namespace) -> Path:
    if args.skills_dir:
        return Path(args.skills_dir)
    if "SKILLS_DIR" in os.environ:
        return Path(os.environ["SKILLS_DIR"])
    # When installed via uvx the repo root doesn't exist on the host machine.
    # Prefer a user-level skills directory; fall back to the repo path in dev.
    user_skills = Path.home() / ".agents" / "skills"
    repo_skills = REPO_ROOT / "skills"
    if user_skills.is_dir():
        return user_skills
    if repo_skills.is_dir():
        return repo_skills
    return user_skills  # will be empty; discovery finds nothing


def main() -> None:
    global SKILLS_DIR
    parser = argparse.ArgumentParser(description="Skills MCP Server")
    parser.add_argument("--skills-dir", help="Path to skills directory")
    args = parser.parse_args()

    SKILLS_DIR = _resolve_skills_dir(args)

    if not SKILLS_DIR.is_dir():
        print(
            f"Warning: skills directory '{SKILLS_DIR}' does not exist. "
            "No skills will be available. "
            "Use --skills-dir or set SKILLS_DIR to point at your skills directory.",
            file=sys.stderr,
        )

    _bootstrap(SKILLS_DIR)
    server.run()


if __name__ == "__main__":
    main()
