# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0



"""
Accessibility checks package.

This package contains all the specific accessibility checks that can be performed.
"""

from content_accessibility_utility_on_aws.audit.checks.heading_checks import (
    HeadingHierarchyCheck,
    HeadingContentCheck,
    DocumentTitleCheck,
)
from content_accessibility_utility_on_aws.audit.checks.structure_checks import (
    MainLandmarkCheck,
    SkipLinkCheck,
    LandmarksCheck,
)
from content_accessibility_utility_on_aws.audit.checks.document_language_check import (
    DocumentLanguageCheck,
)
from content_accessibility_utility_on_aws.audit.checks.image_checks import (
    AltTextCheck,
    FigureStructureCheck,
)
from content_accessibility_utility_on_aws.audit.checks.link_checks import (
    LinkTextCheck,
    NewWindowLinkCheck,
)
from content_accessibility_utility_on_aws.audit.checks.table_checks import (
    TableHeaderCheck,
    TableStructureCheck,
)
from content_accessibility_utility_on_aws.audit.checks.color_contrast_checks import ColorContrastCheck
from content_accessibility_utility_on_aws.audit.checks.form_checks import (
    FormLabelCheck,
    FormRequiredFieldCheck,
    FormFieldsetCheck,
)

__all__ = [
    "HeadingHierarchyCheck",
    "HeadingContentCheck",
    "DocumentTitleCheck",
    "DocumentLanguageCheck",
    "MainLandmarkCheck",
    "SkipLinkCheck",
    "LandmarksCheck",
    "AltTextCheck",
    "FigureStructureCheck",
    "LinkTextCheck",
    "NewWindowLinkCheck",
    "TableHeaderCheck",
    "TableStructureCheck",
    "ColorContrastCheck",
    "FormLabelCheck",
    "FormRequiredFieldCheck",
    "FormFieldsetCheck",
]
