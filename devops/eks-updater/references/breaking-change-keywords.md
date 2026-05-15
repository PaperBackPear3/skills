# Breaking-change keywords

Case-insensitive substrings searched in GitHub release bodies returned by the
GitHub MCP server (see Phase 3.2 of SKILL.md). Any match flags the release as
`breaking: true`.

Keep entries lowercase, one per line, prefixed with `- `. Use plain phrases (no regex).

## Explicit breakage signals

- breaking change
- breaking
- backwards incompatible
- backward incompatible
- not backwards compatible
- incompatible
- action required
- migration required
- manual migration
- requires migration
- removed
- dropped support
- end of support
- end-of-life
- eol
- no longer supported

## Behavior changes that often break consumers

- deprecated
- renamed
- moved
- restructured
- signature change
- api change
- schema change
- default changed
- behavior change
- behaviour change

## Kubernetes / EKS specific

- requires kubernetes
- minimum kubernetes
- minimum k8s
- k8s version
- requires k8s
- crd change
- crd update
- helm 3
- helm v3
