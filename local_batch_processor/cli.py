#!/usr/bin/env python3
"""
CLI for Local Batch PDF Accessibility Enhancement.

Provides command-line interface for:
- Single file processing
- Batch processing with folder structure preservation
"""

import logging
import sys
from pathlib import Path
from typing import Optional

try:
    import typer
    from rich.console import Console
    from rich.logging import RichHandler
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    import argparse

from .enhancement_service import EnhancementService
from .batch_processor import BatchProcessor

if RICH_AVAILABLE:
    app = typer.Typer(
        name="pdf-batch",
        help="Local Batch PDF Accessibility Enhancement Tool",
        add_completion=False
    )
    console = Console()


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO

    if RICH_AVAILABLE:
        logging.basicConfig(
            level=level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True, console=console)]
        )
    else:
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )


if RICH_AVAILABLE:
    @app.command()
    def process(
        input_path: Path = typer.Argument(..., help="Input PDF file"),
        output_path: Path = typer.Argument(..., help="Output PDF file"),
        title: Optional[str] = typer.Option(None, "--title", "-t", help="Document title"),
        author: Optional[str] = typer.Option(None, "--author", "-a", help="Document author"),
        language: str = typer.Option("en-US", "--language", "-l", help="Document language"),
        skip_ocr: bool = typer.Option(False, "--skip-ocr", help="Skip OCR processing"),
        force_ocr: bool = typer.Option(False, "--force-ocr", help="Force OCR even if text exists"),
        text_threshold: int = typer.Option(100, "--text-threshold", help="Min chars/page to skip OCR"),
        dpi: int = typer.Option(300, "--dpi", help="DPI for OCR"),
        ocr_language: str = typer.Option("eng", "--ocr-lang", help="Tesseract language code"),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
    ):
        """Process a single PDF file."""
        setup_logging(verbose)

        console.print("\n[bold]PDF Accessibility Enhancement[/bold]")
        console.print(f"Input:  {input_path}")
        console.print(f"Output: {output_path}\n")

        if not input_path.exists():
            console.print(f"[red]Error: Input file not found: {input_path}[/red]")
            raise typer.Exit(code=1)

        try:
            service = EnhancementService(
                text_threshold=text_threshold,
                dpi=dpi,
                language=ocr_language
            )

            success = service.enhance_document(
                input_path=input_path,
                output_path=output_path,
                title=title,
                author=author,
                language=language,
                skip_ocr=skip_ocr,
                force_ocr=force_ocr
            )

            if success:
                console.print(f"\n[green]✓ Success![/green] Saved to: {output_path}")
                raise typer.Exit(code=0)
            else:
                console.print("\n[red]✗ Enhancement failed[/red]")
                raise typer.Exit(code=1)

        except typer.Exit:
            raise
        except Exception as e:
            console.print(f"\n[red]✗ Error:[/red] {e}")
            raise typer.Exit(code=1)

    @app.command()
    def batch(
        input_dir: Path = typer.Argument(..., help="Input directory"),
        output_dir: Path = typer.Argument(..., help="Output directory"),
        workers: int = typer.Option(1, "--workers", "-w", help="Parallel workers (1=sequential)"),
        recursive: bool = typer.Option(True, "--recursive/--no-recursive", help="Process subdirs"),
        skip_ocr: bool = typer.Option(False, "--skip-ocr", help="Skip OCR for all files"),
        force_ocr: bool = typer.Option(False, "--force-ocr", help="Force OCR"),
        text_threshold: int = typer.Option(100, "--text-threshold", help="Min chars/page"),
        dpi: int = typer.Option(300, "--dpi", help="DPI for OCR"),
        ocr_language: str = typer.Option("eng", "--ocr-lang", help="Tesseract language"),
        verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
    ):
        """Process multiple PDF files preserving folder structure."""
        setup_logging(verbose)

        console.print("\n[bold]Batch PDF Processing[/bold]")
        console.print(f"Input:   {input_dir}")
        console.print(f"Output:  {output_dir}")
        console.print(f"Workers: {workers}")
        console.print(f"Recursive: {recursive}\n")

        if not input_dir.exists():
            console.print(f"[red]Error: Input directory not found: {input_dir}[/red]")
            raise typer.Exit(code=1)

        try:
            processor = BatchProcessor(
                text_threshold=text_threshold,
                dpi=dpi,
                language=ocr_language
            )

            summary = processor.process_batch(
                input_dir=input_dir,
                output_dir=output_dir,
                workers=workers,
                recursive=recursive,
                skip_ocr=skip_ocr,
                force_ocr=force_ocr
            )

            if summary.get("success"):
                console.print("\n[bold]Summary:[/bold]")
                console.print(f"  Total:      {summary['total_files']}")
                console.print(f"  [green]Success:[/green]    {summary['processed']}")
                console.print(f"  [red]Failed:[/red]     {summary['failed']}")
                console.print(f"  Duration:   {summary['total_duration']:.1f}s")
                console.print(f"  Avg/file:   {summary['avg_duration_per_file']:.1f}s")

                if summary['failed'] > 0:
                    console.print("\n[yellow]Failed files:[/yellow]")
                    for failed in summary['failed_files']:
                        console.print(f"  - {failed['file']}: {failed['error']}")

                console.print(f"\n[green]✓ Complete![/green]")
                console.print(f"Summary: {output_dir}/batch_processing_summary.json")

                raise typer.Exit(code=0 if summary['failed'] == 0 else 1)
            else:
                console.print(f"\n[red]✗ Failed:[/red] {summary.get('error')}")
                raise typer.Exit(code=1)

        except typer.Exit:
            raise
        except Exception as e:
            console.print(f"\n[red]✗ Error:[/red] {e}")
            raise typer.Exit(code=1)

    @app.command()
    def version():
        """Display version information."""
        console.print("\n[bold]Local Batch PDF Accessibility Enhancement[/bold]")
        console.print("Version: 1.0.0")
        console.print("\nFeatures:")
        console.print("  - OCR with Tesseract (ocrmypdf)")
        console.print("  - PDF/UA-1 compliance preparation")
        console.print("  - Batch processing with folder preservation")
        console.print("  - Parallel processing support\n")

    def main():
        """Entry point for CLI."""
        app()

else:
    # Fallback for systems without typer/rich
    def main():
        """Simple argparse-based CLI fallback."""
        parser = argparse.ArgumentParser(
            description="Local Batch PDF Accessibility Enhancement"
        )
        subparsers = parser.add_subparsers(dest="command", help="Commands")

        # Process command
        process_parser = subparsers.add_parser("process", help="Process single PDF")
        process_parser.add_argument("input_path", type=Path, help="Input PDF")
        process_parser.add_argument("output_path", type=Path, help="Output PDF")
        process_parser.add_argument("--skip-ocr", action="store_true")
        process_parser.add_argument("--force-ocr", action="store_true")
        process_parser.add_argument("--verbose", "-v", action="store_true")

        # Batch command
        batch_parser = subparsers.add_parser("batch", help="Batch process PDFs")
        batch_parser.add_argument("input_dir", type=Path, help="Input directory")
        batch_parser.add_argument("output_dir", type=Path, help="Output directory")
        batch_parser.add_argument("--workers", "-w", type=int, default=1)
        batch_parser.add_argument("--skip-ocr", action="store_true")
        batch_parser.add_argument("--force-ocr", action="store_true")
        batch_parser.add_argument("--verbose", "-v", action="store_true")

        args = parser.parse_args()
        setup_logging(getattr(args, 'verbose', False))

        if args.command == "process":
            service = EnhancementService()
            success = service.enhance_document(
                args.input_path, args.output_path,
                skip_ocr=args.skip_ocr, force_ocr=args.force_ocr
            )
            sys.exit(0 if success else 1)

        elif args.command == "batch":
            processor = BatchProcessor()
            summary = processor.process_batch(
                args.input_dir, args.output_dir,
                workers=args.workers,
                skip_ocr=args.skip_ocr, force_ocr=args.force_ocr
            )
            sys.exit(0 if summary.get("success") and summary.get("failed", 0) == 0 else 1)

        else:
            parser.print_help()
            sys.exit(1)


if __name__ == "__main__":
    main()
