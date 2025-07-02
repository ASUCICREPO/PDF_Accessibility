# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Page builder module for PDF to HTML conversion.

This module provides functionality to build HTML pages from BDA result elements,
using page indices and reading order to ensure correct page generation.
"""

import os
import logging
import shutil
from bs4 import BeautifulSoup
from typing import Dict, List, Any
import hashlib

# Set up module-level logger
logger = logging.getLogger(__name__)


def handle_image_element(element_tag, element, output_dir):
    """
    Handle image elements by fixing src attributes and copying files if needed.

    Args:
        element_tag: The HTML element tag containing the image
        element: The element data from BDA result
        output_dir: Directory where images are stored

    Returns:
        bool: True if any images were fixed, False otherwise
    """
    # Check if we have crop_images
    if not element.get("crop_images"):
        return False

    # Get the crop image path and filename
    crop_image_path = element["crop_images"][0]
    crop_image_filename = os.path.basename(crop_image_path)
    base_crop_filename = os.path.splitext(crop_image_filename)[0]

    # Find all img tags in the element
    img_tags = element_tag.find_all("img")
    if not img_tags:
        return False

    # Create the extracted_html directory path
    html_output_dir = os.path.join(output_dir, "extracted_html")
    os.makedirs(html_output_dir, exist_ok=True)

    fixed_count = 0
    for img_tag in img_tags:
        old_src = img_tag.get("src", "")

        # Extract just the filename from the src
        src_filename = os.path.basename(old_src.replace("./", "").strip())

        # Check if the src already matches the crop image
        expected_filename = f"{base_crop_filename}.png"

        if src_filename == expected_filename:
            # No need to change anything
            continue

        # If the src is different, we need to copy the crop image with the src name
        logger.debug(f"Image mismatch detected: element_id={element.get('id')}")
        logger.debug(f"  crop_image: {crop_image_path}")
        logger.debug(f"  img src: {old_src}")

        # Find the crop image file in the output directory
        crop_image_file = None
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                if file == expected_filename:
                    crop_image_file = os.path.join(root, file)
                    break
            if crop_image_file:
                break

        if not crop_image_file:
            logger.warning(f"Could not find crop image file: {expected_filename}")
            continue

        # Copy the crop image to match the src in the HTML
        dest_file = os.path.join(html_output_dir, src_filename)
        try:
            shutil.copy2(crop_image_file, dest_file)
            logger.debug(
                f"Copied image {crop_image_file} to {dest_file} to match HTML src"
            )
            fixed_count += 1
        except Exception as e:
            logger.warning(
                f"Failed to copy image file {crop_image_file} to {dest_file}: {e}"
            )

    return fixed_count > 0


def identify_duplicate_html_elements(html_content: str) -> List[Dict[str, Any]]:
    """
    Identify potentially duplicated HTML elements in the content.

    Args:
        html_content: The HTML content to parse and check for duplicates

    Returns:
        List of dictionaries containing information about duplicate elements
    """
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, "html.parser")

    # Find all significant elements that might be duplicated
    significant_elements = soup.find_all(
        ["p", "h1", "h2", "h3", "h4", "h5", "h6", "div", "table", "ul", "ol"]
    )

    # Dictionary to track elements by their content signature
    element_map = {}
    duplicates = []

    for idx, element in enumerate(significant_elements):
        # Create a signature based on text content and tag type
        # Strip whitespace to normalize comparison
        element_text = element.get_text().strip()

        # Skip empty elements
        if not element_text:
            continue

        # Create a signature that includes tag name and content
        signature = f"{element.name}:{element_text}"

        # Hash longer content for efficiency
        if len(signature) > 100:
            signature = hashlib.md5(
                signature.encode(), usedforsecurity=False
            ).hexdigest()

        # Check if we've seen this element before
        if signature in element_map:
            # Found a duplicate
            duplicates.append(
                {
                    "first_occurrence": element_map[signature],
                    "duplicate_idx": idx,
                    "element_type": element.name,
                    "element_text": (
                        element_text[:100] + "..."
                        if len(element_text) > 100
                        else element_text
                    ),
                    "html": str(element),
                }
            )
        else:
            element_map[signature] = idx

    if duplicates:
        logger.debug(f"Found {len(duplicates)} potentially duplicated HTML elements")

    return duplicates


def remove_duplicate_html_elements(
    html_content: str, duplicates: List[Dict[str, Any]]
) -> str:
    """
    Remove duplicate HTML elements from the content based on identified duplicates.

    Args:
        html_content: The original HTML content
        duplicates: List of dictionaries with information about duplicate elements

    Returns:
        The cleaned HTML content with duplicates removed
    """
    if not html_content or not duplicates:
        return html_content

    soup = BeautifulSoup(html_content, "html.parser")

    # Find all significant elements
    significant_elements = soup.find_all(
        ["p", "h1", "h2", "h3", "h4", "h5", "h6", "div", "table", "ul", "ol"]
    )

    # Sort duplicates in reverse order to avoid index shifting when removing elements
    duplicates_sorted = sorted(
        duplicates, key=lambda x: x["duplicate_idx"], reverse=True
    )

    elements_removed = 0
    for duplicate in duplicates_sorted:
        try:
            duplicate_idx = duplicate["duplicate_idx"]

            # Make sure the index is valid
            if duplicate_idx < len(significant_elements):
                element_to_remove = significant_elements[duplicate_idx]

                # Double-check this is the right element by comparing HTML content
                if str(element_to_remove) == duplicate["html"]:
                    element_to_remove.decompose()
                    elements_removed += 1
                else:
                    logger.warning(
                        f"Element mismatch during duplicate removal: {duplicate['element_text'][:50]}"
                    )
        except Exception as e:
            logger.error(f"Error removing duplicate element: {e}")

    if elements_removed > 0:
        logger.debug(f"Removed {elements_removed} duplicate elements from HTML content")

    return str(soup)


def build_html_data(
    result_data: Dict[str, Any], output_dir: str, is_single_page: bool = False
) -> Dict[str, Any]:
    """
    Build HTML pages from BDA result elements.

    Args:
        result_data: The BDA result data containing elements and pages
        output_dir: Directory to save HTML files
        is_single_page: Whether to use the single continuous HTML from document.representation.html

    Returns:
        Dict containing paths to extracted HTML files
    """
    logger.debug("Building document from elements")
    extracted_html_files = []

    # Create a subdirectory for extracted HTML files
    html_output_dir = os.path.join(output_dir, "extracted_html")
    os.makedirs(html_output_dir, exist_ok=True)

    # Get the total number of pages
    num_pages = len(result_data.get("pages", []))

    # Track elements we've already processed to avoid duplicates
    processed_pages = set()

    # Process each page
    for i in range(num_pages):
        # Build the page HTML
        page_html = result_data["pages"][i].get("representation", {}).get("html", "")
        if not page_html:
            logger.warning(f"Page {i+1} has no HTML representation")
            continue

        # Check for duplicated elements in the page
        duplicates = identify_duplicate_html_elements(page_html)
        if duplicates:
            logger.warning(f"Page {i+1} contains {len(duplicates)} duplicated elements")
            # Clean the HTML by removing duplicates
            page_html = remove_duplicate_html_elements(page_html, duplicates)
            # Update the page HTML in the result data
            result_data["pages"][i]["representation"]["html"] = page_html

        processed_pages.add(i)

    if not is_single_page:
        for i in processed_pages:
            # Get the page HTML
            page_html = (
                result_data["pages"][i].get("representation", {}).get("html", "")
            )
            # Create individual page HTML file
            page_file_path = os.path.join(html_output_dir, f"page-{i}.html")
            try:
                with open(page_file_path, "w", encoding="utf-8") as f:
                    f.write('<!DOCTYPE html>\n<html lang="en">\n<head>\n')
                    f.write('    <meta charset="UTF-8">\n')
                    f.write(
                        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
                    )
                    f.write(f"    <title>Page {i+1}</title>\n")
                    f.write(
                        "    <style>\n        body { font-family: Arial, sans-serif; line-height: 1.6; }\n    </style>\n"
                    )
                    f.write("</head>\n<body>\n")
                    f.write(page_html)
                    f.write("\n</body>\n</html>")

                extracted_html_files.append(page_file_path)
                logger.debug(f"Created HTML file for page {i+1}: {page_file_path}")
            except Exception as e:
                logger.error(f"Error writing page HTML file {page_file_path}: {e}")

    else:
        # Create combined HTML file
        combined_html_parts = [
            "<!DOCTYPE html>",
            '<html lang="en">',
            "<head>",
            '    <meta charset="UTF-8">',
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f'    <title>{"Document" if "metadata" not in result_data else result_data["metadata"].get("asset_id", "Document")}</title>',
            "    <style>",
            "        body { font-family: Arial, sans-serif; line-height: 1.6; }",
            "        .page-break { page-break-after: always; margin-bottom: 30px; border-bottom: 1px dashed #ccc; }",
            "    </style>",
            "</head>",
            "<body>",
            "<nav><ul>"
        ]
        pages = []
        for i in range(num_pages):
            page_html = (
                result_data["pages"][i].get("representation", {}).get("html", "")
            )
            menu_link = f'<li><a href="#page-{i}">Page {i+1}</a></li>'
            combined_html_parts.append(menu_link)

            duplicates = identify_duplicate_html_elements(page_html)
            if duplicates:
                logger.warning(
                    f"Page {i+1} contains {len(duplicates)} duplicated elements in combined view"
                )
                # Clean the HTML by removing duplicates
                page_html = remove_duplicate_html_elements(page_html, duplicates)

            pages.append(f'<div id="page-{i}" class="page">')
            pages.append(page_html)
            pages.append("</div>")
            if i < num_pages - 1:
                pages.append('<div class="page-break"></div>')

        combined_html_parts.append("</ul></nav>")
        combined_html_parts.extend(pages)
        combined_html_parts.append("</body>\n</html>")
        combined_html = "\n".join(combined_html_parts)
        try:
            combined_file_path = os.path.join(html_output_dir, "remediated.html")
            with open(combined_file_path, "w", encoding="utf-8") as f:
                f.write(combined_html)
            extracted_html_files.insert(
                0, combined_file_path
            )  # Put the combined file first in the list
            logger.debug(f"Created combined HTML file: {combined_file_path}")
        except Exception as e:
            logger.error(f"Error creating combined HTML file {combined_file_path}: {e}")

    copy_all_images_to_html_dir(output_dir, html_output_dir)

    return {
        "html_files": extracted_html_files,
    }


def copy_all_images_to_html_dir(output_dir, html_output_dir):
    """
    Copy all image files to the extracted_html directory.

    Args:
        output_dir: Base output directory
        html_output_dir: HTML output directory
    """
    logger.debug("Copying all image files to HTML directory...")

    # Find all image files in the output directory
    image_files = []
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            if file.endswith(".png") or file.endswith(".jpg"):
                image_files.append(os.path.join(root, file))

    logger.debug(f"Found {len(image_files)} image files")

    # Copy each image file to the HTML directory
    copied_files = 0
    for image_file in image_files:
        try:
            dest_file = os.path.join(html_output_dir, os.path.basename(image_file))
            if not os.path.exists(dest_file):
                shutil.copy2(image_file, dest_file)
                copied_files += 1
                logger.debug(f"Copied image file: {image_file} -> {dest_file}")
        except Exception as e:
            logger.warning(f"Failed to copy image file {image_file}: {e}")

    logger.debug(f"Copied {copied_files} image files to HTML directory")
