# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Remediator for HTML accessibility issues.

This module provides functionality for remediating accessibility issues in HTML documents.
"""

from typing import Dict, List, Any
from bs4 import BeautifulSoup

from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger
from content_accessibility_utility_on_aws.remediate.remediation_manager import RemediationManager

# Set up module-level logger
logger = setup_logger(__name__)


class Remediator:
    """HTML accessibility remediator."""

    def __init__(self, options: Dict[str, Any]):
        """
        Initialize the remediator.

        Args:
            options: Remediation options
        """
        self.options = options

    def remediate_html(self, html: str, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Remediate accessibility issues in an HTML document.

        Args:
            html: HTML content to remediate
            issues: List of accessibility issues to remediate

        Returns:
            Dictionary containing remediation results and updated HTML
        """
        # Parse HTML
        soup = BeautifulSoup(html, "html.parser")

        # Create remediation manager
        remediation_manager = RemediationManager(soup, self.options)

        # Remediate issues
        remediation_result = remediation_manager.remediate_issues(issues)

        # Get updated HTML
        updated_html = str(soup)

        # Add updated HTML to result
        remediation_result["html"] = updated_html

        return remediation_result

    def _generate_report(
        self, results: Dict[str, Any], html_path: str
    ) -> Dict[str, Any]:
        """
        Generate a report from the remediation results.

        Args:
            results: Remediation results
            html_path: Path to the HTML file

        Returns:
            Dictionary containing the report data
        """
        # Create report model
        report = {
            "html_path": html_path,
            "issues_processed": results.get("issues_processed", 0),
            "issues_remediated": results.get("issues_remediated", 0),
            "issues_failed": results.get("issues_failed", 0),
            "details": results.get("details", []),
            "issues": results.get("details", []),  # For backward compatibility
        }

        # Add file results if available
        if "file_results" in results:
            report["file_results"] = []

            for file_result in results.get("file_results", []):
                # For each file, make sure issues_remediated doesn't exceed issues_processed
                # But store the actual number of changes in changes_applied
                processed = file_result.get("issues_processed", 0)
                remediated = file_result.get("issues_remediated", 0)

                # If more remediated than processed, adjust and store original in changes_applied
                if remediated > processed and processed > 0:
                    file_result["changes_applied"] = remediated
                    file_result["issues_remediated"] = processed

                report["file_results"].append(file_result)

        # Add remediated issues details if available
        if "remediated_issues_details" in results:
            report["remediated_issue_details"] = results.get(
                "remediated_issues_details", []
            )

        # Add failed issues details if available
        if "failed_issues_details" in results:
            report["failed_issue_details"] = results.get("failed_issues_details", [])

        # Add explanation for the discrepancy
        report["explanation"] = (
            "For landmark issues, one processed issue can fix multiple elements. Issues_remediated shows actual issues fixed, while changes_applied shows the total HTML elements changed."
        )

        return report
