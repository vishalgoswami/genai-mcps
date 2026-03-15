FROM python:3.12-slim

WORKDIR /app

# Install shared library first
COPY shared/ /app/shared/
RUN pip install --no-cache-dir -e /app/shared

# Install weather server
COPY servers/weather/pyproject.toml /app/pyproject.toml
COPY servers/weather/src/ /app/src/
RUN pip install --no-cache-dir -e .

EXPOSE 9002

CMD ["weather-server"]
