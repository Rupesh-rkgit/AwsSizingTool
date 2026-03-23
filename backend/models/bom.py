"""Pydantic data models for the AWS Bill of Materials (BOM)."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class BOMLineItem(BaseModel):
    line_item: str = Field(..., min_length=1)
    specification: str = Field(..., min_length=1)
    quantity: str = Field(..., min_length=1)
    unit_price: str = Field(..., min_length=1)
    monthly_estimate: float = Field(..., ge=0)


class BOMSection(BaseModel):
    section_name: str
    section_number: str
    line_items: list[BOMLineItem]
    subtotal: float


class BOMTier(BaseModel):
    tier_name: str
    tier_number: int
    sections: list[BOMSection] = Field(..., min_length=1)
    subtotal: float


class CostSummaryItem(BaseModel):
    category: str
    monthly_estimate: float


class SavingsPlanScenario(BaseModel):
    scenario: str
    monthly_estimate: str
    annual_estimate: str
    savings_vs_on_demand: str


class BOMServiceSummary(BaseModel):
    number: int
    service: str = Field(..., min_length=1)
    purpose: str = Field(..., min_length=1)
    specification: str = Field(..., min_length=1)


class BOMData(BaseModel):
    """Top-level BOM data model."""
    title: str = "AWS Infrastructure – Bill of Materials (BOM)"
    generated_at: datetime
    region: str = "us-east-1"
    pricing_type: str = "On-Demand (USD)"
    tiers: list[BOMTier]
    cost_summary: list[CostSummaryItem]
    total_monthly: float
    total_annual: float
    savings_plans: list[SavingsPlanScenario] = Field(..., min_length=1)
    service_summary: list[BOMServiceSummary] = Field(..., min_length=1)
    notes: list[str]
