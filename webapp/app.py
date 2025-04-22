# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Document Accessibility Streamlit Application

This application provides a web interface for processing PDF documents
through the document accessibility pipeline.
"""

import os
from typing import Dict, Any
import sys
import logging
import streamlit as st
# Import local modules
from config.app_config_local import Config
# Import other local modules
from utils.session_utils import SessionState
from utils.file_utils import save_uploaded_file, detect_file_type
from components.sidebar import create_sidebar
from processors.pdf_processor import process_pdf_file
from processors.html_processor import process_html_file
from processors.zip_processor import process_zip_file
from views.audit_view import display_audit_view
from views.remediation_view import display_remediation_view
from views.report_view import display_report_view
from views.usage_view import display_usage_view
# Make Python able to find local modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))



# Create config instance
app_config = Config()



# Set up logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main():
    """Main application function"""

    # Set page configuration
    st.set_page_config(
        page_title="Document Accessibility Tool",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize session state
    SessionState.initialize_session_state()

    # Create sidebar components
    uploaded_file, processing_options, process_button = create_sidebar()

    # Main content area
    st.title("Document Accessibility Tool")

    # Process the file when the button is clicked
    if uploaded_file is not None and process_button:
        process_uploaded_file(uploaded_file, processing_options)

    # Display results if processing is complete
    if SessionState.is_processing_complete() and SessionState.get_results() is not None:
        display_results(SessionState.get_results(), SessionState.get_temp_dir())


def process_uploaded_file(uploaded_file, processing_options: Dict[str, Any]) -> None:
    """
    Process the uploaded file based on its type.

    Args:
        uploaded_file: Streamlit uploaded file object
        processing_options: Dictionary of processing options
    """
    # Determine the file type
    file_type = detect_file_type(uploaded_file.name)

    if file_type is None:
        st.error(f"Unsupported file type: {uploaded_file.name}")
        return

    # Create a temporary directory to store files
    temp_dir = SessionState.create_temp_dir(app_config.work_dir)

    # Save the uploaded file to the temporary directory
    file_path = save_uploaded_file(uploaded_file, temp_dir)

    # Process the file based on its type
    success = False
    results = None

    if file_type == "pdf":
        success, results = process_pdf_file(
            file_path, temp_dir, app_config, processing_options
        )
    elif file_type == "html":
        success, results = process_html_file(
            file_path, temp_dir, app_config, processing_options
        )
    elif file_type == "zip":
        success, results = process_zip_file(
            file_path, temp_dir, app_config, processing_options
        )

    # Save results to session state if successful
    if success and results:
        SessionState.save_results(results)


def display_results(results: Dict[str, Any], temp_dir: str) -> None:
    """
    Display the results of processing in tabs.

    Args:
        results: Dictionary of processing results
        temp_dir: Temporary directory with processing files
    """
    # Create tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs(
        ["Audit Results", "Remediated Output", "Remediation Report", "Usage Data"]
    )

    # Tab 1: Audit Results
    with tab1:
        if "audit_result" in results:
            display_audit_view(results["audit_result"])
        else:
            st.warning("No audit results available.")

    # Tab 2: Remediated Output
    with tab2:
        if "remediation_result" in results:
            remediated_path = results.get("remediation_result", {}).get(
                "remediated_html_path", ""
            )
            display_remediation_view(remediated_path)
        else:
            st.info("No remediation was performed or no results are available.")

    # Tab 3: Remediation Report
    with tab3:
        if "remediation_result" in results:
            display_report_view(results.get("remediation_result"), temp_dir)
        else:
            st.info("No remediation report is available.")
            
    # Tab 4: Usage Data
    with tab4:
        # Look for usage data in results
        usage_data_path = results.get("usage_data_path")
        
        # If no direct path but we have an S3 URI, show the S3 info
        if not usage_data_path and "usage_data_s3_uri" in results:
            st.info("Usage data was saved to S3. Download and view it locally.")
            st.code(results["usage_data_s3_uri"])
        else:
            # Try to find usage data in the temp directory if not directly provided
            if not usage_data_path and temp_dir:
                possible_path = os.path.join(temp_dir, "usage_data.json")
                if os.path.exists(possible_path):
                    usage_data_path = possible_path
            
            # Display the usage data
            display_usage_view(usage_data_path)


if __name__ == "__main__":
    main()
