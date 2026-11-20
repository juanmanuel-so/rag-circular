# POST /admin/index 🔒

Recorre el bucket de MinIO, extrae el texto de los documentos `.pdf`, `.docx` y `.txt`, los divide en fragmentos, calcula embeddings y los guarda en PostgreSQL/pgvector (tabla `chunks`).

- **Auth:** cabecera `X-API-Key`
- **Body:** ninguno

## Comportamiento
- Los documentos cuyo ETag no ha cambiado desde la última indexación se omiten (`skipped`).
- Los documentos modificados se reindexan: se borran sus fragmentos anteriores y se insertan los nuevos.
- Otras extensiones se ignoran silenciosamente.
- Límites: 15 MiB por documento y 300 páginas por PDF.
- Fragmentos de ~1200 caracteres con solapamiento de 200.
- Los documentos que ya no están en el bucket (borrados desde la consola de MinIO, por ejemplo) se quitan del índice (`removed`).
- Cada ejecución queda registrada en la tabla `indexations` ([historial](admin-indexations.md)), incluso si falla.
- Solo puede haber una indexación a la vez (advisory lock de Postgres); una segunda llamada concurrente recibe `409`.
- La ejecución es síncrona; con muchos documentos la petición puede tardar.

## Respuesta `200`
```json
{
  "indexation_id": 12,
  "started_at": "2026-11-19T15:00:02.118+00:00",
  "finished_at": "2026-11-19T15:00:41.902+00:00",
  "indexed": [{"document": "normativa/ley-rep.pdf", "chunks": 42}],
  "skipped": ["guia-reciclaje.docx"],
  "removed": ["antiguo.pdf"],
  "errors": [{"document": "escaneado.pdf", "error": "Documento sin texto extraíble (puede requerir OCR)"}]
}
```

| Campo | Descripción |
|---|---|
| `indexation_id` | `id` de la fila en `indexations` |
| `started_at`, `finished_at` | Inicio y fin (ISO 8601) |
| `removed` | Documentos quitados del índice porque ya no están en el bucket |
| `indexed` | Documentos procesados en esta ejecución y número de fragmentos generados |
| `skipped` | Documentos sin cambios desde la última indexación |
| `errors` | Documentos que fallaron, con el motivo (máx. 250 caracteres) |

## Errores

| Código | Causa |
|---|---|
| `401` | `X-API-Key` ausente o incorrecta |
| `404` | El bucket no existe (subir un documento con [`POST /admin/documents`](admin-documents.md) lo crea) |
| `409` | Ya hay una indexación en curso |
| `500` | Error inesperado; la fila queda `failed` con el motivo en [`/admin/indexations/latest`](admin-indexations.md) |

## Ejemplo
```bash
curl -X POST http://localhost:8000/admin/index \
  -H "X-API-Key: TU_RAG_API_KEY"
```
