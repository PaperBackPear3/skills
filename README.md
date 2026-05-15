# Agent Skills Toolkit

A collection of agent skills and an MCP server for DevOps workflows — structured for use with Claude Code, Codex, GitHub Copilot, and other AI coding agents.

## Quick Start

### Claude Code

```bash
claude plugin add github:PaperBackPear3/skills/plugins/devops-core
```

### Codex

```json
{ "plugins": ["github:PaperBackPear3/skills/plugins/devops-core"] }
```

### Manual (any agent)

Copy a skill into your agent's skill directory:

```bash
cp -r skills/devops/aws-eks-updater ~/.agents/skills/
```

Or point your agent at the MCP server for dynamic skill discovery:

```json
{
  "mcpServers": {
    "devops-skills": {
      "command": "python3",
      "args": ["<path-to-repo>/mcp-server/server.py"]
    }
  }
}
```

## What's Included

### Plugins

| Plugin | Description |
|--------|-------------|
| `devops-core` | Kubernetes cluster update skills with MCP tools |

### Skills

| Skill | Category | Description |
|-------|----------|-------------|
| [`aws-eks-updater`](skills/devops/aws-eks-updater/SKILL.md) | DevOps | Interactive, safety-first EKS cluster upgrades |
| [`azure-aks-updater`](skills/devops/azure-aks-updater/SKILL.md) | DevOps | Interactive, safety-first AKS cluster upgrades |

### MCP Server

The MCP server (`mcp-server/server.py`) exposes:

- **Tools** — Cluster inventory, Terraform scanning, Helm inventory, prerequisite checks, skill discovery
- **Resources** — Compatibility matrices, report templates
- **Prompts** — Drift analysis, changelog research, upgrade planning

## Repository Structure

```
.claude-plugin/         # Claude Code marketplace index
.agents/plugins/        # Kiro/generic agent marketplace index
plugins/                # Installable plugin packages
  devops-core/          # DevOps plugin (skills + MCP config)
skills/                 # Canonical skill definitions
  devops/
    aws-eks-updater/
    azure-aks-updater/
rules/                  # Agent behavior rules
mcp-server/             # MCP server implementation
docs/                   # Documentation
```

## Documentation

- [Skills Overview](skills/README.md)
- [MCP Server](mcp-server/README.md)
- [Best Practices](docs/BEST_PRACTICES.md)
- [Agent Rules](rules/devops-agent-rules.md)

## License

MIT
