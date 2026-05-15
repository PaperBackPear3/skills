# Agent Skills Toolkit

A framework for packaging business logic as discoverable, composable agent skills — served via MCP to Claude Code, Codex, GitHub Copilot, and other AI coding agents.

Skills can encode expertise from **any domain**: DevOps, security, data engineering, finance, compliance, and more. Each skill is a self-contained instruction package that an agent loads at runtime to perform complex, multi-step tasks safely.

## Quick Start

### Claude Code

Install a plugin (e.g. the DevOps plugin — one of the available plugins):

```bash
claude plugin add github:PaperBackPear3/awsome-agent-toolkits/plugins/devops-core
```

### Codex

```json
{ "plugins": ["github:PaperBackPear3/awsome-agent-toolkits/plugins/devops-core"] }
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
    "skills": {
      "command": "uvx",
      "args": ["skills-mcp-server@latest"]
    }
  }
}
```

## What's Included

### Plugins

| Plugin | Category | Description | Status |
|--------|----------|-------------|--------|
| `devops-core` | DevOps | Kubernetes cluster update skills (EKS + AKS) with MCP tools | ✅ Available |
| _more coming_ | Security, Data, Finance… | Community and first-party plugins | 🚧 Planned |

### Skills (via `devops-core`)

| Skill | Description |
|-------|-------------|
| [`aws-eks-updater`](skills/devops/aws-eks-updater/SKILL.md) | Interactive, safety-first EKS cluster upgrades |
| [`azure-aks-updater`](skills/devops/azure-aks-updater/SKILL.md) | Interactive, safety-first AKS cluster upgrades |

### MCP Server

The MCP server (published as `skills-mcp-server` via uvx) exposes skills as tools, resources, and prompts — making them discoverable by any MCP-compatible agent without manual installation.

## Repository Structure

> This layout is **extensible** — add new domains by creating a directory under `skills/` and a corresponding plugin under `plugins/`.

```
.claude-plugin/         # Claude Code marketplace index
.agents/plugins/        # Kiro/generic agent marketplace index
plugins/                # Installable plugin packages
  devops-core/          #   └─ DevOps plugin (skills + MCP config)
skills/                 # Canonical skill definitions
  devops/               #   └─ DevOps skills (EKS, AKS)
    aws-eks-updater/
    azure-aks-updater/
rules/                  # Agent behavior rules
mcp-server/             # MCP server implementation
docs/                   # Documentation
```

## Documentation

| Doc | What it covers |
|-----|---------------|
| [Installation Guide](docs/INSTALL.md) | All install methods (plugin, MCP, manual, symlink) |
| [Contributing: Add New Stuff](docs/CONTRIBUTING.md) | How to add skills, tools, plugins, rules |
| [Quick Reference Guide](docs/GUIDE.md) | Architecture, concepts, conventions |
| [Best Practices](docs/BEST_PRACTICES.md) | MCP vs Agents vs Tools vs Skills deep-dive |
| [MCP Server](mcp-server/README.md) | Server setup and available tools |
| [Agent Rules](rules/devops-agent-rules.md) | Behavioral guardrails |

## License

MIT
