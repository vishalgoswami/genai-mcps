# registry/backend

FastAPI backend for the MCP Registry web app.

## Features

- Register / update / delete remote MCP servers
- MCP card data: name, description, URL, tags, owner, auth type
- Background status checker polls every server and updates `status` + `tools_count`
- SQLite by default (swap for Postgres via `DATABASE_URL`)

## Running

```bash
pip install -e .
cp ../../.env.example .env
registry-server
# API docs: http://localhost:8080/docs
```

## API

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/servers` | List all registered servers |
| POST | `/api/servers` | Register a new MCP server |
| GET | `/api/servers/{id}` | Get server details |
| PATCH | `/api/servers/{id}` | Update server info |
| DELETE | `/api/servers/{id}` | Remove a server |
