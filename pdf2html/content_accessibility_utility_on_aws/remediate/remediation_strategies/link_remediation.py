# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Link accessibility remediation strategies.

This module provides remediation strategies for link-related accessibility issues.
"""

from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
import re


def remediate_empty_link_text(
    soup: BeautifulSoup, issue: Dict[str, Any]
) -> Optional[str]:
    """
    Remediate empty link text by adding descriptive text based on context.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    # Find the link element from the issue
    element_str = issue.get("element", "")
    if not element_str or not element_str.startswith("<a "):
        return None

    # Extract href from the element string
    href_match = re.search(r'href="([^"]*)"', element_str)
    if not href_match:
        return None

    href = href_match.group(1)

    # Find the link in the document
    links = soup.find_all("a", href=href)
    if not links:
        return None

    # Find the empty link
    empty_link = None
    for link in links:
        if not link.get_text(strip=True):
            empty_link = link
            break

    if not empty_link:
        return None

    # Generate descriptive text based on the URL
    if href.startswith("http"):
        # Extract domain name
        domain_match = re.search(r"https?://(?:www\.)?([^/]+)", href)
        if domain_match:
            domain = domain_match.group(1)
            empty_link.string = f"Link to {domain}"
            return f"Added text to empty link: Link to {domain}"

    # Default text
    empty_link.string = f"Link to {href}"
    return f"Added text to empty link: Link to {href}"


def remediate_generic_link_text(
    soup: BeautifulSoup, issue: Dict[str, Any]
) -> Optional[str]:
    """
    Remediate generic link text by adding more descriptive text based on context.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    # Find the link element from the issue
    element_str = issue.get("element", "")
    if not element_str or not element_str.startswith("<a "):
        return None

    # Extract href and text from the element string
    href_match = re.search(r'href="([^"]*)"', element_str)
    if not href_match:
        return None

    href = href_match.group(1)

    # Find the link in the document
    links = soup.find_all("a", href=href)
    if not links:
        return None

    # Find the link with generic text
    generic_texts = [
        "click here",
        "here",
        "read more",
        "more",
        "learn more",
        "details",
        "link",
    ]
    generic_link = None
    for link in links:
        text = link.get_text(strip=True).lower()
        if text in generic_texts:
            generic_link = link
            break

    if not generic_link:
        return None

    # Generate better text based on the URL and context
    if href.startswith("http"):
        # Extract domain name
        domain_match = re.search(r"https?://(?:www\.)?([^/]+)", href)
        if domain_match:
            domain = domain_match.group(1)
            generic_link.string = f"Visit {domain} website"
            return f"Replaced generic link text with: Visit {domain} website"

    # Try to get context from surrounding text
    parent = generic_link.parent
    if parent and parent.name != "body":
        parent_text = parent.get_text(strip=True)
        # Remove the link text from parent text
        link_text = generic_link.get_text(strip=True)
        context_text = parent_text.replace(link_text, "").strip()
        if context_text:
            # Use first 30 chars of context
            context_preview = context_text[:30].strip()
            if len(context_text) > 30:
                context_preview += "..."
            generic_link.string = f"More about {context_preview}"
            return (
                f"Replaced generic link text with context: More about {context_preview}"
            )

    # Default improvement
    current_text = generic_link.get_text(strip=True)
    if current_text.lower() == "click here":
        generic_link.string = "View details"
    elif current_text.lower() == "read more":
        generic_link.string = "Read more about this topic"
    elif current_text.lower() == "learn more":
        generic_link.string = "Learn more about this topic"
    else:
        generic_link.string = "View related information"

    return f"Replaced generic link text '{current_text}' with more descriptive text"


def remediate_url_as_link_text(
    soup: BeautifulSoup, issue: Dict[str, Any]
) -> Optional[str]:
    """
    Remediate URL as link text by replacing it with more descriptive text.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    # Find the link element from the issue
    element_str = issue.get("element", "")
    if not element_str or not element_str.startswith("<a "):
        return None

    # Extract href from the element string
    href_match = re.search(r'href="([^"]*)"', element_str)
    if not href_match:
        return None

    href = href_match.group(1)

    # Find the link in the document
    links = soup.find_all("a", href=href)
    if not links:
        return None

    # Find the link with URL as text
    url_link = None
    for link in links:
        text = link.get_text(strip=True)
        if text.startswith(("http://", "https://", "www.")):
            url_link = link
            break

    if not url_link:
        return None

    # Extract domain name
    url_text = url_link.get_text(strip=True)
    domain_match = re.search(r"https?://(?:www\.)?([^/]+)", url_text)
    if domain_match:
        domain = domain_match.group(1)
        url_link.string = f"Visit {domain}"
        return f"Replaced URL with domain name: Visit {domain}"

    # Default text
    url_link.string = "Visit website"
    return "Replaced URL with generic description"


def remediate_new_window_link_no_warning(
    soup: BeautifulSoup, issue: Dict[str, Any]
) -> Optional[str]:
    """
    Remediate links that open in new windows without warning by adding a warning.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    # Find the link element from the issue
    element_str = issue.get("element", "")
    if not element_str or not element_str.startswith("<a "):
        return None

    # Check if it has target="_blank"
    if 'target="_blank"' not in element_str:
        return None

    # Extract href from the element string
    href_match = re.search(r'href="([^"]*)"', element_str)
    if not href_match:
        return None

    href = href_match.group(1)

    # Find the link in the document
    links = soup.find_all("a", href=href, target="_blank")
    if not links:
        return None

    # Find the link without warning
    for link in links:
        # Check if it already has a warning
        text = link.get_text(strip=True)
        if "new window" in text.lower() or "new tab" in text.lower():
            continue

        # Add screen reader text
        sr_span = soup.new_tag("span")
        sr_span["class"] = "sr-only"
        sr_span.string = " (opens in new window)"
        link.append(sr_span)

        # Add title attribute if not present
        if not link.get("title"):
            link["title"] = f"{text} (opens in new window)"

        return "Added screen reader text and title to indicate link opens in new window"

    return None
