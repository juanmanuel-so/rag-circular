# POST /admin/documents 🔒

Sube un documento al bucket de MinIO (`MINIO_BUCKET`, por defecto `documentos`). Si el bucket no existe, se crea. El documento **no se indexa** automáticamente: llamar después a [`POST /admin/index`](admin-index.md).

- **Auth:** cabecera `X-API-Key`
- **Content-Type:** `multipart/form-data`

## Campos del formulario

| Campo | Tipo | Obligatorio | Por defecto | Descripción |
|---|---|---|---|---|
| `file` | archivo | sí | — | Documento `.pdf`, `.docx` o `.txt`. Máximo 15 MiB. |
| `prefix` | texto | no | `""` | Carpeta dentro del bucket, p. ej. `normativa/2025`. Segmentos con letras, números, `_`, `-`, `.` o espacios; no se permiten `..` ni segmentos vacíos. |
| `overwrite` | booleano | no | `false` | Si es `true`, reemplaza un documento con el mismo nombre. Al reindexar, el cambio de ETag hace que se regenere su índice. |

`id` es el identificador para [ver](admin-documents-get.md), [renombrar](admin-documents-rename.md) o [eliminar](admin-documents-delete.md) el documento.

El nombre del objeto es el nombre base del archivo subido (se descarta cualquier ruta), precedido por `prefix/` si se indica.

## Respuesta `201`
```json
{
  "id": "bm9ybWF0aXZhL2xleS1yZXAucGRm",
  "bucket": "documentos",
  "document": "normativa/ley-rep.pdf",
  "size": 482113,
  "etag": "9b2cf535f27731c974343645a3985328"
}
```

## Errores

| Código | Causa |
|---|---|
| `400` | Nombre de archivo o prefijo inválido, o archivo vacío |
| `401` | `X-API-Key` ausente o incorrecta |
| `409` | Ya existe un documento con ese nombre y `overwrite` es `false` |
| `413` | El archivo supera 15 MiB |
| `415` | Extensión distinta de PDF, DOCX o TXT |
| `422` | Falta el campo `file` u otro campo tiene un tipo inválido |

## Ejemplos
Subida simple:
```bash
curl -X POST http://localhost:8000/admin/documents \
  -H "X-API-Key: TU_RAG_API_KEY" \
  -F "file=@./ley-rep.pdf"
```

En una carpeta y reemplazando si existe:
```bash
curl -X POST http://localhost:8000/admin/documents \
  -H "X-API-Key: TU_RAG_API_KEY" \
  -F "file=@./ley-rep.pdf" \
  -F "prefix=normativa" \
  -F "overwrite=true"
```

Subir todos los PDF de una carpeta e indexar:
```bash
for f in ./docs-origen/*.pdf; do
  curl -sS -X POST http://localhost:8000/admin/documents -H "X-API-Key: TU_RAG_API_KEY" -F "file=@$f"; echo
done
curl -X POST http://localhost:8000/admin/index -H "X-API-Key: TU_RAG_API_KEY"
```

## Notas
- Validar la extensión no garantiza el contenido: un PDF escaneado sin texto se sube sin problema pero fallará al indexar ("puede requerir OCR").
- El archivo se lee completo en memoria (máx. 15 MiB) antes de enviarlo a MinIO.
