# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Color contrast accessibility checks.

This module provides checks for proper color contrast between text and background.
"""

import re
from typing import Tuple, Optional
from bs4 import Tag

from content_accessibility_utility_on_aws.audit.base_check import AccessibilityCheck


class ColorContrastCheck(AccessibilityCheck):
    """Check for proper color contrast (WCAG 1.4.3, 1.4.11)."""

    def check(self) -> None:
        """
        Check if text elements have sufficient color contrast with their background.

        Issues:
            - insufficient-color-contrast: When text color doesn't have
                enough contrast with background
            - potential-color-contrast-issue: When contrast can't be determined automatically
        """
        # Elements that typically contain text
        text_elements = self.soup.find_all(
            [
                "p",
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "h6",
                "a",
                "span",
                "div",
                "li",
                "td",
                "th",
            ]
        )

        for element in text_elements:
            # Skip empty elements
            if not self.get_element_text(element).strip():
                continue

            # Get text and background colors
            text_color = self._get_text_color(element)
            bg_color = self._get_background_color(element)

            # If we couldn't determine colors, flag as potential issue
            if not text_color or not bg_color:
                # Only report if the element has inline style or class
                if element.get("style") or element.get("class"):
                    self.add_issue(
                        "potential-color-contrast-issue",
                        "1.4.3",
                        "minor",
                        element=element,
                        description="Potential color contrast issue - colors"
                        + "could not be determined automatically",
                    )
                continue

            # Calculate contrast ratio
            contrast_ratio = self._calculate_contrast_ratio(text_color, bg_color)

            # Determine minimum required contrast based on text size
            is_large_text = self._is_large_text(element)
            min_contrast = 3.0 if is_large_text else 4.5

            # Check if contrast is sufficient
            if contrast_ratio < min_contrast:
                self.add_issue(
                    "insufficient-color-contrast",
                    "1.4.3",
                    "major",
                    element=element,
                    description=f"Insufficient color contrast: {contrast_ratio:.2f}:1 "
                    + "(minimum required: {min_contrast}:1)",
                    location={
                        "text_color": text_color,
                        "background_color": bg_color,
                        "contrast_ratio": f"{contrast_ratio:.2f}:1",
                        "required_ratio": f"{min_contrast}:1",
                        "is_large_text": is_large_text,
                    },
                )

    def _get_text_color(self, element: Tag) -> Optional[str]:
        """
        Get the text color of an element.

        Args:
            element: The element to check

        Returns:
            The text color as a hex string, or None if it couldn't be determined
        """
        # Check for inline color style
        if element.get("style"):
            color_match = re.search(
                r"color:\s*(#[0-9a-fA-F]{3,6}|rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\))",
                element["style"],
            )
            if color_match:
                return self._normalize_color(color_match.group(1))

        # Default to black if no color is specified
        return "#000000"

    def _get_background_color(self, element: Tag) -> Optional[str]:
        """
        Get the background color of an element.

        Args:
            element: The element to check

        Returns:
            The background color as a hex string, or None if it couldn't be determined
        """
        # Check for inline background-color style
        if element.get("style"):
            bg_match = re.search(
                r"background-color:\s*(#[0-9a-fA-F]{3,6}|rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\))",
                element["style"],
            )
            if bg_match:
                return self._normalize_color(bg_match.group(1))

        # Check parent elements for background color
        parent = element.parent
        while parent and parent.name != "html":
            if parent.get("style"):
                bg_match = re.search(
                    r"background-color:\s*(#[0-9a-fA-F]{3,6}|rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\))",
                    parent["style"],
                )
                if bg_match:
                    return self._normalize_color(bg_match.group(1))
            parent = parent.parent

        # Default to white if no background color is specified
        return "#FFFFFF"

    def _normalize_color(self, color: str) -> str:
        """
        Normalize a color value to a hex string.

        Args:
            color: The color value to normalize

        Returns:
            The normalized color as a hex string
        """
        # Handle hex colors
        if color.startswith("#"):
            # Convert 3-digit hex to 6-digit
            if len(color) == 4:
                r, g, b = color[1], color[2], color[3]
                return f"#{r}{r}{g}{g}{b}{b}".upper()
            return color.upper()

        # Handle rgb() colors
        rgb_match = re.match(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", color)
        if rgb_match:
            r, g, b = map(int, rgb_match.groups())
            return f"#{r:02X}{g:02X}{b:02X}"

        return color

    def _calculate_contrast_ratio(self, color1: str, color2: str) -> float:
        """
        Calculate the contrast ratio between two colors.

        Args:
            color1: The first color as a hex string
            color2: The second color as a hex string

        Returns:
            The contrast ratio as a float
        """
        # Convert hex to RGB
        rgb1 = self._hex_to_rgb(color1)
        rgb2 = self._hex_to_rgb(color2)

        # Calculate relative luminance
        l1 = self._relative_luminance(rgb1)
        l2 = self._relative_luminance(rgb2)

        # Calculate contrast ratio
        if l1 > l2:
            return (l1 + 0.05) / (l2 + 0.05)
        else:
            return (l2 + 0.05) / (l1 + 0.05)

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """
        Convert a hex color to RGB.

        Args:
            hex_color: The hex color string

        Returns:
            A tuple of (r, g, b) values
        """
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    def _relative_luminance(self, rgb: Tuple[int, int, int]) -> float:
        """
        Calculate the relative luminance of an RGB color.

        Args:
            rgb: The RGB color as a tuple of (r, g, b) values

        Returns:
            The relative luminance as a float
        """
        r, g, b = rgb

        # Normalize RGB values
        r = r / 255
        g = g / 255
        b = b / 255

        # Apply gamma correction
        r = self._gamma_correct(r)
        g = self._gamma_correct(g)
        b = self._gamma_correct(b)

        # Calculate luminance
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def _gamma_correct(self, value: float) -> float:
        """
        Apply gamma correction to a color channel value.

        Args:
            value: The color channel value (0-1)

        Returns:
            The gamma-corrected value
        """
        if value <= 0.03928:
            return value / 12.92
        else:
            return ((value + 0.055) / 1.055) ** 2.4

    def _is_large_text(self, element: Tag) -> bool:
        """
        Determine if an element contains large text.

        Args:
            element: The element to check

        Returns:
            True if the element contains large text, False otherwise
        """
        # Check for heading elements (h1, h2, h3)
        if element.name in ["h1", "h2", "h3"]:
            return True

        # Check for font-size style
        if element.get("style"):
            size_match = re.search(
                r"font-size:\s*(\d+)(px|pt|em|rem)", element["style"]
            )
            if size_match:
                size = float(size_match.group(1))
                unit = size_match.group(2)

                # Convert to pixels (approximate)
                if unit == "pt":
                    size = size * 1.333
                elif unit == "em" or unit == "rem":
                    size = size * 16

                # Large text is 18pt (24px) or 14pt (18.67px) bold
                if size >= 24:
                    return True
                if size >= 18.67 and self._is_bold(element):
                    return True

        return False

    def _is_bold(self, element: Tag) -> bool:
        """
        Determine if an element has bold text.

        Args:
            element: The element to check

        Returns:
            True if the element has bold text, False otherwise
        """
        # Check for bold element
        if element.name in ["b", "strong"]:
            return True

        # Check for font-weight style
        if element.get("style"):
            weight_match = re.search(
                r"font-weight:\s*(bold|700|800|900)", element["style"]
            )
            if weight_match:
                return True

        return False
