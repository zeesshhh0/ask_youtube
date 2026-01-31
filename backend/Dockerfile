# syntax=docker/dockerfile:1

# ---- Builder Stage ----
# This stage installs Python dependencies into a virtual environment.
ARG PYTHON_VERSION=3.13.3
FROM python:${PYTHON_VERSION}-slim AS builder

# Prevent writing .pyc files and disable output buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a virtual environment to isolate dependencies
ENV VENV_PATH=/opt/venv
RUN python -m venv $VENV_PATH
ENV PATH="$VENV_PATH/bin:$PATH"

# Install dependencies from requirements.txt
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ---- Final Stage ----
# This stage creates the final, lean production image.
FROM python:${PYTHON_VERSION}-slim AS final

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VENV_PATH=/opt/venv
ENV PATH="$VENV_PATH/bin:$PATH"

# Create a dedicated, non-privileged user
WORKDIR /app
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --shell "/sbin/nologin" \
    --uid "${UID}" \
    appuser

# Copy the virtual environment from the builder stage
COPY --from=builder ${VENV_PATH} ${VENV_PATH}

# Copy application code and set ownership in one step
# Use a .dockerignore file to exclude unnecessary files/folders
COPY --chown=appuser:appuser . .

# Switch to the non-privileged user
USER appuser

# Expose the port and define the runtime command
EXPOSE 8080
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]