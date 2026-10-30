# ==============================================================================
# SafeGate — Multi-Stage Production Dockerfile
# ==============================================================================
# Hardened container image adhering to CIS Docker benchmark guidelines:
# 1. Non-root user execution (least privilege).
# 2. Minimal debian-slim base to reduce CVE attack surface.
# 3. Suppressed bytecode generation and unbuffered I/O for real-time logging.
# ==============================================================================

FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency requirements
COPY requirements.txt .

# Install dependencies into a separate directory for clean transfer
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ==============================================================================
# Final Runtime Container
# ==============================================================================
FROM python:3.11-slim AS runtime

# Install runtime system packages (OpenCV headless dependencies and ffmpeg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root service user and group
RUN groupadd -r -g 10001 safegate && \
    useradd -r -u 10001 -g safegate -d /app -s /sbin/nologin safegate

WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source code, dashboard, and configuration
COPY app/ ./app/
COPY dashboard/ ./dashboard/
COPY .env.example ./.env

# Create persistent storage directories with proper ownership
RUN mkdir -p quarantine review published && \
    chown -R safegate:safegate /app

# Enforce secure environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0

# Switch to non-privileged user
USER safegate

# Expose service port
EXPOSE 8000

# Health check verifies that the gateway is responsive
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

# Launch SafeGate via Uvicorn
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
