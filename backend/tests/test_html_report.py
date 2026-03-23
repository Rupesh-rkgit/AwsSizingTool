"""Unit tests for ReportGenerator.render_html_report."""

from datetime import datetime

from backend.models.bom import (
    BOMData,
    BOMLineItem,
    BOMSection,
    BOMServiceSummary,
    BOMTier,
    CostSummaryItem,
    SavingsPlanScenario,
)
from backend.models.sizing import (
    BatchJobSpec,
    ConfigParameter,
    CostOptimizationStrategy,
    HPAConfig,
    KubernetesManifest,
    LatencyBudgetItem,
    MonitoringMetric,
    NodeGroupSpec,
    PodSpec,
    ServiceConfig,
    SizingReportData,
    NFRSummaryItem,
)
from backend.services.report_generator import ReportGenerator


def _make_sizing() -> SizingReportData:
    now = datetime(2025, 1, 15, 12, 0, 0)
    return SizingReportData(
        generated_at=now,
        nfr_summary=[NFRSummaryItem(requirement="Latency", target="<200ms")],
        service_configs=[
            ServiceConfig(
                service_name="CloudFront",
                parameters=[ConfigParameter(parameter="TTL", recommendation="3600s", rationale="Cache")],
            )
        ],
        node_groups=[
            NodeGroupSpec(
                name="web", instance_type="c6i.xlarge", vcpu=4, memory_gib=8.0,
                min_nodes=2, max_nodes=6, desired_nodes=3, capacity_type="on-demand",
                disk_size_gib=50, purpose="web serving",
            )
        ],
        pod_specs=[
            PodSpec(
                workload="Web App", cpu_request="500m", cpu_limit="1000m",
                memory_request="512Mi", memory_limit="1536Mi",
                min_pods=2, max_pods=10, scaling_method="HPA",
            )
        ],
        hpa_configs=[
            HPAConfig(
                target_deployment="web", min_replicas=2, max_replicas=10,
                cpu_target_percent=50, scale_up_window_seconds=60,
                scale_down_window_seconds=300,
            )
        ],
        latency_budget=[
            LatencyBudgetItem(component="CloudFront", expected_latency="5ms", notes="CDN edge"),
        ],
        kubernetes_manifests=[
            KubernetesManifest(kind="Deployment", name="web-app", yaml_content="apiVersion: apps/v1\nkind: Deployment"),
        ],
        batch_jobs=[
            BatchJobSpec(
                frequency="daily", record_volume="10K", processing_window="2h",
                throughput_required="100/s", parallelism=3,
                pod_cpu_request="1000m", pod_cpu_limit="2000m",
                pod_memory_request="2Gi", pod_memory_limit="4Gi",
            )
        ],
        cost_optimization=[
            CostOptimizationStrategy(strategy="Spot Instances", savings_potential="60%", applicable_to="Batch"),
        ],
        container_best_practices=[
            ConfigParameter(parameter="Image Size", recommendation="<500MB", rationale="Fast pulls"),
        ],
        network_config=[
            ConfigParameter(parameter="VPC CIDR", recommendation="10.0.0.0/16", rationale="Large range"),
        ],
        monitoring_metrics=[
            MonitoringMetric(metric="CPU Usage", target="<70%", action_if_exceeded="Scale up"),
        ],
    )


def _make_bom() -> BOMData:
    now = datetime(2025, 1, 15, 12, 0, 0)
    section = BOMSection(
        section_name="CDN",
        section_number="1.1",
        line_items=[
            BOMLineItem(
                line_item="CloudFront", specification="Global",
                quantity="1", unit_price="$50", monthly_estimate=50.0,
            )
        ],
        subtotal=50.0,
    )
    return BOMData(
        generated_at=now,
        tiers=[BOMTier(tier_name="Web Tier", tier_number=1, sections=[section], subtotal=50.0)],
        cost_summary=[CostSummaryItem(category="Compute", monthly_estimate=50.0)],
        total_monthly=50.0,
        total_annual=600.0,
        savings_plans=[
            SavingsPlanScenario(
                scenario="1-Year", monthly_estimate="$40",
                annual_estimate="$480", savings_vs_on_demand="20%",
            )
        ],
        service_summary=[
            BOMServiceSummary(number=1, service="CloudFront", purpose="CDN", specification="Global"),
        ],
        notes=["Estimates only"],
    )


class TestRenderHtmlReport:
    def setup_method(self):
        self.rg = ReportGenerator()
        self.sizing = _make_sizing()
        self.bom = _make_bom()
        self.html = self.rg.render_html_report(self.sizing, self.bom)

    def test_returns_html_string(self):
        assert isinstance(self.html, str)
        assert "<!DOCTYPE html>" in self.html
        assert "</html>" in self.html

    def test_contains_top_bar(self):
        assert "top-bar" in self.html
        assert self.sizing.title in self.html

    def test_contains_toc_sidebar(self):
        assert "toc-sidebar" in self.html

    def test_toc_has_all_sizing_anchors(self):
        sizing_anchors = [
            "#nfr-summary", "#service-configs", "#node-groups", "#pod-specs",
            "#hpa-configs", "#latency-budget", "#kubernetes-manifests",
            "#batch-jobs", "#cost-optimization", "#container-best-practices",
            "#network-config", "#monitoring-metrics",
        ]
        for anchor in sizing_anchors:
            assert anchor in self.html, f"Missing TOC anchor: {anchor}"

    def test_toc_has_all_bom_anchors(self):
        bom_anchors = [
            "#bom-tiers", "#cost-summary", "#savings-plans",
            "#service-summary", "#notes",
        ]
        for anchor in bom_anchors:
            assert anchor in self.html, f"Missing TOC anchor: {anchor}"

    def test_sections_have_matching_ids(self):
        section_ids = [
            'id="nfr-summary"', 'id="service-configs"', 'id="node-groups"',
            'id="pod-specs"', 'id="hpa-configs"', 'id="latency-budget"',
            'id="kubernetes-manifests"', 'id="batch-jobs"', 'id="cost-optimization"',
            'id="container-best-practices"', 'id="network-config"',
            'id="monitoring-metrics"', 'id="bom-tiers"', 'id="cost-summary"',
            'id="savings-plans"', 'id="service-summary"', 'id="notes"',
        ]
        for sid in section_ids:
            assert sid in self.html, f"Missing section id: {sid}"

    def test_contains_sizing_data(self):
        assert "c6i.xlarge" in self.html
        assert "CloudFront" in self.html
        assert "web" in self.html

    def test_contains_bom_data(self):
        assert "Web Tier" in self.html
        assert "50.00" in self.html
        assert "600.00" in self.html

    def test_contains_summary_cards(self):
        assert "summary-card" in self.html
        assert "Total Monthly Cost" in self.html
        assert "Total Annual Cost" in self.html

    def test_contains_code_blocks_for_yaml(self):
        assert "<pre>" in self.html
        assert "<code>" in self.html
        assert "apiVersion: apps/v1" in self.html

    def test_contains_styled_tables(self):
        assert "<table>" in self.html
        assert "<th>" in self.html

    def test_has_both_sizing_and_bom_sections(self):
        assert "section-infra" in self.html
        assert "section-bom" in self.html
