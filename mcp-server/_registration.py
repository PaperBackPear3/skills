"""Dynamic registration of tools, prompts, and resources with FastMCP.

Each public function accepts the server instance plus a typed dataclass from
_discovery, keeping registration logic fully separate from filesystem scanning.
"""

import asyncio
import json
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from _discovery import PromptDef, ResourceDef, ToolDef


# ---------------------------------------------------------------------------
# Subprocess runner (used by registered tool functions at call-time)
# ---------------------------------------------------------------------------


async def run_tool_script(script: Path, args: list[str] | None = None) -> str:
    """Run a Python tool script in a subprocess and return its stdout.

    On non-zero exit returns a JSON error object instead of raising so the
    agent always receives parseable output.
    """
    cmd = [sys.executable, str(script)] + (args or [])
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        message = stderr.decode().strip() or f"Script exited with code {proc.returncode}"
        return json.dumps({"error": True, "message": message, "exit_code": proc.returncode})
    return stdout.decode()


# ---------------------------------------------------------------------------
# Public registration helpers
# ---------------------------------------------------------------------------


def register_tool(server: FastMCP, category: str, tool_def: ToolDef, script: Path) -> None:
    """Register a tool (canonical name + any declared aliases) with the MCP server."""
    canonical_name = f"{category}__{tool_def.name}"
    _register_named_tool(server, canonical_name, tool_def.description, script, tool_def.params)

    for alias in tool_def.aliases:
        alias_name = f"{category}__{alias}"
        alias_description = f"[Deprecated alias → {canonical_name}] {tool_def.description}"
        _register_named_tool(server, alias_name, alias_description, script, tool_def.params)


def register_prompt(server: FastMCP, category: str, prompt_def: PromptDef) -> None:
    """Register a prompt template with the MCP server."""
    name = f"{category}__{prompt_def.name}"
    params = prompt_def.params
    template = prompt_def.template

    def prompt_fn(**kwargs: str) -> str:
        return template.format(**kwargs)

    prompt_fn.__name__ = name
    prompt_fn.__doc__ = prompt_def.description
    prompt_fn.__annotations__ = {p["name"]: str for p in params} | {"return": str}
    optional = [p for p in params if not p.get("required", False)]
    prompt_fn.__defaults__ = tuple("" for _ in optional) or None

    server.prompt()(prompt_fn)


def register_resource(server: FastMCP, resource_def: ResourceDef) -> None:
    """Register a file as a read-only MCP resource."""
    _path = resource_def.file_path

    @server.resource(resource_def.uri)
    def resource_fn() -> str:
        return _path.read_text()

    resource_fn.__name__ = (
        f"resource_{resource_def.uri.replace('://', '_').replace('/', '_')}"
    )
    resource_fn.__doc__ = f"Resource: {resource_def.file_path.name}"


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _register_named_tool(
    server: FastMCP,
    name: str,
    description: str,
    script: Path,
    params: list[dict],
) -> None:
    optional_params = [p for p in params if not p.get("required", False)]

    async def tool_fn(**kwargs: str) -> str:
        args: list[str] = []
        for p in params:
            value = kwargs.get(p["name"], "")
            if value:
                args += [p.get("flag", f"--{p['name'].replace('_', '-')}"), str(value)]
        return await run_tool_script(script, args)

    tool_fn.__name__ = name
    tool_fn.__doc__ = description
    tool_fn.__annotations__ = {p["name"]: str for p in params} | {"return": str}
    tool_fn.__defaults__ = tuple("" for _ in optional_params) or None

    server.tool()(tool_fn)
