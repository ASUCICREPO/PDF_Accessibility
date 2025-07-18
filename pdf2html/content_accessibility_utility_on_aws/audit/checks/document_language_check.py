# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Document language check.

This module provides a standalone check for document language.
"""

from content_accessibility_utility_on_aws.audit.base_check import AccessibilityCheck
from ...utils.logging_helper import setup_logger


# Set up module-level logger
logger = setup_logger(__name__)


class DocumentLanguageCheck(AccessibilityCheck):
    """Check for document language specification (WCAG 3.1.1)."""

    def check(self) -> None:
        """
        Check if the document has a language attribute on the html element.

        Issues:
            - missing-document-language: When the html element has no lang attribute
            - invalid-document-language: When the lang attribute has an invalid value
            - compliant-document-language: When the document has a valid language attribute
        """
        logger.debug("Running DocumentLanguageCheck")
        html_tag = self.soup.find("html")

        if not html_tag:
            logger.debug("No HTML tag found")
            return

        if not html_tag.has_attr("lang"):
            logger.debug("HTML tag missing lang attribute")
            self.add_issue(
                "missing-document-language",
                "3.1.1",
                "critical",
                element=html_tag,
                description="Document missing language attribute on HTML element",
                status="needs_remediation",
            )
            return

        # Check for valid language code
        lang = html_tag["lang"].strip()
        if not lang or len(lang) < 2:
            logger.debug("HTML tag has invalid lang attribute: '%s'", lang)
            self.add_issue(
                "invalid-document-language",
                "3.1.1",
                "major",
                element=html_tag,
                description=f"Document has invalid language code: '{lang}'",
                status="needs_remediation",
            )
        else:
            # Document has a valid language attribute
            logger.debug(
                "HTML tag has valid lang attribute: '%s', adding compliant issue", lang
            )
            self.add_issue(
                "compliant-document-language",
                "3.1.1",
                "critical",
                element=html_tag,
                description=f"Document has valid language attribute: '{lang}'",
                status="compliant",
            )
            logger.debug("Added compliant issue for document language")
