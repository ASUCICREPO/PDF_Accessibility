"""
Local Batch Processor for PDF Accessibility Enhancement.

This module provides local/offline batch processing capabilities
complementing the AWS-based PDF accessibility solution.

Features:
- Recursive directory processing with folder structure preservation
- OCR enhancement with Tesseract (via ocrmypdf)
- PDF/UA-1 compliance preparation
- Progress tracking and parallel processing
- JSON summary reports
"""

from .batch_processor import BatchProcessor
from .enhancement_service import EnhancementService
from .ocr_enhancer import OCREnhancer
from .pdfua_enhancer import PDFUAEnhancer

__version__ = "1.0.0"
__all__ = [
    "BatchProcessor",
    "EnhancementService",
    "OCREnhancer",
    "PDFUAEnhancer",
]
