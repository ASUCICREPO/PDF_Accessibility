# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Figure structure remediation strategies.

This module provides remediation strategies for figure-related accessibility issues.
"""

from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
import re

from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger

# Set up module-level logger
logger = setup_logger(__name__)


def remediate_improper_figure_structure(
    soup: BeautifulSoup, issue: Dict[str, Any], *args
) -> Optional[str]:
    """
    Remediate improper figure structure by adding proper figure and figcaption elements.

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

    # Find the image element
    img = None
    for image in soup.find_all("img"):
        # This is a simplified selector match - in practice we would need more robust matching
        if path.lower() in str(image).lower():
            img = image
            break

    if not img:
        logger.warning(f"Could not find image element with path: {path}")
        return None

    # Check if already in a figure
    if img.find_parent("figure"):
        logger.debug("Image is already in a figure element")
        return None

    # Create figure element
    figure = soup.new_tag("figure")

    # Find potential caption text
    caption_text = ""

    # Check for alt text
    if img.get("alt") and len(img["alt"]) > 10:  # Substantive alt text
        caption_text = img["alt"]

    # Check for nearby text with "Figure" reference
    next_p = img.find_next("p")
    if next_p and not caption_text:
        p_text = next_p.get_text(strip=True)
        if p_text.startswith("Figure") or p_text.startswith("Fig."):
            caption_text = p_text
            # Remove the paragraph since we'll use it as caption
            next_p.decompose()

    # Check image title attribute
    if not caption_text and img.get("title"):
        caption_text = img["title"]

    # Check image filename for descriptive name
    if not caption_text and img.get("src"):
        filename = img["src"].split("/")[-1].split(".")[0]
        # Convert filename to readable text (e.g., "figure_3_example" -> "Figure 3 Example")
        if len(filename) > 5 and not filename.isdigit():
            words = re.findall(r"[A-Za-z]+", filename)
            if words:
                caption_text = " ".join(word.capitalize() for word in words)

    # Check for BDA-generated alt text
    if not caption_text and img.get("data-bda-generated-alt"):
        caption_text = img["data-bda-generated-alt"]

    # Check for nearby headings that might describe the image
    if not caption_text:
        prev_heading = img.find_previous(["h1", "h2", "h3", "h4", "h5", "h6"])
        if prev_heading and prev_heading.get_text(strip=True):
            caption_text = prev_heading.get_text(strip=True)

    # Replace image with figure structure
    img_parent = img.parent
    img.extract()  # Remove img from its parent

    # Add role="group" to figure for better screen reader support
    figure["role"] = "group"

    # If we have an ID on the image, move it to the figure
    if img.get("id"):
        figure["id"] = img["id"]
        del img["id"]

    figure.append(img)  # Add img to figure

    # Add figcaption if we have caption text
    if caption_text:
        figcaption = soup.new_tag("figcaption")
        figcaption.string = caption_text

        # Add aria-label to figure matching the caption
        figure["aria-label"] = caption_text

        # Decide whether to place caption before or after image
        # If it's a numbered figure reference, place it before
        if re.match(r"^(Figure|Fig\.)\s+\d+", caption_text, re.IGNORECASE):
            figure.insert(0, figcaption)
        else:
            figure.append(figcaption)

    # Add figure to the document
    img_parent.append(figure)

    # Add CSS class for styling
    figure["class"] = figure.get("class", []) + ["content-figure"]

    # Ensure figure has proper margins
    style = soup.find("style")
    if not style:
        style = soup.new_tag("style")
        head = soup.find("head")
        if head:
            head.append(style)

    # Add CSS if not already present
    figure_css = """
    .content-figure {
        margin: 1em 0;
        padding: 0.5em;
        border: 1px solid #ddd;
    }
    .content-figure img {
        max-width: 100%;
        height: auto;
    }
    .content-figure figcaption {
        margin-top: 0.5em;
        font-style: italic;
        color: #666;
    }
    """

    if style.string:
        if ".content-figure" not in style.string:
            style.string = style.string + figure_css
    else:
        style.string = figure_css

    return "Added figure element with" + (
        " figcaption" if caption_text else " no caption"
    )
