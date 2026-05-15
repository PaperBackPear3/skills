# AKS compatibility references

Where to look when verifying that a target version is compatible with the cluster's
Kubernetes version. Always check the live docs — versions move.

## Kubernetes versions supported by AKS

- Azure docs: https://learn.microsoft.com/en-us/azure/aks/supported-kubernetes-versions
- AKS typically supports the last 3 stable minor Kubernetes versions.
- CLI (authoritative): `az aks get-versions --location <region> --output table`
- Upgrade path: `az aks get-upgrades --name <cluster> --resource-group <rg>`

## Add-on version compatibility per K8s version

- Azure Portal and CLI are authoritative — do not rely on memory:
  ```
  az aks addon show --name <cluster> --resource-group <rg> --addon <name>
  ```
- Azure docs (add-ons overview): https://learn.microsoft.com/en-us/azure/aks/integrations

Common Azure-managed add-ons to expect:
- `monitoring` (Azure Monitor / Container Insights)
- `azure-keyvault-secrets-provider` (Key Vault CSI driver)
- `ingress-appgw` (Application Gateway Ingress Controller / AGIC)
- `azure-policy`
- `gitops` (Flux v2)
- `open-service-mesh` (OSM — deprecated in favor of Istio add-on)
- `virtual-node` (ACI virtual nodes)
- `http_application_routing` (deprecated — prefer AGIC or nginx ingress)

## Extensions (az k8s-extension) common types

- `microsoft.flux` (GitOps / Flux v2)
- `microsoft.dapr` (Dapr)
- `microsoft.azureml.kubernetes` (Azure Machine Learning)
- `microsoft.azure.defender` (Defender for Containers)
- Extensions release trains: `stable`, `preview`
- Extension docs: https://learn.microsoft.com/en-us/azure/azure-arc/kubernetes/extensions

## Helm chart compatibility matrices

Most community charts publish a compatibility matrix in their README on Artifact Hub or
their GitHub repo. Common patterns:

- Chart `Chart.yaml` → `kubeVersion:` constraint (e.g., `>=1.27.0-0`).
- `README.md` section titled "Compatibility", "Supported Kubernetes versions", or
  "Version Matrix".
- For charts published via Bitnami / Helm Hub, check the upstream repo, not the mirror.

## Upgrade path rules (defaults applied by the skill)

- AKS control plane: one minor at a time (e.g., 1.28 → 1.29, not 1.28 → 1.31).
  Azure enforces this — `az aks upgrade` will reject skipped minors.
- Node pools: must be at the same minor version or at most one minor behind the control plane.
  Upgrade node pools after the control plane reaches the target minor.
- Add-ons: typically auto-updated by Azure when the control plane is upgraded. Check
  `az aks addon list` post-upgrade to confirm versions.
- Extensions: controlled by `auto_upgrade_minor_version`. If false, bump manually.
- Helm charts: prefer the previous stable release over the absolute latest (cuts off
  same-day regressions) unless only one stable exists.
