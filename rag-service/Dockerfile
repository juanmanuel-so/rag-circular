FROM python:3.11-slim
WORKDIR /code
COPY requirements.txt .
# CPU-only torch first (~200 MB instead of ~5 GB of CUDA packages; the server has
# no GPU). sentence-transformers then finds torch already installed.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt
COPY app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
