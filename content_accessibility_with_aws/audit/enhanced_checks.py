# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Enhanced accessibility checks for WCAG compliance.

This module provides additional accessibility checks that can be integrated
with the main AccessibilityAuditor class.
"""

import logging
from bs4 import Tag

# Set up module-level logger
logger = logging.getLogger(__name__)


def check_heading_hierarchy(soup, add_issue_callback):
    """
    Check for proper heading hierarchy (WCAG 1.3.1).

    Args:
        soup: BeautifulSoup object of the HTML document
        add_issue_callback: Function to call to add an issue
    """
    headings = []
    for i in range(1, 7):
        headings.extend(soup.find_all(f"h{i}"))

    if not headings:
        return

    # Track heading levels to detect skips
    heading_levels = []
    for heading in headings:
        level = int(heading.name[1])
        heading_levels.append(level)

        # Check if heading level is skipped (e.g., h1 to h3 without h2)
        if level > 1 and level - 1 not in heading_levels:
            add_issue_callback(
                "improper-heading-structure",
                "1.3.1",
                "major",
                element=heading,
                description=f"Heading level skipped: h{level} used without preceding h{level-1}",
            )


def check_document_language(soup, add_issue_callback):
    """
    Check for document language specification (WCAG 3.1.1).

    Args:
        soup: BeautifulSoup object of the HTML document
        add_issue_callback: Function to call to add an issue
    """
    html_tag = soup.find("html")
    if html_tag and not html_tag.has_attr("lang"):
        add_issue_callback(
            "missing-document-language",
            "3.1.1",
            "critical",
            element=html_tag,
            description="Document missing language attribute on HTML element",
        )


def check_page_title(soup, add_issue_callback):
    """
    Check for page title (WCAG 2.4.2).

    Args:
        soup: BeautifulSoup object of the HTML document
        add_issue_callback: Function to call to add an issue
    """
    title_tag = soup.find("title")
    if not title_tag or not title_tag.string or not title_tag.string.strip():
        add_issue_callback(
            "missing-page-title",
            "2.4.2",
            "major",
            element=soup.find("head"),
            description="Document missing title element or title is empty",
        )


def check_main_landmark(soup, add_issue_callback):
    """
    Check for main landmark (WCAG 1.3.1).

    Args:
        soup: BeautifulSoup object of the HTML document
        add_issue_callback: Function to call to add an issue
    """
    main_element = soup.find("main")
    main_role = soup.find(attrs={"role": "main"})
    if not main_element and not main_role:
        add_issue_callback(
            "missing-main-landmark",
            "1.3.1",
            "major",
            element=soup.find("body"),
            description="Document missing main landmark (main element or role='main')",
        )


def check_skip_link(soup, add_issue_callback):
    """
    Check for skip navigation link (WCAG 2.4.1).

    Args:
        soup: BeautifulSoup object of the HTML document
        add_issue_callback: Function to call to add an issue
    """
    # Look for the first few links in the document
    links = soup.find_all("a", limit=5)
    has_skip_link = False

    for link in links:
        href = link.get("href", "")
        text = link.get_text().lower()
        if href.startswith("#") and (
            "skip" in text or "jump" in text or "content" in text or "main" in text
        ):
            has_skip_link = True
            break

    if not has_skip_link:
        add_issue_callback(
            "missing-skip-link",
            "2.4.1",
            "major",
            element=soup.find("body"),
            description="Document missing skip navigation link",
        )


def check_table_structure(soup, add_issue_callback):
    """
    Check for proper table structure (WCAG 1.3.1).

    Args:
        soup: BeautifulSoup object of the HTML document
        add_issue_callback: Function to call to add an issue
    """
    tables = soup.find_all("table")

    for table in tables:
        # Check for table headers
        headers = table.find_all("th")
        if not headers:
            add_issue_callback(
                "missing-table-headers",
                "1.3.1",
                "critical",
                element=table,
                description="Table missing header cells (TH elements)",
            )
        else:
            # Check for scope attribute on headers
            for header in headers:
                if not header.has_attr("scope"):
                    add_issue_callback(
                        "missing-header-scope",
                        "1.3.1",
                        "major",
                        element=header,
                        description="Table header missing scope attribute",
                    )

        # Check for caption
        if not table.find("caption"):
            add_issue_callback(
                "missing-table-caption",
                "1.3.1",
                "minor",
                element=table,
                description="Table missing caption element",
            )

        # Check for complex table structure
        rows = table.find_all("tr")
        if len(rows) > 2 and len(headers) > 2:
            # This might be a complex table, check for headers/id relationships
            data_cells = table.find_all("td")
            cells_with_headers = [
                cell for cell in data_cells if cell.has_attr("headers")
            ]
            if not cells_with_headers and data_cells:
                add_issue_callback(
                    "complex-table-no-ids",
                    "1.3.1",
                    "critical",
                    element=table,
                    description="Complex table missing header IDs and data cell headers attributes",
                )


def check_form_labels(soup, add_issue_callback):
    """
    Check for proper form labels (WCAG 1.3.1, 3.3.2).

    Args:
        soup: BeautifulSoup object of the HTML document
        add_issue_callback: Function to call to add an issue
    """
    # Find all form controls that need labels
    form_controls = soup.find_all(["input", "select", "textarea"])

    for control in form_controls:
        # Skip hidden inputs and buttons
        if control.name == "input" and control.get("type") in [
            "hidden",
            "button",
            "submit",
            "reset",
        ]:
            continue

        # Check for label association
        has_label = False

        # Check for explicit label with for attribute
        control_id = control.get("id")
        if control_id:
            label = soup.find("label", attrs={"for": control_id})
            if label:
                has_label = True

        # Check for aria-label
        if control.has_attr("aria-label") and control["aria-label"].strip():
            has_label = True

        # Check for aria-labelledby
        if control.has_attr("aria-labelledby") and control["aria-labelledby"].strip():
            has_label = True

        # Check for title attribute
        if control.has_attr("title") and control["title"].strip():
            has_label = True

        # If no label found, report issue
        if not has_label:
            add_issue_callback(
                "missing-form-label",
                "3.3.2",
                "critical",
                element=control,
                description=f"{control.name.upper()} element missing accessible label",
            )

        # Check for required attribute without aria-required
        if control.has_attr("required") and not control.has_attr("aria-required"):
            add_issue_callback(
                "missing-aria-required",
                "3.3.2",
                "minor",
                element=control,
                description=f"Required {control.name.upper()} missing aria-required attribute",
            )


def check_link_text(soup, add_issue_callback):
    """
    Check for proper link text (WCAG 2.4.4).

    Args:
        soup: BeautifulSoup object of the HTML document
        add_issue_callback: Function to call to add an issue
    """
    links = soup.find_all("a")

    generic_link_phrases = [
        "click here",
        "click",
        "here",
        "this link",
        "more",
        "read more",
        "details",
        "learn more",
        "link",
        "this",
        "go",
        "go to",
    ]

    for link in links:
        # Check for empty links
        link_text = link.get_text().strip()
        if not link_text and not link.find("img"):
            add_issue_callback(
                "empty-link",
                "2.4.4",
                "critical",
                element=link,
                description="Link has no text content",
            )
            continue

        # Check for generic link text
        link_text_lower = link_text.lower()
        if any(phrase == link_text_lower for phrase in generic_link_phrases):
            add_issue_callback(
                "generic-link-text",
                "2.4.4",
                "major",
                element=link,
                description=f"Link text is generic: '{link_text}'",
            )

        # Check for links with only images and no alt text
        if not link_text:
            img = link.find("img")
            if img and (not img.has_attr("alt") or not img["alt"].strip()):
                add_issue_callback(
                    "link-image-missing-alt",
                    "2.4.4",
                    "critical",
                    element=link,
                    description="Link contains image with missing or empty alt text",
                )


def collect_enhanced_context(element):
    """
    Collect enhanced context information for an element.

    Args:
        element: The HTML element to collect context for

    Returns:
        Dictionary with context information
    """
    if not element or not isinstance(element, Tag):
        return {}

    context = {}

    # Get element attributes
    if hasattr(element, "attrs"):
        context["attributes"] = dict(element.attrs)

    # Get text content
    if hasattr(element, "get_text"):
        text = element.get_text().strip()
        if text:
            context["text"] = text[:100] + ("..." if len(text) > 100 else "")

    # Get surrounding text
    context["surrounding_text"] = {}

    # Previous text
    prev_elem = element.find_previous_sibling()
    if prev_elem and hasattr(prev_elem, "get_text"):
        prev_text = prev_elem.get_text().strip()
        if prev_text:
            context["surrounding_text"]["before"] = prev_text[:100]

    # Next text
    next_elem = element.find_next_sibling()
    if next_elem and hasattr(next_elem, "get_text"):
        next_text = next_elem.get_text().strip()
        if next_text:
            context["surrounding_text"]["after"] = next_text[:100]

    # Get nearest heading
    heading = element.find_previous(["h1", "h2", "h3", "h4", "h5", "h6"])
    if heading:
        context["nearest_heading"] = heading.get_text().strip()

    return context
