# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0


"""
PDF utility functions.
"""

from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger
from pypdf import PdfReader

# Set up module-level logger
logger = setup_logger(__name__)

def is_image_only_pdf(pdf_path: str) -> bool:
    """
    Check if a PDF is image-only (scanned) or contains actual text.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        bool: True if the PDF is likely image-only, False otherwise
    """
    try:
        logger.debug(f"Checking if PDF is image-only: {pdf_path}")
        
        with open(pdf_path, 'rb') as file:
            reader = PdfReader(file)
            
            # Check each page for text content
            for page in reader.pages:
                text = page.extract_text().strip()
                if text:  # If any page has text, it's not image-only
                    return False
                    
            # If we get here, no text was found in any page
            return True
            
    except Exception as e:
        logger.warning(f"Error checking if PDF is image-only: {e}")
        return False
