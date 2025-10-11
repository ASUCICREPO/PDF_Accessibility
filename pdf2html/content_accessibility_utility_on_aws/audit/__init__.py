# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Accessibility audit module for HTML documents.

This module provides functionality for auditing HTML documents for accessibility issues
against WCAG 2.1 accessibility standards.
"""

from content_accessibility_utility_on_aws.audit.auditor import AccessibilityAuditor
from content_accessibility_utility_on_aws.audit.report_generator import generate_report

__all__ = ["AccessibilityAuditor", "generate_report"]
