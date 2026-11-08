FROM python:3.13-slim AS builder
RUN pip install --no-cache-dir uv==0.11.32
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /srv/test-hub
COPY pyproject.toml uv.lock .python-version README.md ./
RUN uv sync --frozen --no-dev

FROM python:3.13-slim
RUN useradd --create-home --uid 1000 hub
WORKDIR /srv/test-hub
COPY --from=builder /srv/test-hub/.venv ./.venv
COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
COPY target_api ./target_api
ENV PATH="/srv/test-hub/.venv/bin:$PATH" PYTHONPATH=/srv/test-hub PYTHONUNBUFFERED=1
USER hub
EXPOSE 8000
CMD ["uvicorn", "app.bootstrap.api:app", "--host", "0.0.0.0", "--port", "8000"]
