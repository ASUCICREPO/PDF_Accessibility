# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Error handling utilities for the document_accessibility package.

This module provides standardized error handling mechanisms, including custom
exceptions and error logging utilities to ensure consistent error handling
across all modules.
"""

import logging
import sys
from typing import Optional, Type, Dict, Any


class DocumentAccessibilityError(Exception):
    """Base exception class for all document_accessibility errors."""



class PDFConversionError(DocumentAccessibilityError):
    """Raised when there's an error converting a PDF document to HTML."""



class AccessibilityAuditError(DocumentAccessibilityError):
    """Raised when there's an error during accessibility auditing."""



class AccessibilityRemediationError(DocumentAccessibilityError):
    """Raised when there's an error during accessibility remediation."""



class ConfigurationError(DocumentAccessibilityError):
    """Raised when there's an error in configuration."""



class ResourceError(DocumentAccessibilityError):
    """Raised when there's an error managing resources."""



class AIRemediationRequiredError(DocumentAccessibilityError):
    """Raised when AI remediation is required but not available."""



# Configure module-level logger
logger = logging.getLogger(__name__)


def setup_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    Set up a logger with standardized formatting.

    Args:
        name: The logger name, typically __name__ of the calling module
        level: The logging level (default: INFO if not in debug mode)

    Returns:
        A configured logger instance
    """
    logger_obj = logging.getLogger(name)

    # Set default level if none provided
    if level is None:
        # Check if root logger is in debug mode (set by --debug flag)
        if logging.getLogger().level <= logging.DEBUG:
            level = logging.DEBUG
        else:
            level = logging.INFO
        
        # Use logging instead of print
        logger.debug(f"Setting logger {name} level to {logging.getLevelName(level)}")

    # Always set the level explicitly to override inheritance
    if level is not None:
        logger_obj.setLevel(level)

    # Ensure propagation is enabled
    logger_obj.propagate = True

    # Create handler if no handlers exist
    if not logger_obj.handlers:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Create handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        logger_obj.addHandler(handler)

    return logger_obj


def log_exception(
    logger: logging.Logger,
    exception: Exception,
    message: str = "An error occurred",
    level: int = logging.ERROR,
    include_traceback: bool = True,
) -> None:
    """
    Log an exception with consistent formatting.

    Args:
        logger: The logger instance to use
        exception: The exception to log
        message: Optional custom message
        level: The logging level to use
        include_traceback: Whether to include the full traceback
    """
    error_type = type(exception).__name__
    error_message = str(exception)

    log_msg = f"{message}: {error_type} - {error_message}"

    if include_traceback:
        logger.log(level, log_msg, exc_info=True)
    else:
        logger.log(level, log_msg)


def handle_exception(
    exc: Exception,
    logger: logging.Logger,
    custom_message: str = None,
    reraise: bool = True,
    custom_exception: Type[Exception] = None,
    additional_data: Dict[str, Any] = None,
) -> Optional[Dict[str, Any]]:
    """
    Standardized exception handling.

    Args:
        exc: The caught exception
        logger: Logger to use for recording the error
        custom_message: Optional message to include
        reraise: Whether to reraise the exception (possibly wrapped)
        custom_exception: Exception type to raise instead of original
        additional_data: Additional context data to include

    Returns:
        If reraise is False, returns error information as a dict

    Raises:
        The original exception or a wrapped custom exception if reraise is True
    """
    # Use the exception's message if no custom message is provided
    message = custom_message if custom_message else str(exc)

    # Log the exception
    log_exception(logger, exc, message)

    # Prepare error information
    error_info = {
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "original_exception": exc,
    }

    # Add additional data if provided
    if additional_data:
        error_info.update(additional_data)

    # Reraise as appropriate
    if reraise:
        if custom_exception:
            # Wrap the original exception with the custom one
            raise custom_exception(message) from exc

    # Return error info if not reraising
    return error_info
