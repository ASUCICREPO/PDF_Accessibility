#!/usr/bin/env python3
"""
Enhancement Service for PDF Accessibility.

Orchestrates the two-step enhancement pipeline:
1. OCR enhancement (if needed)
2. PDF/UA-1 compliance preparation
"""

import logging
import tempfile
from pathlib import Path
from typing import Union, Optional

from .ocr_enhancer import OCREnhancer
from .pdfua_enhancer import PDFUAEnhancer

logger = logging.getLogger(__name__)


class EnhancementService:
    """
    Orchestration service for PDF enhancement pipeline.

    Pipeline:
    1. OCR Enhancement (adds invisible searchable text)
    2. PDF/UA-1 Enhancement (metadata and compliance markers)
    """

    def __init__(
        self,
        text_threshold: int = 100,
        dpi: int = 300,
        language: str = 'eng'
    ):
        """
        Initialize the enhancement service.

        Args:
            text_threshold: Minimum chars/page to skip OCR (default: 100)
            dpi: DPI for OCR processing (default: 300)
            language: OCR language code (default: 'eng')
        """
        self.ocr_enhancer = OCREnhancer(
            text_threshold=text_threshold,
            dpi=dpi,
            language=language
        )
        self.pdfua_enhancer = PDFUAEnhancer()

        logger.info("EnhancementService initialized")

    def enhance_document(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        title: Optional[str] = None,
        author: Optional[str] = None,
        language: str = "en-US",
        skip_ocr: bool = False,
        force_ocr: bool = False,
        **kwargs
    ) -> bool:
        """
        Enhance a PDF document through the complete pipeline.

        Args:
            input_path: Path to input PDF
            output_path: Path for enhanced PDF
            title: Document title (default: from filename)
            author: Document author (default: None)
            language: Document language (default: "en-US")
            skip_ocr: Skip OCR step entirely (default: False)
            force_ocr: Force OCR even if text exists (default: False)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            input_path = Path(input_path)
            output_path = Path(output_path)

            if not input_path.exists():
                logger.error(f"Input file not found: {input_path}")
                return False

            output_path.parent.mkdir(parents=True, exist_ok=True)

            logger.info(f"Starting enhancement: {input_path}")
            logger.info(f"Output: {output_path}")

            # Step 1: OCR Enhancement
            if skip_ocr:
                logger.info("Skipping OCR (skip_ocr=True)")
                ocr_output = input_path
                ocr_performed = False
            else:
                with tempfile.NamedTemporaryFile(
                    suffix='.pdf',
                    delete=False,
                    dir=output_path.parent
                ) as tmp_file:
                    ocr_output = Path(tmp_file.name)

                logger.info("Step 1/2: OCR Enhancement")
                ocr_success = self.ocr_enhancer.enhance_file(
                    input_path,
                    ocr_output,
                    force_ocr=force_ocr
                )

                if not ocr_success:
                    logger.error("OCR enhancement failed")
                    if ocr_output.exists():
                        ocr_output.unlink()
                    return False

                ocr_performed = True

            # Step 2: PDF/UA Enhancement
            logger.info("Step 2/2: PDF/UA-1 Enhancement")
            pdfua_success = self.pdfua_enhancer.enhance_file(
                ocr_output,
                output_path,
                title=title,
                author=author,
                language=language,
                ocr_performed=ocr_performed
            )

            # Cleanup temporary OCR file
            if not skip_ocr and ocr_output != input_path:
                if ocr_output.exists():
                    ocr_output.unlink()

            if not pdfua_success:
                logger.error("PDF/UA enhancement failed")
                return False

            logger.info(f"Enhancement complete: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error in enhancement pipeline: {e}")
            import traceback
            traceback.print_exc()
            return False
