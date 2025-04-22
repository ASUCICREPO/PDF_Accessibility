# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Report view for the Document Accessibility Streamlit application.
"""

import os
import json
import streamlit as st
from typing import Dict, Any, Optional

from ui_helpers.charts import display_remediation_stats, display_severity_breakdown, display_issues_by_type
from ui_helpers.download_helpers import create_download_section_for_reports
from views.audit_view import display_issues_with_filters

def display_report_view(remediation_result: Optional[Dict[str, Any]] = None, temp_dir: Optional[str] = None) -> None:
    """
    Display remediation report with statistics and issue details.
    
    Args:
        remediation_result: Dictionary containing remediation results
        temp_dir: Temporary directory containing report files
    """
    st.header("Remediation Report")
    
    if not remediation_result and not temp_dir:
        st.info("No remediation report is available.")
        return
    
    # Try to load report data from JSON file if remediation_result is not provided
    report_data = remediation_result
    
    if not report_data and temp_dir:
        json_report_path = os.path.join(temp_dir, "remediation_report.json")
        
        if os.path.exists(json_report_path):
            try:
                with open(json_report_path, "r", encoding="utf-8") as f:
                    report_data = json.load(f)
            except Exception as e:
                st.error(f"Error loading remediation report: {str(e)}")
                report_data = None
    
    if not report_data:
        st.warning("No remediation data available for report.")
        return
    
    # Extract data from report
    summary = report_data.get("summary", {})
    issues = report_data.get("issues", [])
    if not issues:
        # Try alternative fields
        fixed_issues = report_data.get("fixed_issues", [])
        remaining_issues = report_data.get("remaining_issues", [])
        issues = fixed_issues + remaining_issues
    
    # Display statistics
    st.subheader("Remediation Statistics")
    display_remediation_stats(summary)
    
    # Display severity breakdown
    display_severity_breakdown(issues, summary)
    
    # Display issues by type chart
    display_issues_by_type(issues, summary)
    
    # Display detailed issue breakdown
    st.subheader("Detailed Issue Breakdown")
    if issues:
        display_issues_with_filters(issues)
    else:
        st.info("No issues available to display.")
    
    # Add download buttons for the reports
    if temp_dir:
        st.divider()
        create_download_section_for_reports(temp_dir)
