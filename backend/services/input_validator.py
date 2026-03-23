"""Server-side input validation for the AWS Infrastructure Sizing Tool.

Validates uploaded files (type via magic bytes, size), NFR document files
(.txt, .md), and ensures at least one input (diagram, prompt, or NFR doc)
is present.  Returns structured error dicts suitable for HTTP 400 JSON
responses.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Magic-byte signatures for supported image formats
# ---------------------------------------------------------------------------
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"  # first 8 bytes
_JPEG_MAGIC = b"\xff\xd8\xff"       # first 3 bytes
_WEBP_RIFF = b"RIFF"                # bytes 0-3
_WEBP_TAG = b"WEBP"                 # bytes 8-11

# Maximum upload size: 20 MB
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20,971,520

# Supported NFR document extensions
NFR_DOC_EXTENSIONS = {".txt", ".md"}
MAX_NFR_DOC_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


class InputValidator:
    """Validates user-supplied inputs before they reach the Sizing Engine."""

    # ------------------------------------------------------------------
    # Individual validators
    # ------------------------------------------------------------------

    @staticmethod
    def validate_file_type(file_bytes: bytes) -> str | None:
        """Check magic bytes and return the media type string, or ``None`` if
        the format is not supported.

        Supported formats and their media types:
        - PNG  → ``"image/png"``
        - JPEG → ``"image/jpeg"``
        - WEBP → ``"image/webp"``
        """
        if len(file_bytes) < 12:
            return None

        if file_bytes[:8] == _PNG_MAGIC:
            return "image/png"

        if file_bytes[:3] == _JPEG_MAGIC:
            return "image/jpeg"

        if file_bytes[:4] == _WEBP_RIFF and file_bytes[8:12] == _WEBP_TAG:
            return "image/webp"

        return None

    @staticmethod
    def validate_file_size(file_bytes: bytes, max_size_mb: int = 20) -> bool:
        """Return ``True`` if *file_bytes* is within the allowed size limit."""
        max_bytes = max_size_mb * 1024 * 1024
        return len(file_bytes) <= max_bytes

    @staticmethod
    def validate_inputs(has_diagram: bool, has_prompt: bool, has_nfr_doc: bool = False) -> bool:
        """Return ``True`` if at least one input is present."""
        return has_diagram or has_prompt or has_nfr_doc

    @staticmethod
    def validate_nfr_doc(file_bytes: bytes, filename: str) -> tuple[bool, str | None]:
        """Validate an NFR document file.

        Returns (is_valid, error_message).
        """
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in NFR_DOC_EXTENSIONS:
            return False, f"Unsupported NFR document format. Supported: {', '.join(NFR_DOC_EXTENSIONS)}"
        if len(file_bytes) > MAX_NFR_DOC_SIZE_BYTES:
            return False, "NFR document too large. Maximum size: 5 MB."
        # Try to decode as UTF-8
        try:
            file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return False, "NFR document must be a valid UTF-8 text file."
        return True, None

    # ------------------------------------------------------------------
    # Full validation pipeline
    # ------------------------------------------------------------------

    def validate(
        self,
        file_bytes: bytes | None,
        filename: str | None,
        prompt: str | None,
        nfr_doc_bytes: bytes | None = None,
        nfr_doc_filename: str | None = None,
    ) -> tuple[bool, list[dict]]:
        """Run all validations and return ``(is_valid, errors)``.

        Each error is a dict with ``"error"`` and ``"details"`` keys matching
        the API error response schema.
        """
        errors: list[dict] = []
        has_diagram = file_bytes is not None and len(file_bytes) > 0
        has_prompt = prompt is not None and prompt.strip() != ""
        has_nfr_doc = nfr_doc_bytes is not None and len(nfr_doc_bytes) > 0

        # 1. At least one input required
        if not self.validate_inputs(has_diagram, has_prompt, has_nfr_doc):
            errors.append({
                "error": "No input provided",
                "details": ["Provide at least a diagram, text prompt, or NFR document"],
            })
            return False, errors

        # 2. If a diagram file was provided, validate it
        if has_diagram:
            assert file_bytes is not None  # for type-checker

            # 2a. File size
            if not self.validate_file_size(file_bytes):
                errors.append({
                    "error": "File too large",
                    "details": ["Maximum file size: 20 MB"],
                })

            # 2b. File type (magic bytes)
            media_type = self.validate_file_type(file_bytes)
            if media_type is None:
                if self._looks_corrupted(file_bytes):
                    errors.append({
                        "error": "File could not be processed",
                        "details": [
                            "The uploaded file appears to be corrupted"
                        ],
                    })
                else:
                    errors.append({
                        "error": "Invalid file format",
                        "details": [
                            "Supported formats: PNG, JPG, JPEG, WEBP"
                        ],
                    })

        # 3. If an NFR document was provided, validate it
        if has_nfr_doc:
            assert nfr_doc_bytes is not None
            assert nfr_doc_filename is not None
            is_valid_doc, doc_error = self.validate_nfr_doc(nfr_doc_bytes, nfr_doc_filename)
            if not is_valid_doc:
                errors.append({
                    "error": "Invalid NFR document",
                    "details": [doc_error or "Unknown error"],
                })

        is_valid = len(errors) == 0
        return is_valid, errors

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _looks_corrupted(file_bytes: bytes) -> bool:
        """Heuristic: if the file is very small (< 12 bytes) it is likely
        corrupted / truncated rather than simply the wrong format."""
        return len(file_bytes) < 12
