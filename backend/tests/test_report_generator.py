"""Unit tests for ReportGenerator serialize/deserialize methods."""

import json
from datetime import datetime

import pytest

from backend.models.bom import (
    BOMData,
    BOMLineItem,
    BOMSection,
    BOMServiceSummary,
    BOMTier,
    CostSummaryItem,
    SavingsPlanScenario,
)
from backend.models.envelope import ReportEnvelope, ReportMetadata
from backend.models.sizing import (
    HPAConfig,
    NodeGroupSpec,
    SizingReportData,
)
from backend.services.report_generator import ReportGenerator


# --- Helpers ---

def _make_envelope() -> ReportEnvelope:
    now = datetime(2025, 1, 15, 12, 0, 0)
    sizing = SizingReportData(
        generated_at=now,
        nfr_summary=[],
        service_configs=[],
        node_groups=[
            NodeGroupSpec(
                name="web", instance_type="c6i.xlarge", vcpu=4, memory_gib=8.0,
                min_nodes=2, max_nodes=6, desired_nodes=3, capacity_type="on-demand",
                disk_size_gib=50, purpose="web serving",
            )
        ],
        pod_specs=[],
        hpa_configs=[
            HPAConfig(
                target_deployment="web", min_replicas=2, max_replicas=10,
                cpu_target_percent=50, scale_up_window_seconds=60,
                scale_down_window_seconds=300,
            )
        ],
        latency_budget=[],
        kubernetes_manifests=[],
        batch_jobs=[],
        cost_optimization=[],
        container_best_practices=[],
        network_config=[],
        monitoring_metrics=[],
    )
    section = BOMSection(
        section_name="CDN", section_number="1.1",
        line_items=[BOMLineItem(
            line_item="CloudFront", specification="Global",
            quantity="1", unit_price="$50", monthly_estimate=50.0,
        )],
        subtotal=50.0,
    )
    bom = BOMData(
        generated_at=now,
        tiers=[BOMTier(tier_name="Web Tier", tier_number=1, sections=[section], subtotal=50.0)],
        cost_summary=[],
        total_monthly=50.0,
        total_annual=600.0,
        savings_plans=[SavingsPlanScenario(
            scenario="1-Year", monthly_estimate="$40",
            annual_estimate="$480", savings_vs_on_demand="20%",
        )],
        service_summary=[BOMServiceSummary(
            number=1, service="CloudFront", purpose="CDN", specification="Global",
        )],
        notes=["Estimates only"],
    )
    meta = ReportMetadata(
        generated_at=now, region="us-east-1", tool_version="1.0",
        llm_model="anthropic.claude-3-5-sonnet-20241022-v2:0",
        bedrock_latency_ms=1200, input_had_diagram=True, input_had_prompt=True,
    )
    return ReportEnvelope(sizing_report=sizing, bom=bom, metadata=meta)


# --- Tests ---

class TestReportGeneratorSerialize:
    def setup_method(self):
        self.rg = ReportGenerator()

    def test_serialize_returns_valid_json(self):
        envelope = _make_envelope()
        result = self.rg.serialize(envelope)
        parsed = json.loads(result)
        assert "sizing_report" in parsed
        assert "bom" in parsed
        assert "metadata" in parsed

    def test_serialize_is_indented(self):
        envelope = _make_envelope()
        result = self.rg.serialize(envelope)
        # indent=2 produces newlines and spaces
        assert "\n" in result

    def test_round_trip_produces_equal_object(self):
        envelope = _make_envelope()
        json_str = self.rg.serialize(envelope)
        restored = self.rg.deserialize(json_str)
        assert restored == envelope

    def test_deserialize_invalid_json_raises(self):
        with pytest.raises(Exception):
            self.rg.deserialize("not valid json")

    def test_deserialize_wrong_schema_raises(self):
        with pytest.raises(Exception):
            self.rg.deserialize('{"foo": "bar"}')


class TestRenderBomMarkdown:
    def setup_method(self):
        self.rg = ReportGenerator()

    def _make_bom(self) -> BOMData:
        now = datetime(2025, 1, 15, 12, 0, 0)
        section1 = BOMSection(
            section_name="Amazon CloudFront (CDN)",
            section_number="1.1",
            line_items=[
                BOMLineItem(
                    line_item="CloudFront Distribution",
                    specification="Global edge locations",
                    quantity="1",
                    unit_price="$50.00",
                    monthly_estimate=50.0,
                )
            ],
            subtotal=50.0,
        )
        section2 = BOMSection(
            section_name="Application Load Balancer",
            section_number="1.2",
            line_items=[
                BOMLineItem(
                    line_item="ALB",
                    specification="2 AZs",
                    quantity="1",
                    unit_price="$22.00",
                    monthly_estimate=22.0,
                )
            ],
            subtotal=22.0,
        )
        tier1 = BOMTier(
            tier_name="Web Application Tier",
            tier_number=1,
            sections=[section1, section2],
            subtotal=72.0,
        )
        tier2 = BOMTier(
            tier_name="Batch Processing Tier",
            tier_number=2,
            sections=[
                BOMSection(
                    section_name="EKS Batch Nodes",
                    section_number="2.1",
                    line_items=[
                        BOMLineItem(
                            line_item="c6i.2xlarge Spot",
                            specification="8 vCPU, 16 GiB",
                            quantity="3",
                            unit_price="$0.10/hr",
                            monthly_estimate=216.0,
                        )
                    ],
                    subtotal=216.0,
                )
            ],
            subtotal=216.0,
        )
        return BOMData(
            generated_at=now,
            tiers=[tier1, tier2],
            cost_summary=[
                CostSummaryItem(category="Compute", monthly_estimate=200.0),
                CostSummaryItem(category="Networking", monthly_estimate=88.0),
            ],
            total_monthly=288.0,
            total_annual=3456.0,
            savings_plans=[
                SavingsPlanScenario(
                    scenario="1-Year No Upfront",
                    monthly_estimate="$230.00",
                    annual_estimate="$2,760.00",
                    savings_vs_on_demand="20%",
                )
            ],
            service_summary=[
                BOMServiceSummary(
                    number=1, service="CloudFront", purpose="CDN", specification="Global",
                ),
                BOMServiceSummary(
                    number=2, service="ALB", purpose="Load Balancing", specification="2 AZs",
                ),
            ],
            notes=["All prices are estimates", "Based on us-east-1 pricing"],
        )

    def test_contains_title(self):
        bom = self._make_bom()
        md = self.rg.render_bom_markdown(bom)
        assert bom.title in md

    def test_contains_metadata(self):
        bom = self._make_bom()
        md = self.rg.render_bom_markdown(bom)
        assert bom.region in md
        assert bom.pricing_type in md
        assert bom.generated_at.isoformat() in md

    def test_contains_all_tier_names(self):
        bom = self._make_bom()
        md = self.rg.render_bom_markdown(bom)
        for tier in bom.tiers:
            assert tier.tier_name in md

    def test_contains_all_section_names(self):
        bom = self._make_bom()
        md = self.rg.render_bom_markdown(bom)
        for tier in bom.tiers:
            for section in tier.sections:
                assert section.section_name in md

    def test_contains_line_items(self):
        bom = self._make_bom()
        md = self.rg.render_bom_markdown(bom)
        for tier in bom.tiers:
            for section in tier.sections:
                for item in section.line_items:
                    assert item.line_item in md
                    assert item.specification in md

    def test_contains_total_monthly(self):
        bom = self._make_bom()
        md = self.rg.render_bom_markdown(bom)
        assert f"${bom.total_monthly:,.2f}" in md

    def test_contains_total_annual(self):
        bom = self._make_bom()
        md = self.rg.render_bom_markdown(bom)
        assert f"${bom.total_annual:,.2f}" in md

    def test_contains_cost_summary(self):
        bom = self._make_bom()
        md = self.rg.render_bom_markdown(bom)
        assert "Cost Summary" in md
        for item in bom.cost_summary:
            assert item.category in md

    def test_contains_savings_plans(self):
        bom = self._make_bom()
        md = self.rg.render_bom_markdown(bom)
        assert "Savings Plans" in md
        for sp in bom.savings_plans:
            assert sp.scenario in md

    def test_contains_service_summary(self):
        bom = self._make_bom()
        md = self.rg.render_bom_markdown(bom)
        assert "Service Summary" in md
        for svc in bom.service_summary:
            assert svc.service in md

    def test_contains_notes(self):
        bom = self._make_bom()
        md = self.rg.render_bom_markdown(bom)
        assert "Notes" in md
        for note in bom.notes:
            assert note in md
