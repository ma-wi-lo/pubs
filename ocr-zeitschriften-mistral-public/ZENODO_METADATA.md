# Zenodo Upload Metadata

This file contains all metadata needed for uploading this repository to Zenodo.

---

## Basic Information

**Title**:
```
OCR Pipeline for Historical Print Periodicals using Mistral AI
```

**Description**:
```
A Jupyter-based OCR pipeline for batch processing scanned historical periodicals using the Mistral OCR Vision API. This reproducible workflow converts multi-page PDFs and images into structured, searchable text documents while preserving layout structure (headings, paragraphs, footnotes).

Key features include:
- Structured OCR with Markdown formatting
- Automatic PDF splitting for large files (>50 MB or >1000 pages)
- SQLite-based checkpoint system for resumable processing
- Robust error handling with exponential backoff retry logic
- Multiple output formats: Markdown (.md), Plain Text (.txt), and JSON metadata
- Batch processing with progress tracking and cost estimation

Designed for researchers and digital humanities practitioners working with historical periodicals, newspaper archives, magazine collections, and academic journals.

Technical stack: Python 3.8+, Jupyter Notebook, Mistral AI SDK, PyMuPDF, Pillow, SQLite
License: MIT
```

**Version**: `1.0.0`

**Publication Date**: `2025-01-16` (or your upload date)

**Upload Type**: `Software`

---

## Authors

**Author**:
```
Family Name: Lorenz
Given Names: Marco
Affiliation: BBF | Research Library for the History of Education in Berlin
ORCID: 0000-0002-0903-2100
```

---

## Keywords

```
OCR
Optical Character Recognition
Digital Humanities
Historical Periodicals
Print Periodicals
Mistral AI
Computer Vision
Jupyter Notebook
Python
Document Analysis
Text Extraction
Layout Analysis
Reproducible Research
Open Science
Document Processing
Historical Research
```

**Minimum 5-8 keywords recommended, use 10-15 for better discoverability**

---

## License

**License**: `MIT License`

**Reasoning**: Permissive open-source license allowing commercial and academic use with attribution.

---

## Related Identifiers

*Add after upload/publication:*

- **GitHub Repository**: `https://github.com/ma-wi-lo/pubs`
- **Is supplement to**: [Add DOI of related publication if applicable]
- **Is cited by**: [Add DOI of papers using this code]

---

## Communities

Recommended Zenodo communities to join:

1. **Digital Humanities** (if available)
2. **Open Science**
3. **Computational Methods**
4. **BBF | Research Library for the History of Education** (if institutional community exists)

*Search for communities on Zenodo during upload*

---

## Funding

*Optional - Add if applicable:*

```
Funder: [e.g., DFG, EU Horizon, etc.]
Grant Number: [Grant ID]
```

---

## Contributors

*Optional - Add co-authors or supervisors:*

```
Family Name: [NAME]
Given Names: [NAME]
Affiliation: [INSTITUTION]
Type: Supervisor / ProjectLeader / Researcher
```

---

## References

**Software References**:

1. Mistral AI SDK
   - URL: https://mistral.ai/
   - Type: Software dependency

2. Python
   - URL: https://www.python.org/
   - Version: 3.8+

3. Jupyter Notebook
   - URL: https://jupyter.org/

---

## Upload Checklist

Before uploading to Zenodo:

- [x] Update `CITATION.cff` with your actual name and ORCID
- [x] Update `README.md` GitHub URLs with your username
- [x] Verify all placeholder text is replaced (search for `YOUR-`)
- [ ] Test the pipeline on a clean system (fresh virtual environment)
- [ ] Create ZIP archive:
  ```bash
  cd /path/to/parent/directory
  zip -r ocr-mistral-periodicals-v1.0.0.zip ocr-zeitschriften-mistral-public/ -x "*.git*" "*__pycache__*" "*.pyc" "*.DS_Store"
  ```
- [ ] Verify ZIP contents (no .git, no large files, no sensitive data)
- [ ] File size < 50 GB (Zenodo limit)
- [ ] Review README for clarity and completeness

---

## Post-Upload Tasks

After receiving DOI from Zenodo:

1. **Update README.md**:
   - Replace `10.5281/zenodo.XXXXXX` with actual DOI
   - Add Zenodo badge at top

2. **Update CITATION.cff**:
   - Replace `10.5281/zenodo.XXXXXX` with actual DOI

3. **GitHub Release** (if using GitHub):
   - Create GitHub release with tag `v1.0.0`
   - Link to Zenodo DOI in release notes

4. **Documentation**:
   - Add DOI to CV, project website, etc.
   - Include in related publications

---

## Suggested Zenodo Upload Notes

**Additional Notes** (visible on Zenodo landing page):

```
This software package provides a complete, reproducible OCR workflow for digitizing historical print periodicals. It was developed as part of research infrastructure at BBF | Research Library for the History of Education in Berlin.

IMPORTANT NOTES:
- Requires Mistral AI API key (sign up at console.mistral.ai)
- API usage is not free (~$1 USD per 1000 pages as of Jan 2025)
- No sample data included to avoid copyright issues
- Tested with Python 3.8+ on Linux, macOS, and Windows
- For questions or bug reports, please open a GitHub issue

Citation: See CITATION.cff file or use Zenodo's citation export function.
```

---

## Alternative Publishing Options

If Zenodo is not suitable, consider:

1. **GitHub Releases**: Free, version-controlled, citable via Zenodo-GitHub integration
2. **OSF.io**: Open Science Framework, good for preprints + code
3. **Figshare**: Similar to Zenodo, 20 GB free storage
4. **Institutional Repository**: BBF or DIPF may have their own repository

---

**Last Updated**: 2025-01-16
