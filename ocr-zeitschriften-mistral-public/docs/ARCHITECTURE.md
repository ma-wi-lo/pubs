# OCR Pipeline for Historical Periodicals: Architecture Documentation

## Project Overview

**Purpose**: Full-text OCR of historical print periodicals using the Mistral OCR API (`mistral-ocr-latest`)

**Version**: 1.1.0

**Institution**: BBF | Research Library for the History of Education in Berlin

---

## System Architecture

### Components

```
ocr-zeitschriften-mistral-public/
├── data/
│   ├── input/              # Source files (PDF, JPG, PNG) - not versioned
│   ├── output/             # OCR results (.md, .txt, .json)
│   └── tracking/           # SQLite database + temporary PDF chunks
├── docs/
│   ├── ARCHITECTURE.md     # This file (system architecture)
│   └── LLM_WORKFLOW.md     # API workflow & post-processing
├── notebooks/
│   ├── ocr_pipeline.ipynb  # Main processing notebook (4 cells)
│   └── utils.py            # Helper functions (~1100 lines)
├── .env                    # API keys (not versioned)
├── .env.template           # Template for .env
├── .gitignore
├── LICENSE
├── CITATION.cff
└── requirements.txt
```

### Data Flow

```
[Input Files: PDF/JPG/PNG]
        │
        ▼
[File Discovery] ─────────────────────────────┐
        │                                      │
        ▼                                      │
[Large PDF?] ─── Yes ──► [Split into 500-page chunks]
        │                         │
        No                        │
        │◄────────────────────────┘
        ▼
[Upload to Mistral Files API]
        │
        ▼
[Get Signed URL]
        │
        ▼
[Mistral OCR API: client.ocr.process()]
        │
        ▼
[Response: pages[] with .markdown]
        │
        ▼
[Combine pages → Full Markdown]
        │
        ▼
[Extract Metadata + Quality Score]
        │
        ▼
[Save: .md + .txt + _metadata.json]
        │
        ▼
[Update SQLite Tracking DB]
```

---

## Technology Stack

### Core Dependencies

- **Mistral AI SDK**: `mistralai` (OCR API)
- **PDF Handling**: `PyMuPDF` (fitz) for splitting large PDFs
- **Data Management**: `sqlite3` (stdlib)
- **Environment**: `python-dotenv`
- **Logging**: Python `logging` stdlib

### API Configuration

```python
# Model
MODEL = "mistral-ocr-latest"  # Dedicated OCR model

# Rate Limiting (configurable via .env)
DELAY_SECONDS = 2.0      # Delay between API calls
MAX_RETRIES = 5          # Retry attempts on failure
TIMEOUT_SECONDS = 120    # API timeout
```

### API Workflow

The pipeline uses Mistral's dedicated OCR API (not the Chat API):

```python
from mistralai import Mistral

client = Mistral(api_key=MISTRAL_API_KEY)

# 1. Upload PDF file
uploaded_file = client.files.upload(
    file={"file_name": "document.pdf", "content": file_bytes},
    purpose="ocr"
)

# 2. Get signed URL (valid for 1 hour)
signed_url = client.files.get_signed_url(
    file_id=uploaded_file.id,
    expiry=1
)

# 3. Process with OCR API
response = client.ocr.process(
    model="mistral-ocr-latest",
    document={"type": "document_url", "document_url": signed_url.url},
    include_image_base64=True
)

# 4. Extract results
for page in response.pages:
    markdown_text = page.markdown
    page_index = page.index
```

---

## Data Model

### Input Formats

| Format | Handling |
|--------|----------|
| PDF | Upload via Files API → Signed URL → OCR |
| JPG/JPEG/PNG | Base64 Data-URI → OCR |

### PDF Splitting

Large PDFs are automatically split to avoid API limits:

| Trigger | Threshold |
|---------|-----------|
| File size | > 50 MB |
| Page count | > 1000 pages |

**Chunk size**: 500 pages, max 45 MB per chunk

**Storage**: `data/tracking/pdf_chunks/` (temporary, cleaned up after processing)

### Output Formats

#### 1. Markdown (.md)

Combined output from all pages with page separators:

```markdown
# Seite 1

[OCR content from page 1...]

---

# Seite 2

[OCR content from page 2...]

---
```

#### 2. Plain Text (.txt)

Same content with Markdown syntax removed.

#### 3. Metadata JSON (_metadata.json)

```json
{
  "zeitschrift": "Periodical Title",
  "ausgabe": "Jahrgang 5, Heft 3",
  "artikel": ["Article 1", "Article 2"],
  "autoren": ["Author Name"],
  "fussnoten_anzahl": 12,
  "tabellen_anzahl": 2,
  "word_count": 5432,
  "total_pages": 24,
  "api_usage": {
    "pages_processed": 24
  }
}
```

---

## SQLite Tracking Schema

```sql
CREATE TABLE ocr_progress (
    pdf_id TEXT PRIMARY KEY,
    source_file TEXT NOT NULL,
    total_pages INTEGER,
    status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'error')),
    output_path_md TEXT,
    output_path_txt TEXT,
    metadata_json TEXT,
    confidence REAL,
    warnings TEXT,
    error_message TEXT,
    processing_start TIMESTAMP,
    processing_end TIMESTAMP,
    processing_duration_sec REAL,
    api_pages_used INTEGER,
    api_bytes_used INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Status Flow

```
pending → processing → completed
                    ↘ error
```

---

## Error Handling

### Retry Logic

| Error Type | Handling |
|------------|----------|
| 429 Rate Limit | Exponential backoff (2s, 4s, 8s, 16s, 32s) |
| 500/503 Server Error | Exponential backoff |
| Other errors | Immediate failure, logged to DB |

### Error Recovery

- **Checkpoint system**: Already-processed files are skipped on restart
- **Resume**: Re-run Cell 3 to continue after interruption
- **Manual reset**: Delete entry from SQLite to reprocess a file

---

## Quality Assurance

### Confidence Score (0.0 - 1.0)

| Factor | Impact |
|--------|--------|
| Word count < 50 | -0.3 |
| Word count < 150 | -0.1 |
| No article headings (H2/H3) | -0.2 |
| No periodical/issue metadata | -0.1 |
| Many unusual characters (>50) | -0.2 |
| Articles found | +0.1 |
| Footnotes found | +0.05 |
| Tables found | +0.05 |

### Validation Warnings

- Empty OCR output
- Very short text (<20 words)
- No structural elements
- Unpaired Markdown syntax
- Excessive empty lines

---

## Notebook Structure

### Cell 1: Setup

- Install dependencies
- Initialize Mistral client
- Create directories
- Initialize SQLite database
- Load configuration from `.env`

### Cell 2: File Discovery

- Scan `data/input/` recursively
- Collect file metadata (path, type, size)
- Output: `FILES_TO_PROCESS` list

### Cell 3: Batch OCR Processing

- Loop through files
- Skip already-completed files (checkpoint)
- Split large PDFs if needed
- Process with OCR API
- Save results and update database

### Cell 4: Cleanup

- Delete temporary PDF chunks
- Display storage statistics
- Preserve: database, results, original files

---

## Configuration (.env)

```bash
# Required
MISTRAL_API_KEY=your_api_key_here

# Optional (with defaults)
MISTRAL_MODEL=mistral-ocr-latest
DELAY_SECONDS=2.0
MAX_RETRIES=5
TIMEOUT_SECONDS=120
```

---

## Performance

| Metric | Value |
|--------|-------|
| Processing time per page | 5-15 seconds |
| Rate with delay | ~30-40 pages/minute |
| 1000 pages | ~25-40 minutes |
| Estimated cost | ~$1 USD per 1000 pages |

---

## Security & Privacy

- API keys stored in `.env` (not versioned)
- Files uploaded temporarily to Mistral for OCR
- Signed URLs expire after 1 hour
- Original files remain local

---

## Contact & Responsibility

**Institution**: BBF | Research Library for the History of Education in Berlin

**License**: MIT License

---

**Last Updated**: 2025-12-19
**Version**: 1.1.0
