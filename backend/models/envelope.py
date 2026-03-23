"""Pydantic data models for the combined report envelope."""

from datetime import datetime

from pydantic import BaseModel

from backend.models.bom import BOMData
from backend.models.sizing import SizingReportData


class ReportMetadata(BaseModel):
    generated_at: datetime
    region: str
    tool_version: str
    llm_model: str
    bedrock_latency_ms: int
    input_had_diagram: bool
    input_had_prompt: bool


class ReportEnvelope(BaseModel):
    """The complete JSON intermediate format wrapping both reports."""
    sizing_report: SizingReportData
    bom: BOMData
    metadata: ReportMetadata
