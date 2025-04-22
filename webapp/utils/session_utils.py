# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Session state management utilities for the Document Accessibility Streamlit application.
"""

import os
import uuid
import tempfile
import streamlit as st
from typing import Dict, Any, Optional

class SessionState:
    """
    Helper class to manage Streamlit session state variables.
    
    Provides methods to initialize, get, and set session state variables.
    """
    
    # Define session state keys
    TEMP_DIR_KEY = "temp_dir"
    RESULTS_KEY = "results"
    HTML_PATH_KEY = "html_path"
    AUDIT_RESULTS_KEY = "audit_results"
    REMEDIATED_PATH_KEY = "remediated_path"
    PROCESSING_COMPLETE_KEY = "processing_complete"
    
    @classmethod
    def initialize_session_state(cls) -> None:
        """Initialize the session state if needed."""
        if cls.PROCESSING_COMPLETE_KEY not in st.session_state:
            st.session_state[cls.PROCESSING_COMPLETE_KEY] = False
            st.session_state[cls.TEMP_DIR_KEY] = None
            st.session_state[cls.RESULTS_KEY] = None
            st.session_state[cls.HTML_PATH_KEY] = None
            st.session_state[cls.AUDIT_RESULTS_KEY] = None
            st.session_state[cls.REMEDIATED_PATH_KEY] = None
    
    @classmethod
    def create_temp_dir(cls, work_dir: Optional[str] = None) -> str:
        """
        Create a temporary directory to store files.
        
        Args:
            work_dir: Optional working directory path
            
        Returns:
            Path to the created temporary directory
        """
        if work_dir:
            # Create a uniquely named subdirectory in the work_dir
            temp_dir = os.path.join(work_dir, f"accessibility-{uuid.uuid4().hex}")
            os.makedirs(temp_dir, exist_ok=True)
        else:
            # Fall back to the default mkdtemp behavior
            temp_dir = tempfile.mkdtemp()
        
        st.session_state[cls.TEMP_DIR_KEY] = temp_dir
        return temp_dir
    
    @classmethod
    def save_results(cls, results: Dict[str, Any]) -> None:
        """
        Store processing results in the session state.
        
        Args:
            results: Dictionary of processing results
        """
        st.session_state[cls.RESULTS_KEY] = results
        st.session_state[cls.PROCESSING_COMPLETE_KEY] = True
        
        # Store audit results if available
        if "audit_result" in results:
            st.session_state[cls.AUDIT_RESULTS_KEY] = results["audit_result"]
            
        # Store remediated path if available
        if "remediation_result" in results:
            remediation_result = results.get("remediation_result", {})
            remediated_path = remediation_result.get("output_path", "")
            st.session_state[cls.REMEDIATED_PATH_KEY] = remediated_path
            
            # Check for alternate paths in known structures
            if remediated_path and "remediated_html" not in remediated_path:
                temp_dir = st.session_state[cls.TEMP_DIR_KEY]
                if temp_dir and os.path.exists(os.path.join(temp_dir, "remediated_html")):
                    st.session_state[cls.REMEDIATED_PATH_KEY] = os.path.join(temp_dir, "remediated_html")
    
    @classmethod
    def get_temp_dir(cls) -> Optional[str]:
        """Get the temporary directory path."""
        return st.session_state.get(cls.TEMP_DIR_KEY)
    
    @classmethod
    def get_results(cls) -> Optional[Dict[str, Any]]:
        """Get the processing results."""
        return st.session_state.get(cls.RESULTS_KEY)
    
    @classmethod
    def get_html_path(cls) -> Optional[str]:
        """Get the HTML file path."""
        return st.session_state.get(cls.HTML_PATH_KEY)
    
    @classmethod
    def get_audit_results(cls) -> Optional[Dict[str, Any]]:
        """Get the audit results."""
        return st.session_state.get(cls.AUDIT_RESULTS_KEY)
    
    @classmethod
    def get_remediated_path(cls) -> Optional[str]:
        """Get the remediated HTML path."""
        return st.session_state.get(cls.REMEDIATED_PATH_KEY)
    
    @classmethod
    def is_processing_complete(cls) -> bool:
        """Check if processing is complete."""
        return st.session_state.get(cls.PROCESSING_COMPLETE_KEY, False)
        
    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """
        Get a value from the session state with a default if it doesn't exist.
        
        Args:
            key: The key to retrieve
            default: Default value if key doesn't exist
            
        Returns:
            The value associated with the key or the default
        """
        return st.session_state.get(key, default)
    
    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """
        Set a value in the session state.
        
        Args:
            key: The key to set
            value: The value to store
        """
        st.session_state[key] = value
