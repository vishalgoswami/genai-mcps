# registry/frontend

React + TypeScript web app for browsing and registering MCP servers.

## Features

- **Registry grid** — MCP server cards with name, description, tools count, tags, and status badge
- **Live status** — auto-refreshes every 30 seconds
- **Register form** — register any remote MCP server by URL

## Running

```bash
npm install
cp .env.example .env.local   # set VITE_API_URL=http://localhost:8080
npm run dev
# open http://localhost:3000
```

## Key files

| File | Description |
|---|---|
| `src/App.tsx` | Registry home page — fetches and renders server cards |
| `src/pages/RegisterPage.tsx` | Register new MCP server form page |
| `src/components/MCPCard.tsx` | Individual server card component |
| `src/components/StatusBadge.tsx` | Online / offline / unknown badge |
| `src/components/RegisterForm.tsx` | Registration form with validation |
| `src/api/servers.ts` | Axios API client |
| `src/types.ts` | TypeScript types |
