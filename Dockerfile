# syntax=docker/dockerfile:1.7
ARG PYTHON_VERSION=3.12

FROM --platform=$BUILDPLATFORM python:${PYTHON_VERSION}-slim AS runtime

# Runtime env
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    PIP_NO_CACHE_DIR=1

# Install tiny init and a small font set for Matplotlib text rendering
RUN apt-get update \
    && apt-get install -y --no-install-recommends tini fonts-dejavu-core wget \
    && rm -rf /var/lib/apt/lists/*

# Isolated virtualenv for smaller/cleaner image
ENV VENV_PATH=/opt/venv
RUN python -m venv "$VENV_PATH"
ENV PATH="$VENV_PATH/bin:$PATH"

# Python deps (keep in sync with pyproject [project.dependencies])
RUN pip install --upgrade pip \
    && pip install \
        fastapi \
        "uvicorn[standard]" \
        matplotlib \
        requests

WORKDIR /app
# App sources (keep context minimal)
COPY app.py ./
# Optional reference JSON files (safe no-op if absent)
COPY *.json ./

# Non-root user
RUN groupadd -r app && useradd -r -g app app \
    && chown -R app:app /app "$VENV_PATH"
USER app

EXPOSE 8000

# Simple healthcheck using curl
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8000/healthz >/dev/null || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
