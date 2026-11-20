# Historial de indexaciones 🔒

Cada llamada a [`POST /admin/index`](admin-index.md) queda registrada en la tabla `indexations`. Estas rutas la consultan; la más útil para la interfaz es `GET /admin/indexations/latest` ("última indexación").

- **Auth:** cabecera `X-API-Key` en todas

## Tabla `indexations`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | bigint | Identificador incremental |
| `started_at` | timestamptz | Inicio |
| `finished_at` | timestamptz | Fin (`null` mientras corre) |
| `status` | text | `running`, `completed` o `failed` |
| `indexed_count` | int | Documentos indexados o reindexados |
| `skipped_count` | int | Documentos sin cambios |
| `removed_count` | int | Documentos quitados del índice porque ya no estaban en el bucket |
| `error_count` | int | Documentos con error (sin texto, demasiado grandes, etc.) |
| `details` | jsonb | Listas `indexed`, `skipped`, `removed`, `errors` |
| `error` | text | Motivo si `status = failed` (`interrumpida` si el servicio se reinició durante la ejecución) |

Se crea automáticamente al arrancar el servicio.

## GET /admin/indexations/latest
Última indexación (cualquier estado) con `details`, o `null` si nunca se indexó.

```json
{
  "id": 12,
  "started_at": "2026-11-19T15:00:02.118+00:00",
  "finished_at": "2026-11-19T15:00:41.902+00:00",
  "status": "completed",
  "indexed_count": 2,
  "skipped_count": 14,
  "removed_count": 1,
  "error_count": 1,
  "error": null,
  "details": {
    "indexed": [{"document": "normativa/ley-rep.pdf", "chunks": 42}],
    "skipped": ["guia.docx"],
    "removed": ["antiguo.pdf"],
    "errors": [{"document": "escaneado.pdf", "error": "Documento sin texto extraíble (puede requerir OCR)"}]
  }
}
```

```bash
curl http://localhost:8000/admin/indexations/latest -H "X-API-Key: TU_RAG_API_KEY"
```

## GET /admin/indexations
Historial, de la más reciente a la más antigua, sin `details`.

| Parámetro | Tipo | Por defecto | Descripción |
|---|---|---|---|
| `limit` | entero 1–100 | `20` | Elementos por página |
| `cursor` | entero | — | `next_cursor` de la página anterior |

```json
{"items": [{"id": 12, "started_at": "…", "finished_at": "…", "status": "completed", "indexed_count": 2, "skipped_count": 14, "removed_count": 1, "error_count": 1, "error": null}], "next_cursor": 11}
```

```bash
curl "http://localhost:8000/admin/indexations?limit=10" -H "X-API-Key: TU_RAG_API_KEY"
```

## GET /admin/indexations/{id}
Una indexación con `details`. `404` si no existe.

```bash
curl http://localhost:8000/admin/indexations/12 -H "X-API-Key: TU_RAG_API_KEY"
```

## Errores comunes

| Código | Causa |
|---|---|
| `401` | `X-API-Key` ausente o incorrecta |
| `404` | (`/{id}`) indexación inexistente |
| `422` | Parámetros fuera de rango |
