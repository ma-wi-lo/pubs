"""
OCR-Zeitschriften-Mistral: Utility Functions

Dieses Modul enthält alle Hilfsfunktionen für die OCR-Verarbeitung
historischer DDR-Zeitschriften mit Mistral OCR API (mistral-ocr-latest).
"""

import os
import json
import logging
import re
import sqlite3
import time
import base64
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import fitz  # PyMuPDF
from mistralai import Mistral

# Setup Logger
logger = logging.getLogger(__name__)


# ============================================================================
# PDF UTILITIES
# ============================================================================

def get_pdf_info(pdf_path: str) -> Dict[str, Any]:
    """
    Ermittelt Informationen über eine PDF-Datei.

    Args:
        pdf_path: Pfad zur PDF-Datei

    Returns:
        Dict mit 'pages', 'size_mb', 'needs_split'
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF nicht gefunden: {pdf_path}")

    size_mb = os.path.getsize(pdf_path) / (1024 * 1024)

    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        doc.close()

        # Prüfe ob Splitting nötig ist
        needs_split = size_mb > 50 or page_count > 1000

        return {
            'pages': page_count,
            'size_mb': round(size_mb, 2),
            'needs_split': needs_split
        }

    except Exception as e:
        logger.error(f"Fehler beim Lesen der PDF: {e}")
        raise ValueError(f"Ungültige PDF: {e}")


def split_pdf(
    pdf_path: str,
    output_dir: str,
    max_pages: int = 500,
    max_size_mb: float = 45.0
) -> List[str]:
    """
    Splittet eine große PDF in kleinere Chunks.

    Args:
        pdf_path: Pfad zur Original-PDF
        output_dir: Verzeichnis für die Split-PDFs
        max_pages: Maximale Seiten pro Chunk (Default: 500)
        max_size_mb: Maximale Größe pro Chunk in MB (Default: 45)

    Returns:
        Liste von Pfaden zu den Split-PDFs

    Raises:
        ValueError: Bei Fehler beim Splitting
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF nicht gefunden: {pdf_path}")

    os.makedirs(output_dir, exist_ok=True)

    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)

        split_files = []
        chunk_start = 0

        while chunk_start < total_pages:
            chunk_end = min(chunk_start + max_pages, total_pages)

            # Erstelle Chunk-PDF
            chunk_doc = fitz.open()
            chunk_doc.insert_pdf(doc, from_page=chunk_start, to_page=chunk_end - 1)

            # Speichere Chunk
            base_name = Path(pdf_path).stem
            chunk_filename = f"{base_name}_chunk_{chunk_start + 1}-{chunk_end}.pdf"
            chunk_path = os.path.join(output_dir, chunk_filename)

            chunk_doc.save(chunk_path)
            chunk_doc.close()

            chunk_size_mb = os.path.getsize(chunk_path) / (1024 * 1024)

            # Prüfe ob Chunk zu groß ist
            if chunk_size_mb > max_size_mb:
                logger.warning(
                    f"Chunk {chunk_filename} ist {chunk_size_mb:.2f} MB groß "
                    f"(Limit: {max_size_mb} MB). Evtl. kleinere Chunks verwenden."
                )

            split_files.append(chunk_path)
            logger.info(
                f"Chunk erstellt: {chunk_filename} "
                f"(Seiten {chunk_start + 1}-{chunk_end}, {chunk_size_mb:.2f} MB)"
            )

            chunk_start = chunk_end

        doc.close()

        logger.info(f"PDF gesplittet: {total_pages} Seiten → {len(split_files)} Chunks")
        return split_files

    except Exception as e:
        logger.error(f"Fehler beim Splitten der PDF: {e}")
        raise ValueError(f"Splitting fehlgeschlagen: {e}")


# ============================================================================
# FILE ENCODING
# ============================================================================

def encode_file_to_base64(file_path: str) -> str:
    """
    Kodiert eine Datei als Base64-String.

    Args:
        file_path: Pfad zur Datei (PDF oder Bild)

    Returns:
        Base64-kodierter String

    Raises:
        FileNotFoundError: Wenn Datei nicht existiert
        ValueError: Bei Encoding-Fehler
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Datei nicht gefunden: {file_path}")

    try:
        with open(file_path, 'rb') as f:
            file_bytes = f.read()

        base64_str = base64.b64encode(file_bytes).decode('utf-8')
        logger.info(f"Datei kodiert: {len(file_bytes)} Bytes → {len(base64_str)} Zeichen Base64")

        return base64_str

    except Exception as e:
        raise ValueError(f"Fehler beim Kodieren der Datei: {e}")


def get_media_type(file_path: str) -> str:
    """
    Ermittelt den MIME-Type einer Datei basierend auf der Endung.

    Args:
        file_path: Pfad zur Datei

    Returns:
        MIME-Type String (z.B. 'application/pdf', 'image/jpeg')

    Raises:
        ValueError: Wenn Dateiformat nicht unterstützt
    """
    ext = Path(file_path).suffix.lower()

    mime_types = {
        '.pdf': 'application/pdf',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png'
    }

    if ext not in mime_types:
        raise ValueError(f"Nicht unterstütztes Dateiformat: {ext}")

    return mime_types[ext]


# ============================================================================
# MISTRAL OCR API
# ============================================================================

def process_pdf_with_ocr(
    pdf_path: str,
    api_key: str,
    model: str = "mistral-ocr-latest",
    include_images: bool = True,
    timeout: int = 120
) -> Dict[str, Any]:
    """
    Verarbeitet eine PDF-Datei mit Mistral OCR API.

    Args:
        pdf_path: Pfad zur lokalen PDF-Datei oder URL
        api_key: Mistral API Key
        model: OCR-Modell (mistral-ocr-latest)
        include_images: Embedded Images als Base64 zurückgeben
        timeout: Timeout in Sekunden

    Returns:
        Dict mit 'pages' (Liste von Page-Objekten), 'usage', 'processing_time'

    Raises:
        ValueError: Bei API-Fehlern oder ungültiger Datei
        FileNotFoundError: Wenn PDF-Datei nicht existiert
    """
    start_time = time.time()

    # Prüfe ob Datei existiert (falls lokaler Pfad)
    if not pdf_path.startswith('http'):
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF nicht gefunden: {pdf_path}")

    try:
        # Initialisiere Mistral Client
        client = Mistral(api_key=api_key)

        # Bestimme Input-Typ
        if pdf_path.startswith('http'):
            # URL-basiert
            document_config = {
                "type": "document_url",
                "document_url": pdf_path
            }
            logger.info(f"Verarbeite Dokument von URL: {pdf_path}")
        else:
            # Lokale Datei
            media_type = get_media_type(pdf_path)

            # Unterscheide zwischen PDF und Bild
            if media_type == 'application/pdf':
                # PDFs müssen über File Upload API hochgeladen werden
                logger.info(f"Lade lokale PDF hoch: {Path(pdf_path).name}")

                # 1. Upload PDF
                with open(pdf_path, 'rb') as f:
                    uploaded_file = client.files.upload(
                        file={
                            "file_name": Path(pdf_path).name,
                            "content": f
                        },
                        purpose="ocr"
                    )

                logger.info(f"PDF hochgeladen, File-ID: {uploaded_file.id}")

                # 2. Get signed URL
                signed_url_response = client.files.get_signed_url(
                    file_id=uploaded_file.id,
                    expiry=1  # 1 Stunde
                )

                document_config = {
                    "type": "document_url",
                    "document_url": signed_url_response.url
                }
                logger.info(f"Signed URL erhalten, verarbeite PDF...")

            else:
                # Für Bilder: Base64 Data-URI
                base64_data = encode_file_to_base64(pdf_path)
                document_config = {
                    "type": "image_url",
                    "image_url": f"data:{media_type};base64,{base64_data}"
                }
                logger.info(f"Verarbeite lokales Bild: {Path(pdf_path).name}")

        # OCR API Call
        logger.info(f"Starte OCR mit Modell: {model}")
        response = client.ocr.process(
            model=model,
            document=document_config,
            include_image_base64=include_images
        )

        processing_time = time.time() - start_time

        # Extrahiere Ergebnisse
        # Response enthält: pages, model, usage_info
        actual_model = getattr(response, 'model', model)  # Fallback auf request model
        usage_info = getattr(response, 'usage_info', None)

        result = {
            'pages': response.pages,
            'model': actual_model,  # Tatsächlich verwendetes Modell (z.B. mistral-ocr-2512)
            'usage': {
                'pages_processed': getattr(usage_info, 'pages_processed', len(response.pages)) if usage_info else len(response.pages),
                'document_size_bytes': getattr(usage_info, 'doc_size_bytes', 0) if usage_info else 0
            },
            'processing_time': processing_time,
            'total_pages': len(response.pages)
        }

        logger.info(
            f"OCR erfolgreich: {result['total_pages']} Seiten, "
            f"Modell: {actual_model}, "
            f"{result['usage']['document_size_bytes'] / 1024:.1f} KB, "
            f"{processing_time:.2f}s"
        )

        return result

    except Exception as e:
        logger.error(f"OCR API Fehler: {e}")
        raise ValueError(f"API-Fehler: {e}")


def process_pdf_with_retry(
    pdf_path: str,
    api_key: str,
    model: str = "mistral-ocr-latest",
    max_retries: int = 5,
    base_delay: float = 2.0,
    **kwargs
) -> Dict[str, Any]:
    """
    Verarbeitet PDF mit Retry-Logic und Exponential Backoff.

    Args:
        pdf_path: Pfad zur PDF oder URL
        api_key: Mistral API Key
        model: OCR-Modell
        max_retries: Maximale Anzahl Versuche
        base_delay: Basis-Delay in Sekunden
        **kwargs: Weitere Parameter für process_pdf_with_ocr()

    Returns:
        Dict mit OCR-Ergebnissen

    Raises:
        ValueError: Wenn alle Versuche fehlschlagen
    """
    for attempt in range(max_retries):
        try:
            result = process_pdf_with_ocr(
                pdf_path=pdf_path,
                api_key=api_key,
                model=model,
                **kwargs
            )
            return result

        except Exception as e:
            error_str = str(e)

            # Rate Limit Error (429)
            if '429' in error_str:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"Rate Limit erreicht (429), Versuch {attempt + 1}/{max_retries}. "
                        f"Warte {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    continue

            # Server Error (500, 503)
            elif any(code in error_str for code in ['500', '503']):
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"Server-Fehler, Versuch {attempt + 1}/{max_retries}. "
                        f"Warte {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    continue

            # Andere Fehler: Sofort abbrechen
            logger.error(f"API-Fehler (nicht wiederholbar): {e}")
            raise

    raise ValueError(f"Alle {max_retries} Versuche fehlgeschlagen")


# ============================================================================
# TEXT PROCESSING
# ============================================================================

def markdown_to_plaintext(markdown: str) -> str:
    """
    Konvertiert Markdown zu Plain Text.

    Args:
        markdown: Markdown-formatierter Text

    Returns:
        Plain Text ohne Markdown-Syntax
    """
    text = markdown

    # Entferne Markdown-Syntax
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)  # Headers
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*(.+?)\*', r'\1', text)  # Italic
    text = re.sub(r'^\>\s+', '', text, flags=re.MULTILINE)  # Blockquotes
    text = re.sub(r'^\-\s+', '', text, flags=re.MULTILINE)  # Lists
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)  # Numbered lists
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)  # Links
    text = re.sub(r'---+', '', text)  # Horizontal rules

    return text.strip()


def extract_metadata_from_markdown(markdown: str) -> Dict[str, Any]:
    """
    Extrahiert strukturierte Metadaten aus Markdown-OCR-Output.

    Args:
        markdown: Markdown-formatierter OCR-Output

    Returns:
        Dict mit Metadaten (zeitschrift, ausgabe, seite, artikel, autoren, etc.)
    """
    metadata = {}

    # Zeitschriftentitel (erste H1)
    match = re.search(r'^#\s+(.+)$', markdown, re.MULTILINE)
    if match:
        metadata['zeitschrift'] = match.group(1).strip()

    # Ausgabe/Jahrgang
    match = re.search(r'(Jahrgang|Heft|Ausgabe|Nr\.?)\s*(\d+)', markdown, re.IGNORECASE)
    if match:
        metadata['ausgabe'] = match.group(0).strip()

    # Seitenzahl
    match = re.search(r'Seite\s*(\d+)', markdown, re.IGNORECASE)
    if match:
        metadata['seite'] = int(match.group(1))

    # Artikeltitel (alle H2 und H3)
    h2_titles = re.findall(r'^##\s+(.+)$', markdown, re.MULTILINE)
    h3_titles = re.findall(r'^###\s+(.+)$', markdown, re.MULTILINE)
    metadata['artikel'] = h2_titles + h3_titles

    # Autoren (verschiedene Muster)
    autoren = []
    # Muster: "Von [Name]" oder "Autor: [Name]"
    autoren.extend(re.findall(r'(?:Von|Autor|Author):\s*([A-ZÄÖÜ][^\n]+)', markdown))
    # Muster: Namenssignaturen am Ende
    autoren.extend(re.findall(r'\n\s*([A-ZÄÖÜ][a-zäöüß]+\s+[A-ZÄÖÜ][a-zäöüß]+)\s*$', markdown, re.MULTILINE))
    metadata['autoren'] = list(set(autoren))  # Duplikate entfernen

    # Fußnoten zählen
    metadata['fussnoten_anzahl'] = len(re.findall(r'^\d+\.\s+.+$', markdown, re.MULTILINE))

    # Tabellen erkennen
    table_lines = re.findall(r'^\|.+\|$', markdown, re.MULTILINE)
    metadata['tabellen_anzahl'] = len([l for l in table_lines if '---' not in l]) // 2  # Header + Rows

    # Wörter zählen
    plain_text = markdown_to_plaintext(markdown)
    metadata['word_count'] = len(plain_text.split())

    return metadata


def combine_pages_to_markdown(pages: List[Any]) -> str:
    """
    Kombiniert mehrere Seiten zu einem Markdown-Dokument.

    Args:
        pages: Liste von Page-Objekten aus OCR-Response

    Returns:
        Kombinierter Markdown-String
    """
    markdown_parts = []

    for page in pages:
        # Seitennummer als Trenner
        markdown_parts.append(f"# Seite {page.index + 1}\n")
        markdown_parts.append(page.markdown)
        markdown_parts.append("\n\n---\n\n")

    return "\n".join(markdown_parts)


# ============================================================================
# QUALITY ASSURANCE
# ============================================================================

def calculate_ocr_confidence(markdown: str, metadata: Dict[str, Any]) -> float:
    """
    Berechnet einen Confidence Score für OCR-Qualität (0.0-1.0).

    Args:
        markdown: OCR-Output in Markdown
        metadata: Extrahierte Metadaten

    Returns:
        Float zwischen 0.0 (schlecht) und 1.0 (gut)
    """
    score = 1.0

    # Penalty: Sehr kurzer Text (vermutlich Fehler)
    word_count = metadata.get('word_count', 0)
    if word_count < 50:
        score -= 0.3
    elif word_count < 150:
        score -= 0.1

    # Penalty: Keine Struktur erkannt
    if not metadata.get('artikel'):
        score -= 0.2

    # Penalty: Fehlende Metadaten
    if not metadata.get('zeitschrift') and not metadata.get('ausgabe'):
        score -= 0.1

    # Bonus: Strukturierte Elemente gefunden
    if metadata.get('artikel'):
        score += 0.1
    if metadata.get('fussnoten_anzahl', 0) > 0:
        score += 0.05
    if metadata.get('tabellen_anzahl', 0) > 0:
        score += 0.05

    # Penalty: Viele ungewöhnliche Zeichen (OCR-Artefakte)
    unusual_chars = len(re.findall(r'[^\w\s\.,;:!?\-äöüÄÖÜß()"\'\[\]]', markdown))
    if unusual_chars > 50:
        score -= 0.2

    return max(0.0, min(1.0, score))


def validate_ocr_output(markdown: str, metadata: Dict[str, Any]) -> List[str]:
    """
    Prüft OCR-Output auf häufige Probleme.

    Args:
        markdown: OCR-Output
        metadata: Metadaten

    Returns:
        Liste von Warnungen
    """
    warnings = []

    # Check: Leerer Output
    if not markdown.strip():
        warnings.append("ERROR: Leerer OCR-Output")

    # Check: Sehr kurzer Text
    word_count = metadata.get('word_count', 0)
    if word_count < 20:
        warnings.append(f"WARN: Sehr wenig Text ({word_count} Wörter)")

    # Check: Keine Struktur erkannt
    if '##' not in markdown and '**' not in markdown:
        warnings.append("WARN: Keine Strukturelemente erkannt")

    # Check: Markdown-Syntax-Fehler
    if markdown.count('**') % 2 != 0:
        warnings.append("WARN: Ungepaartes ** in Markdown")

    # Check: Ungewöhnlich viele Leerzeilen
    empty_lines = len(re.findall(r'\n\s*\n\s*\n', markdown))
    if empty_lines > 20:
        warnings.append(f"WARN: Viele Leerzeilen ({empty_lines}), mögliche Strukturprobleme")

    return warnings


# ============================================================================
# DATABASE / TRACKING
# ============================================================================

def init_tracking_database(db_path: str):
    """
    Initialisiert SQLite-Datenbank für Fortschrittsverfolgung.

    Args:
        db_path: Pfad zur SQLite-Datenbankdatei
    """
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ocr_progress (
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
            )
        """)
        conn.commit()

    logger.info(f"Tracking-Datenbank initialisiert: {db_path}")


def mark_pdf_processing(db_path: str, pdf_id: str, source_file: str, total_pages: int):
    """
    Markiert eine PDF als 'processing' in der Datenbank.
    """
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO ocr_progress
            (pdf_id, source_file, total_pages, status, processing_start, updated_at)
            VALUES (?, ?, ?, 'processing', ?, ?)
        """, (pdf_id, source_file, total_pages, datetime.now(), datetime.now()))
        conn.commit()


def mark_pdf_completed(
    db_path: str,
    pdf_id: str,
    output_path_md: str,
    output_path_txt: str,
    metadata: Dict[str, Any],
    confidence: float,
    warnings: List[str],
    processing_duration: float,
    api_pages: int,
    api_bytes: int
):
    """
    Markiert eine PDF als 'completed' mit allen Ergebnissen.
    """
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            UPDATE ocr_progress SET
                status = 'completed',
                output_path_md = ?,
                output_path_txt = ?,
                metadata_json = ?,
                confidence = ?,
                warnings = ?,
                processing_end = ?,
                processing_duration_sec = ?,
                api_pages_used = ?,
                api_bytes_used = ?,
                updated_at = ?
            WHERE pdf_id = ?
        """, (
            output_path_md,
            output_path_txt,
            json.dumps(metadata, ensure_ascii=False),
            confidence,
            json.dumps(warnings),
            datetime.now(),
            processing_duration,
            api_pages,
            api_bytes,
            datetime.now(),
            pdf_id
        ))
        conn.commit()


def mark_pdf_error(db_path: str, pdf_id: str, error_message: str):
    """
    Markiert eine PDF als 'error' mit Fehlermeldung.
    """
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            UPDATE ocr_progress SET
                status = 'error',
                error_message = ?,
                processing_end = ?,
                updated_at = ?
            WHERE pdf_id = ?
        """, (error_message, datetime.now(), datetime.now(), pdf_id))
        conn.commit()


def get_processed_pdfs(db_path: str) -> set:
    """
    Holt alle bereits verarbeiteten PDF-IDs.

    Returns:
        Set von pdf_ids mit Status 'completed'
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("SELECT pdf_id FROM ocr_progress WHERE status = 'completed'")
        return {row[0] for row in cursor.fetchall()}


def get_processing_stats(db_path: str) -> Dict[str, Any]:
    """
    Berechnet Statistiken über die Verarbeitung.

    Returns:
        Dict mit total, completed, error, avg_duration, avg_confidence
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error,
                AVG(CASE WHEN status = 'completed' THEN processing_duration_sec END) as avg_duration,
                AVG(CASE WHEN status = 'completed' THEN confidence END) as avg_confidence,
                SUM(CASE WHEN status = 'completed' THEN api_pages_used ELSE 0 END) as total_pages,
                SUM(CASE WHEN status = 'completed' THEN api_bytes_used ELSE 0 END) as total_bytes
            FROM ocr_progress
        """)
        row = cursor.fetchone()

        return {
            'total': row[0] or 0,
            'completed': row[1] or 0,
            'error': row[2] or 0,
            'pending': row[0] - (row[1] or 0) - (row[2] or 0),
            'avg_duration_sec': round(row[3], 2) if row[3] else 0,
            'avg_confidence': round(row[4], 3) if row[4] else 0,
            'total_pages': row[5] or 0,
            'total_bytes': row[6] or 0,
            'estimated_cost_usd': (row[5] or 0) * 0.001  # $1 per 1000 pages
        }


# ============================================================================
# FILE PREPARATION
# ============================================================================

def prepare_file_for_ocr(
    file_path: str,
    temp_dir: str
) -> List[str]:
    """
    Bereitet eine Datei für OCR vor. Splittet große PDFs automatisch.

    Args:
        file_path: Pfad zur Original-Datei
        temp_dir: Temporäres Verzeichnis für Split-PDFs

    Returns:
        Liste von Dateipfaden zur Verarbeitung (Original oder Chunks)
    """
    ext = Path(file_path).suffix.lower()

    # Bilder: Keine Vorbereitung nötig
    if ext in ['.jpg', '.jpeg', '.png']:
        return [file_path]

    # PDFs: Prüfe ob Splitting nötig
    if ext == '.pdf':
        pdf_info = get_pdf_info(file_path)

        if not pdf_info['needs_split']:
            # PDF klein genug
            logger.info(
                f"PDF {Path(file_path).name}: "
                f"{pdf_info['pages']} Seiten, {pdf_info['size_mb']} MB - OK"
            )
            return [file_path]
        else:
            # PDF muss gesplittet werden
            logger.warning(
                f"PDF {Path(file_path).name} ist zu groß: "
                f"{pdf_info['pages']} Seiten, {pdf_info['size_mb']} MB"
            )
            logger.info(f"Splitte PDF in 500-Seiten-Chunks...")

            split_files = split_pdf(
                pdf_path=file_path,
                output_dir=temp_dir,
                max_pages=500,
                max_size_mb=45.0
            )

            logger.info(f"✓ PDF gesplittet: {len(split_files)} Chunks erstellt")
            return split_files

    # Nicht unterstütztes Format
    raise ValueError(f"Nicht unterstütztes Dateiformat: {ext}")


# ============================================================================
# FILE I/O
# ============================================================================

def save_ocr_results(
    pdf_id: str,
    markdown: str,
    plain_text: str,
    metadata: Dict[str, Any],
    output_dir: str
) -> Tuple[str, str]:
    """
    Speichert OCR-Ergebnisse als .md und .txt Dateien.

    Args:
        pdf_id: Eindeutige PDF-ID (wird als Dateiname verwendet)
        markdown: Markdown-formatierter Text
        plain_text: Plain Text
        metadata: Metadaten-Dict
        output_dir: Ausgabeverzeichnis

    Returns:
        Tuple (md_path, txt_path)
    """
    os.makedirs(output_dir, exist_ok=True)

    # Markdown-Datei
    md_path = os.path.join(output_dir, f"{pdf_id}.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(markdown)

    # Plain Text-Datei
    txt_path = os.path.join(output_dir, f"{pdf_id}.txt")
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(plain_text)

    # Metadaten-JSON
    json_path = os.path.join(output_dir, f"{pdf_id}_metadata.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    logger.info(f"OCR-Ergebnisse gespeichert: {pdf_id}")

    return md_path, txt_path


def discover_pdfs(input_dir: str) -> List[Dict[str, Any]]:
    """
    Findet alle PDF-Dateien im Input-Verzeichnis.

    Args:
        input_dir: Pfad zum Input-Verzeichnis

    Returns:
        Liste von Dicts mit {'path', 'filename', 'size_mb'}
    """
    pdfs = []

    for root, dirs, files in os.walk(input_dir):
        for filename in files:
            if filename.lower().endswith('.pdf'):
                file_path = os.path.join(root, filename)
                size_mb = os.path.getsize(file_path) / (1024 * 1024)

                pdfs.append({
                    'path': file_path,
                    'filename': filename,
                    'size_mb': round(size_mb, 2)
                })

    logger.info(f"Gefunden: {len(pdfs)} PDF-Dateien in {input_dir}")
    return pdfs


# ============================================================================
# MAIN WORKFLOW FUNCTION
# ============================================================================

def process_single_pdf(
    pdf_id: str,
    pdf_path: str,
    api_key: str,
    output_dir: str,
    db_path: str,
    model: str = "mistral-ocr-latest",
    delay_seconds: float = 2.0,
    **kwargs
) -> Dict[str, Any]:
    """
    Vollständige Verarbeitung einer einzelnen PDF.

    Args:
        pdf_id: Eindeutige ID für diese PDF
        pdf_path: Pfad zur PDF oder URL
        api_key: Mistral API Key
        output_dir: Ausgabeverzeichnis
        db_path: Pfad zur Tracking-Datenbank
        model: OCR-Modell
        delay_seconds: Delay vor API-Call
        **kwargs: Weitere Parameter für API-Call

    Returns:
        Dict mit Verarbeitungsergebnissen
    """
    start_time = time.time()

    try:
        # Markiere als processing
        mark_pdf_processing(db_path, pdf_id, pdf_path, total_pages=0)  # Pages unknown vor OCR

        # Rate Limiting Delay
        time.sleep(delay_seconds)

        # OCR mit Retry
        result = process_pdf_with_retry(
            pdf_path=pdf_path,
            api_key=api_key,
            model=model,
            **kwargs
        )

        # Kombiniere Seiten zu Markdown
        full_markdown = combine_pages_to_markdown(result['pages'])
        plain_text = markdown_to_plaintext(full_markdown)

        # Extrahiere Metadaten
        metadata = extract_metadata_from_markdown(full_markdown)
        metadata['total_pages'] = result['total_pages']
        metadata['model'] = result['model']  # Tatsächlich verwendetes Modell
        metadata['api_usage'] = result['usage']

        # Quality Checks
        confidence = calculate_ocr_confidence(full_markdown, metadata)
        warnings = validate_ocr_output(full_markdown, metadata)

        # Speichere Ergebnisse
        md_path, txt_path = save_ocr_results(
            pdf_id=pdf_id,
            markdown=full_markdown,
            plain_text=plain_text,
            metadata=metadata,
            output_dir=output_dir
        )

        # Update Database
        processing_duration = time.time() - start_time
        mark_pdf_completed(
            db_path=db_path,
            pdf_id=pdf_id,
            output_path_md=md_path,
            output_path_txt=txt_path,
            metadata=metadata,
            confidence=confidence,
            warnings=warnings,
            processing_duration=processing_duration,
            api_pages=result['usage']['pages_processed'],
            api_bytes=0  # Nicht verfügbar
        )

        logger.info(
            f"✓ PDF {pdf_id} verarbeitet: "
            f"{result['total_pages']} Seiten, "
            f"{metadata.get('word_count', 0)} Wörter, "
            f"Confidence {confidence:.2f}, "
            f"{processing_duration:.1f}s"
        )

        return {
            'pdf_id': pdf_id,
            'success': True,
            'total_pages': result['total_pages'],
            'confidence': confidence,
            'warnings': warnings,
            'metadata': metadata,
            'processing_time': processing_duration
        }

    except Exception as e:
        logger.error(f"✗ Fehler bei PDF {pdf_id}: {e}")
        mark_pdf_error(db_path, pdf_id, str(e))

        return {
            'pdf_id': pdf_id,
            'success': False,
            'error': str(e)
        }


# ============================================================================
# CLEANUP / STORAGE MANAGEMENT
# ============================================================================

def cleanup_temp_files(temp_dir: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    Löscht temporäre PDF-Chunk-Dateien aus dem Temp-Verzeichnis.

    Diese Funktion räumt Split-PDFs auf, die nach erfolgreicher OCR-Verarbeitung
    nicht mehr benötigt werden. Die SQLite-Datenbank bleibt erhalten.

    Args:
        temp_dir: Pfad zum Temp-Verzeichnis (z.B. 'data/tracking/pdf_chunks')
        dry_run: Wenn True, zeigt nur was gelöscht würde (ohne zu löschen)

    Returns:
        Dict mit Statistiken: {
            'files_found': int,
            'files_deleted': int,
            'space_freed_mb': float,
            'deleted_files': list
        }
    """
    if not os.path.exists(temp_dir):
        logger.warning(f"Temp-Verzeichnis existiert nicht: {temp_dir}")
        return {
            'files_found': 0,
            'files_deleted': 0,
            'space_freed_mb': 0.0,
            'deleted_files': []
        }

    # Finde alle PDF-Chunks
    chunk_files = []
    total_size_bytes = 0

    for root, dirs, files in os.walk(temp_dir):
        for filename in files:
            if filename.lower().endswith('.pdf'):
                file_path = os.path.join(root, filename)
                file_size = os.path.getsize(file_path)
                chunk_files.append({
                    'path': file_path,
                    'name': filename,
                    'size_mb': file_size / (1024 * 1024)
                })
                total_size_bytes += file_size

    total_size_mb = total_size_bytes / (1024 * 1024)

    # Dry Run: Zeige nur was gelöscht würde
    if dry_run:
        logger.info(f"DRY RUN: {len(chunk_files)} Chunk-Dateien gefunden ({total_size_mb:.2f} MB)")
        for chunk in chunk_files:
            logger.info(f"  Würde löschen: {chunk['name']} ({chunk['size_mb']:.2f} MB)")

        return {
            'files_found': len(chunk_files),
            'files_deleted': 0,
            'space_freed_mb': 0.0,
            'deleted_files': []
        }

    # Tatsächliches Löschen
    deleted_files = []
    for chunk in chunk_files:
        try:
            os.remove(chunk['path'])
            deleted_files.append(chunk['name'])
            logger.info(f"Gelöscht: {chunk['name']} ({chunk['size_mb']:.2f} MB)")
        except Exception as e:
            logger.error(f"Fehler beim Löschen von {chunk['name']}: {e}")

    logger.info(
        f"Cleanup abgeschlossen: {len(deleted_files)}/{len(chunk_files)} Dateien gelöscht, "
        f"{total_size_mb:.2f} MB freigegeben"
    )

    return {
        'files_found': len(chunk_files),
        'files_deleted': len(deleted_files),
        'space_freed_mb': total_size_mb,
        'deleted_files': deleted_files
    }


def get_storage_stats(project_root: str) -> Dict[str, Any]:
    """
    Berechnet Speicherplatz-Statistiken für das Projekt.

    Args:
        project_root: Pfad zum Projekt-Root-Verzeichnis

    Returns:
        Dict mit Größen in MB für verschiedene Ordner
    """
    stats = {}

    dirs_to_check = {
        'input': 'data/input',
        'output': 'data/output',
        'tracking': 'data/tracking',
        'chunks': 'data/tracking/pdf_chunks',
        'database': 'data/tracking/ocr_progress.db'
    }

    for key, rel_path in dirs_to_check.items():
        full_path = os.path.join(project_root, rel_path)

        if not os.path.exists(full_path):
            stats[key] = 0.0
            continue

        # Für Dateien
        if os.path.isfile(full_path):
            stats[key] = os.path.getsize(full_path) / (1024 * 1024)
        # Für Verzeichnisse
        else:
            total_size = 0
            for root, dirs, files in os.walk(full_path):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except:
                        pass
            stats[key] = total_size / (1024 * 1024)

    # Gesamtgröße berechnen
    stats['total'] = sum(stats.values())

    return stats


if __name__ == "__main__":
    # Beispiel-Verwendung
    print("OCR-Zeitschriften-Mistral Utils")
    print("Importiere dieses Modul in einem Jupyter Notebook:")
    print("  from utils import *")
