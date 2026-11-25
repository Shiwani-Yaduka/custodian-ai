# ONE Dockerfile for all five backend services.
# The build argument SERVICE says which service folder goes into the image:
#   docker build --build-arg SERVICE=risk-engine -t custodian-risk-engine .
# (GitHub Actions does this for you, so you never need Docker on your laptop.)

FROM python:3.11-slim

ARG SERVICE

# PYTHONPATH lets every service import the shared "core" and "shared" folders.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

# Upgrade OS base packages and Python build tooling to eliminate known base-image CVEs (zlib1g, libzstd1, setuptools, wheel)
RUN apt-get update && \
    apt-get upgrade -y --no-install-recommends && \
    apt-get install --no-install-recommends -y zlib1g libzstd1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --upgrade pip setuptools wheel && \
    rm -rf /usr/local/lib/python3.11/ensurepip && \
    find /usr/local/lib/python3.11 -name "*.cdx.json" -delete

# Install libraries first: Docker reuses this layer when only your code changes (faster builds).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    find /usr/local/lib/python3.11 -name "*.cdx.json" -delete

COPY core ./core
COPY shared ./shared
COPY scripts ./scripts
COPY services/${SERVICE} ./service

# Security basics: do not run as root.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin appuser
USER 10001

WORKDIR /app/service
EXPOSE 8000

# Each service folder must contain main.py with a FastAPI object called "app".
# Kubernetes sets PORT per service (8001 to 8005).
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
