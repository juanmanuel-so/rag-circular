# PATCH /admin/documents/{id} 🔒

Renombra un documento (o lo mueve de carpeta). Si estaba indexado, sus fragmentos se trasladan al nuevo nombre, así que **no hace falta reindexar**.

- **Auth:** cabecera `X-API-Key`
- **Content-Type:** `application/json`

## Body

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `name` | string (1–500) | sí | Nuevo nombre |

Reglas para `name`:
- **Sin `/`:** solo cambia el nombre; el documento se queda en su carpeta. `"Ley REP 2025"` sobre `normativa/ley-rep.pdf` → `normativa/Ley REP 2025.pdf`.
- **Con `/`:** la parte anterior a la última `/` es la nueva carpeta. `"archivo/ley-rep"` → `archivo/ley-rep.pdf`. Para mover a la raíz del bucket, empezar con `/`: `"/ley-rep"` → `ley-rep.pdf`.
- **Extensión:** si se omite, se conserva la original. Si se indica, debe ser la misma (no se puede convertir un PDF en DOCX renombrándolo).

## Respuesta `200`
Los datos del documento con su nuevo nombre, en el mismo formato que [`GET /admin/documents/{id}`](admin-documents-get.md). **El `id` cambia**, porque se deriva del nombre.

## Errores

| Código | Causa |
|---|---|
| `400` | `id`, nombre o carpeta inválidos |
| `401` | `X-API-Key` ausente o incorrecta |
| `404` | El documento no existe |
| `409` | Ya existe un documento con el nombre destino |
| `415` | Se intentó cambiar la extensión |

## Ejemplo
```bash
curl -X PATCH http://localhost:8000/admin/documents/bm9ybWF0aXZhL2xleS1yZXAucGRm \
  -H "X-API-Key: TU_RAG_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "Ley REP 2025"}'
```

## Notas
MinIO no renombra objetos: se copia al nombre nuevo y luego se borra el original. Los enlaces firmados emitidos para el nombre anterior dejan de funcionar.
