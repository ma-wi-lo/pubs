# Notebooks Directory

This directory contains the main OCR processing pipeline and supporting utilities.

---

## Files

### ocr_pipeline.ipynb

**Main processing notebook** - Complete workflow for batch OCR processing of scanned periodicals.

**Workflow**:
1. **Cell 1**: Setup and initialization (API client, directories, database)
2. **Cell 2**: File discovery (find all PDFs/images in `data/input/`)
3. **Cell 3**: Batch OCR processing (with checkpoint system and retry logic)
4. **Cell 4**: Cleanup (delete temporary PDF chunks to free disk space)

**Usage**:
```bash
jupyter notebook ocr_pipeline.ipynb
```

Or execute non-interactively:
```bash
jupyter execute ocr_pipeline.ipynb
```

---

### utils.py

**Helper functions** for the OCR pipeline.

**Key functions**:
- `init_tracking_database()` - Initialize SQLite checkpoint system
- `prepare_file_for_ocr()` - Handle PDF splitting for large files
- `process_single_pdf()` - Complete OCR workflow for one file
- `get_processing_stats()` - Calculate cost and performance metrics
- `cleanup_temp_files()` - Remove temporary chunk files

All functions include comprehensive docstrings with type hints.

---

## Running the Pipeline

### Interactive Mode (Recommended)

1. Start Jupyter:
   ```bash
   jupyter notebook
   ```

2. Open `ocr_pipeline.ipynb`

3. Run cells sequentially (Shift+Enter)

### Command-Line Mode

Execute all cells:
```bash
cd notebooks
jupyter execute ocr_pipeline.ipynb
```

### Resuming Interrupted Processing

If processing is interrupted:
1. Re-run Cell 3 in the notebook
2. The checkpoint system automatically skips already-processed files
3. Processing continues where it left off

---

## Configuration

All configuration is done via `.env` file in the project root:

```
MISTRAL_API_KEY=your_api_key_here
MISTRAL_MODEL=mistral-ocr-latest
DELAY_SECONDS=2.0
MAX_RETRIES=5
TIMEOUT_SECONDS=120
```

See `.env.template` for a complete example.

---

## Output

Results are saved to `../data/output/`:
- `.md` files - Structured Markdown
- `.txt` files - Plain text
- `_metadata.json` - Processing metadata

Processing state is tracked in `../data/tracking/ocr_progress.db`

---

For detailed documentation, see:
- [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) - System design
- [docs/LLM_WORKFLOW.md](../docs/LLM_WORKFLOW.md) - Prompt engineering details
