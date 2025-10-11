# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Path handling fixes for environment-specific path issues.

This module provides functions to handle path discrepancies between
different environments and mounted filesystems.
"""

import os
import logging
from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger

# Set up module-level logger
logger = setup_logger(__name__, level=logging.DEBUG)


def normalize_path(path):
    """
    Normalize a path to handle symlinks, mount points, and environment-specific issues.

    This function handles cases where paths might be referenced with different prefixes
    (like /local/home/... vs /home/...) due to symlinks or mount points.

    Args:
        path: The path to normalize

    Returns:
        The normalized path
    """
    if path is None:
        logger.debug(f"normalize_path: Received None path")
        return None

    # First apply standard normalization
    normalized = os.path.normpath(os.path.realpath(path))

    return normalized
