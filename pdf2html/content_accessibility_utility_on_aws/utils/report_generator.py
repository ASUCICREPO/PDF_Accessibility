# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Generate reports for accessibility audits and remediations.

This module provides functionality for generating accessibility reports in various formats,
including a unified report that combines audit and remediation data.
"""

import os
import json
from typing import Dict, Any

from flask import Flask, render_template

from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger


# Set up module-level logger
logger = setup_logger(__name__)


def generate_report(
    report_data: Dict[str, Any],
    output_path: str,
    report_format: str = "html",
    report_type: str = "accessibility",
) -> Dict[str, Any]:
    """
    Generate a report in the specified format.

    Args:
        report_data: Dictionary containing the report data
        output_path: Path where the report will be saved
        report_format: Type of report to generate ('html', 'json', 'text', or 'csv')
        report_type: Type of report ('accessibility', 'remediation', or 'unified')

    Returns:
        Standardized report data
    """
    # CRITICAL FIX: Ensure file results have consistent issue counts
    if report_type == "remediation" and "file_results" in report_data:
        for file_result in report_data.get("file_results", []):
            processed = file_result.get("issues_processed", 0)
            remediated = file_result.get("issues_remediated", 0)

            # If remediated exceeds processed, store actual changes in changes_applied and fix remediated
            if remediated > processed and processed > 0:
                file_result["changes_applied"] = remediated
                file_result["issues_remediated"] = processed
                file_result["explanation"] = (
                    f"Fixed {processed} issues with {remediated} HTML changes"
                )

    # Make sure the output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Handle "unified" report format - it's actually just an HTML report
    if report_format == "unified":
        logger.debug("Handling 'unified' as HTML format")
        report_format = "html"

    # Generate the report based on the format
    if report_format == "json":
        return generate_json_report(report_data, output_path)
    elif report_format == "html":
        return generate_html_report(report_data, output_path, report_type)
    elif report_format == "text":
        return generate_text_report(report_data, output_path, report_type)
    elif report_format == "csv":
        return generate_csv_report(report_data, output_path, report_type)
    else:
        # Default to JSON
        logger.warning(f"Unknown report format: {report_format}, using JSON")
        return generate_json_report(report_data, output_path)


def generate_json_report(
    report_data: Dict[str, Any], output_path: str
) -> Dict[str, Any]:
    """
    Generate a JSON report.

    Args:
        report_data: Dictionary containing the report data
        output_path: Path where the report will be saved

    Returns:
        The report data
    """
    try:
        # Create a serializable copy of the data
        serializable_data = prepare_for_json_serialization(report_data)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(serializable_data, f, indent=2)

        logger.info(f"Generated JSON report: {output_path}")
        return report_data
    except Exception as e:
        logger.warning(f"Error generating JSON report: {str(e)}")
        # Fallback to simpler JSON structure
        minimal_data = create_minimal_report(report_data)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(minimal_data, f, indent=2)
        logger.info(f"Generated simplified JSON report: {output_path}")
        return report_data


def prepare_for_json_serialization(data, depth=20, visited=None):
    """
    Prepare a data structure for JSON serialization by removing circular references and limiting recursion depth.

    Args:
        data: The data to prepare
        depth: Maximum recursion depth (default: 20)
        visited: Set of object IDs to detect circular references (default: None)

    Returns:
        A JSON-serializable version of the data
    """
    if visited is None:
        visited = set()

    # Limit recursion depth
    if depth <= 0:
        return "Recursion depth exceeded"

    # For basic types, return as is
    if isinstance(data, (str, int, float, bool, type(None))):
        return data

    # For lists, process each item
    elif isinstance(data, list):
        return [prepare_for_json_serialization(item, depth - 1, visited) for item in data]

    # For dictionaries, process each value
    elif isinstance(data, dict):
        object_id = id(data)
        if object_id in visited:
            return "Circular reference detected"
        visited.add(object_id)

        result = {}
        for key, value in data.items():
            # Skip problematic keys that might cause circular references
            if key in (
                "parent",
                "children",
                "_parent",
                "_children",
                "references",
                "_references",
            ):
                continue

            # Handle nested structures
            result[key] = prepare_for_json_serialization(value, depth - 1, visited)
        visited.remove(object_id)  # Remove the object ID when done processing
        return result

    # For other objects, try to convert to dict or use str representation
    else:
        try:
            object_id = id(data)
            if object_id in visited:
                return "Circular reference detected"
            visited.add(object_id)

            # Try to convert to dict if the object has a __dict__ attribute
            if hasattr(data, "__dict__"):
                result = prepare_for_json_serialization(data.__dict__, depth - 1, visited)
                visited.remove(object_id)
                return result
            # If the object is iterable, convert to list
            elif hasattr(data, "__iter__") and not isinstance(data, str):
                result = prepare_for_json_serialization(list(data), depth - 1, visited)
                visited.remove(object_id)
                return result
            # Otherwise, use string representation
            else:
                visited.remove(object_id)
                return str(data)
        except:
            # If all else fails, use string representation
            return str(data)


def create_minimal_report(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a minimal version of the report with only essential information.

    Args:
        report_data: The original report data

    Returns:
        A simplified version of the report
    """
    minimal = {
        "html_path": report_data.get("html_path", ""),
        "total_issues": report_data.get("total_issues", 0),
    }

    # Extract basic issue information
    if "issues" in report_data and isinstance(report_data["issues"], list):
        minimal["issues"] = []
        for issue in report_data["issues"]:
            if isinstance(issue, dict):
                minimal_issue = {
                    "type": issue.get("type", "unknown"),
                    "severity": issue.get("severity", "minor"),
                    "message": issue.get("message", ""),
                }
                minimal["issues"].append(minimal_issue)

    # Add summary information if available
    if "summary" in report_data and isinstance(report_data["summary"], dict):
        minimal["summary"] = {
            "total_issues": report_data["summary"].get("total_issues", 0),
            "severity_counts": report_data["summary"].get("severity_counts", {}),
        }

    return minimal


def generate_html_report(
    report_data: Dict[str, Any], output_path: str, report_type: str
) -> Dict[str, Any]:
    """
    Generate an HTML report using Flask's render_template.

    Args:
        report_data: Dictionary containing the report data
        output_path: Path where the report will be saved
        report_type: Type of report ('accessibility' or 'remediation')

    Returns:
        The report data
    """
    # Process data for unified report before rendering
    report_data = prepare_unified_report_data(report_data)

    # Prepare data based on the report type
    # For accessibility reports, calculate issue counts by severity and category
    if report_type == "accessibility":
        # Make sure report_data has necessary fields
        if "total_issues" not in report_data and "issues" in report_data:
            report_data["total_issues"] = len(report_data["issues"])

        # Initialize or use existing severity counts
        severity_counts = report_data.get("severity_counts", {})
        if (
            not severity_counts
            and "summary" in report_data
            and "severity_counts" in report_data["summary"]
        ):
            severity_counts = report_data["summary"]["severity_counts"]
        elif not severity_counts:
            severity_counts = {"critical": 0, "major": 0, "minor": 0}

            # Count issues by severity if not already counted
            for issue in report_data.get("issues", []):
                severity = issue.get("severity", "minor")
                if severity in severity_counts:
                    severity_counts[severity] += 1

        # Store severity counts at the top level for the template
        report_data["severity_counts"] = severity_counts

        # Calculate issue type counts
        issue_type_counts = {}
        for issue in report_data.get("issues", []):
            issue_type = issue.get("type", "unknown")
            if issue_type not in issue_type_counts:
                issue_type_counts[issue_type] = 0
            issue_type_counts[issue_type] += 1

        # Add the counts to the report data
        report_data["issue_type_counts"] = issue_type_counts

    # Ensure all issues have messages for display purposes
    for issue in report_data.get("issues", []):
        if not issue.get("message"):
            issue_type = issue.get("type", "unknown issue")
            issue["message"] = f"{issue_type} identified"

    try:
        # Create a temporary Flask app context
        app = Flask(__name__)

        # Render the template with Flask's render_template
        with app.app_context():
            template_file = "unified_report.html"
            logger.debug(f"Using template file: {template_file}")
            html = render_template(
                template_file,
                report=report_data
            )

        logger.info("Using Flask's render_template for secure HTML generation")

        # Write the HTML to the output file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"Generated HTML report: {output_path}")
        return report_data

    except Exception as e:
        logger.error(f"Failed to generate HTML report with Flask: {e}", exc_info=True)
        logger.warning("Falling back to JSON report since Flask rendering failed")
        return generate_json_report(report_data, output_path)


def generate_text_report(
    report_data: Dict[str, Any], output_path: str, report_type: str
) -> Dict[str, Any]:
    """
    Generate a text report.

    Args:
        report_data: Dictionary containing the report data
        output_path: Path where the report will be saved
        report_type: Type of report ('accessibility' or 'remediation')

    Returns:
        The report data
    """
    # Generate text report
    text = []

    # Add report title based on report type
    if report_type == "accessibility":
        text.append("ACCESSIBILITY AUDIT REPORT")
    elif report_type == "unified":
        text.append("ACCESSIBILITY AUDIT & REMEDIATION REPORT")
    else:
        text.append("ACCESSIBILITY REMEDIATION REPORT")

    text.append("=" * 80)
    text.append("")

    # Add summary section
    text.append("SUMMARY")
    text.append("-" * 80)

    # Add file information
    if "html_path" in report_data:
        text.append(f"File: {report_data.get('html_path')}")

    # Add issue counts
    if "total_issues" in report_data:
        text.append(f"Total issues: {report_data.get('total_issues', 0)}")
    elif "issues_processed" in report_data:
        text.append(f"Issues processed: {report_data.get('issues_processed', 0)}")

    if "issues_remediated" in report_data:
        text.append(f"Issues remediated: {report_data.get('issues_remediated', 0)}")

    if "issues_failed" in report_data:
        text.append(f"Issues failed: {report_data.get('issues_failed', 0)}")

    text.append("")

    # Add issues section
    text.append("ISSUES")
    text.append("-" * 80)

    # Add issues details
    issues = report_data.get("issues", []) or report_data.get("details", [])
    if issues:
        for i, issue in enumerate(issues):
            text.append(f"Issue {i+1}:")
            text.append(f"  Type: {issue.get('type', 'unknown')}")
            text.append(f"  Severity: {issue.get('severity', 'unknown')}")
            text.append(f"  Message: {issue.get('message', '')}")

            if "selector" in issue and issue["selector"]:
                text.append(f"  Selector: {issue.get('selector', '')}")

            if "remediation_status" in issue:
                text.append(f"  Status: {issue.get('remediation_status', 'unknown')}")

            text.append("")
    else:
        text.append("No issues found.")
        text.append("")

    # Write the text to the output file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(text))

    logger.info(f"Generated text report: {output_path}")
    return report_data


def prepare_unified_report_data(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare data for a unified report that combines audit and remediation information.

    Args:
        report_data: Dictionary containing report data (can be audit data, remediation data, or both)

    Returns:
        Processed data ready for the unified report template
    """
    # Create a new dictionary for the unified report
    unified_data = dict(report_data)

    # Check if remediation data is present
    has_remediation = False

    # Check for common remediation indicators
    if (
        "issues_remediated" in report_data
        or "issues_processed" in report_data
        or "file_results" in report_data
        or "details" in report_data  # Check for details list
        or any("remediation_status" in issue for issue in report_data.get("issues", []))
    ):
        has_remediation = True
        unified_data["has_remediation"] = True
    else:
        unified_data["has_remediation"] = False

    # Add audit summary data if present (including compliant vs non-compliant counts)
    if "summary" in report_data:
        # Make sure we keep these fields from the summary
        for key in [
            "total_issues",
            "needs_remediation",
            "remediated",
            "auto_remediated",
            "compliant",
        ]:
            if key in report_data["summary"]:
                unified_data[key] = report_data["summary"][key]

        # Ensure total_issues is set
        if "total_issues" in report_data["summary"]:
            unified_data["total_issues"] = report_data["summary"]["total_issues"]

    # Collect issues from all possible sources
    all_issues = []

    # Check for audit issues in by_page structure (common in audit reports)
    if "by_page" in report_data:
        for page_num, page_data in report_data["by_page"].items():
            if "issues" in page_data and isinstance(page_data["issues"], list):
                for issue in page_data["issues"]:
                    all_issues.append(issue)
                logger.info(
                    f"Found {len(page_data['issues'])} issues in by_page[{page_num}]"
                )

    # Check for audit issues in by_status structure
    if "by_status" in report_data:
        for status, status_issues in report_data["by_status"].items():
            if isinstance(status_issues, list):
                # Skip issues with circular references (common in audit reports)
                clean_issues = []
                for issue in status_issues:
                    if isinstance(issue, dict) and not issue.get("$ref"):
                        clean_issues.append(issue)

                if clean_issues:
                    all_issues.extend(clean_issues)
                    logger.debug(
                        f"Found {len(clean_issues)} clean issues in by_status[{status}]"
                    )

    # Check for issues in the main 'issues' list
    if "issues" in report_data and isinstance(report_data["issues"], list):
        # Skip issues with circular references
        clean_issues = []
        for issue in report_data["issues"]:
            if isinstance(issue, dict) and not issue.get("$ref"):
                clean_issues.append(issue)

        if clean_issues:
            all_issues.extend(clean_issues)
            logger.debug(f"Found {len(clean_issues)} clean issues in main issues list")

    # Check for remediation details
    if "details" in report_data and isinstance(report_data["details"], list):
        all_issues.extend(report_data["details"])
        logger.debug(f"Found {len(report_data['details'])} issues in details list")

    # Extract issues from file_results for remediation data
    if "file_results" in unified_data:
        file_result_issues = []
        for file_result in unified_data.get("file_results", []):
            # Get issues from details
            file_issues = file_result.get("details", []) or []
            for issue in file_issues:
                # Add file path to each issue if not already present
                if "file_path" not in issue:
                    issue["file_path"] = file_result.get("file_path", "")
                file_result_issues.append(issue)

        if file_result_issues:
            all_issues.extend(file_result_issues)
            logger.debug(
                f"Extracted {len(file_result_issues)} issues from file_results"
            )

    # Deduplicate issues
    seen_ids = set()
    unified_issues = []

    for issue in all_issues:
        # Create a unique ID for deduplication
        issue_id = issue.get("id")
        if not issue_id:
            # Create a composite ID from type, severity, and selector/element if available
            issue_type = issue.get("type", "unknown")
            severity = issue.get("severity", "unknown")
            selector = issue.get("selector", issue.get("element", ""))
            issue_id = f"{issue_type}-{severity}-{selector}"

        if issue_id not in seen_ids:
            seen_ids.add(issue_id)
            # Give the issue an ID if it doesn't have one
            if "id" not in issue:
                issue["id"] = issue_id
            unified_issues.append(issue)

    # Update issues in unified data
    if unified_issues:
        unified_data["issues"] = unified_issues
        logger.debug(f"Final unified issues count: {len(unified_issues)}")
    elif not unified_data.get("issues"):
        # Ensure there's an empty list if no issues were found
        unified_data["issues"] = []
        logger.warning("No issues found in any source")

    # Ensure all issues have IDs for linking audit with remediation
    for i, issue in enumerate(unified_data.get("issues", [])):
        if not issue.get("id"):
            # Create a consistent ID format: type-severity-index
            issue["id"] = (
                f"{issue.get('type', 'issue')}-{issue.get('severity', 'minor')}-{i+1}"
            )

    # Ensure we have proper severity and issue type counts
    if unified_data.get("issues"):
        # Initialize count dictionaries
        severity_counts = {"critical": 0, "major": 0, "minor": 0, "info": 0}
        identified_issue_type_counts = {}
        remediated_issue_type_counts = {}
        compliant_issue_type_counts = {}
        non_compliant_issue_type_counts = {}

        # Initialize severity breakdowns
        severity_compliant_counts = {"critical": 0, "major": 0, "minor": 0, "info": 0}
        severity_non_compliant_counts = {
            "critical": 0,
            "major": 0,
            "minor": 0,
            "info": 0,
        }

        for issue in unified_data["issues"]:
            # Get issue properties
            severity = issue.get("severity", "minor")
            issue_type = issue.get("type", "unknown")

            # Initialize counters for this issue type if needed
            if issue_type not in identified_issue_type_counts:
                identified_issue_type_counts[issue_type] = 0
                remediated_issue_type_counts[issue_type] = 0
                compliant_issue_type_counts[issue_type] = 0
                non_compliant_issue_type_counts[issue_type] = 0

            # Count all issues by type (identified)
            identified_issue_type_counts[issue_type] += 1

            # Count by severity
            if severity in severity_counts:
                severity_counts[severity] += 1

            # Determine compliance status
            status = issue.get("remediation_status", "")
            compliance_status = issue.get("status", "")

            # Issue is already compliant
            if compliance_status == "compliant" or issue_type.startswith("compliant-"):
                compliant_issue_type_counts[issue_type] += 1
                if severity in severity_compliant_counts:
                    severity_compliant_counts[severity] += 1

            # Issue was remediated to be compliant
            elif status == "remediated":
                remediated_issue_type_counts[issue_type] += 1
                if severity in severity_compliant_counts:
                    severity_compliant_counts[severity] += 1

            # Issue is non-compliant (needs remediation)
            else:
                non_compliant_issue_type_counts[issue_type] += 1
                if severity in severity_non_compliant_counts:
                    severity_non_compliant_counts[severity] += 1

        # Add the counts to the report data
        unified_data["severity_counts"] = severity_counts
        unified_data["severity_compliant_counts"] = severity_compliant_counts
        unified_data["severity_non_compliant_counts"] = severity_non_compliant_counts
        unified_data["identified_issue_type_counts"] = identified_issue_type_counts
        unified_data["remediated_issue_type_counts"] = remediated_issue_type_counts
        unified_data["compliant_issue_type_counts"] = compliant_issue_type_counts
        unified_data["non_compliant_issue_type_counts"] = (
            non_compliant_issue_type_counts
        )

        # Make sure total issues is set
        if "total_issues" not in unified_data:
            unified_data["total_issues"] = len(unified_data["issues"])

    # If this is a remediation report being converted to unified format,
    # ensure we have the proper remediation counts
    if has_remediation:
        # Set remediation stats if not already present
        if "issues_processed" not in unified_data:
            unified_data["issues_processed"] = unified_data.get("total_issues", 0)

        if "issues_remediated" not in unified_data:
            unified_data["issues_remediated"] = sum(
                1
                for issue in unified_data.get("issues", [])
                if issue.get("remediation_status") == "remediated"
            )

        if "issues_failed" not in unified_data:
            unified_data["issues_failed"] = sum(
                1
                for issue in unified_data.get("issues", [])
                if issue.get("remediation_status") == "failed"
            )

    return unified_data


def generate_csv_report(
    report_data: Dict[str, Any], output_path: str, report_type: str
) -> Dict[str, Any]:
    """
    Generate a CSV report using defusedcsv for enhanced security.

    Args:
        report_data: Dictionary containing the report data
        output_path: Path where the report will be saved
        report_type: Type of report ('accessibility' or 'remediation')

    Returns:
        The report data
    """
    try:
        from defusedcsv import writer
    except ImportError:
        logger.warning("defusedcsv not installed. Falling back to JSON report.")
        return generate_json_report(report_data, output_path)

    # Generate CSV report
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        # Create CSV writer
        csv_writer = writer(f)

        # Add header row based on report type
        if report_type == "accessibility":
            csv_writer.writerow(
                [
                    "ID",
                    "Type",
                    "Severity",
                    "Message",
                    "Selector",
                    "File Path",
                    "Fix Available",
                ]
            )
        else:
            # For unified and remediation reports, use the same headers
            csv_writer.writerow(
                ["ID", "Type", "Severity", "Status", "Message", "Selector", "File Path"]
            )

        # Add issues data
        issues = report_data.get("issues", []) or report_data.get("details", [])
        for issue in issues:
            if report_type == "accessibility":
                csv_writer.writerow(
                    [
                        issue.get("id", ""),
                        issue.get("type", "unknown"),
                        issue.get("severity", "unknown"),
                        issue.get("message", ""),
                        issue.get("selector", ""),
                        issue.get("file_path", "")
                        or (issue.get("location", {}) or {}).get("file_path", ""),
                        issue.get("fix_available", False),
                    ]
                )
            else:
                csv_writer.writerow(
                    [
                        issue.get("id", ""),
                        issue.get("type", "unknown"),
                        issue.get("severity", "unknown"),
                        issue.get("remediation_status", "unknown"),
                        issue.get("message", ""),
                        issue.get("selector", ""),
                        issue.get("file_path", "")
                        or (issue.get("location", {}) or {}).get("file_path", ""),
                    ]
                )

    logger.info(f"Generated CSV report: {output_path}")
    return report_data
