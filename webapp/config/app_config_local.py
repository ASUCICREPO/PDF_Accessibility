# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Configuration management for the Document Accessibility Streamlit application.

This module handles environment variables, AWS configuration, and default settings.
"""

import os
from typing import Dict, Any, Optional

class Config:
    """Configuration class for the Document Accessibility Streamlit application."""
    # AWS configuration keys
    S3_BUCKET_KEY = "BDA_S3_BUCKET"
    S3_BUCKET_ALT_KEY = "DOCUMENT_ACCESSIBILITY_S3_BUCKET"
    BDA_PROJECT_ARN_KEY = "BDA_PROJECT_ARN"
    BDA_PROJECT_ARN_ALT_KEY = "DOCUMENT_ACCESSIBILITY_BDA_PROJECT_ARN"
    AWS_PROFILE_KEY = "AWS_PROFILE"
    WORK_DIR_KEY = "DOCUMENT_ACCESSIBILITY_WORK_DIR"
    def __init__(self):
        """Initialize configuration with values from environment variables."""
        # Load configuration from environment variables
        self._s3_bucket = os.environ.get(self.S3_BUCKET_KEY) or os.environ.get(self.S3_BUCKET_ALT_KEY)
        self._bda_project_arn = os.environ.get(self.BDA_PROJECT_ARN_KEY) or os.environ.get(self.BDA_PROJECT_ARN_ALT_KEY)
        self._aws_profile = os.environ.get(self.AWS_PROFILE_KEY)
        self._work_dir = os.environ.get(self.WORK_DIR_KEY)
        # Set environment variables expected by the BDA client
        if self._s3_bucket and self.S3_BUCKET_KEY not in os.environ:
            os.environ[self.S3_BUCKET_KEY] = self._s3_bucket
        if self._bda_project_arn and self.BDA_PROJECT_ARN_KEY not in os.environ:
            os.environ[self.BDA_PROJECT_ARN_KEY] = self._bda_project_arn
    
    @property
    def s3_bucket(self) -> Optional[str]:
        """Get the S3 bucket name."""
        return self._s3_bucket
    
    @property
    def bda_project_arn(self) -> Optional[str]:
        """Get the BDA project ARN."""
        return self._bda_project_arn
    
    @property
    def aws_profile(self) -> Optional[str]:
        """Get the AWS profile name."""
        return self._aws_profile
    
    @property
    def work_dir(self) -> Optional[str]:
        """Get the working directory path."""
        return self._work_dir
    
    @property
    def aws_configured(self) -> bool:
        """Check if AWS S3 bucket is configured."""
        return self._s3_bucket is not None
    
    def get_conversion_options(self, extract_images: bool, image_format: str, multiple_documents: bool) -> Dict[str, Any]:
        """
        Create conversion options dictionary for the document_accessibility API.
        
        Args:
            extract_images: Whether to extract images from the PDF
            image_format: Format for extracted images (png, jpg)
            multiple_documents: Whether to generate multiple HTML files (one per page)
            
        Returns:
            Dictionary of conversion options
        """
        options = {
            "extract_images": extract_images,
            "image_format": image_format,
            "multi_page": multiple_documents,
            "single_page": not multiple_documents,
        }
        
        # Only add AWS parameters if they're configured
        if self._s3_bucket:
            options["s3_bucket"] = self._s3_bucket
        if self._bda_project_arn:
            options["bda_project_arn"] = self._bda_project_arn
        if self._aws_profile:
            options["profile"] = self._aws_profile
            
        return options
    
    def get_audit_options(self, check_images: bool, check_headings: bool, 
                        check_links: bool, check_tables: bool, severity_threshold: str) -> Dict[str, Any]:
        """
        Create audit options dictionary for the document_accessibility API.
        
        Args:
            check_images: Whether to check image accessibility
            check_headings: Whether to check heading structure
            check_links: Whether to check link accessibility
            check_tables: Whether to check table accessibility
            severity_threshold: Minimum severity level to report (error, warning, info)
            
        Returns:
            Dictionary of audit options
        """
        return {
            "check_images": check_images,
            "check_headings": check_headings,
            "check_links": check_links,
            "check_tables": check_tables,
            "severity_threshold": severity_threshold,
            "include_help": True,
            "include_code": True,
            "include_context": True,
        }
    
    def get_remediation_options(self, fix_images: bool, fix_headings: bool, 
                              fix_links: bool, severity_threshold: str) -> Dict[str, Any]:
        """
        Create remediation options dictionary for the document_accessibility API.
        
        Args:
            fix_images: Whether to fix image accessibility issues
            fix_headings: Whether to fix heading structure issues
            fix_links: Whether to fix link accessibility issues
            severity_threshold: Minimum severity level to fix (error, warning, info)
            
        Returns:
            Dictionary of remediation options
        """
        return {
            "fix_images": fix_images,
            "fix_headings": fix_headings,
            "fix_links": fix_links,
            "severity_threshold": severity_threshold,
            "backup": True,
            "format": "json",
        }

# Create a singleton instance
config = Config()
