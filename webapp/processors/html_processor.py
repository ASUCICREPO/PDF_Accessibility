# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
HTML processing functionality for the Document Accessibility Streamlit application.
"""

import os
import logging
import streamlit as st
from typing import Dict, Any, Optional, Tuple

from content_accessibility_utility_on_aws.api import audit_html_accessibility, remediate_html_accessibility, generate_remediation_report

from config.app_config_local import Config

# Set up logger
logger = logging.getLogger(__name__)

def process_html_file(html_path: str, temp_dir: str, config: Config, options: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Process an HTML document using the document_accessibility API.
    
    Args:
        html_path: Path to the HTML file
        temp_dir: Temporary directory for processing files
        config: Application configuration
        options: Processing options
    
    Returns:
        Tuple containing:
        - Boolean indicating processing success/failure
        - Dictionary of results if successful, None otherwise
    """
    # Extract options
    perform_remediation = options.get("perform_remediation", True)
    
    # Initialize results dictionary
    results = {}
    
    try:
        # Step 1: Perform audit
        with st.spinner("Auditing HTML document..."):
            audit_options = config.get_audit_options(
                check_images=options.get("check_images", True),
                check_headings=options.get("check_headings", True),
                check_links=options.get("check_links", True),
                check_tables=options.get("check_tables", True),
                severity_threshold=options.get("severity_threshold", "warning")
            )
            
            audit_result = audit_html_accessibility(
                html_path=html_path,
                options=audit_options,
                output_path=os.path.join(temp_dir, "accessibility_audit.json"),
            )
            results["audit_result"] = audit_result
        
        # Step 2: Perform remediation if requested
        if perform_remediation:
            with st.spinner("Remediating HTML accessibility issues..."):
                remediation_options = config.get_remediation_options(
                    fix_images=options.get("fix_images", True) if "fix_images" in options else True,
                    fix_headings=options.get("fix_headings", True) if "fix_headings" in options else True,
                    fix_links=options.get("fix_links", True) if "fix_links" in options else True,
                    severity_threshold=options.get("severity_threshold", "warning")
                )
                
                remediation_result = remediate_html_accessibility(
                    html_path=html_path,
                    audit_report=audit_result,
                    options=remediation_options,
                    output_path=os.path.join(temp_dir, "remediated_document.html"),
                )
                results["remediation_result"] = remediation_result
                
                # Generate remediation report
                remediation_report_path = os.path.join(temp_dir, "remediation_report.html")
                with st.spinner("Generating remediation report..."):
                    generate_remediation_report(
                        remediation_data=remediation_result,
                        output_path=remediation_report_path,
                        report_format="html",
                    )
                results["remediation_report_path"] = remediation_report_path
                
                # Also generate JSON report for data analysis
                json_report_path = os.path.join(temp_dir, "remediation_report.json")
                generate_remediation_report(
                    remediation_data=remediation_result,
                    output_path=json_report_path,
                    report_format="json",
                )
        
        st.success("HTML processed successfully!")
        return True, results
    
    except Exception as e:
        st.error(f"Error processing HTML document: {str(e)}")
        logger.exception("Error processing HTML document: %s", html_path)
        return False, None
