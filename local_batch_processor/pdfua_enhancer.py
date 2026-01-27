#!/usr/bin/env python3
"""
PDF/UA Enhancer for accessibility compliance.

Prepares PDFs for PDF/UA-1 compliance by:
- Stripping orphan tags that interfere with proper tagging
- Adding required metadata and compliance markers
- Setting document properties (title, author, language)
"""

import logging
import re
from pathlib import Path
from typing import Union, Optional
from datetime import datetime

try:
    import pikepdf
    from pikepdf import Pdf, Name, String, Dictionary, Array
except ImportError:
    raise ImportError("pikepdf is required. Install with: pip install pikepdf")

logger = logging.getLogger(__name__)


class PDFUAEnhancer:
    """
    PDF/UA enhancer for accessibility compliance preparation.

    Features:
    - Orphan tag stripping for clean Acrobat workflow
    - PDF/UA-1 metadata and compliance flags
    - Document property management
    - Structure tree cleanup after OCR
    """

    def __init__(self):
        """Initialize the PDF/UA enhancer."""
        logger.info("PDFUAEnhancer initialized")

    def enhance_file(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        title: Optional[str] = None,
        author: Optional[str] = None,
        language: str = "en-US",
        ocr_performed: bool = False,
        **kwargs
    ) -> bool:
        """
        Apply PDF/UA-1 compliance enhancements.

        Args:
            input_path: Path to the input PDF
            output_path: Path for the enhanced PDF
            title: Document title (default: from filename)
            author: Document author (default: None)
            language: Document language (default: "en-US")
            ocr_performed: Whether OCR was just performed

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

            logger.info(f"Loading PDF: {input_path}")
            document = pikepdf.open(input_path)

            self._enhance(document, input_path, title, author, language, ocr_performed)

            logger.info(f"Saving enhanced PDF: {output_path}")
            document.save(output_path)
            document.close()

            logger.info(f"PDF/UA enhancement complete: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error in PDF/UA enhancement: {e}")
            return False

    def _enhance(
        self,
        document: pikepdf.Pdf,
        input_path: Path,
        title: Optional[str],
        author: Optional[str],
        language: str,
        ocr_performed: bool = False
    ) -> None:
        """Apply PDF/UA-1 enhancements."""
        # Clean up tag structure
        if ocr_performed:
            self._remove_incomplete_struct_tree(document)
        else:
            pages_cleaned = self._strip_orphan_tags(document)
            if pages_cleaned > 0:
                logger.info(f"Stripped orphan tags from {pages_cleaned} pages")

        # Set title
        if not title:
            title = self._extract_title(document, input_path)

        # Update metadata and add compliance markers
        self._update_metadata(document, title, author, language)
        self._add_pdfua_compliance(document, language)

        logger.info("Applied PDF/UA-1 enhancements")

    def _remove_incomplete_struct_tree(self, document: pikepdf.Pdf) -> None:
        """
        Remove incomplete StructTreeRoot but preserve marked content.

        After OCR, we remove orphan structure references while keeping
        the marked content operators that Acrobat needs for manual tagging.
        """
        logger.info("Removing incomplete StructTreeRoot...")

        if Name.StructTreeRoot in document.Root:
            del document.Root[Name.StructTreeRoot]
            logger.info("Removed StructTreeRoot")

        pages_cleaned = 0
        for page in document.pages:
            if Name.StructParents in page:
                del page[Name.StructParents]
                pages_cleaned += 1

        if pages_cleaned > 0:
            logger.info(f"Removed StructParents from {pages_cleaned} pages")

        logger.info("Preserved marked content for Acrobat tagging")

    def _strip_orphan_tags(self, document: pikepdf.Pdf) -> int:
        """
        Strip orphan tagged content that interferes with tag tree creation.

        Returns:
            int: Number of pages cleaned
        """
        logger.info("Starting orphan tag cleanup...")
        pages_cleaned = 0

        try:
            # Check for valid structure
            if Name.StructTreeRoot in document.Root:
                logger.info("Document has StructTreeRoot - preserving")
                return 0

            logger.info("No StructTreeRoot - stripping orphan tags")

            for page in document.pages:
                if Name.StructParents in page:
                    del page[Name.StructParents]
                    pages_cleaned += 1

                try:
                    if Name.Contents in page:
                        contents = page.Contents
                        if isinstance(contents, pikepdf.Array):
                            for stream in contents:
                                self._strip_marked_content(stream)
                        else:
                            self._strip_marked_content(contents)
                except Exception as e:
                    logger.debug(f"Could not clean stream: {e}")

            if pages_cleaned > 0:
                logger.info(f"Removed orphan StructParents from {pages_cleaned} pages")

        except Exception as e:
            logger.warning(f"Error stripping orphan tags: {e}")

        return pages_cleaned

    def _strip_marked_content(self, stream) -> bool:
        """Strip marked content operators from a stream."""
        try:
            content_bytes = stream.read_raw_bytes()

            try:
                content_str = content_bytes.decode('utf-8', errors='ignore')
            except Exception:
                content_str = content_bytes.decode('latin-1', errors='ignore')

            if not any(op in content_str for op in [' BMC', ' BDC', ' EMC']):
                return False

            # Remove marked content operators
            content_str = re.sub(r'/\w+\s+(?:<<[^>]*>>\s+)?BDC\s*', '', content_str)
            content_str = re.sub(r'/\w+\s+BMC\s*', '', content_str)
            content_str = re.sub(r'EMC\s*', '', content_str)

            stream.write(
                content_str.encode('latin-1', errors='ignore'),
                filter=pikepdf.Name.FlateDecode
            )
            return True

        except Exception as e:
            logger.debug(f"Could not strip marked content: {e}")
            return False

    def _extract_title(self, document: pikepdf.Pdf, input_path: Path) -> str:
        """Extract or generate document title."""
        try:
            with document.open_metadata() as meta:
                title = meta.get("dc:title")
                if title and title.strip():
                    return str(title).strip()
        except Exception:
            pass

        # Fallback to filename
        title = input_path.stem.replace("_", " ").replace("-", " ")
        return title.title().strip()

    def _update_metadata(
        self,
        document: pikepdf.Pdf,
        title: str,
        author: Optional[str],
        language: str
    ) -> None:
        """Update document metadata."""
        try:
            with document.open_metadata(set_pikepdf_as_editor=False) as meta:
                if title:
                    meta["dc:title"] = title
                if author:
                    meta["dc:creator"] = author
                meta["dc:language"] = language
                meta["xmp:CreateDate"] = datetime.now().isoformat()
                meta["pdf:Producer"] = "Local Batch Processor for PDF Accessibility"
        except Exception as e:
            logger.warning(f"Error updating metadata: {e}")

    def _add_pdfua_compliance(self, document: pikepdf.Pdf, language: str) -> None:
        """Add PDF/UA-1 compliance markers."""
        # Mark document for tagging
        if Name.MarkInfo not in document.Root:
            document.Root.MarkInfo = Dictionary()

        document.Root.MarkInfo[Name.Marked] = True
        document.Root.MarkInfo[Name.Suspects] = True

        # Set language
        document.Root[Name.Lang] = String(language)

        # Add PDF/UA-1 OutputIntent
        output_intent = Dictionary(
            Type=Name.OutputIntent,
            S=Name.GTS_PDFUA1,
            OutputConditionIdentifier=String("PDF/UA-1"),
            Info=String("PDF for Universal Accessibility"),
            RegistryName=String("http://www.color.org")
        )

        if Name.OutputIntents not in document.Root:
            document.Root.OutputIntents = Array()

        # Check for duplicates
        pdfua_exists = any(
            intent.get(Name.S) == Name.GTS_PDFUA1
            for intent in document.Root.OutputIntents
            if isinstance(intent, Dictionary)
        )

        if not pdfua_exists:
            document.Root.OutputIntents.append(output_intent)

        # Add XMP metadata
        try:
            with document.open_metadata() as meta:
                meta["pdfuaid:part"] = "1"
        except Exception as e:
            logger.warning(f"Error adding XMP metadata: {e}")
