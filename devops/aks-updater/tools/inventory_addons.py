#!/usr/bin/env python3
"""inventory_addons.py — list installed AKS add-ons and extensions with current versions
and available upgrade information.

Emits JSON to stdout:
    {
      "kubernetes_version": "1.29.2",
      "available_upgrades": ["1.29.4", "1.30.0"],
      "addons": [
        {
          "name": "monitoring",
          "enabled": true,
          "config": {...}
        },
        ...
      ],
      "extensions": [
        {
          "name": "microsoft.flux",
          "version": "1.7.5",
          "auto_upgrade_minor_version": true,
          "release_train": "stable",
          "provisioning_state": "Succeeded"
        },
        ...
      ]
    }

Usage:
    ./inventory_addons.py <cluster-name> <resource-group> [subscription-id]
"""
from __future__ import annotations

import json
import os
import subprocess
import sys


def az(args: list[str], subscription: str) -> dict | list:
    cmd = ["az"]
    if subscription:
        cmd += ["--subscription", subscription]
    cmd += ["--output", "json"] + args
    out = subprocess.check_output(cmd, text=True)
    return json.loads(out) if out.strip() else {}


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: inventory_addons.py <cluster> <resource-group> [subscription-id]", file=sys.stderr)
        sys.exit(1)

    cluster = sys.argv[1]
    resource_group = sys.argv[2]
    subscription = sys.argv[3] if len(sys.argv) > 3 else os.environ.get("AZURE_SUBSCRIPTION_ID", "")

    cluster_info = az(
        ["aks", "show", "--name", cluster, "--resource-group", resource_group],
        subscription,
    )
    k8s_version = cluster_info.get("kubernetesVersion", "unknown")

    # Available upgrade versions
    available_upgrades: list[str] = []
    try:
        upgrades_data = az(
            ["aks", "get-upgrades", "--name", cluster, "--resource-group", resource_group],
            subscription,
        )
        for control_plane in upgrades_data.get("controlPlaneProfile", {}).get("upgrades", []):
            v = control_plane.get("kubernetesVersion")
            if v:
                available_upgrades.append(v)
    except subprocess.CalledProcessError:
        pass

    # Add-ons (legacy addon_profile + new per-cluster add-ons)
    addon_profiles = cluster_info.get("addonProfiles") or {}
    addons = []
    for addon_name, addon_data in addon_profiles.items():
        addons.append({
            "name": addon_name,
            "enabled": addon_data.get("enabled", False),
            "config": addon_data.get("config") or {},
        })

    # Extensions (az k8s-extension list)
    extensions: list[dict] = []
    try:
        raw_extensions = az(
            ["k8s-extension", "list",
             "--cluster-name", cluster,
             "--resource-group", resource_group,
             "--cluster-type", "managedClusters"],
            subscription,
        )
        for ext in (raw_extensions if isinstance(raw_extensions, list) else []):
            extensions.append({
                "name": ext.get("name"),
                "extension_type": ext.get("extensionType"),
                "version": ext.get("version"),
                "auto_upgrade_minor_version": ext.get("autoUpgradeMinorVersion"),
                "release_train": ext.get("releaseTrain"),
                "provisioning_state": ext.get("provisioningState"),
            })
    except subprocess.CalledProcessError:
        pass

    print(json.dumps({
        "kubernetes_version": k8s_version,
        "available_upgrades": available_upgrades,
        "addons": addons,
        "extensions": extensions,
    }, indent=2))


if __name__ == "__main__":
    main()
