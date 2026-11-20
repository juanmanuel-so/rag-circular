# GET /health

Comprobación de estado del servicio. No verifica la conexión con PostgreSQL ni MinIO; solo indica que la API está aceptando peticiones.

- **Auth:** no
- **Body:** ninguno

## Respuesta `200`
```json
{"status": "ok"}
```

## Ejemplo
```bash
curl http://localhost:8000/health
```
