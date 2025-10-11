# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Enhanced table accessibility remediation with direct application.

This module extends the table remediation strategies to ensure they're
applied correctly during the document processing workflow.
"""

from typing import Dict, List, Optional, Any, Tuple
from bs4 import BeautifulSoup

from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger
from content_accessibility_utility_on_aws.remediate.remediation_strategies.table_remediation import (
    remediate_table_missing_scope,
    remediate_table_missing_thead,
    remediate_table_missing_tbody,
)

# Set up module-level logger
logger = setup_logger(__name__)


def apply_table_remediation(
    html_content: str,
    audit_issues: Optional[List[Dict[str, Any]]] = None,
    bedrock_client=None,
) -> Tuple[str, int, int]:
    """
    Apply table remediations directly to HTML content.

    Args:
        html_content: The HTML content to remediate
        audit_issues: Optional list of audit issues related to tables
        bedrock_client: Optional BedrockClient instance with AWS credentials

    Returns:
        Tuple of (remediated_html, fixed_count, failed_count)
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Ensure we have a BedrockClient with credentials
    if bedrock_client:
        logger.debug(
            f"Using BedrockClient with model: {bedrock_client.model_id}, profile: {bedrock_client.profile}"
        )
    else:
        # Log a more prominent error since AI is required
        logger.error("No BedrockClient provided, table AI remediation will fail")
        # Early return if no BedrockClient is available - don't try to process without AI
        return html_content, 0, 0

    # Find tables in the document
    tables = soup.find_all("table")
    logger.debug(f"Found {len(tables)} tables in the document")

    # Create issues list if none provided
    table_issues = []
    if audit_issues:
        table_issues = [
            issue
            for issue in audit_issues
            if issue.get("type")
            in ["table-missing-scope", "table-missing-thead", "table-missing-tbody"]
        ]

    # If we don't have issues from an audit report, create mock issues for all tables
    if not table_issues:
        return html_content, 0, 0

    # Apply remediation for each issue
    fixed_count = 0
    failed_count = 0

    # Log the bedrock_client before we start using it
    logger.debug(f"About to use bedrock_client: {bedrock_client}")

    try:
        # First, apply thead remediation to ensure proper table structure
        for issue in [
            i for i in table_issues if i.get("type") == "table-missing-thead"
        ]:
            try:
                # Explicitly log the arguments being passed
                logger.debug(
                    f"Calling remediate_table_missing_thead with bedrock_client: {bedrock_client}"
                )

                # Pass the bedrock_client for AI-powered remediation
                result = remediate_table_missing_thead(soup, issue, bedrock_client)
                if result:
                    logger.debug(f"Fixed {issue.get('type')}: {result}")
                    fixed_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Failed to fix {issue.get('type')}: {e}")
                failed_count += 1

        # Then, apply tbody remediation
        for issue in [
            i for i in table_issues if i.get("type") == "table-missing-tbody"
        ]:
            try:
                # Explicitly log the arguments being passed
                logger.debug(
                    f"Calling remediate_table_missing_tbody with bedrock_client: {bedrock_client}"
                )

                # Pass the bedrock_client for AI-powered remediation
                result = remediate_table_missing_tbody(soup, issue, bedrock_client)
                if result:
                    logger.debug(f"Fixed {issue.get('type')}: {result}")
                    fixed_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Failed to fix {issue.get('type')}: {e}")
                failed_count += 1

        # Finally, apply scope remediation
        for issue in [
            i for i in table_issues if i.get("type") == "table-missing-scope"
        ]:
            try:
                # Explicitly log the arguments being passed
                logger.debug(
                    f"Calling remediate_table_missing_scope with bedrock_client: {bedrock_client}"
                )

                # Pass the bedrock_client for AI-powered remediation
                result = remediate_table_missing_scope(soup, issue, bedrock_client)
                if result:
                    logger.debug(f"Fixed {issue.get('type')}: {result}")
                    fixed_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Failed to fix {issue.get('type')}: {e}")
                failed_count += 1
    except Exception as outer_e:
        logger.error(f"Outer exception in table remediation: {outer_e}")
        return html_content, fixed_count, failed_count

    return str(soup), fixed_count, failed_count


def ensure_table_structure(html_content: str) -> str:
    """
    Ensure that all tables in the HTML content have proper structure.
    This is a simpler function that just adds missing thead/tbody without requiring specific issues.

    Args:
        html_content: The HTML content to fix

    Returns:
        Fixed HTML content
    """
    soup = BeautifulSoup(html_content, "html.parser")
    tables = soup.find_all("table")

    for table in tables:
        # Add thead if missing and we have rows
        if not table.find("thead") and table.find("tr"):
            first_row = table.find("tr")

            # Check if the first row contains th elements or is likely a header
            if first_row.find("th") or all(
                cell.name == "td" and cell.get("scope")
                for cell in first_row.find_all(["td", "th"])
            ):
                # Create thead and move the first row into it
                thead = soup.new_tag("thead")
                first_row.extract()
                thead.append(first_row)
                table.insert(0, thead)

        # Add tbody if missing
        if not table.find("tbody") and table.find("tr"):
            tbody = soup.new_tag("tbody")

            # Get rows that are not in thead or tfoot
            body_rows = []
            for row in table.find_all("tr"):
                if row.parent.name not in ["thead", "tfoot"]:
                    body_rows.append(row)

            # Move the rows to tbody
            for row in body_rows:
                row.extract()
                tbody.append(row)

            # Insert tbody after thead if it exists, otherwise at the beginning
            if table.find("thead"):
                table.find("thead").insert_after(tbody)
            else:
                table.insert(0, tbody)

        # Ensure all headers have scope attributes
        for th in table.find_all("th"):
            if not th.get("scope"):
                # If in first row of thead, it's a column header
                if (
                    th.parent == table.find("thead").find("tr")
                    if table.find("thead")
                    else None
                ):
                    th["scope"] = "col"
                # If first cell in a row, it's likely a row header
                elif th == th.parent.find(["th", "td"]):
                    th["scope"] = "row"
                # Default to col
                else:
                    th["scope"] = "col"

    return str(soup)
