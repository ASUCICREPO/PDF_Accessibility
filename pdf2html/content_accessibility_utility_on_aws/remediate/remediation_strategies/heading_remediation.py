# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Heading accessibility remediation strategies.

This module provides remediation strategies for heading-related accessibility issues.
"""

from typing import Dict, Any, Optional
from bs4 import BeautifulSoup, Tag
import re

from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger

# Set up module-level logger
logger = setup_logger(__name__)


def remediate_missing_h1(
    soup: BeautifulSoup, issue: Dict[str, Any], *args
) -> Optional[str]:
    """
    Remediate missing h1 heading in the document.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    # Check if we already have an h1
    if soup.find("h1"):
        logger.debug("Document already has an h1 heading")
        return "Document already has an h1 heading"

    # Find the best place to insert the h1
    # Try to get document title as content for h1
    title_tag = soup.find("title")
    title_text = title_tag.get_text(strip=True) if title_tag else "Document Title"

    # Find best location for h1
    insertion_point = None

    # Try to find a header element or div that might be a header
    header = soup.find("header")
    if header:
        insertion_point = header
        # Insert at the beginning of the header
    else:
        # Try to find a likely header div
        potential_headers = soup.select('div[class*="header"], div[id*="header"]')
        if potential_headers:
            insertion_point = potential_headers[0]

    # If no header found, try to find the main content
    if not insertion_point:
        main = soup.find("main")
        if main:
            insertion_point = main
        else:
            # If no main, use body
            body = soup.find("body")
            if body:
                insertion_point = body
            else:
                # Fall back to the root element
                insertion_point = soup

    # Create and insert the h1
    h1 = soup.new_tag("h1")
    h1.string = title_text


    first_child = next(insertion_point.children, None)
    if first_child:
        first_child.insert_before(h1)
    else:
        insertion_point.append(h1)


    return f"Added h1 heading with content: '{title_text}'"


def remediate_missing_headings(
    soup: BeautifulSoup, issue: Dict[str, Any], *args
) -> Optional[str]:
    """
    Remediate missing heading structure by converting appropriate text blocks to headings.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    # Check if we already have any headings
    existing_headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    if existing_headings:
        logger.debug(f"Document already has {len(existing_headings)} headings")
        return f"Document already has {len(existing_headings)} headings"

    # Find potential text blocks that could be headings
    potential_headings = []

    # Look for text elements with characteristics of headings
    # Check paragraphs with bold or strong text
    bold_paras = []
    for p in soup.find_all("p"):
        if p.find(["b", "strong"]) and len(p.get_text(strip=True)) < 100:
            bold_paras.append(p)

    # Check standalone divs with short text
    short_divs = []
    for div in soup.find_all("div"):
        # If it has minimal children and short text
        if len(list(div.children)) <= 3 and len(div.get_text(strip=True)) < 100:
            # And doesn't contain other block elements
            if not div.find(["p", "div", "table"]):
                short_divs.append(div)

    # Check elements with "title" or "heading" in class or id
    title_elements = soup.select(
        '[class*="title"], [class*="heading"], [id*="title"], [id*="heading"]'
    )

    # Combine all potential headings
    potential_headings = bold_paras + short_divs + title_elements

    # If no potential headings found, we can't remediate
    if not potential_headings:
        logger.warning("No potential headings found to convert")
        return None

    # Convert the first element to h1 if no h1 exists
    if not soup.find("h1") and potential_headings:
        element = potential_headings[0]
        text = element.get_text(strip=True)
        h1 = soup.new_tag("h1")
        h1.string = text
        element.replace_with(h1)
        potential_headings.pop(0)
        logger.debug(f"Converted element to h1: {text}")

    # Convert remaining potential headings to h2
    heading_count = 0
    for element in potential_headings[:5]:  # Limit to converting 5 elements
        text = element.get_text(strip=True)
        h2 = soup.new_tag("h2")
        h2.string = text
        element.replace_with(h2)
        heading_count += 1
        logger.debug(f"Converted element to h2: {text}")

    if heading_count > 0:
        return f"Added {heading_count + 1} headings by converting text elements"
    else:
        return (
            "Added h1 heading but found no other text elements to convert to headings"
        )


def remediate_skipped_heading_level(
    soup: BeautifulSoup, issue: Dict[str, Any], *args
) -> Optional[str]:
    """
    Remediate skipped heading levels by adding intermediate headings.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    # Extract element path from the issue
    path = issue.get("location", {}).get("path")
    if not path:
        logger.warning("No element path provided in issue")
        return None

    # Find the problematic heading
    heading = None
    for h_tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        # This is a simplified selector match - in practice we would need more robust matching
        if path.lower() in str(h_tag).lower():
            heading = h_tag
            break

    if not heading:
        logger.warning(f"Could not find heading element with path: {path}")
        return None

    # Get current heading level
    current_level = int(heading.name[1])

    # Find previous heading to determine the skipped level
    prev_heading = heading.find_previous(["h1", "h2", "h3", "h4", "h5", "h6"])
    if not prev_heading:
        logger.debug("No previous heading found, cannot determine skipped level")
        return None

    prev_level = int(prev_heading.name[1])

    # Check if there's a skip
    if current_level - prev_level <= 1:
        logger.debug("No heading level skip detected")
        return None

    # Create intermediate headings
    for level in range(prev_level + 1, current_level):
        # Create new heading with interpolated level
        new_heading = soup.new_tag(f"h{level}")

        # Generate appropriate text based on surrounding headings
        if prev_heading.get_text(strip=True) and heading.get_text(strip=True):
            prev_text = prev_heading.get_text(strip=True)
            current_text = heading.get_text(strip=True)
            new_heading.string = f"{prev_text} - {current_text}"
        else:
            new_heading.string = f"Section Heading {level}"

        # Flag as auto-generated
        new_heading["data-auto-generated"] = "true"

        # Insert before the current heading
        heading.insert_before(new_heading)
        logger.debug(f"Added intermediate h{level} heading")

    return f"Added {current_level - prev_level - 1} intermediate heading(s)"


def remediate_empty_heading_content(
    soup: BeautifulSoup, issue: Dict[str, Any], *args
) -> Optional[str]:
    """
    Remediate empty or non-descriptive heading content.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    # Extract element path from the issue
    path = issue.get("location", {}).get("path")
    if not path:
        logger.warning("No element path provided in issue")
        return None

    # Find the problematic heading
    heading = None
    for h_tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        # This is a simplified selector match - in practice we would need more robust matching
        if path.lower() in str(h_tag).lower():
            heading = h_tag
            break

    if not heading:
        logger.warning(f"Could not find heading element with path: {path}")
        return None

    # Check if heading is empty or contains generic text
    heading_text = heading.get_text(strip=True)
    if not heading_text or re.match(
        r"^(heading|title|section|\s*\d+\s*)$", heading_text, re.IGNORECASE
    ):
        # Get the heading level
        level = int(heading.name[1])

        # Analyze surrounding content for context
        context_text = ""

        # Get following paragraph text
        next_p = heading.find_next("p")
        if next_p:
            context_text = next_p.get_text(strip=True)[:100]

        # If no paragraph, get any text in the same section
        if not context_text:
            # Find the next heading of same or higher level
            next_heading = heading.find_next(
                ["h1", "h2", "h3", "h4", "h5", "h6"],
                lambda tag: int(tag.name[1]) <= level,
            )

            # Collect all text between this heading and next
            text_content = []
            current = heading.next_sibling
            while current and (not next_heading or current != next_heading):
                if isinstance(current, Tag):
                    text = current.get_text(strip=True)
                    if text:
                        text_content.append(text)
                current = current.next_sibling

            if text_content:
                context_text = " ".join(text_content)[:100]

        # Generate heading text based on context and level
        if context_text:
            # Extract key phrases or summarize
            words = context_text.split()
            if len(words) > 5:
                new_heading_text = " ".join(words[:5]) + "..."
            else:
                new_heading_text = context_text
        else:
            # Generate from heading position and structure
            if level == 1:
                new_heading_text = "Document Title"
            else:
                siblings = len(list(heading.find_previous_siblings(heading.name)))
                new_heading_text = f"Section {siblings + 1}"

        # Update heading text
        heading.string = new_heading_text
        return f"Updated empty heading content to: {new_heading_text}"

    return None
