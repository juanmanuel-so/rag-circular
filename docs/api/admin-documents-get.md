# GET /admin/documents/{id} 🔒

Devuelve los datos de un documento y un **enlace público firmado** para abrirlo o descargarlo.

- **Auth:** cabecera `X-API-Key`
- **`id`:** el `id` devuelto por el listado o la subida (nombre del objeto en base64url)

## Respuesta `200`
Los mismos campos que cada elemento de [`GET /admin/documents`](admin-documents-list.md), con `content_type` informado, más:

| Campo | Descripción |
|---|---|
| `url` | Enlace firmado a [`/files/...`](files.md), válido durante `FILES_URL_TTL` segundos (15 min por defecto) |
| `url_expires_at` | Momento de expiración del enlace (segundos Unix) |

```json
{
  "id": "bm9ybWF0aXZhL2xleS1yZXAucGRm",
  "name": "normativa/ley-rep.pdf",
  "extension": "pdf",
  "size": 482113,
  "etag": "9b2cf535f27731c974343645a3985328",
  "last_modified": "2026-11-19T14:02:11+00:00",
  "content_type": "application/pdf",
  "index_status": "indexed",
  "chunks": 42,
  "url": "https://piec.ulagos.cl/files/normativa/ley-rep.pdf?exp=1795104000&sig=3f1c…",
  "url_expires_at": 1795104000
}
```

El enlace se puede entregar tal cual al navegador de cualquier usuario: no contiene la API key. Pedir uno nuevo cuando expire.

## Errores

| Código | Causa |
|---|---|
| `400` | `id` mal formado |
| `401` | `X-API-Key` ausente o incorrecta |
| `404` | El documento no existe |

## Ejemplo
```bash
curl http://localhost:8000/admin/documents/bm9ybWF0aXZhL2xleS1yZXAucGRm -H "X-API-Key: TU_RAG_API_KEY"
```
