#!/usr/bin/env python3
"""Scan a repository root for CI/CD configuration files from various systems.

Detects Jenkins, GitLab CI, CircleCI, Azure Pipelines, Travis CI,
Bitbucket Pipelines, and existing GitHub Actions configs. Extracts
stages, triggers, environments, secrets, services, artifacts, and
caching info via best-effort line-by-line parsing.

Outputs JSON to stdout suitable for migration planning to GitHub Actions.
"""

import argparse
import glob
import json
import os
import re
import sys


# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

def _find_configs(root):
    """Return list of (system, relative_path) tuples for detected CI configs."""
    found = []

    # Jenkins
    for name in os.listdir(root):
        if name == "Jenkinsfile" or (name.startswith("Jenkinsfile.") and os.path.isfile(os.path.join(root, name))):
            found.append(("jenkins", name))

    # GitLab CI
    if os.path.isfile(os.path.join(root, ".gitlab-ci.yml")):
        found.append(("gitlab_ci", ".gitlab-ci.yml"))

    # CircleCI
    circleci = os.path.join(root, ".circleci", "config.yml")
    if os.path.isfile(circleci):
        found.append(("circleci", ".circleci/config.yml"))

    # Azure Pipelines
    if os.path.isfile(os.path.join(root, "azure-pipelines.yml")):
        found.append(("azure_pipelines", "azure-pipelines.yml"))
    azure_dir = os.path.join(root, ".azure-pipelines")
    if os.path.isdir(azure_dir):
        for f in sorted(os.listdir(azure_dir)):
            if f.endswith(".yml"):
                found.append(("azure_pipelines", f".azure-pipelines/{f}"))

    # Travis CI
    if os.path.isfile(os.path.join(root, ".travis.yml")):
        found.append(("travis_ci", ".travis.yml"))

    # Bitbucket Pipelines
    if os.path.isfile(os.path.join(root, "bitbucket-pipelines.yml")):
        found.append(("bitbucket_pipelines", "bitbucket-pipelines.yml"))

    # GitHub Actions (existing)
    gha_dir = os.path.join(root, ".github", "workflows")
    if os.path.isdir(gha_dir):
        for f in sorted(os.listdir(gha_dir)):
            if f.endswith(".yml") or f.endswith(".yaml"):
                found.append(("github_actions", f".github/workflows/{f}"))

    return found


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

_STAGE_PATTERNS = [
    re.compile(r"^\s*stage\s*\(\s*['\"](.+?)['\"]\s*\)", re.IGNORECASE),
    re.compile(r"^\s*-?\s*stage:\s*(.+)", re.IGNORECASE),
    re.compile(r"^\s{2}(\w[\w-]*):\s*$"),  # top-level job keys (YAML)
]

_TRIGGER_KEYWORDS = {
    "push": re.compile(r"\b(push|on\s*push|branches)\b", re.IGNORECASE),
    "pull_request": re.compile(r"\b(pull_request|merge_request|PR)\b", re.IGNORECASE),
    "cron": re.compile(r"\b(cron|schedule|timer)\b", re.IGNORECASE),
    "manual": re.compile(r"\b(manual|workflow_dispatch|when:\s*manual)\b", re.IGNORECASE),
    "webhook": re.compile(r"\b(webhook|repository_dispatch)\b", re.IGNORECASE),
    "tag": re.compile(r"\b(tags?|release)\b", re.IGNORECASE),
}

_ENV_PATTERN = re.compile(
    r"\b(?:environment|deploy(?:ment)?(?:_target)?)\s*[:=]\s*['\"]?(\w[\w-]*)",
    re.IGNORECASE,
)

_SECRET_PATTERN = re.compile(
    r"(?:secrets?\.|credentials?\.|vault\(|secret\(|variable\()['\"]?(\w+)",
    re.IGNORECASE,
)

_SERVICE_PATTERN = re.compile(
    r"\b(?:services?|image|container)\s*:\s*['\"]?(\S+)",
    re.IGNORECASE,
)

_ARTIFACT_PATTERN = re.compile(
    r"\b(?:artifacts?|paths?|archive|upload|download)\s*:\s*['\"]?(\S+)",
    re.IGNORECASE,
)

_CACHE_PATTERN = re.compile(
    r"\b(?:cache|restore_cache|save_cache|caching)\b",
    re.IGNORECASE,
)


def _parse_config(root, rel_path):
    """Best-effort extraction from a CI config file."""
    full_path = os.path.join(root, rel_path)
    try:
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return None

    stages = []
    triggers = set()
    environments = []
    secrets = []
    services = []
    artifacts = []
    has_cache = False

    # For YAML-based configs, track top-level keys that look like jobs
    in_jobs_block = False
    jobs_indent = None

    for line in lines:
        stripped = line.rstrip()

        # Stages
        for pat in _STAGE_PATTERNS:
            m = pat.match(stripped)
            if m:
                val = m.group(1).strip().strip("'\"")
                if val and val not in stages and not val.startswith("#"):
                    stages.append(val)

        # Jobs block detection (GitLab/GHA style)
        if re.match(r"^(jobs|stages):\s*$", stripped):
            in_jobs_block = True
            jobs_indent = 2
            continue
        if in_jobs_block:
            m = re.match(r"^(\s{2})(\w[\w-]*):\s*$", stripped)
            if m and m.group(2) not in stages:
                stages.append(m.group(2))

        # Triggers
        for trigger_name, pat in _TRIGGER_KEYWORDS.items():
            if pat.search(stripped):
                triggers.add(trigger_name)

        # Environments
        m = _ENV_PATTERN.search(stripped)
        if m:
            val = m.group(1)
            if val not in environments:
                environments.append(val)

        # Secrets
        m = _SECRET_PATTERN.search(stripped)
        if m:
            val = m.group(1)
            if val not in secrets:
                secrets.append(val)

        # Services
        m = _SERVICE_PATTERN.search(stripped)
        if m:
            val = m.group(1).strip("'\"")
            if val and val not in services and "/" in val:
                services.append(val)

        # Artifacts
        m = _ARTIFACT_PATTERN.search(stripped)
        if m:
            val = m.group(1).strip("'\"")
            if val and val not in artifacts and ("*" in val or "." in val):
                artifacts.append(val)

        # Cache
        if _CACHE_PATTERN.search(stripped):
            has_cache = True

    line_count = len(lines)
    feature_count = sum([
        len(stages) > 3,
        len(triggers) > 2,
        len(environments) > 1,
        len(secrets) > 2,
        len(services) > 0,
        has_cache,
        line_count > 200,
    ])

    if line_count > 300 or feature_count >= 4:
        complexity = "complex"
    elif line_count > 80 or feature_count >= 2:
        complexity = "moderate"
    else:
        complexity = "simple"

    return {
        "stages": stages,
        "triggers": sorted(triggers),
        "environments": environments,
        "secrets": secrets,
        "services": services,
        "artifacts": artifacts,
        "caching": ["enabled"] if has_cache else [],
        "complexity": complexity,
        "line_count": line_count,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def scan(root_dir):
    """Scan root_dir and return result dict."""
    root = os.path.abspath(root_dir)

    if not os.path.isdir(root):
        return {
            "root_dir": root_dir,
            "configs_found": [],
            "summary": {
                "systems_found": [],
                "total_configs": 0,
                "migration_complexity": "unknown",
            },
            "error": f"Directory does not exist: {root_dir}",
        }

    detected = _find_configs(root)
    configs = []

    for system, rel_path in detected:
        parsed = _parse_config(root, rel_path)
        if parsed is None:
            continue
        entry = {"system": system, "file_path": rel_path}
        entry.update(parsed)
        configs.append(entry)

    systems_found = sorted(set(c["system"] for c in configs))

    # Overall migration complexity
    complexities = [c["complexity"] for c in configs]
    if "complex" in complexities:
        overall = "complex"
    elif "moderate" in complexities:
        overall = "moderate"
    elif complexities:
        overall = "simple"
    else:
        overall = "none"

    return {
        "root_dir": root_dir,
        "configs_found": configs,
        "summary": {
            "systems_found": systems_found,
            "total_configs": len(configs),
            "migration_complexity": overall,
        },
        "error": None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Detect and parse CI/CD configs for migration to GitHub Actions."
    )
    parser.add_argument(
        "--root-dir",
        required=True,
        help="Root directory of the repository to scan.",
    )
    args = parser.parse_args()

    result = scan(args.root_dir)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
