# Skills MCP Server

An MCP (Model Context Protocol) server that exposes the DevOps skill tools as MCP tools, resources, and prompts.

## Prerequisites

- Python 3.10+
- Cloud CLIs: `aws` (for EKS tools), `az` (for AKS tools)
- `kubectl` and `helm` (for cluster inventory tools)
- `terraform` (for scan tools)

## Installation

```bash
cd mcp-server
pip install -r requirements.txt
```

## Running

```bash
python server.py
```

The server uses **stdio transport** (stdin/stdout) — it's designed to be launched by an MCP client.

## Configuration

### VS Code (GitHub Copilot)

Add to your `.vscode/mcp.json` or user MCP settings:

```json
{
  "servers": {
    "skills": {
      "command": "python",
      "args": ["<path-to-repo>/mcp-server/server.py"],
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
    "skills": {
      "command": "python",
      "args": ["<path-to-repo>/mcp-server/server.py"]
    }
  }
}
```

## Available Tools

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

## Available Prompts

| Prompt | Description | Arguments |
|--------|-------------|-----------|
| `analyze_drift` | Compare inventory vs Terraform versions | `inventory_json`, `terraform_json` |
| `changelog_research` | Research changelog between versions | `package`, `from_version`, `to_version` |
| `upgrade_plan` | Generate upgrade plan from drift analysis | `drift_analysis` |
