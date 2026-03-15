FROM python:3.12-slim

WORKDIR /app

COPY registry/backend/ .

RUN pip install --no-cache-dir .

ENV REGISTRY_HOST=0.0.0.0
ENV REGISTRY_PORT=8080

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

CMD ["registry-server"]
