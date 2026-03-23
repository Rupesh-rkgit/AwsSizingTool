"""Pydantic data models for the AWS Infrastructure Sizing Report."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class NFRSummaryItem(BaseModel):
    requirement: str
    target: str


class ConfigParameter(BaseModel):
    parameter: str
    recommendation: str
    rationale: Optional[str] = None


class ServiceConfig(BaseModel):
    """Configuration for a single AWS service (e.g., CloudFront, ALB, EKS)."""
    service_name: str
    parameters: list[ConfigParameter]


class NodeGroupSpec(BaseModel):
    name: str
    instance_type: str = Field(..., min_length=1)
    vcpu: int = Field(..., gt=0)
    memory_gib: float = Field(..., gt=0)
    min_nodes: int
    max_nodes: int
    desired_nodes: int
    capacity_type: str
    disk_size_gib: int
    purpose: str


class PodSpec(BaseModel):
    workload: str
    cpu_request: str
    cpu_limit: str
    memory_request: str
    memory_limit: str
    min_pods: int
    max_pods: int
    scaling_method: str


class HPAConfig(BaseModel):
    target_deployment: str
    min_replicas: int
    max_replicas: int
    cpu_target_percent: int = Field(..., gt=0)
    scale_up_window_seconds: int
    scale_down_window_seconds: int

    @field_validator("max_replicas")
    @classmethod
    def max_replicas_gte_min(cls, v: int, info) -> int:
        min_r = info.data.get("min_replicas")
        if min_r is not None and v < min_r:
            raise ValueError("max_replicas must be >= min_replicas")
        return v


class LatencyBudgetItem(BaseModel):
    component: str = Field(..., min_length=1)
    expected_latency: str = Field(..., min_length=1)
    notes: str


class KubernetesManifest(BaseModel):
    """A Kubernetes YAML snippet (Deployment, HPA, Job, Karpenter NodePool)."""
    kind: str
    name: str
    yaml_content: str


class BatchJobSpec(BaseModel):
    frequency: str
    record_volume: str
    processing_window: str
    throughput_required: str
    parallelism: int = Field(..., ge=1)
    pod_cpu_request: str = Field(..., min_length=1)
    pod_cpu_limit: str = Field(..., min_length=1)
    pod_memory_request: str = Field(..., min_length=1)
    pod_memory_limit: str = Field(..., min_length=1)


class CostOptimizationStrategy(BaseModel):
    strategy: str
    savings_potential: str
    applicable_to: str


class MonitoringMetric(BaseModel):
    metric: str
    target: str
    action_if_exceeded: str


class SizingReportData(BaseModel):
    """Top-level sizing report data model."""
    title: str = "AWS Infrastructure Sizing Recommendations"
    generated_at: datetime
    region: str = "us-east-1"
    nfr_summary: list[NFRSummaryItem]
    service_configs: list[ServiceConfig]
    node_groups: list[NodeGroupSpec]
    pod_specs: list[PodSpec]
    hpa_configs: list[HPAConfig]
    latency_budget: list[LatencyBudgetItem]
    kubernetes_manifests: list[KubernetesManifest]
    batch_jobs: list[BatchJobSpec]
    cost_optimization: list[CostOptimizationStrategy]
    container_best_practices: list[ConfigParameter]
    network_config: list[ConfigParameter]
    monitoring_metrics: list[MonitoringMetric]
