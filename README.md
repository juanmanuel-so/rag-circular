# RAG mínimo para la Plataforma Inteligente de Economía Circular de la Región de Los Lagos

Prototipo con MinIO → ingesta PDF/DOCX/TXT → embeddings multilingües → PostgreSQL/pgvector → API FastAPI.

El stack que se levanta con Docker es solo el RAG: `postgres` (pgvector), `minio` (almacenamiento de documentos) y `rag` (FastAPI en el puerto 8000). El cliente Next.js es opcional y no forma parte del arranque (ver al final).

## Requisitos
- Docker + Docker Compose
- Clave de un LLM compatible con OpenAI Chat Completions
- Internet durante el primer arranque para descargar el modelo de embeddings (~centenares de MB)

## 1. Configurar
```bash
cp .env.example .env
```
Editar `.env` y establecer valores reales para `POSTGRES_PASSWORD`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `RAG_API_KEY` y `OPENAI_API_KEY`. Para una API OpenAI-compatible local, configurar `OPENAI_BASE_URL` y `OPENAI_MODEL`. **`.env` está en `.gitignore`: no subirlo nunca al repositorio.**

Generar una `RAG_API_KEY` aleatoria:
```bash
openssl rand -hex 32
```

## 2. Arrancar el RAG
```bash
docker compose up --build -d
```
Seguir los logs hasta que uvicorn indique `Application startup complete` (el primer arranque descarga el modelo multilingüe):
```bash
docker compose logs -f rag
```
Comprobar que responde:
```bash
curl http://localhost:8000/health
```
Respuesta esperada: `{"status":"ok"}`. La documentación interactiva queda en http://localhost:8000/docs.

## 3. Subir documentos a MinIO
Abrir http://localhost:9001 e iniciar sesión con `MINIO_ROOT_USER` y `MINIO_ROOT_PASSWORD` de `.env`. Crear el bucket `documentos` (o el configurado en `MINIO_BUCKET`) y subir PDF, DOCX o TXT con texto extraíble. Los PDF escaneados requieren OCR externo. Límite MVP: 15 MiB por documento, 300 páginas por PDF.

## 4. Indexar
```bash
curl -X POST http://localhost:8000/admin/index \
  -H "X-API-Key: TU_RAG_API_KEY"
```
Los documentos modificados se reindexan usando su ETag; los no modificados se omiten. **Limitación:** los documentos eliminados del bucket no se eliminan automáticamente del índice.

## 5. Consultar
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: TU_RAG_API_KEY" \
  -d '{"question":"¿Qué oportunidades de valorización de residuos se mencionan?","top_k":5}'
```
Ejemplo de respuesta JSON: `{ "answer": "... [Fuente 1]", "sources": [{"document":"informe.pdf","page":3,"chunk_index":4,"score":0.78,"excerpt":"..."}] }`.

## Detener y reiniciar
```bash
docker compose down        # detiene los servicios, conserva datos
docker compose down -v     # borra también la base, los documentos y la caché del modelo
docker compose up --build -d rag   # reconstruir solo el servicio RAG tras cambiar el código
```

## Consideraciones importantes antes de producción
- **NO hay multi-tenancy, RLS ni separación de empresas.** Todos los documentos indexados son consultables por quien acceda a la API con la clave. Usar solo documentos públicos o de prueba hasta implementar autorización por organización y recurso.
- **NO hay autenticación de usuarios** (ni en la API más allá de la API key, ni en Next.js), ni rate limiting, ni protección antiabuso. Agregar antes de exponer públicamente.
- La API de indexación es síncrona. Mover a un worker/cola de tareas para documentos numerosos y limitar concurrencia.
- No hay OCR, búsqueda híbrida, reranking, evaluación de citas ni control de vigencia normativa.
- Las citas son generadas por el LLM y no están verificadas automáticamente; la lista `sources` permite mostrar la evidencia recuperada.
- MinIO se expone solo en loopback para desarrollo local; usar TLS, usuarios con permisos mínimos y redes privadas en despliegue real. Evitar credenciales root en el servicio RAG.
- El modelo de embeddings debe mantenerse estable: si cambia EMBEDDING_MODEL, regenerar la tabla e índices, incluyendo su dimensión.
- El índice pgvector utiliza búsqueda exacta para simplificar el MVP; añadir HNSW y medición de calidad al escalar.
- Los fragmentos se generan por longitud de caracteres, no por tokens; mejorar con segmentación estructural.
- Los archivos de texto recuperados se envían al proveedor LLM configurado; revisar privacidad y acuerdos antes de procesar datos confidenciales.

## Opcional: cliente Next.js
`next-app/` contiene un chat de ejemplo que consume la API. No se levanta con Docker; requiere Node.js 20+ y el RAG ya corriendo.
```bash
cd next-app
cp .env.local.example .env.local
# Configurar RAG_API_KEY igual a .env y RAG_API_URL=http://127.0.0.1:8000
npm install
npm run dev
```
Abrir http://localhost:3000. La API key se utiliza solo en la ruta de servidor `app/api/chat/route.ts`; no se envía al navegador.
