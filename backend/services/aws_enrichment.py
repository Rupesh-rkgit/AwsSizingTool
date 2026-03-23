"""AWS data enrichment service for real-time pricing and documentation.

Fetches live data from the AWS Pricing API and AWS documentation pages
to inject current, accurate context into the LLM prompt — replacing
stale training-data pricing with real numbers.

This replicates the data sources used by the awslabs MCP servers
(aws-pricing-mcp-server, aws-documentation-mcp-server, aws-iac-mcp-server)
but as an importable library suitable for a deployed backend.
"""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Service name mapping — maps common names to AWS Pricing API service codes
# ---------------------------------------------------------------------------

_SERVICE_CODE_MAP: dict[str, str] = {
    "ec2": "AmazonEC2",
    "amazon ec2": "AmazonEC2",
    "elastic compute": "AmazonEC2",
    "rds": "AmazonRDS",
    "amazon rds": "AmazonRDS",
    "aurora": "AmazonRDS",
    "s3": "AmazonS3",
    "amazon s3": "AmazonS3",
    "cloudfront": "AmazonCloudFront",
    "amazon cloudfront": "AmazonCloudFront",
    "elb": "AWSELB",
    "alb": "AWSELB",
    "nlb": "AWSELB",
    "load balancer": "AWSELB",
    "elastic load": "AWSELB",
    "elasticache": "AmazonElastiCache",
    "amazon elasticache": "AmazonElastiCache",
    "redis": "AmazonElastiCache",
    "memcached": "AmazonElastiCache",
    "eks": "AmazonEKS",
    "amazon eks": "AmazonEKS",
    "kubernetes": "AmazonEKS",
    "ecs": "AmazonECS",
    "amazon ecs": "AmazonECS",
    "lambda": "AWSLambda",
    "aws lambda": "AWSLambda",
    "dynamodb": "AmazonDynamoDB",
    "amazon dynamodb": "AmazonDynamoDB",
    "nat gateway": "AmazonEC2",
    "vpc": "AmazonVPC",
    "amazon vpc": "AmazonVPC",
    "cloudwatch": "AmazonCloudWatch",
    "amazon cloudwatch": "AmazonCloudWatch",
    "sqs": "AWSQueueService",
    "amazon sqs": "AWSQueueService",
    "sns": "AmazonSNS",
    "amazon sns": "AmazonSNS",
    "api gateway": "AmazonApiGateway",
    "apigateway": "AmazonApiGateway",
    "route 53": "AmazonRoute53",
    "route53": "AmazonRoute53",
    "waf": "awswaf",
    "aws waf": "awswaf",
    "secrets manager": "AWSSecretsManager",
    "ecr": "AmazonECR",
    "elastic container registry": "AmazonECR",
    "efs": "AmazonEFS",
    "elastic file system": "AmazonEFS",
    "kinesis": "AmazonKinesis",
    "amazon kinesis": "AmazonKinesis",
    "msk": "AmazonMSK",
    "kafka": "AmazonMSK",
    "opensearch": "AmazonES",
    "elasticsearch": "AmazonES",
    "bedrock": "AmazonBedrock",
    "sagemaker": "AmazonSageMaker",
    "step functions": "AWSStepFunctions",
    "codepipeline": "AWSCodePipeline",
    "fargate": "AmazonECS",
}

# AWS doc base URLs for common services
_DOC_URLS: dict[str, str] = {
    "AmazonEC2": "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html",
    "AmazonRDS": "https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html",
    "AmazonS3": "https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html",
    "AmazonEKS": "https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html",
    "AmazonECS": "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html",
    "AWSLambda": "https://docs.aws.amazon.com/lambda/latest/dg/welcome.html",
    "AmazonCloudFront": "https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html",
    "AmazonElastiCache": "https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/WhatIs.html",
    "AmazonDynamoDB": "https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html",
    "AWSELB": "https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/what-is-load-balancing.html",
}

# Region name mapping for pricing API
_REGION_NAMES: dict[str, str] = {
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "us-west-1": "US West (N. California)",
    "us-west-2": "US West (Oregon)",
    "eu-west-1": "EU (Ireland)",
    "eu-west-2": "EU (London)",
    "eu-central-1": "EU (Frankfurt)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "ap-southeast-2": "Asia Pacific (Sydney)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
    "ap-south-1": "Asia Pacific (Mumbai)",
    "ca-central-1": "Canada (Central)",
    "sa-east-1": "South America (Sao Paulo)",
}


class _SimpleHTMLStripper(HTMLParser):
    """Minimal HTML-to-text converter."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = True
        if tag in ("p", "br", "div", "h1", "h2", "h3", "h4", "li", "tr"):
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts).strip()



class AWSEnrichmentService:
    """Fetches real-time AWS pricing and documentation to enrich LLM prompts.

    Parameters
    ----------
    region:
        AWS region for pricing lookups (default ``us-east-1``).
    timeout_seconds:
        HTTP/API timeout for external calls.
    max_pricing_results:
        Max price list items to fetch per service.
    """

    def __init__(
        self,
        region: str = "us-east-1",
        timeout_seconds: int = 15,
        max_pricing_results: int = 10,
    ) -> None:
        self._region = region
        self._timeout = timeout_seconds
        self._max_results = max_pricing_results
        # Pricing API is only available in us-east-1 and ap-south-1
        self._pricing_client = boto3.client(
            "pricing",
            region_name="us-east-1",
            config=Config(
                read_timeout=timeout_seconds,
                retries={"max_attempts": 2, "mode": "adaptive"},
            ),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enrich(self, prompt_text: str | None, region: str | None = None) -> str:
        """Build an enrichment context block from real-time AWS data.

        Detects AWS services mentioned in the prompt, fetches their current
        pricing, and returns a formatted context string to inject into the
        system prompt.

        Parameters
        ----------
        prompt_text:
            The user's NFR / volumetric text (may be None).
        region:
            Override region for pricing lookups.

        Returns
        -------
        str
            Formatted enrichment context, or empty string if nothing found.
        """
        if not prompt_text:
            return ""

        target_region = region or self._region
        detected = self._detect_services(prompt_text)

        if not detected:
            return ""

        logger.info("Detected AWS services for enrichment: %s", list(detected))

        sections: list[str] = []

        # Fetch pricing data in parallel
        pricing_data = self._fetch_pricing_parallel(detected, target_region)
        if pricing_data:
            sections.append(self._format_pricing_context(pricing_data, target_region))

        # Fetch relevant doc snippets in parallel
        doc_data = self._fetch_docs_parallel(detected)
        if doc_data:
            sections.append(self._format_docs_context(doc_data))

        if not sections:
            return ""

        header = (
            f"## Real-Time AWS Data (fetched live for {target_region})\n"
            "Use this data for accurate pricing and specifications. "
            "These are current on-demand prices from the AWS Pricing API.\n"
        )
        return header + "\n\n".join(sections)

    # ------------------------------------------------------------------
    # Service detection
    # ------------------------------------------------------------------

    def _detect_services(self, text: str) -> set[str]:
        """Detect AWS service codes mentioned in the text."""
        text_lower = text.lower()
        found: set[str] = set()

        for keyword, service_code in _SERVICE_CODE_MAP.items():
            # Use word boundary matching for short keywords
            if len(keyword) <= 3:
                if re.search(rf"\b{re.escape(keyword)}\b", text_lower):
                    found.add(service_code)
            else:
                if keyword in text_lower:
                    found.add(service_code)

        return found

    # ------------------------------------------------------------------
    # Pricing fetcher
    # ------------------------------------------------------------------

    def _fetch_pricing_for_service(
        self, service_code: str, region: str
    ) -> dict[str, Any] | None:
        """Fetch pricing for a single service from the AWS Pricing API."""
        region_name = _REGION_NAMES.get(region, region)

        try:
            filters = [
                {"Type": "TERM_MATCH", "Field": "location", "Value": region_name},
            ]

            # Add service-specific filters for more relevant results
            if service_code == "AmazonEC2":
                filters.extend([
                    {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
                    {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
                    {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
                    {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
                ])

            response = self._pricing_client.get_products(
                ServiceCode=service_code,
                Filters=filters,
                MaxResults=self._max_results,
            )

            price_items = []
            for price_json_str in response.get("PriceList", []):
                price_data = json.loads(price_json_str) if isinstance(price_json_str, str) else price_json_str
                product = price_data.get("product", {})
                attrs = product.get("attributes", {})
                terms = price_data.get("terms", {})

                # Extract on-demand pricing
                on_demand = terms.get("OnDemand", {})
                price_per_unit = ""
                unit = ""
                for _term_key, term_val in on_demand.items():
                    for _dim_key, dim_val in term_val.get("priceDimensions", {}).items():
                        ppu = dim_val.get("pricePerUnit", {})
                        price_per_unit = ppu.get("USD", "")
                        unit = dim_val.get("unit", "")
                        break
                    break

                if price_per_unit and price_per_unit != "0.0000000000":
                    item_info: dict[str, str] = {
                        "price_usd": price_per_unit,
                        "unit": unit,
                    }
                    # Include relevant attributes
                    for key in ("instanceType", "memory", "vcpu", "storage",
                                "instanceFamily", "usagetype", "databaseEngine",
                                "cacheEngine", "storageClass"):
                        if key in attrs:
                            item_info[key] = attrs[key]

                    price_items.append(item_info)

            if price_items:
                return {"service_code": service_code, "items": price_items}

        except (ClientError, BotoCoreError) as exc:
            logger.warning("Pricing fetch failed for %s: %s", service_code, exc)
        except Exception as exc:
            logger.warning("Unexpected error fetching pricing for %s: %s", service_code, exc)

        return None

    def _fetch_pricing_parallel(
        self, service_codes: set[str], region: str
    ) -> list[dict[str, Any]]:
        """Fetch pricing for multiple services concurrently."""
        results: list[dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self._fetch_pricing_for_service, sc, region): sc
                for sc in service_codes
            }
            for future in as_completed(futures, timeout=self._timeout + 5):
                try:
                    result = future.result(timeout=self._timeout)
                    if result:
                        results.append(result)
                except Exception as exc:
                    sc = futures[future]
                    logger.warning("Pricing thread failed for %s: %s", sc, exc)

        return results

    # ------------------------------------------------------------------
    # Documentation fetcher
    # ------------------------------------------------------------------

    def _fetch_doc_page(self, service_code: str) -> dict[str, str] | None:
        """Fetch and extract text from an AWS documentation page."""
        url = _DOC_URLS.get(service_code)
        if not url:
            return None

        try:
            req = Request(url, headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                )
            })
            with urlopen(req, timeout=self._timeout) as resp:
                html = resp.read().decode("utf-8", errors="replace")

            stripper = _SimpleHTMLStripper()
            stripper.feed(html)
            text = stripper.get_text()

            # Truncate to keep context manageable
            if len(text) > 3000:
                text = text[:3000] + "\n... [truncated]"

            return {"service_code": service_code, "url": url, "content": text}

        except (URLError, OSError) as exc:
            logger.warning("Doc fetch failed for %s: %s", service_code, exc)
        except Exception as exc:
            logger.warning("Unexpected error fetching docs for %s: %s", service_code, exc)

        return None

    def _fetch_docs_parallel(self, service_codes: set[str]) -> list[dict[str, str]]:
        """Fetch documentation for multiple services concurrently."""
        results: list[dict[str, str]] = []
        # Only fetch docs for services we have URLs for
        fetchable = service_codes & set(_DOC_URLS.keys())

        if not fetchable:
            return results

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self._fetch_doc_page, sc): sc
                for sc in fetchable
            }
            for future in as_completed(futures, timeout=self._timeout + 5):
                try:
                    result = future.result(timeout=self._timeout)
                    if result:
                        results.append(result)
                except Exception as exc:
                    sc = futures[future]
                    logger.warning("Doc thread failed for %s: %s", sc, exc)

        return results

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _format_pricing_context(
        pricing_data: list[dict[str, Any]], region: str
    ) -> str:
        """Format pricing data into a context block for the LLM."""
        lines = [f"### Current On-Demand Pricing ({region})\n"]

        for svc in pricing_data:
            service_code = svc["service_code"]
            lines.append(f"**{service_code}:**")
            for item in svc["items"][:8]:  # Cap per service
                parts = []
                if "instanceType" in item:
                    parts.append(f"Instance: {item['instanceType']}")
                if "vcpu" in item:
                    parts.append(f"vCPU: {item['vcpu']}")
                if "memory" in item:
                    parts.append(f"Memory: {item['memory']}")
                if "databaseEngine" in item:
                    parts.append(f"Engine: {item['databaseEngine']}")
                if "cacheEngine" in item:
                    parts.append(f"Engine: {item['cacheEngine']}")
                if "storageClass" in item:
                    parts.append(f"Storage: {item['storageClass']}")
                parts.append(f"Price: ${item['price_usd']}/{item['unit']}")
                lines.append(f"  - {', '.join(parts)}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _format_docs_context(doc_data: list[dict[str, str]]) -> str:
        """Format documentation snippets into a context block."""
        lines = ["### AWS Service Reference (live documentation)\n"]

        for doc in doc_data:
            lines.append(f"**{doc['service_code']}** (source: {doc['url']})")
            # Take first ~800 chars of content as a summary
            content = doc["content"]
            if len(content) > 800:
                content = content[:800] + "..."
            lines.append(content)
            lines.append("")

        return "\n".join(lines)
