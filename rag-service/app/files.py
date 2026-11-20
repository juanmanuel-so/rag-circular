"""Enlaces públicos firmados a documentos.

nginx expone solo /files/ de este servicio. Un archivo se entrega únicamente
con un enlace firmado (HMAC-SHA256) y vigente emitido por la propia API.
"""
import hashlib
import hmac
import time
from urllib.parse import quote, urlencode

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from minio.error import S3Error

from .config import (
    ALLOWED_EXTENSIONS, BUCKET, FILES_PUBLIC_BASE_URL, FILES_SIGNING_SECRET, FILES_URL_TTL,
    extension_of, minio,
)

router = APIRouter()


def _signature(name: str, exp: int) -> str:
    return hmac.new(FILES_SIGNING_SECRET, f"{name}\n{exp}".encode(), hashlib.sha256).hexdigest()


def sign_url(name: str, ttl: int = FILES_URL_TTL) -> tuple[str, int]:
    """Devuelve (url, exp) para un objeto del bucket."""
    exp = int(time.time()) + ttl
    query = urlencode({"exp": exp, "sig": _signature(name, exp)})
    return f"{FILES_PUBLIC_BASE_URL}/files/{quote(name, safe='/')}?{query}", exp


def _verify(name: str, exp: str | None, sig: str | None) -> int:
    try:
        exp_int = int(exp or "")
    except ValueError:
        raise HTTPException(403, "Enlace inválido")
    if not sig or not hmac.compare_digest(sig, _signature(name, exp_int)):
        raise HTTPException(403, "Enlace inválido")
    remaining = exp_int - int(time.time())
    if remaining <= 0:
        raise HTTPException(403, "Enlace expirado")
    return remaining


@router.api_route("/files/{name:path}", methods=["GET", "HEAD"], include_in_schema=True)
def get_file(name: str, request: Request, exp: str | None = None, sig: str | None = None):
    remaining = _verify(name, exp, sig)
    try:
        stat = minio.stat_object(BUCKET, name)
    except S3Error as exc:
        if exc.code in ("NoSuchKey", "NoSuchObject", "NoSuchBucket"):
            raise HTTPException(404, "Documento no encontrado")
        raise
    base = name.rsplit("/", 1)[-1]
    headers = {
        "Content-Type": stat.content_type or ALLOWED_EXTENSIONS.get(extension_of(name), "application/octet-stream"),
        "Content-Length": str(stat.size),
        "Content-Disposition": f"inline; filename*=UTF-8''{quote(base)}",
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": f"private, max-age={min(remaining, 300)}",
        "Referrer-Policy": "no-referrer",
    }
    if request.method == "HEAD":
        return Response(status_code=200, headers=headers)

    obj = minio.get_object(BUCKET, name)

    def body():
        try:
            yield from obj.stream(64 * 1024)
        finally:
            obj.close()
            obj.release_conn()

    return StreamingResponse(body(), headers=headers)
