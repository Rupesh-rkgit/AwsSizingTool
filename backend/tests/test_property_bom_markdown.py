"""Property test: BOM Markdown contains all cost data.

Feature: aws-infra-sizing-tool, Property 8: BOM Markdown contains all cost data

Validates: Requirements 5.2
"""

from hypothesis import given, settings

from backend.models.bom import BOMData
from backend.services.report_generator import ReportGenerator
from backend.tests.test_property_bom_structural import bom_data_st


class TestBOMMarkdownContainsAllCostData:
    """Feature: aws-infra-sizing-tool, Property 8: BOM Markdown contains all cost data"""

    @given(data=bom_data_st)
    @settings(max_examples=100)
    def test_bom_markdown_contains_all_cost_data(self, data: BOMData):
        """Rendered BOM Markdown contains every tier's tier_name, every
        section's section_name, and the formatted total_monthly value.

        **Validates: Requirements 5.2**
        """
        renderer = ReportGenerator()
        md = renderer.render_bom_markdown(data)

        # Every tier name must appear in the output
        for tier in data.tiers:
            assert tier.tier_name in md, (
                f"Tier name '{tier.tier_name}' not found in rendered Markdown"
            )

            # Every section name within each tier must appear
            for section in tier.sections:
                assert section.section_name in md, (
                    f"Section name '{section.section_name}' not found in rendered Markdown"
                )

        # The formatted total monthly cost must appear
        expected_total = f"${data.total_monthly:,.2f}"
        assert expected_total in md, (
            f"Formatted total_monthly '{expected_total}' not found in rendered Markdown"
        )
