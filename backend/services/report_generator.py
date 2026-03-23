"""Report generator service for serialization, deserialization, and rendering."""

import os
from datetime import datetime, timezone

from jinja2 import Environment, FileSystemLoader

from backend.models.bom import BOMData
from backend.models.envelope import ReportEnvelope
from backend.models.sizing import SizingReportData


def _fmt_dt(dt: datetime) -> str:
    """Format a datetime as a human-readable string in UTC, e.g. '23 Mar 2026, 10:06 AM UTC'."""
    utc = dt.astimezone(timezone.utc)
    # %d gives zero-padded day; lstrip removes leading zero on Windows & Linux
    day = str(utc.day)
    return utc.strftime(f"{day} %b %Y, %I:%M %p UTC")


class ReportGenerator:
    """Converts report data to/from JSON, Markdown, and HTML formats."""

    def serialize(self, envelope: ReportEnvelope) -> str:
        """Serialize ReportEnvelope to a JSON string.

        Args:
            envelope: The complete report envelope containing sizing, BOM, and metadata.

        Returns:
            A JSON string representation of the envelope.
        """
        return envelope.model_dump_json(indent=2)

    def deserialize(self, json_str: str) -> ReportEnvelope:
        """Parse a JSON string back into a ReportEnvelope.

        Args:
            json_str: A JSON string previously produced by serialize().

        Returns:
            A ReportEnvelope instance reconstructed from the JSON.
        """
        return ReportEnvelope.model_validate_json(json_str)

    def render_sizing_markdown(self, data: SizingReportData) -> str:
        """Render SizingReportData to a Markdown string.

        Produces a complete Markdown document with sections for NFR summary,
        service configs, node groups, pod specs, HPA configs, latency budget,
        Kubernetes YAML snippets, batch jobs, cost optimization, container
        best practices, network config, and monitoring metrics.

        Args:
            data: The sizing report data to render.

        Returns:
            A Markdown-formatted string containing the full sizing report.
        """
        lines: list[str] = []

        # Title and metadata
        lines.append(f"# {data.title}")
        lines.append("")
        lines.append(f"**Generated:** {_fmt_dt(data.generated_at)}")
        lines.append(f"**Region:** {data.region}")
        lines.append("")

        # NFR Summary
        if data.nfr_summary:
            lines.append("## Non-Functional Requirements Summary")
            lines.append("")
            lines.append("| Requirement | Target |")
            lines.append("|---|---|")
            for item in data.nfr_summary:
                lines.append(f"| {item.requirement} | {item.target} |")
            lines.append("")

        # Service Configs
        if data.service_configs:
            lines.append("## Service Configurations")
            lines.append("")
            for svc in data.service_configs:
                lines.append(f"### {svc.service_name}")
                lines.append("")
                lines.append("| Parameter | Recommendation | Rationale |")
                lines.append("|---|---|---|")
                for p in svc.parameters:
                    rationale = p.rationale or ""
                    lines.append(f"| {p.parameter} | {p.recommendation} | {rationale} |")
                lines.append("")

        # Node Groups
        if data.node_groups:
            lines.append("## Node Groups")
            lines.append("")
            lines.append("| Name | Instance Type | vCPU | Memory (GiB) | Min Nodes | Max Nodes | Desired Nodes | Capacity Type |")
            lines.append("|---|---|---|---|---|---|---|---|")
            for ng in data.node_groups:
                lines.append(
                    f"| {ng.name} | {ng.instance_type} | {ng.vcpu} | {ng.memory_gib} "
                    f"| {ng.min_nodes} | {ng.max_nodes} | {ng.desired_nodes} | {ng.capacity_type} |"
                )
            lines.append("")

        # Pod Specs
        if data.pod_specs:
            lines.append("## Pod Specifications")
            lines.append("")
            lines.append("| Workload | CPU Request | CPU Limit | Memory Request | Memory Limit | Min Pods | Max Pods | Scaling Method |")
            lines.append("|---|---|---|---|---|---|---|---|")
            for ps in data.pod_specs:
                lines.append(
                    f"| {ps.workload} | {ps.cpu_request} | {ps.cpu_limit} "
                    f"| {ps.memory_request} | {ps.memory_limit} "
                    f"| {ps.min_pods} | {ps.max_pods} | {ps.scaling_method} |"
                )
            lines.append("")

        # HPA Configs
        if data.hpa_configs:
            lines.append("## HPA Configurations")
            lines.append("")
            lines.append("| Target Deployment | Min Replicas | Max Replicas | CPU Target % |")
            lines.append("|---|---|---|---|")
            for hpa in data.hpa_configs:
                lines.append(
                    f"| {hpa.target_deployment} | {hpa.min_replicas} "
                    f"| {hpa.max_replicas} | {hpa.cpu_target_percent} |"
                )
            lines.append("")

        # Latency Budget
        if data.latency_budget:
            lines.append("## Latency Budget")
            lines.append("")
            lines.append("| Component | Expected Latency | Notes |")
            lines.append("|---|---|---|")
            for lb in data.latency_budget:
                lines.append(f"| {lb.component} | {lb.expected_latency} | {lb.notes} |")
            lines.append("")

        # Kubernetes Manifests
        if data.kubernetes_manifests:
            lines.append("## Kubernetes YAML Snippets")
            lines.append("")
            for manifest in data.kubernetes_manifests:
                lines.append(f"### {manifest.kind}: {manifest.name}")
                lines.append("")
                lines.append("```yaml")
                lines.append(manifest.yaml_content)
                lines.append("```")
                lines.append("")

        # Batch Jobs
        if data.batch_jobs:
            lines.append("## Batch Jobs")
            lines.append("")
            lines.append("| Frequency | Record Volume | Processing Window | Throughput Required | Parallelism | CPU Request | CPU Limit | Memory Request | Memory Limit |")
            lines.append("|---|---|---|---|---|---|---|---|---|")
            for bj in data.batch_jobs:
                lines.append(
                    f"| {bj.frequency} | {bj.record_volume} | {bj.processing_window} "
                    f"| {bj.throughput_required} | {bj.parallelism} "
                    f"| {bj.pod_cpu_request} | {bj.pod_cpu_limit} "
                    f"| {bj.pod_memory_request} | {bj.pod_memory_limit} |"
                )
            lines.append("")

        # Cost Optimization
        if data.cost_optimization:
            lines.append("## Cost Optimization Strategies")
            lines.append("")
            lines.append("| Strategy | Savings Potential | Applicable To |")
            lines.append("|---|---|---|")
            for co in data.cost_optimization:
                lines.append(f"| {co.strategy} | {co.savings_potential} | {co.applicable_to} |")
            lines.append("")

        # Container Best Practices
        if data.container_best_practices:
            lines.append("## Container Best Practices")
            lines.append("")
            lines.append("| Parameter | Recommendation | Rationale |")
            lines.append("|---|---|---|")
            for bp in data.container_best_practices:
                rationale = bp.rationale or ""
                lines.append(f"| {bp.parameter} | {bp.recommendation} | {rationale} |")
            lines.append("")

        # Network Config
        if data.network_config:
            lines.append("## Network Configuration")
            lines.append("")
            lines.append("| Parameter | Recommendation | Rationale |")
            lines.append("|---|---|---|")
            for nc in data.network_config:
                rationale = nc.rationale or ""
                lines.append(f"| {nc.parameter} | {nc.recommendation} | {rationale} |")
            lines.append("")

        # Monitoring Metrics
        if data.monitoring_metrics:
            lines.append("## Monitoring Metrics")
            lines.append("")
            lines.append("| Metric | Target | Action if Exceeded |")
            lines.append("|---|---|---|")
            for mm in data.monitoring_metrics:
                lines.append(f"| {mm.metric} | {mm.target} | {mm.action_if_exceeded} |")
            lines.append("")

        return "\n".join(lines)

    def render_html_report(self, sizing: SizingReportData, bom: BOMData) -> str:
        """Render a combined HTML report from sizing and BOM data using Jinja2.

        Produces a professional HTML document with a top bar, TOC sidebar with
        anchor links, color-coded sections for infrastructure sizing and BOM,
        styled tables, code blocks for YAML snippets, and summary cards.

        Args:
            sizing: The sizing report data to render.
            bom: The BOM data to render.

        Returns:
            A rendered HTML string containing the full combined report.
        """
        templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        env = Environment(loader=FileSystemLoader(templates_dir), autoescape=True)
        template = env.get_template("report.html")
        return template.render(sizing=sizing, bom=bom)

    def render_bom_markdown(self, data: BOMData) -> str:
        """Render BOMData to a Markdown string.

        Produces a complete Markdown document with tiers, sections, line items,
        cost summary, savings plans, service summary, and notes.

        Args:
            data: The BOM data to render.

        Returns:
            A Markdown-formatted string containing the full BOM report.
        """
        lines: list[str] = []

        # Title and metadata
        lines.append(f"# {data.title}")
        lines.append("")
        lines.append(f"**Generated:** {_fmt_dt(data.generated_at)}")
        lines.append(f"**Region:** {data.region}")
        lines.append(f"**Pricing:** {data.pricing_type}")
        lines.append("")

        # Tiers
        for tier in data.tiers:
            lines.append(f"## {tier.tier_name}")
            lines.append("")

            for section in tier.sections:
                lines.append(f"### {section.section_name}")
                lines.append("")
                lines.append("| Line Item | Specification | Quantity | Unit Price | Monthly Estimate |")
                lines.append("|---|---|---|---|---|")
                for item in section.line_items:
                    lines.append(
                        f"| {item.line_item} | {item.specification} "
                        f"| {item.quantity} | {item.unit_price} "
                        f"| ${item.monthly_estimate:,.2f} |"
                    )
                lines.append("")
                lines.append(f"**Section Subtotal:** ${section.subtotal:,.2f}")
                lines.append("")

            lines.append(f"**Tier Subtotal:** ${tier.subtotal:,.2f}")
            lines.append("")

        # Cost Summary
        if data.cost_summary:
            lines.append("## Cost Summary")
            lines.append("")
            lines.append("| Category | Monthly Estimate |")
            lines.append("|---|---|")
            for item in data.cost_summary:
                lines.append(f"| {item.category} | ${item.monthly_estimate:,.2f} |")
            lines.append("")

        # Total costs
        lines.append(f"**Total Monthly Cost:** ${data.total_monthly:,.2f}")
        lines.append("")
        lines.append(f"**Total Annual Cost:** ${data.total_annual:,.2f}")
        lines.append("")

        # Savings Plans
        if data.savings_plans:
            lines.append("## Savings Plans")
            lines.append("")
            lines.append("| Scenario | Monthly Estimate | Annual Estimate | Savings vs On-Demand |")
            lines.append("|---|---|---|---|")
            for sp in data.savings_plans:
                lines.append(
                    f"| {sp.scenario} | {sp.monthly_estimate} "
                    f"| {sp.annual_estimate} | {sp.savings_vs_on_demand} |"
                )
            lines.append("")

        # Service Summary
        if data.service_summary:
            lines.append("## Service Summary")
            lines.append("")
            lines.append("| # | Service | Purpose | Specification |")
            lines.append("|---|---|---|---|")
            for svc in data.service_summary:
                lines.append(
                    f"| {svc.number} | {svc.service} "
                    f"| {svc.purpose} | {svc.specification} |"
                )
            lines.append("")

        # Notes
        if data.notes:
            lines.append("## Notes")
            lines.append("")
            for note in data.notes:
                lines.append(f"- {note}")
            lines.append("")

        return "\n".join(lines)
