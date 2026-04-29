FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download EasyOCR models (CRAFT + English) so no runtime download needed
RUN python -c "import easyocr; easyocr.Reader(['en'], gpu=False, download_enabled=True, verbose=True, model_storage_directory='/app/ml/models')"

COPY --chown=app:app . .

RUN mkdir -p /app/media /app/media/plate_debug /app/ml/models /app/.EasyOCR \
    && chown -R app:app /app/media /app/ml/models /app/.EasyOCR

USER app

EXPOSE 8009

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8009/health/')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8009", "--workers", "2"]
