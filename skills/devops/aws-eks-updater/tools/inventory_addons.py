#!/usr/bin/env python3
"""inventory_addons.py — list installed EKS add-ons with current and latest-compatible versions.

Emits JSON to stdout:
    {
      "kubernetes_version": "1.29",
      "addons": [
        {
          "name": "vpc-cni",
          "current": "v1.18.0-eksbuild.1",
          "latest_compatible": "v1.19.0-eksbuild.1",
          "default": "v1.18.5-eksbuild.1",
          "all_compatible": [{"version": "...", "default": true|false}, ...]
        },
        ...
      ]
    }

Usage:
    ./inventory_addons.py <cluster-name> <region> [aws-profile]
"""
from __future__ import annotations

import json
import os
import subprocess
import sys


def aws(args: list[str], profile: str, region: str) -> dict | list:
    cmd = ["aws"]
    if profile:
        cmd += ["--profile", profile]
    cmd += ["--region", region, "--output", "json"] + args
    out = subprocess.check_output(cmd, text=True)
    return json.loads(out) if out.strip() else {}


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: inventory_addons.py <cluster> <region> [profile]", file=sys.stderr)
        sys.exit(1)

    cluster = sys.argv[1]
    region = sys.argv[2]
    profile = sys.argv[3] if len(sys.argv) > 3 else os.environ.get("AWS_PROFILE", "")

    cluster_info = aws(["eks", "describe-cluster", "--name", cluster], profile, region)
    k8s_version = cluster_info["cluster"]["version"]

    installed = aws(["eks", "list-addons", "--cluster-name", cluster], profile, region)
    addon_names = installed.get("addons", [])

    result_addons = []
    for name in addon_names:
        try:
            described = aws(
                ["eks", "describe-addon", "--cluster-name", cluster, "--addon-name", name],
                profile, region,
            )
            current = described["addon"].get("addonVersion", "unknown")
        except subprocess.CalledProcessError:
            current = "unknown"

        try:
            versions_data = aws(
                ["eks", "describe-addon-versions",
                 "--addon-name", name,
                 "--kubernetes-version", k8s_version],
                profile, region,
            )
        except subprocess.CalledProcessError:
            versions_data = {"addons": []}

        all_versions = []
        latest = "unknown"
        default_ver = "unknown"

        addon_blocks = versions_data.get("addons", [])
        if addon_blocks:
            for v in addon_blocks[0].get("addonVersions", []):
                version = v.get("addonVersion", "")
                is_default = any(c.get("defaultVersion") for c in v.get("compatibilities", []))
                all_versions.append({"version": version, "default": bool(is_default)})

            if all_versions:
                latest = all_versions[0]["version"]
                defaults = [v["version"] for v in all_versions if v["default"]]
                if defaults:
                    default_ver = defaults[0]

        result_addons.append({
            "name": name,
            "current": current,
            "latest_compatible": latest,
            "default": default_ver,
            "all_compatible": all_versions,
        })

    print(json.dumps({
        "kubernetes_version": k8s_version,
        "addons": result_addons,
    }, indent=2))


if __name__ == "__main__":
    main()
