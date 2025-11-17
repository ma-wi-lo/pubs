# OCR Pipeline: LLM Workflow & Prompt Engineering

## Overview

This document describes the interaction with the Mistral Pixtral Vision Model for structured OCR processing of historical print periodicals.

---

## Mistral Pixtral Model

### Specifications

- **Model ID**: `mistral-ocr-latest` (or `pixtral-12b-2409`)
- **Type**: Vision-Language Model (VLM)
- **Capabilities**:
  - Optical Character Recognition (OCR)
  - Layout analysis
  - Structure recognition
  - Multilingual text recognition
- **Input**: Base64-encoded images (JPEG, PNG)
- **Output**: Structured text (Markdown, JSON)

### API Configuration

```python
from mistralai import Mistral

client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))

response = client.chat.complete(
    model="mistral-ocr-latest",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url", "image_url": f"data:image/jpeg;base64,{base64_image}"}
            ]
        }
    ],
    temperature=0.0,      # Deterministic
    max_tokens=4096,      # For longer articles
    response_format={"type": "text"}  # Markdown output
)
```

---

## Prompt Design

### Base Prompt: Structured OCR

```markdown
You are a specialized OCR assistant for historical print periodicals.

TASK:
Extract all text from the provided periodical scan while preserving structural hierarchy.

OUTPUT FORMAT: Markdown with the following structure:

# [Periodical Title]
**Issue**: [Year/Month/Number]
**Page**: [Page Number]

---

## Table of Contents
(Only if present on this page)
- [Article Title] - Page X
- [Article Title] - Page Y

---

## [Article Heading]
**Author**: [First Name Last Name]

[Article text - paragraphs separated by blank lines]

### [Subheading if present]

[More text...]

---

**Footnotes**:
1. [Footnote text]
2. [Footnote text]

---

CRITICAL RULES:

1. **Text Accuracy**:
   - Preserve ALL words exactly as printed
   - No modernization of historical orthography
   - Keep period-specific terminology unchanged
   - Retain hyphens and syllable breaks

2. **Structure Recognition**:
   - Main headings as H2 (##)
   - Subheadings as H3 (###)
   - Author lines in bold (**Author**: ...)
   - Numbered footnotes at end

3. **Layout Specifics**:
   - Multi-column layouts: Read left to right, column by column
   - Marginalia: As blockquote (> ...)
   - Image captions: *Italic*
   - Tables: As Markdown tables

4. **Special Cases**:
   - Poetry: Preserve line breaks with double space at line end
   - Quotes: As blockquote (> ...)
   - Lists: As Markdown lists

5. **Uncertainty**:
   - Illegible words: [illegible]
   - Uncertain reading: [possibly: word]
   - Missing page number: [page number not visible]

6. **Metadata Extraction**:
   - Periodical title from header
   - Issue/volume from title page or header
   - Page number from footer or header
   - Author from article head or signature

IMPORTANT: Focus on accuracy over speed. Take special care with Gothic fonts or hard-to-read sections.

Begin OCR processing of the provided scan now.
```

---

## Extended Prompts

### Prompt for Table of Contents

```markdown
You are a specialized OCR assistant for historical periodicals.

SPECIAL TASK: Table of Contents Extraction

Extract the table of contents from the scan and structure it as a Markdown table:

| Title | Author(s) | Page |
|-------|-----------|------|
| [Article Title 1] | [Name] | XX |
| [Article Title 2] | [Name 1, Name 2] | YY |

RULES:
- Preserve titles exactly as printed
- Multiple authors: comma-separated
- If no author listed: "-"
- Page numbers as numbers (no "p." or "page")

Additionally: Extract issue metadata:
- Periodical title
- Volume/issue number
- Publication date
- ISSN (if available)

Output as structured JSON:

{
  "periodical": "Title",
  "issue": "Vol X/Year",
  "date": "Month Year",
  "issn": "XXXX-XXXX",
  "contents": [
    {"title": "...", "authors": ["..."], "page": XX},
    ...
  ]
}
```

### Prompt for Metadata Extraction

```markdown
SPECIAL TASK: Metadata Extraction

Analyze the scan and extract the following metadata as JSON:

{
  "page_type": "cover|contents|article|imprint|advertisement",
  "periodical_title": "...",
  "issue": "...",
  "page_number": XX,
  "article": {
    "title": "...",
    "authors": ["First Last", ...],
    "subtitle": "...",
    "summary": "First 2-3 sentences of article"
  },
  "structural_elements": {
    "headings": ["H2 Title", "H3 Subtitle"],
    "footnote_count": X,
    "image_count": X,
    "table_count": X
  },
  "readability": {
    "print_quality": "good|medium|poor",
    "illegible_areas": ["Description of issues"],
    "special_features": ["Gothic font", "Multi-column", ...]
  }
}

If information is not visible, use `null`.
```

---

## Prompt Strategies for Challenges

### Gothic/Fraktur Fonts

```markdown
NOTE: This scan contains Gothic/Fraktur script.

Pay attention to typical Fraktur characteristics:
- Long ſ (s) vs. round s
- Ligatures: ſt, ch, ck, tz
- Confusion risk: r/n, u/n, s/f

If uncertain: mark as [Fraktur: uncertain].
```

### Multi-Column Layouts

```markdown
LAYOUT: This scan has a multi-column layout.

READING ORDER:
1. Left column completely from top to bottom
2. Right column completely from top to bottom
3. For 3+ columns: left to right

Do NOT mark column transitions - create continuous flowing text.
```

### Poor Scan Quality

```markdown
NOTE: This scan has low print quality.

STRATEGY:
- Use context for illegible words
- Mark truly illegible spots as [illegible]
- When uncertain: [possibly: word?]
- Don't guess - better to mark than transcribe incorrectly
```

---

## Response Parsing

### Markdown Extraction

```python
def parse_ocr_response(response: dict) -> tuple[str, str]:
    """
    Extracts Markdown and plain text from Mistral response.

    Returns:
        (markdown_text, plain_text)
    """
    content = response.choices[0].message.content

    # Use Markdown directly
    markdown_text = content.strip()

    # Plain text: Remove Markdown syntax
    plain_text = markdown_to_plaintext(markdown_text)

    return markdown_text, plain_text

def markdown_to_plaintext(md: str) -> str:
    """Converts Markdown to plain text."""
    import re

    # Remove Markdown syntax
    text = re.sub(r'^#+\s+', '', md, flags=re.MULTILINE)  # Headers
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*(.+?)\*', r'\1', text)  # Italic
    text = re.sub(r'^\>\s+', '', text, flags=re.MULTILINE)  # Blockquotes
    text = re.sub(r'^\-\s+', '', text, flags=re.MULTILINE)  # Lists
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)  # Numbered lists
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)  # Links
    text = re.sub(r'---+', '', text)  # Horizontal rules

    return text.strip()
```

### Metadata Extraction

```python
def extract_metadata_from_markdown(md: str) -> dict:
    """
    Extracts structured metadata from Markdown OCR output.
    """
    import re

    metadata = {}

    # Periodical title (first H1)
    match = re.search(r'^#\s+(.+)$', md, re.MULTILINE)
    if match:
        metadata['periodical'] = match.group(1).strip()

    # Issue
    match = re.search(r'\*\*Issue\*\*:\s*(.+)$', md, re.MULTILINE)
    if match:
        metadata['issue'] = match.group(1).strip()

    # Page number
    match = re.search(r'\*\*Page\*\*:\s*(\d+)', md, re.MULTILINE)
    if match:
        metadata['page'] = int(match.group(1))

    # Article titles (all H2)
    metadata['articles'] = re.findall(r'^##\s+(.+)$', md, re.MULTILINE)

    # Authors
    metadata['authors'] = re.findall(r'\*\*Author\*\*:\s*(.+)$', md, re.MULTILINE)

    # Count footnotes
    metadata['footnote_count'] = len(re.findall(r'^\d+\.\s+.+$', md, re.MULTILINE))

    # Count words
    text = markdown_to_plaintext(md)
    metadata['word_count'] = len(text.split())

    return metadata
```

---

## Quality Assurance

### Confidence Scoring

```python
def calculate_ocr_confidence(markdown: str, metadata: dict) -> float:
    """
    Calculates a confidence score for OCR quality (0.0-1.0).
    """
    score = 1.0

    # Penalty: Many [illegible] marks
    illegible_count = markdown.count('[illegible]')
    score -= min(0.3, illegible_count * 0.05)

    # Penalty: Many [possibly: ...] marks
    possibly_count = markdown.count('[possibly:')
    score -= min(0.2, possibly_count * 0.03)

    # Penalty: Missing metadata
    if not metadata.get('periodical'):
        score -= 0.1
    if not metadata.get('page'):
        score -= 0.1

    # Penalty: Very short text (likely error)
    if metadata.get('word_count', 0) < 50:
        score -= 0.2

    # Bonus: Structured elements found
    if metadata.get('articles'):
        score += 0.05
    if metadata.get('footnote_count', 0) > 0:
        score += 0.05

    return max(0.0, min(1.0, score))
```

### Validation Checks

```python
def validate_ocr_output(markdown: str, metadata: dict) -> list[str]:
    """
    Checks OCR output for common issues.

    Returns:
        List of warnings
    """
    warnings = []

    # Check: Empty output
    if not markdown.strip():
        warnings.append("ERROR: Empty OCR output")

    # Check: Very short text
    word_count = metadata.get('word_count', 0)
    if word_count < 20:
        warnings.append(f"WARN: Very little text ({word_count} words)")

    # Check: No structure recognized
    if '##' not in markdown and '**' not in markdown:
        warnings.append("WARN: No structural elements recognized")

    # Check: Missing metadata
    if not metadata.get('page'):
        warnings.append("WARN: Page number not recognized")

    # Check: High uncertainty
    if markdown.count('[illegible]') > 5:
        warnings.append("WARN: Many illegible areas (>5)")

    # Check: Markdown syntax errors
    if markdown.count('**') % 2 != 0:
        warnings.append("WARN: Unpaired ** in Markdown")

    return warnings
```

---

## Workflow Diagram

```
┌─────────────────┐
│  Scan File      │
│  (PDF/JPG)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Image Prep      │
│ - Load          │
│ - Resize        │
│ - Base64 Encode │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Mistral Pixtral │
│ API Call        │
│ + Prompt        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Parse Response  │
│ - Markdown      │
│ - Metadata      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Quality Check   │
│ - Confidence    │
│ - Validation    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Save Output     │
│ - .md File      │
│ - .txt File     │
│ - JSON Metadata │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Update Tracking │
│ (SQLite)        │
└─────────────────┘
```

---

## Iterative Improvement

### Prompt Tuning Strategy

1. **Baseline**: 10-20 test scans with base prompt
2. **Manual Review**: Compare OCR vs. original
3. **Error Analysis**: Categorize errors
   - Structure errors (incorrect hierarchy)
   - Text errors (wrong characters)
   - Layout errors (column order)
   - Metadata errors (missing extraction)
4. **Prompt Adjustment**: Specific instructions for common errors
5. **A/B Testing**: Compare old vs. new prompt
6. **Production**: Roll out at >95% accuracy

### Feedback Loop

```python
def log_ocr_feedback(scan_id: str, issue_type: str, description: str):
    """
    Logs manual corrections for prompt improvement.
    """
    with sqlite3.connect('data/tracking/ocr_feedback.db') as conn:
        conn.execute("""
            INSERT INTO feedback (scan_id, issue_type, description, timestamp)
            VALUES (?, ?, ?, ?)
        """, (scan_id, issue_type, description, datetime.now()))
```

---

## Best Practices

1. **Temperature 0.0**: Deterministic behavior for reproducibility
2. **Large max_tokens**: 4096+ for longer articles (better too much than truncated)
3. **Increase timeout**: Vision API slower than text-only (120s instead of 60s)
4. **Rate limiting**: 2.0s delay between calls (Mistral API limits)
5. **Error handling**: Exponential backoff for 429/500 errors
6. **Logging**: Detailed logs for debugging (request ID, processing time)
7. **Checkpoint**: Save after each scan (resumable after interruption)
8. **Manual review**: Spot-check results (min. 5% of scans)

---

## Expected Performance

### Processing Time

- **Single page**: 5-15 seconds (depending on complexity)
- **Rate limiting**: 2.0s delay → ~30-40 pages/minute
- **1000 pages**: ~25-40 minutes pure processing time

### OCR Accuracy

- **Target**: >95% Character Accuracy Rate (CAR)
- **Realistic**: 90-95% for good-quality scans
- **Challenges**: Gothic fonts, poor scans → 80-90%

### Structure Recognition

- **Headings**: >95% accuracy
- **Authors**: >90% accuracy
- **Footnotes**: >85% accuracy (often challenging)
- **Multi-column layouts**: 80-90% correct order

---

## Production Monitoring

### Key Metrics to Track

```python
{
  "total_pages_processed": 1500,
  "avg_processing_time_sec": 8.3,
  "avg_confidence_score": 0.93,
  "error_rate": 0.02,
  "estimated_cost_usd": 1.50
}
```

### Quality Assurance Checklist

- [ ] Spot-check 5% of processed pages manually
- [ ] Verify metadata extraction accuracy
- [ ] Check structure preservation (headings, footnotes)
- [ ] Validate text accuracy against sample
- [ ] Review flagged low-confidence outputs
- [ ] Document any systematic errors for prompt tuning

---

**Last Updated**: 2025-01-16
**Version**: 1.0.0
