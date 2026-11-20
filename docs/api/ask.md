# POST /ask 🔒

Busca los fragmentos más similares a la pregunta y genera una respuesta con el LLM configurado (`OPENAI_MODEL`), citando las fuentes como `[Fuente N]`.

- **Auth:** cabecera `X-API-Key`
- **Content-Type:** `application/json`

## Body

| Campo | Tipo | Obligatorio | Por defecto | Restricciones |
|---|---|---|---|---|
| `question` | string | sí | — | 3–2000 caracteres |
| `top_k` | integer | no | `5` | 1–10; número de fragmentos recuperados |

```json
{"question": "¿Qué obligaciones establece la Ley REP para envases?", "top_k": 5}
```

## Respuesta `200`
```json
{
  "answer": "La Ley REP establece metas de recolección... [Fuente 1]",
  "sources": [
    {
      "document": "normativa/ley-rep.pdf",
      "page": 12,
      "chunk_index": 31,
      "score": 0.8123,
      "excerpt": "Artículo 9.- Los productores de envases...",
      "url": "https://piec.ulagos.cl/files/normativa/ley-rep.pdf?exp=1795104000&sig=3f1c…"
    }
  ]
}
```

| Campo | Descripción |
|---|---|
| `answer` | Respuesta generada. Si no hay documentos indexados: `"Todavía no hay documentos indexados para responder esta consulta."` con `sources` vacío |
| `sources[].document` | Nombre del objeto en MinIO |
| `sources[].page` | Página (solo PDF; `null` en DOCX/TXT) |
| `sources[].chunk_index` | Índice del fragmento dentro del documento |
| `sources[].score` | Similitud coseno (0–1, mayor es más similar) |
| `sources[].excerpt` | Primeros 350 caracteres del fragmento |
| `sources[].url` | Enlace público firmado al documento ([`/files`](files.md)), válido `FILES_URL_TTL` segundos; se puede mostrar directamente al usuario final. `null` si no se pudo generar |

## Errores

| Código | Causa |
|---|---|
| `401` | `X-API-Key` ausente o incorrecta |
| `422` | `question` o `top_k` fuera de rango |
| `500` | Fallo del proveedor LLM (clave inválida, timeout de 45 s, etc.) |

## Ejemplo
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: TU_RAG_API_KEY" \
  -d '{"question":"¿Qué obligaciones establece la Ley REP para envases?","top_k":5}'
```

## Notas
- Las citas las genera el LLM y no se verifican automáticamente; usar `sources` como evidencia.
- Los fragmentos recuperados se envían al proveedor LLM configurado.
