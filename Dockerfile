FROM registry.access.redhat.com/ubi9/python-312

# Set environment variables
ENV POETRY_VERSION=1.8.2 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install dependencies (including Poetry)
RUN python -m pip install --upgrade pip && \
    pip install "poetry==$POETRY_VERSION"

# Set working directory
WORKDIR /app

# Copy pyproject and poetry.lock first for better caching
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry install --no-interaction --no-ansi

# Copy the rest of the application
COPY . .

EXPOSE 8888
ENV PORT=8888

# Run the app
ENTRYPOINT ["python", "-m", "src.main"]
