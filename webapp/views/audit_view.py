# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Audit results view for the Document Accessibility Streamlit application.
"""

import streamlit as st
from typing import Dict, Any, List, Optional

from ui_helpers.charts import display_audit_summary

def display_audit_view(audit_result: Optional[Dict[str, Any]] = None) -> None:
    """
    Display audit results in a structured format.
    
    Args:
        audit_result: Dictionary containing audit results
    """
    st.header("Audit Results")
    
    if not audit_result:
        st.info("No audit results available.")
        return
    
    issues = audit_result.get("issues", [])
    summary = audit_result.get("summary", {})

    # Display summary
    st.subheader("Audit Summary")
    display_audit_summary(summary)

    # Display issues
    st.subheader("Accessibility Issues")

    if issues:
        # Group issues by type
        issues_by_type = {}
        for issue in issues:
            issue_type = issue.get("type", "Unknown")
            if issue_type not in issues_by_type:
                issues_by_type[issue_type] = []
            issues_by_type[issue_type].append(issue)

        # Create expandable sections for each issue type
        for issue_type, type_issues in issues_by_type.items():
            with st.expander(f"{issue_type} ({len(type_issues)})"):
                for i, issue in enumerate(type_issues):
                    st.markdown(f"### {i+1}. {issue.get('criterion_name', 'No message')}")

                    # Create columns for details
                    col1, col2 = st.columns(2)
                    with col1:
                        severity = issue.get('severity', 'Unknown').lower()
                        severity_color = {
                            'critical': '#FF0000',  # Bright red
                            'major': '#FF6B6B',     # Light red  
                            'minor': '#FFD700'      # Yellow
                        }.get(severity, 'black')
                        severity_display = severity.title() if severity in ['critical', 'major', 'minor'] else severity
                        st.markdown(
                            f"**Severity:** <span style='color:{severity_color}'>{severity_display}</span>",
                            unsafe_allow_html=True
                        )
                        # Fix element display by checking multiple possible field names
                        element_info = issue.get('element_type') or issue.get('element') or issue.get('element_name') or issue.get('selector', 'Unknown')
                        # Some fields might contain HTML tags - extract just the tag name if present
                        if element_info and isinstance(element_info, str) and element_info.startswith('<') and '>' in element_info:
                            element_tag = element_info.split('<')[1].split('>')[0].split()[0]
                            element_info = element_tag
                        st.markdown(f"**Element:** {element_info}")
                        page_number = issue.get('location', {}).get('page_number', 'Unknown')

                        st.markdown(f"**Page:** {page_number}")
                    with col2:
                        st.markdown(
                            f"**WCAG:** {issue.get('wcag_criterion', 'N/A')} - {issue.get('criterion_name', 'N/A')}\n\n"+
                            f"**WCAG Description:** {issue.get('description', 'N/A')}"
                        )
                        status = issue.get('remediation_status', 'Unknown')
                        color = 'green' if status == 'compliant' else 'red' if status == 'needs_remediation' else 'black'
                        display_text = 'Compliant' if status == 'compliant' else 'Not Compliant' if status == 'needs_remediation' else status
                        st.markdown(
                            f"**Status:** <span style='color:{color}'>{display_text}</span>",
                            unsafe_allow_html=True
                        )

                    # Display the HTML code with the issue
                    if "html_snippet" in issue:
                        with st.expander("HTML Snippet"):
                            st.code(issue["html_snippet"], language="html")

                    # Display help text
                    if "help_text" in issue:
                        with st.expander("Remediation Help"):
                            st.markdown(issue["help_text"])

                    st.divider()
    else:
        st.success("No accessibility issues found!")

def display_issues_with_filters(issues: List[Dict[str, Any]]) -> None:
    """
    Display issues with filtering options.
    
    Args:
        issues: List of issue dictionaries
    """
    # Create filter options
    status_filter = st.radio(
        "Filter by Status",
        options=["All Issues", "Remediated", "Failed"],
        horizontal=True,
    )

    severity_filter = st.radio(
        "Filter by Severity",
        options=["All Severities", "Critical", "Major", "Minor"],
        horizontal=True,
    )

    # Apply filters with extra validation
    filtered_issues = [i for i in issues if isinstance(i, dict)]

    if status_filter == "Remediated":
        filtered_issues = [
            i for i in filtered_issues 
            if str(i.get("remediation_status", "")).lower() == "remediated"
        ]
    elif status_filter == "Failed":
        filtered_issues = [
            i for i in filtered_issues
            if str(i.get("remediation_status", "")).lower() != "remediated"
        ]

    if severity_filter != "All Severities":
        filtered_issues = [
            i for i in filtered_issues
            if str(i.get("severity", "")).lower() == severity_filter.lower()
        ]

    # Group issues by type
    issues_by_type = {}
    for issue in filtered_issues:
        issue_type = issue.get("type", "Unknown")
        if issue_type not in issues_by_type:
            issues_by_type[issue_type] = []
        issues_by_type[issue_type].append(issue)

    # Check if we have issues after filtering
    if not filtered_issues:
        st.info("No issues match the selected filters.")
        return

    # Display issues grouped by type
    for issue_type, type_issues in issues_by_type.items():
        with st.expander(f"{issue_type} ({len(type_issues)})"):
            for i, issue in enumerate(type_issues):
                # Determine status color
                status = issue.get("remediation_status")
                status_color = "green" if status == "remediated" else "red"
                status_icon = "✅" if status == "remediated" else "❌"

                # Create a panel for each issue
                st.markdown(f"### {i+1}. {issue.get('message', 'No message')} {status_icon}")

                # Create columns for details
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Severity:** {issue.get('severity', 'Unknown')}")
                    # Fix element display by checking multiple possible field names
                    element_info = issue.get('element_type') or issue.get('element') or issue.get('element_name') or issue.get('selector', 'Unknown')
                    # Some fields might contain HTML tags - extract just the tag name if present
                    if isinstance(element_info, str) and element_info.startswith('<') and '>' in element_info:
                        element_tag = element_info.split('<')[1].split('>')[0].split()[0]
                        element_info = element_tag
                    st.markdown(f"**Element:** {element_info}")
                with col2:
                    st.markdown(f"**WCAG:** {issue.get('wcag_criteria', 'N/A')}")
                    st.markdown(
                        f"**Status:** <span style='color:{status_color}'>{status.upper() if status else 'Unknown'}</span>",
                        unsafe_allow_html=True,
                    )
                    if issue.get("selector"):
                        st.markdown(f"**Selector:** `{issue.get('selector')}`")

                # Display remediation details if available
                remediation_details = issue.get("remediation_details", {})

                if remediation_details:
                    st.markdown("##### Remediation Details")
                    if remediation_details.get("description"):
                        st.markdown(f"**Description:** {remediation_details.get('description')}")

                    if remediation_details.get("fix_description"):
                        st.markdown(f"**Fix Applied:** {remediation_details.get('fix_description')}")

                    if remediation_details.get("failure_reason"):
                        st.markdown(f"**Failure Reason:** {remediation_details.get('failure_reason')}")

                    # Show before/after HTML if available
                    if remediation_details.get("before_content") and remediation_details.get("after_content"):
                        st.markdown("##### Before/After Comparison")

                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Before:**")
                            st.code(
                                remediation_details.get("before_content", ""),
                                language="html",
                            )
                        with col2:
                            st.markdown("**After:**")
                            st.code(
                                remediation_details.get("after_content", ""),
                                language="html",
                            )

                st.divider()
