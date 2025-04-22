# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Color contrast accessibility remediation strategies.

This module provides remediation strategies for color contrast-related accessibility issues.
"""

from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
import re


def remediate_insufficient_color_contrast(
    soup: BeautifulSoup, issue: Dict[str, Any]
) -> Optional[str]:
    """
    Remediate insufficient color contrast by adjusting text or background color.

    Args:
        soup: The BeautifulSoup object representing the HTML document
        issue: The accessibility issue to remediate

    Returns:
        A message describing the remediation, or None if no remediation was performed
    """
    # Find the element from the issue
    element_str = issue.get("element", "")
    if not element_str:
        return None

    # Extract element tag name
    tag_match = re.match(r"<([a-zA-Z0-9]+)", element_str)
    if not tag_match:
        return None

    tag_name = tag_match.group(1)

    # Try to find the element in the document
    # This is a simplified approach - in a real implementation, we would need a more robust way to find the element
    elements = soup.find_all(tag_name)
    if not elements:
        return None

    # Extract class information if available
    class_match = re.search(r'class="([^"]*)"', element_str)
    class_names = class_match.group(1).split() if class_match else []

    # Find elements with matching classes
    matching_elements = []
    for element in elements:
        if class_names:
            element_classes = element.get("class", [])
            if all(cls in element_classes for cls in class_names):
                matching_elements.append(element)
        else:
            # If no class to match, just use the first element of the tag type
            matching_elements.append(element)
            break

    if not matching_elements:
        return None

    # Apply contrast fix to all matching elements
    for element in matching_elements:
        # Determine if we should adjust text color or background color
        # For simplicity, we'll always adjust text color to black or white

        # Check if the element has inline style with background-color
        style = element.get("style", "")
        bg_color_match = re.search(r"background-color:\s*([^;]+)", style)

        if bg_color_match:
            bg_color = bg_color_match.group(1).strip().lower()

            # Determine if background is light or dark (simplified)
            is_dark_bg = _is_dark_color(bg_color)

            # Set text color based on background
            new_color = "#FFFFFF" if is_dark_bg else "#000000"

            # Update or add color to style
            if "color:" in style:
                style = re.sub(r"color:\s*[^;]+", f"color: {new_color}", style)
            else:
                style += f"; color: {new_color}"

            element["style"] = style
            return f"Adjusted text color to {new_color} for better contrast"

        # If no background color in style, check for text color
        color_match = re.search(r"color:\s*([^;]+)", style)
        if color_match:
            text_color = color_match.group(1).strip().lower()

            # Determine if text is light or dark (simplified)
            is_dark_text = _is_dark_color(text_color)

            # Set background color based on text
            new_bg_color = "#000000" if is_dark_text else "#FFFFFF"

            # Update or add background-color to style
            if "background-color:" in style:
                style = re.sub(
                    r"background-color:\s*[^;]+",
                    f"background-color: {new_bg_color}",
                    style,
                )
            else:
                style += f"; background-color: {new_bg_color}"

            element["style"] = style
            return f"Adjusted background color to {new_bg_color} for better contrast"

        # If no inline styles, add them
        element["style"] = "color: #000000; background-color: #FFFFFF"
        return "Added high contrast colors (black text on white background)"

    return None


def _is_dark_color(color: str) -> bool:
    """
    Determine if a color is dark or light.

    Args:
        color: CSS color value

    Returns:
        True if the color is dark, False if it's light
    """
    # Handle hex colors
    if color.startswith("#"):
        if len(color) == 4:  # Short hex (#RGB)
            r = int(color[1] + color[1], 16)
            g = int(color[2] + color[2], 16)
            b = int(color[3] + color[3], 16)
        elif len(color) == 7:  # Full hex (#RRGGBB)
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
        else:
            return False  # Invalid hex

    # Handle rgb/rgba colors
    elif color.startswith("rgb"):
        rgb_match = re.search(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", color)
        if rgb_match:
            r = int(rgb_match.group(1))
            g = int(rgb_match.group(2))
            b = int(rgb_match.group(3))
        else:
            return False  # Invalid rgb

    # Handle named colors (simplified)
    elif color in [
        "black",
        "darkblue",
        "darkgreen",
        "darkred",
        "navy",
        "purple",
        "brown",
    ]:
        return True
    # elif color in ['white', 'yellow', 'lime', 'cyan', 'pink', 'lightblue', 'lightgreen']:
    #     return False
    else:
        return False  # Unknown color

    # Calculate perceived brightness
    # Formula: (0.299*R + 0.587*G + 0.114*B)
    brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255

    # Return True if dark (brightness < 0.5)
    return brightness < 0.5
