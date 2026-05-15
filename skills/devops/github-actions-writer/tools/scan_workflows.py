#!/usr/bin/env python3
"""Scan GitHub Actions workflow files and extract structural information.

Parses .github/workflows/*.yml and *.yaml files using a line-by-line
approach (no external YAML library required) and outputs JSON to stdout.
"""

import argparse
import glob
import json
import os
import re
import sys


def get_indent(line):
    """Return the number of leading spaces."""
    return len(line) - len(line.lstrip())


def strip_comment(line):
    """Remove inline comments (naive: doesn't handle # inside quotes)."""
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == '#' and not in_single and not in_double:
            return line[:i].rstrip()
    return line.rstrip()


def parse_yaml_value(raw):
    """Parse a simple scalar YAML value."""
    val = raw.strip()
    if val == '' or val == '~' or val == 'null':
        return None
    if val in ('true', 'True', 'yes', 'on'):
        return True
    if val in ('false', 'False', 'no', 'off'):
        return False
    # Strip quotes
    if (val.startswith('"') and val.endswith('"')) or \
       (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    # Try number
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val


def parse_workflow(filepath):
    """Parse a GitHub Actions workflow file and extract key fields."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        return None, str(e)

    result = {
        'filename': os.path.basename(filepath),
        'name': None,
        'triggers': {},
        'jobs': [],
        'reusable_workflow_calls': [],
        'concurrency': None,
        'permissions': None,
        'env': None,
    }

    # We'll do a two-pass approach:
    # 1. Identify top-level keys and their line ranges
    # 2. Parse each section

    # Find top-level keys (indent 0)
    top_sections = []  # (key, value_on_same_line, start_line, end_line)
    for i, raw_line in enumerate(lines):
        line = raw_line.rstrip('\n\r')
        if not line.strip() or line.strip().startswith('#'):
            continue
        if get_indent(line) == 0 and ':' in line:
            key_part = line.split(':', 1)
            key = key_part[0].strip()
            val = strip_comment(key_part[1]).strip() if len(key_part) > 1 else ''
            top_sections.append((key, val, i))

    # Assign end lines
    for idx in range(len(top_sections)):
        start = top_sections[idx][2]
        end = top_sections[idx + 1][2] if idx + 1 < len(top_sections) else len(lines)
        top_sections[idx] = (top_sections[idx][0], top_sections[idx][1], start, end)

    for key, inline_val, start, end in top_sections:
        section_lines = lines[start + 1:end]

        if key == 'name':
            result['name'] = parse_yaml_value(inline_val) if inline_val else None
            if result['name'] is None and section_lines:
                result['name'] = parse_yaml_value(section_lines[0].strip())

        elif key == 'on' or key == 'true':
            # YAML parses `on:` as True key sometimes, but we read raw
            result['triggers'] = _parse_triggers(inline_val, section_lines)

        elif key == 'jobs':
            result['jobs'] = _parse_jobs(section_lines)

        elif key == 'concurrency':
            result['concurrency'] = _parse_inline_or_block(inline_val, section_lines)

        elif key == 'permissions':
            result['permissions'] = _parse_inline_or_block(inline_val, section_lines)

        elif key == 'env':
            result['env'] = _parse_map_block(section_lines)

    # Extract reusable workflow calls from jobs
    for job in result['jobs']:
        for action in job.get('actions_used', []):
            if '/.github/workflows/' in action:
                result['reusable_workflow_calls'].append(action)

    return result, None


def _parse_inline_or_block(inline_val, section_lines):
    """Parse a value that may be inline or a block mapping."""
    if inline_val:
        return parse_yaml_value(inline_val)
    # Collect as a simple dict or string
    mapping = _parse_map_block(section_lines)
    return mapping if mapping else None


def _parse_map_block(section_lines):
    """Parse a simple key: value mapping block (one level)."""
    result = {}
    if not section_lines:
        return result
    base_indent = None
    for raw in section_lines:
        line = raw.rstrip('\n\r')
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        indent = get_indent(line)
        if base_indent is None:
            base_indent = indent
        if indent < base_indent:
            break
        if indent == base_indent and ':' in stripped:
            k, v = stripped.split(':', 1)
            result[k.strip()] = parse_yaml_value(strip_comment(v))
    return result


def _parse_triggers(inline_val, section_lines):
    """Parse the on: block."""
    if inline_val:
        # Could be `on: push` or `on: [push, pull_request]`
        val = inline_val.strip()
        if val.startswith('[') and val.endswith(']'):
            events = [e.strip().strip("'\"") for e in val[1:-1].split(',')]
            return {e: {} for e in events if e}
        return {val: {}}

    triggers = {}
    if not section_lines:
        return triggers

    base_indent = None
    current_event = None
    current_config = {}

    for raw in section_lines:
        line = raw.rstrip('\n\r')
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        indent = get_indent(line)
        if base_indent is None:
            base_indent = indent
        if indent < base_indent:
            break

        if indent == base_indent:
            # Save previous
            if current_event:
                triggers[current_event] = current_config
            # List item like `- push`
            if stripped.startswith('- '):
                current_event = stripped[2:].strip().rstrip(':')
                current_config = {}
            elif ':' in stripped:
                current_event = stripped.split(':', 1)[0].strip()
                current_config = {}
            else:
                current_event = stripped
                current_config = {}
        elif current_event and indent > base_indent:
            # Sub-config for current event
            if ':' in stripped:
                k, v = stripped.split(':', 1)
                k = k.strip().lstrip('- ')
                v = strip_comment(v).strip()
                if v.startswith('[') and v.endswith(']'):
                    current_config[k] = [x.strip().strip("'\"") for x in v[1:-1].split(',') if x.strip()]
                elif v:
                    current_config.setdefault(k, [])
                    if isinstance(current_config[k], list):
                        current_config[k].append(v)
                    else:
                        current_config[k] = v
            elif stripped.startswith('- '):
                # List continuation for last key
                val = stripped[2:].strip().strip("'\"")
                # Find last key added
                if current_config:
                    last_key = list(current_config.keys())[-1]
                    if isinstance(current_config[last_key], list):
                        current_config[last_key].append(val)

    if current_event:
        triggers[current_event] = current_config

    return triggers


def _parse_jobs(section_lines):
    """Parse the jobs: block."""
    jobs = []
    if not section_lines:
        return jobs

    # Find job-level keys (first indentation level)
    base_indent = None
    job_ranges = []  # (job_id, start_idx, end_idx)

    for i, raw in enumerate(section_lines):
        line = raw.rstrip('\n\r')
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        indent = get_indent(line)
        if base_indent is None:
            base_indent = indent
        if indent == base_indent and ':' in stripped and not stripped.startswith('-'):
            job_id = stripped.split(':', 1)[0].strip()
            job_ranges.append((job_id, i))

    # Assign end indices
    for idx in range(len(job_ranges)):
        start = job_ranges[idx][1]
        end = job_ranges[idx + 1][1] if idx + 1 < len(job_ranges) else len(section_lines)
        job_ranges[idx] = (job_ranges[idx][0], start, end)

    for job_id, start, end in job_ranges:
        job_lines = section_lines[start + 1:end]
        job = _parse_single_job(job_id, job_lines)
        jobs.append(job)

    return jobs


def _parse_single_job(job_id, job_lines):
    """Parse a single job block."""
    job = {
        'job_id': job_id,
        'name': None,
        'runs_on': None,
        'environment': None,
        'needs': [],
        'steps_count': 0,
        'actions_used': [],
        'secrets_referenced': [],
        'env_vars': {},
        'concurrency': None,
        'permissions': None,
    }

    all_text = ''.join(job_lines)

    # Extract secrets referenced via ${{ secrets.* }}
    secrets = re.findall(r'\$\{\{\s*secrets\.([A-Za-z_][A-Za-z0-9_]*)\s*\}\}', all_text)
    job['secrets_referenced'] = sorted(set(secrets))

    # Parse line by line for structure
    base_indent = None
    for raw in job_lines:
        line = raw.rstrip('\n\r')
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        indent = get_indent(line)
        if base_indent is None:
            base_indent = indent
        if indent != base_indent:
            continue

        if ':' in stripped:
            k, v = stripped.split(':', 1)
            k = k.strip()
            v = strip_comment(v).strip()

            if k == 'name':
                job['name'] = parse_yaml_value(v) if v else None
            elif k == 'runs-on':
                if v.startswith('[') and v.endswith(']'):
                    job['runs_on'] = [x.strip().strip("'\"") for x in v[1:-1].split(',')]
                elif v:
                    job['runs_on'] = parse_yaml_value(v)
            elif k == 'environment':
                job['environment'] = parse_yaml_value(v) if v else None
            elif k == 'needs':
                if v.startswith('[') and v.endswith(']'):
                    job['needs'] = [x.strip().strip("'\"") for x in v[1:-1].split(',') if x.strip()]
                elif v:
                    job['needs'] = [parse_yaml_value(v)]
            elif k == 'concurrency':
                job['concurrency'] = parse_yaml_value(v) if v else None
            elif k == 'permissions':
                job['permissions'] = parse_yaml_value(v) if v else None

    # Count steps and extract uses
    steps_count = 0
    for raw in job_lines:
        stripped = raw.strip()
        if stripped.startswith('- uses:') or stripped.startswith('- name:') or stripped.startswith('- run:'):
            steps_count += 1
        if stripped.startswith('- uses:') or stripped.startswith('uses:'):
            val = stripped.split(':', 1)
            if len(val) > 1:
                action = val[1].strip().lstrip('- ').strip()
                if stripped.startswith('- uses:'):
                    action = stripped.split('uses:', 1)[1].strip()
                if action:
                    job['actions_used'].append(action)

    job['steps_count'] = steps_count
    job['actions_used'] = sorted(set(job['actions_used']))

    # Extract env vars at job level
    in_env = False
    env_indent = None
    for raw in job_lines:
        line = raw.rstrip('\n\r')
        stripped = line.strip()
        indent = get_indent(line)
        if not stripped or stripped.startswith('#'):
            continue
        if indent == base_indent and stripped.startswith('env:'):
            in_env = True
            env_indent = None
            continue
        if in_env:
            if env_indent is None:
                if indent > base_indent:
                    env_indent = indent
                else:
                    in_env = False
                    continue
            if indent < env_indent:
                in_env = False
                continue
            if indent == env_indent and ':' in stripped:
                k, v = stripped.split(':', 1)
                job['env_vars'][k.strip()] = strip_comment(v).strip()

    # Parse needs if it's a list block
    if not job['needs']:
        in_needs = False
        needs_indent = None
        for raw in job_lines:
            line = raw.rstrip('\n\r')
            stripped = line.strip()
            indent = get_indent(line)
            if not stripped or stripped.startswith('#'):
                continue
            if indent == base_indent and stripped == 'needs:':
                in_needs = True
                needs_indent = None
                continue
            if in_needs:
                if needs_indent is None:
                    if indent > base_indent:
                        needs_indent = indent
                    else:
                        in_needs = False
                        continue
                if indent < needs_indent:
                    in_needs = False
                    continue
                if stripped.startswith('- '):
                    job['needs'].append(stripped[2:].strip().strip("'\""))

    return job


def scan_workflows(root_dir):
    """Scan the .github/workflows directory and return parsed workflows."""
    workflows_dir = os.path.join(root_dir, '.github', 'workflows')

    if not os.path.isdir(root_dir):
        return {
            'workflows': [],
            'root_dir': root_dir,
            'error': f'Directory does not exist: {root_dir}',
        }

    if not os.path.isdir(workflows_dir):
        return {
            'workflows': [],
            'root_dir': root_dir,
            'error': None,
        }

    files = sorted(
        glob.glob(os.path.join(workflows_dir, '*.yml')) +
        glob.glob(os.path.join(workflows_dir, '*.yaml'))
    )

    if not files:
        return {
            'workflows': [],
            'root_dir': root_dir,
            'error': None,
        }

    workflows = []
    for filepath in files:
        wf, err = parse_workflow(filepath)
        if err:
            workflows.append({
                'filename': os.path.basename(filepath),
                'error': err,
            })
        else:
            workflows.append(wf)

    return {
        'workflows': workflows,
        'root_dir': root_dir,
        'error': None,
    }


def main():
    parser = argparse.ArgumentParser(
        description='Scan GitHub Actions workflow files and output JSON.'
    )
    parser.add_argument(
        '--root-dir', required=True,
        help='Root directory of the repository to scan.'
    )
    args = parser.parse_args()

    result = scan_workflows(args.root_dir)
    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == '__main__':
    main()
