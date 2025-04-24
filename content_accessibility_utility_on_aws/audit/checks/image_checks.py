# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0


"""
Image accessibility checks.

This module provides checks for proper image accessibility.
"""

from content_accessibility_utility_on_aws.audit.base_check import AccessibilityCheck


class AltTextCheck(AccessibilityCheck):
    """Check for proper alt text on images (WCAG 1.1.1)."""

    def check(self) -> None:
        """
        Check if images have appropriate alt text.

        Issues:
            - missing-alt-text: When an image has no alt attribute
            - empty-alt-text: When an image has an empty alt attribute
            - generic-alt-text: When an image has generic alt text like "image"
            - compliant-alt-text: When an image has proper alt text
        """
        images = self.soup.find_all("img")

        if not images:
            return  # No images to check

        for img in images:
            if not img.has_attr("alt"):
                self.add_issue(
                    "missing-alt-text",
                    "1.1.1",
                    "critical",
                    element=img,
                    description="Image missing alt text",
                    status="needs_remediation",
                )
            else:
                alt_text = img["alt"].strip()
                if not alt_text:
                    # Check if this is a decorative image
                    if (
                        img.get("role") == "presentation"
                        or img.get("aria-hidden") == "true"
                    ):
                        self.add_issue(
                            "compliant-decorative-image",
                            "1.1.1",
                            "minor",
                            element=img,
                            description="Decorative image properly marked",
                            status="compliant",
                        )
                    else:
                        self.add_issue(
                            "empty-alt-text",
                            "1.1.1",
                            "major",
                            element=img,
                            description="Image has empty alt text but is not marked as decorative",
                            status="needs_remediation",
                        )
                elif alt_text.lower() in [
                    "image",
                    "diagram",
                    "photo",
                    "picture",
                    "graphic",
                    "icon",
                ]:
                    self.add_issue(
                        "generic-alt-text",
                        "1.1.1",
                        "major",
                        element=img,
                        description=f"Image has generic alt text: '{alt_text}'",
                        status="needs_remediation",
                    )
                else:
                    # Image has non-empty, non-generic alt text
                    self.add_issue(
                        "compliant-alt-text",
                        "1.1.1",
                        "critical",
                        element=img,
                        description="Image has proper alt text",
                        status="compliant",
                    )


class FigureStructureCheck(AccessibilityCheck):
    """Check for proper figure structure (WCAG 1.1.1)."""

    def check(self) -> None:
        """
        Check if figures have proper structure and captions.

        Issues:
            - missing-figure-caption: When a figure has no caption
            - empty-figure-caption: When a figure has an empty caption
            - compliant-figure-structure: When a figure has proper structure
        """
        figures = self.soup.find_all("figure")

        if not figures:
            return  # No figures to check

        for figure in figures:
            caption = figure.find("figcaption")

            if not caption:
                self.add_issue(
                    "missing-figure-caption",
                    "1.1.1",
                    "major",
                    element=figure,
                    description="Figure missing caption",
                    status="needs_remediation",
                )
            else:
                caption_text = self.get_element_text(caption)
                if not caption_text:
                    self.add_issue(
                        "empty-figure-caption",
                        "1.1.1",
                        "major",
                        element=figure,
                        description="Figure has empty caption",
                        status="needs_remediation",
                    )
                else:
                    # Figure has proper structure and non-empty caption
                    self.add_issue(
                        "compliant-figure-structure",
                        "1.1.1",
                        "major",
                        element=figure,
                        description="Figure has proper structure and caption",
                        status="compliant",
                    )
