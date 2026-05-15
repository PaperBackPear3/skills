# Multi-Environment Deployment Patterns

Reference for designing GitHub Actions deployment architectures across environments.

## GitHub Environments Configuration

- Environments are configured in repo Settings → Environments
- Each environment can have: required reviewers, wait timer, deployment branches, custom rules
- Secrets and variables can be scoped per environment (`secrets.<name>` resolves per env)
- Environment URLs show in the deployments tab

## Pattern 1: Sequential Promotion (Most Common)

```
dev (auto) → staging (auto) → production (manual approval)
```

- Use `needs:` to chain deploy jobs
- Each job references a different `environment:`
- Production job requires reviewer approval via environment protection rule
- Same reusable workflow called 3 times with different environment input

## Pattern 2: Reusable Deploy Workflow

- Create `.github/workflows/deploy.yml` with `workflow_call` trigger
- Inputs: `environment`, `aws-role-arn` (or equivalent), `version`
- Caller workflows pass environment-specific values
- Single source of truth for deployment logic

## Pattern 3: Matrix-Based Multi-Environment

- Use `strategy.matrix` with environment list
- Good for identical environments (e.g., multi-region)
- Less suitable when environments need different approval gates

## Pattern 4: Release-Based Production Deploy

```
push to main → deploy dev+staging (auto)
release published → deploy production (with approval)
```

- Separates CI (every push) from production CD (releases only)
- Use `on: release: types: [published]` for production trigger
- Tag-based versioning feeds into deployment

## Pattern 5: GitFlow with Environment Mapping

```
feature/* → no deploy
develop → dev (auto)
release/* → staging (auto)
main → production (approval)
```

- Use `on.push.branches` filters per workflow or conditional jobs

## OIDC Per Environment

- Configure different IAM roles per GitHub Environment
- AWS: `role-to-assume` differs per environment, audience is `sts.amazonaws.com`
- Azure: different `client-id` per environment, federated credential per env
- GCP: different `workload_identity_provider` per environment
- Store role ARNs/client IDs as environment-scoped secrets

## Environment Protection Rules

- **Required reviewers**: up to 6 people/teams; any one can approve
- **Wait timer**: 0-43200 minutes delay before deploy starts
- **Deployment branches**: restrict which branches can deploy to this env
- **Custom rules**: third-party deployment protection rules (e.g., change management)

## Rollback Patterns

- **Re-deploy previous version**: `workflow_dispatch` with version input, deploy that tag/SHA
- **Git revert + redeploy**: revert commit on main, triggers normal pipeline
- **Blue/green**: maintain two target groups, swap on deploy, swap back on rollback
- **Feature flags**: disable feature remotely without redeployment

## Concurrency Controls

- Use `concurrency: group: deploy-${{ inputs.environment }}` to prevent parallel deploys to same env
- `cancel-in-progress: false` for deployments (don't cancel mid-deploy)
- `cancel-in-progress: true` for CI/PR workflows (save resources)

## Secret Management

- Use environment-scoped secrets for credentials that differ per env
- Use repository secrets for shared values (e.g., Slack webhook)
- Use organization secrets for org-wide values
- Prefer OIDC over stored credentials wherever possible
- `vars.*` (GitHub Variables) for non-sensitive config (URLs, feature flags)
