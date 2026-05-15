#!/usr/bin/env python3
"""check_prereqs.py — verify required CLIs and AWS auth before running the eks-updater skill.

Exits non-zero on first failure with a clear message.

Usage:
    ./check_prereqs.py [aws-profile]
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys


REQUIRED_BINS = ["aws", "kubectl", "helm", "terraform"]


def ok(msg: str) -> None:
    print(f"  \033[32m✓\033[0m {msg}")


def warn(msg: str) -> None:
    print(f"  \033[31m✗\033[0m {msg}", file=sys.stderr)


def run(cmd: list[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return result.returncode, (result.stdout + result.stderr).strip()
    except FileNotFoundError:
        return 127, ""
    except subprocess.TimeoutExpired:
        return 124, ""


def main() -> None:
    profile = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("AWS_PROFILE", "")
    failures: list[str] = []

    print("Checking required CLIs...")
    for binary in REQUIRED_BINS:
        path = shutil.which(binary)
        if path:
            ok(f"{binary}: {path}")
        else:
            warn(f"{binary} not found in PATH — please install it.")
            failures.append(f"{binary} missing")

    print("\nChecking AWS authentication...")
    aws_cmd = ["aws", "sts", "get-caller-identity", "--output", "json"]
    if profile:
        aws_cmd += ["--profile", profile]

    rc, out = run(aws_cmd)
    if rc != 0:
        hint = f"aws sso login --profile {profile}" if profile else "aws sso login --profile <name>"
        warn(f"AWS not authenticated{' (' + profile + ')' if profile else ''}. Try: {hint}")
        failures.append("AWS auth")
    else:
        ok(f"AWS authenticated{' as profile ' + profile if profile else ''}")
        print(out)

    print("\nChecking kubectl context...")
    rc, ctx = run(["kubectl", "config", "current-context"])
    if rc != 0 or not ctx:
        warn("No active kubectl context. Run: aws eks update-kubeconfig --name <cluster> --region <region>")
        failures.append("kubectl context")
    else:
        ok(f"kubectl context: {ctx}")

    if failures:
        print(f"\n\033[31m{len(failures)} prerequisite(s) failed: {', '.join(failures)}\033[0m", file=sys.stderr)
        sys.exit(1)

    print("\nAll prerequisites satisfied.")


if __name__ == "__main__":
    main()
