# MCP Server Feasibility Investigation

## Executive Summary

**Recommendation: Yes — expose a subset of tools as an MCP server.**

The inventory and scanning tools (`inventory_addons`, `inventory_helm`, `scan_terraform_eks/aks`) are excellent MCP candidates: they are stateless, accept simple parameters, and return structured JSON. This would allow any MCP-compatible agent (not just the skill orchestrator) to query cluster state on demand — enabling ad-hoc drift checks, compliance audits, and integration with other workflows.

`check_prereqs` and `generate_report` are weaker candidates — the former is a side-effect-heavy validation step best left to orchestration, and the latter requires complex multi-field JSON input that the skill assembles across multiple phases.

## Tool-by-Tool Analysis

| Tool | MCP Fit (1-5) | Reasoning |
|------|:---:|-----------|
| `inventory_addons.py` (EKS) | **5** | Stateless, structured JSON output, clear params (cluster, region, profile). Perfect MCP tool. |
| `inventory_addons.py` (AKS) | **5** | Same qualities — params are (cluster, resource-group, subscription). |
| `inventory_helm.py` | **5** | Zero params, returns JSON array. Trivial to expose. Useful standalone for any Helm audit. |
| `scan_terraform_eks.py` | **4** | Stateless file-system scan with JSON output. Single param (root dir). Slight concern: agent must have filesystem access to the Terraform root. |
| `scan_terraform_aks.py` | **4** | Same as above. |
| `check_prereqs.py` | **2** | Primarily produces human-readable colored output with exit codes. More of a health-check than a data-retrieval tool. Could be adapted but low value as MCP tool since agents already handle prerequisite gating. |
| `generate_report.py` | **2** | Requires large, multi-phase JSON assembled by the orchestrating agent. Not useful standalone — consumers would need to replicate the full skill context. Better as an internal step. |

## Proposed MCP Server Design

### Tools (callable by any MCP client)

```
eks/inventory-addons
  params: cluster (string, required), region (string, required), profile (string, optional)
  returns: JSON object with kubernetes_version and addons array

aks/inventory-addons
  params: cluster (string, required), resource_group (string, required), subscription (string, optional)
  returns: JSON object with kubernetes_version, available_upgrades, addons, extensions

inventory-helm
  params: none (uses current kubectl context)
  returns: JSON array of Helm releases

eks/scan-terraform
  params: root_dir (string, required)
  returns: JSON with declared EKS resources, modules, versions

aks/scan-terraform
  params: root_dir (string, required)
  returns: JSON with declared AKS resources, modules, versions

check-prereqs
  params: provider (enum: aws|azure), profile_or_subscription (string, optional)
  returns: JSON object { "ok": bool, "checks": [...], "failures": [...] }
```

### Resources (read-only data the server exposes)

| URI Pattern | Description |
|---|---|
| `compatibility://eks/{k8s_version}` | EKS add-on compatibility matrix from `references/` |
| `compatibility://aks/{k8s_version}` | AKS add-on compatibility matrix from `references/` |
| `template://plan-report/{provider}` | HTML report template (plan) |
| `template://summary-report/{provider}` | HTML report template (summary) |

### Prompts (reusable prompt templates)

| Prompt Name | Description |
|---|---|
| `analyze-drift` | Given inventory + terraform scan results, produce a drift analysis with upgrade recommendations |
| `changelog-research` | Given a package name and version range, research breaking changes from GitHub releases |
| `upgrade-plan` | Given drift analysis, produce a prioritized step-by-step upgrade plan |

## Additional Agent Capabilities to Add

1. **Rollback advisor** — Given a failed upgrade (addon name, error message), suggest rollback steps and root-cause patterns from known issues.

2. **Cost impact estimator** — Before upgrading node groups, estimate cost delta from instance type changes or new node pool configurations.

3. **Compliance snapshot** — Periodically capture cluster state (versions, configs) as a resource, enabling time-series drift tracking without running the full skill.

4. **Multi-cluster federation** — Accept a list of clusters and produce a unified drift/version matrix across all of them, highlighting inconsistencies.

5. **Pre-flight simulation** — Dry-run Terraform plan for proposed version bumps and surface potential conflicts before the user commits.

6. **Notification integration** — After drift detection, optionally create GitHub Issues or Slack messages summarizing findings (as an MCP prompt/tool combo).

## Risks and Considerations

| Risk | Mitigation |
|---|---|
| **Credential exposure** — MCP tools invoke cloud CLIs using ambient credentials | Document that the MCP server must run in a trusted environment; never pass credentials as tool params |
| **Long execution times** — `inventory_addons` makes multiple sequential API calls | Implement timeouts and progress notifications via MCP streaming; consider caching |
| **Filesystem access** — Terraform scan tools need access to the repo checkout | Restrict `root_dir` param to an allowlist or require it be under the workspace root |
| **Versioning drift** — MCP server and skill tools could diverge | Single source of truth: MCP server imports the same Python modules used by the CLI tools |
| **Scope creep** — Exposing everything as MCP dilutes the curated skill experience | Keep `generate_report` and multi-phase orchestration inside the skill; MCP provides building blocks only |
| **Error handling** — CLI tools use exit codes + stderr; MCP needs structured errors | Wrap each tool in a try/except that returns `{"error": "...", "code": "..."}` on failure |
