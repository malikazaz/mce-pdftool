# MedConnect PDF Assembly Tool — single-service image.
# Stage 1 builds the React/Vite frontend; stage 2 is the Python API runtime with
# Tesseract (incl. the Bulgarian language pack) that also serves the built frontend.

# --- Stage 1: build the frontend ---
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build   # -> /app/frontend/dist

# --- Stage 2: backend runtime ---
FROM python:3.12-slim AS runtime

# Tesseract OCR + English & Bulgarian language data (needed for auto-recognition).
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-bul \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

# Bundle the built SPA so FastAPI serves it from the same origin as /api.
COPY --from=frontend /app/frontend/dist ./static

ENV MCE_STATIC_DIR=/app/static \
    MCE_TESSERACT_CMD=/usr/bin/tesseract \
    MCE_OCR_DPI=300

EXPOSE 8000
# Render injects $PORT; default to 8000 for local `docker run`.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
