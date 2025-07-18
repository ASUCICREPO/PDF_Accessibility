# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Resource management utilities for the document_accessibility package.

This module provides consistent resource handling including file system
operations, temporary resources, and cleanup mechanisms.
"""

import os
import tempfile
import shutil
import uuid
import contextlib
from typing import List, Dict, Generator

from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger, ResourceError
from content_accessibility_utility_on_aws.utils.path_fixes import normalize_path

# Configure module-level logger
logger = setup_logger(__name__)


@contextlib.contextmanager
def temp_directory(
    prefix: str = "docaccess_", cleanup: bool = True, use_cwd: bool = True
) -> Generator[str, None, None]:
    """
    Context manager for creating and cleaning up a temporary directory.

    Args:
        prefix: Prefix for the temporary directory name
        cleanup: Whether to remove the directory when exiting the context
        use_cwd: If True, create directory in current working directory instead of system temp

    Yields:
        Path to the temporary directory

    Raises:
        ResourceError: If there's an error creating or cleaning up the directory
    """
    temp_dir = None
    try:
        if use_cwd:
            # Create in current working directory
            unique_id = str(uuid.uuid4())[:8]
            temp_dir_name = f"{prefix}{unique_id}"
            # Normalize path to handle symlinks and ensure consistent paths
            current_dir = os.path.realpath(os.getcwd())
            temp_dir = normalize_path(os.path.join(current_dir, temp_dir_name))
            os.makedirs(temp_dir, exist_ok=True)
            logger.debug(
                f"Created temporary directory in current working directory: {temp_dir}"
            )
        else:
            # Use system temp directory
            temp_dir = tempfile.mkdtemp(prefix=prefix)
            logger.debug(f"Created temporary directory in system temp: {temp_dir}")

        yield temp_dir
    except Exception as e:
        logger.error(f"Error in temporary directory context: {e}")
        raise ResourceError(f"Temporary directory error: {e}") from e
    finally:
        if cleanup and temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.debug(f"Removed temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(
                    f"Failed to clean up temporary directory {temp_dir}: {e}"
                )


def ensure_directory(directory_path: str) -> str:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        directory_path: Path to the directory

    Returns:
        The normalized absolute path to the directory

    Raises:
        ResourceError: If the directory cannot be created
    """
    try:
        # Normalize the path to handle symlinks and ensure consistency
        norm_path = normalize_path(directory_path)
        os.makedirs(norm_path, exist_ok=True)
        return norm_path
    except Exception as e:
        logger.warning(f"Failed to create directory {directory_path}: {e}")
        raise ResourceError(f"Directory creation error: {e}") from e


def safe_file_copy(src_path: str, dest_path: str, overwrite: bool = True) -> str:
    """
    Safely copy a file, ensuring the destination directory exists.

    Args:
        src_path: Source file path
        dest_path: Destination file path
        overwrite: Whether to overwrite an existing destination file

    Returns:
        Path to the copied file

    Raises:
        ResourceError: If the file cannot be copied
    """
    try:
        # Check if source file exists
        if not os.path.isfile(src_path):
            raise ResourceError(f"Source file does not exist: {src_path}")

        # Create destination directory if needed
        dest_dir = os.path.dirname(dest_path)
        if dest_dir:
            ensure_directory(dest_dir)

        # Check if destination file exists and overwrite flag
        if os.path.exists(dest_path) and not overwrite:
            logger.warning(f"Destination file exists and overwrite=False: {dest_path}")
            return dest_path

        # Copy the file
        shutil.copy2(src_path, dest_path)
        logger.debug(f"Copied file from {src_path} to {dest_path}")
        return dest_path

    except ResourceError:
        raise
    except Exception as e:
        logger.error(f"Failed to copy file from {src_path} to {dest_path}: {e}")
        raise ResourceError(f"File copy error: {e}") from e


def safe_rename(src_path: str, dest_path: str, overwrite: bool = False) -> str:
    """
    Safely rename/move a file, ensuring the destination directory exists.

    Args:
        src_path: Source file path
        dest_path: Destination file path
        overwrite: Whether to overwrite an existing destination file

    Returns:
        Path to the renamed/moved file

    Raises:
        ResourceError: If the file cannot be renamed
    """
    try:
        # Check if source file exists
        if not os.path.exists(src_path):
            raise ResourceError(f"Source path does not exist: {src_path}")

        # Create destination directory if needed
        dest_dir = os.path.dirname(dest_path)
        if dest_dir:
            ensure_directory(dest_dir)

        # Check if destination file exists and overwrite flag
        if os.path.exists(dest_path):
            if not overwrite:
                logger.warning(f"Destination exists and overwrite=False: {dest_path}")
                return dest_path
            else:
                # Handle directory vs file differently
                if os.path.isdir(dest_path):
                    shutil.rmtree(dest_path)
                else:
                    os.remove(dest_path)

        # Rename/move the file
        shutil.move(src_path, dest_path)
        logger.debug(f"Moved {src_path} to {dest_path}")
        return dest_path

    except ResourceError:
        raise
    except Exception as e:
        logger.error(f"Failed to rename/move from {src_path} to {dest_path}: {e}")
        raise ResourceError(f"File rename error: {e}") from e


def copy_directory_contents(
    src_dir: str, dest_dir: str, pattern: str = None
) -> List[str]:
    """
    Copy contents of a directory, optionally filtering by pattern.

    Args:
        src_dir: Source directory path
        dest_dir: Destination directory path
        pattern: Optional glob pattern to filter files

    Returns:
        List of paths to copied files

    Raises:
     ResourceError: If the directory contents cannot be copied
    """
    try:
        # Ensure both directories exist
        if not os.path.isdir(src_dir):
            raise ResourceError(f"Source directory does not exist: {src_dir}")

        ensure_directory(dest_dir)

        copied_files = []

        # Walk through the source directory
        for root, _, files in os.walk(src_dir):
            # Calculate the relative path to preserve directory structure
            rel_path = os.path.relpath(root, src_dir)

            for file in files:
                # Skip files not matching pattern if specified
                if pattern and not _match_pattern(file, pattern):
                    continue

                src_file = os.path.join(root, file)

                # Determine destination path, preserving directory structure
                if rel_path == ".":
                    dest_file = os.path.join(dest_dir, file)
                else:
                    dest_subdir = os.path.join(dest_dir, rel_path)
                    ensure_directory(dest_subdir)
                    dest_file = os.path.join(dest_subdir, file)

                # Copy the file
                shutil.copy2(src_file, dest_file)
                copied_files.append(dest_file)
                logger.debug(f"Copied {src_file} to {dest_file}")

        logger.info(f"Copied {len(copied_files)} files from {src_dir} to {dest_dir}")
        return copied_files

    except ResourceError:
        raise
    except Exception as e:
        logger.error(
            f"Failed to copy directory contents from {src_dir} to {dest_dir}: {e}"
        )
        raise ResourceError(f"Directory copy error: {e}") from e


def _match_pattern(filename: str, pattern: str) -> bool:
    """
    Check if a filename matches a glob-like pattern.

    Args:
        filename: Name of the file to check
        pattern: Glob pattern (e.g., '*.png', '*.jp*g')

    Returns:
        True if the filename matches the pattern, False otherwise
    """
    import fnmatch

    return fnmatch.fnmatch(filename.lower(), pattern.lower())


def generate_unique_id() -> str:
    """
    Generate a unique identifier for resources.

    Returns:
        A unique string identifier
    """
    return str(uuid.uuid4())


def generate_temp_filename(prefix: str = "tmp", suffix: str = "") -> str:
    """
    Generate a unique temporary filename (not a file).

    Args:
        prefix: Prefix for the filename
        suffix: Suffix for the filename (e.g. '.html', '.json')

    Returns:
        A unique filename
    """
    return f"{prefix}_{generate_unique_id()}{suffix}"


def get_file_size(file_path: str) -> int:
    """
    Get the size of a file in bytes.

    Args:
        file_path: Path to the file

    Returns:
        Size of the file in bytes

    Raises:
        ResourceError: If the file does not exist or cannot be accessed
    """
    try:
        if not os.path.isfile(file_path):
            raise ResourceError(f"File does not exist: {file_path}")

        return os.path.getsize(file_path)
    except ResourceError:
        raise
    except Exception as e:
        logger.error(f"Failed to get file size for {file_path}: {e}")
        raise ResourceError(f"File size error: {e}") from e


class ResourceTracker:
    """
    Track and manage temporary resources to ensure proper cleanup.

    This class helps track files and directories created during processing
    and ensures they are properly cleaned up, even if exceptions occur.
    """

    def __init__(self):
        """Initialize a new resource tracker."""
        self.resources = {"files": [], "dirs": []}

    def add_file(self, file_path: str) -> str:
        """
        Add a file to be tracked.

        Args:
            file_path: Path to the file

        Returns:
            The file path for chaining
        """
        if os.path.isfile(file_path):
            self.resources["files"].append(file_path)
        return file_path

    def add_directory(self, dir_path: str) -> str:
        """
        Add a directory to be tracked.

        Args:
            dir_path: Path to the directory

        Returns:
            The directory path for chaining
        """
        if os.path.isdir(dir_path):
            self.resources["dirs"].append(dir_path)
        return dir_path

    def cleanup(
        self, cleanup_files: bool = True, cleanup_dirs: bool = True
    ) -> Dict[str, int]:
        """
        Clean up tracked resources.

        Args:
            cleanup_files: Whether to remove tracked files
            cleanup_dirs: Whether to remove tracked directories

        Returns:
            Dictionary with counts of cleaned resources
        """
        cleaned = {"files": 0, "dirs": 0}

        # Clean up files first
        if cleanup_files:
            for file_path in self.resources["files"]:
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        cleaned["files"] += 1
                        logger.debug(f"Removed temporary file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file {file_path}: {e}")

        # Then clean up directories
        if cleanup_dirs:
            for dir_path in self.resources["dirs"]:
                try:
                    if os.path.isdir(dir_path):
                        shutil.rmtree(dir_path)
                        cleaned["dirs"] += 1
                        logger.debug(f"Removed temporary directory: {dir_path}")
                except Exception as e:
                    logger.warning(
                        f"Failed to remove temporary directory {dir_path}: {e}"
                    )

        # Reset the tracking lists if cleaned
        if cleanup_files:
            self.resources["files"] = []
        if cleanup_dirs:
            self.resources["dirs"] = []

        return cleaned
