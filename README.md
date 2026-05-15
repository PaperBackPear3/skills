# Skills

A collection of advanced agent skills for GitHub Copilot.

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

## Usage

Skills are loaded by GitHub Copilot agent when the user's request matches the skill description. Each `SKILL.md` contains the full instructions the agent follows.
