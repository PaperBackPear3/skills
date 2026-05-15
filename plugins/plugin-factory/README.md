# plugin-factory

A meta-plugin for creating new plugins and skills in this repository.

## What it does

- Scaffolds complete plugin directory structures
- Creates skills with proper SKILL.md frontmatter and phased workflows
- Generates MCP tool scripts and declarations
- Validates plugins and skills against repository conventions
- Registers everything in manifests and marketplace files

## Installation

### Claude Code

```bash
/plugin marketplace add PaperBackPear3/skills
/plugin install plugin-factory@skills
```

### Codex

```bash
codex plugin marketplace add PaperBackPear3/skills
# Then install plugin-factory from /plugins
```

## Skills included

- **plugin-factory** — Interactive workflow for creating plugins and skills from scratch

## MCP Tools

| Tool | Description |
|------|-------------|
| `meta__scaffold_plugin` | Create plugin directory structure |
| `meta__scaffold_skill` | Create skill directory with SKILL.md template |
| `meta__validate_plugin` | Validate plugin structure and config |
| `meta__validate_skill` | Validate skill SKILL.md and tools |
