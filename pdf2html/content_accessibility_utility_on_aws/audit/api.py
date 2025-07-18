# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
API for HTML accessibility auditing.

This module provides the implementation for auditing HTML documents for accessibility issues.
"""

import os
import traceback
from typing import Dict, Any, Optional

from content_accessibility_utility_on_aws.audit.auditor import AccessibilityAuditor

# IMPORTANT FIX: Import from the correct module path
from content_accessibility_utility_on_aws.audit.report_generator import generate_report
from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger

# Set up module-level logger
logger = setup_logger(__name__)


def audit_html_accessibility(
    html_path: str,
    image_dir: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Audit an HTML document for accessibility issues.

    Args:
        html_path: Path to the HTML file or directory of HTML files.
        image_dir: Directory containing images referenced in the HTML.
        options: Audit options.
        output_path: Path to save the audit report.

    Returns:
        Dictionary containing audit results.
    """
    if options is None:
        options = {}

    try:
        # Use the AccessibilityAuditor to perform the audit
        auditor = AccessibilityAuditor(
            html_path=html_path, image_dir=image_dir, options=options
        )
        audit_results = auditor.audit()

        # Log initial audit results
        logger.debug("Raw audit results type: %s", type(audit_results))
        logger.debug(
            "Raw audit results keys: %s",
            (
                list(audit_results.keys())
                if isinstance(audit_results, dict)
                else "Not a dict"
            ),
        )

        # Validate audit results structure
        if not isinstance(audit_results, dict):
            raise ValueError(f"Invalid audit results type: {type(audit_results)}")
        if "issues" not in audit_results:
            raise ValueError("Audit results missing 'issues' field")
        if not isinstance(audit_results["issues"], list):
            raise ValueError("Audit results 'issues' must be a list")

        # Log audit results details
        logger.debug("Number of issues: %d", len(audit_results["issues"]))
        logger.debug("Summary data: %s", audit_results.get("summary", {}))

        logger.debug("Generating text report...")
        text_report = generate_report(
            audit_results, output_path=output_path, report_format="text"
        )
        if text_report is None:
            logger.warning("Text report generation failed, using basic format")
            # Generate a basic text report
            total = audit_results.get("summary", {}).get("total_issues", 0)
            compliant = audit_results.get("summary", {}).get("compliant", 0)
            needs_remediation = audit_results.get("summary", {}).get(
                "needs_remediation", 0
            )
            text_report = (
                f"Total issues: {total}\nCompliant: {compliant}\nNeeds "
                + f"remediation: {needs_remediation}"
            )
        audit_results["report"] = text_report

        # Generate and save report if output path is specified
        if output_path:
            # Determine the report format
            report_format = options.get("report_format", "json")
            logger.debug(
                "Preparing to save %s report to: %s", report_format.upper(), output_path
            )

            # Create output directory if needed
            output_dir = os.path.dirname(os.path.abspath(output_path))
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                logger.debug("Created output directory: %s", output_dir)

            # Generate report using the specified format
            logger.debug("Generating %s report...", report_format.upper())
            report_result = generate_report(
                audit_results, output_path=output_path, report_format=report_format
            )

            if report_format == "json" and report_result:
                # Only validate if it's a json report that returns data
                logger.debug(
                    "JSON report keys: %s",
                    (
                        list(report_result.keys())
                        if isinstance(report_result, dict)
                        else "Not a dict"
                    ),
                )
                if isinstance(report_result, dict) and "issues" in report_result:
                    logger.debug(
                        "Number of issues in JSON report: %d",
                        len(report_result["issues"]),
                    )

            audit_results["report_path"] = output_path
            logger.debug(
                "Successfully saved %s report to: %s",
                report_format.upper(),
                output_path,
            )

    except Exception as e:
        logger.warning("Error in report generation: %s", str(e))
        logger.warning("Error details: %s", traceback.format_exc())
        raise ValueError(f"Failed to generate report: {str(e)}") from e

    return audit_results
