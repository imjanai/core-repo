# syntax=docker/dockerfile:1
# Eén image voor api, worker én beat: dezelfde code, dezelfde lockfile,
# alleen het command verschilt (zie infra/docker-compose.yml).
FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

# Eerst alleen de manifesten: deze laag met alle dependencies wordt gecached
# zolang uv.lock niet verandert, wat `docker compose build` bijna altijd zo is.
# Het project zelf heeft geen build-system, dus er valt niets te installeren
# zolang de bron nog niet gekopieerd is.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 8080

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
