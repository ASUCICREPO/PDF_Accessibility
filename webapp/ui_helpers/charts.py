# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Chart and visualization components for the Document Accessibility Streamlit application.
"""

import streamlit as st
from typing import Dict, Any, List, Optional

def display_audit_summary(summary: Dict[str, Any]) -> None:
    """
    Display audit summary metrics.
    
    Args:
        summary: Dictionary containing audit summary data
    """
    if not summary:
        return
    
    # Display summary metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Issues", summary.get("total_issues", 0))
    with col2:
        st.metric(
            "Compliant",
            summary.get("compliant", 0),
            delta=None,
            delta_color="inverse",
        )
    with col3:
        st.metric(
            "Needs Remediation",
            summary.get("needs_remediation", 0),
            delta=None,
            delta_color="inverse",
        )

def display_remediation_stats(summary: Dict[str, Any]) -> None:
    """
    Display remediation statistics.
    
    Args:
        summary: Dictionary containing remediation summary data
    """
    if not summary:
        return
    
    # Calculate remediation statistics
    total_issues = summary.get("total_issues", 0)
    remediated_issues = summary.get("remediated_issues", 0)
    failed_issues = summary.get("failed_issues", 0)
    
    # Check if we need to calculate the values
    if remediated_issues == 0 and failed_issues == 0 and "issues" in summary:
        issues = summary.get("issues", [])
        remediated_issues = sum(
            1 for i in issues if i.get("remediation_status") == "remediated"
        )
        failed_issues = sum(
            1 for i in issues if i.get("remediation_status") != "remediated"
        )
    
    # Calculate success rate
    success_rate = 0
    if total_issues > 0:
        success_rate = int((remediated_issues / total_issues) * 100)
    
    # Display the statistics in columns
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Issues", total_issues)
    with col2:
        st.metric("Successfully Remediated", remediated_issues)
    with col3:
        st.metric("Failed Remediation", failed_issues)
    
    # Add progress bar for success rate
    st.progress(success_rate / 100)
    st.caption(f"Success Rate: {success_rate}%")

def display_severity_breakdown(issues: List[Dict[str, Any]], summary: Optional[Dict[str, Any]] = None) -> None:
    """
    Display severity breakdown of issues.
    
    Args:
        issues: List of issue dictionaries
        summary: Optional summary dictionary that may contain pre-calculated severity counts
    """
    # Get severity counts from summary if available
    if summary and "severity_counts" in summary:
        severity_counts = summary.get("severity_counts", {})
        critical = severity_counts.get("critical", 0)
        major = severity_counts.get("major", 0)
        minor = severity_counts.get("minor", 0)
    else:
        # Calculate from issues
        critical = sum(1 for i in issues if i.get("severity") == "critical")
        major = sum(1 for i in issues if i.get("severity") == "major")
        minor = sum(1 for i in issues if i.get("severity") == "minor")
    
    # Display severity breakdown
    st.subheader("Severity Breakdown")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Critical Issues",
            critical,
            delta=(
                f"{sum(1 for i in issues if i.get('severity') == 'critical' and i.get('remediation_status') == 'remediated')} fixed"
                if critical > 0
                else None
            ),
        )
    with col2:
        st.metric(
            "Major Issues",
            major,
            delta=(
                f"{sum(1 for i in issues if i.get('severity') == 'major' and i.get('remediation_status') == 'remediated')} fixed"
                if major > 0
                else None
            ),
        )
    with col3:
        st.metric(
            "Minor Issues",
            minor,
            delta=(
                f"{sum(1 for i in issues if i.get('severity') == 'minor' and i.get('remediation_status') == 'remediated')} fixed"
                if minor > 0
                else None
            ),
        )

def display_issues_by_type(issues: List[Dict[str, Any]], summary: Optional[Dict[str, Any]] = None) -> None:
    """
    Display issues grouped by type with bar charts.
    
    Args:
        issues: List of issue dictionaries
        summary: Optional summary dictionary that may contain pre-calculated type statistics
    """
    # Get issue type statistics
    issue_types = {}
    
    if summary and "issue_type_stats" in summary:
        issue_types = summary.get("issue_type_stats", {})
    else:
        # Calculate from issues
        for issue in issues:
            issue_type = issue.get("type", "Unknown")
            if issue_type not in issue_types:
                issue_types[issue_type] = 0
            issue_types[issue_type] += 1
    
    # Display issue type breakdown if we have any
    if issue_types:
        st.subheader("Issues by Type")
        
        # Sort issue types by count (descending)
        sorted_issues = sorted(
            issue_types.items(), key=lambda x: x[1], reverse=True
        )
        
    
        # Display horizontal bar chart using markdown
        for issue_type, count in sorted_issues:
            # Count remediated issues of this type
            remediated_of_type = sum(
                1
                for i in issues
                if i.get("type") == issue_type
                and i.get("remediation_status") == "remediated"
            )
            
            # Display bar with label
            st.write(f"**{issue_type}**: {count} ({remediated_of_type} remediated)")
            progress_value = remediated_of_type / count if count > 0 else 0
            st.progress(progress_value)
