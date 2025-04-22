# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
AWS utilities for the Document Accessibility Streamlit application.
"""

import streamlit as st
from typing import Optional

def check_aws_configuration(s3_bucket: Optional[str]) -> bool:
    """
    Check if AWS S3 bucket is configured.
    
    Args:
        s3_bucket: S3 bucket name
        
    Returns:
        True if configured, False otherwise
    """
    return s3_bucket is not None

def display_aws_warning() -> None:
    """Display a warning about missing AWS configuration."""
    st.warning(
        """
        ⚠️ AWS S3 bucket is not configured. PDF to HTML conversion requires an S3 bucket.
        
        Please set the following environment variables:
        - DOCUMENT_ACCESSIBILITY_S3_BUCKET: Your S3 bucket name
        - DOCUMENT_ACCESSIBILITY_BDA_PROJECT_ARN: Your BDA project ARN (optional)
        
        Without these, PDF processing will fail. Consider uploading HTML files directly if AWS resources aren't available.
        """
    )
    
    # Add a second notice that will appear in the main content area
    st.error(
        """
        ## AWS Resources Required
        
        The PDF to HTML conversion feature requires AWS resources:
        
        1. **S3 Bucket**: Required for temporary storage during conversion
        2. **BDA Project ARN**: Optional for improved PDF structure recognition
        
        Please configure these resources using environment variables or upload HTML files directly.
        """
    )

def display_html_upload_notice() -> None:
    """Display a notice about uploading HTML files directly."""
    st.info(
        """
        ### HTML and ZIP files do not require AWS resources
        
        Try uploading an HTML file directly if you have one available, or use the command line tool with 
        AWS credentials configured.
        
        To configure AWS resources:
        ```bash
        export DOCUMENT_ACCESSIBILITY_S3_BUCKET=your-bucket-name
        export DOCUMENT_ACCESSIBILITY_BDA_PROJECT_ARN=your-project-arn # optional
        ```
        """
    )
