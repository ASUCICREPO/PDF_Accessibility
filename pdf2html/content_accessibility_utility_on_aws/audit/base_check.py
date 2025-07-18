# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Base classes for accessibility checks.

This module provides the foundation for all accessibility checks in the system.
"""

import logging
from typing import Callable, Optional, List
from bs4 import BeautifulSoup, Tag

# Set up module-level logger
logger = logging.getLogger(__name__)


class AccessibilityError(Exception):
    """Base class for accessibility-related errors."""



def safe_check(check_func):
    """
    Decorator for safely running accessibility checks.

    Catches exceptions and logs them without crashing the entire audit process.
    """

    def wrapper(*args, **kwargs):
        try:
            return check_func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {check_func.__name__}: {str(e)}")
            return None

    return wrapper


class AccessibilityCheck:
    """
    Base class for all accessibility checks.

    This class defines the interface that all specific checks must implement.
    """

    def __init__(self, soup: BeautifulSoup, add_issue_callback: Callable):
        """
        Initialize the accessibility check.

        Args:
            soup: BeautifulSoup object of the HTML document
            add_issue_callback: Function to call to add an issue
        """
        self.soup = soup
        self.add_issue = add_issue_callback

    @safe_check
    def check(self) -> None:
        """
        Perform the accessibility check.

        This method must be implemented by all subclasses.
        """
        raise NotImplementedError("Subclasses must implement check()")

    def find_elements(self, selector: str) -> List[Tag]:
        """
        Find elements matching the given CSS selector.

        Args:
            selector: CSS selector to match elements

        Returns:
            List of matching elements
        """
        try:
            return self.soup.select(selector)
        except Exception as e:
            logger.error(f"Error finding elements with selector '{selector}': {str(e)}")
            return []

    def element_exists(self, selector: str) -> bool:
        """
        Check if at least one element matches the given CSS selector.

        Args:
            selector: CSS selector to match elements

        Returns:
            True if at least one element matches, False otherwise
        """
        return len(self.find_elements(selector)) > 0

    def get_element_text(self, element: Tag) -> str:
        """
        Get the text content of an element.

        Args:
            element: BeautifulSoup Tag object

        Returns:
            Text content of the element
        """
        try:
            return element.get_text(strip=True)
        except Exception:
            return ""

    def get_attribute(self, element: Tag, attribute: str) -> Optional[str]:
        """
        Get the value of an attribute on an element.

        Args:
            element: BeautifulSoup Tag object
            attribute: Name of the attribute

        Returns:
            Value of the attribute, or None if not present
        """
        try:
            return element.get(attribute)
        except Exception:
            return None
