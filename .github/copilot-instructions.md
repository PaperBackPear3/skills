# Copilot Instructions

## Repository Overview

This is a collection of **agent skills** — self-contained instruction packages that AI coding agents (GitHub Copilot, Claude Code) load at runtime to perform complex DevOps tasks. There is no application code, no build system, and no tests. The deliverables are Markdown prompts, Python helper scripts, and HTML report templates.

Skills are installed by symlinking a skill directory into the agent's skills folder (e.g., `~/.agents/skills/` for Copilot, `~/.claude/skills/` for Claude Code). The agent discovers a skill via the YAML frontmatter (`name`, `description`) in its `SKILL.md`.

## Architecture

Each skill follows an identical structure:

```
devops/<skill-name>/
  SKILL.md              # Entry point — YAML frontmatter + phase-based playbook
  agents/               # Sub-agent prompts (delegated via fan-out)
  assets/               # HTML report templates (Mustache-style {{placeholders}})
  references/           # Static reference data (compatibility matrices, keyword lists)
  tools/                # Python helper scripts (run by the agent at runtime)
```

### SKILL.md conventions

- Starts with YAML frontmatter: `name` and `description` fields (used for skill discovery).
- Body is a **phase-based playbook** (PHASE 0 through PHASE 6) that the agent follows linearly.
- Contains a "hard rules" section at the top with safety constraints.
- Ends with a "Files in this skill" inventory listing every file and its purpose.

### Sub-agents (`agents/`)

Each file is a standalone Markdown prompt given to a sub-agent for parallel fan-out work (e.g., `changelog-researcher.md` fetches changelogs from multiple GitHub repos concurrently via the GitHub MCP server).

### Tools (`tools/`)

Python scripts executed by the agent during specific phases. They are CLI tools that print structured output (typically JSON or plain text) for the agent to parse. Common scripts across skills:

- `check_prereqs.py` — Validates required CLIs and auth (cloud provider, kubectl, helm, terraform).
- `scan_terraform_*.py` — Parses Terraform files to inventory declared resources and versions.
- `inventory_addons.py` — Queries the cloud provider API for installed add-on versions.
- `inventory_helm.py` — Queries Helm for installed release versions.
- `generate_report.py` — Renders HTML reports from templates in `assets/`.

### Report templates (`assets/`)

HTML files with `{{PLACEHOLDER}}` tokens. Two per skill: `plan_template.html` (pre-update plan) and `summary_template.html` (post-update summary).

## Key Conventions

- **Safety-first**: Skills never apply changes without explicit user confirmation. Updates are proposed one package at a time.
- **Mirror structure**: Both skills (`aws-eks-updater`, `azure-aks-updater`) follow the exact same directory layout, phase structure, and naming patterns. When adding a new skill or modifying an existing one, maintain this symmetry.
- **No dependencies to install**: Python scripts use only the standard library. No `requirements.txt` or virtual environment needed.
- **No CI/CD, no tests, no linting**: This repo has no build pipeline. Validation is manual.
