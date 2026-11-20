# DELETE /admin/documents/{id} 🔒

Elimina un documento del bucket **y sus fragmentos del índice**, así deja de aparecer en las respuestas de [`/ask`](ask.md) de inmediato. No se puede deshacer.

- **Auth:** cabecera `X-API-Key`
- **Body:** ninguno

## Respuesta `204`
Sin contenido.

## Errores

| Código | Causa |
|---|---|
| `400` | `id` mal formado |
| `401` | `X-API-Key` ausente o incorrecta |
| `404` | El documento no existe |

## Ejemplo
```bash
curl -X DELETE http://localhost:8000/admin/documents/bm9ybWF0aXZhL2xleS1yZXAucGRm \
  -H "X-API-Key: TU_RAG_API_KEY"
```

## Notas
Los enlaces firmados ya emitidos para el documento responden `404` a partir de ese momento.
