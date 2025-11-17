# OCR Pipeline for Historical Periodicals: Architecture Documentation

## Project Overview

**Purpose**: Full-text OCR of historical print periodicals with structural text analysis using Mistral Pixtral Vision AI

**Version**: 1.0.0

**Institution**: BBF | Research Library for the History of Education in Berlin

---

## System Architecture

### Components

```
ocr-zeitschriften-mistral-public/
├── data/
│   ├── input/              # Scans (PDF, JPG) - not versioned
│   ├── output/             # OCR results (.txt, .md, .json)
│   └── tracking/           # SQLite state management
├── docs/
│   ├── ARCHITECTURE.md     # This file
│   └── LLM_WORKFLOW.md     # Prompt engineering & workflow
├── notebooks/
│   ├── ocr_pipeline.ipynb  # Main processing pipeline
│   └── utils.py            # Shared functions
├── .env                    # API keys (not versioned)
├── .gitignore
├── LICENSE
├── CITATION.cff
└── requirements.txt
```

### Data Flow

```
[Scanned Files]
    ↓ (Batch Loading)
[Image Preprocessing]
    ↓ (Base64 Encoding)
[Mistral Pixtral API]
    ↓ (Vision + OCR)
[Structure Extraction]
    ↓ (Markdown Formatting)
[Output: .txt + .md + .json]
```

---

## Technology Stack

### Core Dependencies

- **Mistral AI SDK**: `mistralai` (Pixtral Vision Model)
- **Image Processing**: `Pillow` (PIL)
- **PDF Handling**: `PyMuPDF` (fitz) or `pdf2image`
- **Data Management**: `pandas`, `sqlite3`
- **Environment**: `python-dotenv`
- **Logging**: Python `logging` stdlib

### API Configuration

```python
MODEL = "mistral-ocr-latest"  # Or pixtral-12b-2409
TEMPERATURE = 0.0  # Deterministic for reproducibility
MAX_TOKENS = 4096  # For longer articles
TIMEOUT = 120      # Seconds (Vision API can be slow)
```

### Rate Limiting

- **Delay**: 2.0s between API calls (configurable)
- **Retry Logic**: Exponential backoff (5 attempts)
- **Checkpoint**: SQLite-based progress tracking

---

## Data Model

### Input Formats

1. **PDF Files**: Multi-page periodical issues
   - Conversion to images (page-by-page)
   - Metadata: Filename, page count, file size

2. **JPG/PNG Files**: Single-page scans
   - Direct processing
   - Metadata: Filename, resolution, file size

### Output Formats

#### 1. Markdown (.md)
```markdown
# [Periodical Title]
**Issue**: [Year/Month]
**Page**: [Page Number]

---

## [Article Heading]
**Author**: [Name]

[Article text with paragraphs...]

### [Subheading]
[More text...]

---
**Footnotes**:
1. [Footnote text]
```

#### 2. Plain Text (.txt)
- Structured text output without Markdown syntax
- Hierarchy via blank lines/indentation

#### 3. Metadata (JSON)
```json
{
  "scan_id": "periodical_1965_03_p012",
  "source_file": "periodical_1965_03.pdf",
  "page_number": 12,
  "processed_date": "2025-01-16T12:00:00",
  "structure": {
    "title": "Article Title",
    "authors": ["Author 1", "Author 2"],
    "sections": 3,
    "footnotes": 5,
    "word_count": 1234
  },
  "confidence": 0.95,
  "processing_time_sec": 8.3
}
```

---

## OCR Strategy

### Structure Recognition

Mistral Pixtral identifies the following elements:

1. **Periodical Metadata**
   - Periodical title
   - Issue/volume number
   - Publication date
   - ISSN (if available)

2. **Table of Contents**
   - Article overview with page numbers
   - Author index

3. **Article Structure**
   - Main heading (H1)
   - Subheadings (H2, H3)
   - Author line
   - Body text with paragraphs
   - Block quotes
   - Lists (bulleted/numbered)

4. **Footnotes & References**
   - Numbering
   - Association with text passages
   - Bibliographic details

5. **Special Cases**
   - Image captions
   - Tables
   - Poetry (preserve line breaks)
   - Multi-column layouts

### Common Challenges for Historical Periodicals

1. **Typography**
   - Fraktur/Gothic fonts (occasionally in historical citations)
   - Period-specific typefaces
   - Variable print quality

2. **Layout**
   - Multi-column articles
   - Marginalia and annotations
   - Changing layouts across issues

3. **Language**
   - Historical orthography
   - Period-specific terminology
   - Abbreviations and sigla

---

## Batch Processing & Checkpointing

### SQLite Tracking Schema

```sql
CREATE TABLE ocr_progress (
    pdf_id TEXT PRIMARY KEY,
    source_file TEXT NOT NULL,
    page_number INTEGER,
    status TEXT CHECK(status IN ('pending', 'processing', 'completed', 'error')),
    output_path_md TEXT,
    output_path_txt TEXT,
    metadata_json TEXT,
    error_message TEXT,
    processing_start TIMESTAMP,
    processing_end TIMESTAMP,
    api_call_duration_sec REAL,
    confidence REAL,
    total_pages INTEGER
);
```

### Batch Strategy

1. **Scan Discovery**: Load all PDFs/images from `data/input/`
2. **PDF → Images**: Convert multi-page PDFs to individual images
3. **Checkpoint Check**: Skip already-processed scans
4. **Batch Processing**:
   - Individual API calls (1 image = 1 call)
   - Rate limiting with delays
   - Exponential backoff on errors
5. **Incremental Save**: Save results after each scan
6. **Resume Capability**: Automatically resume after interruption

---

## Error Handling

### Error Cases

1. **API Errors**
   - 429 Rate Limit: Exponential backoff (up to 5 attempts)
   - 500 Server Error: Retry with backoff
   - Timeout: Increased timeout limit for large images

2. **Image Errors**
   - Invalid format: Skip with warning
   - Too large: Downsample before API call
   - Corrupt: Log error, proceed to next image

3. **OCR Quality Issues**
   - Confidence score < threshold: Flag for manual review
   - Incomplete structure: Fallback to plain text
   - Empty pages: Mark, but don't treat as error

### Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/tracking/ocr_processing.log'),
        logging.StreamHandler()
    ]
)
```

---

## Performance Optimization

### Image Processing

- **Compression**: JPEG quality 85% for API transmission
- **Resolution**: Max 2048px longest side (balance OCR quality vs. API limits)
- **Caching**: Cache base64-encoded images on retry

### API Optimization

- **Connection Pooling**: `requests.Session()` for persistent connections
- **Batch Strategy**: Currently 1 image per call (evaluate multi-image later)
- **Timeout Tuning**: Dynamic timeout based on image size

### Memory Efficiency

- **Streaming**: Process large PDFs page-by-page
- **Cleanup**: Delete temp images after processing
- **Incremental Write**: Write results immediately, don't accumulate in memory

---

## Extensibility

### Planned Features (Post-MVP)

1. **Quality Control**
   - Confidence scoring per page
   - Automatic duplicate detection
   - OCR diff tool for manual corrections

2. **Enhanced Metadata**
   - Named Entity Recognition for authors/organizations
   - Thematic classification
   - Linkage with authority files (e.g., GND IDs)

3. **Export Formats**
   - TEI-XML for digital editions
   - JSON-LD for Linked Open Data
   - Full-text search index (Elasticsearch/Whoosh)

4. **UI/Monitoring**
   - Web dashboard for progress monitoring
   - Batch job scheduler
   - Quality review interface

---

## Security & Privacy

### API Keys

- `.env` file (not versioned)
- Environment variable: `MISTRAL_API_KEY`
- No hard-coded keys in code

### Data Handling

- **Input**: Scans remain local (sent to Mistral API only for OCR)
- **Privacy**: Check copyright status of historical periodicals
- **Backup**: Regular backups of `data/output/` and `data/tracking/`

---

## Testing Strategy

### MVP Testing

1. **Sample Set**: 10-20 representative pages
2. **Manual Validation**: OCR accuracy vs. ground truth
3. **Structure Check**: Markdown rendering in viewer
4. **Edge Cases**: Tables, poetry, multi-column layouts

### Production Readiness

- Error Rate < 5%
- OCR Accuracy > 95% (Character Error Rate)
- Processing Time < 15s per page (average)

---

## Contact & Responsibility

**Institution**: BBF | Research Library for the History of Education in Berlin

**License**: MIT License (see LICENSE file)

**Citation**: See CITATION.cff for structured citation metadata

---

**Last Updated**: 2025-01-16
**Version**: 1.0.0
