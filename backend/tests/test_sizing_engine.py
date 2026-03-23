"""Unit tests for the SizingEngine orchestrator.

All tests use a mocked BedrockClient so no real AWS calls are made.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from backend.services.prompt_builder import PromptBuilder
from backend.services.sizing_engine import (
    DiagramUnrecognizableError,
    LLMParseError,
    SizingEngine,
    SizingEngineError,
)


# ---------------------------------------------------------------------------
# Helpers – minimal valid JSON payloads
# ---------------------------------------------------------------------------

def _minimal_sizing_report() -> dict:
    return {
        "title": "AWS Infrastructure Sizing Recommendations",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "region": "us-east-1",
        "nfr_summary": [{"requirement": "Throughput", "target": "1000 rps"}],
        "service_configs": [],
        "node_groups": [],
        "pod_specs": [],
        "hpa_configs": [],
        "latency_budget": [],
        "kubernetes_manifests": [],
        "batch_jobs": [],
        "cost_optimization": [],
        "container_best_practices": [],
        "network_config": [],
        "monitoring_metrics": [],
    }


def _minimal_bom() -> dict:
    return {
        "title": "AWS Infrastructure – Bill of Materials (BOM)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "region": "us-east-1",
        "pricing_type": "On-Demand (USD)",
        "tiers": [
            {
                "tier_name": "Web Tier",
                "tier_number": 1,
                "sections": [
                    {
                        "section_name": "CloudFront",
                        "section_number": "1.1",
                        "line_items": [
                            {
                                "line_item": "Data Transfer",
                                "specification": "1 TB/month",
                                "quantity": "1",
                                "unit_price": "$0.085/GB",
                                "monthly_estimate": 85.0,
                            }
                        ],
                        "subtotal": 85.0,
                    }
                ],
                "subtotal": 85.0,
            }
        ],
        "cost_summary": [{"category": "Web Tier", "monthly_estimate": 85.0}],
        "total_monthly": 85.0,
        "total_annual": 1020.0,
        "savings_plans": [
            {
                "scenario": "1-Year No Upfront",
                "monthly_estimate": "$70.00",
                "annual_estimate": "$840.00",
                "savings_vs_on_demand": "17%",
            }
        ],
        "service_summary": [
            {
                "number": 1,
                "service": "CloudFront",
                "purpose": "CDN",
                "specification": "1 TB/month",
            }
        ],
        "notes": ["Prices are estimates."],
    }


def _build_llm_response(sizing: dict | None = None, bom: dict | None = None) -> str:
    """Return a JSON string mimicking the LLM output."""
    payload = {
        "sizing_report": sizing or _minimal_sizing_report(),
        "bom": bom or _minimal_bom(),
    }
    return json.dumps(payload)


def _make_engine(llm_responses: list[str] | str) -> SizingEngine:
    """Create a SizingEngine with a mocked BedrockClient."""
    mock_bedrock = MagicMock()
    if isinstance(llm_responses, str):
        mock_bedrock.analyze.return_value = llm_responses
    else:
        mock_bedrock.analyze.side_effect = llm_responses
    prompt_builder = PromptBuilder()
    return SizingEngine(bedrock_client=mock_bedrock, prompt_builder=prompt_builder)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSizingEngineHappyPath:
    """Verify the normal orchestration flow."""

    def test_analyze_returns_valid_models(self):
        engine = _make_engine(_build_llm_response())
        sizing, bom = engine.analyze(prompt_text="1000 rps web app")

        assert sizing.title == "AWS Infrastructure Sizing Recommendations"
        assert bom.total_monthly == 85.0

    def test_analyze_with_image(self):
        engine = _make_engine(_build_llm_response())
        sizing, bom = engine.analyze(
            image_bytes=b"\x89PNG",
            image_media_type="image/png",
            prompt_text="Analyze this diagram",
        )
        assert sizing is not None
        assert bom is not None

    def test_analyze_passes_region_to_prompt_builder(self):
        engine = _make_engine(_build_llm_response())
        engine.analyze(prompt_text="test", region="eu-west-1")
        # The bedrock mock was called; we just verify no error
        assert engine._bedrock.analyze.called

    def test_analyze_strips_markdown_fences(self):
        raw = "```json\n" + _build_llm_response() + "\n```"
        engine = _make_engine(raw)
        sizing, bom = engine.analyze(prompt_text="test")
        assert sizing is not None
        assert bom is not None


class TestSizingEngineRetryLogic:
    """Verify retry behaviour on parse failures."""

    def test_retries_on_invalid_json_then_succeeds(self):
        """First response is garbage, second is valid."""
        responses = [
            "This is not JSON at all",
            _build_llm_response(),
        ]
        engine = _make_engine(responses)
        sizing, bom = engine.analyze(prompt_text="test")
        assert sizing is not None
        assert bom is not None
        # Should have called bedrock twice (initial + 1 retry)
        assert engine._bedrock.analyze.call_count == 2

    def test_retries_on_missing_key_then_succeeds(self):
        """First response is valid JSON but missing 'bom' key."""
        bad_response = json.dumps({"sizing_report": _minimal_sizing_report()})
        responses = [bad_response, _build_llm_response()]
        engine = _make_engine(responses)
        sizing, bom = engine.analyze(prompt_text="test")
        assert bom is not None
        assert engine._bedrock.analyze.call_count == 2

    def test_retries_on_validation_error_then_succeeds(self):
        """First response has invalid model data, second is valid."""
        bad_sizing = _minimal_sizing_report()
        bad_sizing["nfr_summary"] = "not a list"  # will fail Pydantic validation
        bad_response = _build_llm_response(sizing=bad_sizing)
        responses = [bad_response, _build_llm_response()]
        engine = _make_engine(responses)
        sizing, bom = engine.analyze(prompt_text="test")
        assert sizing is not None
        assert engine._bedrock.analyze.call_count == 2

    def test_raises_after_all_retries_exhausted(self):
        """All 3 attempts (initial + 2 retries) return garbage."""
        responses = ["bad1", "bad2", "bad3"]
        engine = _make_engine(responses)
        with pytest.raises(LLMParseError, match="Could not parse"):
            engine.analyze(prompt_text="test")
        assert engine._bedrock.analyze.call_count == 3

    def test_second_retry_succeeds(self):
        """First two responses fail, third succeeds."""
        responses = ["bad1", "bad2", _build_llm_response()]
        engine = _make_engine(responses)
        sizing, bom = engine.analyze(prompt_text="test")
        assert sizing is not None
        assert engine._bedrock.analyze.call_count == 3


class TestSizingEngineDiagramUnrecognizable:
    """Verify unrecognizable diagram detection."""

    def test_raises_on_error_nfr_summary(self):
        sizing = _minimal_sizing_report()
        sizing["nfr_summary"] = [
            {"requirement": "error", "target": "Could not interpret the uploaded image"}
        ]
        response = _build_llm_response(sizing=sizing)
        engine = _make_engine(response)
        with pytest.raises(DiagramUnrecognizableError, match="Could not interpret"):
            engine.analyze(image_bytes=b"\x89PNG", image_media_type="image/png")

    def test_does_not_raise_when_nfr_has_multiple_entries(self):
        """Error detection only triggers when there is exactly one entry."""
        sizing = _minimal_sizing_report()
        sizing["nfr_summary"] = [
            {"requirement": "error", "target": "something"},
            {"requirement": "Throughput", "target": "1000 rps"},
        ]
        response = _build_llm_response(sizing=sizing)
        engine = _make_engine(response)
        result_sizing, _ = engine.analyze(prompt_text="test")
        assert len(result_sizing.nfr_summary) == 2

    def test_does_not_retry_on_diagram_error(self):
        """DiagramUnrecognizableError should NOT trigger retries."""
        sizing = _minimal_sizing_report()
        sizing["nfr_summary"] = [
            {"requirement": "error", "target": "Not an architecture diagram"}
        ]
        response = _build_llm_response(sizing=sizing)
        engine = _make_engine(response)
        with pytest.raises(DiagramUnrecognizableError):
            engine.analyze(image_bytes=b"\x89PNG", image_media_type="image/png")
        # Only one call — no retries
        assert engine._bedrock.analyze.call_count == 1


class TestSizingEngineExceptions:
    """Verify exception hierarchy."""

    def test_llm_parse_error_is_sizing_engine_error(self):
        assert issubclass(LLMParseError, SizingEngineError)

    def test_diagram_unrecognizable_is_sizing_engine_error(self):
        assert issubclass(DiagramUnrecognizableError, SizingEngineError)
