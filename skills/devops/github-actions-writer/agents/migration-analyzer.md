# Migration Analyzer Subagent

Use this prompt with the `general-purpose` agent type when the github-actions-writer skill needs
to analyze a large or complex CI configuration (≥ 5 stages/pipelines) from another system
(Jenkins, GitLab CI, CircleCI, Azure Pipelines) for migration to GitHub Actions.

## When to spawn

Spawn ONE instance with the full CI config context — not one agent per pipeline file. The agent
reads the configuration, uses the GitHub MCP server to inspect the target repository structure,
and produces a consolidated migration analysis.

## Prompt template

When invoking the agent, send a self-contained prompt like this:

    You are analyzing a CI/CD configuration for migration to GitHub Actions. Read the source
    configuration below and produce a migration mapping.

    Use the GitHub MCP server (mcp__github__* tools) to:
    - Inspect the target repository structure (languages, frameworks, existing workflows)
    - Check available GitHub Environments and their protection rules
    - Identify existing secrets (names only) that may need reconfiguration

    Migration reference mappings:
    <paste the contents of references/migration-mappings.md>

    Source CI system: <system>
    Source configuration:
    <paste the full CI config file contents>

    For each stage/job/pipeline in the source config, produce:
      - source stage name and purpose (one line)
      - recommended GitHub Actions equivalent (job in which workflow file)
      - trigger mapping (how the source trigger maps to GHA `on:` events)
      - any secrets/credentials that need to be configured
      - any features with no direct equivalent (flag for manual handling)
      - complexity: LOW / MEDIUM / HIGH

    Return:
    1. A markdown table mapping each source concept to its GHA equivalent
    2. A proposed workflow file structure (which workflows to create)
    3. An ordered migration plan (what to migrate first based on dependencies)
    4. A risk assessment noting any features that need manual intervention
    Keep the response under 800 words.

## What the subagent must NOT do

- Do not edit or create workflow files.
- Do not run git, kubectl, helm, terraform, or cloud provider commands.
- Do not make the final migration decision — that belongs to the skill + user.
- Do not fall back to curl or web scraping if the GitHub MCP is unavailable — report the
  failure and let the parent skill decide how to proceed.

## When NOT to spawn

If the source CI configuration has fewer than 5 stages/pipelines, analyze it inline from
the skill. The subagent's overhead (separate context window, model spin-up) only pays off
when the configuration is genuinely complex.
