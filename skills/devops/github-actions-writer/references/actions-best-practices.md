# GitHub Actions best practices

Reference for the AI agent during workflow generation. Each bullet is a single
actionable rule — scan by section to apply relevant practices.

## Security Hardening

- Pin third-party actions to full commit SHA (tags like `@v1` are mutable and can be hijacked)
- Use `permissions:` block at workflow and job level — principle of least privilege
- Never use `pull_request_target` with `actions/checkout` of PR head (code injection risk)
- Use OIDC for cloud authentication (AWS, Azure, GCP) — no long-lived credentials
- Store secrets in GitHub Secrets, never hardcode in workflow files
- Use `CODEOWNERS` for `.github/workflows/` to require review on workflow changes
- Limit `GITHUB_TOKEN` permissions to minimum needed per job
- Use `environment` protection rules for sensitive deployments
- Audit third-party actions before use — prefer official (`actions/*`) or verified creators

## Performance

- Cache dependencies (`actions/cache` or built-in caching in setup actions)
- Use matrix strategies for parallel testing across versions/platforms
- Set `timeout-minutes` on all jobs (default 360 min is too long)
- Use `concurrency` groups to cancel redundant runs (especially on PRs)
- Minimize checkout depth: `fetch-depth: 0` only when needed (tags, history)
- Use larger runners for heavy workloads when cost-effective
- Split long workflows into smaller reusable workflows for faster feedback

## DRY Patterns

- Extract shared logic into reusable workflows (`workflow_call` trigger)
- Use composite actions for shared step sequences (`.github/actions/<name>/action.yml`)
- Parameterize with inputs — avoid duplicating workflows per environment
- Use `workflow_dispatch` inputs for manual triggers with parameters
- Use caller/callee pattern: one deploy workflow called per environment

## Reliability

- Always set `timeout-minutes` per job
- Use `continue-on-error` only when intentional (mark clearly)
- Use `if: always()` for cleanup steps, `if: failure()` for notification
- Retry flaky steps with community actions or shell loops (with backoff)
- Use `concurrency` with `cancel-in-progress: true` for PR workflows
- Use `needs:` to express job dependencies explicitly

## Deployment Patterns

- Use GitHub Environments with protection rules (required reviewers, wait timers)
- Deploy to lower environments automatically, gate production with approvals
- Use OIDC with different IAM roles per environment
- Implement rollback as a `workflow_dispatch` with version input
- Use deployment status checks and health verification after deploy
- Tag releases and trigger production deploy on release publish

## Expression & Syntax

- Use `${{ github.event_name }}` not hardcoded event checks
- Prefer `${{ vars.* }}` for non-sensitive configuration (GitHub Variables)
- Use `toJSON()`, `fromJSON()` for complex data passing between jobs
- Use `hashFiles()` for cache keys
- Outputs between steps: `$GITHUB_OUTPUT` (not deprecated `::set-output`)
- Outputs between jobs: `jobs.<id>.outputs.<name>`
