"""Unit tests for Pydantic data models (sizing, bom, envelope)."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from backend.models.sizing import (
    NFRSummaryItem,
    ConfigParameter,
    ServiceConfig,
    NodeGroupSpec,
    PodSpec,
    HPAConfig,
    LatencyBudgetItem,
    KubernetesManifest,
    BatchJobSpec,
    CostOptimizationStrategy,
    MonitoringMetric,
    SizingReportData,
)
from backend.models.bom import (
    BOMLineItem,
    BOMSection,
    BOMTier,
    CostSummaryItem,
    SavingsPlanScenario,
    BOMServiceSummary,
    BOMData,
)
from backend.models.envelope import ReportMetadata, ReportEnvelope


# --- Fixtures ---

def make_node_group(**overrides):
    defaults = dict(
        name="web", instance_type="c6i.xlarge", vcpu=4, memory_gib=8.0,
        min_nodes=2, max_nodes=6, desired_nodes=3, capacity_type="on-demand",
        disk_size_gib=50, purpose="web serving",
    )
    defaults.update(overrides)
    return NodeGroupSpec(**defaults)


def make_hpa(**overrides):
    defaults = dict(
        target_deployment="web", min_replicas=2, max_replicas=10,
        cpu_target_percent=50, scale_up_window_seconds=60, scale_down_window_seconds=300,
    )
    defaults.update(overrides)
    return HPAConfig(**defaults)


def make_batch_job(**overrides):
    defaults = dict(
        frequency="daily", record_volume="10K", processing_window="2h",
        throughput_required="100/s", parallelism=3,
        pod_cpu_request="500m", pod_cpu_limit="1000m",
        pod_memory_request="512Mi", pod_memory_limit="1Gi",
    )
    defaults.update(overrides)
    return BatchJobSpec(**defaults)


def make_bom_line_item(**overrides):
    defaults = dict(
        line_item="CloudFront Distribution", specification="Global edge",
        quantity="1", unit_price="$50.00", monthly_estimate=50.0,
    )
    defaults.update(overrides)
    return BOMLineItem(**defaults)


def make_bom_data(**overrides):
    section = BOMSection(
        section_name="CDN", section_number="1.1",
        line_items=[make_bom_line_item()], subtotal=50.0,
    )
    tier = BOMTier(tier_name="Web Tier", tier_number=1, sections=[section], subtotal=50.0)
    defaults = dict(
        generated_at=datetime(2025, 1, 15, 12, 0, 0),
        tiers=[tier], cost_summary=[], total_monthly=50.0, total_annual=600.0,
        savings_plans=[SavingsPlanScenario(
            scenario="1-Year", monthly_estimate="$40", annual_estimate="$480",
            savings_vs_on_demand="20%",
        )],
        service_summary=[BOMServiceSummary(number=1, service="CloudFront", purpose="CDN", specification="Global")],
        notes=["Prices are estimates"],
    )
    defaults.update(overrides)
    return BOMData(**defaults)


# --- NodeGroupSpec Tests ---

class TestNodeGroupSpec:
    def test_valid_creation(self):
        ng = make_node_group()
        assert ng.vcpu == 4
        assert ng.memory_gib == 8.0
        assert ng.instance_type == "c6i.xlarge"

    def test_rejects_empty_instance_type(self):
        with pytest.raises(ValidationError):
            make_node_group(instance_type="")

    def test_rejects_vcpu_zero(self):
        with pytest.raises(ValidationError):
            make_node_group(vcpu=0)

    def test_rejects_negative_vcpu(self):
        with pytest.raises(ValidationError):
            make_node_group(vcpu=-1)

    def test_rejects_memory_gib_zero(self):
        with pytest.raises(ValidationError):
            make_node_group(memory_gib=0)

    def test_rejects_negative_memory_gib(self):
        with pytest.raises(ValidationError):
            make_node_group(memory_gib=-1.0)


# --- HPAConfig Tests ---

class TestHPAConfig:
    def test_valid_creation(self):
        hpa = make_hpa()
        assert hpa.min_replicas == 2
        assert hpa.max_replicas == 10

    def test_rejects_max_less_than_min(self):
        with pytest.raises(ValidationError):
            make_hpa(min_replicas=5, max_replicas=2)

    def test_allows_equal_min_max(self):
        hpa = make_hpa(min_replicas=3, max_replicas=3)
        assert hpa.min_replicas == hpa.max_replicas

    def test_rejects_cpu_target_zero(self):
        with pytest.raises(ValidationError):
            make_hpa(cpu_target_percent=0)

    def test_rejects_negative_cpu_target(self):
        with pytest.raises(ValidationError):
            make_hpa(cpu_target_percent=-10)


# --- BatchJobSpec Tests ---

class TestBatchJobSpec:
    def test_valid_creation(self):
        bj = make_batch_job()
        assert bj.parallelism == 3

    def test_rejects_parallelism_zero(self):
        with pytest.raises(ValidationError):
            make_batch_job(parallelism=0)

    def test_allows_parallelism_one(self):
        bj = make_batch_job(parallelism=1)
        assert bj.parallelism == 1

    def test_rejects_empty_pod_cpu_request(self):
        with pytest.raises(ValidationError):
            make_batch_job(pod_cpu_request="")

    def test_rejects_empty_pod_memory_limit(self):
        with pytest.raises(ValidationError):
            make_batch_job(pod_memory_limit="")


# --- LatencyBudgetItem Tests ---

class TestLatencyBudgetItem:
    def test_valid_creation(self):
        item = LatencyBudgetItem(component="CDN", expected_latency="5ms", notes="edge cache")
        assert item.component == "CDN"

    def test_rejects_empty_component(self):
        with pytest.raises(ValidationError):
            LatencyBudgetItem(component="", expected_latency="5ms", notes="n")

    def test_rejects_empty_expected_latency(self):
        with pytest.raises(ValidationError):
            LatencyBudgetItem(component="CDN", expected_latency="", notes="n")


# --- BOMLineItem Tests ---

class TestBOMLineItem:
    def test_valid_creation(self):
        item = make_bom_line_item()
        assert item.monthly_estimate == 50.0

    def test_rejects_empty_line_item(self):
        with pytest.raises(ValidationError):
            make_bom_line_item(line_item="")

    def test_rejects_empty_specification(self):
        with pytest.raises(ValidationError):
            make_bom_line_item(specification="")

    def test_rejects_negative_monthly_estimate(self):
        with pytest.raises(ValidationError):
            make_bom_line_item(monthly_estimate=-1.0)

    def test_allows_zero_monthly_estimate(self):
        item = make_bom_line_item(monthly_estimate=0.0)
        assert item.monthly_estimate == 0.0


# --- BOMTier Tests ---

class TestBOMTier:
    def test_rejects_empty_sections(self):
        with pytest.raises(ValidationError):
            BOMTier(tier_name="Web", tier_number=1, sections=[], subtotal=0.0)

    def test_valid_with_one_section(self):
        section = BOMSection(
            section_name="CDN", section_number="1.1",
            line_items=[make_bom_line_item()], subtotal=50.0,
        )
        tier = BOMTier(tier_name="Web", tier_number=1, sections=[section], subtotal=50.0)
        assert len(tier.sections) == 1


# --- BOMData Tests ---

class TestBOMData:
    def test_valid_creation(self):
        bom = make_bom_data()
        assert bom.total_monthly == 50.0

    def test_rejects_empty_savings_plans(self):
        with pytest.raises(ValidationError):
            make_bom_data(savings_plans=[])

    def test_rejects_empty_service_summary(self):
        with pytest.raises(ValidationError):
            make_bom_data(service_summary=[])


# --- BOMServiceSummary Tests ---

class TestBOMServiceSummary:
    def test_rejects_empty_service(self):
        with pytest.raises(ValidationError):
            BOMServiceSummary(number=1, service="", purpose="CDN", specification="Global")

    def test_rejects_empty_purpose(self):
        with pytest.raises(ValidationError):
            BOMServiceSummary(number=1, service="CF", purpose="", specification="Global")

    def test_rejects_empty_specification(self):
        with pytest.raises(ValidationError):
            BOMServiceSummary(number=1, service="CF", purpose="CDN", specification="")


# --- ReportEnvelope Round-Trip Test ---

class TestReportEnvelope:
    def test_round_trip_serialization(self):
        now = datetime(2025, 1, 15, 12, 0, 0)
        sizing = SizingReportData(
            generated_at=now, nfr_summary=[], service_configs=[],
            node_groups=[make_node_group()], pod_specs=[], hpa_configs=[make_hpa()],
            latency_budget=[], kubernetes_manifests=[], batch_jobs=[],
            cost_optimization=[], container_best_practices=[], network_config=[],
            monitoring_metrics=[],
        )
        bom = make_bom_data()
        meta = ReportMetadata(
            generated_at=now, region="us-east-1", tool_version="1.0",
            llm_model="claude", bedrock_latency_ms=1000,
            input_had_diagram=True, input_had_prompt=True,
        )
        envelope = ReportEnvelope(sizing_report=sizing, bom=bom, metadata=meta)
        json_str = envelope.model_dump_json()
        restored = ReportEnvelope.model_validate_json(json_str)
        assert restored == envelope
