# CLAUDE.md

This is a framework for packaging business logic as discoverable agent skills.
Skills are multi-step playbooks; MCP tools are their stateless building blocks.

## Quick context

- No build system, no tests, no external deps. Deliverables are Markdown + Python scripts.
- `skills/<category>/<skill>/SKILL.md` — the agent entry point (YAML frontmatter + phases)
- `tools/mcp_tools.json` in a skill — auto-discovered by `mcp-server/server.py`
- `skills/manifest.json` — must be updated when adding/removing skills
- `references/` and `assets/` — auto-exposed as MCP resources

## When working here, always:

1. Check `skills/manifest.json` before adding/modifying skills
2. Use `tools/mcp_tools.json` for tool declarations (never hardcode in server.py)
3. Keep Python scripts stdlib-only (no pip install)
4. SKILL.md descriptions must include "Use when..." and "Do NOT use for..."
5. Namespace tools as `<category>__<tool_name>`

## Key files

- `docs/GUIDE.md` — architecture and conventions quick reference
- `docs/CONTRIBUTING.md` — how to add skills, tools, plugins
- `docs/INSTALL.md` — how users install this
- `mcp-server/server.py` — auto-discovering MCP server
