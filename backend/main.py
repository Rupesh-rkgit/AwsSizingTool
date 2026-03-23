"""AWS Infrastructure Sizing Tool - FastAPI Backend.

Provides the POST /api/analyze endpoint that wires together:
InputValidator → SizingEngine → ReportGenerator → DatabaseManager.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Load .env file (sets AWS_BEARER_TOKEN_BEDROCK etc.) before any boto3 usage.
# override=True ensures .env always wins over any stale shell-level env vars.
load_dotenv(Path(__file__).parent / ".env", override=True)
from datetime import datetime, timezone
from typing import AsyncIterator
from uuid import uuid4

import botocore.exceptions

from fastapi import FastAPI, File, Form, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import load_settings
from backend.models.envelope import ReportEnvelope, ReportMetadata
from backend.services.bedrock_client import BedrockClient
from backend.services.database import DatabaseManager
from backend.services.input_validator import InputValidator
from backend.services.prompt_builder import PromptBuilder
from backend.services.report_generator import ReportGenerator
from backend.services.aws_enrichment import AWSEnrichmentService
from backend.services.sizing_engine import (
    DiagramUnrecognizableError,
    LLMParseError,
    SizingEngine,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Application-level singletons (populated during lifespan startup)
# ---------------------------------------------------------------------------
_settings = None
_input_validator: InputValidator | None = None
_sizing_engine: SizingEngine | None = None
_report_generator: ReportGenerator | None = None
_db_manager: DatabaseManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialise services on startup and tear down on shutdown."""
    global _settings, _input_validator, _sizing_engine, _report_generator, _db_manager

    _settings = load_settings()

    # Services
    bedrock_client = BedrockClient(_settings.bedrock)
    prompt_builder = PromptBuilder()
    enrichment_service = None
    if _settings.app.enable_enrichment:
        enrichment_service = AWSEnrichmentService(
            region=_settings.app.default_pricing_region,
            timeout_seconds=_settings.app.enrichment_timeout_seconds,
            max_pricing_results=_settings.app.enrichment_max_pricing_results,
        )

    _input_validator = InputValidator()
    _sizing_engine = SizingEngine(bedrock_client, prompt_builder, enrichment_service)
    _report_generator = ReportGenerator()
    _db_manager = DatabaseManager(_settings.database.path)
    await _db_manager.init_db()

    yield

    # Shutdown
    if _db_manager is not None:
        await _db_manager.close()


app = FastAPI(title="AWS Infrastructure Sizing Tool", lifespan=lifespan)

# CORS — origins are configured via settings; added after app creation so
# the middleware is always present even before lifespan runs.
# We use a permissive default here; the real origins come from config.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# POST /api/analyze
# ---------------------------------------------------------------------------


@app.post("/api/analyze")
async def analyze(
    diagram: UploadFile | None = File(default=None),
    nfr_doc: UploadFile | None = File(default=None),
    prompt: str | None = Form(default=None),
    region: str = Form(default="us-east-1"),
) -> JSONResponse:
    """Analyse an architecture diagram, NFR document, and/or text prompt.

    Returns sizing report, BOM, HTML report, and JSON intermediate data.
    """
    assert _input_validator is not None
    assert _sizing_engine is not None
    assert _report_generator is not None
    assert _db_manager is not None
    assert _settings is not None

    session_id = str(uuid4())
    file_bytes: bytes | None = None
    filename: str | None = None
    nfr_doc_bytes: bytes | None = None
    nfr_doc_filename: str | None = None

    # --- Read uploaded diagram (if any) ---
    if diagram is not None and diagram.filename:
        file_bytes = await diagram.read()
        filename = diagram.filename

    # --- Read uploaded NFR document (if any) ---
    if nfr_doc is not None and nfr_doc.filename:
        nfr_doc_bytes = await nfr_doc.read()
        nfr_doc_filename = nfr_doc.filename

    # --- Input validation ---
    is_valid, errors = _input_validator.validate(
        file_bytes, filename, prompt,
        nfr_doc_bytes=nfr_doc_bytes,
        nfr_doc_filename=nfr_doc_filename,
    )
    if not is_valid:
        first_error = errors[0]
        return JSONResponse(
            status_code=400,
            content={
                "error": first_error["error"],
                "details": first_error.get("details", []),
            },
        )

    # Determine media type for valid images
    image_media_type: str | None = None
    if file_bytes:
        image_media_type = _input_validator.validate_file_type(file_bytes)

    # Combine NFR doc content with prompt text
    combined_prompt = prompt
    if nfr_doc_bytes:
        nfr_text = nfr_doc_bytes.decode("utf-8")
        if combined_prompt:
            combined_prompt = f"{combined_prompt}\n\n--- NFR Document ({nfr_doc_filename}) ---\n\n{nfr_text}"
        else:
            combined_prompt = f"--- NFR Document ({nfr_doc_filename}) ---\n\n{nfr_text}"

    # --- Create pending session in DB ---
    had_diagram = file_bytes is not None and len(file_bytes) > 0
    await _db_manager.create_session(
        session_id=session_id,
        prompt_text=combined_prompt,
        region=region,
        had_diagram=had_diagram,
        diagram_filename=filename,
        bedrock_model_id=_settings.bedrock.model_id,
    )

    # --- Run sizing analysis ---
    try:
        import time

        start_ts = time.monotonic()
        sizing_data, bom_data = await asyncio.to_thread(
            _sizing_engine.analyze,
            image_bytes=file_bytes,
            image_media_type=image_media_type,
            prompt_text=combined_prompt,
            region=region,
        )
        elapsed_ms = int((time.monotonic() - start_ts) * 1000)

    except DiagramUnrecognizableError as exc:
        await _db_manager.delete_session(session_id)
        return JSONResponse(
            status_code=422,
            content={
                "error": "Diagram analysis incomplete",
                "details": [str(exc)],
            },
        )

    except LLMParseError as exc:
        await _db_manager.delete_session(session_id)
        return JSONResponse(
            status_code=422,
            content={
                "error": "Could not generate report",
                "details": [
                    "The AI response could not be parsed into a valid report. "
                    "Please try rephrasing your prompt."
                ],
            },
        )

    except Exception as exc:
        # Use isinstance checks against actual botocore classes — more reliable
        # than comparing __name__ strings which can silently break on refactors.
        if isinstance(exc, botocore.exceptions.ReadTimeoutError):
            await _db_manager.delete_session(session_id)
            return JSONResponse(
                status_code=504,
                content={
                    "error": "Analysis timed out",
                    "details": [
                        "The Bedrock service took too long to respond. Please try again."
                    ],
                },
            )

        if isinstance(exc, (botocore.exceptions.NoCredentialsError, botocore.exceptions.PartialCredentialsError)):
            await _db_manager.delete_session(session_id)
            return JSONResponse(
                status_code=502,
                content={
                    "error": "AWS credentials not configured",
                    "details": [
                        "No valid AWS credentials were found. "
                        "Configure AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY or an IAM role."
                    ],
                },
            )

        if isinstance(exc, botocore.exceptions.ClientError):
            await _db_manager.delete_session(session_id)
            error_code = exc.response.get("Error", {}).get("Code", "Unknown")  # type: ignore[attr-defined]
            return JSONResponse(
                status_code=502,
                content={
                    "error": "Bedrock service error",
                    "details": [f"{error_code}: {exc}"],
                },
            )

        if isinstance(exc, botocore.exceptions.BotoCoreError):
            await _db_manager.delete_session(session_id)
            return JSONResponse(
                status_code=502,
                content={
                    "error": "AWS service error",
                    "details": [str(exc)],
                },
            )

        # Catch-all 500
        logger.exception("Unexpected error during analysis")
        await _db_manager.delete_session(session_id)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal error",
                "details": ["An unexpected error occurred. Check server logs for details."],
            },
        )

    # --- Generate reports ---
    generated_at = datetime.now(timezone.utc)

    sizing_report_md = _report_generator.render_sizing_markdown(sizing_data)
    bom_md = _report_generator.render_bom_markdown(bom_data)
    html_report = _report_generator.render_html_report(sizing_data, bom_data)

    envelope = ReportEnvelope(
        sizing_report=sizing_data,
        bom=bom_data,
        metadata=ReportMetadata(
            generated_at=generated_at,
            region=region,
            tool_version="1.0.0",
            llm_model=_settings.bedrock.model_id,
            bedrock_latency_ms=elapsed_ms,
            input_had_diagram=had_diagram,
            input_had_prompt=combined_prompt is not None and combined_prompt.strip() != "",
        ),
    )
    report_data_json = _report_generator.serialize(envelope)

    # --- Persist report and update session ---
    report_id = str(uuid4())
    await _db_manager.store_report(
        report_id=report_id,
        session_id=session_id,
        sizing_report_md=sizing_report_md,
        bom_md=bom_md,
        html_report=html_report,
        report_data_json=report_data_json,
    )
    await _db_manager.update_session_status(
        session_id,
        status="completed",
        total_monthly_cost=bom_data.total_monthly,
        bedrock_latency_ms=elapsed_ms,
    )

    return JSONResponse(
        status_code=200,
        content={
            "session_id": session_id,
            "sizing_report_md": sizing_report_md,
            "bom_md": bom_md,
            "html_report": html_report,
            "report_data_json": report_data_json,
            "generated_at": generated_at.isoformat(),
        },
    )


# ---------------------------------------------------------------------------
# GET /api/sessions — paginated session list
# ---------------------------------------------------------------------------


@app.get("/api/sessions")
async def list_sessions(
    page: int = 1,
    per_page: int = 20,
) -> JSONResponse:
    """Return a paginated list of past analysis sessions."""
    assert _db_manager is not None

    sessions, total = await _db_manager.list_sessions(page=page, per_page=per_page)

    items = []
    for s in sessions:
        prompt_text = s.get("prompt_text") or ""
        items.append({
            "id": s["id"],
            "created_at": s["created_at"],
            "prompt_snippet": prompt_text[:100],
            "region": s["region"],
            "had_diagram": s["had_diagram"],
            "total_monthly_cost": s["total_monthly_cost"],
        })

    return JSONResponse(
        status_code=200,
        content={
            "sessions": items,
            "total": total,
            "page": page,
            "per_page": per_page,
        },
    )


# ---------------------------------------------------------------------------
# GET /api/sessions/{id} — full session with report artifacts
# ---------------------------------------------------------------------------


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> JSONResponse:
    """Return full report artifacts for a past session."""
    assert _db_manager is not None

    session = await _db_manager.get_session(session_id)
    if session is None:
        return JSONResponse(
            status_code=404,
            content={"error": "Session not found"},
        )

    report = await _db_manager.get_report(session_id)

    return JSONResponse(
        status_code=200,
        content={
            "session_id": session["id"],
            "sizing_report_md": report["sizing_report_md"] if report else None,
            "bom_md": report["bom_md"] if report else None,
            "html_report": report["html_report"] if report else None,
            "report_data_json": report["report_data_json"] if report else None,
            "generated_at": session["created_at"],
        },
    )


# ---------------------------------------------------------------------------
# DELETE /api/sessions/{id} — delete a session
# ---------------------------------------------------------------------------


@app.delete("/api/sessions/{session_id}", response_model=None)
async def delete_session(session_id: str):
    """Delete a session and its reports. Returns 204 on success, 404 if not found."""
    assert _db_manager is not None

    deleted = await _db_manager.delete_session(session_id)
    if not deleted:
        return JSONResponse(
            status_code=404,
            content={"error": "Session not found"},
        )

    return Response(status_code=204)
