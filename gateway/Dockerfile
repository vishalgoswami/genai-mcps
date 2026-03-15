FROM python:3.12-slim

WORKDIR /app

# Install shared library first (credentials + OAuth middleware)
COPY shared/ /app/shared/
RUN pip install --no-cache-dir -e /app/shared

# Install gateway
COPY gateway/pyproject.toml /app/pyproject.toml
COPY gateway/src/ /app/src/
COPY gateway/config/ /app/config/

# Also copy credentials file
COPY infra/credentials.yaml /app/infra/credentials.yaml

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["gateway"]
