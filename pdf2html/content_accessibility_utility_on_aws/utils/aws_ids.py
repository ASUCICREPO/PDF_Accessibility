# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Region- and partition-aware AWS identifiers.

Keeps Bedrock model IDs and ARNs valid in both commercial AWS and AWS GovCloud.
"""

import os
from typing import Optional

import boto3

DEFAULT_MODEL_NAME = "amazon.nova-lite-v1:0"


def inference_profile_prefix(region: Optional[str]) -> str:
    """
    Return the Bedrock cross-region inference profile prefix for a region,
    e.g. 'us-gov.' for us-gov-west-1, 'us.' for us-east-1, 'eu.' for eu-west-1.
    Falls back to 'us.' for unrecognized regions.
    """
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
    """
    Return the Bedrock model ID to use for remediation.

    The BEDROCK_MODEL_ID environment variable takes precedence; otherwise the
    region's cross-region inference profile for Nova Lite is used.
    """
    return os.getenv("BEDROCK_MODEL_ID") or f"{inference_profile_prefix(region)}{DEFAULT_MODEL_NAME}"
