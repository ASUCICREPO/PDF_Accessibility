# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0


"""
BDA Integration module.

This module provides components for integrating Bedrock Data Automation (BDA) results
into the accessibility remediation workflow.
"""

__version__ = "0.1.0"

from .element_parser import BDAElementParser
from .element_index import ElementIndex
from .remediation_manager import RemediationManager

__all__ = ["BDAElementParser", "ElementIndex", "RemediationManager"]
