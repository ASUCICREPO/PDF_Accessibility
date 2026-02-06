#!/usr/bin/env python3
"""
OCR Enhancer for PDF Accessibility.

Creates invisible OCR text layers that screen readers can access
while preserving the visual appearance of the document.
"""

import logging
import shutil
import tempfile
import os
from pathlib import Path
from typing import Union

try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("PyMuPDF is required. Install with: pip install PyMuPDF")

try:
    import ocrmypdf
    OCRMYPDF_AVAILABLE = True
except ImportError:
    OCRMYPDF_AVAILABLE = False

try:
    import pikepdf
    PIKEPDF_AVAILABLE = True
except ImportError:
    PIKEPDF_AVAILABLE = False

logger = logging.getLogger(__name__)


class OCREnhancer:
    """
    OCR enhancer that creates invisible searchable text layers.

    Features:
    - Intelligent OCR detection (checks existing text content)
    - Sandwich renderer for invisible text placement
    - Page box normalization for non-standard PDFs
    - Configurable DPI and language settings
    """

    def __init__(
        self,
        text_threshold: int = 100,
        dpi: int = 300,
        language: str = 'eng'
    ):
        """
        Initialize the OCR enhancer.

        Args:
            text_threshold: Minimum avg chars/page to skip OCR (default: 100)
            dpi: DPI for OCR processing (default: 300)
            language: Tesseract language code (default: 'eng')
        """
        if not OCRMYPDF_AVAILABLE:
            raise ImportError(
                "ocrmypdf is required. Install with: pip install ocrmypdf"
            )

        self.text_threshold = text_threshold
        self.dpi = dpi
        self.language = language

        logger.info(
            f"OCREnhancer initialized (DPI: {dpi}, Lang: {language}, "
            f"Threshold: {text_threshold})"
        )

    def needs_ocr(self, pdf_path: Union[str, Path]) -> bool:
        """
        Check if PDF needs OCR by analyzing text content.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            bool: True if OCR is needed, False otherwise
        """
        try:
            pdf_path = Path(pdf_path)
            doc = fitz.open(pdf_path)

            total_pages = len(doc)
            if total_pages == 0:
                doc.close()
                return True

            # Sample first few pages
            sample_pages = min(3, total_pages)
            total_chars = 0

            for page_num in range(sample_pages):
                page = doc[page_num]
                text = page.get_text().strip()
                total_chars += len(text)

            doc.close()

            avg_chars = total_chars / sample_pages
            needs_ocr = avg_chars < self.text_threshold

            logger.info(
                f"Text analysis: {avg_chars:.1f} avg chars/page - "
                f"OCR needed: {needs_ocr}"
            )
            return needs_ocr

        except Exception as e:
            logger.error(f"Error analyzing PDF text: {e}")
            return True

    def enhance_file(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        force_ocr: bool = False,
        **kwargs
    ) -> bool:
        """
        Apply OCR to PDF file if needed.

        Args:
            input_path: Path to the input PDF
            output_path: Path for the enhanced PDF
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

            if not force_ocr and not self.needs_ocr(input_path):
                logger.info("PDF has sufficient text - copying to output")
                shutil.copy2(input_path, output_path)
                return True

            logger.info(f"Starting OCR processing: {input_path}")
            return self._apply_ocr(input_path, output_path, force_ocr=force_ocr)

        except Exception as e:
            logger.error(f"Error in OCR enhancement: {e}")
            return False

    def _apply_ocr(
        self,
        input_path: Path,
        output_path: Path,
        force_ocr: bool = False
    ) -> bool:
        """Apply OCR using ocrmypdf."""
        try:
            # Normalize page boxes for non-standard PDFs
            temp_normalized = None
            if force_ocr and PIKEPDF_AVAILABLE:
                logger.info("Normalizing page boxes before OCR")
                normalized_path = self._normalize_page_boxes(input_path)
                if normalized_path != input_path:
                    temp_normalized = normalized_path
                    input_path = normalized_path

            options = {
                "language": self.language,
                "redo_ocr": force_ocr,
                "force_ocr": False,
                "skip_text": not force_ocr,
                "optimize": 0,
                "output_type": "pdf",
                "pdf_renderer": "sandwich",
                "progress_bar": False,
                "image_dpi": self.dpi,
                "rotate_pages": True,
                "remove_vectors": False,
            }

            ocrmypdf.ocr(input_path, output_path, **options)

            if temp_normalized:
                try:
                    os.unlink(temp_normalized)
                except Exception:
                    pass

            logger.info(f"OCR complete: {output_path}")
            return True

        except ocrmypdf.exceptions.PriorOcrFoundError:
            logger.info("PDF already has OCR text, copying")
            shutil.copy2(input_path, output_path)
            return True

        except ocrmypdf.exceptions.EncryptedPdfError:
            logger.error(f"Cannot process encrypted PDF: {input_path}")
            return False

        except Exception as e:
            logger.error(f"Error applying OCR: {e}")
            return False

    def _normalize_page_boxes(self, input_path: Path) -> Path:
        """
        Normalize PDF page boxes to handle non-standard coordinates.

        Some PDFs have MediaBox with negative origins which causes
        OCR text positioning issues.
        """
        if not PIKEPDF_AVAILABLE:
            return input_path

        try:
            temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
            os.close(temp_fd)

            with pikepdf.open(input_path) as pdf:
                pages_normalized = 0

                for page_num, page in enumerate(pdf.pages):
                    if '/MediaBox' not in page:
                        continue

                    media_box = page.MediaBox
                    x0 = float(media_box[0])
                    y0 = float(media_box[1])
                    x1 = float(media_box[2])
                    y1 = float(media_box[3])

                    if x0 != 0 or y0 != 0:
                        width = x1 - x0
                        height = y1 - y0

                        # Shift content to match normalized coordinates
                        transformation = f"1 0 0 1 {-x0} {-y0} cm\n".encode('latin-1')

                        if '/Contents' in page:
                            contents = page.Contents
                            if isinstance(contents, pikepdf.Array):
                                first_stream = contents[0]
                                old_data = first_stream.read_bytes()
                                first_stream.write(transformation + old_data)
                            else:
                                old_data = contents.read_bytes()
                                contents.write(transformation + old_data)

                        page.MediaBox = pikepdf.Array([0, 0, width, height])

                        for box_name in ['/CropBox', '/TrimBox', '/BleedBox', '/ArtBox']:
                            if box_name in page:
                                box = page[box_name]
                                page[box_name] = pikepdf.Array([
                                    float(box[0]) - x0,
                                    float(box[1]) - y0,
                                    float(box[2]) - x0,
                                    float(box[3]) - y0
                                ])

                        pages_normalized += 1

                pdf.save(temp_path)

            if pages_normalized > 0:
                logger.info(f"Normalized {pages_normalized} pages")
                return Path(temp_path)
            else:
                os.unlink(temp_path)
                return input_path

        except Exception as e:
            logger.warning(f"Could not normalize page boxes: {e}")
            return input_path
