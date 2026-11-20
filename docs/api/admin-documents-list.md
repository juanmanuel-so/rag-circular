# GET /admin/documents 🔒

Lista los documentos del bucket (solo `.pdf`, `.docx`, `.txt`) en orden alfabético, con paginación por cursor y su estado de indexación.

- **Auth:** cabecera `X-API-Key`

## Parámetros de consulta

| Parámetro | Tipo | Por defecto | Descripción |
|---|---|---|---|
| `limit` | entero 1–100 | `20` | Documentos por página |
| `cursor` | string | — | Valor `next_cursor` de la página anterior. Omitir para la primera página. |
| `prefix` | string | `""` | Limita el listado a una carpeta, p. ej. `normativa` (incluye subcarpetas) |

MinIO no permite saltar a la página N, por eso la paginación es por cursor: cada página devuelve el cursor de la siguiente.

## Respuesta `200`
```json
{
  "items": [
    {
      "id": "bm9ybWF0aXZhL2xleS1yZXAucGRm",
      "name": "normativa/ley-rep.pdf",
      "extension": "pdf",
      "size": 482113,
      "etag": "9b2cf535f27731c974343645a3985328",
      "last_modified": "2026-11-19T14:02:11.000000+00:00",
      "content_type": null,
      "index_status": "indexed",
      "chunks": 42
    }
  ],
  "next_cursor": "bm9ybWF0aXZhL2xleS1yZXAucGRm"
}
```

| Campo | Descripción |
|---|---|
| `id` | Identificador para las demás rutas: el nombre del objeto en base64url sin relleno |
| `name` | Nombre del objeto en MinIO (con carpeta) |
| `size` | Bytes |
| `content_type` | Siempre `null` en el listado (MinIO no lo devuelve al listar); ver [`GET /admin/documents/{id}`](admin-documents-get.md) |
| `index_status` | `indexed` (indexado y sin cambios), `outdated` (cambió desde la última indexación), `not_indexed` (nunca indexado o sin texto extraíble) |
| `chunks` | Fragmentos en el índice (0 si no está indexado) |
| `next_cursor` | Cursor de la página siguiente, o `null` si es la última |

Si el bucket aún no existe, devuelve `{"items": [], "next_cursor": null}`.

## Errores

| Código | Causa |
|---|---|
| `400` | `cursor` o `prefix` inválido |
| `401` | `X-API-Key` ausente o incorrecta |
| `422` | `limit` fuera de rango |

## Ejemplo
```bash
curl "http://localhost:8000/admin/documents?limit=20" -H "X-API-Key: TU_RAG_API_KEY"
# página siguiente
curl "http://localhost:8000/admin/documents?limit=20&cursor=NEXT_CURSOR" -H "X-API-Key: TU_RAG_API_KEY"
```
