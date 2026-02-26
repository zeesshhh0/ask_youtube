FROM python:3.13-slim

# Copy uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Optimization: Copy dependency files first to leverage Docker cache
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
# --frozen ensures we use the exact versions in uv.lock
# --no-dev skips installing development dependencies
RUN uv sync --frozen --no-dev --no-install-project

# Copy the rest of the application
COPY . /app

# Install the project itself
RUN uv sync --frozen --no-dev

# Ensure uvicorn runs on the port required by Google Cloud Run (default: 8080)
# Cloud Run automatically sets the PORT environment variable
CMD ["sh", "-c", "uv run uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
