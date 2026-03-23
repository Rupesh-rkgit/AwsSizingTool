"""Property test: Sizing Markdown contains all report data.

Feature: aws-infra-sizing-tool, Property 7: Sizing Markdown contains all report data

Validates: Requirements 5.1, 10.4
"""

from hypothesis import given, settings

from backend.services.report_generator import ReportGenerator
from backend.models.sizing import SizingReportData
from backend.tests.test_property_sizing_structural import sizing_report_st


class TestSizingMarkdownContainsAllReportData:
    """Feature: aws-infra-sizing-tool, Property 7: Sizing Markdown contains all report data"""

    @given(report=sizing_report_st)
    @settings(max_examples=100)
    def test_markdown_contains_all_node_group_instance_types(self, report: SizingReportData):
        """Every node group's instance_type appears in the rendered Markdown.

        **Validates: Requirements 5.1, 10.4**
        """
        md = ReportGenerator().render_sizing_markdown(report)
        for ng in report.node_groups:
            assert ng.instance_type in md, (
                f"Node group instance_type '{ng.instance_type}' not found in Markdown output"
            )

    @given(report=sizing_report_st)
    @settings(max_examples=100)
    def test_markdown_contains_all_latency_budget_components(self, report: SizingReportData):
        """Every latency budget item's component appears in the rendered Markdown.

        **Validates: Requirements 5.1, 10.4**
        """
        md = ReportGenerator().render_sizing_markdown(report)
        for item in report.latency_budget:
            assert item.component in md, (
                f"Latency budget component '{item.component}' not found in Markdown output"
            )

    @given(report=sizing_report_st)
    @settings(max_examples=100)
    def test_markdown_contains_all_batch_job_frequencies(self, report: SizingReportData):
        """Every batch job's frequency appears in the rendered Markdown.

        **Validates: Requirements 5.1, 10.4**
        """
        md = ReportGenerator().render_sizing_markdown(report)
        for bj in report.batch_jobs:
            assert bj.frequency in md, (
                f"Batch job frequency '{bj.frequency}' not found in Markdown output"
            )

    @given(report=sizing_report_st)
    @settings(max_examples=100)
    def test_markdown_contains_all_hpa_target_deployments(self, report: SizingReportData):
        """Every HPA config's target_deployment appears in the rendered Markdown.

        **Validates: Requirements 5.1, 10.4**
        """
        md = ReportGenerator().render_sizing_markdown(report)
        for hpa in report.hpa_configs:
            assert hpa.target_deployment in md, (
                f"HPA target_deployment '{hpa.target_deployment}' not found in Markdown output"
            )
