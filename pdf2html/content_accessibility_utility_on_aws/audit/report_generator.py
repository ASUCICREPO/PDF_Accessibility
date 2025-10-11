# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Generate accessibility audit reports in various formats.

This module has been updated to use the unified report generation system
with Pydantic models for data validation.
"""

from typing import Dict, Any
from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger
from content_accessibility_utility_on_aws.utils.report_generator import (
    generate_report as utils_generate_report,
)

logger = setup_logger(__name__)


def generate_report(
    audit_data: Dict[str, Any],
    output_path: str,
    report_format: str = "json",
    unified: bool = False,
) -> Dict[str, Any]:
    """
    Generate an accessibility audit report in the specified format.

    Args:
        audit_data: Dictionary containing the audit results
        output_path: Path where the report should be saved
        report_format: Format of the report (json, html, or text)
        unified: If True, generates a unified report that can show both audit and remediation data

    Returns:
        Standardized report data
    """
    report_type = "unified" if unified else "accessibility"
    logger.info(f"Generating {report_format} {report_type} report at {output_path}")

    # Use the unified report generator
    return utils_generate_report(
        report_data=audit_data,
        output_path=output_path,
        report_format=report_format,
        report_type=report_type,
    )
