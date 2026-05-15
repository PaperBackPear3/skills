#!/usr/bin/env python3
"""Generate self-contained HTML reports for eks-updater.

Two report types:

  plan     — produced after Phase 4. Drift, per-package decisions, prioritized
             update plan, and blocked items. Read before the user authorizes
             execution; can be attached to a change-management ticket.

  summary  — produced after Phase 6. Final results table with status counts
             and deferred majors.

Usage:
  python3 tools/generate_report.py plan    <output.html>   < input.json
  python3 tools/generate_report.py summary <output.html>   < input.json

Reads JSON from stdin. See module docstring at the bottom for the expected
input schemas.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"


def esc(value) -> str:
    if value is None:
        return ""
    return html.escape(str(value))


def code(value) -> str:
    if value is None or value == "":
        return '<span class="empty">—</span>'
    return f"<code>{esc(value)}</code>"


def status_pill(decision: str) -> str:
    d = (decision or "").lower()
    if d in ("auto-plan", "auto", "ok", "in-sync"):
        return f'<span class="status status-ok">{esc(decision)}</span>'
    if d in ("manual-review", "review", "declared-ahead", "installed-ahead"):
        return f'<span class="status status-review">{esc(decision)}</span>'
    if d in ("blocked",):
        return f'<span class="status status-blocked">{esc(decision)}</span>'
    return f'<span class="status status-info">{esc(decision)}</span>'


def result_pill(status: str) -> str:
    s = (status or "").lower()
    cls = {
        "updated": "status-updated",
        "skipped": "status-skipped",
        "deferred": "status-deferred",
        "blocked": "status-blocked",
    }.get(s, "status-skipped")
    return f'<span class="status {cls}">{esc(status)}</span>'


def render_drift(rows) -> str:
    if not rows:
        return '<p class="empty">No drift detected — declared and installed versions match.</p>'
    body = "\n".join(
        f"<tr><td>{code(r.get('package'))}</td>"
        f"<td>{code(r.get('declared'))}</td>"
        f"<td>{code(r.get('installed'))}</td>"
        f"<td>{status_pill(r.get('status', ''))}</td></tr>"
        for r in rows
    )
    return (
        "<table><thead><tr>"
        "<th>Package</th><th>Declared</th><th>Installed</th><th>Status</th>"
        f"</tr></thead><tbody>{body}</tbody></table>"
    )


def render_decisions(rows) -> str:
    if not rows:
        return '<p class="empty">No decisions recorded.</p>'
    body = "\n".join(
        f"<tr><td>{code(r.get('package'))}</td>"
        f"<td>{esc(r.get('source'))}</td>"
        f"<td>{code(r.get('current'))}</td>"
        f"<td>{code(r.get('recommended'))}</td>"
        f"<td>{code(r.get('latest_stable'))}</td>"
        f"<td>{esc(r.get('breaking'))}</td>"
        f"<td>{esc(r.get('k8s_compatible'))}</td>"
        f"<td>{status_pill(r.get('decision', ''))}</td>"
        f"<td>{esc(r.get('reason'))}</td></tr>"
        for r in rows
    )
    return (
        "<table><thead><tr>"
        "<th>Package</th><th>Source</th><th>Current</th><th>Recommended</th>"
        "<th>Latest stable</th><th>Breaking?</th><th>K8s OK?</th>"
        "<th>Decision</th><th>Reason</th>"
        f"</tr></thead><tbody>{body}</tbody></table>"
    )


def render_plan(steps) -> str:
    if not steps:
        return '<p class="empty">No actionable steps in this plan.</p>'
    parts = []
    for i, s in enumerate(steps, 1):
        order = s.get("step", i)
        pkg = esc(s.get("package", ""))
        frm = esc(s.get("from", ""))
        to = esc(s.get("to", ""))
        file_path = esc(s.get("file", ""))
        rationale = esc(s.get("rationale", ""))
        parts.append(
            f'<div class="plan-step">'
            f'<div class="plan-step-header">{order}. {pkg} — <code>{frm}</code> → <code>{to}</code></div>'
            f'<div class="plan-step-meta">File: <code>{file_path}</code></div>'
            f'<div class="plan-step-meta">{rationale}</div>'
            f"</div>"
        )
    return "\n".join(parts)


def render_blocked(rows) -> str:
    if not rows:
        return '<p class="empty">No blocked packages.</p>'
    body = "\n".join(
        f"<tr><td>{code(r.get('package'))}</td><td>{esc(r.get('reason'))}</td></tr>"
        for r in rows
    )
    return (
        "<table><thead><tr><th>Package</th><th>Reason</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def render_results(rows) -> str:
    if not rows:
        return '<p class="empty">No results.</p>'
    body = "\n".join(
        f"<tr><td>{code(r.get('package'))}</td>"
        f"<td>{esc(r.get('source'))}</td>"
        f"<td>{code(r.get('old'))}</td>"
        f"<td>{code(r.get('new'))}</td>"
        f"<td>{result_pill(r.get('status', ''))}</td>"
        f"<td>{esc(r.get('notes', ''))}</td></tr>"
        for r in rows
    )
    return (
        "<table><thead><tr>"
        "<th>Package</th><th>Source</th><th>Old</th><th>New</th>"
        "<th>Status</th><th>Notes</th>"
        f"</tr></thead><tbody>{body}</tbody></table>"
    )


def render_deferred(rows) -> str:
    if not rows:
        return '<p class="empty">No deferred major upgrades.</p>'
    body = "\n".join(
        f"<tr><td>{code(r.get('package'))}</td>"
        f"<td>{code(r.get('from'))}</td>"
        f"<td>{code(r.get('to'))}</td>"
        f"<td>{esc(r.get('investigation_needed', ''))}</td></tr>"
        for r in rows
    )
    return (
        "<table><thead><tr>"
        "<th>Package</th><th>From</th><th>To</th><th>Investigation needed</th>"
        f"</tr></thead><tbody>{body}</tbody></table>"
    )


def fill(template: str, mapping: dict) -> str:
    for key, value in mapping.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def build_plan(data: dict) -> str:
    template = (ASSETS / "plan_template.html").read_text()
    cluster = data.get("cluster", {})
    generated = data.get("generated_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return fill(template, {
        "CLUSTER_NAME": esc(cluster.get("name", "unknown")),
        "REGION": esc(cluster.get("region", "—")),
        "PROFILE": esc(cluster.get("profile", "—")),
        "K8S_VERSION": esc(cluster.get("k8s_version", "—")),
        "GENERATED_AT": esc(generated),
        "DRIFT_TABLE": render_drift(data.get("drift", [])),
        "DECISIONS_TABLE": render_decisions(data.get("decisions", [])),
        "PLAN_STEPS": render_plan(data.get("plan", [])),
        "BLOCKED_TABLE": render_blocked(data.get("blocked", [])),
    })


def build_summary(data: dict) -> str:
    template = (ASSETS / "summary_template.html").read_text()
    cluster = data.get("cluster", {})
    results = data.get("results", [])
    generated = data.get("generated_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    counts = {"updated": 0, "skipped": 0, "deferred": 0, "blocked": 0}
    for r in results:
        s = (r.get("status") or "").lower()
        if s in counts:
            counts[s] += 1
    return fill(template, {
        "CLUSTER_NAME": esc(cluster.get("name", "unknown")),
        "REGION": esc(cluster.get("region", "—")),
        "PROFILE": esc(cluster.get("profile", "—")),
        "K8S_VERSION": esc(cluster.get("k8s_version", "—")),
        "GENERATED_AT": esc(generated),
        "COUNT_UPDATED": str(counts["updated"]),
        "COUNT_SKIPPED": str(counts["skipped"]),
        "COUNT_DEFERRED": str(counts["deferred"]),
        "COUNT_BLOCKED": str(counts["blocked"]),
        "RESULTS_TABLE": render_results(results),
        "DEFERRED_TABLE": render_deferred(data.get("deferred_majors", [])),
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("kind", choices=["plan", "summary"], help="Which report to generate.")
    parser.add_argument("output", help="Output HTML file path (written to CWD by convention).")
    args = parser.parse_args()

    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"error: invalid JSON on stdin: {e}", file=sys.stderr)
        return 2

    html_out = build_plan(data) if args.kind == "plan" else build_summary(data)
    Path(args.output).write_text(html_out)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------
# plan:
# {
#   "cluster":      {"name": str, "region": str, "profile": str, "k8s_version": str},
#   "generated_at": str (optional ISO/human),
#   "drift":        [{"package", "declared", "installed", "status"}],
#       # status ∈ {"in-sync", "declared-ahead", "installed-ahead"}
#   "decisions":    [{"package", "source", "current", "recommended",
#                     "latest_stable", "breaking", "k8s_compatible",
#                     "decision", "reason"}],
#       # source ∈ {"terraform", "addon", "helm"}
#       # decision ∈ {"auto-plan", "manual-review", "blocked"}
#   "plan":         [{"step", "package", "file", "from", "to", "rationale"}],
#   "blocked":      [{"package", "reason"}]
# }
#
# summary:
# {
#   "cluster":          {"name", "region", "profile", "k8s_version"},
#   "generated_at":     str (optional),
#   "results":          [{"package", "source", "old", "new", "status", "notes"}],
#       # status ∈ {"updated", "skipped", "deferred", "blocked"}
#   "deferred_majors":  [{"package", "from", "to", "investigation_needed"}]
# }
