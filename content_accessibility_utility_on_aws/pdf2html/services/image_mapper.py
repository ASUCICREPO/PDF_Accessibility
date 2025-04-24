# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Image mapper module for PDF to HTML conversion.

This module provides functionality to map image references in HTML to their actual files.
"""

import os
import logging
import shutil
from bs4 import BeautifulSoup

# Set up module-level logger
logger = logging.getLogger(__name__)


def find_all_images(output_dir):
    """
    Find all image files in the output directory and its subdirectories.

    Args:
        output_dir: Base output directory

    Returns:
        dict: Dictionary mapping image filenames to their full paths
    """
    image_files = {}
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            if file.endswith(".png") or file.endswith(".jpg"):
                image_files[file] = os.path.join(root, file)

    logger.debug(f"Found {len(image_files)} image files in {output_dir}")
    return image_files


def copy_missing_images(html_file, output_dir, html_output_dir):
    """
    Find all image references in an HTML file and copy any missing images.

    Args:
        html_file: Path to the HTML file
        output_dir: Base output directory containing images
        html_output_dir: Directory where HTML files are stored

    Returns:
        int: Number of images copied
    """
    logger.debug(f"Checking for missing images in {html_file}")

    # Read the HTML file
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Parse the HTML
    soup = BeautifulSoup(html_content, "html.parser")

    # Find all image tags
    img_tags = soup.find_all("img")
    logger.debug(f"Found {len(img_tags)} img tags in {html_file}")

    # Find all image files in the output directory
    all_images = find_all_images(output_dir)

    # Check each image tag
    copied_count = 0
    for img_tag in img_tags:
        src = img_tag.get("src", "")
        if not src:
            continue

        # Get the filename from the src
        src_filename = os.path.basename(src.replace("./", "").strip())
        logger.debug(f"Checking image: {src_filename}")

        # Check if the image exists in the HTML output directory
        dest_file = os.path.join(html_output_dir, src_filename)
        if os.path.exists(dest_file):
            logger.debug(f"Image already exists: {dest_file}")
            continue

        # If the image doesn't exist, try to find it in the output directory
        if src_filename in all_images:
            src_file = all_images[src_filename]
            try:
                shutil.copy2(src_file, dest_file)
                logger.debug(f"Copied missing image: {src_file} -> {dest_file}")
                copied_count += 1
            except Exception as e:
                logger.warning(f"Failed to copy image {src_file}: {e}")
        else:
            # Try to find a similar image
            for img_name, img_path in all_images.items():
                try:
                    shutil.copy2(img_path, dest_file)
                    logger.debug(f"Copied alternative image: {img_path} -> {dest_file}")
                    copied_count += 1
                    break
                except Exception as e:
                    logger.warning(f"Failed to copy alternative image: {e}")

    return copied_count


def ensure_all_images_available(output_dir):
    """
    Ensure all images referenced in HTML files are available.

    Args:
        output_dir: Base output directory

    Returns:
        int: Number of images copied
    """
    logger.debug(f"Ensuring all images are available in {output_dir}")

    # Find the HTML output directory
    html_output_dir = os.path.join(output_dir, "extracted_html")
    if not os.path.exists(html_output_dir):
        logger.warning(f"HTML output directory not found: {html_output_dir}")
        return 0

    # Find all HTML files
    html_files = []
    for file in os.listdir(html_output_dir):
        if file.endswith(".html"):
            html_files.append(os.path.join(html_output_dir, file))

    logger.debug(f"Found {len(html_files)} HTML files")

    # Process each HTML file
    total_copied = 0
    for html_file in html_files:
        copied = copy_missing_images(html_file, output_dir, html_output_dir)
        total_copied += copied

    logger.debug(f"Copied {total_copied} missing images")
    return total_copied
