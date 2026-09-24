FROM ghcr.io/astral-sh/uv:0.12.16 AS uv
FROM python:3.14.0-slim-bookworm AS build
COPY --from=uv /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev

FROM python:3.14.0-slim-bookworm AS runtime
RUN groupadd --gid 10001 factory && useradd --uid 10001 --gid 10001 --no-create-home factory
WORKDIR /app
COPY --from=build --chown=10001:10001 /app /app
COPY --chown=10001:10001 config.yaml ./
ENV PATH="/app/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER 10001:10001
ENTRYPOINT ["factory"]
CMD ["--help"]
