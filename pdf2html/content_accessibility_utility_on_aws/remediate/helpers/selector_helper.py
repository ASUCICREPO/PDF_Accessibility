# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Selector Helper module.

This module provides functionality to generate and manipulate CSS selectors
for HTML elements.
"""

from typing import Optional
from bs4 import BeautifulSoup

from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger

# Set up module-level logger
logger = setup_logger(__name__)


class SelectorHelper:
    """
    Class for generating and manipulating CSS selectors for HTML elements.
    """

    @staticmethod
    def generate_selector(
        element_html: str, context_html: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate a CSS selector for an HTML element.

        Args:
            element_html: HTML of the element
            context_html: HTML context surrounding the element

        Returns:
            CSS selector or None if not possible
        """
        try:
            # Parse the element HTML
            soup = BeautifulSoup(element_html, "html.parser")
            element = soup.find()

            if not element:
                return None

            # Start with the tag name
            selector = element.name

            # Add ID if available
            if element.get("id"):
                selector = f"{selector}#{element['id']}"
                return selector

            # Add classes if available
            if element.get("class"):
                classes = ".".join(element["class"])
                selector = f"{selector}.{classes}"
                return selector

            # Add data attributes if available
            for attr in element.attrs:
                if attr.startswith("data-"):
                    selector = f"{selector}[{attr}='{element[attr]}']"
                    return selector

            # For images, use src attribute
            if element.name == "img" and element.get("src"):
                src = element["src"].split("/")[-1]  # Just use filename
                selector = f"{selector}[src$='{src}']"
                return selector

            # If we have context, try to create a more specific selector
            if context_html:
                context_soup = BeautifulSoup(context_html, "html.parser")
                parent = context_soup.find(element.name)

                if parent:
                    # Count siblings with same tag
                    siblings = parent.find_all(element.name)
                    if len(siblings) > 1:
                        # Find position of this element
                        for i, sibling in enumerate(siblings):
                            if str(sibling) == str(element):
                                selector = f"{selector}:nth-of-type({i+1})"
                                break

            return selector

        except Exception as e:
            logger.warning(f"Error generating selector: {e}")
            return None

    @staticmethod
    def get_element_by_selector(html: str, selector: str) -> Optional[BeautifulSoup]:
        """
        Get an element from HTML using a CSS selector.

        Args:
            html: HTML content
            selector: CSS selector

        Returns:
            BeautifulSoup element or None if not found
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
            return soup.select_one(selector)
        except Exception as e:
            logger.warning(f"Error getting element by selector: {e}")
            return None

    @staticmethod
    def get_element_context(
        html: str, selector: str, context_size: int = 3
    ) -> Optional[str]:
        """
        Get the HTML context surrounding an element.

        Args:
            html: HTML content
            selector: CSS selector for the element
            context_size: Number of siblings to include before and after

        Returns:
            HTML context or None if element not found
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
            element = soup.select_one(selector)

            if not element:
                return None

            # Get parent
            parent = element.parent

            # Get siblings
            siblings = list(parent.children)

            # Find index of element in siblings
            element_index = None
            for i, sibling in enumerate(siblings):
                if sibling is element:
                    element_index = i
                    break

            if element_index is None:
                return str(parent)

            # Get context range
            start = max(0, element_index - context_size)
            end = min(len(siblings), element_index + context_size + 1)

            # Create a new element with just the context
            context_soup = BeautifulSoup("<div></div>", "html.parser")
            context_div = context_soup.div

            # Add siblings in context range
            for i in range(start, end):
                context_div.append(siblings[i])

            return str(context_div)

        except Exception as e:
            logger.warning(f"Error getting element context: {e}")
            return None
