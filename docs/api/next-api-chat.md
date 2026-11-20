# POST /api/chat (cliente Next.js)

Ruta de servidor de `next-app` (`next-app/app/api/chat/route.ts`) que reenvía la pregunta a [`POST /ask`](ask.md) del servicio RAG añadiendo la `X-API-Key` desde el servidor, para que la clave nunca llegue al navegador.

- **Base URL:** `http://localhost:3000` (`npm run dev`)
- **Auth:** ninguna en el MVP. Añadir autenticación antes de exponerla públicamente.
- **Content-Type:** `application/json`
- **Variables de entorno:** `RAG_API_URL`, `RAG_API_KEY` (en `next-app/.env.local`)

## Body
| Campo | Tipo | Obligatorio | Restricciones |
|---|---|---|---|
| `question` | string | sí | 3–2000 caracteres (se recorta para validar el mínimo) |

`top_k` siempre se envía como `5`.

## Respuesta `200`
La misma que [`POST /ask`](ask.md), con `Cache-Control: no-store`.

## Errores
| Código | Body | Causa |
|---|---|---|
| `400` | `{"error": "JSON inválido"}` | El body no es JSON |
| `400` | `{"error": "Pregunta inválida"}` | Falta `question` o está fuera de rango |
| `502` | `{"error": "Servicio RAG no disponible"}` | El RAG respondió con un código distinto de 2xx |
| `502` | `{"error": "Error al conectar con el servicio RAG"}` | Error de red o timeout de 60 s |

## Ejemplo
```bash
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"¿Qué es la economía circular?"}'
```
