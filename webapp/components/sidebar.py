# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Sidebar components for the Document Accessibility Streamlit application.
"""

import streamlit as st
from typing import Dict, Any, Tuple, Optional

from content_accessibility_with_aws import __version__ as current_version
from utils.file_utils import detect_file_type


def create_sidebar() -> (
    Tuple[Optional[st.runtime.uploaded_file_manager.UploadedFile], Dict[str, Any], bool]
):
    """
    Create the sidebar with file upload, processing options, and configuration.

    Returns:
        Tuple containing:
        - Uploaded file object or None
        - Dictionary of processing options
        - Boolean indicating whether the process button was clicked
    """
    with st.sidebar:
        st.title("Document Accessibility")
        st.markdown("Upload a document to process through the accessibility pipeline.")

        # File uploader widget - accepts PDF, HTML, and ZIP files
        uploaded_file = st.file_uploader(
            "Choose a document",
            type=["pdf", "html", "zip"],
            help="Upload PDF for conversion/audit/remediation, or HTML/ZIP for direct audit/remediation",
        )

        # Determine file type (if file is uploaded)
        file_type = None
        if uploaded_file is not None:
            file_type = detect_file_type(uploaded_file.name)

        # Processing options in sidebar
        processing_options = get_processing_options(file_type)

        # Process button
        process_button = st.button("Process Document", type="primary")

        st.markdown(f"Using document-accessibility v{current_version}")
        st.markdown("Bedrock Model: `amazon.nova-lite-v1:0`")

        return uploaded_file, processing_options, process_button


def get_processing_options(file_type: Optional[str]) -> Dict[str, Any]:
    """
    Get processing options based on file type.

    Args:
        file_type: Type of file ('pdf', 'html', 'zip', or None)

    Returns:
        Dictionary of processing options
    """
    st.header("Processing Options")

    # Processing mode selection
    if file_type == "pdf":
        processing_mode = st.radio(
            "Processing Mode",
            options=["Convert Only", "Convert + Audit", "Full Processing"],
            index=2,  # Default to Full Processing
            help="Select the level of processing to apply",
        )
    elif file_type in ["html", "zip"]:
        processing_mode = st.radio(
            "Processing Mode",
            options=["Audit Only", "Audit + Remediate"],
            index=1,  # Default to Audit + Remediate
            help="Select the level of processing to apply",
        )
    else:
        # No file uploaded yet, show all options
        processing_mode = st.radio(
            "Processing Mode",
            options=["Convert Only", "Convert + Audit", "Full Processing"],
            index=2,  # Default to Full Processing
            help="Select the level of processing to apply",
        )

    # Determine processing flags based on selected mode
    if file_type == "pdf":
        perform_audit = processing_mode in ["Convert + Audit", "Full Processing"]
        perform_remediation = processing_mode == "Full Processing"
    else:  # HTML or ZIP
        perform_audit = True  # Always audit HTML/ZIP
        perform_remediation = processing_mode == "Audit + Remediate"

    options = {
        "processing_mode": processing_mode,
        "perform_audit": perform_audit,
        "perform_remediation": perform_remediation,
    }

    # PDF to HTML conversion options - only show if PDF is selected
    if file_type == "pdf" or file_type is None:
        with st.expander("PDF to HTML Options", expanded=False):
            options["extract_images"] = st.checkbox("Extract images", value=True)
            options["image_format"] = st.selectbox(
                "Image format", ["png", "jpg"], index=0
            )
            options["multiple_documents"] = st.checkbox(
                "Generate multiple HTML files", value=False
            )

    # Audit options
    with st.expander("Audit Options", expanded=False):
        options["check_images"] = st.checkbox("Check images", value=True)
        options["check_headings"] = st.checkbox("Check headings", value=True)
        options["check_links"] = st.checkbox("Check links", value=True)
        options["check_tables"] = st.checkbox("Check tables", value=True)
        options["severity_threshold"] = st.selectbox(
            "Severity threshold", ["error", "warning", "info"], index=1
        )

    # Remediation options - only show if remediation is part of selected mode
    if (
        (file_type == "pdf" and processing_mode == "Full Processing")
        or (file_type in ["html", "zip"] and processing_mode == "Audit + Remediate")
        or (file_type is None)
    ):
        with st.expander("Remediation Options", expanded=False):
            options["fix_images"] = st.checkbox("Fix image issues", value=True)
            options["fix_headings"] = st.checkbox("Fix heading issues", value=True)
            options["fix_links"] = st.checkbox("Fix link issues", value=True)

    # Cost calculation options
    with st.expander("Cost Calculation Options", expanded=False):
        # Retrieve current values from session state or use defaults
        # Get cost rates from session state
        # Price defaults are for Amazon Bedrock Data Automation (BDA) and Bedrock API using of
        # Amazon Nova Lite Model with on-demand in US East (N. Virginia) region as of 2025-04-01
        # These rates are subject to change, please refer to the official AWS pricing page for the most up-to-date information.
        # https://aws.amazon.com/bedrock/pricing/
        if "cost_per_bda_page" in st.session_state:
            cost_per_bda_page = st.session_state["cost_per_bda_page"]
        else:
            cost_per_bda_page = 0.01
            st.session_state["cost_per_bda_page"] = cost_per_bda_page

        if "cost_per_input_token" in st.session_state:
            cost_per_input_token = st.session_state["cost_per_input_token"]
        else:
            cost_per_input_token = 0.00006
            st.session_state["cost_per_input_token"] = cost_per_input_token

        if "cost_per_output_token" in st.session_state:
            cost_per_output_token = st.session_state["cost_per_output_token"]
        else:
            cost_per_output_token = 0.00024
            st.session_state["cost_per_output_token"] = cost_per_output_token

        # Display cost input fields
        new_cost_per_bda_page = st.number_input(
            "Cost per page in BDA ($)",
            min_value=0.0,
            value=float(cost_per_bda_page),
            format="%.2f",
            help="Cost in $ per page processed through Bedrock Data Automation",
        )

        new_cost_per_input_token = st.number_input(
            "Cost per 1K input tokens ($)",
            min_value=0.0,
            value=float(cost_per_input_token),
            format="%.6f",
            help="Cost in $ per 1,000 input tokens for Bedrock models",
        )

        new_cost_per_output_token = st.number_input(
            "Cost per 1K output tokens ($)",
            min_value=0.0,
            value=float(cost_per_output_token),
            format="%.6f",
            help="Cost in $ per 1,000 output tokens for Bedrock models",
        )
        st.caption(
            "Note: Default costs are base on AWS Pricing of Amazon Bedrock Data Automation & Amazon Bedrock Nova Lite Model with on-demand consumption in US East (N. Virginia) region as of 2025-04-01. These costs may vary based on your consumption type, provisioned capacity, model and region. Please refer to the [AWS Pricing page](https://aws.amazon.com/bedrock/pricing/) for the most accurate and up-to-date information."
        )

        # Update session state values if they've changed
        if new_cost_per_bda_page != cost_per_bda_page:
            st.session_state["cost_per_bda_page"] = new_cost_per_bda_page

        if new_cost_per_input_token != cost_per_input_token:
            st.session_state["cost_per_input_token"] = new_cost_per_input_token

        if new_cost_per_output_token != cost_per_output_token:
            st.session_state["cost_per_output_token"] = new_cost_per_output_token

    return options
