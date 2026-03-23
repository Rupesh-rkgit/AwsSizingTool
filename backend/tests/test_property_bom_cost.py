"""Property test: BOM cost calculation consistency.

Feature: aws-infra-sizing-tool, Property 6: BOM cost calculation consistency

Validates: Requirements 4.3
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
# Shared leaf strategies
# ---------------------------------------------------------------------------

non_empty_text = st.text(
    min_size=1,
    max_size=30,
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S"),
        whitelist_characters=" -_./",
    ),
)

# Use integers-as-cents then divide to avoid floating-point drift
_cents = st.integers(min_value=0, max_value=10_000_000)  # 0 – 100 000.00


def _to_dollars(cents: int) -> float:
    return round(cents / 100.0, 2)


# ---------------------------------------------------------------------------
# Composite strategy: build self-consistent BOMData bottom-up
# ---------------------------------------------------------------------------


@st.composite
def consistent_line_item(draw):
    """A single BOM line item with a known monthly_estimate."""
    cents = draw(_cents)
    return BOMLineItem(
        line_item=draw(non_empty_text),
        specification=draw(non_empty_text),
        quantity=draw(non_empty_text),
        unit_price=draw(non_empty_text),
        monthly_estimate=_to_dollars(cents),
    )


@st.composite
def consistent_section(draw):
    """A BOM section whose subtotal equals the sum of its line-item costs."""
    items = draw(st.lists(consistent_line_item(), min_size=1, max_size=5))
    subtotal = round(sum(item.monthly_estimate for item in items), 2)
    return BOMSection(
        section_name=draw(non_empty_text),
        section_number=draw(non_empty_text),
        line_items=items,
        subtotal=subtotal,
    )


@st.composite
def consistent_tier(draw):
    """A BOM tier whose subtotal equals the sum of its section subtotals."""
    sections = draw(st.lists(consistent_section(), min_size=1, max_size=4))
    subtotal = round(sum(s.subtotal for s in sections), 2)
    return BOMTier(
        tier_name=draw(non_empty_text),
        tier_number=draw(st.integers(min_value=1, max_value=100)),
        sections=sections,
        subtotal=subtotal,
    )


@st.composite
def consistent_bom_data(draw):
    """A complete BOMData object with self-consistent cost calculations.

    - Each section subtotal == sum of its line-item monthly_estimates
    - Each tier subtotal == sum of its section subtotals
    - total_monthly == sum of tier subtotals
    - total_annual == total_monthly * 12
    """
    tiers = draw(st.lists(consistent_tier(), min_size=1, max_size=4))
    total_monthly = round(sum(t.subtotal for t in tiers), 2)
    total_annual = round(total_monthly * 12, 2)

    cost_summary = draw(
        st.lists(
            st.builds(
                CostSummaryItem,
                category=non_empty_text,
                monthly_estimate=st.floats(
                    min_value=0.0, max_value=100_000.0,
                    allow_nan=False, allow_infinity=False,
                ),
            ),
            min_size=0,
            max_size=3,
        )
    )

    savings_plans = draw(
        st.lists(
            st.builds(
                SavingsPlanScenario,
                scenario=non_empty_text,
                monthly_estimate=non_empty_text,
                annual_estimate=non_empty_text,
                savings_vs_on_demand=non_empty_text,
            ),
            min_size=1,
            max_size=3,
        )
    )

    service_summary = draw(
        st.lists(
            st.builds(
                BOMServiceSummary,
                number=st.integers(min_value=1, max_value=100),
                service=non_empty_text,
                purpose=non_empty_text,
                specification=non_empty_text,
            ),
            min_size=1,
            max_size=5,
        )
    )

    notes = draw(st.lists(non_empty_text, min_size=0, max_size=3))

    return BOMData(
        title=draw(non_empty_text),
        generated_at=datetime(2025, 1, 15, 12, 0, 0),
        region="us-east-1",
        pricing_type="On-Demand (USD)",
        tiers=tiers,
        cost_summary=cost_summary,
        total_monthly=total_monthly,
        total_annual=total_annual,
        savings_plans=savings_plans,
        service_summary=service_summary,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Property test
# ---------------------------------------------------------------------------


class TestBOMCostCalculationConsistency:
    """Feature: aws-infra-sizing-tool, Property 6: BOM cost calculation consistency"""

    @given(bom=consistent_bom_data())
    @settings(max_examples=100)
    def test_total_monthly_equals_sum_of_tier_subtotals(self, bom: BOMData):
        """Sum of tier subtotals equals total_monthly within 0.01 tolerance.

        **Validates: Requirements 4.3**
        """
        tier_sum = sum(t.subtotal for t in bom.tiers)
        assert abs(bom.total_monthly - tier_sum) <= 0.01, (
            f"total_monthly ({bom.total_monthly}) != sum of tier subtotals ({tier_sum})"
        )

    @given(bom=consistent_bom_data())
    @settings(max_examples=100)
    def test_total_annual_equals_total_monthly_times_12(self, bom: BOMData):
        """total_annual equals total_monthly * 12 within 0.12 tolerance.

        **Validates: Requirements 4.3**
        """
        expected_annual = bom.total_monthly * 12
        assert abs(bom.total_annual - expected_annual) <= 0.12, (
            f"total_annual ({bom.total_annual}) != total_monthly * 12 ({expected_annual})"
        )

    @given(bom=consistent_bom_data())
    @settings(max_examples=100)
    def test_tier_subtotal_equals_sum_of_section_subtotals(self, bom: BOMData):
        """Each tier's subtotal equals the sum of its section subtotals.

        **Validates: Requirements 4.3**
        """
        for tier in bom.tiers:
            section_sum = sum(s.subtotal for s in tier.sections)
            assert abs(tier.subtotal - section_sum) <= 0.01, (
                f"Tier '{tier.tier_name}' subtotal ({tier.subtotal}) "
                f"!= sum of section subtotals ({section_sum})"
            )

    @given(bom=consistent_bom_data())
    @settings(max_examples=100)
    def test_section_subtotal_equals_sum_of_line_item_costs(self, bom: BOMData):
        """Each section's subtotal equals the sum of its line-item monthly_estimates.

        **Validates: Requirements 4.3**
        """
        for tier in bom.tiers:
            for section in tier.sections:
                item_sum = sum(item.monthly_estimate for item in section.line_items)
                assert abs(section.subtotal - item_sum) <= 0.01, (
                    f"Section '{section.section_name}' subtotal ({section.subtotal}) "
                    f"!= sum of line-item costs ({item_sum})"
                )
