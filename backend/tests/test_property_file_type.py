"""Property test: File type validation is exact.

Feature: aws-infra-sizing-tool, Property 1: File type validation is exact

Validates: Requirements 1.1, 1.4
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.services.input_validator import InputValidator

# ---------------------------------------------------------------------------
# Magic-byte constants (must match input_validator.py)
# ---------------------------------------------------------------------------
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"  # 8 bytes
_JPEG_MAGIC = b"\xff\xd8\xff"       # 3 bytes
_WEBP_PREFIX = b"RIFF"              # bytes 0-3
_WEBP_TAG = b"WEBP"                 # bytes 8-11

validator = InputValidator()

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Minimum padding so the file is at least 12 bytes (validator rejects < 12)
_MIN_PADDING = 4


def _png_bytes() -> st.SearchStrategy[bytes]:
    """Generate bytes starting with PNG magic, padded to >= 12 bytes."""
    return st.binary(min_size=_MIN_PADDING).map(lambda tail: _PNG_MAGIC + tail)


def _jpeg_bytes() -> st.SearchStrategy[bytes]:
    """Generate bytes starting with JPEG magic, padded to >= 12 bytes."""
    return st.binary(min_size=max(12 - len(_JPEG_MAGIC), 0)).map(
        lambda tail: _JPEG_MAGIC + tail
    )


def _webp_bytes() -> st.SearchStrategy[bytes]:
    """Generate bytes with RIFF at 0-3 and WEBP at 8-11."""
    # bytes 4-7 are arbitrary (file size field in RIFF), bytes 12+ are payload
    return st.tuples(
        st.binary(min_size=4, max_size=4),  # bytes 4-7
        st.binary(min_size=0, max_size=64),  # bytes 12+
    ).map(lambda parts: _WEBP_PREFIX + parts[0] + _WEBP_TAG + parts[1])


def _valid_image_bytes() -> st.SearchStrategy[bytes]:
    """Generate bytes that should be accepted (PNG, JPEG, or WEBP)."""
    return st.one_of(_png_bytes(), _jpeg_bytes(), _webp_bytes())


def _non_magic_bytes() -> st.SearchStrategy[bytes]:
    """Generate random bytes (>= 12) that do NOT start with any known magic."""
    return st.binary(min_size=12, max_size=256).filter(
        lambda b: (
            b[:8] != _PNG_MAGIC
            and b[:3] != _JPEG_MAGIC
            and not (b[:4] == _WEBP_PREFIX and b[8:12] == _WEBP_TAG)
        )
    )


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


class TestFileTypeValidationIsExact:
    """Property 1: File type validation is exact."""

    @given(data=_png_bytes())
    @settings(max_examples=100)
    def test_png_magic_accepted(self, data: bytes) -> None:
        """Any file starting with PNG magic bytes is accepted as image/png."""
        result = validator.validate_file_type(data)
        assert result == "image/png", f"Expected image/png, got {result}"

    @given(data=_jpeg_bytes())
    @settings(max_examples=100)
    def test_jpeg_magic_accepted(self, data: bytes) -> None:
        """Any file starting with JPEG magic bytes is accepted as image/jpeg."""
        result = validator.validate_file_type(data)
        assert result == "image/jpeg", f"Expected image/jpeg, got {result}"

    @given(data=_webp_bytes())
    @settings(max_examples=100)
    def test_webp_magic_accepted(self, data: bytes) -> None:
        """Any file with RIFF+WEBP magic bytes is accepted as image/webp."""
        result = validator.validate_file_type(data)
        assert result == "image/webp", f"Expected image/webp, got {result}"

    @given(data=_valid_image_bytes())
    @settings(max_examples=100)
    def test_valid_formats_always_accepted(self, data: bytes) -> None:
        """Any file with PNG, JPEG, or WEBP magic bytes returns a non-None media type."""
        result = validator.validate_file_type(data)
        assert result in {"image/png", "image/jpeg", "image/webp"}, (
            f"Valid magic bytes should be accepted, got {result}"
        )

    @given(data=_non_magic_bytes())
    @settings(max_examples=100)
    def test_non_magic_bytes_rejected(self, data: bytes) -> None:
        """Any file >= 12 bytes without known magic bytes is rejected (returns None)."""
        result = validator.validate_file_type(data)
        assert result is None, (
            f"Non-magic bytes should be rejected, got {result}"
        )

    @given(data=st.binary(min_size=0, max_size=11))
    @settings(max_examples=100)
    def test_short_bytes_rejected(self, data: bytes) -> None:
        """Any file shorter than 12 bytes is rejected (returns None)."""
        result = validator.validate_file_type(data)
        assert result is None, (
            f"Short file (<12 bytes) should be rejected, got {result}"
        )
