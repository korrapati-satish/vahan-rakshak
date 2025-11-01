# Deployable Dockerfile for Cloud Run
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# System deps (kept minimal; wheels should satisfy numpy/pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    make \
    python3-dev \
    libyaml-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Expose default Cloud Run port
EXPOSE 8080

# Start FastAPI app
CMD ["uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8080"]
