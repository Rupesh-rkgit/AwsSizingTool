"""Constructs system and user prompts for the Bedrock Converse API.

The system prompt instructs the LLM to output structured JSON conforming to
the SizingReportData and BOMData Pydantic schemas.  The user message combines
the caller-supplied text prompt with an image reference (when present).
"""

from __future__ import annotations


class PromptBuilder:
    """Builds the system prompt and user message sent to Bedrock."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_system_prompt(
        self,
        region: str = "us-east-1",
        enrichment_context: str | None = None,
    ) -> str:
        """Return the system prompt that instructs the LLM on output format.

        Parameters
        ----------
        region:
            AWS region used for pricing context (default ``us-east-1``).
        enrichment_context:
            Optional real-time AWS pricing/docs data to inject into the prompt.
        """
        base = _SYSTEM_PROMPT_TEMPLATE.format(region=region)
        if enrichment_context:
            base += "\n\n" + enrichment_context
        return base

    def build_user_message(
        self,
        prompt_text: str | None,
        has_image: bool,
    ) -> str:
        """Return the user message combining text and image context.

        Parameters
        ----------
        prompt_text:
            Free-form NFR / volumetric text supplied by the user, or *None*.
        has_image:
            Whether an architecture diagram image accompanies this request.
            The actual image bytes are attached separately by ``BedrockClient``.
        """
        parts: list[str] = []

        if has_image:
            parts.append(
                "I have attached an AWS architecture diagram. "
                "Analyze the diagram to identify all AWS services, "
                "their relationships, and the overall topology."
            )

        if prompt_text:
            parts.append(
                "Here are my non-functional requirements and volumetric details:\n\n"
                + prompt_text
            )

        if not parts:
            # Defensive — the input validator should prevent this.
            parts.append("Please provide general AWS infrastructure sizing guidance.")

        parts.append(
            "\nBased on the above, generate the complete JSON output "
            "with both `sizing_report` and `bom` objects as described "
            "in your instructions."
        )

        return "\n\n".join(parts)


# ------------------------------------------------------------------
# System prompt template
# ------------------------------------------------------------------

_SYSTEM_PROMPT_TEMPLATE = """\
You are an expert AWS Solutions Architect specializing in infrastructure \
sizing, cost estimation, and Kubernetes workload planning.

Your task is to analyze the provided architecture diagram and/or \
non-functional requirements (NFRs) / volumetric details and produce a \
comprehensive AWS infrastructure sizing recommendation together with a \
Bill of Materials (BOM).

## Output Format

You MUST respond with a single JSON object containing exactly two top-level \
keys: `sizing_report` and `bom`.  Do NOT include any text outside the JSON \
object — no preamble, no explanation, no markdown fences.

### `sizing_report` schema

```
{{
  "title": "AWS Infrastructure Sizing Recommendations",
  "generated_at": "<ISO 8601 timestamp>",
  "region": "{region}",
  "nfr_summary": [
    {{ "requirement": "<string>", "target": "<string>" }}
  ],
  "service_configs": [
    {{
      "service_name": "<string>",
      "parameters": [
        {{ "parameter": "<string>", "recommendation": "<string>", "rationale": "<string or null>" }}
      ]
    }}
  ],
  "node_groups": [
    {{
      "name": "<string>",
      "instance_type": "<e.g. c6i.xlarge>",
      "vcpu": <int>,
      "memory_gib": <float>,
      "min_nodes": <int>,
      "max_nodes": <int>,
      "desired_nodes": <int>,
      "capacity_type": "<on-demand | spot>",
      "disk_size_gib": <int>,
      "purpose": "<string>"
    }}
  ],
  "pod_specs": [
    {{
      "workload": "<string>",
      "cpu_request": "<e.g. 500m>",
      "cpu_limit": "<e.g. 1000m>",
      "memory_request": "<e.g. 512Mi>",
      "memory_limit": "<e.g. 1536Mi>",
      "min_pods": <int>,
      "max_pods": <int>,
      "scaling_method": "<e.g. HPA (CPU 50%)>"
    }}
  ],
  "hpa_configs": [
    {{
      "target_deployment": "<string>",
      "min_replicas": <int>,
      "max_replicas": <int>,
      "cpu_target_percent": <int, must be > 0>,
      "scale_up_window_seconds": <int>,
      "scale_down_window_seconds": <int>
    }}
  ],
  "latency_budget": [
    {{ "component": "<string>", "expected_latency": "<string>", "notes": "<string>" }}
  ],
  "kubernetes_manifests": [
    {{
      "kind": "<Deployment | HPA | Job | NodePool>",
      "name": "<string>",
      "yaml_content": "<valid YAML string>"
    }}
  ],
  "batch_jobs": [
    {{
      "frequency": "<daily | monthly | quarterly | annual>",
      "record_volume": "<string>",
      "processing_window": "<string>",
      "throughput_required": "<string>",
      "parallelism": <int, >= 1>,
      "pod_cpu_request": "<string>",
      "pod_cpu_limit": "<string>",
      "pod_memory_request": "<string>",
      "pod_memory_limit": "<string>"
    }}
  ],
  "cost_optimization": [
    {{ "strategy": "<string>", "savings_potential": "<string>", "applicable_to": "<string>" }}
  ],
  "container_best_practices": [
    {{ "parameter": "<string>", "recommendation": "<string>", "rationale": "<string or null>" }}
  ],
  "network_config": [
    {{ "parameter": "<string>", "recommendation": "<string>", "rationale": "<string or null>" }}
  ],
  "monitoring_metrics": [
    {{ "metric": "<string>", "target": "<string>", "action_if_exceeded": "<string>" }}
  ]
}}
```

### `bom` schema

```
{{
  "title": "AWS Infrastructure \\u2013 Bill of Materials (BOM)",
  "generated_at": "<ISO 8601 timestamp>",
  "region": "{region}",
  "pricing_type": "On-Demand (USD)",
  "tiers": [
    {{
      "tier_name": "<e.g. Web Application Tier>",
      "tier_number": <int>,
      "sections": [
        {{
          "section_name": "<e.g. Amazon CloudFront (CDN)>",
          "section_number": "<e.g. 1.1>",
          "line_items": [
            {{
              "line_item": "<string>",
              "specification": "<string>",
              "quantity": "<string>",
              "unit_price": "<string>",
              "monthly_estimate": <float, >= 0>
            }}
          ],
          "subtotal": <float>
        }}
      ],
      "subtotal": <float>
    }}
  ],
  "cost_summary": [
    {{ "category": "<string>", "monthly_estimate": <float> }}
  ],
  "total_monthly": <float>,
  "total_annual": <float>,
  "savings_plans": [
    {{
      "scenario": "<string>",
      "monthly_estimate": "<string>",
      "annual_estimate": "<string>",
      "savings_vs_on_demand": "<string>"
    }}
  ],
  "service_summary": [
    {{
      "number": <int>,
      "service": "<string>",
      "purpose": "<string>",
      "specification": "<string>"
    }}
  ],
  "notes": ["<string>"]
}}
```

## AWS Pricing Context

- Use **{region}** on-demand pricing (USD).
- When real-time pricing data is provided below, you MUST use those exact \
prices instead of your training data. Real-time data is always more accurate.
- Reference current AWS public pricing for common services: EC2, EKS, \
CloudFront, ALB, NAT Gateway, RDS, ElastiCache, S3, CloudWatch, etc.
- When exact pricing is unavailable from real-time data or your knowledge, \
provide reasonable estimates and note the assumption.
- Include Savings Plan and Reserved Instance scenarios in the BOM \
`savings_plans` array.

## Kubernetes YAML Snippets

Where applicable, include Kubernetes YAML manifests in the \
`kubernetes_manifests` array for:
- Deployments (with resource requests/limits)
- HorizontalPodAutoscalers
- Kubernetes Jobs (for batch workloads)
- Karpenter NodePool specs (if Karpenter is appropriate)

Each manifest's `yaml_content` field must contain valid YAML.

## Important Rules

1. Ensure `hpa_configs` entries have `min_replicas <= max_replicas` and \
`cpu_target_percent > 0`.
2. Ensure every `node_groups` entry has a non-empty `instance_type`, \
`vcpu > 0`, and `memory_gib > 0`.
3. Ensure every `batch_jobs` entry has `parallelism >= 1` and non-empty \
pod resource request/limit strings.
4. Ensure every `latency_budget` entry has non-empty `component` and \
`expected_latency`.
5. Ensure BOM `total_annual` equals `total_monthly * 12`.
6. Ensure each tier `subtotal` equals the sum of its section subtotals, \
and `total_monthly` equals the sum of all tier subtotals.
7. The `savings_plans` list must contain at least one scenario.
8. The `service_summary` list must contain at least one entry with \
non-empty `service`, `purpose`, and `specification`.

## Unrecognizable Diagram Handling

If the provided image is not an AWS architecture diagram or cannot be \
meaningfully interpreted, set the `sizing_report.nfr_summary` to a single \
entry with `requirement` = "error" and `target` describing what could not \
be interpreted.  Still produce a best-effort BOM if any textual requirements \
were provided.

Respond ONLY with the JSON object.\
"""
