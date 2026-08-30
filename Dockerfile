# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NJORD_SERVER_MODE=true \
    NJORD_HOST=0.0.0.0 \
    NJORD_PORT=5001 \
    NJORD_DATA_DIR=/var/lib/njorddeploy \
    NJORD_SSH_KEY_PATH=/var/lib/njorddeploy/id_ed25519_njorddeploy

WORKDIR /app

# Install runtime system packages: openssh client, nmap (discovery), sshpass, curl, ca-certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    nmap \
    sshpass \
    curl \
    ca-certificates \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Create persistent storage directory
RUN mkdir -p /var/lib/njorddeploy && chmod 755 /var/lib/njorddeploy

# Copy pyproject.toml to install application dependencies
COPY pyproject.toml /app/
RUN pip install --no-cache-dir gunicorn waitress .

# Copy application source and assets
COPY src/ /app/src/
COPY config/ /app/config/
COPY component_templates/ /app/component_templates/
COPY ansible/ /app/ansible/
COPY run_service.py /app/
COPY run_configurator.py /app/
COPY run_editor.py /app/

# Expose default service port
EXPOSE 5001

# Persistent storage volume for SSH keys, config caches, and artifacts
VOLUME ["/var/lib/njorddeploy"]

# Healthcheck definition
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5001/api/health || exit 1

# Graceful termination signal
STOPSIGNAL SIGTERM

ENTRYPOINT ["python", "run_service.py"]
