FROM ubuntu:24.04
# Ubuntu, not python:slim — ships Python 3.12 by default.
# Build with: docker build --platform linux/amd64 (EKS nodes are x86).

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# --break-system-packages: required on Ubuntu 24.04 (PEP 668).
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY . .

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

CMD ["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
