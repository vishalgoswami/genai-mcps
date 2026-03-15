FROM python:3.12-slim

WORKDIR /app

# No shared library needed — calculator has no auth
COPY servers/calculator/pyproject.toml /app/pyproject.toml
COPY servers/calculator/src/ /app/src/
RUN pip install --no-cache-dir .

ENV MCP_TRANSPORT=streamable-http
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=9004

EXPOSE 9004

CMD ["calculator-server"]
