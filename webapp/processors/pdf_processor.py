# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
PDF processing functionality for the Document Accessibility Streamlit application.
"""

import logging
import streamlit as st
from typing import Dict, Any, Optional, Tuple

from content_accessibility_utility_on_aws.api import process_pdf_accessibility

from utils.aws_utils import display_aws_warning, display_html_upload_notice
from config.app_config_local import Config

# Set up logger
logger = logging.getLogger(__name__)

def process_pdf_file(pdf_path: str, temp_dir: str, config: Config, options: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Process a PDF document using the document_accessibility API.
    
    Args:
        pdf_path: Path to the PDF file
        temp_dir: Temporary directory for processing files
        config: Application configuration
        options: Processing options
    
    Returns:
        Tuple containing:
        - Boolean indicating processing success/failure
        - Dictionary of results if successful, None otherwise
    """
    # Check if AWS S3 bucket is configured
    if not config.aws_configured:
        display_aws_warning()
        display_html_upload_notice()
        return False, None
    
    # Extract options
    perform_audit = options.get("perform_audit", True)
    perform_remediation = options.get("perform_remediation", True)
    
    # Get PDF to HTML conversion options
    conversion_options = config.get_conversion_options(
        extract_images=options.get("extract_images", True),
        image_format=options.get("image_format", "png"),
        multiple_documents=options.get("multiple_documents", False)
    )
    
    # Get audit options if needed
    audit_options = None
    if perform_audit:
        audit_options = config.get_audit_options(
            check_images=options.get("check_images", True),
            check_headings=options.get("check_headings", True),
            check_links=options.get("check_links", True),
            check_tables=options.get("check_tables", True),
            severity_threshold=options.get("severity_threshold", "warning")
        )
    
    # Get remediation options if needed
    remediation_options = None
    if perform_remediation:
        remediation_options = config.get_remediation_options(
            fix_images=options.get("fix_images", True) if "fix_images" in options else True,
            fix_headings=options.get("fix_headings", True) if "fix_headings" in options else True,
            fix_links=options.get("fix_links", True) if "fix_links" in options else True,
            severity_threshold=options.get("severity_threshold", "warning")
        )
    
    # Process the PDF
    with st.spinner("Processing PDF document..."):
        try:
            results = process_pdf_accessibility(
                pdf_path=pdf_path,
                output_dir=temp_dir,
                conversion_options=conversion_options,
                audit_options=audit_options,
                remediation_options=remediation_options,
                perform_audit=perform_audit,
                perform_remediation=perform_remediation,
                usage_data_bucket=None,  # Default to local file storage
            )
            
            st.success("PDF processed successfully!")
            return True, results
        except Exception as e:
            if "S3 bucket not configured" in str(e):
                st.error("⛔ PDF processing failed: AWS S3 bucket not configured")
                display_html_upload_notice()
            else:
                st.error(f"Error processing PDF document: {str(e)}")
                logger.exception("Error processing PDF document: %s", pdf_path)
            
            return False, None
