"""
MCP server with auto-discovery of tools from skill directories.

Tools are discovered from skills/<category>/<skill>/tools/mcp_tools.json files.
Prompts are discovered from skills/<category>/<skill>/tools/mcp_prompts.json files.
Resources are auto-discovered from skills/<category>/<skill>/references/ and assets/.
Skill discovery (list_skills, retrieve_skill) is always available.
"""

import asyncio
import json
import re
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

server = FastMCP("skills-mcp-server")


# --- Utility ---


async def run_tool_script(script: Path, args: list[str] | None = None) -> str:
    """Run a Python tool script as subprocess and return stdout or raise on error."""
    cmd = [sys.executable, str(script)] + (args or [])
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        error_msg = stderr.decode().strip() or f"Script exited with code {proc.returncode}"
        return json.dumps({"error": True, "message": error_msg, "exit_code": proc.returncode})
    return stdout.decode()


# --- Skill Discovery (always available) ---


@server.tool()
async def list_skills() -> str:
    """List all available skills with their names, categories, and descriptions."""
    skills = []
    for skill_path in SKILLS_DIR.rglob("SKILL.md"):
        content = skill_path.read_text()
        if content.startswith("---"):
            try:
                end = content.index("---", 3)
                frontmatter = content[3:end]
                name_match = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
                desc_match = re.search(r"description:\s*>?\s*\n?((?:\s+.+\n?)+)", frontmatter)
                if name_match:
                    # Derive category from path: skills/<category>/<skill>/SKILL.md
                    rel = skill_path.relative_to(SKILLS_DIR)
                    category = rel.parts[0] if len(rel.parts) > 2 else "general"
                    skill_info = {
                        "name": name_match.group(1).strip(),
                        "category": category,
                        "path": str(rel.parent),
                    }
                    if desc_match:
                        skill_info["description"] = " ".join(desc_match.group(1).split())
                    skills.append(skill_info)
            except ValueError:
                continue
    return json.dumps(skills, indent=2)


@server.tool()
async def retrieve_skill(name: str) -> str:
    """Retrieve a skill by name. Returns the full SKILL.md content."""
    for skill_path in SKILLS_DIR.rglob("SKILL.md"):
        content = skill_path.read_text()
        if content.startswith("---"):
            try:
                end = content.index("---", 3)
                frontmatter = content[3:end]
                if f"name: {name}" in frontmatter:
                    return content
            except ValueError:
                continue
    return json.dumps({"error": True, "message": f"Skill '{name}' not found"})


# --- Auto-discovered Tools ---


def _discover_and_register_tools():
    """Scan skills for mcp_tools.json and register tools dynamically."""
    for tools_manifest in SKILLS_DIR.rglob("tools/mcp_tools.json"):
        skill_dir = tools_manifest.parent.parent
        rel = skill_dir.relative_to(SKILLS_DIR)
        category = rel.parts[0] if len(rel.parts) > 1 else "general"

        try:
            manifest = json.loads(tools_manifest.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        for tool_def in manifest.get("tools", []):
            tool_name = f"{category}__{tool_def['name']}"
            script_path = tools_manifest.parent / tool_def["script"]
            description = tool_def.get("description", f"Run {tool_def['script']}")
            params = tool_def.get("params", [])

            # Create a closure-based async tool function
            _register_dynamic_tool(tool_name, description, script_path, params)


def _register_dynamic_tool(
    name: str, description: str, script: Path, params: list[dict]
):
    """Register a single dynamic tool with the MCP server."""

    # Build the parameter signature for the tool
    param_names = [p["name"] for p in params]
    required_params = [p["name"] for p in params if p.get("required", False)]
    optional_params = [p["name"] for p in params if not p.get("required", False)]

    async def tool_fn(**kwargs) -> str:
        args = []
        for p in params:
            value = kwargs.get(p["name"], "")
            if value:
                if "flag" in p:
                    args += [p["flag"], str(value)]
                else:
                    args += [f"--{p['name'].replace('_', '-')}", str(value)]
        return await run_tool_script(script, args)

    # Set function metadata for FastMCP
    tool_fn.__name__ = name
    tool_fn.__doc__ = description

    # Build annotations for typed parameters
    annotations = {}
    for p in params:
        annotations[p["name"]] = str
    # Add defaults for optional params
    defaults = tuple("" for _ in optional_params)
    tool_fn.__defaults__ = defaults if defaults else None
    tool_fn.__annotations__ = {**annotations, "return": str}

    server.tool()(tool_fn)


# --- Auto-discovered Resources ---


def _discover_and_register_resources():
    """Scan skills for references/ and assets/ files and register as resources."""
    for skill_path in SKILLS_DIR.rglob("SKILL.md"):
        skill_dir = skill_path.parent
        rel = skill_dir.relative_to(SKILLS_DIR)
        category = rel.parts[0] if len(rel.parts) > 1 else "general"
        skill_name = rel.parts[-1] if len(rel.parts) > 1 else rel.parts[0]

        # Register references
        refs_dir = skill_dir / "references"
        if refs_dir.is_dir():
            for ref_file in refs_dir.iterdir():
                if ref_file.is_file() and ref_file.suffix in (".md", ".json", ".yaml", ".yml", ".txt"):
                    uri = f"skills://{category}/{skill_name}/references/{ref_file.name}"
                    _register_resource(uri, ref_file)

        # Register assets
        assets_dir = skill_dir / "assets"
        if assets_dir.is_dir():
            for asset_file in assets_dir.iterdir():
                if asset_file.is_file():
                    uri = f"skills://{category}/{skill_name}/assets/{asset_file.name}"
                    _register_resource(uri, asset_file)


def _register_resource(uri: str, file_path: Path):
    """Register a single file as an MCP resource."""
    desc = f"Resource: {file_path.name}"

    @server.resource(uri)
    def resource_fn(path=file_path, description=desc) -> str:
        return path.read_text()

    resource_fn.__name__ = f"resource_{uri.replace('://', '_').replace('/', '_')}"
    resource_fn.__doc__ = desc


# --- Auto-discovered Prompts ---


def _discover_and_register_prompts():
    """Scan skills for mcp_prompts.json and register prompts dynamically."""
    seen = set()
    for prompts_manifest in SKILLS_DIR.rglob("tools/mcp_prompts.json"):
        skill_dir = prompts_manifest.parent.parent
        rel = skill_dir.relative_to(SKILLS_DIR)
        category = rel.parts[0] if len(rel.parts) > 1 else "general"

        try:
            manifest = json.loads(prompts_manifest.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        for prompt_def in manifest.get("prompts", []):
            prompt_name = f"{category}__{prompt_def['name']}"
            if prompt_name in seen:
                continue
            seen.add(prompt_name)
            _register_dynamic_prompt(
                prompt_name,
                prompt_def.get("description", prompt_def["name"]),
                prompt_def.get("template", ""),
                prompt_def.get("params", []),
            )


def _register_dynamic_prompt(name: str, description: str, template: str, params: list[dict]):
    """Register a single dynamic prompt with the MCP server."""

    def prompt_fn(**kwargs) -> str:
        return template.format(**kwargs)

    prompt_fn.__name__ = name
    prompt_fn.__doc__ = description

    annotations = {p["name"]: str for p in params}
    annotations["return"] = str
    prompt_fn.__annotations__ = annotations

    optional = [p for p in params if not p.get("required", False)]
    prompt_fn.__defaults__ = tuple("" for _ in optional) if optional else None

    server.prompt()(prompt_fn)


# --- Bootstrap and Entry Point ---


_discover_and_register_tools()
_discover_and_register_resources()
_discover_and_register_prompts()

if __name__ == "__main__":
    server.run()
