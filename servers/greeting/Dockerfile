FROM python:3.12-slim

WORKDIR /app

# Install shared library (for OIDCIdTokenVerifier)
COPY shared/ /app/shared/
RUN pip install --no-cache-dir /app/shared

# Install greeting server
COPY servers/greeting/pyproject.toml /app/pyproject.toml
COPY servers/greeting/src/ /app/src/
RUN pip install --no-cache-dir .

ENV MCP_TRANSPORT=streamable-http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=9005

EXPOSE 9005

CMD ["greeting-server"]
