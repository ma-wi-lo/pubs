# Pipeline Review - Code-basierte Beobachtungen

**Datum:** 2025-12-19
**Methode:** Direkte Code-Analyse von `ocr_pipeline.ipynb` und `utils.py` (ohne Dokumentation)

---

## 1. Projektstruktur

```
ocr-zeitschriften-mistral-public/
├── notebooks/
│   ├── ocr_pipeline.ipynb    # Haupt-Notebook (4 Zellen)
│   └── utils.py              # Hilfsfunktionen (~1120 Zeilen)
├── data/
│   ├── input/                # Quelldateien (PDFs, Images)
│   ├── output/               # OCR-Ergebnisse (.md, .txt, .json)
│   └── tracking/             # SQLite DB + temporäre PDF-Chunks
├── docs/
│   ├── ARCHITECTURE.md
│   ├── LLM_WORKFLOW.md
│   └── CODING_INSTRUCTIONS.md
└── requirements.txt
```

---

## 2. Pipeline-Ablauf (ocr_pipeline.ipynb)

### Cell 1: Setup
**Zweck:** Initialisierung aller Komponenten

**Aktionen:**
- `pip install -r ../requirements.txt`
- Imports (os, json, logging, pathlib, dotenv, mistralai)
- Import von `utils.py` Funktionen
- Logging-Setup (INFO-Level, StreamHandler)
- API-Key aus `.env` laden
- Mistral-Client initialisieren
- Projekt-Pfade definieren (PROJECT_ROOT, DATA_INPUT, DATA_OUTPUT, DATA_TRACKING)
- Verzeichnisse erstellen (falls nicht vorhanden)
- Konfiguration aus `.env`: DELAY_SECONDS, MAX_RETRIES, TIMEOUT_SECONDS
- SQLite-Datenbank initialisieren (`init_tracking_database`)

**Konfigurierbare Parameter:**
| Variable | Default | Quelle |
|----------|---------|--------|
| MISTRAL_MODEL | mistral-ocr-latest | .env |
| DELAY_SECONDS | 2.0 | .env |
| MAX_RETRIES | 5 | .env |
| TIMEOUT_SECONDS | 120 | .env |

### Cell 2: File Discovery
**Zweck:** Alle verarbeitbaren Dateien finden

**Unterstützte Formate:**
- PDF: `.pdf`
- Images: `.jpg`, `.jpeg`, `.png`

**Aktionen:**
- Rekursive Suche in `DATA_INPUT`
- Metadaten sammeln: path, filename, type, size_mb, extension
- Fehlerbehandlung für nicht-zugängliche Dateien (Symlinks, Permissions)
- Statistik-Output (Anzahl PDFs, Images, Gesamtgröße)

**Output-Variable:** `FILES_TO_PROCESS` (Liste von Dicts)

### Cell 3: Batch OCR Processing
**Zweck:** Hauptverarbeitung aller Dateien

**Ablauf pro Datei:**
1. **Skip-Check:** Bereits in DB als 'completed'? → Überspringen
2. **Prepare:** `prepare_file_for_ocr()` - Splitting falls nötig
3. **OCR:** `process_single_pdf()` für jeden Chunk
4. **Aggregate:** Ergebnisse zusammenfassen

**Splitting-Logik (in utils.py):**
- Trigger: >50 MB ODER >1000 Seiten
- Chunk-Größe: 500 Seiten, max 45 MB
- Output: `data/tracking/pdf_chunks/`

**API-Workflow:**
1. Lokale PDF → Upload via `client.files.upload(purpose="ocr")`
2. Signed URL holen via `client.files.get_signed_url(expiry=1)`
3. OCR via `client.ocr.process()`

**Retry-Logic:**
- Rate Limit (429): Exponential Backoff (2s, 4s, 8s...)
- Server Error (500, 503): Exponential Backoff
- Andere Fehler: Sofortiger Abbruch

**Output pro Datei:**
- `{pdf_id}.md` - Markdown mit Seitenstruktur
- `{pdf_id}.txt` - Plain Text
- `{pdf_id}_metadata.json` - Extrahierte Metadaten

### Cell 4: Cleanup
**Zweck:** Temporäre Dateien löschen

**Was wird gelöscht:**
- PDF-Chunks in `data/tracking/pdf_chunks/`

**Was bleibt erhalten:**
- SQLite-Datenbank
- OCR-Ergebnisse in `data/output/`
- Original-PDFs in `data/input/`

**Features:**
- Dry-Run Modus verfügbar
- Speicherstatistik vor/nach Cleanup
- Kann unabhängig von Cell 1 ausgeführt werden

---

## 3. utils.py - Funktionsübersicht

### PDF Utilities
| Funktion | Beschreibung |
|----------|--------------|
| `get_pdf_info(pdf_path)` | Seiten, Größe, needs_split |
| `split_pdf(pdf_path, output_dir, max_pages=500)` | PDF in Chunks teilen |

### File Encoding
| Funktion | Beschreibung |
|----------|--------------|
| `encode_file_to_base64(file_path)` | Datei → Base64 String |
| `get_media_type(file_path)` | Extension → MIME-Type |

### Mistral OCR API
| Funktion | Beschreibung |
|----------|--------------|
| `process_pdf_with_ocr(pdf_path, api_key, ...)` | Einzelner OCR-Call |
| `process_pdf_with_retry(pdf_path, api_key, max_retries=5, ...)` | Mit Retry-Logic |

### Text Processing
| Funktion | Beschreibung |
|----------|--------------|
| `markdown_to_plaintext(markdown)` | Markdown → Plain Text |
| `extract_metadata_from_markdown(markdown)` | Zeitschrift, Ausgabe, Autoren etc. |
| `combine_pages_to_markdown(pages)` | Seiten → ein Dokument |

### Quality Assurance
| Funktion | Beschreibung |
|----------|--------------|
| `calculate_ocr_confidence(markdown, metadata)` | Score 0.0-1.0 |
| `validate_ocr_output(markdown, metadata)` | Liste von Warnungen |

### Database/Tracking
| Funktion | Beschreibung |
|----------|--------------|
| `init_tracking_database(db_path)` | SQLite Schema erstellen |
| `mark_pdf_processing(...)` | Status → 'processing' |
| `mark_pdf_completed(...)` | Status → 'completed' + Ergebnisse |
| `mark_pdf_error(...)` | Status → 'error' + Message |
| `get_processed_pdfs(db_path)` | Set von completed pdf_ids |
| `get_processing_stats(db_path)` | Aggregierte Statistiken |

### Workflow
| Funktion | Beschreibung |
|----------|--------------|
| `prepare_file_for_ocr(file_path, temp_dir)` | Auto-Split falls nötig |
| `process_single_pdf(...)` | Kompletter Workflow für eine PDF |
| `save_ocr_results(...)` | .md, .txt, .json speichern |
| `discover_pdfs(input_dir)` | PDFs in Verzeichnis finden |

### Storage Management
| Funktion | Beschreibung |
|----------|--------------|
| `cleanup_temp_files(temp_dir, dry_run=False)` | Chunks löschen |
| `get_storage_stats(project_root)` | Speicherverbrauch berechnen |

---

## 4. Datenbank-Schema (SQLite)

**Tabelle:** `ocr_progress`

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| pdf_id | TEXT PRIMARY KEY | Eindeutige ID |
| source_file | TEXT NOT NULL | Original-Dateipfad |
| total_pages | INTEGER | Seitenanzahl |
| status | TEXT | pending/processing/completed/error |
| output_path_md | TEXT | Pfad zur .md Datei |
| output_path_txt | TEXT | Pfad zur .txt Datei |
| metadata_json | TEXT | JSON-String mit Metadaten |
| confidence | REAL | OCR-Qualitätsscore |
| warnings | TEXT | JSON-Array mit Warnungen |
| error_message | TEXT | Fehlermeldung (bei status=error) |
| processing_start | TIMESTAMP | Startzeit |
| processing_end | TIMESTAMP | Endzeit |
| processing_duration_sec | REAL | Dauer in Sekunden |
| api_pages_used | INTEGER | Verarbeitete Seiten (API) |
| api_bytes_used | INTEGER | Verarbeitete Bytes (API) |
| created_at | TIMESTAMP | Erstellungszeit |
| updated_at | TIMESTAMP | Letzte Änderung |

---

## 5. Confidence-Score Berechnung

**Basis:** 1.0

**Penalties:**
- Word count < 50: -0.3
- Word count < 150: -0.1
- Keine Artikel (H2/H3): -0.2
- Keine Zeitschrift/Ausgabe: -0.1
- Viele ungewöhnliche Zeichen (>50): -0.2

**Bonuses:**
- Artikel gefunden: +0.1
- Fußnoten gefunden: +0.05
- Tabellen gefunden: +0.05

**Range:** 0.0 - 1.0

---

## 6. Metadaten-Extraktion

Aus Markdown extrahiert:
- `zeitschrift`: Erste H1-Überschrift
- `ausgabe`: Regex für Jahrgang/Heft/Ausgabe/Nr.
- `seite`: Regex für "Seite X"
- `artikel`: Alle H2 und H3 Überschriften
- `autoren`: "Von X", "Autor: X", Namenssignaturen
- `fussnoten_anzahl`: Nummerierte Listen
- `tabellen_anzahl`: Markdown-Tabellen
- `word_count`: Wörter im Plain Text

---

## 7. Beobachtungen & Potenzielle Issues

### Positiv
- Robustes Checkpoint-System (Resume nach Unterbrechung)
- Saubere Trennung Notebook/Utils
- Umfassende Fehlerbehandlung mit Retry-Logic
- Multi-Format Output (md, txt, json)

### Potenziell problematisch
1. **TIMEOUT_SECONDS wird nicht verwendet:** In Cell 1 definiert, aber `process_pdf_with_ocr()` hat eigenen `timeout=120` Parameter
2. **api_bytes_used immer 0:** In `process_pdf_with_ocr()` wird `document_size_bytes: 0` gesetzt ("Nicht verfügbar in OCR Response")
3. **Signed URL Expiry:** `expiry=1` (1 Stunde) - könnte bei sehr langen Verarbeitungen problematisch sein
4. **Metadaten-Extraktion DDR-spezifisch:** Regex-Patterns möglicherweise zu eng für andere Zeitschriften

### Unklar
- Wird `MAX_RETRIES` aus Cell 1 tatsächlich an `process_pdf_with_retry()` übergeben? (Scheint nicht der Fall)
- Gibt es eine Möglichkeit, fehlgeschlagene Dateien erneut zu verarbeiten? (Status 'error' bleibt in DB)

---

## 8. Abgleich mit Dokumentation

### 8.1 ARCHITECTURE.md - Diskrepanzen

| Thema | Dokumentation sagt | Code macht | Schwere |
|-------|-------------------|------------|---------|
| **API-Modell** | "Mistral Pixtral Vision AI", "pixtral-12b-2409" | `mistral-ocr-latest` via OCR-API | KRITISCH |
| **API-Endpoint** | `client.chat.complete()` (Chat-API) | `client.ocr.process()` (OCR-API) | KRITISCH |
| **PDF-Verarbeitung** | "PDF → Images: Convert multi-page PDFs to individual images" | PDFs werden direkt hochgeladen, KEINE Image-Konvertierung | KRITISCH |
| **Image-Input** | Base64-encoded in Chat-Message | File Upload → Signed URL für PDFs; Base64 Data-URI nur für Images | MITTEL |
| **Bild-Komprimierung** | "JPEG quality 85%, Max 2048px longest side" | Nicht implementiert - Originaldateien werden verwendet | MITTEL |
| **Logging** | FileHandler + StreamHandler | Nur StreamHandler (kein File-Log) | GERING |
| **DB-Schema Spalte** | `api_call_duration_sec` | `processing_duration_sec` | GERING |
| **DB-Schema Spalte** | `page_number` | `total_pages` (andere Semantik) | GERING |

### 8.2 LLM_WORKFLOW.md - Diskrepanzen

| Thema | Dokumentation sagt | Code macht | Schwere |
|-------|-------------------|------------|---------|
| **Gesamter Workflow** | Chat-API mit ausführlichen Prompts | OCR-API ohne Prompts | KRITISCH |
| **Prompt Engineering** | 130 Zeilen detaillierte Prompts für strukturierte Extraktion | KEINE PROMPTS - OCR-API hat keinen Prompt-Parameter | KRITISCH |
| **Confidence-Berechnung** | Penalisiert `[illegible]` und `[possibly:]` Markers | Penalisiert kurze Texte, fehlende Struktur, ungewöhnliche Zeichen | MITTEL |
| **Metadaten-Regex** | `\*\*Issue\*\*:`, `\*\*Author\*\*:`, `\*\*Page\*\*:` | `Jahrgang\|Heft\|Ausgabe`, `Von\|Autor\|Author`, `Seite X` | MITTEL |
| **Workflow-Diagramm** | Zeigt "Image Prep → Resize → Base64 Encode" | Kein Resize, PDFs werden direkt hochgeladen | MITTEL |
| **Response-Parsing** | `response.choices[0].message.content` (Chat-Format) | `response.pages` (OCR-Format mit Page-Objekten) | KRITISCH |

### 8.3 README.md - Status

Die README.md ist **weitgehend korrekt** und beschreibt den tatsächlichen Workflow:
- Korrekt: Mistral OCR API (`mistral-ocr-latest`)
- Korrekt: PDF-Splitting bei >50MB oder >1000 Seiten
- Korrekt: Checkpoint-System mit SQLite
- Korrekt: Output-Formate (.md, .txt, .json)

### 8.4 Zusammenfassung der kritischen Diskrepanzen

**Die Dokumentation in `ARCHITECTURE.md` und `LLM_WORKFLOW.md` beschreibt einen ANDEREN Workflow:**

1. **Dokumentation:** Vision-Chat-API mit Prompts für strukturierte OCR
2. **Code:** Dedizierte OCR-API ohne Prompts

Dies deutet darauf hin, dass:
- Entweder die Dokumentation vor einem API-Wechsel geschrieben wurde
- Oder die Dokumentation für einen geplanten, aber nicht implementierten Workflow erstellt wurde

**Empfehlung:** `ARCHITECTURE.md` und `LLM_WORKFLOW.md` müssen grundlegend überarbeitet werden, um den tatsächlichen OCR-API-Workflow zu beschreiben.

---

## 9. Empfehlungen

### Sofort zu beheben (Dokumentation)
1. `ARCHITECTURE.md`: API-Workflow auf OCR-API umschreiben
2. `LLM_WORKFLOW.md`: Entweder löschen oder komplett neu schreiben für OCR-API
3. DB-Schema in Doku aktualisieren

### Code-Verbesserungen (optional)
1. `TIMEOUT_SECONDS` aus .env tatsächlich an API-Call übergeben
2. `MAX_RETRIES` aus .env an `process_pdf_with_retry()` übergeben
3. Mechanismus für Re-Processing von 'error' Dateien hinzufügen
4. File-Logging optional aktivieren

### Validierung
1. Testen ob OCR-API tatsächlich strukturiertes Markdown zurückgibt (ohne Prompts)
2. Prüfen ob Metadaten-Regex für DDR-Zeitschriften ausreichend ist
