# OCR Pipeline: API Workflow & Post-Processing

## Overview

This document describes the interaction with the Mistral OCR API (`mistral-ocr-latest`) and the post-processing steps for structured text extraction from historical print periodicals.

---

## Mistral OCR API

### API Specifications

- **Endpoint**: `client.ocr.process()`
- **Model**: `mistral-ocr-latest`
- **Type**: Dedicated OCR API (not Chat/Vision API)
- **Input**: PDF files (via signed URL) or images (via Base64 Data-URI)
- **Output**: Structured response with `pages[]` containing `.markdown` per page

### Key Difference from Chat API

The OCR API is a **dedicated document processing endpoint**:
- No prompt engineering required
- No temperature or max_tokens parameters
- Returns structured page-by-page results
- Automatic layout analysis and text extraction

---

## API Workflow

### Step 1: File Upload (PDFs only)

```python
from mistralai import Mistral

client = Mistral(api_key=MISTRAL_API_KEY)

# Upload PDF to Mistral Files API
with open(pdf_path, 'rb') as f:
    uploaded_file = client.files.upload(
        file={
            "file_name": Path(pdf_path).name,
            "content": f
        },
        purpose="ocr"
    )

print(f"Uploaded: {uploaded_file.id}")
```

### Step 2: Get Signed URL

```python
# Get temporary signed URL (valid for 1 hour)
signed_url_response = client.files.get_signed_url(
    file_id=uploaded_file.id,
    expiry=1  # Hours
)

document_url = signed_url_response.url
```

### Step 3: OCR Processing

```python
# Process document with OCR API
response = client.ocr.process(
    model="mistral-ocr-latest",
    document={
        "type": "document_url",
        "document_url": document_url
    },
    include_image_base64=True  # Include embedded images
)
```

### Step 4: Extract Results

```python
# Response structure
for page in response.pages:
    page_number = page.index + 1  # 0-indexed
    markdown_content = page.markdown
    # Optional: page.images (if include_image_base64=True)
```

---

## Image Processing (JPG/PNG)

For single images, use Base64 Data-URI instead of file upload:

```python
import base64

# Read and encode image
with open(image_path, 'rb') as f:
    base64_data = base64.b64encode(f.read()).decode('utf-8')

# Determine MIME type
mime_types = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png'
}
media_type = mime_types[Path(image_path).suffix.lower()]

# Process with OCR API
response = client.ocr.process(
    model="mistral-ocr-latest",
    document={
        "type": "image_url",
        "image_url": f"data:{media_type};base64,{base64_data}"
    }
)
```

---

## Response Structure

### OCRResponse Object

```python
response.pages  # List of Page objects
response.model  # Actual model used (e.g., "mistral-ocr-2512")
```

**Important:** When using `mistral-ocr-latest`, the `response.model` field reveals the actual model version. This is logged and saved in metadata for reproducibility.

### Page Object

| Attribute | Type | Description |
|-----------|------|-------------|
| `index` | int | Page number (0-indexed) |
| `markdown` | str | OCR text in Markdown format |
| `images` | list | Embedded images (if requested) |

### Example Output

The OCR API returns Markdown with automatic structure detection:

```markdown
## Artikel-Überschrift

**Von Hans Müller**

Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

### Unterabschnitt

Weitere Textinhalte...

---

1. Fußnote mit Quellenangabe
2. Weitere Fußnote
```

---

## Post-Processing

### Combine Pages to Document

```python
def combine_pages_to_markdown(pages: list) -> str:
    """Combines multiple pages into a single Markdown document."""
    markdown_parts = []

    for page in pages:
        markdown_parts.append(f"# Seite {page.index + 1}\n")
        markdown_parts.append(page.markdown)
        markdown_parts.append("\n\n---\n\n")

    return "\n".join(markdown_parts)
```

### Convert to Plain Text

```python
import re

def markdown_to_plaintext(markdown: str) -> str:
    """Removes Markdown syntax for plain text output."""
    text = markdown

    # Remove headers
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # Remove bold
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # Remove italic
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    # Remove blockquotes
    text = re.sub(r'^\>\s+', '', text, flags=re.MULTILINE)
    # Remove list markers
    text = re.sub(r'^\-\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
    # Remove links
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    # Remove horizontal rules
    text = re.sub(r'---+', '', text)

    return text.strip()
```

---

## Metadata Extraction

The pipeline extracts structured metadata from OCR output using regex patterns optimized for German historical periodicals:

### Extraction Patterns

```python
def extract_metadata_from_markdown(markdown: str) -> dict:
    metadata = {}

    # Periodical title (first H1)
    match = re.search(r'^#\s+(.+)$', markdown, re.MULTILINE)
    if match:
        metadata['zeitschrift'] = match.group(1).strip()

    # Issue/Volume (German patterns)
    match = re.search(
        r'(Jahrgang|Heft|Ausgabe|Nr\.?)\s*(\d+)',
        markdown,
        re.IGNORECASE
    )
    if match:
        metadata['ausgabe'] = match.group(0).strip()

    # Page number
    match = re.search(r'Seite\s*(\d+)', markdown, re.IGNORECASE)
    if match:
        metadata['seite'] = int(match.group(1))

    # Article titles (H2 and H3)
    h2_titles = re.findall(r'^##\s+(.+)$', markdown, re.MULTILINE)
    h3_titles = re.findall(r'^###\s+(.+)$', markdown, re.MULTILINE)
    metadata['artikel'] = h2_titles + h3_titles

    # Authors (multiple patterns)
    autoren = []
    # Pattern: "Von [Name]" or "Autor: [Name]"
    autoren.extend(re.findall(
        r'(?:Von|Autor|Author):\s*([A-ZÄÖÜ][^\n]+)',
        markdown
    ))
    # Pattern: Name signatures at end of text
    autoren.extend(re.findall(
        r'\n\s*([A-ZÄÖÜ][a-zäöüß]+\s+[A-ZÄÖÜ][a-zäöüß]+)\s*$',
        markdown,
        re.MULTILINE
    ))
    metadata['autoren'] = list(set(autoren))

    # Count footnotes
    metadata['fussnoten_anzahl'] = len(
        re.findall(r'^\d+\.\s+.+$', markdown, re.MULTILINE)
    )

    # Count tables
    table_lines = re.findall(r'^\|.+\|$', markdown, re.MULTILINE)
    metadata['tabellen_anzahl'] = len(
        [l for l in table_lines if '---' not in l]
    ) // 2

    # Word count
    plain_text = markdown_to_plaintext(markdown)
    metadata['word_count'] = len(plain_text.split())

    return metadata
```

---

## Quality Assurance

### Confidence Score Calculation

```python
def calculate_ocr_confidence(markdown: str, metadata: dict) -> float:
    """
    Calculates confidence score (0.0 - 1.0) based on output quality.
    """
    score = 1.0

    # Penalties
    word_count = metadata.get('word_count', 0)
    if word_count < 50:
        score -= 0.3  # Very short text
    elif word_count < 150:
        score -= 0.1  # Short text

    if not metadata.get('artikel'):
        score -= 0.2  # No structure

    if not metadata.get('zeitschrift') and not metadata.get('ausgabe'):
        score -= 0.1  # Missing metadata

    # Penalty for OCR artifacts (unusual characters)
    unusual_chars = len(re.findall(
        r'[^\w\s\.,;:!?\-äöüÄÖÜß()"\'\[\]]',
        markdown
    ))
    if unusual_chars > 50:
        score -= 0.2

    # Bonuses
    if metadata.get('artikel'):
        score += 0.1
    if metadata.get('fussnoten_anzahl', 0) > 0:
        score += 0.05
    if metadata.get('tabellen_anzahl', 0) > 0:
        score += 0.05

    return max(0.0, min(1.0, score))
```

### Validation Checks

```python
def validate_ocr_output(markdown: str, metadata: dict) -> list:
    """
    Checks OCR output for common issues.
    Returns list of warnings.
    """
    warnings = []

    # Empty output
    if not markdown.strip():
        warnings.append("ERROR: Empty OCR output")

    # Very short text
    word_count = metadata.get('word_count', 0)
    if word_count < 20:
        warnings.append(f"WARN: Very little text ({word_count} words)")

    # No structure
    if '##' not in markdown and '**' not in markdown:
        warnings.append("WARN: No structural elements recognized")

    # Markdown syntax errors
    if markdown.count('**') % 2 != 0:
        warnings.append("WARN: Unpaired ** in Markdown")

    # Excessive empty lines (possible layout issues)
    empty_lines = len(re.findall(r'\n\s*\n\s*\n', markdown))
    if empty_lines > 20:
        warnings.append(
            f"WARN: Many empty lines ({empty_lines}), possible structure issues"
        )

    return warnings
```

---

## Retry Logic

### Exponential Backoff

```python
def process_pdf_with_retry(
    pdf_path: str,
    api_key: str,
    max_retries: int = 5,
    base_delay: float = 2.0
) -> dict:
    """Process PDF with automatic retry on failure."""

    for attempt in range(max_retries):
        try:
            return process_pdf_with_ocr(pdf_path, api_key)

        except Exception as e:
            error_str = str(e)

            # Rate limit (429)
            if '429' in error_str:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Rate limit, waiting {delay}s...")
                    time.sleep(delay)
                    continue

            # Server error (500, 503)
            elif any(code in error_str for code in ['500', '503']):
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Server error, waiting {delay}s...")
                    time.sleep(delay)
                    continue

            # Other errors: fail immediately
            raise

    raise ValueError(f"All {max_retries} attempts failed")
```

---

## Output Files

### File Naming

```
{pdf_stem}.md           # Markdown with structure
{pdf_stem}.txt          # Plain text
{pdf_stem}_metadata.json  # Extracted metadata
```

### Save Results

```python
def save_ocr_results(
    pdf_id: str,
    markdown: str,
    plain_text: str,
    metadata: dict,
    output_dir: str
) -> tuple:
    """Saves OCR results to files."""

    os.makedirs(output_dir, exist_ok=True)

    # Markdown
    md_path = os.path.join(output_dir, f"{pdf_id}.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(markdown)

    # Plain text
    txt_path = os.path.join(output_dir, f"{pdf_id}.txt")
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(plain_text)

    # Metadata JSON
    json_path = os.path.join(output_dir, f"{pdf_id}_metadata.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return md_path, txt_path
```

---

## Workflow Diagram

```
┌─────────────────────┐
│  Input File         │
│  (PDF / JPG / PNG)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  PDF?               │
│  ├─ Yes → Upload    │
│  │        → Signed URL
│  └─ No  → Base64    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Mistral OCR API    │
│  client.ocr.process │
│  (no prompts)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Response:          │
│  pages[].markdown   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Combine Pages      │
│  → Full Markdown    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Post-Processing    │
│  ├─ → Plain Text    │
│  ├─ → Metadata      │
│  └─ → Confidence    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Quality Validation │
│  → Warnings List    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Save Files         │
│  ├─ .md             │
│  ├─ .txt            │
│  └─ _metadata.json  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Update SQLite DB   │
│  (Tracking)         │
└─────────────────────┘
```

---

## Performance Expectations

| Metric | Value |
|--------|-------|
| Processing time per page | 5-15 seconds |
| Throughput with 2s delay | ~30-40 pages/minute |
| 1000 pages total time | ~25-40 minutes |
| OCR accuracy (good scans) | 90-95% CAR |
| Structure recognition | >95% |

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Rate limit (429) | Increase `DELAY_SECONDS` in .env |
| Timeout | Increase `TIMEOUT_SECONDS` in .env |
| Low confidence | Check scan quality, verify periodical format |
| Missing metadata | Adjust regex patterns for specific periodical |

### Debugging

```python
# Enable detailed logging
import logging
logging.getLogger('mistralai').setLevel(logging.DEBUG)

# Check response structure
print(f"Pages: {len(response.pages)}")
for page in response.pages:
    print(f"Page {page.index}: {len(page.markdown)} chars")
```

---

**Last Updated**: 2025-12-20
**Version**: 1.2.0
