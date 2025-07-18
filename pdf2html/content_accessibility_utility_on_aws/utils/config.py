# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Configuration management utilities for the document_accessibility package.

This module provides a centralized configuration system that manages default
options, user-provided settings, and environment variables across all modules.
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional
from copy import deepcopy

from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger, ConfigurationError

# Configure module-level logger
logger = setup_logger(__name__)


class ConfigManager:
    """
    Centralized configuration manager for document accessibility components.

    This class handles:
    - Default options
    - User-provided options
    - Environment variables
    - Option validation
    - Option merging and cascade
    """

    def __init__(
        self, defaults: Dict[str, Any] = None, env_prefix: str = "DOC_ACCESS_"
    ):
        """
        Initialize a configuration manager.

        Args:
            defaults: Dictionary of default options
            env_prefix: Prefix for environment variables
        """
        self.defaults = defaults or {}
        self.env_prefix = env_prefix
        self.user_config = {}

    def get_config(
        self, user_options: Dict[str, Any] = None, section: str = None
    ) -> Dict[str, Any]:
        """
        Get the resolved configuration with defaults, environment vars, and user options.

        Args:
            user_options: User-provided option overrides
            section: Optional section name to retrieve (e.g., 'pdf', 'audit', 'remediation')

        Returns:
            Dict with the resolved configuration options
        """
        # Start with defaults
        if section and section in self.defaults:
            config = deepcopy(self.defaults[section])
        else:
            config = deepcopy(self.defaults)

        # Apply stored user config
        if section and section in self.user_config:
            config.update(self.user_config[section])
        elif not section:
            config.update(self.user_config)

        # Apply environment variables
        self._apply_env_vars(config, section)

        # Apply runtime user options (highest precedence)
        if user_options:
            config.update(user_options)

        return config

    def update_defaults(
        self, new_defaults: Dict[str, Any], section: str = None
    ) -> None:
        """
        Update default configuration values.

        Args:
            new_defaults: Dictionary of new default values
            section: Optional section to update
        """
        if section:
            if section not in self.defaults:
                self.defaults[section] = {}
            self.defaults[section].update(new_defaults)
        else:
            self.defaults.update(new_defaults)

    def set_user_config(self, config: Dict[str, Any], section: str = None) -> None:
        """
        Set persistent user configuration.

        Args:
            config: Dictionary of configuration options
            section: Optional section name
        """
        if section:
            if section not in self.user_config:
                self.user_config[section] = {}
            self.user_config[section].update(config)
        else:
            self.user_config.update(config)

    def _apply_env_vars(self, config: Dict[str, Any], section: str = None) -> None:
        """
        Apply relevant environment variables to the configuration.

        Args:
            config: Configuration dictionary to update
            section: Optional section name to scope environment variables
        """
        prefix = self.env_prefix
        if section:
            prefix = f"{prefix}{section.upper()}_"

        # Find all relevant environment variables
        for env_var, value in os.environ.items():
            # Skip if not matching our prefix
            if not env_var.startswith(prefix):
                continue

            # Extract the option name by removing the prefix
            option_name = env_var[len(prefix) :].lower()

            # Convert value type based on existing config if possible
            if option_name in config:
                # Try to convert to the same type as the default
                try:
                    existing_value = config[option_name]
                    existing_type = type(existing_value)

                    if existing_type == bool:
                        # Special handling for booleans
                        value = value.lower() in ("true", "1", "yes", "y")
                    elif existing_type == int:
                        value = int(value)
                    elif existing_type == float:
                        value = float(value)
                    elif existing_type == list:
                        # Split by commas for list values
                        value = [item.strip() for item in value.split(",")]
                    # else use the string value
                except (ValueError, TypeError):
                    logger.warning(
                        f"Could not convert environment variable {env_var} to {existing_type.__name__}"
                    )

            # Update the config with the environment value
            config[option_name] = value
            logger.debug(f"Applied environment variable {env_var}")


def validate_options(
    options: Dict[str, Any],
    required_fields: Optional[Dict[str, type]] = None,
    optional_fields: Optional[Dict[str, type]] = None,
) -> None:
    """
    Validate configuration options against schemas.

    Args:
        options: The options dictionary to validate
        required_fields: Dictionary mapping field names to expected types
        optional_fields: Dictionary mapping optional field names to expected types

    Raises:
        ConfigurationError: If validation fails
    """
    # Validate required fields
    if required_fields:
        for field, field_type in required_fields.items():
            if field not in options:
                raise ConfigurationError(f"Required field '{field}' is missing")

            if not isinstance(options[field], field_type):
                raise ConfigurationError(
                    f"Field '{field}' has incorrect type. "
                    f"Expected {field_type.__name__}, got {type(options[field]).__name__}"
                )

    # Validate optional fields if present
    if optional_fields:
        for field, field_type in optional_fields.items():
            if field in options and not isinstance(options[field], field_type):
                raise ConfigurationError(
                    f"Field '{field}' has incorrect type. "
                    f"Expected {field_type.__name__}, got {type(options[field]).__name__}"
                )


def load_config_file(file_path: str) -> Dict[str, Any]:
    """
    Load configuration from a file.
    
    Supports YAML (.yaml, .yml) and JSON (.json) formats.
    
    Args:
        file_path: Path to the configuration file
        
    Returns:
        Dictionary with configuration options
        
    Raises:
        ConfigurationError: If file cannot be loaded or parsed
    """
    path = Path(file_path)
    
    if not path.exists():
        raise ConfigurationError(f"Configuration file not found: {file_path}")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            if path.suffix.lower() in ('.yaml', '.yml'):
                return yaml.safe_load(f) or {}
            elif path.suffix.lower() == '.json':
                return json.load(f)
            else:
                raise ConfigurationError(
                    f"Unsupported configuration file format: {path.suffix}. "
                    "Supported formats: YAML (.yaml, .yml), JSON (.json)"
                )
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        raise ConfigurationError(f"Error parsing configuration file: {e}")
    except Exception as e:
        raise ConfigurationError(f"Error loading configuration file: {e}")


def save_config(config: Dict[str, Any], file_path: str, file_format: str = "yaml") -> None:
    """
    Save configuration to a file.
    
    Args:
        config: Configuration dictionary
        file_path: Path to save the configuration file
        format: File format ('yaml' or 'json')
        
    Raises:
        ConfigurationError: If file cannot be written
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            if file_format.lower() == "yaml":
                yaml.dump(config, f, default_flow_style=False)
            elif file_format.lower() == "json":
                json.dump(config, f, indent=2)
            else:
                raise ConfigurationError(f"Unsupported format: {file_format}")
        logger.info(f"Configuration saved to {file_path}")
    except Exception as e:
        raise ConfigurationError(f"Error saving configuration: {e}")


# Global instance for shared configuration
config_manager = ConfigManager(
    {
        # PDF to HTML conversion defaults
        "pdf": {
            "extract_images": True,
            "image_format": "png",
            "embed_fonts": False,
            "single_html": False,
            "page_range": None,
            "single_file": False,
            "continuous": True,
            "inline_css": False,
            "embed_images": False,
            "exclude_images": False,
            "cleanup_bda_output": False,
        },
        # Accessibility auditing defaults
        "audit": {
            "audit_accessibility": True,
            "min_severity": "minor",  # minor, major, critical
            "detailed_context": True,
            "skip_automated_checks": False,
            "issue_types": None,  # List of issue types to check, None = all
        },
        # Accessibility remediation defaults
        "remediate": {
            "max_issues": None,  # None = all issues
            "model_id": "us.amazon.nova-lite-v1:0",
            "issue_types": None,  # List of issue types to remediate, None = all
            "severity_threshold": "minor",  # Include all issues by default
            "report_format": "json",
        },
        # AWS/BDA-related defaults
        "aws": {
            "create_bda_project": False,
            "bda_project_name": None,
            "bda_profile_name": None,
        },
    }
)
