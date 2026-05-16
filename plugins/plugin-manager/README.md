# Plugin Manager

Discover, install, and verify skills and plugins from the awesome-agent-toolkits registry.

## What it does

- **List** available plugins and skills from the registry
- **Install** skills into your agent tools directory (`~/.agents/skills/`) by symlink or copy
- **Verify** that installed skills are valid and complete

## Skill loaded

`plugin-manager` — available via `retrieve_skill("plugin-manager")` once the MCP server is running.

## MCP server

This plugin connects to the `awesome-agent-toolkits-mcp-server`, which auto-discovers and exposes all installed skills.

## Usage

Once your agent loads this plugin, ask it to:

- "What skills are available?"
- "Install the devops-core skills"
- "Verify my installed skills"
