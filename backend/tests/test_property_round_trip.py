"""Property test: Report data round-trip serialization.

Feature: aws-infra-sizing-tool, Property 12: Report data round-trip serialization

Validates: Requirements 10.1, 10.2, 10.3
"""

from datetime import datetime

from hypothesis import given, settings
from hypothesis import strategies as st

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
    BatchJobSpec,
    ConfigParameter,
    CostOptimizationStrategy,
    HPAConfig,
    KubernetesManifest,
    LatencyBudgetItem,
    MonitoringMetric,
    NFRSummaryItem,
    NodeGroupSpec,
    PodSpec,
    ServiceConfig,
    SizingReportData,
)
from backend.services.report_generator import ReportGenerator

# ---------------------------------------------------------------------------
# Reusable primitive strategies
# ---------------------------------------------------------------------------

non_empty_text = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S"),
        whitelist_characters=" -_./",
    ),
)

positive_int = st.integers(min_value=1, max_value=10_000)
positive_float = st.floats(min_value=0.1, max_value=100_000.0, allow_nan=False, allow_infinity=False)
non_negative_float = st.floats(min_value=0.0, max_value=100_000.0, allow_nan=False, allow_infinity=False)
non_negative_int = st.integers(min_value=0, max_value=10_000)

# ---------------------------------------------------------------------------
# Sizing sub-model strategies (reused from test_property_sizing_structural)
# ---------------------------------------------------------------------------

nfr_summary_st = st.builds(
    NFRSummaryItem,
    requirement=non_empty_text,
    target=non_empty_text,
)

config_param_st = st.builds(
    ConfigParameter,
    parameter=non_empty_text,
    recommendation=non_empty_text,
    rationale=st.one_of(st.none(), non_empty_text),
)

service_config_st = st.builds(
    ServiceConfig,
    service_name=non_empty_text,
    parameters=st.lists(config_param_st, min_size=0, max_size=3),
)

node_group_st = st.builds(
    NodeGroupSpec,
    name=non_empty_text,
    instance_type=non_empty_text,
    vcpu=positive_int,
    memory_gib=positive_float,
    min_nodes=non_negative_int,
    max_nodes=non_negative_int,
    desired_nodes=non_negative_int,
    capacity_type=st.sampled_from(["on-demand", "spot"]),
    disk_size_gib=non_negative_int,
    purpose=non_empty_text,
)

pod_spec_st = st.builds(
    PodSpec,
    workload=non_empty_text,
    cpu_request=non_empty_text,
    cpu_limit=non_empty_text,
    memory_request=non_empty_text,
    memory_limit=non_empty_text,
    min_pods=non_negative_int,
    max_pods=non_negative_int,
    scaling_method=non_empty_text,
)


@st.composite
def hpa_config_st(draw):
    min_r = draw(st.integers(min_value=0, max_value=100))
    max_r = draw(st.integers(min_value=min_r, max_value=min_r + 100))
    return HPAConfig(
        target_deployment=draw(non_empty_text),
        min_replicas=min_r,
        max_replicas=max_r,
        cpu_target_percent=draw(positive_int),
        scale_up_window_seconds=draw(non_negative_int),
        scale_down_window_seconds=draw(non_negative_int),
    )


latency_budget_st = st.builds(
    LatencyBudgetItem,
    component=non_empty_text,
    expected_latency=non_empty_text,
    notes=non_empty_text,
)

k8s_manifest_st = st.builds(
    KubernetesManifest,
    kind=st.sampled_from(["Deployment", "HPA", "Job", "NodePool"]),
    name=non_empty_text,
    yaml_content=non_empty_text,
)

batch_job_st = st.builds(
    BatchJobSpec,
    frequency=st.sampled_from(["daily", "monthly", "quarterly", "annual"]),
    record_volume=non_empty_text,
    processing_window=non_empty_text,
    throughput_required=non_empty_text,
    parallelism=st.integers(min_value=1, max_value=100),
    pod_cpu_request=non_empty_text,
    pod_cpu_limit=non_empty_text,
    pod_memory_request=non_empty_text,
    pod_memory_limit=non_empty_text,
)

cost_opt_st = st.builds(
    CostOptimizationStrategy,
    strategy=non_empty_text,
    savings_potential=non_empty_text,
    applicable_to=non_empty_text,
)

monitoring_metric_st = st.builds(
    MonitoringMetric,
    metric=non_empty_text,
    target=non_empty_text,
    action_if_exceeded=non_empty_text,
)

sizing_report_st = st.builds(
    SizingReportData,
    title=non_empty_text,
    generated_at=st.just(datetime(2025, 1, 15, 12, 0, 0)),
    region=st.just("us-east-1"),
    nfr_summary=st.lists(nfr_summary_st, min_size=0, max_size=3),
    service_configs=st.lists(service_config_st, min_size=0, max_size=3),
    node_groups=st.lists(node_group_st, min_size=1, max_size=5),
    pod_specs=st.lists(pod_spec_st, min_size=0, max_size=3),
    hpa_configs=st.lists(hpa_config_st(), min_size=1, max_size=5),
    latency_budget=st.lists(latency_budget_st, min_size=1, max_size=5),
    kubernetes_manifests=st.lists(k8s_manifest_st, min_size=0, max_size=3),
    batch_jobs=st.lists(batch_job_st, min_size=1, max_size=5),
    cost_optimization=st.lists(cost_opt_st, min_size=0, max_size=3),
    container_best_practices=st.lists(config_param_st, min_size=0, max_size=3),
    network_config=st.lists(config_param_st, min_size=0, max_size=3),
    monitoring_metrics=st.lists(monitoring_metric_st, min_size=0, max_size=3),
)

# ---------------------------------------------------------------------------
# BOM sub-model strategies (reused from test_property_bom_structural)
# ---------------------------------------------------------------------------

line_item_st = st.builds(
    BOMLineItem,
    line_item=non_empty_text,
    specification=non_empty_text,
    quantity=non_empty_text,
    unit_price=non_empty_text,
    monthly_estimate=non_negative_float,
)

section_st = st.builds(
    BOMSection,
    section_name=non_empty_text,
    section_number=non_empty_text,
    line_items=st.lists(line_item_st, min_size=1, max_size=5),
    subtotal=non_negative_float,
)

tier_st = st.builds(
    BOMTier,
    tier_name=non_empty_text,
    tier_number=positive_int,
    sections=st.lists(section_st, min_size=1, max_size=4),
    subtotal=non_negative_float,
)

cost_summary_st = st.builds(
    CostSummaryItem,
    category=non_empty_text,
    monthly_estimate=non_negative_float,
)

savings_plan_st = st.builds(
    SavingsPlanScenario,
    scenario=non_empty_text,
    monthly_estimate=non_empty_text,
    annual_estimate=non_empty_text,
    savings_vs_on_demand=non_empty_text,
)

service_summary_st = st.builds(
    BOMServiceSummary,
    number=positive_int,
    service=non_empty_text,
    purpose=non_empty_text,
    specification=non_empty_text,
)

bom_data_st = st.builds(
    BOMData,
    title=non_empty_text,
    generated_at=st.just(datetime(2025, 1, 15, 12, 0, 0)),
    region=st.just("us-east-1"),
    pricing_type=st.just("On-Demand (USD)"),
    tiers=st.lists(tier_st, min_size=1, max_size=4),
    cost_summary=st.lists(cost_summary_st, min_size=0, max_size=3),
    total_monthly=non_negative_float,
    total_annual=non_negative_float,
    savings_plans=st.lists(savings_plan_st, min_size=1, max_size=3),
    service_summary=st.lists(service_summary_st, min_size=1, max_size=5),
    notes=st.lists(non_empty_text, min_size=0, max_size=3),
)

# ---------------------------------------------------------------------------
# ReportMetadata strategy
# ---------------------------------------------------------------------------

report_metadata_st = st.builds(
    ReportMetadata,
    generated_at=st.just(datetime(2025, 1, 15, 12, 0, 0)),
    region=st.just("us-east-1"),
    tool_version=non_empty_text,
    llm_model=non_empty_text,
    bedrock_latency_ms=st.integers(min_value=0, max_value=60_000),
    input_had_diagram=st.booleans(),
    input_had_prompt=st.booleans(),
)

# ---------------------------------------------------------------------------
# ReportEnvelope strategy
# ---------------------------------------------------------------------------

report_envelope_st = st.builds(
    ReportEnvelope,
    sizing_report=sizing_report_st,
    bom=bom_data_st,
    metadata=report_metadata_st,
)


# ---------------------------------------------------------------------------
# Property test
# ---------------------------------------------------------------------------


class TestReportDataRoundTripSerialization:
    """Feature: aws-infra-sizing-tool, Property 12: Report data round-trip serialization"""

    @given(envelope=report_envelope_st)
    @settings(max_examples=100)
    def test_serialize_then_deserialize_equals_original(self, envelope: ReportEnvelope):
        """Serializing to JSON then deserializing back produces an equivalent object.

        **Validates: Requirements 10.1, 10.2, 10.3**
        """
        generator = ReportGenerator()
        json_str = generator.serialize(envelope)
        restored = generator.deserialize(json_str)
        assert restored == envelope
