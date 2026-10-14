# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Region- and partition-aware AWS identifiers.

Keeps Bedrock model IDs and ARNs valid in both commercial AWS and AWS GovCloud.
"""

import os
from typing import Optional

import boto3

DEFAULT_MODEL_NAME = "openai.gpt-5.6-luna"


def inference_profile_prefix(region: Optional[str]) -> str:
    """Cross-region inference profile prefix for the region (us., us-gov., eu., apac.)."""
    region = region or ""
    if region.startswith("us-gov-"):
        return "us-gov."
    if region.startswith("eu-"):
        return "eu."
    if region.startswith("ap-"):
        return "apac."
    return "us."


def partition_for_region(region: Optional[str]) -> str:
    """Return the ARN partition ('aws', 'aws-us-gov', 'aws-cn', ...) for a region."""
    if not region:
        return "aws"
    return boto3.Session().get_partition_for_region(region)


def default_model_id(region: Optional[str]) -> str:
    """Model ID for remediation: BEDROCK_MODEL_ID, else the region's inference profile for DEFAULT_MODEL_NAME."""
    return os.getenv("BEDROCK_MODEL_ID") or f"{inference_profile_prefix(region)}{DEFAULT_MODEL_NAME}"


def model_request_fields(model_id: str) -> dict:
    """Per-provider Converse request fields."""
    if "openai." in model_id:
        return {"additionalModelRequestFields": {"reasoning": {"effort": os.getenv("BEDROCK_REASONING_EFFORT", "low")}}}
    return {}
