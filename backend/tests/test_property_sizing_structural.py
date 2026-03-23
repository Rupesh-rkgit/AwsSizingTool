"""Property test: SizingReportData structural completeness.

Feature: aws-infra-sizing-tool, Property 4: SizingReportData structural completeness

Validates: Requirements 3.4, 3.5, 3.6, 3.7
"""

from datetime import datetime

from hypothesis import given, settings
from hypothesis import strategies as st

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

# ---------------------------------------------------------------------------
# Hypothesis strategies for each sub-model
# ---------------------------------------------------------------------------

non_empty_text = st.text(min_size=1, max_size=50, alphabet=st.characters(
    whitelist_categories=("L", "N", "P", "S"),
    whitelist_characters=" -_./",
))

positive_int = st.integers(min_value=1, max_value=10_000)
positive_float = st.floats(min_value=0.1, max_value=100_000.0, allow_nan=False, allow_infinity=False)
non_negative_int = st.integers(min_value=0, max_value=10_000)

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
# Property test
# ---------------------------------------------------------------------------


class TestSizingReportDataStructuralCompleteness:
    """Feature: aws-infra-sizing-tool, Property 4: SizingReportData structural completeness"""

    @given(report=sizing_report_st)
    @settings(max_examples=100)
    def test_node_groups_have_valid_specs(self, report: SizingReportData):
        """Every node group has non-empty instance_type, vcpu > 0, memory_gib > 0.

        **Validates: Requirements 3.4**
        """
        for ng in report.node_groups:
            assert len(ng.instance_type) > 0, "instance_type must be non-empty"
            assert ng.vcpu > 0, "vcpu must be > 0"
            assert ng.memory_gib > 0, "memory_gib must be > 0"

    @given(report=sizing_report_st)
    @settings(max_examples=100)
    def test_latency_budget_items_have_required_fields(self, report: SizingReportData):
        """Every latency budget item has non-empty component and expected_latency.

        **Validates: Requirements 3.5**
        """
        for item in report.latency_budget:
            assert len(item.component) > 0, "component must be non-empty"
            assert len(item.expected_latency) > 0, "expected_latency must be non-empty"

    @given(report=sizing_report_st)
    @settings(max_examples=100)
    def test_batch_jobs_have_valid_specs(self, report: SizingReportData):
        """Every batch job has parallelism >= 1 and non-empty pod resource fields.

        **Validates: Requirements 3.6**
        """
        for bj in report.batch_jobs:
            assert bj.parallelism >= 1, "parallelism must be >= 1"
            assert len(bj.pod_cpu_request) > 0, "pod_cpu_request must be non-empty"
            assert len(bj.pod_cpu_limit) > 0, "pod_cpu_limit must be non-empty"
            assert len(bj.pod_memory_request) > 0, "pod_memory_request must be non-empty"
            assert len(bj.pod_memory_limit) > 0, "pod_memory_limit must be non-empty"

    @given(report=sizing_report_st)
    @settings(max_examples=100)
    def test_hpa_configs_have_valid_constraints(self, report: SizingReportData):
        """Every HPA config has min_replicas <= max_replicas and cpu_target_percent > 0.

        **Validates: Requirements 3.7**
        """
        for hpa in report.hpa_configs:
            assert hpa.min_replicas <= hpa.max_replicas, (
                f"min_replicas ({hpa.min_replicas}) must be <= max_replicas ({hpa.max_replicas})"
            )
            assert hpa.cpu_target_percent > 0, "cpu_target_percent must be > 0"
