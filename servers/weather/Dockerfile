FROM python:3.12-slim

WORKDIR /app

# Install shared library first
COPY shared/ /app/shared/
RUN pip install --no-cache-dir /app/shared

# Install weather server
COPY servers/weather/pyproject.toml /app/pyproject.toml
COPY servers/weather/src/ /app/src/
RUN pip install --no-cache-dir .

# Default to streamable-http on 0.0.0.0:9002 in Docker
ENV MCP_TRANSPORT=streamable-http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=9002

EXPOSE 9002

CMD ["weather-server"]
