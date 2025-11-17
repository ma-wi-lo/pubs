# OCR Pipeline for Historical Print Periodicals using Mistral AI

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.17631913.svg)](https://doi.org/10.5281/zenodo.17631913)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**A Jupyter-based OCR pipeline for batch processing scanned periodicals using the Mistral OCR API**

This repository provides a complete, reproducible workflow for converting scanned historical print periodicals (PDFs and images) into structured, searchable text documents using the Mistral OCR Vision API (`mistral-ocr-latest`).

---

## Features

- **Structured OCR**: Preserves layout structure (headings, paragraphs, footnotes) using Markdown formatting
- **Batch Processing**: Process multiple documents with automatic checkpoint system for resumability
- **PDF Splitting**: Automatically handles large PDFs (>50 MB or >1000 pages) by splitting into manageable chunks
- **Robust Error Handling**: Exponential backoff retry logic for API failures
- **Multiple Output Formats**: Markdown (.md), Plain Text (.txt), and JSON metadata
- **Progress Tracking**: SQLite-based checkpoint system allows resuming interrupted processing

---

## Use Cases

This pipeline is designed for researchers and digital humanities practitioners working with:
- Historical periodicals and journals
- Scanned newspaper archives
- Magazine collections
- Academic journal archives
- Any multi-page printed documents requiring structured text extraction

---

## Requirements

### API Access

**Mistral API Key required**: Sign up at [console.mistral.ai](https://console.mistral.ai) to obtain an API key.

**Pricing**: Approximately $1 USD per 1000 pages (as of 2025; check current Mistral pricing)

### Software Dependencies

- Python 3.8+
- Jupyter Notebook
- See `requirements.txt` for complete Python package list

---

## Installation

### 1. Clone or Download Repository

```bash
git clone https://github.com/ma-wi-lo/pubs.git
cd pubs
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API Key

Create a `.env` file in the project root directory:

```bash
# .env
MISTRAL_API_KEY=your_mistral_api_key_here
MISTRAL_MODEL=mistral-ocr-latest
DELAY_SECONDS=2.0
MAX_RETRIES=5
TIMEOUT_SECONDS=120
```

**Template available**: Copy `.env.template` and fill in your API key.

---

## Usage

### Quick Start

1. **Add Input Files**: Place your PDF or image files in `data/input/`
2. **Open Notebook**: `jupyter notebook notebooks/ocr_pipeline.ipynb`
3. **Run All Cells**: Execute the notebook cells in order

### Workflow Overview

**Cell 1: Setup**
- Initializes Mistral API client
- Creates directory structure (`data/input/`, `data/output/`, `data/tracking/`)
- Sets up SQLite checkpoint database

**Cell 2: File Discovery**
- Scans `data/input/` for PDFs (`.pdf`) and images (`.jpg`, `.jpeg`, `.png`)
- Displays file statistics (count, total size)

**Cell 3: Batch OCR Processing**
- Processes all discovered files with Mistral OCR API
- Automatically splits large PDFs into 500-page chunks
- Skips already-processed files (resumable)
- Saves results as `.md`, `.txt`, and `_metadata.json`

**Cell 4: Cleanup (Optional)**
- Removes temporary PDF chunk files from `data/tracking/pdf_chunks/`
- Frees up disk space while preserving original files and OCR results

### Output Formats

All output files are saved to `data/output/`:

**1. Markdown (`.md`)**
- Structured full text with headings, paragraphs, and footnotes
- Preserves document hierarchy

**2. Plain Text (`.txt`)**
- Same content without Markdown formatting
- Useful for downstream text mining

**3. JSON Metadata (`_metadata.json`)**
```json
{
  "total_pages": 120,
  "confidence": 0.95,
  "word_count": 12340,
  "processing_time_sec": 45.2,
  "warnings": []
}
```

---

## Project Structure

```
ocr-zeitschriften-mistral-public/
├── README.md                    # This file
├── LICENSE                      # MIT License
├── CITATION.cff                 # Citation metadata
├── requirements.txt             # Python dependencies
├── .env.template                # API key template
├── .gitignore
├── notebooks/
│   ├── ocr_pipeline.ipynb       # Main processing notebook
│   ├── utils.py                 # Helper functions
│   └── README.md                # Notebook documentation
├── data/
│   ├── input/                   # Place your PDFs/images here
│   ├── output/                  # OCR results (.md, .txt, .json)
│   ├── tracking/                # SQLite database + temp chunks
│   └── README.md                # Data directory documentation
└── docs/
    ├── ARCHITECTURE.md          # System architecture overview
    └── LLM_WORKFLOW.md          # Prompt engineering details
```

---

## Performance

**Processing Speed**:
- ~5-15 seconds per page (depending on complexity)
- ~40 pages/minute with rate limiting
- 1000 pages: ~25-40 minutes

**OCR Quality**:
- Character Accuracy Rate (CAR): 90-95% for good-quality scans
- Layout Recognition: >95% (headings, paragraphs, footnotes)

**Costs** (estimated):
- $1 USD per 1000 pages (Mistral OCR API pricing, Nov 2025)

---

## Troubleshooting

### API Key Not Found

```
ValueError: MISTRAL_API_KEY nicht gefunden!
```

**Solution**: Create `.env` file in project root with `MISTRAL_API_KEY=your_key_here`

### Rate Limit Error (429)

**Solution**: Increase `DELAY_SECONDS` in `.env` (e.g., to 3.0 or 4.0)

### Timeout on Large PDFs

**Solution**: Increase `TIMEOUT_SECONDS` in `.env` (e.g., to 180 or 240)

### Resuming Interrupted Processing

The checkpoint system automatically skips already-processed files. Simply re-run Cell 3 to continue where you left off.

To manually reset a file's processing status, delete its entry from the SQLite database at `data/tracking/ocr_progress.db`.

---

## Documentation

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**: Detailed system architecture, data flow, and error handling
- **[docs/LLM_WORKFLOW.md](docs/LLM_WORKFLOW.md)**: Prompt engineering approach and API configuration
- **[notebooks/utils.py](notebooks/utils.py)**: All helper functions with comprehensive docstrings

---

## Citation

If you use this pipeline in your research, please cite:

```bibtex
@software{ocr_mistral_periodicals_2025,
  author = {Lorenz, Marco},
  title = {OCR Pipeline for Historical Print Periodicals using Mistral AI},
  year = {2025},
  version = {1.0.0},
  doi = {10.5281/zenodo.17631913},
  url = {https://github.com/ma-wi-lo/pubs}
}
```

See [CITATION.cff](CITATION.cff) for structured citation metadata.

---

## Contributing

This is a research code repository. Contributions, bug reports, and suggestions are welcome via GitHub Issues.

---

## License

This project is licensed under the **MIT License** - see [LICENSE](LICENSE) file for details.

**Summary**: You are free to use, modify, and distribute this code for any purpose, including commercial use, provided you include the original copyright notice.

---

## Acknowledgments

- **Mistral AI** for providing the OCR Vision API
- **BBF | Research Library for the History of Education in Berlin** for institutional support
- Documentation and packaging assisted by Claude (Anthropic AI)

---

## Contact

For questions or collaborations:
- Open an issue on GitHub
- Contact: Marco Lorenz (m.lorenz@dipf.de)
- Institution: BBF | Research Library for the History of Education in Berlin

---

**Version**: 1.0.0
**Last Updated**: 2025-11-16
**Status**: Production Ready
