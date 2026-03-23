"""Unit tests for InputValidator."""

import pytest

from backend.services.input_validator import InputValidator, MAX_FILE_SIZE_BYTES

# ---------------------------------------------------------------------------
# Helpers – minimal valid image headers
# ---------------------------------------------------------------------------

def _png_header() -> bytes:
    """Return minimal bytes that pass PNG magic-byte check."""
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 4


def _jpeg_header() -> bytes:
    return b"\xff\xd8\xff\xe0" + b"\x00" * 8


def _webp_header() -> bytes:
    # RIFF....WEBP
    return b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP"


def _pdf_header() -> bytes:
    return b"%PDF-1.4" + b"\x00" * 4


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

validator = InputValidator()


class TestValidateFileType:
    def test_accepts_png(self):
        assert validator.validate_file_type(_png_header()) == "image/png"

    def test_accepts_jpeg(self):
        assert validator.validate_file_type(_jpeg_header()) == "image/jpeg"

    def test_accepts_webp(self):
        assert validator.validate_file_type(_webp_header()) == "image/webp"

    def test_rejects_pdf(self):
        assert validator.validate_file_type(_pdf_header()) is None

    def test_rejects_random_bytes(self):
        assert validator.validate_file_type(b"\x00\x01\x02\x03" * 4) is None

    def test_rejects_too_short(self):
        assert validator.validate_file_type(b"\x89PNG") is None


class TestValidateFileSize:
    def test_accepts_small_file(self):
        assert validator.validate_file_size(b"\x00" * 100) is True

    def test_accepts_exact_limit(self):
        assert validator.validate_file_size(b"\x00" * MAX_FILE_SIZE_BYTES) is True

    def test_rejects_one_byte_over(self):
        assert validator.validate_file_size(b"\x00" * (MAX_FILE_SIZE_BYTES + 1)) is False

    def test_accepts_empty(self):
        assert validator.validate_file_size(b"") is True


class TestValidateInputs:
    def test_both_present(self):
        assert validator.validate_inputs(True, True) is True

    def test_diagram_only(self):
        assert validator.validate_inputs(True, False) is True

    def test_prompt_only(self):
        assert validator.validate_inputs(False, True) is True

    def test_neither_present(self):
        assert validator.validate_inputs(False, False) is False


class TestValidateFull:
    def test_valid_png_with_prompt(self):
        ok, errs = validator.validate(_png_header(), "arch.png", "size my infra")
        assert ok is True
        assert errs == []

    def test_valid_prompt_only(self):
        ok, errs = validator.validate(None, None, "size my infra")
        assert ok is True
        assert errs == []

    def test_valid_diagram_only(self):
        ok, errs = validator.validate(_jpeg_header(), "arch.jpg", None)
        assert ok is True
        assert errs == []

    def test_no_inputs(self):
        ok, errs = validator.validate(None, None, None)
        assert ok is False
        assert errs[0]["error"] == "No input provided"

    def test_empty_prompt_no_diagram(self):
        ok, errs = validator.validate(None, None, "   ")
        assert ok is False
        assert errs[0]["error"] == "No input provided"

    def test_invalid_file_type(self):
        ok, errs = validator.validate(_pdf_header(), "doc.pdf", "prompt")
        assert ok is False
        assert errs[0]["error"] == "Invalid file format"

    def test_corrupted_file(self):
        ok, errs = validator.validate(b"\x00\x01", "bad.png", "prompt")
        assert ok is False
        assert errs[0]["error"] == "File could not be processed"

    def test_oversized_file(self):
        big = _png_header() + b"\x00" * MAX_FILE_SIZE_BYTES
        ok, errs = validator.validate(big, "huge.png", "prompt")
        assert ok is False
        assert any(e["error"] == "File too large" for e in errs)

    def test_empty_bytes_no_prompt(self):
        ok, errs = validator.validate(b"", None, None)
        assert ok is False
        assert errs[0]["error"] == "No input provided"
