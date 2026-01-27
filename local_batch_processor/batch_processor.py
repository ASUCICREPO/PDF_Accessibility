#!/usr/bin/env python3
"""
Batch Processor for PDF Accessibility Enhancement.

Provides batch processing capabilities with:
- Recursive directory walking
- Folder structure preservation
- Progress tracking
- Parallel processing support
- Summary reporting
"""

import logging
import json
from pathlib import Path
from typing import Union, Dict, List
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

from .enhancement_service import EnhancementService

logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Batch processor for PDF documents.

    Features:
    - Recursive directory walking
    - Preserves folder structure in output
    - Progress bar (if tqdm available)
    - Parallel processing (ThreadPoolExecutor)
    - JSON summary report
    """

    def __init__(
        self,
        text_threshold: int = 100,
        dpi: int = 300,
        language: str = 'eng'
    ):
        """
        Initialize the batch processor.

        Args:
            text_threshold: Minimum chars/page to skip OCR
            dpi: DPI for OCR processing
            language: OCR language code
        """
        self.service = EnhancementService(
            text_threshold=text_threshold,
            dpi=dpi,
            language=language
        )

    def process_batch(
        self,
        input_dir: Union[str, Path],
        output_dir: Union[str, Path],
        workers: int = 1,
        recursive: bool = True,
        skip_ocr: bool = False,
        force_ocr: bool = False,
        **kwargs
    ) -> Dict:
        """
        Process all PDFs in input directory.

        Args:
            input_dir: Input directory containing PDFs
            output_dir: Output directory for enhanced PDFs
            workers: Number of parallel workers (1 = sequential)
            recursive: Process subdirectories recursively
            skip_ocr: Skip OCR step for all files
            force_ocr: Force OCR even if text exists

        Returns:
            Dict: Summary report with processing statistics
        """
        try:
            input_dir = Path(input_dir)
            output_dir = Path(output_dir)

            if not input_dir.exists():
                logger.error(f"Input directory not found: {input_dir}")
                return {"success": False, "error": "Input directory not found"}

            output_dir.mkdir(parents=True, exist_ok=True)

            # Find all PDFs
            pdf_files = self._find_pdf_files(input_dir, recursive)

            if not pdf_files:
                logger.warning(f"No PDF files found in: {input_dir}")
                return {
                    "success": True,
                    "total_files": 0,
                    "processed": 0,
                    "failed": 0,
                    "message": "No PDF files found"
                }

            logger.info(f"Found {len(pdf_files)} PDF files")
            logger.info(f"Using {workers} worker(s)")

            start_time = datetime.now()

            if workers > 1:
                results = self._process_parallel(
                    pdf_files, input_dir, output_dir,
                    workers, skip_ocr, force_ocr, **kwargs
                )
            else:
                results = self._process_sequential(
                    pdf_files, input_dir, output_dir,
                    skip_ocr, force_ocr, **kwargs
                )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            summary = self._generate_summary(results, duration)
            self._save_summary(output_dir, summary)

            logger.info(
                f"Batch complete: {summary['processed']}/{summary['total_files']} "
                f"successful"
            )
            return summary

        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def _find_pdf_files(self, directory: Path, recursive: bool) -> List[Path]:
        """Find all PDF files in directory."""
        if recursive:
            return sorted(directory.rglob("*.pdf"))
        else:
            return sorted(directory.glob("*.pdf"))

    def _get_output_path(
        self,
        input_file: Path,
        input_dir: Path,
        output_dir: Path
    ) -> Path:
        """Calculate output path preserving folder structure."""
        relative_path = input_file.relative_to(input_dir)
        return output_dir / relative_path

    def _process_sequential(
        self,
        pdf_files: List[Path],
        input_dir: Path,
        output_dir: Path,
        skip_ocr: bool,
        force_ocr: bool,
        **kwargs
    ) -> List[Dict]:
        """Process files sequentially with progress bar."""
        results = []

        if TQDM_AVAILABLE:
            iterator = tqdm(pdf_files, desc="Processing PDFs", unit="file")
        else:
            iterator = pdf_files
            logger.info("Processing files (install tqdm for progress bar)")

        for pdf_file in iterator:
            result = self._process_single_file(
                pdf_file, input_dir, output_dir,
                skip_ocr, force_ocr, **kwargs
            )
            results.append(result)

        return results

    def _process_parallel(
        self,
        pdf_files: List[Path],
        input_dir: Path,
        output_dir: Path,
        workers: int,
        skip_ocr: bool,
        force_ocr: bool,
        **kwargs
    ) -> List[Dict]:
        """Process files in parallel."""
        results = []

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_file = {
                executor.submit(
                    self._process_single_file,
                    pdf_file, input_dir, output_dir,
                    skip_ocr, force_ocr, **kwargs
                ): pdf_file
                for pdf_file in pdf_files
            }

            if TQDM_AVAILABLE:
                iterator = tqdm(
                    as_completed(future_to_file),
                    total=len(pdf_files),
                    desc="Processing PDFs",
                    unit="file"
                )
            else:
                iterator = as_completed(future_to_file)
                logger.info(f"Processing {len(pdf_files)} files with {workers} workers")

            for future in iterator:
                result = future.result()
                results.append(result)

        return results

    def _process_single_file(
        self,
        input_file: Path,
        input_dir: Path,
        output_dir: Path,
        skip_ocr: bool,
        force_ocr: bool,
        **kwargs
    ) -> Dict:
        """Process a single PDF file."""
        start_time = datetime.now()

        try:
            output_path = self._get_output_path(input_file, input_dir, output_dir)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            success = self.service.enhance_document(
                input_file,
                output_path,
                skip_ocr=skip_ocr,
                force_ocr=force_ocr,
                **kwargs
            )

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            return {
                "input_file": str(input_file),
                "output_file": str(output_path),
                "success": success,
                "duration": duration,
                "error": None
            }

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.error(f"Error processing {input_file}: {e}")

            return {
                "input_file": str(input_file),
                "output_file": None,
                "success": False,
                "duration": duration,
                "error": str(e)
            }

    def _generate_summary(self, results: List[Dict], duration: float) -> Dict:
        """Generate summary report from processing results."""
        total_files = len(results)
        successful = sum(1 for r in results if r["success"])
        failed = total_files - successful

        avg_duration = (
            sum(r["duration"] for r in results) / total_files
            if total_files > 0 else 0
        )

        return {
            "success": True,
            "total_files": total_files,
            "processed": successful,
            "failed": failed,
            "total_duration": duration,
            "avg_duration_per_file": avg_duration,
            "successful_files": [
                r["input_file"] for r in results if r["success"]
            ],
            "failed_files": [
                {"file": r["input_file"], "error": r["error"]}
                for r in results if not r["success"]
            ],
            "timestamp": datetime.now().isoformat()
        }

    def _save_summary(self, output_dir: Path, summary: Dict) -> None:
        """Save summary report to JSON file."""
        try:
            summary_file = output_dir / "batch_processing_summary.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            logger.info(f"Saved summary: {summary_file}")
        except Exception as e:
            logger.warning(f"Could not save summary: {e}")
