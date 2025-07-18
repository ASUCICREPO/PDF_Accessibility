# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Image accessibility remediation strategies.

This module provides remediation strategies for image-related accessibility issues.
"""

from typing import Dict, Any, Optional
from bs4 import BeautifulSoup, Tag
import os
import re

from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger
from content_accessibility_utility_on_aws.remediate.prompt_generators.alt_text_generator import (
    generate_alt_text,
)
from content_accessibility_utility_on_aws.remediate.services.bedrock_client import (
    BedrockClient,
    AltTextGenerationError,
)

# Set up module-level logger
logger = setup_logger(__name__)


def remediate_missing_alt_text(
    soup: BeautifulSoup,
    issue: Dict[str, Any],
    bedrock_client: Optional[BedrockClient] = None,
) -> Optional[str]:
    """
    Remediate missing alt text by adding appropriate alternative text.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate
        bedrock_client: Optional Bedrock client for GenAI integration

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    # Find the image element from the issue
    element_str = issue.get("element", "")
    if not element_str or not element_str.startswith("<img "):
        return None

    # Extract src and data-bda-id from the element string
    src_match = re.search(r'src="([^"]*)"', element_str)
    data_bda_id_match = re.search(r'data-bda-id="([^"]*)"', element_str)

    if not src_match:
        return None

    src = src_match.group(1)

    # Try to find the image using multiple strategies
    img = None

    # Strategy 1: Try to find by data-bda-id if available
    if data_bda_id_match:
        bda_id = data_bda_id_match.group(1)
        img = soup.find("img", attrs={"data-bda-id": bda_id})

    # Strategy 2: Try to find by src
    if not img:
        img = soup.find("img", src=src)

        # If not found, try matching just the filename
        if not img:
            filename = os.path.basename(src)
            for image in soup.find_all("img"):
                if image.get("src") and os.path.basename(image["src"]) == filename:
                    img = image
                    break

    if not img:
        return None

    if not img.has_attr("alt"):
        try:
            # Generate alt text using GenAI
            alt_text = generate_alt_text(img, soup, bedrock_client)

            # Add alt attribute
            img["alt"] = alt_text
            return f"Added AI-generated alt text to image: {alt_text}"
        except (AltTextGenerationError, FileNotFoundError) as e:
            logger.error(f"Failed to generate alt text: {e}")
            # Add a placeholder alt text to avoid accessibility errors
            img["alt"] = "Image description unavailable"
            return f"Added placeholder alt text due to error: {str(e)}"

    return None


def remediate_empty_alt_text(
    soup: BeautifulSoup,
    issue: Dict[str, Any],
    bedrock_client: Optional[BedrockClient] = None,
) -> Optional[str]:
    """
    Remediate empty alt text by adding appropriate alternative text or confirming decorative status.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate
        bedrock_client: Optional Bedrock client for GenAI integration

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    # Find the image element from the issue
    element_str = issue.get("element", "")
    if not element_str or not element_str.startswith("<img "):
        return None

    # Extract src and data-bda-id from the element string
    src_match = re.search(r'src="([^"]*)"', element_str)
    data_bda_id_match = re.search(r'data-bda-id="([^"]*)"', element_str)

    if not src_match:
        return None

    src = src_match.group(1)

    # Try to find the image using multiple strategies
    img = None

    # Strategy 1: Try to find by data-bda-id if available
    if data_bda_id_match:
        bda_id = data_bda_id_match.group(1)
        img = soup.find("img", attrs={"data-bda-id": bda_id})

    # Strategy 2: Try to find by src
    if not img:
        img = soup.find("img", src=src)

        # If not found, try matching just the filename
        if not img:
            filename = os.path.basename(src)
            for image in soup.find_all("img"):
                if image.get("src") and os.path.basename(image["src"]) == filename:
                    img = image
                    break

    if not img:
        return None

    if img.has_attr("alt") and img["alt"] == "":
        # Check if it's likely decorative
        is_decorative = _is_decorative_image(img)

        if is_decorative:
            # Add role="presentation" to confirm it's decorative
            img["role"] = "presentation"
            return "Confirmed image is decorative with role='presentation'"
        else:
            try:
                # Generate alt text using GenAI
                alt_text = generate_alt_text(img, soup, bedrock_client)

                # Add alt attribute
                img["alt"] = alt_text
                return (
                    f"Added AI-generated alt text to image with empty alt: {alt_text}"
                )
            except (AltTextGenerationError, FileNotFoundError) as e:
                logger.error(f"Failed to generate alt text: {e}")
                # Add a placeholder alt text to avoid accessibility errors
                img["alt"] = "Image description unavailable"
                return f"Added placeholder alt text due to error: {str(e)}"

    return None


def find_image_by_issue(soup: BeautifulSoup, issue: Dict[str, Any]) -> Optional[Tag]:
    """
    Enhanced function to find an image element using multiple strategies.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue containing image information

    Returns:
        The image element if found, None otherwise
    """
    # Try to get image information from the issue
    element_str = issue.get("element", "")
    element_selector = issue.get("selector", "")

    # Strategy 1: Try to use the selector if available
    if element_selector:
        try:
            img = soup.select_one(element_selector)
            if img and img.name == "img":
                logger.debug(f"Found image using selector: {element_selector}")
                return img
        except Exception as e:
            logger.error(f"Error using selector: {str(e)}")

    # Strategy 2: Extract information from element string
    src_match = re.search(r'src="([^"]*)"', element_str) if element_str else None
    alt_match = re.search(r'alt="([^"]*)"', element_str) if element_str else None
    data_bda_id_match = (
        re.search(r'data-bda-id="([^"]*)"', element_str) if element_str else None
    )

    # Strategy 3: Try to find by data-bda-id if available
    if data_bda_id_match:
        bda_id = data_bda_id_match.group(1)
        img = soup.find("img", attrs={"data-bda-id": bda_id})
        if img:
            logger.debug(f"Found image using data-bda-id: {bda_id}")
            return img

    # Strategy 4: Try to find by src if available
    if src_match:
        src = src_match.group(1)
        img = soup.find("img", src=src)
        if img:
            logger.debug(f"Found image using src: {src}")
            return img

        # If not found, try matching just the filename
        filename = os.path.basename(src)
        for image in soup.find_all("img"):
            if image.get("src") and os.path.basename(image["src"]) == filename:
                logger.debug(f"Found image using filename: {filename}")
                return image

    # Strategy 5: Try to find by alt text if available
    generic_alt = None
    if alt_match:
        generic_alt = alt_match.group(1)
        images_with_alt = soup.find_all("img", alt=generic_alt)
        if images_with_alt:
            logger.debug(f"Found image using alt text: {generic_alt}")
            return images_with_alt[0]  # Use the first match

        # Case-insensitive match
        for image in soup.find_all("img"):
            if image.get("alt") and image["alt"].upper() == generic_alt.upper():
                logger.debug(
                    f"Found image using case-insensitive alt text: {generic_alt}"
                )
                return image

    # Strategy 6: Use context information
    context = issue.get("context", {})
    if context:
        # Check for position information
        position = context.get("position")
        if position:
            all_images = soup.find_all("img")
            try:
                index = int(position) - 1  # Convert from 1-based to 0-based
                if 0 <= index < len(all_images):
                    logger.debug(f"Found image using position: {position}")
                    return all_images[index]
            except (ValueError, TypeError):
                pass

        # Check for surrounding text
        surrounding_text = context.get("text", "")
        if surrounding_text:
            # Look for images near elements containing this text
            text_elements = []
            for tag in soup.find_all(
                string=lambda s: surrounding_text in s if s else False
            ):
                text_elements.append(tag.parent)

            # Find closest image to any of these elements
            if text_elements:
                for element in text_elements:
                    # Check previous and next siblings
                    img = element.find_previous("img")
                    if img:
                        logger.debug(
                            f"Found image using surrounding text (previous): {surrounding_text}"
                        )
                        return img

                    img = element.find_next("img")
                    if img:
                        logger.debug(
                            f"Found image using surrounding text (next): {surrounding_text}"
                        )
                        return img

    # Strategy 7: Check for issue type specific matching
    issue_type = issue.get("type", "")
    if issue_type == "generic-alt-text":
        # Look for images with common generic alt text patterns
        generic_patterns = [
            r"^image$",
            r"^picture$",
            r"^photo$",
            r"^graphic$",
            r"^icon$",
            r"^img\d*$",
            r"^pic\d*$",
            r"^[\d\s]*$",
            r"^\.+$",
            r"^untitled$",
            r"^no description$",
            r"^photograph$",
        ]
        for image in soup.find_all("img"):
            if image.has_attr("alt"):
                alt_text = image["alt"].strip().lower()
                if alt_text and any(
                    re.match(pattern, alt_text) for pattern in generic_patterns
                ):
                    logger.debug(
                        f"Found image with generic alt text pattern: {alt_text}"
                    )
                    return image

    # If we've tried everything and failed, log the failure
    logger.warning(f"Could not find image for issue: {issue.get('type', 'unknown')}")
    return None


def remediate_generic_alt_text(soup, issue, bedrock_client=None):
    """
    Remediate generic alt text (like 'image', 'photo', 'diagram', etc.) by replacing it
    with more descriptive alt text.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate
        bedrock_client: Optional Bedrock client for GenAI integration

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    # Extract the alt text from the issue if available
    generic_alt = None
    element_str = issue.get("element", "")
    alt_match = re.search(r'alt="([^"]*)"', element_str) if element_str else None
    if alt_match:
        generic_alt = alt_match.group(1)

    # Define generic alt text patterns
    generic_patterns = [
        "image", "IMAGE", "Image", 
        "picture", "PICTURE", "Picture",
        "photo", "PHOTO", "Photo",
        "graphic", "GRAPHIC", "Graphic",
        "diagram", "DIAGRAM", "Diagram",
        "chart", "CHART", "Chart",
        "graph", "GRAPH", "Graph",
        "icon", "ICON", "Icon",
        "img", "IMG", "Img",
        "pic", "PIC", "Pic"
    ]

    # First, try to find the image using the standard finder function
    img = find_image_by_issue(soup, issue)
    
    # If not found and we have a generic alt value from the issue, try direct search
    if not img and generic_alt:
        images = soup.find_all("img", alt=generic_alt)
        if images:
            img = images[0]
            logger.debug(f"Found image with exact alt text: '{generic_alt}'")
        else:
            # Try case-insensitive search
            for image in soup.find_all("img"):
                if image.has_attr("alt") and image["alt"].upper() == generic_alt.upper():
                    img = image
                    logger.debug(f"Found image with case-insensitive alt text: '{generic_alt}'")
                    break

    # If still not found, search for all images with generic alt text
    if not img:
        for pattern in generic_patterns:
            images = soup.find_all("img", alt=pattern)
            if images:
                img = images[0]
                generic_alt = pattern
                logger.debug(f"Found image with generic alt text: '{pattern}'")
                break

    if not img:
        logger.warning("Could not find image for generic alt text remediation")
        return None

    # Confirm this image has generic alt text
    current_alt = img.get("alt", "").strip()
    if not current_alt or current_alt.upper() not in [p.upper() for p in generic_patterns]:
        logger.info(f"Image alt text '{current_alt}' is not recognized as generic")
        return None

    try:
        # Try to generate alt text using Bedrock AI
        if bedrock_client:
            alt_text = generate_alt_text(img, soup, bedrock_client)
            if alt_text:
                img["alt"] = alt_text
                return f"Added AI-generated alt text '{alt_text}' to replace generic '{current_alt}'"
    except Exception as e:
        logger.error(f"Error generating AI alt text: {e}")

    # Extract context for the image
    context = ""
    
    # Try to get context from nearby text
    parent_text = img.parent.get_text(strip=True) if img.parent else ""
    if parent_text and len(parent_text) < 200:
        context = parent_text
    
    # Try nearby headings if no context yet
    if not context:
        heading = img.find_previous(["h1", "h2", "h3", "h4", "h5", "h6"])
        if heading:
            context = heading.get_text(strip=True)
    
    # Create context-based alt text based on generic type
    generic_type = current_alt.lower()
    if "diagram" in generic_type or "chart" in generic_type or "graph" in generic_type:
        new_alt = f"Diagram showing {context}" if context else "Diagram related to this content"
    elif "photo" in generic_type or "picture" in generic_type:
        new_alt = f"Photo of {context}" if context else "Photo related to this content"
    else:
        new_alt = f"Image of {context}" if context else "Image related to this content"
    
    img["alt"] = new_alt
    return f"Added context-based alt text '{new_alt}' to replace generic '{current_alt}'"


def remediate_long_alt_text(
    soup: BeautifulSoup,
    issue: Dict[str, Any],
    bedrock_client: Optional[BedrockClient] = None,
) -> Optional[str]:
    """
    Remediate excessively long alt text by making it more concise.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate
        bedrock_client: Optional Bedrock client for GenAI integration

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    # Find the image element from the issue
    element_str = issue.get("element", "")
    if not element_str or not element_str.startswith("<img "):
        return None

    # Extract src and alt from the element string
    src_match = re.search(r'src="([^"]*)"', element_str)
    alt_match = re.search(r'alt="([^"]*)"', element_str)
    if not src_match or not alt_match:
        return None

    src = src_match.group(1)
    long_alt = alt_match.group(1)

    # Find the image in the document
    images = soup.find_all("img", src=src)
    if not images:
        return None

    # Find the image with long alt text
    for img in images:
        if img.has_attr("alt") and img["alt"] == long_alt and len(img["alt"]) > 125:
            # Generate concise alt text using GenAI
            alt_text = generate_alt_text(img, soup, bedrock_client)

            # Add alt attribute
            img["alt"] = alt_text
            return f"Shortened long alt text to: {alt_text}"

    return None


def _is_decorative_image(img: Tag) -> bool:
    """
    Determine if an image is likely decorative.

    Args:
        img: The image element

    Returns:
        True if the image appears to be decorative, False otherwise
    """
    # Check for role="presentation" or role="none"
    if img.get("role") in ["presentation", "none"]:
        return True

    # Check for CSS classes that suggest decorative images
    css_classes = img.get("class", [])
    if css_classes:
        decorative_class_patterns = [
            "decorative",
            "icon",
            "bullet",
            "separator",
            "spacer",
            "bg",
        ]
        if any(
            pattern in " ".join(css_classes).lower()
            for pattern in decorative_class_patterns
        ):
            return True

    # Check for small dimensions
    width = img.get("width")
    height = img.get("height")
    if width and height:
        try:
            if int(width) <= 16 and int(height) <= 16:
                return True
        except ValueError:
            pass

    # Check if it's in a context that suggests decoration
    parent = img.parent
    if parent and parent.name == "div" and parent.get("class"):
        parent_classes = " ".join(parent.get("class", []))
        if any(
            pattern in parent_classes.lower()
            for pattern in ["banner", "header", "logo", "icon"]
        ):
            return True

    return False
