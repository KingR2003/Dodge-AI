# SAP O2C Graph UI

Minimal React UI that:
- Renders the graph using `react-force-graph-2d`
- Click-to-expand (one-hop subgraph) and shows node metadata
- Provides a chat interface that calls the backend `POST /chat`

## Run (local)

1. Start the FastAPI backend on `http://localhost:8000`.
2. Start the UI:

```powershell
cd "d:\Dodge AI\frontend"
npm run dev
```

The dev server proxies `/graph` and `/chat` to the backend, so CORS is not required in development.

## Configure backend

The UI relies on these endpoints:
- `GET /graph`
- `POST /chat`

