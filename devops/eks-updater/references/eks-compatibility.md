# EKS compatibility references

Where to look when verifying that a target version is compatible with the cluster's
Kubernetes version. Always check the live docs — versions move.

## Kubernetes versions supported by EKS

- AWS docs: https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html
- Standard support: typically 14 months after release, then extended support (additional fees).
- CLI: `aws eks describe-cluster-versions` (lists currently supported versions in the region).

## Add-on version compatibility per K8s version

- CLI is authoritative — do not rely on memory:
  ```
  aws eks describe-addon-versions \
    --addon-name <name> --kubernetes-version <x.y>
  ```
- AWS docs: https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html

Common AWS-managed add-ons to expect:
- `vpc-cni`
- `coredns`
- `kube-proxy`
- `aws-ebs-csi-driver`
- `aws-efs-csi-driver`
- `aws-mountpoint-s3-csi-driver`
- `eks-pod-identity-agent`
- `adot` (AWS Distro for OpenTelemetry)
- `amazon-cloudwatch-observability`

## Helm chart compatibility matrices

Most community charts publish a compatibility matrix in their README on Artifact Hub or
their GitHub repo. Common patterns:

- Chart `Chart.yaml` → `kubeVersion:` constraint (e.g., `>=1.27.0-0`).
- `README.md` section titled "Compatibility", "Supported Kubernetes versions", or
  "Version Matrix".
- For charts published via Bitnami / Helm Hub, check the upstream repo, not the mirror.

## Upgrade path rules (defaults applied by the skill)

- EKS control plane: one minor at a time (e.g., 1.28 → 1.29, not 1.28 → 1.31).
- Node groups: align to control plane minor before bumping the control plane further.
- Add-ons: bump to the **default** version for the target K8s minor unless the user wants
  the latest compatible.
- Helm charts: prefer the previous stable release over the absolute latest (cuts off
  same-day regressions) unless only one stable exists.
