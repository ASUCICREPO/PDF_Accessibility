# Copyright 2025 Amazon.com, Inc. or its affiliates.
# SPDX-License-Identifier: Apache-2.0

"""
Bedrock client for AI text and image analysis.

This module provides a client for interacting with AWS Bedrock for multimodal AI capabilities.
"""

import boto3
import os
from datetime import datetime
from typing import Optional

from content_accessibility_utility_on_aws.utils.logging_helper import setup_logger
from content_accessibility_utility_on_aws.utils.usage_tracker import SessionUsageTracker
from content_accessibility_utility_on_aws.utils.image_utils import resize_image

# Set up module-level logger
logger = setup_logger(__name__)


class AltTextGenerationError(Exception):
    """Exception raised when alt text generation fails."""


class BedrockClient:
    """Client for interacting with AWS Bedrock for multimodal AI capabilities.

    Attributes:
        model_id: The Bedrock model ID to use
        profile: AWS credentials profile name
        client: Boto3 Bedrock runtime client
        MAX_IMAGE_SIZE: Maximum allowed image size in bytes
    """

    # Maximum image size in bytes (4MB)
    MAX_IMAGE_SIZE = 4_000_000

    def __init__(
        self,
        model_id: str = "us.amazon.nova-lite-v1:0",
        profile: Optional[str] = None,
    ):
        """
        Initialize the Bedrock client.

        Args:
            model_id: The ID of the Bedrock model to use
            profile: AWS profile name to use for authentication
        """
        self.model_id = model_id
        self.profile = profile
        try:
            # Create a boto3 session with the provided profile
            if profile:
                try:
                    # Try to create a session with the provided profile
                    session = boto3.Session(profile_name=profile)
                    logger.debug(f"Using AWS profile: {profile}")
                except Exception as profile_error:
                    # If profile doesn't exist or other error, try default credentials
                    logger.warning(
                        f"Couldn't use AWS profile '{profile}', falling back to default credentials: {profile_error}"
                    )
                    session = boto3.Session()
            else:
                # No profile specified, use default credentials
                session = boto3.Session()

            self.client = session.client("bedrock-runtime")
            logger.debug(
                f"Initialized Bedrock client with model: {model_id}, profile: {profile}"
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Bedrock client: {e}")
            raise

    def generate_text(
        self, prompt: str, purpose: str = "general", max_tokens: int = 500
    ) -> str:
        """
        Generate text using the Bedrock model.

        Args:
            prompt: The prompt to send to the model
            purpose: The purpose of the call (e.g., 'alt_text_generation', 'table_remediation')
            max_tokens: Maximum number of tokens to generate

        Returns:
            The generated text

        Raises:
            AltTextGenerationError: If text generation fails
        """
        start_time = datetime.now()

        try:
            # Estimate input tokens
            input_tokens = SessionUsageTracker.estimate_tokens(prompt)

            # Invoke the model
            response = self.client.converse(
                modelId=self.model_id,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "text": prompt,
                            }
                        ],
                    }
                ],
                inferenceConfig={
                    "maxTokens": max_tokens,
                },
            )

            # Extract the generated text
            generated_text = ""
            if (
                "output" in response
                and "message" in response["output"]
                and "content" in response["output"]["message"]
                and len(response["output"]["message"]["content"]) > 0
            ):
                generated_text = response["output"]["message"]["content"][0]["text"]

                # Track token usage
                end_time = datetime.now()
                processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
                output_tokens = SessionUsageTracker.estimate_tokens(generated_text)

                try:
                    # Track the usage in the session tracker
                    usage_tracker = SessionUsageTracker.get_instance()
                    usage_tracker.track_bedrock_call(
                        model_id=self.model_id,
                        purpose=purpose,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        processing_time_ms=processing_time_ms,
                    )
                    logger.debug(
                        f"Tracked Bedrock call: purpose={purpose}, input_tokens={input_tokens}, output_tokens={output_tokens}"
                    )
                except Exception as track_error:
                    logger.warning(f"Failed to track Bedrock usage: {track_error}")

                return generated_text
            else:
                logger.warning("No content in Bedrock response")
                raise AltTextGenerationError("No content in Bedrock response")

        except Exception as e:
            logger.warning(f"Error generating text with Bedrock: {e}")
            raise AltTextGenerationError(
                f"Failed to generate text with Bedrock: {str(e)}"
            )

    def generate_alt_text_for_image(
        self, image_path: str, prompt: str, max_tokens: int = 500
    ) -> str:
        """
        Generate alt text for an image using multimodal capabilities.

        Args:
            image_path: Path to the image file
            prompt: The prompt to send to the model
            max_tokens: Maximum number of tokens to generate

        Returns:
            The generated alt text

        Raises:
            AltTextGenerationError: If alt text generation fails
            FileNotFoundError: If the image file is not found
        """
        start_time = datetime.now()
        input_tokens = (
            SessionUsageTracker.estimate_tokens(prompt) + 1000
        )  # Add 1000 tokens to account for image
        try:
            # Check if image exists
            if not os.path.exists(image_path):
                logger.warning(f"Image file not found: {image_path}")
                raise FileNotFoundError(f"Image file not found: {image_path}")

            # Check image size and resize if needed
            temp_image_path = None
            try:
                image_size = os.path.getsize(image_path)
                if image_size > self.MAX_IMAGE_SIZE:
                    logger.warning(
                        f"Image size {image_size} bytes exceeds limit of {self.MAX_IMAGE_SIZE}, resizing"
                    )

                    temp_image_path = resize_image(
                        image_path, max_size=self.MAX_IMAGE_SIZE
                    )
                    if temp_image_path and temp_image_path != image_path:
                        logger.info(
                            f"Image resized successfully: {os.path.getsize(temp_image_path)} bytes"
                        )
                        image_path = temp_image_path
                    else:
                        logger.warning(
                            "Image resizing did not produce a new file, using original"
                        )
            except Exception as resize_error:
                logger.warning(
                    f"Failed to resize large image: {str(resize_error)}, attempting with original"
                )

            # Read and encode the image
            try:
                with open(image_path, "rb") as image_file:
                    image_data = image_file.read()

            finally:
                # Clean up temporary file if created
                if (
                    temp_image_path
                    and temp_image_path != image_path
                    and os.path.exists(temp_image_path)
                ):
                    try:
                        os.unlink(temp_image_path)
                        logger.debug(
                            f"Removed temporary resized image: {temp_image_path}"
                        )
                    except Exception as e:
                        logger.debug(f"Failed to remove temporary file: {e}")

    
            content = [
                {
                    "text": prompt,
                },
                {
                    "image": {
                        "format": self._get_media_type(image_path)
                        .split("/")[1]
                        .lower(),
                        "source": {"bytes": image_data},
                    },
                },
            ]

            # Invoke the model using converse API
            response = self.client.converse(
                modelId=self.model_id,
                messages=[
                    {
                        "role": "user",
                        "content": content,
                    }
                ],
                inferenceConfig={
                    "maxTokens": max_tokens,
                },
            )

            # Extract the generated text
            if (
                "output" in response
                and "message" in response["output"]
                and "content" in response["output"]["message"]
                and len(response["output"]["message"]["content"]) > 0
            ):
                generated_text = response["output"]["message"]["content"][0]["text"]

                # Track token usage
                end_time = datetime.now()
                processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
                output_tokens = SessionUsageTracker.estimate_tokens(generated_text)

                try:
                    # Track the usage in the session tracker
                    usage_tracker = SessionUsageTracker.get_instance()
                    usage_tracker.track_bedrock_call(
                        model_id=self.model_id,
                        purpose="alt_text_generation",
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        processing_time_ms=processing_time_ms,
                    )
                    logger.debug(
                        f"Tracked Bedrock image analysis call: input_tokens={input_tokens}, output_tokens={output_tokens}"
                    )
                except Exception as track_error:
                    logger.warning(f"Failed to track Bedrock usage: {track_error}")

                return generated_text
            else:
                logger.warning("No content in Bedrock response")
                raise AltTextGenerationError("No content in Bedrock response")

        except FileNotFoundError:
            # Re-raise file not found errors
            raise
        except Exception as e:
            logger.warning(f"Error generating alt text with Bedrock: {e}")
            raise AltTextGenerationError(f"Failed to generate alt text: {str(e)}")

    def _get_media_type(self, file_path: str) -> str:
        """
        Get the media type based on file extension.

        Args:
            file_path: Path to the file

        Returns:
            Media type string
        """
        extension = os.path.splitext(file_path)[1].lower()

        if extension == ".jpg" or extension == ".jpeg":
            return "image/jpeg"
        elif extension == ".png":
            return "image/png"
        elif extension == ".gif":
            return "image/gif"
        elif extension == ".webp":
            return "image/webp"
        else:
            # Default to png
            return "image/png"
