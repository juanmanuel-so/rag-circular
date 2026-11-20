import base64
import hmac
import os
from typing import Annotated

import psycopg
from fastapi import Header, HTTPException
from minio import Minio
from pgvector.psycopg import register_vector

# Normalizar URLs de SQLAlchemy para utilizarlas con psycopg
DATABASE_URL = os.getenv("DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://", 1)
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está configurada")

BUCKET = os.environ.get("MINIO_BUCKET", "documentos")
API_KEY = os.environ["RAG_API_KEY"]
EMBED_MODEL = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
MODEL_NAME = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")

FILES_SIGNING_SECRET = os.environ["FILES_SIGNING_SECRET"].encode()
FILES_PUBLIC_BASE_URL = os.environ.get("FILES_PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
FILES_URL_TTL = min(max(int(os.environ.get("FILES_URL_TTL", "900")), 60), 86400)

MAX_BYTES = 15 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain; charset=utf-8",
}

minio = Minio(
    os.getenv("MINIO_ENDPOINT", "minio:9000"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False,
)


class State:
    """Objetos cargados al arrancar (ver lifespan en main.py)."""
    encoder = None


def db():
    conn = psycopg.connect(DATABASE_URL, autocommit=False)
    register_vector(conn)
    return conn


def require_key(x_api_key: Annotated[str | None, Header()] = None):
    if not x_api_key or not hmac.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="No autorizado")


def extension_of(name: str) -> str:
    base = name.rsplit("/", 1)[-1]
    return base.rsplit(".", 1)[-1].lower() if "." in base else ""


def encode_id(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def decode_id(value: str) -> str:
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode()
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(400, "Identificador inválido")
