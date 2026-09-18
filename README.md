# Full Search Engine

A local full-text search engine for a crawled document corpus. The project builds an inverted index from HTML documents, ranks pages, exposes search through a FastAPI service, and provides a React web interface.

## Features

- Boolean AND retrieval across normalized and stemmed query terms
- Ranking with TF-IDF cosine similarity, term proximity, phrase/bigram matches, HTML element importance, and PageRank
- Near-duplicate filtering while indexing
- FastAPI JSON API with interactive documentation
- React and TypeScript web interface powered by Vite

## Tech stack

- Python 3.10+
- FastAPI and Uvicorn
- NLTK, NumPy, and lxml
- React, TypeScript, and Vite

## Project structure

```text
Backend/     FastAPI application
Combiner/    Partial-index merger and merged index files
Indexer/     Corpus indexer and document-ID mapping
Search/      Query processing and ranking modules
frontend/    React web application
```

## Start the web app

The web app has two processes: the API server and the frontend development server. Run them in separate terminals from the repository root.

### 1. Prerequisites

Install:

- Python 3.10 or newer
- Node.js 20.19+ or 22.12+
- npm

The checked-in index under `Combiner/index/` and document mapping at `Indexer/doc_ids.json` let you search without rebuilding the corpus first.

### 2. Configure and install the backend

Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

Create a `.env` file in the repository root:

```properties
DOC_PATH=./DEV
```

`DOC_PATH` points to the corpus directory. The backend expects this setting even when it uses the existing index. If your corpus is elsewhere, replace `./DEV` with that path.

### 3. Start the API

In the first terminal, from the repository root:

```bash
python3 -m uvicorn Backend.main:app --reload
```

The API is available at [http://127.0.0.1:8000](http://127.0.0.1:8000). You can confirm it is running at [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health), and browse the interactive API documentation at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 4. Start the frontend

In a second terminal:

```bash
cd frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser. During development, Vite forwards requests beginning with `/api` to the backend on port `8000`.

## API usage

Search with `GET /api/search`:

```bash
curl "http://127.0.0.1:8000/api/search?q=machine%20learning&limit=10"
```

Parameters:

| Parameter | Required | Default | Description |
| --- | --- | --- | --- |
| `q` | Yes | — | Search query, from 1 to 200 characters |
| `limit` | No | `10` | Number of results to return, from 1 to 50 |

Example response:

```json
{
  "query": "machine learning",
  "total": 42,
  "elapsed_ms": 3.27,
  "results": [
    {
      "url": "https://example.com/page",
      "score": 1.2345
    }
  ]
}
```

## Rebuild the search data

You only need these steps when the document corpus changes. Make sure `DOC_PATH` in `.env` points to a corpus whose immediate subdirectories contain the crawled JSON documents.

From the repository root, build partial indexes and the document-ID mapping:

```bash
python3 Indexer/Indexer.py
```

Merge the partial indexes into the files used by search:

```bash
python3 Combiner/Combiner.py
```

Compute PageRank scores:

```bash
python3 Search/PageRank.py
```

## Command-line search

To query the index without the web app:

```bash
python3 Search/Search.py
```

Enter a query at the prompt. Search terms are matched using AND semantics. Enter `quit`, `exit`, or a blank line to stop.

## Frontend commands

Run these inside `frontend/`:

```bash
npm run dev      # start the development server
npm run build    # type-check and create a production build
npm run preview  # preview the production build locally
npm run lint     # run ESLint
```
