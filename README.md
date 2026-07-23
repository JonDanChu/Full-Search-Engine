# CS-121-Search-Engine

For milestones 1-3. Capable search engine!

## Setup

Create and activate a virtual environment, then install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

To deactivate the virtual environment when you're done:

```bash
deactivate
```

## Configuration

Create a `.env` file in the repo root with the following variables:

```properties
DOC_PATH=./DEV
```

| Variable   | Description                        |
| ---------- | ---------------------------------- |
| `DOC_PATH` | Path to the document corpus folder |

## Run the Indexer

Create the partial inverted index:

```bash
python3 Indexer/Indexer.py
```

## Merge Partial Indexes

Merge the batch files from the repo root:

```bash
python3 Combiner/Combiner.py
```

## Compute PageRank

Build the precomputed PageRank scores from the repo root:

```bash
python3 Search/PageRank.py
```

## Run Search

Start the search interface:

```bash
python3 Search/Search.py
```

`Search/pagerank.json` is optional at runtime. If it exists, search uses it as a small authority boost during ranking.

## Run the API

Start the API server from the repo root:

```bash
python3 -m uvicorn Api.Api:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`. Interactive docs are at `http://localhost:8000/docs`.

### Endpoint

```
GET /search
```

| Parameter | Type    | Default  | Description                               |
| --------- | ------- | -------- | ----------------------------------------- |
| `q`       | string  | required | Search query (terms are ANDed by default) |
| `limit`   | integer | 5        | Number of results to return (1–50)        |

### Example

```bash
curl "http://localhost:8000/search?q=machine+learning&limit=5"
```

```json
{
  "query": "machine learning",
  "normalized_tokens": ["machin", "learn"],
  "total_results": 42,
  "returned_results": 5,
  "results": ["https://example.com/page1", "https://example.com/page2"],
  "query_time_ms": 3.271,
  "proximity_used": true
}
```

## Run the Web Frontend

The web frontend is a Vite + React app that talks to the API. Make sure the API (see "Run the API" above) is running before you start the frontend.

> **Note:** These instructions assume you are running behind a JupyterHub proxy. Throughout this section, replace `<HUB_HOST>` with your hub's hostname (e.g. `staging-hub.ics.uci.edu`) and `<USERNAME>` with your hub username (e.g. `noahmk1`).

### 1. Move into the frontend directory

```bash
cd Web/search-engine
```

### 2. Install dependencies

```bash
npm install
```

### 3. Configure `vite.config.ts` for the proxy

Because the dev server is served through the JupyterHub proxy rather than directly, Vite needs to be told which host is allowed to connect and where to route its Hot Module Reload (HMR) websocket. Without this, the browser will either reject the host or fail to establish the live-reload connection.

Open `vite.config.ts` and make sure it matches the following, updating `allowedHosts` and `hmr.path` for your own hub host and username:

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  base: './',
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    allowedHosts: ['<HUB_HOST>'],
    hmr: {
      clientPort: 443,
      protocol: 'wss',
      path: '/user/<USERNAME>/vscode/proxy/5173/',
    },
  },
});
```

What these settings do:

- **`base: './'`** — uses relative asset paths so files resolve correctly under the proxy prefix instead of being requested from the server root.
- **`allowedHosts`** — whitelists the hub hostname so Vite doesn't block the proxied request.
- **`hmr.clientPort: 443` / `protocol: 'wss'`** — tells the HMR client to connect over secure websockets on the standard HTTPS port, since the proxy terminates TLS.
- **`hmr.path`** — routes the HMR websocket through the same proxy path the app is served from.

### 4. Build the app

```bash
npm run build
```

### 5. Preview the built app

```bash
npm run preview -- --host 0.0.0.0
```

### 6. Open it in your browser

The preview server runs on port `4173`. Navigate to the following URL, including the trailing slash:

```
https://<HUB_HOST>/user/<USERNAME>/vscode/proxy/4173/
```
