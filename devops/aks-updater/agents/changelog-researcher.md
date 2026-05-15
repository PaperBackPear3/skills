# Changelog Researcher Subagent

Use this prompt with the `general-purpose` agent type when the aks-updater skill needs to fetch
changelogs for many packages (≥ 8) and benefits from running them in parallel without flooding
the main conversation with raw API output.

## When to spawn

Spawn ONE instance with the full package list — not one agent per package. The agent fans out
internally with parallel tool calls to the GitHub MCP server.

## Prompt template

When invoking the agent, send a self-contained prompt like this:

```
You are researching upgrade changelogs for an AKS cluster update. For each package below,
use the GitHub MCP server (mcp__github__* tools — list_releases / get_release_by_tag or
equivalent) to fetch every release between "from" (exclusive) and "to" (inclusive). Run
the MCP calls in parallel where possible.

Breaking-change keywords (case-insensitive substrings to search in release bodies):
<paste the contents of references/breaking-change-keywords.md>

Packages:
  1. <name>  repo=<owner/repo>  from=<v>  to=<v>
  2. ...

For each package, capture:
  - whether ANY release between from..to contained one or more keywords (= "breaking: true")
  - the union of matched keywords across all releases in the range
  - the highest version in the range with NO matched keywords (the safe target)
  - the URL of any release flagged as breaking

Return a single markdown table plus a 3–6 line prose summary identifying which packages
need manual review and which are safe to auto-plan. Keep the response under 500 words.
Do NOT recommend a final upgrade plan — only report findings.
```

## What the subagent must NOT do

- Do not edit files.
- Do not run kubectl/helm/terraform/az commands.
- Do not propose a final upgrade plan — that decision belongs to the skill + user.
- Do not fall back to curl or web scraping if the GitHub MCP is unavailable — report the
  failure and let the parent skill decide how to proceed.

## When NOT to spawn

If fewer than 8 packages need changelog lookup, just call the GitHub MCP tools inline from
the skill. The subagent's overhead (separate context window, model spin-up) only pays off
when parallelism is genuinely useful.
