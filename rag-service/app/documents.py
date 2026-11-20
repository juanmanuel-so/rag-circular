"""Administración de documentos en MinIO: subir, listar, ver, renombrar y eliminar."""
import io
import re
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from minio.commonconfig import CopySource
from minio.error import S3Error
from pydantic import BaseModel, Field

from .config import (
    ALLOWED_EXTENSIONS, BUCKET, MAX_BYTES, db, decode_id, encode_id, extension_of, minio, require_key,
)
from .files import sign_url

router = APIRouter(prefix="/admin/documents", dependencies=[Depends(require_key)])

MISSING = ("NoSuchKey", "NoSuchObject", "NoSuchBucket")


def safe_base_name(filename: str | None) -> str:
    # Conservar solo el nombre base para evitar rutas arbitrarias (../, /, \)
    base = (filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not base or base in (".", "..") or len(base) > 200 or any(ord(c) < 32 for c in base):
        raise HTTPException(400, "Nombre de archivo inválido")
    return base


def safe_prefix(prefix: str) -> str:
    prefix = prefix.strip().strip("/")
    if prefix:
        parts = prefix.split("/")
        if any(p in ("", ".", "..") or not re.fullmatch(r"[\w\-. ]{1,100}", p) for p in parts):
            raise HTTPException(400, "Prefijo inválido")
    return prefix


def join_name(prefix: str, base: str) -> str:
    return f"{prefix}/{base}" if prefix else base


def object_exists(name: str) -> bool:
    try:
        minio.stat_object(BUCKET, name)
        return True
    except S3Error as exc:
        if exc.code in MISSING:
            return False
        raise


def stat_or_404(name: str):
    try:
        return minio.stat_object(BUCKET, name)
    except S3Error as exc:
        if exc.code in MISSING:
            raise HTTPException(404, "Documento no encontrado")
        raise


def index_info(names: list[str]) -> dict[str, tuple[str, int]]:
    """object_name -> (etag indexado, número de fragmentos)."""
    if not names:
        return {}
    with db() as conn:
        rows = conn.execute(
            "SELECT object_name, etag, count(*) FROM chunks WHERE object_name = ANY(%s) GROUP BY object_name, etag",
            (names,),
        ).fetchall()
    return {r[0]: (r[1], r[2]) for r in rows}


def serialize(name: str, size: int, etag: str, last_modified, content_type: str | None, info) -> dict:
    indexed = info.get(name)
    if indexed is None:
        status, chunks = "not_indexed", 0
    else:
        status, chunks = ("indexed" if indexed[0] == etag else "outdated"), indexed[1]
    return {
        "id": encode_id(name),
        "name": name,
        "extension": extension_of(name),
        "size": size,
        "etag": etag,
        "last_modified": last_modified.isoformat() if last_modified else None,
        "content_type": content_type,
        "index_status": status,
        "chunks": chunks,
    }


def detail(name: str) -> dict:
    stat = stat_or_404(name)
    data = serialize(name, stat.size, stat.etag, stat.last_modified, stat.content_type, index_info([name]))
    data["url"], exp = sign_url(name)
    data["url_expires_at"] = exp
    return data


@router.get("")
def list_documents(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: str | None = None,
    prefix: Annotated[str, Query(max_length=300)] = "",
):
    prefix = safe_prefix(prefix)
    if not minio.bucket_exists(BUCKET):
        return {"items": [], "next_cursor": None}
    start_after = decode_id(cursor) if cursor else None
    objects = []
    listing = minio.list_objects(
        BUCKET, prefix=f"{prefix}/" if prefix else None, recursive=True, start_after=start_after,
    )
    for obj in listing:
        if extension_of(obj.object_name) not in ALLOWED_EXTENSIONS:
            continue
        objects.append(obj)
        if len(objects) > limit:
            break
    has_more = len(objects) > limit
    objects = objects[:limit]
    info = index_info([o.object_name for o in objects])
    items = [serialize(o.object_name, o.size, o.etag, o.last_modified, None, info) for o in objects]
    return {"items": items, "next_cursor": encode_id(objects[-1].object_name) if has_more else None}


@router.get("/{doc_id}")
def get_document(doc_id: str):
    return detail(decode_id(doc_id))


@router.post("", status_code=201)
def upload_document(
    file: Annotated[UploadFile, File(description="Documento PDF, DOCX o TXT (máx. 15 MiB)")],
    prefix: Annotated[str, Form(max_length=300)] = "",
    overwrite: Annotated[bool, Form()] = False,
):
    name = join_name(safe_prefix(prefix), safe_base_name(file.filename))
    ext = extension_of(name)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, "Solo se admiten PDF, DOCX y TXT")
    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Archivo demasiado grande (máx. 15 MiB)")
    if not data:
        raise HTTPException(400, "Archivo vacío")

    if not minio.bucket_exists(BUCKET):
        minio.make_bucket(BUCKET)
    if not overwrite and object_exists(name):
        raise HTTPException(409, f"El documento '{name}' ya existe; use overwrite=true para reemplazarlo")

    result = minio.put_object(
        BUCKET, name, io.BytesIO(data), length=len(data), content_type=ALLOWED_EXTENSIONS[ext],
    )
    return {"id": encode_id(name), "bucket": BUCKET, "document": name, "size": len(data), "etag": result.etag}


class RenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=500)


@router.patch("/{doc_id}")
def rename_document(doc_id: str, req: RenameRequest):
    old = decode_id(doc_id)
    stat_or_404(old)
    old_ext = extension_of(old)

    # "nombre" conserva la carpeta actual; "carpeta/nombre" la cambia.
    raw = req.name.strip().replace("\\", "/")
    if "/" in raw:
        folder, base = raw.rsplit("/", 1)
        prefix = safe_prefix(folder)
    else:
        prefix, base = (old.rsplit("/", 1)[0] if "/" in old else ""), raw
    base = safe_base_name(base)
    new_ext = extension_of(base)
    if new_ext in ALLOWED_EXTENSIONS:
        if new_ext != old_ext:
            raise HTTPException(415, "No se puede cambiar el tipo de archivo al renombrar")
    else:
        base = f"{base}.{old_ext}"
    new = join_name(prefix, base)

    if new == old:
        return detail(old)
    if object_exists(new):
        raise HTTPException(409, f"El documento '{new}' ya existe")

    minio.copy_object(BUCKET, new, CopySource(BUCKET, old))
    new_stat = minio.stat_object(BUCKET, new)
    # Mover los fragmentos indexados para no tener que reindexar.
    with db() as conn:
        # Fragmentos huérfanos con el nombre destino (documento borrado fuera de la API).
        conn.execute("DELETE FROM chunks WHERE object_name=%s", (new,))
        conn.execute("UPDATE chunks SET object_name=%s, etag=%s WHERE object_name=%s", (new, new_stat.etag, old))
    minio.remove_object(BUCKET, old)
    return detail(new)


@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: str):
    name = decode_id(doc_id)
    stat_or_404(name)
    minio.remove_object(BUCKET, name)
    with db() as conn:
        conn.execute("DELETE FROM chunks WHERE object_name=%s", (name,))
    return Response(status_code=204)
