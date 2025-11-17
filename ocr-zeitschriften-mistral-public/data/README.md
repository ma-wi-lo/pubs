# Data Directory

This directory contains all input files, output results, and processing metadata for the OCR pipeline.

## Directory Structure

```
data/
├── input/              # Place your PDFs and images here
├── output/             # OCR results (.md, .txt, .json)
└── tracking/           # SQLite database and temporary chunks
```

---

## input/

**Purpose**: Place your scanned periodicals (PDFs or images) in this directory for processing.

**Supported formats**:
- PDF (`.pdf`) - Multi-page documents
- Images (`.jpg`, `.jpeg`, `.png`) - Single pages

**Note**: This directory is empty in the published repository. No sample data is included to avoid copyright issues.

---

## output/

**Purpose**: Stores OCR results after processing.

**Output formats**:
- `.md` files - Markdown-formatted full text with structure
- `.txt` files - Plain text without Markdown syntax
- `_metadata.json` files - Processing metadata (confidence scores, page counts, warnings)

**Example**:
```
output/
├── periodical_1962.md
├── periodical_1962.txt
├── periodical_1962_metadata.json
├── large_periodical_chunk1.md
└── large_periodical_chunk2.md
```

Large PDFs (>50 MB or >1000 pages) are automatically split into chunks during processing.

---

## tracking/

**Purpose**: Internal processing state and temporary files.

**Contents**:
- `ocr_progress.db` - SQLite database tracking processing status (checkpoint system)
- `pdf_chunks/` - Temporary PDF chunk files (created when large PDFs are split)

**Note**: The `pdf_chunks/` directory can be safely deleted after processing to free up disk space (see Cell 4 in the notebook). The SQLite database should be preserved to maintain processing history.

---

## Privacy & Copyright

**Important**: Do not commit your input files or OCR results to version control if they contain:
- Copyrighted material without permission
- Personal data subject to GDPR
- Unpublished research material

The `.gitignore` file is configured to exclude `input/` and `output/` directories by default.

---

## Data Management Best Practices

1. **Backup**: Regularly backup your `output/` directory before major processing runs
2. **Organization**: Use descriptive filenames for input files (e.g., `periodical_year_issue.pdf`)
3. **Cleanup**: Run Cell 4 in the notebook periodically to delete temporary chunks
4. **Monitoring**: Check the SQLite database to track processing progress and costs

---

For more information, see the main [README.md](../README.md) or [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md).
