"""Unit tests for PromptBuilder."""

from backend.services.prompt_builder import PromptBuilder


class TestBuildSystemPrompt:
    def setup_method(self):
        self.builder = PromptBuilder()

    def test_default_region_is_us_east_1(self):
        prompt = self.builder.build_system_prompt()
        assert "us-east-1" in prompt

    def test_custom_region_appears_in_prompt(self):
        prompt = self.builder.build_system_prompt(region="eu-west-1")
        assert "eu-west-1" in prompt
        # The default region should NOT appear when overridden
        assert "us-east-1" not in prompt

    def test_contains_sizing_report_schema(self):
        prompt = self.builder.build_system_prompt()
        assert "sizing_report" in prompt
        assert "node_groups" in prompt
        assert "hpa_configs" in prompt
        assert "latency_budget" in prompt
        assert "batch_jobs" in prompt
        assert "kubernetes_manifests" in prompt

    def test_contains_bom_schema(self):
        prompt = self.builder.build_system_prompt()
        assert '"bom"' in prompt or "`bom`" in prompt
        assert "tiers" in prompt
        assert "savings_plans" in prompt
        assert "service_summary" in prompt
        assert "total_monthly" in prompt
        assert "total_annual" in prompt

    def test_contains_pricing_context(self):
        prompt = self.builder.build_system_prompt()
        assert "pricing" in prompt.lower()

    def test_contains_kubernetes_yaml_instructions(self):
        prompt = self.builder.build_system_prompt()
        assert "Kubernetes" in prompt
        assert "YAML" in prompt

    def test_contains_unrecognizable_diagram_handling(self):
        prompt = self.builder.build_system_prompt()
        assert "unrecognizable" in prompt.lower() or "not an AWS architecture" in prompt

    def test_instructs_json_only_output(self):
        prompt = self.builder.build_system_prompt()
        assert "JSON" in prompt


class TestBuildUserMessage:
    def setup_method(self):
        self.builder = PromptBuilder()

    def test_with_both_image_and_text(self):
        msg = self.builder.build_user_message("My NFRs: 100ms latency", has_image=True)
        assert "architecture diagram" in msg.lower()
        assert "My NFRs: 100ms latency" in msg

    def test_with_text_only(self):
        msg = self.builder.build_user_message("Scale to 10k RPS", has_image=False)
        assert "Scale to 10k RPS" in msg
        assert "diagram" not in msg.lower()

    def test_with_image_only(self):
        msg = self.builder.build_user_message(None, has_image=True)
        assert "architecture diagram" in msg.lower()

    def test_with_neither_input(self):
        """Defensive case — validator should prevent this, but builder handles it."""
        msg = self.builder.build_user_message(None, has_image=False)
        assert len(msg) > 0

    def test_with_empty_string_prompt(self):
        """Empty string is falsy, treated same as None."""
        msg = self.builder.build_user_message("", has_image=True)
        assert "architecture diagram" in msg.lower()

    def test_always_requests_json_generation(self):
        msg = self.builder.build_user_message("test", has_image=False)
        assert "JSON" in msg or "json" in msg.lower()
