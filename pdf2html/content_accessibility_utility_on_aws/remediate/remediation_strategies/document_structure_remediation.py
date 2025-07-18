# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Document structure remediation strategies.

This module provides remediation strategies for document-level accessibility issues.
"""

from typing import Dict, Any, Optional
from bs4 import BeautifulSoup

from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger

# Set up module-level logger
logger = setup_logger(__name__)


def remediate_missing_document_title(
    soup: BeautifulSoup, issue: Dict[str, Any], *args
) -> Optional[str]:
    """
    Remediate missing document title by adding a proper title element.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    # Check if title already exists
    head = soup.find("head")
    if not head:
        logger.warning("No head element found")
        head = soup.new_tag("head")
        if soup.html:
            if soup.html.contents:
                soup.html.contents[0].insert_before(head)
            else:
                soup.html.append(head)
        else:
            logger.warning("No html element found, cannot add head")
            return None

    existing_title = head.find("title")

    # If title exists and has content, no remediation needed
    if existing_title and existing_title.get_text(strip=True):
        logger.debug("Document already has a title")
        return None

    # Create or update title element
    title_text = "Document Title"

    # Try to derive title from first h1
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        title_text = h1.get_text(strip=True)

    # If no h1, try to derive from content
    if title_text == "Document Title":
        # Check for any metadata
        meta_description = soup.find("meta", attrs={"name": "description"})
        if meta_description and meta_description.get("content"):
            title_text = meta_description["content"].strip()[:60]

    # Create or update title element
    if existing_title:
        existing_title.string = title_text
    else:
        title_tag = soup.new_tag("title")
        title_tag.string = title_text
        head.append(title_tag)

    return f"Added document title: {title_text}"


def remediate_missing_language(
    soup: BeautifulSoup, issue: Dict[str, Any], *args
) -> Optional[str]:
    """
    Remediate missing lang attribute on the HTML element.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    html = soup.find("html")
    if not html:
        logger.warning("No html element found")
        return None

    # Check if lang attribute already exists
    if html.get("lang"):
        logger.debug("HTML element already has lang attribute")
        return None

    # Set default language as English
    lang_code = "en"

    # Future enhancement: detect language based on content using a language detection library
    # For now, use English as the default language

    html["lang"] = lang_code
    return f"Added language attribute: lang='{lang_code}'"
