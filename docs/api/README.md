# Documentación de la API

Servicio RAG (FastAPI) en `http://localhost:8000`. La documentación interactiva generada automáticamente está en `/docs` (Swagger) y `/openapi.json`.

## Autenticación
Las rutas marcadas con 🔒 son privadas (solo dentro de la red Docker `web`; nginx no las expone) y requieren la cabecera `X-API-Key` con el valor de `RAG_API_KEY` definido en `.env`. Si falta o no coincide, responden `401 {"detail": "No autorizado"}`.

## Rutas del servicio RAG

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | [`/health`](health.md) | — | Comprobación de estado |
| GET | [`/admin/documents`](admin-documents-list.md) | 🔒 | Lista documentos (paginado por cursor) con estado de indexación |
| POST | [`/admin/documents`](admin-documents.md) | 🔒 | Sube un documento a MinIO |
| GET | [`/admin/documents/{id}`](admin-documents-get.md) | 🔒 | Datos de un documento y enlace público firmado |
| PATCH | [`/admin/documents/{id}`](admin-documents-rename.md) | 🔒 | Renombra o mueve un documento (sin reindexar) |
| DELETE | [`/admin/documents/{id}`](admin-documents-delete.md) | 🔒 | Elimina un documento y sus fragmentos del índice |
| POST | [`/admin/index`](admin-index.md) | 🔒 | Indexa documentos nuevos o modificados y registra la ejecución |
| GET | [`/admin/indexations`](admin-indexations.md) | 🔒 | Historial de indexaciones (paginado) |
| GET | [`/admin/indexations/latest`](admin-indexations.md#get-adminindexationslatest) | 🔒 | Última indexación |
| GET | [`/admin/indexations/{id}`](admin-indexations.md#get-adminindexationsid) | 🔒 | Una indexación con detalle |
| POST | [`/ask`](ask.md) | 🔒 | Pregunta al RAG y devuelve respuesta con fuentes (con enlace) |
| GET, HEAD | [`/files/{name}`](files.md) | firma | **Público vía nginx.** Entrega un documento con un enlace firmado y vigente |

## Rutas del cliente Next.js (opcional)

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | [`/api/chat`](next-api-chat.md) | — | Proxy de servidor hacia `/ask` del RAG |

## Identificador de documento
Las rutas `/admin/documents/{id}` usan como `id` el nombre del objeto en MinIO codificado en base64url sin relleno (`normativa/ley-rep.pdf` → `bm9ybWF0aXZhL2xleS1yZXAucGRm`). Lo devuelven el listado y la subida; no hace falta calcularlo.

## Flujo típico
1. `POST /admin/documents` — subir uno o varios documentos.
2. `GET /admin/documents` — ver cuáles están `not_indexed` u `outdated`.
3. `POST /admin/index` — indexar lo nuevo o modificado.
4. `GET /admin/indexations/latest` — fecha y resultado de la última indexación.
5. `POST /ask` — consultar; cada fuente trae un enlace público firmado.

## Formato de errores
FastAPI devuelve los errores como `{"detail": "<mensaje>"}`. Los errores de validación (`422`) devuelven `detail` como lista de objetos con `loc`, `msg` y `type`.
