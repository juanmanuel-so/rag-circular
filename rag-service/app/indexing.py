"""Indexación de documentos e historial de indexaciones (tabla indexations)."""
import io
import re
from typing import Annotated

import psycopg
from docx import Document
from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg.types.json import Jsonb
from pypdf import PdfReader

from .config import ALLOWED_EXTENSIONS, BUCKET, DATABASE_URL, MAX_BYTES, State, db, extension_of, minio, require_key

router = APIRouter(prefix="/admin", dependencies=[Depends(require_key)])

# Clave del advisory lock de Postgres que impide dos indexaciones simultáneas.
INDEX_LOCK_KEY = 727274

SUMMARY_COLUMNS = "id, started_at, finished_at, status, indexed_count, skipped_count, removed_count, error_count, error"


def init_indexations(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS indexations (
        id BIGSERIAL PRIMARY KEY,
        started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        finished_at TIMESTAMPTZ,
        status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
        indexed_count INTEGER NOT NULL DEFAULT 0,
        skipped_count INTEGER NOT NULL DEFAULT 0,
        removed_count INTEGER NOT NULL DEFAULT 0,
        error_count INTEGER NOT NULL DEFAULT 0,
        details JSONB NOT NULL DEFAULT '{}'::jsonb,
        error TEXT
    )""")
    # Ejecuciones que quedaron a medias porque el contenedor se reinició.
    conn.execute("UPDATE indexations SET status='failed', finished_at=now(), error='interrumpida' WHERE status='running'")


def extract_pages(name: str, data: bytes):
    ext = extension_of(name)
    if ext == "pdf":
        reader = PdfReader(io.BytesIO(data))
        if len(reader.pages) > 300:
            raise ValueError("PDF excede 300 páginas")
        return [(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]
    if ext == "docx":
        doc = Document(io.BytesIO(data))
        return [(None, "\n".join(p.text for p in doc.paragraphs) + "\n" + "\n".join(" | ".join(c.text for c in row.cells) for table in doc.tables for row in table.rows))]
    if ext == "txt":
        return [(None, data.decode("utf-8-sig"))]
    raise ValueError("Solo se admiten PDF, DOCX y TXT")


def split_text(text: str, chunk_size=1200, overlap=200):
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            boundary = text.rfind(" ", start + chunk_size // 2, end)
            if boundary > start:
                end = boundary
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks


def index_one(obj, indexed, skipped, errors):
    name = obj.object_name
    if obj.size is None or obj.size > MAX_BYTES:
        errors.append({"document": name, "error": "Archivo demasiado grande"})
        return
    try:
        with db() as conn:
            previous = conn.execute("SELECT etag FROM chunks WHERE object_name=%s LIMIT 1", (name,)).fetchone()
        if previous and previous[0] == obj.etag:
            skipped.append(name)
            return
        response = minio.get_object(BUCKET, name)
        try:
            data = response.read(MAX_BYTES + 1)
        finally:
            response.close()
            response.release_conn()
        if len(data) > MAX_BYTES:
            raise ValueError("Archivo demasiado grande")
        items = [(page, part) for page, text in extract_pages(name, data) for part in split_text(text)]
        if not items:
            raise ValueError("Documento sin texto extraíble (puede requerir OCR)")
        vectors = State.encoder.encode([part for _, part in items], normalize_embeddings=True)
        with db() as conn:
            conn.execute("DELETE FROM chunks WHERE object_name=%s", (name,))
            for i, ((page, part), vec) in enumerate(zip(items, vectors)):
                conn.execute(
                    "INSERT INTO chunks (object_name, etag, chunk_index, page_number, content, embedding) VALUES (%s,%s,%s,%s,%s,%s)",
                    (name, obj.etag, i, page, part, vec),
                )
        indexed.append({"document": name, "chunks": len(items)})
    except Exception as exc:
        errors.append({"document": name, "error": str(exc)[:250]})


def row_to_dict(row, with_details: bool) -> dict:
    keys = SUMMARY_COLUMNS.split(", ") + (["details"] if with_details else [])
    data = dict(zip(keys, row))
    for key in ("started_at", "finished_at"):
        data[key] = data[key].isoformat() if data[key] else None
    return data


@router.post("/index")
def index_documents():
    if not minio.bucket_exists(BUCKET):
        raise HTTPException(404, f"Bucket '{BUCKET}' no existe; suba un documento para crearlo")

    # Conexión propia en autocommit: mantiene el lock y registra la ejecución.
    with psycopg.connect(DATABASE_URL, autocommit=True) as lock_conn:
        if not lock_conn.execute("SELECT pg_try_advisory_lock(%s)", (INDEX_LOCK_KEY,)).fetchone()[0]:
            raise HTTPException(409, "Ya hay una indexación en curso")
        run_id = lock_conn.execute(
            "INSERT INTO indexations (status) VALUES ('running') RETURNING id"
        ).fetchone()[0]
        indexed, skipped, errors, removed = [], [], [], []
        try:
            seen = set()
            for obj in minio.list_objects(BUCKET, recursive=True):
                if extension_of(obj.object_name) not in ALLOWED_EXTENSIONS:
                    continue
                seen.add(obj.object_name)
                index_one(obj, indexed, skipped, errors)

            # Quitar del índice los documentos que ya no están en el bucket.
            with db() as conn:
                stored = [r[0] for r in conn.execute("SELECT DISTINCT object_name FROM chunks").fetchall()]
                removed = [name for name in stored if name not in seen]
                if removed:
                    conn.execute("DELETE FROM chunks WHERE object_name = ANY(%s)", (removed,))

            details = {"indexed": indexed, "skipped": skipped, "removed": removed, "errors": errors}
            row = lock_conn.execute(
                """UPDATE indexations SET status='completed', finished_at=now(),
                   indexed_count=%s, skipped_count=%s, removed_count=%s, error_count=%s, details=%s
                   WHERE id=%s RETURNING started_at, finished_at""",
                (len(indexed), len(skipped), len(removed), len(errors), Jsonb(details), run_id),
            ).fetchone()
        except Exception as exc:
            lock_conn.execute(
                "UPDATE indexations SET status='failed', finished_at=now(), error=%s, details=%s WHERE id=%s",
                (str(exc)[:500], Jsonb({"indexed": indexed, "skipped": skipped, "errors": errors}), run_id),
            )
            raise HTTPException(500, "La indexación falló; ver /admin/indexations/latest")
        finally:
            lock_conn.execute("SELECT pg_advisory_unlock(%s)", (INDEX_LOCK_KEY,))

    return {
        "indexation_id": run_id,
        "started_at": row[0].isoformat(),
        "finished_at": row[1].isoformat(),
        **details,
    }


@router.get("/indexations")
def list_indexations(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[int | None, Query(ge=1)] = None,
):
    with db() as conn:
        rows = conn.execute(
            f"SELECT {SUMMARY_COLUMNS} FROM indexations WHERE (%s::bigint IS NULL OR id < %s) ORDER BY id DESC LIMIT %s",
            (cursor, cursor, limit + 1),
        ).fetchall()
    items = [row_to_dict(r, False) for r in rows[:limit]]
    return {"items": items, "next_cursor": items[-1]["id"] if len(rows) > limit else None}


@router.get("/indexations/latest")
def latest_indexation():
    with db() as conn:
        row = conn.execute(f"SELECT {SUMMARY_COLUMNS}, details FROM indexations ORDER BY id DESC LIMIT 1").fetchone()
    return row_to_dict(row, True) if row else None


@router.get("/indexations/{indexation_id}")
def get_indexation(indexation_id: int):
    with db() as conn:
        row = conn.execute(f"SELECT {SUMMARY_COLUMNS}, details FROM indexations WHERE id=%s", (indexation_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Indexación no encontrada")
    return row_to_dict(row, True)
