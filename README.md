# Skills

A collection of advanced agent skills.

## Available Skills

### DevOps

| Skill                                                  | Description                                                                                                                                                                                                                                                                                        |
| ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [aws-eks-updater](devops/aws-eks-updater/SKILL.md)     | Interactive, safety-first skill for updating an AWS EKS cluster. Verifies prerequisites, inventories the cluster from Terraform definitions, AWS-managed add-ons, and Helm releases, then walks through updates one package at a time with changelog scanning for breaking changes.                |
| [azure-aks-updater](devops/azure-aks-updater/SKILL.md) | Interactive, safety-first skill for updating an Azure AKS cluster. Verifies prerequisites, inventories the cluster from Terraform definitions, Azure-managed add-ons/extensions, and Helm releases, then walks through updates one package at a time with changelog scanning for breaking changes. |

## Structure

```
devops/
  aws-eks-updater/    # AWS EKS cluster update skill
    SKILL.md          # Skill definition and instructions
    agents/           # Sub-agent prompts
    assets/           # Report templates
    references/       # Reference data (breaking-change keywords, EKS compatibility)
    tools/            # Python helper scripts
  azure-aks-updater/  # Azure AKS cluster update skill
    SKILL.md          # Skill definition and instructions
    agents/           # Sub-agent prompts
    assets/           # Report templates
    references/       # Reference data (breaking-change keywords, AKS compatibility)
    tools/            # Python helper scripts
```

## How to Use

### 1. Clone the repository

```bash
git clone https://github.com/your-org/skills.git ~/skills
```

### 2. Symlink the skill(s) you want

Pick any skill from this repo and symlink it into your agent skills folder.

#### GitHub Copilot (VS Code)

Skills live in `~/.agents/skills/`. Create the directory if it doesn't exist:

```bash
mkdir -p ~/.agents/skills
ln -s ~/skills/devops/aws-eks-updater ~/.agents/skills/aws-eks-updater
ln -s ~/skills/devops/azure-aks-updater ~/.agents/skills/azure-aks-updater
```

#### Claude Code

Skills live in `~/.claude/skills/`. Create the directory if it doesn't exist:

```bash
mkdir -p ~/.claude/skills
ln -s ~/skills/devops/aws-eks-updater ~/.claude/skills/aws-eks-updater
ln -s ~/skills/devops/azure-aks-updater ~/.claude/skills/azure-aks-updater
```

After symlinking, the agent will automatically pick up the skill when your request matches its description. Each `SKILL.md` contains the full instructions the agent follows.
