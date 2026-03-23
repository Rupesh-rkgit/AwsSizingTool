"""SizingEngine orchestrator.

Receives validated inputs, builds prompts via PromptBuilder, calls
BedrockClient, and parses the LLM response into SizingReportData and
BOMData Pydantic models.  Includes retry logic for parse failures and
detection of unrecognizable-diagram errors.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from backend.models.bom import BOMData
from backend.models.sizing import SizingReportData
from backend.services.bedrock_client import BedrockClient
from backend.services.prompt_builder import PromptBuilder
from backend.services.aws_enrichment import AWSEnrichmentService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class SizingEngineError(Exception):
    """Base exception for SizingEngine failures."""


class LLMParseError(SizingEngineError):
    """Raised when the LLM response cannot be parsed into valid models."""


class DiagramUnrecognizableError(SizingEngineError):
    """Raised when the LLM reports it cannot interpret the diagram."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_PARSE_RETRIES = 2

_CORRECTIVE_PROMPT = (
    "Your previous response could not be parsed. The error was:\n\n"
    "{error}\n\n"
    "Please respond again with ONLY a valid JSON object containing "
    "exactly two top-level keys: `sizing_report` and `bom`, conforming "
    "to the schemas described in your instructions. "
    "Do NOT include any text outside the JSON object."
)

# ---------------------------------------------------------------------------
# SizingEngine
# ---------------------------------------------------------------------------


class SizingEngine:
    """Orchestrates the end-to-end sizing analysis pipeline.

    Parameters
    ----------
    bedrock_client:
        A configured ``BedrockClient`` instance for calling the LLM.
    prompt_builder:
        A ``PromptBuilder`` instance for constructing system/user prompts.
    enrichment_service:
        An optional ``AWSEnrichmentService`` for real-time pricing/docs.
    """

    def __init__(
        self,
        bedrock_client: BedrockClient,
        prompt_builder: PromptBuilder,
        enrichment_service: AWSEnrichmentService | None = None,
    ) -> None:
        self._bedrock = bedrock_client
        self._prompt_builder = prompt_builder
        self._enrichment = enrichment_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        image_bytes: bytes | None = None,
        image_media_type: str | None = None,
        prompt_text: str | None = None,
        region: str = "us-east-1",
    ) -> tuple[SizingReportData, BOMData]:
        """Run the full sizing analysis and return parsed models.

        Parameters
        ----------
        image_bytes:
            Raw bytes of the architecture diagram, or ``None``.
        image_media_type:
            MIME type of the image (e.g. ``"image/png"``), or ``None``.
        prompt_text:
            Free-form NFR / volumetric text, or ``None``.
        region:
            AWS region for pricing context (default ``"us-east-1"``).

        Returns
        -------
        tuple[SizingReportData, BOMData]

        Raises
        ------
        DiagramUnrecognizableError
            If the LLM indicates the diagram cannot be interpreted.
        LLMParseError
            If the LLM response cannot be parsed after retries.
        SizingEngineError
            For other unexpected failures.
        """
        system_prompt = self._prompt_builder.build_system_prompt(region)
        user_message = self._prompt_builder.build_user_message(
            prompt_text, has_image=image_bytes is not None
        )

        # Enrich with real-time AWS pricing and documentation
        enrichment_context = ""
        if self._enrichment:
            try:
                enrichment_context = self._enrichment.enrich(prompt_text, region)
                if enrichment_context:
                    logger.info("Enrichment context added (%d chars)", len(enrichment_context))
                    system_prompt = self._prompt_builder.build_system_prompt(
                        region, enrichment_context=enrichment_context
                    )
            except Exception as exc:
                # Enrichment is best-effort — don't fail the request
                logger.warning("Enrichment failed, proceeding without: %s", exc)

        # First attempt
        raw_response = self._bedrock.analyze(
            system_prompt, user_message, image_bytes, image_media_type
        )

        last_error: str = ""
        for attempt in range(1 + MAX_PARSE_RETRIES):  # initial + retries
            try:
                sizing, bom = self._parse_response(raw_response)
                self._check_unrecognizable_diagram(sizing)
                return sizing, bom
            except DiagramUnrecognizableError:
                # Don't retry — this is a semantic signal, not a parse error
                raise
            except (json.JSONDecodeError, ValidationError, KeyError, TypeError) as exc:
                last_error = str(exc)
                logger.warning(
                    "Parse attempt %d/%d failed: %s",
                    attempt + 1,
                    1 + MAX_PARSE_RETRIES,
                    last_error,
                )
                if attempt < MAX_PARSE_RETRIES:
                    # Retry with corrective prompt
                    corrective = _CORRECTIVE_PROMPT.format(error=last_error)
                    raw_response = self._bedrock.analyze(
                        system_prompt, corrective, image_bytes, image_media_type
                    )

        raise LLMParseError(
            "Could not parse LLM response into valid report models after "
            f"{1 + MAX_PARSE_RETRIES} attempts. Last error: {last_error}"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(raw: str) -> tuple[SizingReportData, BOMData]:
        """Parse the raw LLM text into Pydantic models.

        The LLM is expected to return a JSON object with ``sizing_report``
        and ``bom`` top-level keys.
        """
        # Strip potential markdown fences the LLM might add
        text = raw.strip()
        if text.startswith("```"):
            # Remove opening fence (```json or ```)
            first_newline = text.index("\n")
            text = text[first_newline + 1 :]
        if text.endswith("```"):
            text = text[: -3]
        text = text.strip()

        data: dict[str, Any] = json.loads(text)

        sizing_raw = data["sizing_report"]
        bom_raw = data["bom"]

        sizing = SizingReportData.model_validate(sizing_raw)
        bom = BOMData.model_validate(bom_raw)

        return sizing, bom

    @staticmethod
    def _check_unrecognizable_diagram(sizing: SizingReportData) -> None:
        """Raise if the LLM flagged the diagram as unrecognizable.

        The system prompt instructs the LLM to set ``nfr_summary`` to a
        single entry with ``requirement == "error"`` when the diagram
        cannot be interpreted.
        """
        if sizing.nfr_summary and len(sizing.nfr_summary) == 1:
            entry = sizing.nfr_summary[0]
            if entry.requirement.lower() == "error":
                raise DiagramUnrecognizableError(
                    f"Diagram analysis incomplete: {entry.target}"
                )
