# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Remediation strategies for landmark accessibility issues.

This module provides functions for remediating landmark accessibility issues.
"""

from typing import Dict, Any, Optional
from bs4 import BeautifulSoup, Tag

from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger

# Set up module-level logger
logger = setup_logger(__name__)


def remediate_missing_skip_link(
    soup: BeautifulSoup, issue: Dict[str, Any], *args
) -> Optional[str]:
    """
    Remediate missing skip link by adding a skip link.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation or None if no remediation was performed
    """
    # Check if skip link already exists
    skip_links = soup.find_all("a", string=lambda s: s and "skip" in s.lower())
    for link in skip_links:
        if link.get("href", "").startswith("#") and (
            "skip" in link.get("class", [""])[0].lower() if link.get("class") else False
        ):
            logger.debug("Skip link already exists")
            return "Skip link already exists - no remediation needed"

    # Find main content area
    main = soup.find("main") or soup.find(attrs={"role": "main"})
    if not main or not main.get("id"):
        # No main content area with ID, add one
        if not main:
            # Create main element if it doesn't exist
            body = soup.find("body")
            if not body:
                logger.warning("No body element found")
                return None

            main = soup.new_tag("main")
            main["role"] = "main"

            # Find all direct children of body
            body_children = list(body.children)

            # Find header and nav elements if they exist
            header = soup.find("header") or soup.find(attrs={"role": "banner"})
            nav = soup.find("nav") or soup.find(attrs={"role": "navigation"})

            # Remove header and nav from body_children list
            if header in body_children:
                body_children.remove(header)
            if nav in body_children:
                body_children.remove(nav)

            # Add remaining children to main element
            for child in body_children:
                if child.name:  # Only move elements, not text nodes
                    main.append(child.extract())

            # Add main element to body after header and nav
            if nav:
                nav.insert_after(main)
            elif header:
                header.insert_after(main)
            else:
                body.append(main)

        # Add ID to main element
        main["id"] = "main-content"
        logger.debug("Added ID to main element: main-content")

    # Create skip link
    skip_link = soup.new_tag("a")
    skip_link["href"] = f"#{main['id']}"
    skip_link["class"] = "skip-link"
    skip_link.string = "Skip to main content"

    # Add CSS for skip link if not already present
    head = soup.find("head")
    if head:
        skip_link_style = """
        <style>
        .skip-link {
            position: absolute;
            top: -40px;
            left: 0;
            background: #000;
            color: white;
            padding: 8px;
            z-index: 100;
            transition: top 0.3s;
        }
        .skip-link:focus {
            top: 0;
        }
        </style>
        """

        # Check if skip-link style already exists
        skip_style_exists = False
        for style in head.find_all("style"):
            if ".skip-link" in style.text:
                skip_style_exists = True
                break

        if not skip_style_exists:
            head.append(BeautifulSoup(skip_link_style, "html.parser"))

    # Add skip link to the beginning of the body
    body = soup.find("body")
    if body:
        body.insert(0, skip_link)
        logger.debug("Added skip link")
        return "Added skip link to body"
    else:
        logger.warning("No body element found")
        return None


def remediate_missing_footer_landmark(
    soup: BeautifulSoup, issue: Dict[str, Any], *args
) -> Optional[str]:
    """
    Remediate missing footer landmark by adding a footer element.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation or None if no remediation was performed
    """
    # Check if footer landmark already exists
    if soup.find("footer") or soup.find(attrs={"role": "contentinfo"}):
        logger.debug("Footer landmark already exists")
        return "Footer landmark already exists - no remediation needed"

    logger.debug("Starting footer landmark remediation")

    # Find the body element
    body = soup.find("body")
    if not body:
        logger.warning("No body element found")
        return None

    # Create footer element
    footer = soup.new_tag("footer")
    footer["role"] = "contentinfo"

    # Add content to footer
    copyright_tag = soup.new_tag("p")
    copyright_tag.string = "© " + str(2024) + " - All rights reserved."
    footer.append(copyright_tag)

    # Add footer to the end of the body
    body.append(footer)
    logger.debug("Added footer landmark")

    # Continue remediation with skip link
    remediate_missing_skip_link(soup, issue, *args)

    return "Added footer landmark to document"


def remediate_missing_header_landmark(
    soup: BeautifulSoup, issue: Dict[str, Any], *args
) -> Optional[str]:
    """
    Remediate missing header landmark by adding a header element.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation or None if no remediation was performed
    """
    # Check if header landmark already exists
    if soup.find("header") or soup.find(attrs={"role": "banner"}):
        logger.debug("Header landmark already exists")
        return "Header landmark already exists - no remediation needed"

    logger.debug("Starting header landmark remediation")

    # Find the body element
    body = soup.find("body")
    if not body:
        logger.warning("No body element found")
        return None

    # Create header element
    header = soup.new_tag("header")
    header["role"] = "banner"

    # Look for a title to use
    title_text = "Document Title"
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        title_text = title_tag.string

    # Add content to header
    h1 = soup.find("h1")
    if h1:
        # If h1 exists, move it to the header
        h1.extract()
        header.append(h1)
    else:
        # Create a new h1
        h1 = soup.new_tag("h1")
        h1.string = title_text
        header.append(h1)

    # Add header as the first element in the body
    if len(body.contents) > 0:
        body.insert(0, header)
    else:
        body.append(header)

    logger.debug("Added header landmark")

    # Continue remediation with footer
    remediate_missing_footer_landmark(soup, issue, *args)

    return "Added header landmark to document"


def remediate_missing_navigation_landmark(
    soup: BeautifulSoup, issue: Dict[str, Any], *args
) -> Optional[str]:
    """
    Remediate missing navigation landmark by adding a nav element.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation or None if no remediation was performed
    """
    # Check if navigation landmark already exists
    if soup.find("nav") or soup.find(attrs={"role": "navigation"}):
        logger.debug("Navigation landmark already exists")
        return "Navigation landmark already exists - no remediation needed"

    logger.debug("Starting navigation landmark remediation")

    # Find the body element
    body = soup.find("body")
    if not body:
        logger.warning("No body element found")
        return None

    # Create nav element
    nav = soup.new_tag("nav")
    nav["role"] = "navigation"
    nav["aria-label"] = "Main navigation"

    # Try to find existing navigation lists
    nav_list = soup.find("ul", class_=lambda c: c and ("nav" in c or "menu" in c))

    if not nav_list:
        # Look for a series of links that might be a navigation
        links = soup.find_all("a")
        potential_navs = []

        for i in range(len(links) - 1):
            if links[i].parent == links[i + 1].parent and links[i].parent.name in [
                "div",
                "p",
                "header",
            ]:
                potential_navs.append(links[i].parent)

        if potential_navs:
            # Use the first potential navigation container
            nav_container = potential_navs[0]

            # Create a list from the links
            ul = soup.new_tag("ul")
            for link in nav_container.find_all("a"):
                li = soup.new_tag("li")
                link_copy = link.extract()
                li.append(link_copy)
                ul.append(li)

            nav.append(ul)
        else:
            # Create a simple navigation
            ul = soup.new_tag("ul")

            nav.append(ul)
    else:
        # Move existing list to nav
        nav_list.extract()
        nav.append(nav_list)

    # Find the header element or add nav after it
    header = soup.find("header") or soup.find(attrs={"role": "banner"})
    if header:
        header.insert_after(nav)
    else:
        # Add nav as the first element in the body
        if len(body.contents) > 0:
            body.insert(0, nav)
        else:
            body.append(nav)

    logger.debug("Added navigation landmark")

    # Continue remediation with header
    remediate_missing_header_landmark(soup, issue, *args)

    return "Added navigation landmark to document"


def remediate_missing_main_landmark(
    soup: BeautifulSoup, issue: Dict[str, Any], *args
) -> Optional[str]:
    """
    Remediate missing main landmark by adding a main element.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation or None if no remediation was performed
    """
    # Check if main landmark already exists
    if soup.find("main") or soup.find(attrs={"role": "main"}):
        logger.debug("Main landmark already exists")
        return "Main landmark already exists - no remediation needed"

    logger.debug("Starting main landmark remediation")

    # Find the body element
    body = soup.find("body")
    if not body:
        logger.warning("No body element found")
        return None

    # Create main element
    main = soup.new_tag("main")
    main["id"] = "main-content"
    main["role"] = "main"

    # Find existing landmarks
    header = soup.find("header") or soup.find(attrs={"role": "banner"})
    nav = soup.find("nav") or soup.find(attrs={"role": "navigation"})
    footer = soup.find("footer") or soup.find(attrs={"role": "contentinfo"})

    logger.debug(
        f"Found existing landmarks - header: {bool(header)}, nav: {bool(nav)}, footer: {bool(footer)}"
    )

    # Find the main content container (often a div with class="page" or similar)
    content_containers = soup.find_all(
        "div", class_=lambda c: c and ("page" in c or "content" in c)
    )
    logger.debug(f"Found {len(content_containers)} potential content containers")

    # First remove any duplicate content
    seen_content = {}
    for container in content_containers:
        # Get text content and normalize it
        content = container.get_text().strip()
        # Remove extra whitespace and normalize case
        content = " ".join(content.lower().split())

        # If we've seen this content before
        if content in seen_content:
            logger.debug(f"Found duplicate content: {content[:50]}...")
        else:
            seen_content[content] = container

    # Check if we found any content containers
    if content_containers:
        # Use the first content container and move it into main
        container = content_containers[0]
        container.extract()
        main.append(container)
        logger.debug("Moved content container into main element")
    else:
        # No content container found, move all content that's not in landmarks
        for child in list(body.children):
            # Skip if not an element node
            if not isinstance(child, Tag):
                continue

            # Skip existing landmarks
            if (child == header) or (child == nav) or (child == footer):
                continue

            # Skip script and style tags
            if child.name in ["script", "style", "noscript"]:
                continue

            # Move this element to main
            main.append(child.extract())
            logger.debug(f"Moved {child.name} element into main")

    # Add main at the right position
    if nav:
        nav.insert_after(main)
    elif header:
        header.insert_after(main)
    else:
        body.insert(0, main)

    logger.debug("Added main landmark")

    # First check if we need navigation since we just added main
    if not (soup.find("nav") or soup.find(attrs={"role": "navigation"})):
        # Track that we want to avoid chain reactions
        issue["child_remediations"] = issue.get("child_remediations", set())
        if "navigation" not in issue["child_remediations"]:
            issue["child_remediations"].add("navigation")
            # Add navigation landmark
            nav_result = remediate_missing_navigation_landmark(soup, issue, *args)
            logger.debug(f"Navigation remediation result: {nav_result}")

    return "Added main landmark to document"
