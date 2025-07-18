# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Table accessibility remediation strategies.

This module provides remediation strategies for table-related accessibility issues.
"""

from typing import Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup, Tag
import re
import json
from difflib import SequenceMatcher
from content_accessibility_utility_on_aws.utils.logging_helper import (
    setup_logger,
)
from content_accessibility_utility_on_aws.remediate.services.bedrock_client import (
    BedrockClient,
)

# Set up module-level logger
logger = setup_logger(__name__)


def get_table_from_issue(soup: BeautifulSoup, issue: Dict[str, Any]) -> Optional[Tag]:
    """
    Helper function to find the specific table from an issue.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue containing table information

    Returns:
        The specific table element if found, None otherwise
    """
    logger.debug(f"Finding table element for issue: {issue}")
    element_str = issue.get("element", "")
    element_selector = issue.get("selector", "")
    context = issue.get("context", {})
    file_path = issue.get("location", {}).get("file_path", "")

    logger.debug(f"Searching for table with selector: {element_selector}")
    logger.debug(f"Element string: {element_str[:100]}...")
    logger.debug(f"Context data: {json.dumps(context, indent=2)}")
    logger.debug(f"File path from issue: {file_path}")

    # First try direct selector match
    if element_selector:
        try:
            logger.debug(f"Attempting selector match: {element_selector}")
            table = soup.select_one(element_selector)
            if table and table.name == "table":
                logger.debug(f"Found table via selector: {element_selector}")
                return table
            else:
                logger.debug(
                    f"Selector {element_selector} didn't match a table element"
                )
        except Exception as e:
            logger.warning(f"Selector match failed: {str(e)}")

    # Try using the element string
    if element_str:
        # If it's just the tag name
        if element_str == "table":
            # Use context to find the right table
            context = issue.get("context", {})
            text_content = context.get("text", "")

            # Try to find table by surrounding text content
            if text_content:
                for table in soup.find_all("table"):
                    if text_content in table.get_text():
                        return table

            # If no text match, try using position/index if available
            index = context.get("index", 0)
            tables = soup.find_all("table")
            if 0 <= index < len(tables):
                return tables[index]

        # If it's an HTML string
        elif element_str.startswith("<table"):
            # Try to find matching table structure
            for table in soup.find_all("table"):
                # Compare structure (ignoring whitespace)
                if re.sub(r"\s+", "", str(table)) == re.sub(r"\s+", "", element_str):
                    return table

    # If we have multiple tables, try to find one that matches the issue type
    issue_type = issue.get("type", "")
    if issue_type:
        for table in soup.find_all("table"):
            if issue_type == "table-missing-headers" and not table.find("th"):
                return table
            elif issue_type == "table-missing-scope" and table.find("th", scope=False):
                return table
            elif issue_type == "table-missing-thead" and not table.find("thead"):
                return table
            elif issue_type == "table-missing-tbody" and not table.find("tbody"):
                return table
            elif issue_type == "table-irregular-headers" and table.find("th"):
                # Check for irregular header structure
                headers = table.find_all("th")
                if any(not h.get("scope") for h in headers):
                    return table

    # If all else fails, try finding all tables and adding scope to all headers
    if issue_type and issue_type.startswith("table-"):
        tables = soup.find_all("table")
        if tables:
            logger.debug(
                f"No specific table found for {issue_type}, returning first table as fallback"
            )
            return tables[0]

    return None


def remediate_table_headers_id(
    soup: BeautifulSoup, issue: Dict[str, Any], *args
) -> Optional[str]:
    """
    Remediate tables with missing header IDs by adding IDs to headers and linking cells.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    logger.debug(f"Remediating missing header IDs in table")
    table = get_table_from_issue(soup, issue)
    if not table:
        logger.warning("Could not find table element for remediation")
        return None

    # Find all header cells
    headers = table.find_all("th")
    if not headers:
        logger.warning("Table has no header cells to add IDs to")
        return None

    # Add IDs to all headers
    modified = False
    for i, th in enumerate(headers):
        if not th.get("id"):
            # Create a unique ID based on text content or position
            if th.get_text(strip=True):
                id_text = th.get_text(strip=True).lower()
                # Remove non-alphanumeric characters and replace spaces with hyphens
                id_text = "".join(c if c.isalnum() else "-" for c in id_text)
                # Ensure it starts with a letter
                if not id_text or not id_text[0].isalpha():
                    id_text = f"header-{i+1}"
                th["id"] = f"th-{id_text[:20]}"  # Limit length
            else:
                th["id"] = f"th-{i+1}"
            modified = True

    # Link data cells to headers
    headers_with_ids = [th for th in headers if th.get("id")]
    if headers_with_ids:
        # Get header positions
        header_map = {}

        # Map header positions by row and column
        for th in headers_with_ids:
            # Find parent row and index within row
            parent_row = th.parent
            if parent_row and parent_row.name == "tr":
                row_index = (
                    list(parent_row.parent.find_all("tr")).index(parent_row)
                    if parent_row.parent
                    else 0
                )
                cell_index = list(parent_row.find_all(["th", "td"])).index(th)
                header_map[(row_index, cell_index)] = th.get("id")

        # Apply headers attribute to data cells
        for row_idx, tr in enumerate(table.find_all("tr")):
            for col_idx, td in enumerate(tr.find_all("td")):
                headers_for_cell = []

                # Column headers are in row 0
                if (0, col_idx) in header_map:
                    headers_for_cell.append(header_map[(0, col_idx)])

                # Row headers are in column 0
                if (row_idx, 0) in header_map:
                    headers_for_cell.append(header_map[(row_idx, 0)])

                # Add headers attribute if we found relevant headers
                if headers_for_cell:
                    td["headers"] = " ".join(headers_for_cell)
                    modified = True

    if modified:
        return "Added IDs to table headers and linked data cells with headers attribute"

    return None


def remediate_table_missing_headers(
    soup: BeautifulSoup, issue: Dict[str, Any], *args
) -> Optional[str]:
    """
    Remediate tables with missing header cells by converting first row to headers.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    logger.debug("Remediating missing header cells in table")
    table = get_table_from_issue(soup, issue)
    if not table:
        return None

    # Check if the table has any th elements
    if not table.find("th"):
        # Get the first row
        first_row = table.find("tr")
        if first_row:
            # Convert all td elements in the first row to th
            for td in first_row.find_all("td"):
                td.name = "th"
            return "Converted first row cells to header cells"

    return None


def normalize_header_text(text: str) -> str:
    """
    Normalize header text for more reliable matching.

    Args:
        text: The header text to normalize

    Returns:
        Normalized text (lowercase, no extra whitespace, no special chars)
    """

    if not text:
        return ""

    # Convert to lowercase
    normalized = text.lower()

    # Replace multiple whitespace with single space
    normalized = re.sub(r"\s+", " ", normalized)

    # Remove non-alphanumeric characters
    normalized = re.sub(r"[^a-z0-9 ]", "", normalized)

    # Remove leading/trailing whitespace
    normalized = normalized.strip()

    return normalized


def fuzzy_match_header(
    ai_headers: Dict[str, str], actual_header: str, threshold: float = 0.6
) -> Tuple[Optional[str], Optional[str]]:
    """
    Find the best match for a header in the AI response using fuzzy matching.

    Args:
        ai_headers: Dictionary mapping header text to scope value from AI
        actual_header: The actual header text to match
        threshold: Minimum similarity ratio to consider a match

    Returns:
        Tuple of (matched_header, scope_value) or (None, None) if no match found
    """
    best_match = None
    best_ratio = 0.0
    best_scope = None

    normalized_actual = normalize_header_text(actual_header)

    # Check for exact normalized match first
    for ai_text, scope in ai_headers.items():
        normalized_ai = normalize_header_text(ai_text)
        if normalized_actual == normalized_ai:
            return ai_text, scope

    # If no exact match, try fuzzy matching
    for ai_text, scope in ai_headers.items():
        normalized_ai = normalize_header_text(ai_text)
        # Skip empty texts
        if not normalized_actual or not normalized_ai:
            continue

        ratio = SequenceMatcher(None, normalized_actual, normalized_ai).ratio()

        if ratio > best_ratio:
            best_ratio = ratio
            best_match = ai_text
            best_scope = scope

    if best_ratio >= threshold:
        logger.debug(
            f"Fuzzy matched '{actual_header}' to '{best_match}' with confidence {best_ratio:.2f}"
        )
        return best_match, best_scope

    return None, None


def infer_scope_from_position(table: Tag, th: Tag) -> str:
    """
    Enhanced scope inference based on header position in table.

    Args:
        table: The table element
        th: The header element

    Returns:
        Either 'col' or 'row' based on position
    """
    # Find parent row and its position
    parent_row = th.parent
    if not parent_row or parent_row.name != "tr":
        return "col"  # Default to column header

    # Check if header is in thead - these are almost always column headers
    if th.parent.parent and th.parent.parent.name == "thead":
        return "col"

    # Get all rows in the table
    all_rows = table.find_all("tr")
    row_index = list(all_rows).index(parent_row) if parent_row in all_rows else -1

    # Get position of cell in row
    cell_index = (
        list(parent_row.find_all(["th", "td"])).index(th)
        if th in parent_row.find_all(["th", "td"])
        else -1
    )

    # First row headers are typically column headers
    if row_index == 0:
        return "col"
    # First column headers are typically row headers
    elif cell_index == 0:
        return "row"

    # Headers in the second row but possibly part of header structure
    if (
        row_index == 1
        and table.find("thead")
        and th.parent in table.find("thead").find_all("tr")
    ):
        return "col"

    # Check for "rowheader" role or similar class names
    if th.get("role") == "rowheader" or any(
        "rowhead" in c.lower() for c in th.get("class", [])
    ):
        return "row"
    if th.get("role") == "columnheader" or any(
        "colhead" in c.lower() for c in th.get("class", [])
    ):
        return "col"

    # Default to column header
    return "col"


def remediate_table_missing_scope(
    soup: BeautifulSoup, issue: Dict[str, Any], *args
) -> Optional[str]:
    """
    Proactively add scope attributes to header cells in tables using AI analysis and fallback methods.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate
        args: Additional arguments, including potential BedrockClient

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    logger.debug("Remediating missing scope attributes in table headers")
    # Try to find the specific table first
    table = get_table_from_issue(soup, issue)
    logger.debug(f"Found table: {table}")
    if not table or table.name != "table":
        logger.warning("No valid table element found for remediation")
        # If no specific table found for this issue, try processing all tables
        logger.warning(
            "No specific table found for this issue - will attempt to fix all tables"
        )
        tables = soup.find_all("table")
        if not tables:
            logger.warning("No tables found in document")
            return None

        # If we have multiple tables, just remediate all of them
        # This is a last resort approach when we can't identify the specific table
        fallback_total = 0
        tables_modified = 0

        for table in tables:
            logger.debug(
                f"Remediating table with {len(table.find_all('th', scope=False))} missing scope attributes"
            )
            # Skip tables that already have proper scope attributes
            headers = table.find_all("th", scope=False)
            if not headers:
                # No headers without scope, nothing to do
                logger.debug("Table already has proper scope attributes")
                continue

            # Apply scope attributes based on position
            modified = False
            for th in headers:
                logger.debug(
                    f"Adding scope attribute to header cell: {th.get_text(strip=True)}"
                )
                scope_value = infer_scope_from_position(table, th)
                th["scope"] = scope_value
                modified = True
                fallback_total += 1

            if modified:
                logger.debug(f"Added scope attributes to table header cells")
                tables_modified += 1

        if tables_modified > 0:
            logger.debug(
                f"Added scope attributes to {fallback_total} header cells across {tables_modified} tables using fallback method"
            )
            return f"Added scope attributes to {fallback_total} header cells across {tables_modified} tables using fallback method"
        else:
            logger.warning("No header cells were modified during scope remediation")
            return None

    # Find all header cells (th) without scope attributes
    headers = table.find_all("th", scope=False)
    if not headers:
        logger.debug("Table already has proper scope attributes")
        # No headers without scope, nothing to do
        return "Table already has proper scope attributes"

    # Extract the BedrockClient if provided
    bedrock_client = None
    if args:
        logger.debug(f"Checking for BedrockClient in arguments: {args}")
        for arg in args:
            logger.debug(f"Checking argument: {arg}")
            if arg is not None and isinstance(arg, BedrockClient):
                bedrock_client = arg
                logger.debug(
                    f"Using provided BedrockClient with model: {bedrock_client.model_id}, profile: {bedrock_client.profile}"
                )
                break

    # AI is required for table remediation
    if not bedrock_client:
        logger.debug("BedrockClient not available for table scope remediation")
        # IMPORTANT: Instead of raising an error, use fallback method when AI is not available
        logger.warning(
            "BedrockClient not available for table scope remediation - using fallback method"
        )
        fallback_count = 0
        modified = False

        # Apply fallback scope determination to all headers without scope
        for th in headers:
            scope_value = infer_scope_from_position(table, th)
            th["scope"] = scope_value
            modified = True
            fallback_count += 1

        if modified:
            message = f"Added scope attributes to {fallback_count} header cells using fallback method (no AI available)"
            logger.debug(message)
            return message
        else:
            return None

    # Find all th elements
    headers = table.find_all("th")
    if not headers:
        logger.warning("No header cells found in table")
        return None

    # Get table structure for analysis
    table_html = str(table)

    # Collect actual header texts for validation
    actual_headers = [h.get_text(strip=True) for h in headers]
    header_texts = ", ".join([f'"{h}"' for h in actual_headers if h])

    # Create a more specific prompt that includes the actual header texts
    prompt = f"""
    Analyze this HTML table structure and determine the appropriate scope attribute (col or row) 
    for each header cell (<th>).
    
    The table contains these headers: {header_texts}
    
    You MUST include ALL of these headers in your response, including:
    - Headers with nested elements (like images, spans, etc.)
    - Headers with complex formatting
    - Empty header cells
    
    Determine if each header is a column header (scope="col") or row header (scope="row").
    
    HTML Table:
    {table_html}
    
    IMPORTANT: Respond ONLY with a valid JSON object where:
    - Keys should be the EXACT text content of header cells (include text of any nested elements)
    - Values must be EXACTLY either "col" or "row" (lowercase)
    - Include ALL headers in your response, even empty ones (use "empty-header-N" for empty headers)
    - Be accurate with spelling, case, and whitespace in keys
    - If header contains special characters or no text, still include it in your analysis
    
    Example format:
    {{
        "Header1": "col",
        "Header2": "col",
        "Row Header": "row",
        "empty-header-1": "col"
    }}
    """

    # Track retry attempts
    max_retries = 3
    table_analysis = None
    last_error = None

    # Attempt AI analysis with retries
    for attempt in range(max_retries):
        try:
            json_response = bedrock_client.generate_text(prompt, purpose="table_remediation", max_tokens=2000)

            # Extract JSON from the response
            json_start = json_response.find("{")
            json_end = json_response.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_text = json_response[json_start:json_end]
                try:
                    table_analysis = json.loads(json_text)
                    logger.debug(
                        f"AI analysis of table headers (attempt {attempt+1}): {table_analysis}"
                    )
                    break
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON response: {e}")
                    last_error = str(e)

                    if attempt == max_retries - 1:
                        # On final retry, don't fail completely - use fallback approach
                        logger.error(
                            f"Failed to parse AI response as JSON after {max_retries} attempts"
                        )
                        table_analysis = {}  # Empty analysis will trigger fallbacks
            else:
                # No valid JSON found
                logger.warning("AI returned no valid JSON for table analysis")
                if attempt == max_retries - 1:
                    # On final retry, don't fail completely - use fallback approach
                    table_analysis = {}

        except Exception as e:
            logger.warning(
                f"Failed to use AI for table analysis (attempt {attempt+1}): {e}"
            )
            last_error = str(e)

            if attempt == max_retries - 1:
                # On final retry, don't fail completely - use fallback approach
                logger.error(
                    f"AI table analysis failed after {max_retries} attempts: {last_error}"
                )
                table_analysis = {}

    # Process headers with the analysis we have (might be empty)
    modified = False
    fallback_count = 0
    ai_match_count = 0

    # Check if AI missed any headers and use fallback for those
    actual_header_texts = [h.get_text(strip=True) for h in headers]

    # Handle empty headers specially
    empty_header_count = 0
    empty_header_map = {}

    for i, header_text in enumerate(actual_header_texts):
        if not header_text:
            empty_key = f"empty-header-{empty_header_count + 1}"
            if empty_key in table_analysis:
                empty_header_map[i] = empty_key
            empty_header_count += 1

    # Add missing headers to analysis with fallback values
    missing_headers = []
    for i, header_text in enumerate(actual_header_texts):
        if not header_text:
            # Skip empty headers for now, handled separately
            continue

        if header_text not in table_analysis and i not in [
            headers.index(h) for h, t in missing_headers
        ]:
            # Check if a fuzzy match exists
            matched, _ = fuzzy_match_header(table_analysis, header_text)
            if not matched:
                # No match found - use fallback
                th = headers[i]
                fallback_scope = infer_scope_from_position(table, th)
                missing_headers.append((th, header_text))
                table_analysis[header_text] = fallback_scope
                logger.debug(
                    f"Added missing header '{header_text}' with fallback scope '{fallback_scope}'"
                )

    # First pass: apply AI analysis with fuzzy matching where possible
    for th in headers:
        if th.get("scope"):  # Skip headers that already have scope
            continue

        # Get header text
        header_text = th.get_text(strip=True)

        # Handle empty headers
        if not header_text:
            header_idx = headers.index(th)
            if header_idx in empty_header_map:
                empty_key = empty_header_map[header_idx]
                scope_value = table_analysis.get(empty_key)
                if scope_value in ["col", "row"]:
                    th["scope"] = scope_value
                    modified = True
                    ai_match_count += 1
                    continue

            # Fallback for empty headers
            scope_value = infer_scope_from_position(table, th)
            th["scope"] = scope_value
            modified = True
            fallback_count += 1
            logger.debug(
                f"Using fallback scope '{scope_value}' for empty header at index {headers.index(th)}"
            )
            continue

        # Try exact match first
        if header_text in table_analysis:
            scope_value = table_analysis[header_text]
            if scope_value in ["col", "row"]:
                th["scope"] = scope_value
                modified = True
                ai_match_count += 1
                continue

        # Try fuzzy matching if no exact match
        matched_header, scope_value = fuzzy_match_header(table_analysis, header_text)
        if matched_header and scope_value in ["col", "row"]:
            th["scope"] = scope_value
            modified = True
            ai_match_count += 1
            continue

        # If AI analysis failed completely or didn't provide this header,
        # use positional fallback logic to assign scope
        scope_value = infer_scope_from_position(table, th)
        th["scope"] = scope_value
        modified = True
        fallback_count += 1
        logger.debug(f"Using fallback scope '{scope_value}' for header '{header_text}'")

    # Report on remediation results
    if modified:
        message = f"Added scope attributes to table header cells (AI: {ai_match_count}, Fallback: {fallback_count})"
        logger.debug(message)
        return message
    else:
        logger.warning("No header cells were modified during scope remediation")
        return "No scope attributes were modified"


def remediate_table_missing_caption(
    soup: BeautifulSoup, issue: Dict[str, Any], *args
) -> Optional[str]:
    """
    Remediate tables with missing captions.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    logger.debug("Remediating missing table captions")
    table = get_table_from_issue(soup, issue)
    if not table:
        logger.warning("Could not find table element for remediation")
        return None

    if not table.find("caption"):
        logger.debug("Adding caption to table")
        # Try to generate a caption based on context
        caption_text = "Table data"

        # Look for preceding heading
        prev_heading = table.find_previous(["h1", "h2", "h3", "h4", "h5", "h6"])
        if prev_heading:
            caption_text = prev_heading.get_text(strip=True)

        # Create and insert caption
        caption = soup.new_tag("caption")
        caption.string = caption_text
        table.insert(0, caption)

        return f"Added caption to table: {caption_text}"

    return None


def remediate_table_missing_thead(
    soup: BeautifulSoup, issue: Dict[str, Any], *args
) -> Optional[str]:
    """
    Remediate tables with missing thead elements.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate
        args: Additional arguments, including potential BedrockClient

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    logger.debug("Remediating table missing thead")
    table = get_table_from_issue(soup, issue) or soup.find("table")
    if not table:
        return None

    # Check if table already has thead
    if table.find("thead"):
        logger.debug("Table already has thead element")
        return "Table already has thead element"

    # Extract the BedrockClient if provided
    bedrock_client = None
    if args:
        for arg in args:
            if arg is not None and isinstance(arg, BedrockClient):
                bedrock_client = arg
                logger.debug(
                    f"Using provided BedrockClient with model: {bedrock_client.model_id}, profile: {bedrock_client.profile}"
                )
                break

    # If AI is not available, use fallback method
    if not bedrock_client:
        logger.warning(
            "BedrockClient not available for table thead remediation - using fallback method"
        )

        # First row is typically the header row
        rows = table.find_all("tr")
        if rows:
            first_row = rows[0]
            # Check if first row has header cells
            if first_row.find("th"):
                # Create thead element and move first row into it
                thead = soup.new_tag("thead")
                first_row.extract()
                thead.append(first_row)
                table.insert(0, thead)
                return "Added thead element with first row (fallback method)"
            else:
                # Convert first row cells to headers and then add to thead
                for td in first_row.find_all("td"):
                    td.name = "th"
                thead = soup.new_tag("thead")
                first_row.extract()
                thead.append(first_row)
                table.insert(0, thead)
                return "Converted first row to headers and added thead element (fallback method)"

        return None

    if not table.find("thead"):
        # Find header rows using AI
        header_rows = []
        all_rows = table.find_all("tr")

        # Create a simplified representation of the table
        table_html = str(table)
        prompt = f"""
        Analyze this HTML table structure and determine which rows should be part of the table header (thead).
        Consider semantic meaning, formatting, and the content of cells to identify header rows.
        
        HTML Table:
        {table_html}
        
        Respond with ONLY the zero-based indices of rows that should be in the thead, in JSON array format.
        For example: [0] for just the first row, or [0, 1] for the first and second rows.
        """

        try:
            json_response = bedrock_client.generate_text(prompt, purpose="table_remediation", max_tokens=2000)
            # Extract just the JSON part
            json_start = json_response.find("[")
            json_end = json_response.rfind("]") + 1
            if json_start >= 0 and json_end > json_start:
                json_text = json_response[json_start:json_end]
                header_indices = json.loads(json_text)

                # Get the corresponding rows
                all_rows = table.find_all("tr")
                header_rows = [all_rows[i] for i in header_indices if i < len(all_rows)]
                logger.debug(f"AI identified header rows: {header_indices}")
            else:
                # Fallback: use first row as header
                header_rows = [all_rows[0]] if all_rows else []
                logger.error(
                    "AI returned no valid JSON for thead analysis - using first row as fallback"
                )
        except Exception as e:
            # Fallback: use first row as header
            logger.error(
                f"Failed to use AI for thead analysis: {e} - using first row as fallback"
            )
            header_rows = [all_rows[0]] if all_rows else []

        if header_rows:
            # Create thead element
            thead = soup.new_tag("thead")

            # Move header rows to thead
            for row in header_rows:
                row.extract()
                thead.append(row)

            # Insert thead at the beginning of the table
            table.insert(0, thead)

            return f"Added thead element to table with {len(header_rows)} header row(s)"

    return None


def remediate_table_missing_tbody(
    soup: BeautifulSoup, issue: Dict[str, Any], *args
) -> Optional[str]:
    """
    Remediate tables with missing tbody elements.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate
        args: Additional arguments, including potential BedrockClient

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    logger.debug("Remediating table missing tbody")
    table = get_table_from_issue(soup, issue)
    logger.debug(f"Table: {table}")
    if not table:
        logger.warning("Could not find table element for remediation")
        return None

    # Check if table already has tbody
    if table.find("tbody"):
        logger.debug("Table already has tbody element")
        return "Table already has tbody element"

    # Create tbody element
    tbody = soup.new_tag("tbody")

    # Find all rows that aren't in thead or tfoot
    body_rows = []
    for row in table.find_all("tr"):
        # Skip rows that are already in thead or tfoot
        if row.parent and row.parent.name in ["thead", "tfoot"]:
            continue
        body_rows.append(row)

    # If no body rows, nothing to do
    if not body_rows:
        logger.debug("Table has no body rows to move to tbody")
        return None

    # Move the body rows to tbody
    for row in body_rows:
        row.extract()
        tbody.append(row)

    # Add tbody to table
    table.append(tbody)
    return f"Added tbody element with {len(body_rows)} data rows"


def remediate_table_irregular_headers(
    soup: BeautifulSoup, issue: Dict[str, Any], *args
) -> Optional[str]:
    """
    Remediate tables with irregular or inconsistent header structures.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    # This is essentially a wrapper around remediate_table_missing_scope which handles irregular headers
    return remediate_table_missing_scope(soup, issue, *args)
