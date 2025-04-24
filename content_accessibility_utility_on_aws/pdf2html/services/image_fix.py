# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Image src attribute fix for PDF to HTML conversion.

This module provides a function to fix image src attributes in HTML generated from PDFs.
"""

import os
import logging
import shutil
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def fix_image_src_attributes(soup, element, image_dir=None):
    """
    Fix image src attributes for FIGURE elements with crop_images.

    Args:
        soup: BeautifulSoup object containing the HTML
        element: Element data dictionary from BDA result
        image_dir: Optional directory path for relative image references

    Returns:
        bool: True if any images were fixed, False otherwise
    """
    if not (
        element.get("type") == "FIGURE"
        and element.get("sub_type") in  ["IMAGE", "DIAGRAM"]
        and element.get("crop_images")
    ):
        return False

    element_id = element.get("id")
    if not element_id:
        return False

    logger.debug(f"Fixing image src attributes for element {element_id}")
    logger.debug(f"Crop images: {element.get('crop_images')}")

    # Find elements with matching data-bda-id
    matching_elements = soup.find_all(attrs={"data-bda-id": element_id})
    if not matching_elements:
        # Try to find elements by their HTML representation
        element_html = element.get("representation", {}).get("html", "")
        if element_html:
            element_soup = BeautifulSoup(element_html, "html.parser")
            first_tag = element_soup.find()
            if first_tag:
                # Find matching elements in the page
                matching_elements = soup.find_all(
                    lambda tag: str(tag) == str(first_tag)
                )

    logger.debug(f"Found {len(matching_elements)} matching elements")

    fixed_count = 0
    for matching_element in matching_elements:
        img_tags = matching_element.find_all("img")
        logger.debug(f"Found {len(img_tags)} img tags in matching element")

        for img_tag in img_tags:
            # Extract the correct image filename from crop_images
            crop_image_path = element["crop_images"][0]
            image_filename = os.path.basename(crop_image_path)
            # Remove file extension if present and add .png
            base_filename = os.path.splitext(image_filename)[0]

            # Get the current src
            old_src = img_tag.get("src", "")
            logger.debug(f"Current img src: {old_src}")

            # Extract just the filename from the src
            src_filename = os.path.basename(old_src.replace("./", "").strip())
            logger.debug(f"Extracted src filename: {src_filename}")

            # Check if the src already matches the crop image
            expected_filename = f"{base_filename}.png"
            logger.debug(f"Expected filename: {expected_filename}")

            if src_filename == expected_filename:
                logger.debug("Src already matches crop image, no change needed")
                continue

            logger.debug(f"MISMATCH DETECTED: {src_filename} != {expected_filename}")

            # If image_dir is provided, try to copy the file
            if image_dir:
                # Source and destination paths for copying
                src_file = os.path.join(image_dir, expected_filename)
                dest_file = os.path.join(image_dir, src_filename)

                logger.debug(f"Source file: {src_file}")
                logger.debug(f"Destination file: {dest_file}")
                logger.debug(f"Source file exists: {os.path.exists(src_file)}")

                # Try to find the source file in other locations if it doesn't exist
                if not os.path.exists(src_file):
                    # Look for the file in the image_dir structure
                    for root, dirs, files in os.walk(image_dir):
                        for file in files:
                            if file == expected_filename or file == image_filename:
                                src_file = os.path.join(root, file)
                                logger.debug(f"Found source file at: {src_file}")
                                break
                        if os.path.exists(src_file):
                            break

                # Copy the crop image to match the src in the HTML
                if os.path.exists(src_file):
                    try:
                        shutil.copy2(src_file, dest_file)
                        logger.debug(f"SUCCESS: Copied image {src_file} to {dest_file}")
                        fixed_count += 1
                        continue  # Skip updating the src since we've copied the file
                    except Exception as e:
                        logger.warning(
                            f"Failed to copy image file {src_file} to {dest_file}: {e}"
                        )

            # Update the src attribute if we couldn't copy the file or no image_dir was provided
            new_src = expected_filename
            if image_dir:
                # Create a relative path based on the image_dir
                new_src = os.path.join(os.path.basename(image_dir), expected_filename)
                # Ensure forward slashes for web paths
                new_src = new_src.replace(os.sep, "/")

            img_tag["src"] = new_src
            logger.debug(f"Updated image src from {old_src} to {new_src}")
            fixed_count += 1

    return fixed_count > 0
