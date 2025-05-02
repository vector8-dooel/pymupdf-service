FROM registry.access.redhat.com/ubi9/python-312

# Set environment variables
ENV POETRY_VERSION=1.8.2 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=true \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

USER 0

# Install system packages and Poetry
RUN python -m pip install --upgrade pip && \
    pip install "poetry==$POETRY_VERSION"

WORKDIR /app

# Copy project metadata for better caching
COPY ../pyproject.toml poetry.lock* ./

# Install dependencies into project .venv
RUN poetry install --no-interaction --no-ansi

# Copy application code
COPY .. .

EXPOSE 8888
ENV PORT=8888

# Run the app
ENTRYPOINT ["python", "-m", "src.main"]
