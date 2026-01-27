# Local Batch Processor for PDF Accessibility

A local/offline batch processing tool for PDF accessibility enhancement. This module complements the AWS-based PDF accessibility solution by enabling:

- **Offline processing** without AWS infrastructure
- **Pre-processing** before cloud upload
- **Development/testing** workflows
- **High-volume batch processing** with folder structure preservation

## Features

- **OCR Enhancement**: Adds invisible searchable text layers using Tesseract (via ocrmypdf)
- **PDF/UA-1 Preparation**: Adds compliance metadata and markers for accessibility
- **Batch Processing**: Process entire directory trees with folder structure preservation
- **Progress Tracking**: Visual progress bar with tqdm
- **Parallel Processing**: Multi-threaded processing for faster throughput
- **Summary Reports**: JSON reports with processing statistics

## Installation

### Prerequisites

1. **Python 3.8+**
2. **Tesseract OCR** (system dependency)

   ```bash
   # macOS
   brew install tesseract

   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr

   # Windows
   # Download from: https://github.com/UB-Mannheim/tesseract/wiki
   ```

3. **Ghostscript** (required by ocrmypdf)

   ```bash
   # macOS
   brew install ghostscript

   # Ubuntu/Debian
   sudo apt-get install ghostscript
   ```

### Python Dependencies

```bash
cd local_batch_processor
pip install -r requirements.txt
```

## Usage

### Command Line Interface

**Process a single PDF:**

```bash
python -m local_batch_processor.cli process input.pdf output.pdf
```

**Batch process a directory:**

```bash
python -m local_batch_processor.cli batch input_folder/ output_folder/
```

**With options:**

```bash
# Process with 4 parallel workers
python -m local_batch_processor.cli batch input/ output/ --workers 4

# Skip OCR (only apply PDF/UA metadata)
python -m local_batch_processor.cli batch input/ output/ --skip-ocr

# Force OCR even if text exists
python -m local_batch_processor.cli batch input/ output/ --force-ocr

# Set custom DPI for OCR
python -m local_batch_processor.cli batch input/ output/ --dpi 400

# Use different OCR language
python -m local_batch_processor.cli batch input/ output/ --ocr-lang deu
```

### Python API

```python
from local_batch_processor import BatchProcessor, EnhancementService

# Single file processing
service = EnhancementService(text_threshold=100, dpi=300)
success = service.enhance_document(
    input_path="input.pdf",
    output_path="output.pdf",
    title="My Document",
    author="Author Name",
    language="en-US"
)

# Batch processing
processor = BatchProcessor(text_threshold=100, dpi=300)
summary = processor.process_batch(
    input_dir="./pdfs",
    output_dir="./enhanced",
    workers=4,
    recursive=True
)

print(f"Processed: {summary['processed']}/{summary['total_files']}")
print(f"Failed: {summary['failed']}")
```

## Processing Pipeline

1. **OCR Enhancement** (if needed)
   - Analyzes PDF text content
   - Applies OCR using sandwich renderer (invisible text behind visible content)
   - Normalizes non-standard page boxes for accurate text positioning

2. **PDF/UA-1 Preparation**
   - Strips orphan tags that interfere with accessibility tools
   - Adds PDF/UA-1 compliance metadata
   - Sets document properties (title, author, language)
   - Marks document for manual tagging workflow

## Output Structure

```
output_folder/
├── subfolder1/
│   ├── document1.pdf
│   └── document2.pdf
├── subfolder2/
│   └── document3.pdf
└── batch_processing_summary.json
```

The folder structure from the input directory is preserved in the output.

## Summary Report

After batch processing, a `batch_processing_summary.json` file is created:

```json
{
  "success": true,
  "total_files": 100,
  "processed": 98,
  "failed": 2,
  "total_duration": 1234.5,
  "avg_duration_per_file": 12.3,
  "successful_files": ["file1.pdf", "file2.pdf", ...],
  "failed_files": [
    {"file": "bad.pdf", "error": "Encrypted PDF"},
    {"file": "corrupt.pdf", "error": "Invalid PDF structure"}
  ],
  "timestamp": "2024-01-15T10:30:00"
}
```

## Integration with AWS Solution

This local batch processor can be used alongside the AWS-based solution:

1. **Pre-processing**: Process PDFs locally before uploading to S3
2. **Testing**: Verify accessibility enhancements locally before cloud deployment
3. **Offline workflow**: Process PDFs when AWS infrastructure is not available
4. **High-volume batch jobs**: Process large collections locally with parallel workers

## Troubleshooting

### "ocrmypdf is not installed"

Install Tesseract OCR and the Python package:

```bash
# Install Tesseract (system)
brew install tesseract  # macOS

# Install Python package
pip install ocrmypdf
```

### "Cannot process encrypted PDF"

The processor cannot handle password-protected PDFs. Remove protection before processing.

### "OCR text positioning is incorrect"

Use the `--force-ocr` flag to regenerate the text layer with corrected positioning:

```bash
python -m local_batch_processor.cli process input.pdf output.pdf --force-ocr
```

## License

This module is part of the PDF Accessibility Solutions project. See the main repository LICENSE for details.
