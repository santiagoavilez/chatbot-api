FROM python:3.13-slim AS builder

WORKDIR /app

# Copy dependencies files
COPY pyproject.toml uv.lock ./

# install uv
ENV PATH="/app/.venv/bin:$PATH"
RUN pip install uv --no-deps

# install dependencies
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code
COPY app/ ./app/

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

CMD uvicorn app.main:app --host ${API_HOST} --port ${API_PORT}
