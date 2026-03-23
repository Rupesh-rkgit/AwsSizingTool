"""Property test: Input combination validation requires at least one input.

Feature: aws-infra-sizing-tool, Property 3: Input combination validation requires at least one input

Validates: Requirements 2.2, 2.3, 9.1
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.services.input_validator import InputValidator


class TestInputCombinationValidation:
    """Property 3: Input combination validation requires at least one input.

    For any combination of (has_diagram: bool, has_prompt: bool), the
    InputValidator accepts the submission if and only if at least one of
    has_diagram or has_prompt is true.  The combination (False, False)
    must be rejected.
    """

    @given(has_diagram=st.booleans(), has_prompt=st.booleans())
    @settings(max_examples=100)
    def test_accepts_iff_at_least_one_input(
        self, has_diagram: bool, has_prompt: bool
    ) -> None:
        """validate_inputs returns True iff at least one input is present."""
        result = InputValidator.validate_inputs(has_diagram, has_prompt)
        expected = has_diagram or has_prompt
        assert result == expected, (
            f"validate_inputs({has_diagram}, {has_prompt}) returned {result}, "
            f"expected {expected}"
        )
