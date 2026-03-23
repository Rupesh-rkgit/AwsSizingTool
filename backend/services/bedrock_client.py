"""Wrapper around the boto3 Bedrock Runtime Converse API.

Handles multimodal (image + text) requests, timeout configuration,
adaptive exponential backoff retries, and credential resolution
via the standard boto3 chain (env vars → config file → IAM role).
"""

from __future__ import annotations

import boto3
from botocore.config import Config

from backend.config import BedrockConfig


class BedrockClient:
    """Thin wrapper around the Bedrock Runtime ``converse`` API."""

    def __init__(self, settings: BedrockConfig) -> None:
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=settings.region,
            config=Config(
                read_timeout=settings.timeout_seconds,
                retries={
                    "max_attempts": settings.retry_attempts,
                    "mode": "adaptive",
                },
            ),
        )
        self.model_id = settings.model_id
        self.max_tokens = settings.max_tokens
        self.temperature = settings.temperature

    def analyze(
        self,
        system_prompt: str,
        user_text: str,
        image_bytes: bytes | None = None,
        image_media_type: str | None = None,
    ) -> str:
        """Send a multimodal request to Bedrock and return the text response.

        Parameters
        ----------
        system_prompt:
            Instructions placed in the ``system`` block of the Converse call.
        user_text:
            The user-facing text content (NFR / volumetric prompt).
        image_bytes:
            Raw bytes of the architecture diagram image, or ``None``.
        image_media_type:
            MIME type of the image (e.g. ``"image/png"``), or ``None``.

        Returns
        -------
        str
            The text content extracted from the first content block of the
            model response.
        """
        content_blocks: list[dict] = []

        if image_bytes and image_media_type:
            content_blocks.append(
                {
                    "image": {
                        "format": image_media_type.split("/")[-1],  # "png", "jpeg", "webp"
                        "source": {"bytes": image_bytes},
                    }
                }
            )

        content_blocks.append({"text": user_text})

        response = self.client.converse(
            modelId=self.model_id,
            system=[{"text": system_prompt}],
            messages=[{"role": "user", "content": content_blocks}],
            inferenceConfig={
                "maxTokens": self.max_tokens,
                "temperature": self.temperature,
            },
        )

        return response["output"]["message"]["content"][0]["text"]
