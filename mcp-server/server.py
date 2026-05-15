"""MCP server exposing existing Python tools as MCP tools, resources, and prompts."""

import asyncio
import json
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

REPO_ROOT = Path(__file__).resolve().parent.parent
EKS_TOOLS = REPO_ROOT / "skills" / "devops" / "aws-eks-updater" / "tools"
AKS_TOOLS = REPO_ROOT / "skills" / "devops" / "azure-aks-updater" / "tools"
EKS_REFS = REPO_ROOT / "skills" / "devops" / "aws-eks-updater" / "references"
AKS_REFS = REPO_ROOT / "skills" / "devops" / "azure-aks-updater" / "references"
EKS_ASSETS = REPO_ROOT / "skills" / "devops" / "aws-eks-updater" / "assets"
AKS_ASSETS = REPO_ROOT / "skills" / "devops" / "azure-aks-updater" / "assets"

server = FastMCP("skills-mcp-server")


async def run_tool_script(script: Path, args: list[str] | None = None) -> str:
    """Run a Python tool script as subprocess and return stdout or raise on error."""
    cmd = [sys.executable, str(script)] + (args or [])
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        error_msg = stderr.decode().strip() or f"Script exited with code {proc.returncode}"
        return json.dumps({"error": True, "message": error_msg, "exit_code": proc.returncode})
    return stdout.decode()


# --- Tools ---


@server.tool()
async def eks_inventory_addons(cluster: str, region: str, profile: str = "") -> str:
    """Inventory installed EKS add-ons for a cluster via AWS API."""
    args = ["--cluster", cluster, "--region", region]
    if profile:
        args += ["--profile", profile]
    return await run_tool_script(EKS_TOOLS / "inventory_addons.py", args)


@server.tool()
async def aks_inventory_addons(cluster: str, resource_group: str, subscription: str = "") -> str:
    """Inventory installed AKS add-ons for a cluster via Azure API."""
    args = ["--cluster", cluster, "--resource-group", resource_group]
    if subscription:
        args += ["--subscription", subscription]
    return await run_tool_script(AKS_TOOLS / "inventory_addons.py", args)


@server.tool()
async def inventory_helm() -> str:
    """Inventory Helm releases in the current kubeconfig context."""
    return await run_tool_script(EKS_TOOLS / "inventory_helm.py")


@server.tool()
async def eks_scan_terraform(root_dir: str) -> str:
    """Scan Terraform files for EKS resource definitions and versions."""
    return await run_tool_script(EKS_TOOLS / "scan_terraform_eks.py", ["--root-dir", root_dir])


@server.tool()
async def aks_scan_terraform(root_dir: str) -> str:
    """Scan Terraform files for AKS resource definitions and versions."""
    return await run_tool_script(AKS_TOOLS / "scan_terraform_aks.py", ["--root-dir", root_dir])


@server.tool()
async def check_prereqs(provider: str, profile: str = "") -> str:
    """Check prerequisites (CLIs, auth) for a cloud provider (aws or azure)."""
    if provider not in ("aws", "azure"):
        return json.dumps({"error": True, "message": "provider must be 'aws' or 'azure'"})
    script = EKS_TOOLS / "check_prereqs.py" if provider == "aws" else AKS_TOOLS / "check_prereqs.py"
    args = []
    if profile:
        args += ["--profile", profile]
    return await run_tool_script(script, args)


# --- Resources ---


@server.resource("skills://eks/compatibility")
def eks_compatibility() -> str:
    """EKS add-on compatibility matrix."""
    return (EKS_REFS / "eks-compatibility.md").read_text()


@server.resource("skills://aks/compatibility")
def aks_compatibility() -> str:
    """AKS add-on compatibility matrix."""
    return (AKS_REFS / "aks-compatibility.md").read_text()


@server.resource("skills://eks/report-templates")
def eks_report_templates() -> str:
    """EKS HTML report templates (plan + summary)."""
    plan = (EKS_ASSETS / "plan_template.html").read_text()
    summary = (EKS_ASSETS / "summary_template.html").read_text()
    return json.dumps({"plan_template": plan, "summary_template": summary})


@server.resource("skills://aks/report-templates")
def aks_report_templates() -> str:
    """AKS HTML report templates (plan + summary)."""
    plan = (AKS_ASSETS / "plan_template.html").read_text()
    summary = (AKS_ASSETS / "summary_template.html").read_text()
    return json.dumps({"plan_template": plan, "summary_template": summary})


# --- Prompts ---


@server.prompt()
def analyze_drift(inventory_json: str, terraform_json: str) -> str:
    """Analyze drift between installed versions (inventory) and declared versions (terraform)."""
    return (
        "Compare the following installed add-on inventory with the Terraform-declared versions. "
        "Identify any version drift and classify each as: in-sync, minor-drift, or major-drift.\n\n"
        f"## Installed Inventory\n```json\n{inventory_json}\n```\n\n"
        f"## Terraform Declarations\n```json\n{terraform_json}\n```\n\n"
        "Produce a table with columns: Component, Installed Version, Declared Version, Drift Status."
    )


@server.prompt()
def changelog_research(package: str, from_version: str, to_version: str) -> str:
    """Generate a research prompt for changelog analysis between two versions."""
    return (
        f"Research the changelog for **{package}** from version **{from_version}** to **{to_version}**.\n\n"
        "For each version in the range:\n"
        "1. Find the GitHub release notes or CHANGELOG.md entries\n"
        "2. Flag any breaking changes, deprecations, or required migration steps\n"
        "3. Note new features that may be relevant\n\n"
        "Summarize findings with a risk assessment: LOW / MEDIUM / HIGH."
    )


@server.prompt()
def upgrade_plan(drift_analysis: str) -> str:
    """Generate an upgrade plan from a drift analysis."""
    return (
        "Based on the following drift analysis, produce a step-by-step upgrade plan.\n\n"
        f"## Drift Analysis\n{drift_analysis}\n\n"
        "Requirements:\n"
        "- Order updates by dependency (control plane first, then add-ons, then Helm releases)\n"
        "- For each component, specify: current version, target version, update method (Terraform / CLI / Helm)\n"
        "- Flag any components that require a specific update sequence\n"
        "- Include rollback steps for each component"
    )


# --- Skill Discovery ---


@server.tool()
async def retrieve_skill(name: str) -> str:
    """Retrieve a skill by name. Returns the SKILL.md content for the requested skill."""
    skills_dir = REPO_ROOT / "skills"
    for skill_path in skills_dir.rglob("SKILL.md"):
        content = skill_path.read_text()
        if content.startswith("---"):
            end = content.index("---", 3)
            frontmatter = content[3:end]
            if f"name: {name}" in frontmatter:
                return content
    return json.dumps({"error": True, "message": f"Skill '{name}' not found"})


@server.tool()
async def list_skills() -> str:
    """List all available skills with their names and descriptions."""
    import re

    skills = []
    skills_dir = REPO_ROOT / "skills"
    for skill_path in skills_dir.rglob("SKILL.md"):
        content = skill_path.read_text()
        if content.startswith("---"):
            end = content.index("---", 3)
            frontmatter = content[3:end]
            name_match = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
            desc_match = re.search(r"description:\s*>?\s*\n?((?:\s+.+\n?)+)", frontmatter)
            if name_match:
                skill_info = {"name": name_match.group(1).strip()}
                if desc_match:
                    skill_info["description"] = " ".join(desc_match.group(1).split())
                skills.append(skill_info)
    return json.dumps(skills, indent=2)


# --- Entry point ---


if __name__ == "__main__":
    server.run()
