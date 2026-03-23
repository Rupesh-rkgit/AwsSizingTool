"""Property test: BOMData structural completeness.

Feature: aws-infra-sizing-tool, Property 5: BOMData structural completeness

Validates: Requirements 4.1, 4.2, 4.4, 4.5
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

# ---------------------------------------------------------------------------
# Hypothesis strategies for each sub-model
# ---------------------------------------------------------------------------

non_empty_text = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S"),
        whitelist_characters=" -_./",
    ),
)

non_negative_float = st.floats(
    min_value=0.0, max_value=100_000.0, allow_nan=False, allow_infinity=False
)

positive_float = st.floats(
    min_value=0.01, max_value=100_000.0, allow_nan=False, allow_infinity=False
)

positive_int = st.integers(min_value=1, max_value=10_000)

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
# Property test
# ---------------------------------------------------------------------------


class TestBOMDataStructuralCompleteness:
    """Feature: aws-infra-sizing-tool, Property 5: BOMData structural completeness"""

    @given(bom=bom_data_st)
    @settings(max_examples=100)
    def test_line_items_have_required_fields(self, bom: BOMData):
        """Every line item has non-empty line_item, specification, quantity,
        unit_price, and monthly_estimate >= 0.

        **Validates: Requirements 4.1**
        """
        for tier in bom.tiers:
            for section in tier.sections:
                for item in section.line_items:
                    assert len(item.line_item) > 0, "line_item must be non-empty"
                    assert len(item.specification) > 0, "specification must be non-empty"
                    assert len(item.quantity) > 0, "quantity must be non-empty"
                    assert len(item.unit_price) > 0, "unit_price must be non-empty"
                    assert item.monthly_estimate >= 0, "monthly_estimate must be >= 0"

    @given(bom=bom_data_st)
    @settings(max_examples=100)
    def test_every_tier_has_at_least_one_section(self, bom: BOMData):
        """Every tier must contain at least one section.

        **Validates: Requirements 4.2**
        """
        for tier in bom.tiers:
            assert len(tier.sections) >= 1, (
                f"Tier '{tier.tier_name}' must have at least one section"
            )

    @given(bom=bom_data_st)
    @settings(max_examples=100)
    def test_savings_plans_is_non_empty(self, bom: BOMData):
        """The savings_plans list must be non-empty.

        **Validates: Requirements 4.4**
        """
        assert len(bom.savings_plans) >= 1, "savings_plans must be non-empty"

    @given(bom=bom_data_st)
    @settings(max_examples=100)
    def test_service_summary_entries_have_required_fields(self, bom: BOMData):
        """service_summary entries have non-empty service, purpose, specification.

        **Validates: Requirements 4.5**
        """
        assert len(bom.service_summary) >= 1, "service_summary must be non-empty"
        for entry in bom.service_summary:
            assert len(entry.service) > 0, "service must be non-empty"
            assert len(entry.purpose) > 0, "purpose must be non-empty"
            assert len(entry.specification) > 0, "specification must be non-empty"
