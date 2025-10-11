# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Image Utility Functions.

This module provides functions for handling images in HTML documents, including
finding, copying, and updating image references.
"""

import os
import shutil
from typing import List, Optional
from bs4 import BeautifulSoup
from PIL import Image

from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger

# Set up module-level logger
logger = setup_logger(__name__)


def find_images_in_html(soup: BeautifulSoup) -> List:
    """
    Extract all image elements from an HTML document.

    Args:
        soup: BeautifulSoup object representing the HTML document

    Returns:
        List of image elements found in the HTML
    """
    images = soup.find_all("img")
    logger.debug(f"Found {len(images)} images in HTML")
    return images


def resize_image(image_path: str, max_size: int = 4000000, quality: int = 85) -> str:
    """
    Resize an image if it exceeds size limits while preserving aspect ratio.
    Will progressively reduce dimensions until the file is below max_size.

    Args:
        image_path: Path to the image file
        max_size: Maximum allowed size in bytes (default 4MB)
        quality: JPEG quality percentage (1-100)

    Returns:
        Path to the resized image (original path if not resized)

    Raises:
        ValueError: If image cannot be processed
    """
    try:
        original_size = os.path.getsize(image_path)
        if original_size <= max_size:
            return image_path

        with Image.open(image_path) as img:
            # Get format or default to PNG
            img_format = img.format or "PNG"
            
            # Map format to appropriate extension and ensure lowercase
            format_ext_map = {
                "JPEG": "jpg",
                "PNG": "png",
                "GIF": "gif",
                "BMP": "bmp",
                "TIFF": "tif",
                "WEBP": "webp"
            }
            ext = format_ext_map.get(img_format, "jpg").lower()
            temp_path = f"{image_path}.resized.{ext}"

            # Calculate initial dimensions
            width, height = img.size
            ratio = (max_size / original_size) ** 0.5
            new_width = int(width * ratio)
            new_height = int(height * ratio)

            # Convert mode if necessary for format compatibility
            if img_format == "JPEG" and img.mode == "RGBA":
                img = img.convert("RGB")
            
            # Initial quality setting
            current_quality = quality
            
            # Try up to 10 times with progressively smaller dimensions
            for attempt in range(10):
                # Ensure minimum dimensions
                new_width = max(new_width, 100)
                new_height = max(new_height, 100)
                
                logger.debug(f"Resize attempt {attempt+1}: {new_width}x{new_height}, quality={current_quality}")
                
                # Resize the image
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Save with optimized settings
                save_kwargs = {}
                if img_format in ("JPEG", "PNG"):
                    save_kwargs["optimize"] = True
                if img_format == "JPEG":
                    save_kwargs["quality"] = current_quality
                    save_kwargs["progressive"] = True
                elif img_format == "PNG":
                    save_kwargs["compress_level"] = 9
                
                resized_img.save(temp_path, format=img_format, **save_kwargs)
                
                # Check if we succeeded
                new_size = os.path.getsize(temp_path)
                if new_size <= max_size:
                    logger.debug(f"Successfully resized image to {new_size} bytes ({new_width}x{new_height}, quality={current_quality})")
                    return temp_path
                
                # Adjust for next attempt - first reduce quality, then dimensions
                if img_format == "JPEG" and current_quality > 60:
                    current_quality = max(current_quality - 10, 60)
                else:
                    # Reduce dimensions by 20% each time
                    new_width = int(new_width * 0.8)
                    new_height = int(new_height * 0.8)
                    
                    # If dimensions are getting too small, just reduce quality further
                    if new_width < 300 and img_format == "JPEG" and current_quality > 40:
                        new_width = int(width * 0.3)  # Reset to 30% of original
                        new_height = int(height * 0.3)
                        current_quality = max(current_quality - 15, 40)
            
            # If we've tried everything and failed
            os.remove(temp_path)
            logger.warning(f"Failed to resize image to meet size requirement after multiple attempts: {image_path}")
            raise ValueError(f"Could not resize image to meet {max_size} byte limit after multiple attempts")
            
    except (IOError, OSError) as e:
        logger.error(f"Error processing image {image_path}: {str(e)}")
        return image_path  # Return original path if resizing fails


def find_image_directory(base_path: str) -> Optional[str]:
    """
    Find the most likely directory containing images based on a base path.

    Args:
        base_path: Base path (HTML file or directory) to search from

    Returns:
        Path to the likely image directory, or None if not found
    """
    # Try common image directory locations
    potential_image_dirs = [
        os.path.join(os.path.dirname(base_path), "images"),
        os.path.join(base_path, "images") if os.path.isdir(base_path) else None,
        os.path.join(os.path.dirname(base_path), "assets"),
        os.path.join(os.path.dirname(os.path.dirname(base_path)), "images"),
        os.path.join(os.path.dirname(os.path.dirname(base_path)), "assets"),
        os.path.join(os.path.dirname(base_path), "extracted_html"),
    ]

    # Filter out None values and check if directories exist
    potential_image_dirs = [d for d in potential_image_dirs if d and os.path.isdir(d)]

    if potential_image_dirs:
        image_dir = potential_image_dirs[0]
        logger.debug(f"Found likely image directory: {image_dir}")
        return image_dir

    # If no specific image directory found, use the HTML directory itself
    if os.path.isdir(base_path):
        logger.debug(f"Using base directory as image source: {base_path}")
        return base_path
    else:
        parent_dir = os.path.dirname(base_path)
        logger.debug(f"Using parent directory as image source: {parent_dir}")
        return parent_dir


def resolve_image_path(image_filename: str, base_dirs: List[str]) -> Optional[str]:
    """
    Find the actual path to an image file checking multiple possible locations.

    Args:
        image_filename: Name of the image file to locate
        base_dirs: List of directories to search in

    Returns:
        Full path to the image file if found, None otherwise
    """
    # Generate potential locations to check
    potential_locations = []

    # Check standard locations
    for base_dir in base_dirs:
        if not base_dir:
            continue

        potential_locations.extend(
            [
                # Direct in directory
                os.path.join(base_dir, image_filename),
                # In extracted_html subdirectory
                os.path.join(base_dir, "extracted_html", image_filename),
                # In assets subdirectory
                os.path.join(base_dir, "assets", image_filename),
                # In parent's assets directory
                os.path.join(os.path.dirname(base_dir), "assets", image_filename),
            ]
        )

        # Look for standard_output/assets directories
        for root, dirs, _ in os.walk(os.path.dirname(base_dir)):
            if "standard_output" in root and "assets" in dirs:
                potential_locations.append(os.path.join(root, "assets", image_filename))

    # Filter out invalid paths
    potential_locations = [loc for loc in potential_locations if loc]

    # Check each location in order
    for path in potential_locations:
        if os.path.exists(path) and os.path.isfile(path):
            return path

    # If still not found, search recursively as a last resort
    logger.debug(
        f"Image not found in standard locations, searching recursively for {image_filename}"
    )
    for base_dir in base_dirs:
        if not base_dir or not os.path.exists(base_dir):
            continue

        for root, _, files in os.walk(base_dir):
            # Exact match
            if image_filename in files:
                return os.path.join(root, image_filename)

            # Check for similar filenames (same base name, different extension)
            base_name = os.path.splitext(image_filename)[0]
            for file in files:
                if file.startswith(base_name) and file.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".gif")
                ):
                    logger.debug(
                        f"Found similar filename: {file} instead of {image_filename}"
                    )
                    return os.path.join(root, file)

    # Not found
    return None


def update_image_references(soup: BeautifulSoup, path_mapping: dict) -> None:
    """
    Update image references in an HTML document to use new paths.

    Args:
        soup: BeautifulSoup object representing the HTML document
        path_mapping: Dictionary mapping original filenames to new paths
    """
    for img in soup.find_all("img"):
        if img.get("src"):
            src = img["src"]
            filename = os.path.basename(src)

            if filename in path_mapping:
                # Update the path
                img["src"] = path_mapping[filename]
                logger.debug(
                    f"Updated image reference from {src} to {path_mapping[filename]}"
                )


def copy_images_to_output(
    src_dir: str, dest_dir: str, html_soup: BeautifulSoup, use_images_prefix: bool = False
) -> dict:
    """
    Copy all image files from source directory to destination directory and update image paths.

    Args:
        src_dir: Source directory containing images
        dest_dir: Destination directory to copy images to
        html_soup: BeautifulSoup object to update image paths

    Returns:
        Dictionary mapping image filenames to their new paths
    """
    # Create destination directory if it doesn't exist
    os.makedirs(dest_dir, exist_ok=True)

    logger.debug(f"Copying images from {src_dir} to {dest_dir}")

    # Find all images in the HTML
    images = find_images_in_html(html_soup)

    copied_count = 0
    not_found_count = 0
    path_mapping = {}

    for img in images:
        if img.get("src"):
            # Get the filename from the src
            src_attr = img["src"]
            filename = os.path.basename(src_attr)
            dest_path = os.path.join(dest_dir, filename)

            logger.debug(f"Processing image: {src_attr} (filename: {filename})")

            # Check if destination already exists
            if os.path.exists(dest_path):
                logger.debug(f"Image already exists at destination: {dest_path}")
                # Use images/ prefix if requested
                if use_images_prefix:
                    rel_path = f"./images/{filename}"
                else:
                    rel_path = f"./{filename}"
                img["src"] = rel_path
                path_mapping[filename] = rel_path
                continue

            # Try to find the image file
            src_path = resolve_image_path(filename, [src_dir, os.path.dirname(src_dir)])

            if src_path:
                try:
                    logger.debug(f"Copying image from {src_path} to {dest_path}")
                    shutil.copy2(src_path, dest_path)
                    logger.debug(f"Successfully copied image: {filename}")
                    copied_count += 1

                    # Check if we're using a different filename due to similarity
                    found_filename = os.path.basename(src_path)
                    if found_filename != filename:
                        # Update the src attribute to use the found filename
                        if use_images_prefix:
                            rel_path = f"./images/{found_filename}"
                        else:
                            rel_path = f"./{found_filename}"
                        img["src"] = rel_path
                        path_mapping[filename] = rel_path
                    else:
                        # Standard relative path
                        if use_images_prefix:
                            rel_path = f"./images/{filename}"
                        else:
                            rel_path = f"./{filename}"
                        img["src"] = rel_path
                        path_mapping[filename] = rel_path

                except Exception as e:
                    logger.error(f"Error copying image {filename}: {e}")
                    not_found_count += 1
            else:
                logger.warning(f"Image file not found anywhere: {filename}")
                not_found_count += 1

                # Still update to use relative path
                if use_images_prefix:
                    rel_path = f"./images/{filename}"
                else:
                    rel_path = f"./{filename}"
                img["src"] = rel_path
                path_mapping[filename] = rel_path

    logger.debug(
        f"Image copying complete: {copied_count} copied, {not_found_count} not found"
    )
    return path_mapping
