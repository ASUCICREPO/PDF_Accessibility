# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
ZIP archive processing functionality for the Document Accessibility Streamlit application.
"""

import os
import logging
import streamlit as st
from typing import Dict, Any, Optional, Tuple

from content_accessibility_with_aws.api import audit_html_accessibility, remediate_html_accessibility, generate_remediation_report

from utils.file_utils import extract_zip_file
from config.app_config_local import Config

# Set up logger
logger = logging.getLogger(__name__)

def process_zip_file(zip_path: str, temp_dir: str, config: Config, options: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Process a ZIP archive containing HTML files using the document_accessibility API.
    
    Args:
        zip_path: Path to the ZIP file
        temp_dir: Temporary directory for processing files
        config: Application configuration
        options: Processing options
    
    Returns:
        Tuple containing:
        - Boolean indicating processing success/failure
        - Dictionary of results if successful, None otherwise
    """
    # Extract options
    options.get("perform_audit", True)
    perform_remediation = options.get("perform_remediation", True)
    
    # Extract the ZIP file
    extract_dir = os.path.join(temp_dir, "extracted_zip")
    os.makedirs(extract_dir, exist_ok=True)
    
    with st.spinner("Extracting ZIP archive..."):
        try:
            html_files = extract_zip_file(zip_path, extract_dir)
            
            if not html_files:
                st.error("No HTML files found in the ZIP archive.")
                return False, None
        except Exception as e:
            st.error(f"Error extracting ZIP archive: {str(e)}")
            logger.exception("Error extracting ZIP archive: %s", zip_path)
            return False, None
    
    # Process each HTML file
    with st.spinner(f"Processing {len(html_files)} HTML files from ZIP archive..."):
        audit_results = []
        remediation_results = []
        
        for i, html_file in enumerate(html_files):
            # Update progress
            progress_text = f"Processing file {i+1} of {len(html_files)}: {os.path.basename(html_file)}"
            st.text(progress_text)
            
            try:
                # Step 1: Perform audit
                audit_options = config.get_audit_options(
                    check_images=options.get("check_images", True),
                    check_headings=options.get("check_headings", True),
                    check_links=options.get("check_links", True),
                    check_tables=options.get("check_tables", True),
                    severity_threshold=options.get("severity_threshold", "warning")
                )
                
                audit_result = audit_html_accessibility(
                    html_path=html_file,
                    options=audit_options,
                    output_path=os.path.join(temp_dir, f"accessibility_audit_{i}.json"),
                )
                audit_results.append(audit_result)
                
                # Step 2: Perform remediation if requested
                if perform_remediation:
                    remediation_options = config.get_remediation_options(
                        fix_images=options.get("fix_images", True) if "fix_images" in options else True,
                        fix_headings=options.get("fix_headings", True) if "fix_headings" in options else True,
                        fix_links=options.get("fix_links", True) if "fix_links" in options else True,
                        severity_threshold=options.get("severity_threshold", "warning")
                    )
                    
                    # Create subdirectory for remediated files
                    remediated_dir = os.path.join(temp_dir, "remediated_html")
                    os.makedirs(remediated_dir, exist_ok=True)
                    
                    # Determine relative path to maintain directory structure
                    rel_path = os.path.relpath(html_file, extract_dir)
                    output_dir = os.path.dirname(os.path.join(remediated_dir, rel_path))
                    os.makedirs(output_dir, exist_ok=True)
                    
                    remediation_result = remediate_html_accessibility(
                        html_path=html_file,
                        audit_report=audit_result,
                        options=remediation_options,
                        output_path=os.path.join(remediated_dir, rel_path),
                    )
                    remediation_results.append(remediation_result)
            except Exception as e:
                st.warning(f"Error processing {os.path.basename(html_file)}: {str(e)}")
                logger.warning("Error processing HTML file: %s", html_file)
                continue
    
    # Combine results
    combined_issues = []
    combined_fixed_issues = []
    combined_remaining_issues = []
    
    for audit_result in audit_results:
        combined_issues.extend(audit_result.get("issues", []))
    
    for remediation_result in remediation_results:
        combined_fixed_issues.extend(remediation_result.get("fixed_issues", []))
        combined_remaining_issues.extend(remediation_result.get("remaining_issues", []))
    
    # Create combined audit result
    combined_audit_result = {
        "issues": combined_issues,
        "summary": {
            "total_issues": len(combined_issues),
            "error_count": sum(1 for issue in combined_issues if issue.get("severity") == "error"),
            "warning_count": sum(1 for issue in combined_issues if issue.get("severity") == "warning"),
            "info_count": sum(1 for issue in combined_issues if issue.get("severity") == "info"),
            "compliant": sum(1 for issue in combined_issues if issue.get("remediation_status") == "compliant"),
            "needs_remediation": sum(1 for issue in combined_issues if issue.get("remediation_status") == "needs_remediation"),
        },
    }
    
    # Create combined remediation result
    remediated_html_dir = os.path.join(temp_dir, "remediated_html")
    combined_remediation_result = {
        "fixed_issues": combined_fixed_issues,
        "remaining_issues": combined_remaining_issues,
        "output_path": remediated_html_dir,
        "remediated_html_path": remediated_html_dir,
    }
    
    # Store in results
    results = {
        "audit_result": combined_audit_result
    }
    
    if perform_remediation:
        results["remediation_result"] = combined_remediation_result
        
        # Generate remediation report
        with st.spinner("Generating remediation report..."):
            try:
                remediation_report_path = os.path.join(temp_dir, "remediation_report.html")
                generate_remediation_report(
                    remediation_data=combined_remediation_result,
                    output_path=remediation_report_path,
                    report_format="html",
                )
                results["remediation_report_path"] = remediation_report_path
                
                # Also generate JSON report for data analysis
                json_report_path = os.path.join(temp_dir, "remediation_report.json")
                generate_remediation_report(
                    remediation_data=combined_remediation_result,
                    output_path=json_report_path,
                    report_format="json",
                )
            except Exception as e:
                st.warning(f"Error generating remediation report: {str(e)}")
                logger.warning("Error generating remediation report: %s", str(e))
    
    st.success(f"Processed {len(html_files)} HTML files from ZIP archive!")
    return True, results
