# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Document structure accessibility checks.

This module provides checks for proper document structure and landmarks.
"""

from content_accessibility_utility_on_aws.audit.base_check import AccessibilityCheck


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
        html_tag = self.soup.find("html")

        if not html_tag:
            return

        if not html_tag.has_attr("lang"):
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
            self.add_issue(
                "compliant-document-language",
                "3.1.1",
                "critical",
                element=html_tag,
                description=f"Document has valid language attribute: '{lang}'",
                status="compliant",
            )


class MainLandmarkCheck(AccessibilityCheck):
    """Check for main landmark (WCAG 1.3.1, 2.4.1)."""

    def check(self) -> None:
        """
        Check if the document has a main landmark.

        Issues:
            - missing-main-landmark: When there is no main element or role="main"
            - compliant-main-landmark: When there is a main element or role="main"
        """
        main_element = self.soup.find("main")
        main_role = self.soup.find(attrs={"role": "main"})

        if not main_element and not main_role:
            self.add_issue(
                "missing-main-landmark",
                "1.3.1",
                "major",
                element=self.soup.find("body"),
                description="Document missing main landmark (main element or role='main')",
                status="needs_remediation",
            )
        else:
            # Document has a main landmark - mark as compliant
            element = main_element if main_element else main_role
            self.add_issue(
                "compliant-main-landmark",
                "1.3.1",
                "major",
                element=element,
                description="Document has proper main landmark",
                status="compliant",
            )


class SkipLinkCheck(AccessibilityCheck):
    """Check for skip navigation link (WCAG 2.4.1)."""

    def check(self) -> None:
        """
        Check if the document has a skip navigation link.

        Issues:
            - missing-skip-link: When there is no skip navigation link
            - compliant-skip-link: When there is a skip navigation link
        """
        # Look for the first few links in the document
        links = self.soup.find_all("a", limit=5)
        has_skip_link = False
        skip_link = None

        for link in links:
            href = link.get("href", "")
            text = self.get_element_text(link).lower()

            if href.startswith("#") and (
                "skip" in text or "jump" in text or "content" in text or "main" in text
            ):
                has_skip_link = True
                skip_link = link
                break

        if not has_skip_link:
            self.add_issue(
                "missing-skip-link",
                "2.4.1",
                "major",
                element=self.soup.find("body"),
                description="Document missing skip navigation link",
                status="needs_remediation",
            )
        else:
            # Document has a skip link - mark as compliant
            self.add_issue(
                "compliant-skip-link",
                "2.4.1",
                "major",
                element=skip_link,
                description="Document has proper skip navigation link",
                status="compliant",
            )


class LandmarksCheck(AccessibilityCheck):
    """Check for proper landmarks (WCAG 1.3.1, 2.4.1)."""

    def check(self) -> None:
        """
        Check if the document has proper landmarks for navigation.

        Issues:
            - missing-navigation-landmark: When there is no nav element or role="navigation"
            - missing-header-landmark: When there is no header element or role="banner"
            - missing-footer-landmark: When there is no footer element or role="contentinfo"
            - compliant-navigation-landmark: When there is a nav element or role="navigation"
            - compliant-header-landmark: When there is a header element or role="banner"
            - compliant-footer-landmark: When there is a footer element or role="contentinfo"
        """
        # Check for navigation landmark
        nav_element = self.soup.find("nav")
        nav_role = self.soup.find(attrs={"role": "navigation"})

        if not nav_element and not nav_role:
            self.add_issue(
                "missing-navigation-landmark",
                "1.3.1",
                "minor",
                element=self.soup.find("body"),
                description="Document missing navigation landmark "
                + "(nav element or role='navigation')",
                status="needs_remediation",
            )
        else:
            # Document has a navigation landmark - mark as compliant
            element = nav_element if nav_element else nav_role
            self.add_issue(
                "compliant-navigation-landmark",
                "1.3.1",
                "minor",
                element=element,
                description="Document has proper navigation landmark",
                status="compliant",
            )

        # Check for header landmark
        header_element = self.soup.find("header")
        banner_role = self.soup.find(attrs={"role": "banner"})

        if not header_element and not banner_role:
            self.add_issue(
                "missing-header-landmark",
                "1.3.1",
                "minor",
                element=self.soup.find("body"),
                description="Document missing header landmark (header element or role='banner')",
                status="needs_remediation",
            )
        else:
            # Document has a header landmark - mark as compliant
            element = header_element if header_element else banner_role
            self.add_issue(
                "compliant-header-landmark",
                "1.3.1",
                "minor",
                element=element,
                description="Document has proper header landmark",
                status="compliant",
            )

        # Check for footer landmark
        footer_element = self.soup.find("footer")
        contentinfo_role = self.soup.find(attrs={"role": "contentinfo"})

        if not footer_element and not contentinfo_role:
            self.add_issue(
                "missing-footer-landmark",
                "1.3.1",
                "minor",
                element=self.soup.find("body"),
                description="Document missing footer landmark "
                + "(footer element or role='contentinfo')",
                status="needs_remediation",
            )
        else:
            # Document has a footer landmark - mark as compliant
            element = footer_element if footer_element else contentinfo_role
            self.add_issue(
                "compliant-footer-landmark",
                "1.3.1",
                "minor",
                element=element,
                description="Document has proper footer landmark",
                status="compliant",
            )
