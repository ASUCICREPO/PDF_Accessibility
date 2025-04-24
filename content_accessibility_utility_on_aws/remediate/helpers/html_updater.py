# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
HTML updater for accessibility remediation.

This module provides utilities for updating HTML elements to fix accessibility issues.
"""

import os
import logging
from typing import Optional
from bs4 import BeautifulSoup

# Set up module-level logger
logger = logging.getLogger(__name__)


class HTMLUpdater:
    """Class for updating HTML elements to fix accessibility issues."""

    def __init__(self, html_path: str):
        """
        Initialize the HTML updater.

        Args:
            html_path: Path to the HTML file to update
        """
        self.html_path = html_path
        self.soup = None
        self.load_html()

    def load_html(self) -> bool:
        """
        Load the HTML content from file.

        Returns:
            True if loading was successful, False otherwise
        """
        logger.debug(f"Loading HTML from path: {self.html_path}")

        try:
            with open(self.html_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            logger.debug(f"Loaded {len(html_content)} characters from HTML file")
            self.soup = BeautifulSoup(html_content, "html.parser")
            return True
        except Exception as e:
            logger.error(f"Error loading HTML: {e}")
            return False

    def update_element_attribute(
        self, selector: str, attribute: str, value: str
    ) -> bool:
        """
        Update an attribute of an HTML element.

        Args:
            selector: CSS selector for the element
            attribute: Name of the attribute to update
            value: New value for the attribute

        Returns:
            True if the update was successful, False otherwise
        """
        logger.debug(f"Selector: {selector}")
        logger.debug(f"Attribute updates: {{{attribute}: {value}}}")

        try:
            element = self.soup.select_one(selector)
            if not element:
                logger.warning(f"Element not found with selector: {selector}")
                return False

            logger.debug(f"Found element with {selector}")

            # Update the attribute
            old_value = element.get(attribute, "")
            element[attribute] = value
            logger.debug(f"Setting attribute: {attribute}='{value}'")
            logger.debug(
                f"Attribute updated: {attribute} from '{old_value}' to '{value}'"
            )

            # Save the updated HTML
            self.save_html()

            return True
        except Exception as e:
            logger.error(f"Error updating element attribute: {e}")
            return False

    def update_element_content(self, selector: str, content: str) -> bool:
        """
        Update the content of an HTML element.

        Args:
            selector: CSS selector for the element
            content: New HTML content for the element

        Returns:
            True if the update was successful, False otherwise
        """
        logger.debug("===== Applying fix =====")
        logger.debug(f"Selector: {selector}")
        logger.debug(f"Content updates provided: True")

        try:
            element = self.soup.select_one(selector)
            if not element:
                logger.warning(f"Element not found with selector: {selector}")
                return False

            logger.debug(f"Found element with {selector}")

            # Update the content
            old_content = str(element)[:50] + ("..." if len(str(element)) > 50 else "")
            new_soup = BeautifulSoup(content, "html.parser")
            element.replace_with(new_soup)

            logger.debug(f"Updating content with {len(content)} characters")
            logger.debug(f"Content updated from '{old_content}' to '{content[:50]}...'")

            # Save the updated HTML
            self.save_html()

            logger.debug("Fix applied successfully")
            return True
        except Exception as e:
            logger.error(f"Error updating element content: {e}")
            return False

    def replace_element(self, selector: str, new_element: str) -> bool:
        """
        Replace an HTML element with a new one.

        Args:
            selector: CSS selector for the element to replace
            new_element: New HTML element as a string

        Returns:
            True if the replacement was successful, False otherwise
        """
        logger.debug("===== Applying fix =====")
        logger.debug(f"Selector: {selector}")
        logger.debug(f"Replace element: True")

        try:
            element = self.soup.select_one(selector)
            if not element:
                logger.warning(f"Element not found with selector: {selector}")
                return False

            logger.debug(f"Found element with {selector}")

            # Replace the element
            new_soup = BeautifulSoup(new_element, "html.parser")
            new_tag = new_soup.contents[0]
            element.replace_with(new_tag)

            logger.debug(f"Element replaced with {len(new_element)} characters of HTML")

            # Save the updated HTML
            self.save_html()

            logger.debug("Fix applied successfully")
            return True
        except Exception as e:
            logger.error(f"Error replacing element: {e}")
            return False

    def save_html(self, output_path: Optional[str] = None) -> bool:
        """
        Save the updated HTML to file.

        Args:
            output_path: Path to save the HTML file (defaults to original path)

        Returns:
            True if saving was successful, False otherwise
        """
        if not self.soup:
            logger.error("No HTML content to save")
            return False

        output_path = output_path or self.html_path
        logger.debug(f"Saving HTML to original path")

        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            logger.debug(
                f"Creating directory if needed: {os.path.dirname(output_path)}"
            )

            # Save the HTML
            html_output = str(self.soup)
            logger.debug(f"Prepared HTML output: {len(html_output)} characters")

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_output)

            logger.debug(f"HTML successfully saved to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving HTML: {e}")
            return False
