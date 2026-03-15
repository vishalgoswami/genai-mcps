# Stock Price MCP Server

Real-time stock quotes, historical prices, and company information via [Yahoo Finance](https://finance.yahoo.com/).

## Tools

| Tool               | Description                                         |
| ------------------- | --------------------------------------------------- |
| `get_stock_price`   | Current price, change, day range, market cap         |
| `get_stock_history` | Recent daily closing prices (up to 365 days)         |
| `get_company_info`  | Company name, sector, industry, summary              |

## Run locally

```bash
cd servers/stock
pip install -e .
stock-server
```

Server starts at `http://localhost:9003/mcp`.

## Docker

```bash
# From repo root
docker compose up stock-server
```

## Environment

| Variable           | Default | Description                          |
| ------------------- | ------- | ------------------------------------ |
| `MCP_AUTH_ENABLED`  | `false` | Enable OAuth token validation        |
| `KEYCLOAK_URL`      | —       | Keycloak base URL (when auth enabled)|
| `KEYCLOAK_REALM`    | `mcp`   | Keycloak realm name                  |
