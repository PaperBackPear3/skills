# CI/CD Migration Mappings → GitHub Actions

Reference for mapping CI/CD platform concepts to GitHub Actions equivalents.

## Jenkins → GitHub Actions

| Jenkins Concept | GitHub Actions Equivalent | Notes |
|----------------|--------------------------|-------|
| `pipeline { }` | Workflow YAML file | One Jenkinsfile → one or more workflow files |
| `agent` / `node` | `runs-on:` | `agent any` → `runs-on: ubuntu-latest` |
| `stage` | `jobs.<id>` | Each stage becomes a job (or step group) |
| `steps { }` | `steps:` | Direct mapping |
| `sh` / `bat` | `run:` | Shell commands |
| `environment { }` | `env:` block or `${{ vars.* }}` | |
| `credentials()` | `${{ secrets.* }}` | Configure in repo Settings |
| `when { branch }` | `on.push.branches` or `if:` condition | |
| `parallel` | Jobs without `needs:` (run in parallel by default) | |
| `post { always }` | `if: always()` on step or job | |
| `post { failure }` | `if: failure()` | |
| `input` (approval) | Environment protection rules (required reviewers) | |
| `stash`/`unstash` | `actions/upload-artifact` / `actions/download-artifact` | |
| `Shared Libraries` | Reusable workflows + composite actions | |
| `parameters` | `workflow_dispatch.inputs` | |
| `cron` trigger | `on.schedule.cron` | |
| `Dockerfile` agent | `container:` on job | |
| `tools { maven }` | `actions/setup-java` + mvn in `run:` | |

## GitLab CI → GitHub Actions

| GitLab CI Concept | GitHub Actions Equivalent | Notes |
|------------------|--------------------------|-------|
| `.gitlab-ci.yml` | `.github/workflows/*.yml` | Can split into multiple workflow files |
| `stages:` | Job `needs:` graph | GHA jobs are parallel by default; use `needs:` for ordering |
| `image:` | `runs-on:` + `container:` | Or use setup actions |
| `script:` | `run:` in steps | |
| `before_script` | Early steps in job | No direct equivalent; just add steps |
| `after_script` | Steps with `if: always()` | |
| `variables:` | `env:` block or `${{ vars.* }}` | |
| `secrets` | `${{ secrets.* }}` | |
| `artifacts: paths:` | `actions/upload-artifact` | |
| `cache: key:` | `actions/cache` with `hashFiles()` key | |
| `rules: - if:` | `if:` condition on job or `on:` trigger filters | |
| `environment:` | `environment:` on job | Direct equivalent |
| `when: manual` | `workflow_dispatch` or environment approval | |
| `extends:` / `include:` | Reusable workflows (`workflow_call`) | |
| `services:` | `services:` on job | Direct equivalent |
| `parallel: matrix:` | `strategy.matrix` | Direct equivalent |
| `trigger:` (child pipeline) | Reusable workflow or `workflow_dispatch` via API | |
| `needs:` | `needs:` | Direct equivalent |
| `only/except` (deprecated) | `on:` trigger configuration | |

## CircleCI → GitHub Actions

| CircleCI Concept | GitHub Actions Equivalent | Notes |
|-----------------|--------------------------|-------|
| `config.yml` | `.github/workflows/*.yml` | |
| `executors:` | `runs-on:` or `container:` | |
| `jobs:` | `jobs:` | Direct mapping |
| `steps:` | `steps:` | Direct mapping |
| `run:` | `run:` | Direct mapping |
| `orbs:` | Third-party actions (`uses:`) | Similar concept: reusable packages |
| `workflows:` | Workflow file with job `needs:` | |
| `requires:` | `needs:` | |
| `filters: branches:` | `on.push.branches` | |
| `context:` | GitHub Environments + environment secrets | |
| `persist_to_workspace` / `attach_workspace` | `actions/upload-artifact` / `download-artifact` | |
| `save_cache` / `restore_cache` | `actions/cache` | |
| `approval` job type | Environment protection rules | |
| `matrix:` | `strategy.matrix` | |
| `when` (conditional) | `if:` on step or job | |
| `pipeline.parameters` | `workflow_dispatch.inputs` | |
| `setup: true` (dynamic config) | No direct equivalent | Use `workflow_dispatch` + API or conditional jobs |

## Azure Pipelines → GitHub Actions

| Azure Pipelines Concept | GitHub Actions Equivalent | Notes |
|------------------------|--------------------------|-------|
| `azure-pipelines.yml` | `.github/workflows/*.yml` | |
| `pool: vmImage:` | `runs-on:` | `ubuntu-latest` maps directly |
| `stages:` | Jobs with `needs:` | |
| `jobs:` | `jobs:` | Direct mapping |
| `steps:` | `steps:` | Direct mapping |
| `script:` | `run:` | |
| `task:` | `uses:` (action) | Find equivalent GHA action |
| `variables:` | `env:` or `${{ vars.* }}` | |
| `variable groups` | GitHub Environments + secrets/variables | |
| `parameters:` | `workflow_dispatch.inputs` | |
| `trigger:` / `pr:` | `on.push` / `on.pull_request` | |
| `schedules:` | `on.schedule` | |
| `resources: containers:` | `container:` / `services:` on job | |
| `template:` | Reusable workflows | |
| `deployment` job + `environment:` | Job with `environment:` | |
| `strategy: runOnce/canary/rolling` | Custom implementation needed | GHA has no built-in deployment strategies |
| `condition:` | `if:` | Syntax differs: `eq()` → `==` |
| `artifacts` | `actions/upload-artifact` / `download-artifact` | |
| `approvals & checks` | Environment protection rules | |
| `service connections` | OIDC or repository secrets | Prefer OIDC |

## Concepts with No Direct Equivalent

| Platform | Concept | Workaround |
|----------|---------|------------|
| Jenkins | Shared Libraries (Groovy) | Reusable workflows + composite actions (no scripting language) |
| GitLab | `include: remote:` | Must vendor or use actions (no remote YAML include) |
| CircleCI | `setup: true` (dynamic config) | Use conditional jobs or API-triggered workflows |
| Azure | Built-in deployment strategies (canary, rolling) | Implement manually or use cloud-native tools |
| All | Artifact promotion across pipelines | Use `workflow_dispatch` with artifact reference or container registry tags |
