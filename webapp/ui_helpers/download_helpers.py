# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Download utilities for the Document Accessibility Streamlit application.
"""

import os
import zipfile
import streamlit as st
from typing import Optional

def create_download_button_for_file(file_path: str, button_text: str, download_filename: Optional[str] = None) -> None:
    """
    Create a download button for a file.
    
    Args:
        file_path: Path to the file
        button_text: Text to display on the button
        download_filename: Optional filename to use for download (defaults to basename of file_path)
    """
    if not os.path.exists(file_path):
        st.warning(f"File not found: {file_path}")
        return
    
    if download_filename is None:
        download_filename = os.path.basename(file_path)
    
    # Determine the MIME type
    mime_type = "application/octet-stream"
    if file_path.lower().endswith(".html"):
        mime_type = "text/html"
    elif file_path.lower().endswith(".json"):
        mime_type = "application/json"
    elif file_path.lower().endswith(".zip"):
        mime_type = "application/zip"
    elif file_path.lower().endswith(".pdf"):
        mime_type = "application/pdf"
    
    # Read and create download button
    with open(file_path, "rb", encoding=None) as file:
        st.download_button(
            label=button_text,
            data=file,
            file_name=download_filename,
            mime=mime_type,
        )

def create_download_button_for_directory(directory_path: str, button_text: str, download_filename: str) -> None:
    """
    Create a download button for a directory by zipping its contents.
    
    Args:
        directory_path: Path to the directory
        button_text: Text to display on the button
        download_filename: Filename to use for the zip download
    """
    import tempfile
    
    if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
        st.warning(f"Directory not found: {directory_path}")
        return
    
    # Create a temporary zip file - using secure mkstemp instead of insecure mktemp
    fd, temp_zip_path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)  # Close the file descriptor immediately
    
    try:
        # Create a zip file containing the directory contents
        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(directory_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, directory_path)
                    zipf.write(file_path, arcname)
        
        # Create download button for the zip file
        with open(temp_zip_path, "rb") as file:
            st.download_button(
                label=button_text,
                data=file,
                file_name=download_filename,
                mime="application/zip",
            )
    
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_zip_path):
            try:
                os.remove(temp_zip_path)
            except Exception:
                print(f"Failed to remove temporary file: {temp_zip_path}")

def create_download_section_for_remediated_files(remediated_path: str) -> None:
    """
    Create a download section for remediated files.
    
    Args:
        remediated_path: Path to the remediated files
    """
    if not os.path.exists(remediated_path):
        st.warning(f"No remediated files found at {remediated_path}")
        return
    
    st.subheader("Download Remediated Files")
    
    if os.path.isdir(remediated_path):
        # Directory with multiple files
        html_files = [f for f in os.listdir(remediated_path) 
                      if f.lower().endswith(".html") and os.path.isfile(os.path.join(remediated_path, f))]
        
        if len(html_files) > 1:
            # Multiple HTML files - offer both individual and zip download
            col1, col2 = st.columns(2)
            
            with col1:
                create_download_button_for_directory(
                    remediated_path,
                    "Download All Files (ZIP)",
                    "remediated_files.zip"
                )
                
            with col2:
                # Allow downloading individual files
                selected_file = st.selectbox(
                    "Select individual file to download:",
                    html_files
                )
                if selected_file:
                    create_download_button_for_file(
                        os.path.join(remediated_path, selected_file),
                        f"Download {selected_file}",
                        selected_file
                    )
        
        elif len(html_files) == 1:
            # Single HTML file
            create_download_button_for_file(
                os.path.join(remediated_path, html_files[0]),
                "Download Remediated HTML",
                "remediated_document.html"
            )
        
        else:
            st.info("No HTML files found in the remediation directory.")
    
    else:
        # Single file
        create_download_button_for_file(
            remediated_path,
            "Download Remediated HTML",
            "remediated_document.html"
        )

def create_download_section_for_reports(temp_dir: str) -> None:
    """
    Create a download section for report files.
    
    Args:
        temp_dir: Temporary directory containing report files
    """
    if not os.path.exists(temp_dir):
        return
        
    # Find report files
    html_report_path = os.path.join(temp_dir, "remediation_report.html")
    json_report_path = os.path.join(temp_dir, "remediation_report.json")
    audit_report_path = os.path.join(temp_dir, "accessibility_audit.json")
    
    has_reports = (os.path.exists(html_report_path) or 
                  os.path.exists(json_report_path) or 
                  os.path.exists(audit_report_path))
    
    if has_reports:
        st.subheader("Download Reports")
        
        
        # HTML remediation report
        if os.path.exists(html_report_path):
            create_download_button_for_file(
                html_report_path,
                "Download HTML Report",
                "remediation_report.html"
            )
        
        # JSON remediation report
        if os.path.exists(json_report_path):
            create_download_button_for_file(
                json_report_path,
                "Download JSON Remediation Report",
                "remediation_report.json"
            )
        
        # Audit report
        if os.path.exists(audit_report_path):
            create_download_button_for_file(
                audit_report_path,
                "Download Audit Report",
                "accessibility_audit.json"
            )
