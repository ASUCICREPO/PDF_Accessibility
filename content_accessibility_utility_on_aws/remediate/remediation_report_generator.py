# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Generate accessibility remediation reports in various formats.

This module has been updated to use the unified report generation system
with Pydantic models for data validation.
"""

from typing import Dict, Any
from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger
from content_accessibility_utility_on_aws.utils.report_generator import (
    generate_report as utils_generate_report,
)

logger = setup_logger(__name__)


def generate_remediation_report(
    remediation_data: Dict[str, Any],
    output_path: str,
    report_format: str = "html",
    format_type: str = None,
) -> Dict[str, Any]:
    """
    Generate an accessibility remediation report in the specified format.

    Args:
        remediation_data: Dictionary containing the remediation data
        output_path: Path where the report will be saved
        report_format: Type of report to generate ('html', 'json', or 'text')
        format_type: Alternative parameter name for backward compatibility

    Returns:
        Standardized report data
    """
    # Use format_type if report_format is not specified (for backward compatibility)
    format_to_use = format_type if format_type is not None else report_format
    logger.debug(f"Generating {format_to_use} remediation report at {output_path}")

    # Synchronize top-level counts with file-level totals
    # This ensures top-level remediated count matches what's in the files
    if "file_results" in remediation_data:
        total_processed = 0
        total_remediated = 0
        total_failed = 0

        for file_result in remediation_data.get("file_results", []):
            total_processed += file_result.get("issues_processed", 0)
            total_remediated += file_result.get("issues_remediated", 0)
            total_failed += file_result.get("issues_failed", 0)

        # Update top-level counts
        remediation_data["issues_processed"] = total_processed
        remediation_data["issues_remediated"] = total_remediated
        remediation_data["issues_failed"] = total_failed

        # Ensure the summary reflects the correct counts too
        if "summary" not in remediation_data:
            remediation_data["summary"] = {}

        remediation_data["summary"]["total_issues"] = total_processed
        remediation_data["summary"]["issues_processed"] = total_processed
        remediation_data["summary"]["remediated_issues"] = total_remediated
        remediation_data["summary"]["failed_issues"] = total_failed

    # Make sure all issues in the issues array have their remediation_status
    # properly reflected in the top-level counts
    if "issues" in remediation_data:
        remediated_count = 0
        failed_count = 0

        for issue in remediation_data["issues"]:
            if issue.get("remediation_status") == "remediated":
                remediated_count += 1
            else:
                failed_count += 1

        # If there's no file_results section, use these counts
        if "file_results" not in remediation_data:
            remediation_data["issues_processed"] = len(remediation_data["issues"])
            remediation_data["issues_remediated"] = remediated_count
            remediation_data["issues_failed"] = failed_count

            # Update summary as well
            if "summary" not in remediation_data:
                remediation_data["summary"] = {}

            remediation_data["summary"]["total_issues"] = len(
                remediation_data["issues"]
            )
            remediation_data["summary"]["issues_processed"] = len(
                remediation_data["issues"]
            )
            remediation_data["summary"]["remediated_issues"] = remediated_count
            remediation_data["summary"]["failed_issues"] = failed_count

        # Add detailed issue information to the report data if available from file_results
    if "file_results" in remediation_data:
        # Extract issues from file results
        issues = []
        for file_result in remediation_data.get("file_results", []):
            file_issues = file_result.get("details", [])
            for issue in file_issues:
                # Add file path to each issue
                issue["file_path"] = file_result.get("file_path", "")
                issues.append(issue)

        # Add issues to remediation data
        if issues:
            remediation_data["issues"] = issues
            logger.debug(f"Added {len(issues)} detailed issues from file_results")

    # Use the unified report generator
    prepared_data = utils_generate_report(
        report_data=remediation_data,
        output_path=output_path,
        report_format=format_to_use,
        report_type="remediation",
    )

    return prepared_data
