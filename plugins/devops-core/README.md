# DevOps Core Plugin

Interactive, safety-first skills for updating Kubernetes clusters (EKS and AKS).

## Installation

### Claude Code

```bash
claude plugin add github:PaperBackPear3/awesome-agent-toolkits/plugins/devops-core
```

### Codex

Add to your `.codex/plugins.json`:

```json
{
  "plugins": ["github:PaperBackPear3/awesome-agent-toolkits/plugins/devops-core"]
}
```

### Manual

1. Clone this repository
2. Symlink or copy `plugins/devops-core/` into your agent's plugin directory
3. The MCP server starts automatically via `.mcp.json`

## Included Skills

- **aws-eks-updater** — Guided EKS cluster upgrades (control plane, add-ons, Helm)
- **azure-aks-updater** — Guided AKS cluster upgrades (control plane, add-ons, Helm)

## MCP Server

The plugin includes an MCP server providing tools for:
- Cluster add-on inventory (AWS/Azure APIs)
- Terraform scanning for declared versions
- Helm release inventory
- Prerequisite checks
- Skill discovery (`list_skills`, `retrieve_skill`)
