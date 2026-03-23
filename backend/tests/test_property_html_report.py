"""Property test: HTML report contains both sections with TOC.

Feature: aws-infra-sizing-tool, Property 9: HTML report contains both sections with TOC

Validates: Requirements 5.3, 5.4
"""

from hypothesis import given, settings

from backend.services.report_generator import ReportGenerator
from backend.tests.test_property_round_trip import report_envelope_st

# All TOC anchor IDs that must appear as section ids in the HTML
TOC_ANCHOR_IDS = [
    "nfr-summary",
    "service-configs",
    "node-groups",
    "pod-specs",
    "hpa-configs",
    "latency-budget",
    "kubernetes-manifests",
    "batch-jobs",
    "cost-optimization",
    "container-best-practices",
    "network-config",
    "monitoring-metrics",
    "bom-tiers",
    "cost-summary",
    "savings-plans",
    "service-summary",
    "notes",
]


class TestHTMLReportContainsBothSectionsWithTOC:
    """Feature: aws-infra-sizing-tool, Property 9: HTML report contains both sections with TOC"""

    @given(envelope=report_envelope_st)
    @settings(max_examples=100)
    def test_all_toc_anchor_ids_exist_as_section_ids(self, envelope):
        """Every TOC anchor ID exists as a section id in the rendered HTML.

        **Validates: Requirements 5.3, 5.4**
        """
        generator = ReportGenerator()
        html = generator.render_html_report(envelope.sizing_report, envelope.bom)

        for anchor_id in TOC_ANCHOR_IDS:
            assert f'id="{anchor_id}"' in html, (
                f"TOC anchor id '{anchor_id}' not found as a section id in the HTML"
            )

    @given(envelope=report_envelope_st)
    @settings(max_examples=100)
    def test_both_section_css_classes_present(self, envelope):
        """Both 'section-infra' and 'section-bom' CSS classes appear in the HTML.

        **Validates: Requirements 5.3, 5.4**
        """
        generator = ReportGenerator()
        html = generator.render_html_report(envelope.sizing_report, envelope.bom)

        assert "section-infra" in html, "CSS class 'section-infra' not found in HTML"
        assert "section-bom" in html, "CSS class 'section-bom' not found in HTML"

    @given(envelope=report_envelope_st)
    @settings(max_examples=100)
    def test_well_formed_html_structure(self, envelope):
        """HTML starts with '<!DOCTYPE html>' and ends with '</html>'.

        **Validates: Requirements 5.3, 5.4**
        """
        generator = ReportGenerator()
        html = generator.render_html_report(envelope.sizing_report, envelope.bom)

        assert html.strip().startswith("<!DOCTYPE html>"), (
            "HTML does not start with '<!DOCTYPE html>'"
        )
        assert html.strip().endswith("</html>"), (
            "HTML does not end with '</html>'"
        )
