# syntax=docker/dockerfile:1
#
# diligence-reader: the API on port 8000, and the command each run starts.
#
#   docker build -f deploy/Dockerfile -t diligence-reader .
#   docker run -p 8000:8000 -v <runs>:/app/runs ghcr.io/muhanad-husn/diligence-reader
#
# Layers go in the order they change: the system layer, then the Python packages read from
# pyproject.toml alone, then the code. A code-only change rebuilds the last layer only. The
# build context is the whitelist in Dockerfile.dockerignore. The PDF export needs no system
# library: pandoc ships inside pypandoc-binary and Typst inside the typst wheel. Claude Code is
# not in the image, so claude-code/ models are for a local install. The saved model settings
# live in the runs volume so that they outlive the container.

FROM python:3.14-slim@sha256:a2b82f3c48559aa0a8446d9af49826b6e2b2016f4cd2afabfe6013ec53729170 AS deps

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# The system layer: Debian's security fixes since the base was cut, pip removed since uv
# installs everything (pip's vendored packages carry findings of their own), and the user.
RUN apt-get update \
    && apt-get -y upgrade \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip uninstall -y pip \
    && rm -rf /usr/local/lib/python3.13/ensurepip \
    && useradd --uid 10001 --user-group --create-home --home-dir /home/app app \
    && mkdir -p /app/runs \
    && chown app:app /app/runs

WORKDIR /app

COPY pyproject.toml /app/
RUN --mount=from=ghcr.io/astral-sh/uv:0.12.23@sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    uv pip install -r pyproject.toml

# The tests' image: the same packages with pytest, run with tests/ and samples/ mounted.
FROM deps AS test
RUN --mount=from=ghcr.io/astral-sh/uv:0.12.23@sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    uv pip install -r pyproject.toml --extra dev
ENV PYTHONPATH=/app/src:/app \
    RLM_RUNS=/app/runs
COPY . /app/
USER app

FROM deps AS runtime
ENV PYTHONPATH=/app/src:/app \
    RLM_RUNS=/app/runs \
    RLM_SETTINGS=/app/runs/settings.json
COPY . /app/
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
