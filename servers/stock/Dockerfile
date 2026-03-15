FROM python:3.12-slim

WORKDIR /app

# Install shared library first
COPY shared/ /app/shared/
RUN pip install --no-cache-dir -e /app/shared

# Install stock server
COPY servers/stock/pyproject.toml /app/pyproject.toml
COPY servers/stock/src/ /app/src/
RUN pip install --no-cache-dir -e .

EXPOSE 9003

CMD ["stock-server"]
