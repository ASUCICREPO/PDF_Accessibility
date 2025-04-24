# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Alt text generator module.

This module provides functionality for generating alt text for images using GenAI.
"""

import os
import re
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup, Tag, NavigableString
from PIL import Image
from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger
from content_accessibility_utility_on_aws.remediate.services.bedrock_client import (
    BedrockClient,
    AltTextGenerationError,
)

# Set up module-level logger
logger = setup_logger(__name__)


def extract_image_context(img: Tag, soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Extract context information for an image from surrounding elements.

    Args:
        img: The image element
        soup: The BeautifulSoup object representing the HTML document

    Returns:
        Dictionary containing context information
    """
    context = {}

    # Try to find a caption or figure text
    caption = None

    # Check if the image is inside a figure element
    figure = img.find_parent("figure")
    if figure:
        # Look for figcaption
        figcaption = figure.find("figcaption")
        if figcaption:
            caption = figcaption.get_text(strip=True)

        # If no figcaption, look for any paragraph inside the figure
        if not caption:
            p = figure.find("p")
            if p:
                caption = p.get_text(strip=True)

    # If no caption found yet, check if there's a paragraph right after the image
    if not caption:
        next_sibling = img.next_sibling
        while (
            next_sibling
            and isinstance(next_sibling, NavigableString)
            and not next_sibling.strip()
        ):
            next_sibling = next_sibling.next_sibling

        if next_sibling and next_sibling.name == "p":
            caption = next_sibling.get_text(strip=True)

    # If still no caption, check if the image is inside a div with a paragraph
    if not caption:
        parent_div = img.find_parent("div")
        if parent_div:
            p = parent_div.find("p")
            if p:
                caption = p.get_text(strip=True)

    # Add caption to context if found
    if caption:
        context["caption"] = caption

        # Try to extract figure number from caption
        figure_match = re.search(r"figure\s+(\d+(?:\.\d+)?)", caption, re.IGNORECASE)
        if figure_match:
            context["figure_number"] = figure_match.group(1)

    # Get surrounding text (from parent element or nearby paragraphs)
    surrounding_text = []

    # Get text from parent element
    parent = img.parent
    if parent and parent.name not in ["figure", "body", "html"]:
        parent_text = parent.get_text(strip=True)
        if parent_text and parent_text not in surrounding_text:
            surrounding_text.append(parent_text)

    # Get text from previous and next paragraphs
    prev_p = img.find_previous("p")
    if prev_p:
        prev_text = prev_p.get_text(strip=True)
        if prev_text and prev_text not in surrounding_text:
            surrounding_text.append(prev_text)

    next_p = img.find_next("p")
    if next_p:
        next_text = next_p.get_text(strip=True)
        if next_text and next_text not in surrounding_text:
            surrounding_text.append(next_text)

    # Add surrounding text to context
    if surrounding_text:
        context["surrounding_text"] = " ".join(surrounding_text)

    return context


def clean_alt_text(alt_text: str) -> str:
    """
    Clean up generated alt text.

    Args:
        alt_text: The generated alt text

    Returns:
        Cleaned alt text
    """
    # Remove any quotes that might be around the text
    alt_text = alt_text.strip("\"'")

    # Remove phrases like "Image of" or "Picture of" from the beginning
    alt_text = re.sub(
        r"^(image|picture|photo|photograph|illustration|graphic|icon)\s+of\s+",
        "",
        alt_text,
        flags=re.IGNORECASE,
    )

    # Remove any trailing periods
    alt_text = alt_text.rstrip(".")

    # Capitalize first letter
    if alt_text:
        alt_text = alt_text[0].upper() + alt_text[1:]

    return alt_text


def generate_alt_text(
    img: Tag, soup: BeautifulSoup, bedrock_client: Optional[BedrockClient] = None
) -> str:
    """
    Generate alt text for an image using GenAI.

    Args:
        img: The image element
        soup: The BeautifulSoup object representing the HTML document
        bedrock_client: Optional Bedrock client for GenAI integration

    Returns:
        Generated alt text for the image

    Raises:
        AltTextGenerationError: If alt text generation fails
        FileNotFoundError: If the image file is not found
    """
    # Get image path
    src = img.get("src", "")
    if not src:
        logger.warning("Image missing src attribute")
        raise AltTextGenerationError("Image missing src attribute")

    # Get absolute path to image
    img_path = os.path.abspath(src)
    if not os.path.exists(img_path):
        # Try relative to the HTML file location
        html_dir = (
            os.path.dirname(soup.original_url)
            if hasattr(soup, "original_url")
            else os.getcwd()
        )
        img_path = os.path.join(html_dir, os.path.basename(src))

        # If still not found, try looking in the same directory as the HTML
        if not os.path.exists(img_path) and hasattr(soup, "original_url"):
            html_dir = os.path.dirname(soup.original_url)
            img_path = os.path.join(html_dir, os.path.basename(src))

        # If still not found, try looking in parent directories
        if not os.path.exists(img_path):
            base_filename = os.path.basename(src)
            parent_dir = os.path.dirname(html_dir)

            # Check in extracted_html directory
            extracted_html_dir = os.path.join(parent_dir, "extracted_html")
            if os.path.exists(extracted_html_dir):
                extracted_path = os.path.join(extracted_html_dir, base_filename)
                if os.path.exists(extracted_path):
                    img_path = extracted_path
                    logger.debug(f"Found image in extracted_html directory: {img_path}")

            # Check in standard_output/assets directory
            if not os.path.exists(img_path):
                for root, dirs, files in os.walk(parent_dir):
                    if "standard_output" in root and "assets" in dirs:
                        assets_dir = os.path.join(root, "assets")
                        assets_path = os.path.join(assets_dir, base_filename)
                        if os.path.exists(assets_path):
                            img_path = assets_path
                            logger.debug(
                                f"Found image in standard_output/assets directory: {img_path}"
                            )
                            break

            # If still not found, try to find any image with a similar name
            if not os.path.exists(img_path):
                base_name = os.path.splitext(base_filename)[0]
                for root, _, files in os.walk(parent_dir):
                    for file in files:
                        if file.startswith(base_name) and (
                            file.endswith(".png") or file.endswith(".jpg")
                        ):
                            img_path = os.path.join(root, file)
                            logger.debug(f"Found similar image: {img_path}")
                            break
                    if os.path.exists(img_path):
                        break

    if not os.path.exists(img_path):
        logger.warning(f"Image file not found: {img_path}")
        raise FileNotFoundError(f"Image file not found: {img_path}")

    # Extract context from surrounding elements
    context = extract_image_context(img, soup)

    # Generate alt text using Bedrock
    if not bedrock_client:
        bedrock_client = BedrockClient()

    try:
        # Generate prompt for alt text
        prompt = generate_alt_text_prompt(img_path, context)

        # Get alt text from Bedrock using generate_alt_text_for_image method
        alt_text = bedrock_client.generate_alt_text_for_image(img_path, prompt)

        # Clean up the alt text
        alt_text = clean_alt_text(alt_text)

        return alt_text
    except Exception as e:
        logger.warning(f"Failed to generate alt text: {e}")
        raise AltTextGenerationError(f"Failed to generate alt text: {e}")


def generate_alt_text_prompt(
    image_path: str, context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate a prompt for generating alt text for an image.

    Args:
        image_path: Path to the image file
        context: Optional context information about the image

    Returns:
        str: Prompt for generating alt text
    """
    # Get the image dimensions and format
    try:
        with Image.open(image_path) as img:
            width, height = img.size
    except Exception as e:
        logger.warning(f"Error reading image {image_path}: {e}")
        width, height = 0, 0

    # Build the prompt
    prompt = f"""You are an accessibility expert specializing in generating descriptive alt text for images.

I need you to generate concise, accurate alt text for an image with the following characteristics:
- Dimensions: {width}x{height} pixels

Guidelines for generating good alt text:
1. Be concise but descriptive (aim for 125 characters or less)
2. Describe the content and function of the image
3. Don't start with phrases like "Image of" or "Picture of"
4. Include relevant details but omit unnecessary information
5. If the image contains text, include the important text in the alt text
6. Focus on what's important about the image in its context

Please provide only the alt text with no additional explanation or commentary.
"""

    # Add context information if available
    if context:
        if "surrounding_text" in context and context["surrounding_text"]:
            prompt += f"\n\nThe image appears in the following context:\n{context['surrounding_text']}\n"

        if "caption" in context and context["caption"]:
            prompt += f"\nThe image has this caption: {context['caption']}\n"

        if "figure_number" in context and context["figure_number"]:
            prompt += f"\nThis is Figure {context['figure_number']}.\n"

    return prompt
