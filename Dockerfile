# ==============================================================================
# LandGuard AI — Hugging Face Spaces & Production Dockerfile
# Optimized for 16 GB RAM + 2 vCPU with full bilingual Tesseract (Bengali + English)
# ==============================================================================

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    HOME=/home/user

# Install OS libraries, OpenCV dependencies, and full bilingual Tesseract OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    tesseract-ocr-ben \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for Hugging Face Spaces security
RUN useradd -m -u 1000 user
WORKDIR $HOME/app

# Install Python requirements
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code and seed data
COPY --chown=user:user . .

# Ensure data directories exist and are writable
RUN mkdir -p data/uploads/deeds data/full data/targeted_expansion models && \
    chmod -R 777 data

# Switch to non-root user
USER user

# Hugging Face Spaces default port
EXPOSE 7860

# Launch FastAPI ASGI server
CMD ["uvicorn", "src.landguard_web.app:app", "--host", "0.0.0.0", "--port", "7860"]
