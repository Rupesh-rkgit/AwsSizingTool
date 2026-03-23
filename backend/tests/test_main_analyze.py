"""Tests for POST /api/analyze endpoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

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
    NFRSummaryItem,
    NodeGroupSpec,
    SizingReportData,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sizing_data() -> SizingReportData:
    return SizingReportData(
        title="Test Sizing",
        generated_at=datetime(2025, 1, 15, tzinfo=timezone.utc),
        region="us-east-1",
        nfr_summary=[NFRSummaryItem(requirement="Latency", target="<200ms")],
        service_configs=[],
        node_groups=[
            NodeGroupSpec(
                name="web", instance_type="c6i.xlarge", vcpu=4,
                memory_gib=8.0, min_nodes=2, max_nodes=10, desired_nodes=3,
                capacity_type="on-demand", disk_size_gib=50, purpose="Web tier",
            )
        ],
        pod_specs=[], hpa_configs=[], latency_budget=[],
        kubernetes_manifests=[], batch_jobs=[], cost_optimization=[],
        container_best_practices=[], network_config=[], monitoring_metrics=[],
    )


def _make_bom_data() -> BOMData:
    return BOMData(
        title="Test BOM",
        generated_at=datetime(2025, 1, 15, tzinfo=timezone.utc),
        region="us-east-1", pricing_type="On-Demand (USD)",
        tiers=[BOMTier(
            tier_name="Web Tier", tier_number=1,
            sections=[BOMSection(
                section_name="EC2", section_number="1.1",
                line_items=[BOMLineItem(
                    line_item="c6i.xlarge", specification="4 vCPU, 8 GiB",
                    quantity="3", unit_price="$0.17/hr", monthly_estimate=367.20,
                )],
                subtotal=367.20,
            )],
            subtotal=367.20,
        )],
        cost_summary=[CostSummaryItem(category="Compute", monthly_estimate=367.20)],
        total_monthly=367.20, total_annual=4406.40,
        savings_plans=[SavingsPlanScenario(
            scenario="1yr", monthly_estimate="$280",
            annual_estimate="$3360", savings_vs_on_demand="24%",
        )],
        service_summary=[BOMServiceSummary(
            number=1, service="EC2", purpose="Compute", specification="c6i.xlarge",
        )],
        notes=["Prices are estimates"],
    )


_VALID_PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx"
    b"\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00"
    b"\x00\x00\x00IEND\xaeB`\x82"
)


# ---------------------------------------------------------------------------
# Fixture: build a TestClient with a no-op lifespan and mocked services
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """TestClient with all backend services mocked out."""
    import backend.main as main_mod

    # Replace the lifespan with a no-op so it doesn't touch real DB / config
    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    original_lifespan = main_mod.app.router.lifespan_context
    main_mod.app.router.lifespan_context = _noop_lifespan

    # Inject mock singletons
    mock_settings = MagicMock()
    mock_settings.bedrock.model_id = "test-model"

    main_mod._settings = mock_settings
    main_mod._input_validator = MagicMock()
    main_mod._sizing_engine = MagicMock()
    main_mod._report_generator = MagicMock()
    main_mod._db_manager = MagicMock()
    main_mod._db_manager.create_session = AsyncMock()
    main_mod._db_manager.update_session_status = AsyncMock()
    main_mod._db_manager.store_report = AsyncMock()

    with TestClient(main_mod.app, raise_server_exceptions=False) as c:
        yield c, main_mod

    # Restore
    main_mod.app.router.lifespan_context = original_lifespan


# ---------------------------------------------------------------------------
# Tests: Validation errors → 400
# ---------------------------------------------------------------------------


class TestValidationErrors:

    def test_no_inputs_returns_400(self, client):
        c, mod = client
        mod._input_validator.validate.return_value = (
            False,
            [{"error": "No input provided", "details": ["Provide at least a diagram or text prompt"]}],
        )
        resp = c.post("/api/analyze")
        assert resp.status_code == 400
        assert resp.json()["error"] == "No input provided"

    def test_invalid_file_type_returns_400(self, client):
        c, mod = client
        mod._input_validator.validate.return_value = (
            False,
            [{"error": "Invalid file format", "details": ["Supported formats: PNG, JPG, JPEG, WEBP"]}],
        )
        resp = c.post(
            "/api/analyze",
            files={"diagram": ("test.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
        assert resp.status_code == 400
        assert "Invalid file format" in resp.json()["error"]

    def test_file_too_large_returns_400(self, client):
        c, mod = client
        mod._input_validator.validate.return_value = (
            False,
            [{"error": "File too large", "details": ["Maximum file size: 20 MB"]}],
        )
        resp = c.post(
            "/api/analyze",
            files={"diagram": ("big.png", b"x" * 100, "image/png")},
        )
        assert resp.status_code == 400
        assert "File too large" in resp.json()["error"]


# ---------------------------------------------------------------------------
# Tests: Sizing engine errors → 422, 502, 504, 500
# ---------------------------------------------------------------------------


class TestSizingEngineErrors:

    def _setup_valid_input(self, mod):
        mod._input_validator.validate.return_value = (True, [])
        mod._input_validator.validate_file_type.return_value = "image/png"

    def test_diagram_unrecognizable_returns_422(self, client):
        c, mod = client
        self._setup_valid_input(mod)
        from backend.services.sizing_engine import DiagramUnrecognizableError
        mod._sizing_engine.analyze.side_effect = DiagramUnrecognizableError("Could not interpret")
        resp = c.post("/api/analyze", files={"diagram": ("arch.png", _VALID_PNG, "image/png")})
        assert resp.status_code == 422
        assert "Diagram analysis incomplete" in resp.json()["error"]

    def test_llm_parse_error_returns_422(self, client):
        c, mod = client
        self._setup_valid_input(mod)
        from backend.services.sizing_engine import LLMParseError
        mod._sizing_engine.analyze.side_effect = LLMParseError("parse failed")
        resp = c.post("/api/analyze", data={"prompt": "Size my infra"})
        assert resp.status_code == 422
        assert "Could not generate report" in resp.json()["error"]

    def test_read_timeout_returns_504(self, client):
        c, mod = client
        self._setup_valid_input(mod)

        class ReadTimeoutError(Exception):
            pass

        mod._sizing_engine.analyze.side_effect = ReadTimeoutError("timed out")
        resp = c.post("/api/analyze", data={"prompt": "Size my infra"})
        assert resp.status_code == 504
        assert "Analysis timed out" in resp.json()["error"]

    def test_client_error_returns_502(self, client):
        c, mod = client
        self._setup_valid_input(mod)

        class ClientError(Exception):
            pass

        mod._sizing_engine.analyze.side_effect = ClientError("Rate limit")
        resp = c.post("/api/analyze", data={"prompt": "Size my infra"})
        assert resp.status_code == 502
        assert "Bedrock service unavailable" in resp.json()["error"]

    def test_unexpected_error_returns_500(self, client):
        c, mod = client
        self._setup_valid_input(mod)
        mod._sizing_engine.analyze.side_effect = RuntimeError("boom")
        resp = c.post("/api/analyze", data={"prompt": "Size my infra"})
        assert resp.status_code == 500
        assert "Internal error" in resp.json()["error"]


# ---------------------------------------------------------------------------
# Tests: Successful analysis → 200
# ---------------------------------------------------------------------------


class TestSuccessfulAnalysis:

    def _setup_success(self, mod):
        mod._input_validator.validate.return_value = (True, [])
        mod._input_validator.validate_file_type.return_value = "image/png"
        mod._sizing_engine.analyze.return_value = (_make_sizing_data(), _make_bom_data())
        mod._report_generator.render_sizing_markdown.return_value = "# Sizing MD"
        mod._report_generator.render_bom_markdown.return_value = "# BOM MD"
        mod._report_generator.render_html_report.return_value = "<html>report</html>"
        mod._report_generator.serialize.return_value = '{"test": "json"}'

    def test_prompt_only_returns_200(self, client):
        c, mod = client
        self._setup_success(mod)
        resp = c.post("/api/analyze", data={"prompt": "Size my infra"})
        assert resp.status_code == 200
        body = resp.json()
        assert "session_id" in body
        assert body["sizing_report_md"] == "# Sizing MD"
        assert body["bom_md"] == "# BOM MD"
        assert body["html_report"] == "<html>report</html>"
        assert body["report_data_json"] == '{"test": "json"}'
        assert "generated_at" in body

    def test_diagram_only_returns_200(self, client):
        c, mod = client
        self._setup_success(mod)
        resp = c.post("/api/analyze", files={"diagram": ("arch.png", _VALID_PNG, "image/png")})
        assert resp.status_code == 200
        assert "session_id" in resp.json()

    def test_both_inputs_returns_200(self, client):
        c, mod = client
        self._setup_success(mod)
        resp = c.post(
            "/api/analyze",
            files={"diagram": ("arch.png", _VALID_PNG, "image/png")},
            data={"prompt": "Size my infra", "region": "eu-west-1"},
        )
        assert resp.status_code == 200

    def test_session_stored_in_db(self, client):
        c, mod = client
        self._setup_success(mod)
        resp = c.post("/api/analyze", data={"prompt": "test"})
        assert resp.status_code == 200
        mod._db_manager.create_session.assert_called_once()
        mod._db_manager.store_report.assert_called_once()
        mod._db_manager.update_session_status.assert_called_once()

    def test_failed_session_stored_with_error(self, client):
        c, mod = client
        mod._input_validator.validate.return_value = (True, [])
        mod._input_validator.validate_file_type.return_value = None
        mod._sizing_engine.analyze.side_effect = RuntimeError("boom")
        resp = c.post("/api/analyze", data={"prompt": "test"})
        assert resp.status_code == 500
        mod._db_manager.create_session.assert_called_once()
        mod._db_manager.update_session_status.assert_called_once()
        call_args = mod._db_manager.update_session_status.call_args
        assert call_args[1].get("status") == "failed" or "failed" in str(call_args)
