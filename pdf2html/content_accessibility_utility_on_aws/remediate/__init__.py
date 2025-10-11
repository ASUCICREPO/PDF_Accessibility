# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
HTML Accessibility Remediation functionality.
"""

from content_accessibility_utility_on_aws.remediate.api import remediate_html_accessibility
from content_accessibility_utility_on_aws.remediate.remediation_report_generator import (
    generate_remediation_report,
)

__all__ = [
    "remediate_html_accessibility",
    "generate_remediation_report",
]
