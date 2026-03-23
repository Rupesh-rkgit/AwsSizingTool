"""Property test: File size validation rejects oversized files.

Feature: aws-infra-sizing-tool, Property 2: File size validation rejects oversized files

Validates: Requirements 1.3
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.services.input_validator import InputValidator, MAX_FILE_SIZE_BYTES

validator = InputValidator()

# 20 MB boundary in bytes
_MAX_SIZE = MAX_FILE_SIZE_BYTES  # 20,971,520


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

def _small_sizes() -> st.SearchStrategy[int]:
    """Sizes well below the limit (0 to 1 MB)."""
    return st.integers(min_value=0, max_value=1 * 1024 * 1024)


def _boundary_sizes() -> st.SearchStrategy[int]:
    """Sizes around the 20 MB boundary (±1024 bytes)."""
    return st.integers(min_value=_MAX_SIZE - 1024, max_value=_MAX_SIZE + 1024)


def _over_limit_sizes() -> st.SearchStrategy[int]:
    """Sizes above the limit (20 MB + 1 to 25 MB)."""
    return st.integers(min_value=_MAX_SIZE + 1, max_value=25 * 1024 * 1024)


def _any_size() -> st.SearchStrategy[int]:
    """Sizes from 0 to 25 MB, biased toward the boundary."""
    return st.one_of(
        _small_sizes(),
        _boundary_sizes(),
        _over_limit_sizes(),
        st.integers(min_value=0, max_value=25 * 1024 * 1024),
    )


def _make_bytes(size: int) -> bytes:
    """Create a bytes object of exactly *size* bytes.

    For sizes up to ~1 MB we allocate real bytes.  For larger sizes we use
    ``bytes(size)`` which is a zero-filled buffer — cheap to allocate and
    ``len()`` returns the correct value, which is all ``validate_file_size``
    inspects.
    """
    return bytes(size)


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


class TestFileSizeValidationRejectsOversizedFiles:
    """Property 2: File size validation rejects oversized files."""

    @given(size=_any_size())
    @settings(max_examples=100)
    def test_accept_iff_within_limit(self, size: int) -> None:
        """validate_file_size accepts if and only if size <= 20 MB."""
        file_bytes = _make_bytes(size)
        result = validator.validate_file_size(file_bytes)
        if size <= _MAX_SIZE:
            assert result is True, (
                f"File of {size} bytes should be accepted (limit {_MAX_SIZE})"
            )
        else:
            assert result is False, (
                f"File of {size} bytes should be rejected (limit {_MAX_SIZE})"
            )

    @given(size=_small_sizes())
    @settings(max_examples=100)
    def test_small_files_always_accepted(self, size: int) -> None:
        """Files well below 20 MB are always accepted."""
        file_bytes = _make_bytes(size)
        assert validator.validate_file_size(file_bytes) is True

    @given(size=_over_limit_sizes())
    @settings(max_examples=100)
    def test_oversized_files_always_rejected(self, size: int) -> None:
        """Files above 20 MB are always rejected."""
        file_bytes = _make_bytes(size)
        assert validator.validate_file_size(file_bytes) is False

    @given(size=_boundary_sizes())
    @settings(max_examples=100)
    def test_boundary_region_correct(self, size: int) -> None:
        """Files around the exact 20 MB boundary are handled correctly."""
        file_bytes = _make_bytes(size)
        result = validator.validate_file_size(file_bytes)
        expected = size <= _MAX_SIZE
        assert result is expected, (
            f"Boundary: size={size}, expected={expected}, got={result}"
        )

    def test_exact_limit_accepted(self) -> None:
        """A file of exactly 20 MB (20,971,520 bytes) is accepted."""
        file_bytes = _make_bytes(_MAX_SIZE)
        assert validator.validate_file_size(file_bytes) is True

    def test_one_byte_over_rejected(self) -> None:
        """A file of 20 MB + 1 byte is rejected."""
        file_bytes = _make_bytes(_MAX_SIZE + 1)
        assert validator.validate_file_size(file_bytes) is False
