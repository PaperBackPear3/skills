# Installation Guide

## Prerequisites

- **Python 3.10+** (for MCP server)
- **An AI coding agent** — Claude Code, Codex, Cursor, Kiro, or any MCP-compatible agent
- **Cloud CLIs** (only for skills that need them): `aws`, `az`, `kubectl`, `helm`, `terraform`

---

## Option 1: Plugin Install (Recommended)

One command gives your agent skills + MCP server — no manual config needed.

### Claude Code

```bash
/plugin marketplace add PaperBackPear3/skills
/plugin install devops-core@skills
```

### Codex

```bash
codex plugin marketplace add PaperBackPear3/skills
# Then run /plugins in Codex to install devops-core
```

### Kiro

Add to `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "skills-mcp": {
      "command": "python3",
      "args": ["/path/to/skills/mcp-server/server.py"]
    }
  }
}
```

Then copy skills:
```bash
cp -r skills/<category>/* ~/.kiro/skills/
```

---

## Option 2: MCP Server Only

Run the MCP server for tool access + runtime skill discovery. Your agent finds and loads skills dynamically — no local skill installation needed.

### 1. Clone the repo

```bash
git clone https://github.com/PaperBackPear3/skills.git ~/skills
```

### 2. Install dependencies

```bash
cd ~/skills/mcp-server
pip install -r requirements.txt
```

### 3. Configure your agent

Add to your agent's MCP config:

**VS Code (GitHub Copilot)** — `.vscode/mcp.json`:
```json
{
  "servers": {
    "skills-mcp": {
      "command": "python3",
      "args": ["/Users/you/skills/mcp-server/server.py"]
    }
  }
}
```

**Claude Code** — `~/.claude/settings.json` or project `.mcp.json`:
```json
{
  "mcpServers": {
    "skills-mcp": {
      "command": "python3",
      "args": ["/Users/you/skills/mcp-server/server.py"]
    }
  }
}
```

**Claude Desktop** — `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "skills-mcp": {
      "command": "python3",
      "args": ["/Users/you/skills/mcp-server/server.py"]
    }
  }
}
```

### 4. Verify

Ask your agent: *"List available skills"* — it should call `list_skills()` and show your installed skills.

---

## Option 3: Manual Skill Copy

Copy individual skills into your agent's skill directory. No MCP server needed, but no runtime discovery.

```bash
git clone https://github.com/PaperBackPear3/skills.git ~/skills
```

| Agent | Skills directory |
|-------|-----------------|
| Claude Code | `~/.claude/skills/` or `.claude/skills/` (project) |
| Codex | `~/.codex/skills/` or `.agents/skills/` (project) |
| GitHub Copilot | `~/.agents/skills/` |
| Cursor | `~/.cursor/skills/` or `.cursor/skills/` (project) |
| Kiro | `~/.kiro/skills/` or `.kiro/skills/` (project) |

```bash
# Example: install EKS updater for Claude Code
mkdir -p ~/.claude/skills
cp -r ~/skills/skills/devops/aws-eks-updater ~/.claude/skills/
```

---

## Option 4: Symlinks (for development)

If you want to edit skills and have changes reflected immediately:

```bash
mkdir -p ~/.claude/skills
ln -s ~/skills/skills/devops/aws-eks-updater ~/.claude/skills/aws-eks-updater
ln -s ~/skills/skills/devops/azure-aks-updater ~/.claude/skills/azure-aks-updater
```

---

## Verifying Installation

After any method, test by asking your agent:

- *"List available skills"* → (MCP) should call `list_skills()` and show installed skills
- *"Help me with [task matching a skill description]"* → should trigger the relevant skill
- *"What skills do you have?"* → should enumerate available skills

---

## Uninstalling

| Method | Uninstall |
|--------|-----------|
| Plugin | `/plugin uninstall devops-core@skills` |
| MCP | Remove the server entry from your MCP config |
| Manual copy | Delete the skill directory |
| Symlink | Remove the symlink |
