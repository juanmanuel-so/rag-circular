# GET /files/{name} (público, firmado)

Entrega el contenido de un documento a **cualquier usuario**, sin API key, siempre que el enlace esté firmado por esta API y no haya expirado. Es la única ruta del RAG que nginx expone a internet: el resto (rutas `/admin/*` y `/ask`) sigue siendo privado dentro de la red Docker `web`.

- **Métodos:** `GET` (contenido) y `HEAD` (solo cabeceras)
- **Auth:** firma en la URL

Los enlaces no se construyen a mano: los devuelven [`GET /admin/documents/{id}`](admin-documents-get.md) (`url`) y [`POST /ask`](ask.md) (`sources[].url`).

## Formato del enlace
```
{FILES_PUBLIC_BASE_URL}/files/{nombre-url-encoded}?exp={unix}&sig={hex}
```

- `exp`: momento de expiración en segundos Unix (`ahora + FILES_URL_TTL`).
- `sig`: `HMAC-SHA256(FILES_SIGNING_SECRET, "{nombre}\n{exp}")` en hexadecimal. Cambiar el nombre o `exp` invalida la firma.

## Respuesta `200`
El archivo, en streaming, con estas cabeceras:

| Cabecera | Valor |
|---|---|
| `Content-Type` | El guardado en MinIO (o según la extensión) |
| `Content-Length` | Tamaño en bytes |
| `Content-Disposition` | `inline; filename*=UTF-8''<nombre>` (el navegador lo abre; "Guardar como" usa ese nombre) |
| `Cache-Control` | `private, max-age=<segundos restantes, máx. 300>` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `no-referrer` |

## Errores

| Código | Body | Causa |
|---|---|---|
| `403` | `{"detail": "Enlace inválido"}` | Falta `exp`/`sig`, o la firma no coincide |
| `403` | `{"detail": "Enlace expirado"}` | `exp` ya pasó |
| `404` | `{"detail": "Documento no encontrado"}` | El documento se eliminó o renombró |
| `403` (nginx) | página de nginx | Método distinto de GET/HEAD |

## Configuración

| Variable (`.env`) | Por defecto | Descripción |
|---|---|---|
| `FILES_SIGNING_SECRET` | — (obligatoria) | Secreto de firma, distinto de `RAG_API_KEY`. Generar con `openssl rand -hex 32`. Cambiarlo invalida todos los enlaces emitidos. |
| `FILES_PUBLIC_BASE_URL` | `http://localhost:8000` | Origen público de los enlaces. En el servidor: `https://piec.ulagos.cl` |
| `FILES_URL_TTL` | `900` | Vigencia en segundos (60–86400) |

## nginx (repo docker-proxy)
En el servidor por defecto de `nginx/default.conf.http` y `.https`:
```nginx
location ^~ /files/ {
    limit_except GET HEAD { deny all; }
    set $upstream http://rag-circular:8000;
    proxy_pass $upstream;          # sin URI: la ruta llega intacta
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_buffering off;
}
```
`^~` hace que esta ruta tenga prioridad sobre `location /` (encircular). Solo `/files/` llega al RAG.

## Ejemplo
```bash
URL=$(curl -s http://localhost:8000/admin/documents/ID -H "X-API-Key: TU_RAG_API_KEY" | python3 -c "import sys,json;print(json.load(sys.stdin)['url'])")
curl -I "$URL"         # cabeceras
curl -o doc.pdf "$URL" # descarga
```

## Seguridad
- Quien tenga el enlace puede abrir el documento hasta que expire; no hay revocación individual (salvo rotar `FILES_SIGNING_SECRET`, que invalida todos).
- La firma se compara en tiempo constante.
