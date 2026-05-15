# Skills MCP Server

An MCP (Model Context Protocol) server that exposes skill tools as MCP tools, resources, and prompts. It auto-discovers skills from any domain (devops, security, data, etc.) and makes their tools available to any MCP-compatible agent.

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (for `uvx` usage)
- Domain-specific CLIs as needed by individual skills (e.g., `aws`, `az`, `kubectl`, `helm`, `terraform`)

## Installation

### Option 1: uvx (Recommended)

No install needed — `uvx` runs the server directly from PyPI:

```json
{
  "mcpServers": {
    "awesome-agent-toolkits-mcp": {
      "command": "uvx",
      "args": ["awesome-agent-toolkits-mcp-server@latest"]
    }
  }
}
```

Pass `--skills-dir` to point at your skills directory:

```json
{
  "mcpServers": {
    "awesome-agent-toolkits-mcp": {
      "command": "uvx",
      "args": ["awesome-agent-toolkits-mcp-server@latest", "--skills-dir", "/path/to/skills"]
    }
  }
}
```

### Option 2: Docker (Local Development)

From the repo root:

```bash
docker compose up mcp-server
```

This builds the server image and mounts `./skills` as a read-only volume. Configure your agent to use it with stdio transport.

### Option 3: Run from source

```bash
cd mcp-server
pip install -r requirements.txt
python server.py
```

Or with a custom skills directory:

```bash
python server.py --skills-dir /path/to/skills
```

The `SKILLS_DIR` environment variable is also supported.

The server uses **stdio transport** (stdin/stdout) — it's designed to be launched by an MCP client.

## Configuration Examples

### VS Code (GitHub Copilot)

Add to your `.vscode/mcp.json` or user MCP settings:

```json
{
  "servers": {
    "awesome-agent-toolkits-mcp": {
      "command": "uvx",
      "args": ["awesome-agent-toolkits-mcp-server@latest"],
      "transportType": "stdio"
    }
  }
}
```

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "awesome-agent-toolkits-mcp": {
      "command": "uvx",
      "args": ["awesome-agent-toolkits-mcp-server@latest"]
    }
  }
}
```

## Available Tools (Examples)

The server auto-discovers tools from all installed skills. Below are examples from the included devops skills:

| Tool | Description | Parameters |
|------|-------------|------------|
| `eks_inventory_addons` | Inventory EKS add-ons via AWS API | `cluster`, `region`, `profile` (optional) |
| `aks_inventory_addons` | Inventory AKS add-ons via Azure API | `cluster`, `resource_group`, `subscription` (optional) |
| `inventory_helm` | List Helm releases in current context | — |
| `eks_scan_terraform` | Scan Terraform for EKS resources | `root_dir` |
| `aks_scan_terraform` | Scan Terraform for AKS resources | `root_dir` |
| `check_prereqs` | Validate CLI/auth prerequisites | `provider` (aws\|azure), `profile` (optional) |

## Available Resources

| URI | Description |
|-----|-------------|
| `skills://eks/compatibility` | EKS add-on compatibility matrix |
| `skills://aks/compatibility` | AKS add-on compatibility matrix |
| `skills://eks/report-templates` | EKS HTML report templates |
| `skills://aks/report-templates` | AKS HTML report templates |

## Adding Tools from New Skills

To expose a new skill's tools via MCP, create a `tools/mcp_tools.json` file in the skill directory:

```json
{
  "tools": [
    {
      "name": "my_tool_name",
      "script": "my_script.py",
      "description": "What this tool does.",
      "params": [
        { "name": "param_name", "flag": "--param-name", "required": true, "description": "Param description" }
      ]
    }
  ]
}
```

The MCP server auto-discovers these at startup. Tools are namespaced by category: `<category>__<tool_name>` (e.g., `devops__eks_inventory_addons`).

### Adding Resources

Any files in `references/` or `assets/` within a skill directory are automatically exposed as MCP resources with URI pattern:
```
skills://<category>/<skill-name>/references/<filename>
skills://<category>/<skill-name>/assets/<filename>
```

## Available Prompts

Prompts are auto-discovered from `tools/mcp_prompts.json` in each skill directory, namespaced as `<category>__<prompt_name>`. Example prompts from the devops skills:

| Prompt | Description | Arguments |
|--------|-------------|-----------|
| `devops__analyze_drift` | Compare inventory vs Terraform versions | `inventory_json`, `terraform_json` |
| `devops__changelog_research` | Research changelog between versions | `package`, `from_version`, `to_version` |
| `devops__upgrade_plan` | Generate upgrade plan from drift analysis | `drift_analysis` |

### Adding Prompts

Create a `tools/mcp_prompts.json` in your skill directory:

```json
{
  "prompts": [
    {
      "name": "my_prompt",
      "description": "What this prompt produces.",
      "params": [
        { "name": "input_data", "required": true, "description": "Data to analyze" }
      ],
      "template": "Analyze the following:\n\n{input_data}\n\nProduce a summary."
    }
  ]
}
```
