# ============================================================================
# Cancer Health Dashboard  — Dockerfile
# Target: VPS deployment via Docker Compose + Nginx reverse proxy
# Registry: ghcr.io/dvouna/geospatial_analytical_dashboard
# ============================================================================

FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies required by geospatial libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev \
    libproj-dev \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user so the container doesn't run as root
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Install Python dependencies before copying source (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Ensure the non-root user owns the app directory
RUN chown -R appuser:appuser /app
USER appuser

# Streamlit listens on 8501; Nginx proxies external traffic to this port
EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
