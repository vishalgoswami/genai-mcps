FROM python:3.12-slim

WORKDIR /app

# Install shared library first
COPY shared/ /app/shared/
RUN pip install --no-cache-dir /app/shared

# Install stock server
COPY servers/stock/pyproject.toml /app/pyproject.toml
COPY servers/stock/src/ /app/src/
RUN pip install --no-cache-dir .

# Default to streamable-http on 0.0.0.0:9003 in Docker
ENV MCP_TRANSPORT=streamable-http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=9003

EXPOSE 9003

CMD ["stock-server"]
