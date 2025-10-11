# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0


"""
Heading structure accessibility checks.

This module provides checks for proper heading structure and content.
"""

from content_accessibility_utility_on_aws.audit.base_check import AccessibilityCheck


class HeadingHierarchyCheck(AccessibilityCheck):
    """Check for proper heading hierarchy (WCAG 1.3.1, 2.4.10)."""

    def check(self) -> None:
        """
        Check if the document has proper heading hierarchy.

        Issues:
            - skipped-heading-level: When heading levels are skipped (e.g., h1 to h3)
            - no-h1: When the document has no h1 element
            - compliant-heading-hierarchy: When the document has proper heading hierarchy
        """
        headings = []
        for i in range(1, 7):
            for h in self.soup.find_all(f"h{i}"):
                headings.append((i, h))

        if not headings:
            self.add_issue(
                "no-headings",
                "1.3.1",
                "major",
                element=self.soup.find("body"),
                description="Document has no heading elements",
                status="needs_remediation",
            )
            return

        # Check for h1
        has_h1 = any(level == 1 for level, _ in headings)
        if not has_h1:
            self.add_issue(
                "no-h1",
                "1.3.1",
                "major",
                element=self.soup.find("body"),
                description="Document has no main heading (h1)",
                status="needs_remediation",
            )

        # Check for skipped heading levels
        prev_level = 0
        has_skipped_levels = False

        for level, heading in headings:
            if prev_level > 0 and level > prev_level + 1:
                has_skipped_levels = True
                self.add_issue(
                    "skipped-heading-level",
                    "1.3.1",
                    "major",
                    element=heading,
                    description=f"Heading level skipped from H{prev_level} to H{level}",
                    status="needs_remediation",
                )
            prev_level = level

        # If we have headings, h1, and no skipped levels, mark as compliant
        if has_h1 and not has_skipped_levels:
            self.add_issue(
                "compliant-heading-hierarchy",
                "1.3.1",
                "major",
                element=headings[0][1],  # Use the first heading
                description="Document has proper heading hierarchy",
                status="compliant",
            )


class HeadingContentCheck(AccessibilityCheck):
    """Check for proper heading content (WCAG 2.4.6)."""

    def check(self) -> None:
        """
        Check if headings have proper content.

        Issues:
            - empty-heading: When a heading has no text content
            - generic-heading: When a heading has generic text like "Heading"
            - compliant-heading-content: When headings have proper content
        """
        headings = []
        for i in range(1, 7):
            for h in self.soup.find_all(f"h{i}"):
                headings.append(h)

        if not headings:
            return  # No headings to check

        has_issues = False

        for heading in headings:
            text = self.get_element_text(heading)

            if not text:
                has_issues = True
                self.add_issue(
                    "empty-heading",
                    "2.4.6",
                    "major",
                    element=heading,
                    description="Heading has no text content",
                    status="needs_remediation",
                )
            elif text.lower() in ["heading", "title", "subtitle", "header"]:
                has_issues = True
                self.add_issue(
                    "generic-heading",
                    "2.4.6",
                    "minor",
                    element=heading,
                    description=f"Heading has generic text: '{text}'",
                    status="needs_remediation",
                )

        # If we have headings and no issues, mark as compliant
        if not has_issues:
            self.add_issue(
                "compliant-heading-content",
                "2.4.6",
                "major",
                element=headings[0],  # Use the first heading
                description="Document has proper heading content",
                status="compliant",
            )


class DocumentTitleCheck(AccessibilityCheck):
    """Check for document title (WCAG 2.4.2)."""

    def check(self) -> None:
        """
        Check if the document has a proper title.

        Issues:
            - missing-title: When the document has no title element
            - empty-title: When the title element has no text content
            - generic-title: When the title has generic text like "Untitled"
            - compliant-document-title: When the document has a proper title
        """
        title = self.soup.find("title")

        if not title:
            self.add_issue(
                "missing-title",
                "2.4.2",
                "major",
                element=self.soup.find("head"),
                description="Document missing title element",
                status="needs_remediation",
            )
            return

        title_text = self.get_element_text(title)

        if not title_text:
            self.add_issue(
                "empty-title",
                "2.4.2",
                "major",
                element=title,
                description="Document has empty title element",
                status="needs_remediation",
            )
        elif title_text.lower() in [
            "untitled",
            "document",
            "page",
            "new page",
            "title",
        ]:
            self.add_issue(
                "generic-title",
                "2.4.2",
                "minor",
                element=title,
                description=f"Document has generic title: '{title_text}'",
                status="needs_remediation",
            )
        else:
            # Document has a proper title - mark as compliant
            self.add_issue(
                "compliant-document-title",
                "2.4.2",
                "major",
                element=title,
                description="Document has proper title",
                status="compliant",
            )
