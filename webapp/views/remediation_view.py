# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Remediation results view for the Document Accessibility Streamlit application.
"""

import os
import streamlit as st
from typing import Optional

from ui_helpers.html_preview import display_html_with_pagination
from ui_helpers.download_helpers import create_download_section_for_remediated_files

def display_remediation_view(remediated_path: Optional[str] = None) -> None:
    """
    Display remediated HTML output with download options.
    
    Args:
        remediated_path: Path to the remediated HTML file(s)
    """
    st.header("Remediated Output")
    
    if not remediated_path or not os.path.exists(remediated_path):
        st.info("No remediated output is available.")
        return
    
    # Display HTML preview
    st.subheader("HTML Preview")
    st.divider()
    
    # Display HTML content with pagination if multiple files
    display_html_with_pagination(remediated_path)
    
    # Add download section
    st.divider()
    create_download_section_for_remediated_files(remediated_path)
