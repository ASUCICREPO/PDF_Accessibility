# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0


"""
Link-related accessibility checks.

This module provides checks for proper link accessibility.
"""

import re
from typing import List, Dict

from content_accessibility_utility_on_aws.audit.base_check import AccessibilityCheck


class LinkTextCheck(AccessibilityCheck):
    """Check for proper link text (WCAG 2.4.4, 2.4.9)."""

    def check(self) -> None:
        """
        Check if links have descriptive text.

        Issues:
            - empty-link-text: When a link has no text content
            - generic-link-text: When a link has generic text like "click here" or "read more"
            - url-as-link-text: When a link text is just a URL
            - duplicate-link-text-different-url: When links with same
              text go to different destinations
            - compliant-link-text: When a link has descriptive text (compliance success)
        """
        links = self.soup.find_all("a")

        # Track links by text for duplicate detection
        links_by_text: Dict[str, List[str]] = {}

        # Generic link text patterns
        generic_link_texts = [
            "click here",
            "click",
            "here",
            "read more",
            "more",
            "learn more",
            "details",
            "link",
            "this link",
            "this page",
            "this",
            "go",
            "go to",
            "view",
            "view more",
            "see more",
            "see details",
            "continue",
            "continue reading",
        ]

        for link in links:
            # Skip links that are just anchors
            if link.get("href", "").startswith("#") and not link.get("href", "").strip(
                "#"
            ):
                continue

            # Get visible text
            text = self.get_element_text(link)

            # Check for empty links
            if not text:
                # Check if there's an image with alt text
                img = link.find("img")
                if img and img.get("alt"):
                    self.add_issue(
                        "compliant-image-link",
                        "2.4.4",
                        "info",
                        element=link,
                        description="Link with image has appropriate alt"
                        + f"text: \"{img.get('alt')}\"",
                        status="compliant",
                    )
                    continue

                self.add_issue(
                    "empty-link-text",
                    "2.4.4",
                    "critical",
                    element=link,
                    description="Link has no text content",
                )
                continue

            # Check for generic link text
            text_lower = text.lower()
            if text_lower in generic_link_texts:
                self.add_issue(
                    "generic-link-text",
                    "2.4.4",
                    "major",
                    element=link,
                    description=f"Generic link text: '{text}' is not descriptive",
                )

            # Check for URL as link text
            elif self._is_url(text):
                self.add_issue(
                    "url-as-link-text",
                    "2.4.4",
                    "minor",
                    element=link,
                    description=f"URL used as link text: '{text}'",
                )
            else:
                # Link has descriptive text - report as compliant
                self.add_issue(
                    "compliant-link-text",
                    "2.4.4",
                    "info",
                    element=link,
                    description=f"Link has descriptive text: '{text}'",
                    status="compliant",
                )

            # Track links by text for duplicate detection
            href = link.get("href", "")
            if text_lower not in links_by_text:
                links_by_text[text_lower] = []
            links_by_text[text_lower].append(href)

        # Check for duplicate link text with different destinations
        for text, hrefs in links_by_text.items():
            if len(hrefs) > 1 and len(set(hrefs)) > 1:
                # Find all links with this text
                for link in self.soup.find_all(
                    "a", text=re.compile(f"^{re.escape(text)}$", re.IGNORECASE)
                ):
                    self.add_issue(
                        "duplicate-link-text-different-url",
                        "2.4.9",
                        "major",
                        element=link,
                        description=f"Multiple links with text '{text}'"
                        + "go to different destinations",
                    )

    def _is_url(self, text: str) -> bool:
        """
        Check if text appears to be a URL.

        Args:
            text: The text to check

        Returns:
            True if the text appears to be a URL, False otherwise
        """
        url_patterns = [
            r"^https?://",
            r"^www\.",
            r"\.com(/|$)",
            r"\.org(/|$)",
            r"\.net(/|$)",
            r"\.edu(/|$)",
            r"\.gov(/|$)",
            r"\.io(/|$)",
        ]

        return any(re.search(pattern, text, re.IGNORECASE) for pattern in url_patterns)


class NewWindowLinkCheck(AccessibilityCheck):
    """Check for links that open in new windows (WCAG 3.2.5)."""

    def check(self) -> None:
        """
        Check if links that open in new windows have appropriate warning.

        Issues:
            - new-window-link-no-warning: When a link opens in a new window without warning
            - compliant-new-window-link: When a link opens in a new window with appropriate warning
        """
        # Find links with target="_blank" or rel="external"
        new_window_links = self.soup.find_all("a", attrs={"target": "_blank"})
        new_window_links.extend(self.soup.find_all("a", attrs={"rel": "external"}))

        for link in new_window_links:
            text = self.get_element_text(link)

            # Check if there's a warning about new window
            has_warning = False
            warning_method = ""

            # Check for common warning phrases in text
            warning_phrases = ["new window", "new tab", "opens in new", "external"]
            if any(phrase in text.lower() for phrase in warning_phrases):
                has_warning = True
                warning_method = "text content"

            # Check for aria-label with warning
            aria_label = link.get("aria-label", "")
            if any(phrase in aria_label.lower() for phrase in warning_phrases):
                has_warning = True
                warning_method = "aria-label"

            # Check for title attribute with warning
            title = link.get("title", "")
            if any(phrase in title.lower() for phrase in warning_phrases):
                has_warning = True
                warning_method = "title attribute"

            # Check for screen reader text
            sr_elements = link.find_all(
                ["span", "div"],
                class_=lambda c: c
                and any(
                    sr_class in c
                    for sr_class in ["sr-only", "visually-hidden", "screen-reader-text"]
                ),
            )
            for sr_elem in sr_elements:
                sr_text = sr_elem.get_text(strip=True)
                if any(phrase in sr_text.lower() for phrase in warning_phrases):
                    has_warning = True
                    warning_method = "screen reader text"

            # Check for icon indicating external link
            if link.find(
                "i",
                class_=lambda c: c
                and any(
                    icon_class in c
                    for icon_class in ["external", "new-window", "fa-external-link"]
                ),
            ):
                has_warning = True
                warning_method = "icon"

            if has_warning:
                self.add_issue(
                    "compliant-new-window-link",
                    "3.2.5",
                    "info",
                    element=link,
                    description="Link opens in new window with appropriate warning"
                    + f" via {warning_method}: '{text}'",
                    status="compliant",
                )
            else:
                self.add_issue(
                    "new-window-link-no-warning",
                    "3.2.5",
                    "minor",
                    element=link,
                    description=f"Link opens in new window without warning: '{text}'",
                )
