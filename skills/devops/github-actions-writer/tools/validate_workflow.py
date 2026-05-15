#!/usr/bin/env python3
"""Validate a GitHub Actions workflow YAML file.

Performs structural and best-practice checks on a workflow file,
reporting each as pass/warn/fail. Uses only Python stdlib (no PyYAML).
Outputs JSON to stdout. Always exits 0.
"""

import argparse
import json
import re
import sys


def read_file(path):
    """Read file contents, return (lines, error)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return lines, None
    except FileNotFoundError:
        return None, "File not found"
    except PermissionError:
        return None, "Permission denied"
    except Exception as e:
        return None, str(e)


def get_indent(line):
    """Return number of leading spaces."""
    return len(line) - len(line.lstrip(" "))


def check_valid_yaml(lines):
    """Check basic YAML structural validity."""
    for i, line in enumerate(lines):
        if "\t" in line and line.strip() and not line.lstrip().startswith("#"):
            # Tabs mixed with content (YAML forbids tabs for indentation)
            stripped = line.lstrip("\t")
            if len(line) - len(stripped) > 0 and line[0] == "\t":
                return {"name": "valid_yaml", "status": "fail",
                        "message": f"Tab used for indentation", "line": i + 1}
        # Check for obviously broken structure (e.g., key with no colon at top level)
    return {"name": "valid_yaml", "status": "pass", "message": "File is parseable"}


def check_has_on_trigger(lines):
    """Check for on: top-level key."""
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if re.match(r'^on\s*:', line) or re.match(r'^"on"\s*:', line) or re.match(r"^'on'\s*:", line):
            return {"name": "has_on_trigger", "status": "pass",
                    "message": "Found on: trigger", "line": i + 1}
        if line == "on:\n" or line == "on:":
            return {"name": "has_on_trigger", "status": "pass",
                    "message": "Found on: trigger", "line": i + 1}
    return {"name": "has_on_trigger", "status": "fail",
            "message": "Missing on: trigger definition"}


def check_has_jobs(lines):
    """Check for jobs: top-level key."""
    for i, line in enumerate(lines):
        if re.match(r'^jobs\s*:', line):
            return {"name": "has_jobs", "status": "pass",
                    "message": "Found jobs: key", "line": i + 1}
    return {"name": "has_jobs", "status": "fail",
            "message": "Missing jobs: key"}


def find_jobs(lines):
    """Find job names and their line ranges. Returns list of (name, start, end)."""
    jobs_start = None
    for i, line in enumerate(lines):
        if re.match(r'^jobs\s*:', line):
            jobs_start = i
            break
    if jobs_start is None:
        return []

    jobs = []
    job_indent = None
    for i in range(jobs_start + 1, len(lines)):
        line = lines[i]
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = get_indent(line)
        # First non-empty line after jobs: determines job indent level
        if job_indent is None:
            job_indent = indent
        if indent == 0 and not line.strip().startswith("#"):
            break  # new top-level key
        if indent == job_indent and re.match(r'^\s+[\w-]+\s*:', line):
            name = line.strip().split(":")[0].strip()
            jobs.append((name, i))

    # Determine end of each job
    result = []
    for idx, (name, start) in enumerate(jobs):
        end = jobs[idx + 1][1] if idx + 1 < len(jobs) else len(lines)
        result.append((name, start, end))
    return result


def check_jobs_have_runs_on(lines):
    """Each job must have runs-on unless it uses a reusable workflow."""
    jobs = find_jobs(lines)
    if not jobs:
        return {"name": "jobs_have_runs_on", "status": "pass",
                "message": "No jobs to check"}
    for name, start, end in jobs:
        has_runs_on = False
        has_uses = False
        job_indent = get_indent(lines[start])
        for i in range(start + 1, end):
            line = lines[i]
            if not line.strip() or line.strip().startswith("#"):
                continue
            indent = get_indent(line)
            if indent <= job_indent and line.strip():
                break
            # Direct child of job
            if indent == job_indent + 2 or indent == job_indent + 4:
                if re.match(r'\s+runs-on\s*:', line):
                    has_runs_on = True
                if re.match(r'\s+uses\s*:', line):
                    has_uses = True
        if not has_runs_on and not has_uses:
            return {"name": "jobs_have_runs_on", "status": "fail",
                    "message": f"Job '{name}' missing runs-on", "line": start + 1}
    return {"name": "jobs_have_runs_on", "status": "pass",
            "message": "All jobs have runs-on or uses"}


def check_steps_have_action_or_run(lines):
    """Each step must have uses: or run:."""
    in_steps = False
    step_start = None
    step_indent = None
    has_action = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Detect steps: key
        if re.match(r'\s+steps\s*:', line):
            in_steps = True
            step_indent = None
            step_start = None
            has_action = False
            continue

        if in_steps:
            indent = get_indent(line)
            # Detect step item (starts with -)
            if re.match(r'\s+-\s+', line) or re.match(r'\s+-$', line):
                # Check previous step
                if step_start is not None and not has_action:
                    return {"name": "steps_have_action_or_run", "status": "fail",
                            "message": "Step missing uses: or run:", "line": step_start + 1}
                step_start = i
                step_indent = indent
                has_action = False
                # Check if this line itself has uses/run
                if re.search(r'\buses\s*:', stripped) or re.search(r'\brun\s*:', stripped):
                    has_action = True
            elif step_start is not None:
                if re.search(r'\buses\s*:', stripped) or re.search(r'\brun\s*:', stripped):
                    has_action = True
                # If we've left the steps block
                if indent <= get_indent(lines[step_start]) - 2 and not re.match(r'\s+-', line):
                    if not has_action:
                        return {"name": "steps_have_action_or_run", "status": "fail",
                                "message": "Step missing uses: or run:",
                                "line": step_start + 1}
                    in_steps = False
                    step_start = None

    if step_start is not None and not has_action:
        return {"name": "steps_have_action_or_run", "status": "fail",
                "message": "Step missing uses: or run:", "line": step_start + 1}

    return {"name": "steps_have_action_or_run", "status": "pass",
            "message": "All steps have uses: or run:"}


def check_no_deprecated_commands(lines):
    """No ::set-output or ::save-state in run: blocks."""
    in_run = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r'.*\brun\s*:\s*\|', line) or re.match(r'.*\brun\s*:', line):
            in_run = True
            # Check inline run value
            after_run = re.sub(r'.*\brun\s*:\s*', '', line)
            if "::set-output" in after_run or "::save-state" in after_run:
                return {"name": "no_deprecated_commands", "status": "fail",
                        "message": "Deprecated ::set-output or ::save-state command",
                        "line": i + 1}
            continue
        if in_run:
            if stripped and not stripped.startswith("#"):
                if "::set-output" in stripped or "::save-state" in stripped:
                    return {"name": "no_deprecated_commands", "status": "fail",
                            "message": "Deprecated ::set-output or ::save-state command",
                            "line": i + 1}
            # Detect end of run block (line with less/equal indent and a key)
            if stripped and not line.startswith(" " * 6) and re.match(r'\s+\w', line):
                if re.match(r'\s+[\w-]+\s*:', line) and not line.strip().startswith("#"):
                    in_run = False
    return {"name": "no_deprecated_commands", "status": "pass",
            "message": "No deprecated workflow commands found"}


def check_no_plaintext_secrets(lines):
    """No patterns like password:/token:/secret: with literal values."""
    secret_pattern = re.compile(
        r'(password|token|secret|api_key|apikey)\s*:\s*["\']?(?!\s*\$\{\{)'
        r'[A-Za-z0-9+/=_\-]{8,}',
        re.IGNORECASE
    )
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        # Skip lines referencing ${{ secrets.* }}
        if "${{ secrets." in line or "${{secrets." in line:
            continue
        if secret_pattern.search(line):
            return {"name": "no_plaintext_secrets", "status": "fail",
                    "message": "Possible plaintext secret detected", "line": i + 1}
    return {"name": "no_plaintext_secrets", "status": "pass",
            "message": "No plaintext secrets detected"}


def check_actions_pinned_to_sha(lines):
    """Third-party actions should use SHA pins."""
    uses_pattern = re.compile(r'\buses\s*:\s*([^\s#]+)')
    for i, line in enumerate(lines):
        m = uses_pattern.search(line)
        if not m:
            continue
        action = m.group(1).strip().strip("'\"")
        # Skip local actions and official actions/*
        if action.startswith("./") or action.startswith("actions/"):
            continue
        # Skip docker:// references
        if action.startswith("docker://"):
            continue
        # Check if pinned to SHA (40 hex chars or sha256:)
        if "@" in action:
            ref = action.split("@", 1)[1]
            if re.match(r'^[0-9a-f]{40}$', ref) or ref.startswith("sha256:"):
                continue
            return {"name": "actions_pinned_to_sha", "status": "warn",
                    "message": f"Action '{action}' not pinned to SHA", "line": i + 1}
        else:
            return {"name": "actions_pinned_to_sha", "status": "warn",
                    "message": f"Action '{action}' missing version pin", "line": i + 1}
    return {"name": "actions_pinned_to_sha", "status": "pass",
            "message": "All third-party actions pinned to SHA"}


def check_has_permissions(lines):
    """Check for permissions: block at top-level or in jobs."""
    for i, line in enumerate(lines):
        if re.match(r'^permissions\s*:', line):
            return {"name": "has_permissions", "status": "pass",
                    "message": "Top-level permissions found", "line": i + 1}
    # Check per-job permissions
    jobs = find_jobs(lines)
    for name, start, end in jobs:
        for i in range(start + 1, end):
            stripped = lines[i].strip()
            if re.match(r'permissions\s*:', stripped):
                return {"name": "has_permissions", "status": "pass",
                        "message": f"Job '{name}' has permissions", "line": i + 1}
    return {"name": "has_permissions", "status": "warn",
            "message": "No permissions: block found (least privilege recommended)"}


def check_valid_expressions(lines):
    """Check that ${{ }} expressions are properly closed."""
    for i, line in enumerate(lines):
        # Count ${{ and }} occurrences
        opens = [m.start() for m in re.finditer(r'\$\{\{', line)]
        for pos in opens:
            rest = line[pos + 3:]
            if '}}' not in rest:
                return {"name": "valid_expressions", "status": "fail",
                        "message": "Unclosed ${{ expression", "line": i + 1}
    return {"name": "valid_expressions", "status": "pass",
            "message": "All expressions properly closed"}


def check_no_pull_request_target_checkout(lines):
    """Warn if pull_request_target trigger with PR head checkout."""
    has_prt = False
    for line in lines:
        if "pull_request_target" in line and not line.strip().startswith("#"):
            has_prt = True
            break
    if not has_prt:
        return {"name": "no_pull_request_target_checkout", "status": "pass",
                "message": "No pull_request_target trigger"}
    # Look for checkout with PR head ref
    checkout_pattern = re.compile(
        r'github\.event\.pull_request\.head\.(sha|ref)'
    )
    for i, line in enumerate(lines):
        if checkout_pattern.search(line):
            return {"name": "no_pull_request_target_checkout", "status": "warn",
                    "message": "pull_request_target with PR head checkout is dangerous",
                    "line": i + 1}
    return {"name": "no_pull_request_target_checkout", "status": "pass",
            "message": "No dangerous pull_request_target checkout pattern"}


def check_has_timeout(lines):
    """Warn if jobs lack timeout-minutes."""
    jobs = find_jobs(lines)
    if not jobs:
        return {"name": "has_timeout", "status": "pass",
                "message": "No jobs to check"}
    for name, start, end in jobs:
        has_timeout = False
        for i in range(start + 1, end):
            if re.search(r'\btimeout-minutes\s*:', lines[i]):
                has_timeout = True
                break
        if not has_timeout:
            return {"name": "has_timeout", "status": "warn",
                    "message": f"Job '{name}' missing timeout-minutes",
                    "line": start + 1}
    return {"name": "has_timeout", "status": "pass",
            "message": "All jobs have timeout-minutes"}


def validate(path):
    """Run all checks on the given file."""
    lines, error = read_file(path)
    if error:
        return {
            "file": path,
            "valid": False,
            "checks": [{"name": "file_read", "status": "fail", "message": error}],
            "summary": {"pass": 0, "warn": 0, "fail": 1}
        }

    checks = [
        check_valid_yaml(lines),
        check_has_on_trigger(lines),
        check_has_jobs(lines),
        check_jobs_have_runs_on(lines),
        check_steps_have_action_or_run(lines),
        check_no_deprecated_commands(lines),
        check_no_plaintext_secrets(lines),
        check_actions_pinned_to_sha(lines),
        check_has_permissions(lines),
        check_valid_expressions(lines),
        check_no_pull_request_target_checkout(lines),
        check_has_timeout(lines),
    ]

    summary = {"pass": 0, "warn": 0, "fail": 0}
    for c in checks:
        summary[c["status"]] += 1

    return {
        "file": path,
        "valid": summary["fail"] == 0,
        "checks": checks,
        "summary": summary
    }


def main():
    parser = argparse.ArgumentParser(
        description="Validate a GitHub Actions workflow YAML file."
    )
    parser.add_argument("--file", required=True, help="Path to workflow YAML file")
    args = parser.parse_args()

    result = validate(args.file)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
