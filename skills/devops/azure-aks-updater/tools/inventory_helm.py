#!/usr/bin/env python3
"""inventory_helm.py — JSON list of Helm releases across all namespaces.

Emits a trimmed-down array of releases with only the fields the skill cares about.

Usage:
    ./inventory_helm.py
"""
from __future__ import annotations

import json
import subprocess
import sys


FIELDS = ("name", "namespace", "chart", "app_version", "status", "updated", "revision")


def main() -> None:
    try:
        raw = subprocess.check_output(
            ["helm", "list", "--all-namespaces", "-o", "json"], text=True
        )
    except subprocess.CalledProcessError as exc:
        print(f"helm list failed: {exc}", file=sys.stderr)
        sys.exit(1)

    releases = json.loads(raw) if raw.strip() else []
    trimmed = [{k: r.get(k) for k in FIELDS} for r in releases]
    print(json.dumps(trimmed, indent=2))


if __name__ == "__main__":
    main()
