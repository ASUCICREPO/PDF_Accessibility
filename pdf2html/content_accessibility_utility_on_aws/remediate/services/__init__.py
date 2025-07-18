# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Services for HTML accessibility remediation.

This package provides services used by the HTML accessibility remediator.
"""

from content_accessibility_utility_on_aws.remediate.services.bedrock_client import BedrockClient

__all__ = ["BedrockClient"]
