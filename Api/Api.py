import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import time
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from Search.Search import (
    tokenize_query,
    run_query,
    build_doc_id_table,
    load_pagerank_scores,
    normalize_pagerank_scores,
    DOC_ID_PATH,
    PAGERANK_PATH,
)

class SearchResponse(BaseModel):
    query: str
    normalized_tokens: list[str]
    total_results: int
    returned_results: int
    results: list[str]
    query_time_ms: float
    proximity_used: bool


app = FastAPI(
    title="Search Engine API",
    description="Web Search API built for CS121 Spring 2026.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_doc_id_table: dict[int, str] = {}
_pagerank_scores: dict[int, float] = {}


@app.on_event("startup")
def startup_event() -> None:
    global _doc_id_table, _pagerank_scores
    _doc_id_table = build_doc_id_table(DOC_ID_PATH)
    _pagerank_scores = normalize_pagerank_scores(load_pagerank_scores(PAGERANK_PATH))


@app.get("/search", response_model=SearchResponse, summary="Run a search query")
def search(
    q: str = Query(..., description="Search query. Use AND to explicitly join terms (it is dropped during normalization). All terms are ANDed by default."),
    limit: int = Query(5, ge=1, le=50, description="Maximum number of result URLs to return."),
) -> SearchResponse:
    query_tokens = tokenize_query(q)

    if not query_tokens:
        raise HTTPException(
            status_code=422,
            detail="Invalid query: no usable search terms after normalization.",
        )

    start = time.perf_counter()
    result_docs = run_query(query_tokens, _pagerank_scores)
    elapsed_ms = (time.perf_counter() - start) * 1000

    result_urls = [
        _doc_id_table[doc_id]
        for doc_id, _score in result_docs[:limit]
        if doc_id in _doc_id_table
    ]

    return SearchResponse(
        query=q,
        normalized_tokens=query_tokens,
        total_results=len(result_docs),
        returned_results=len(result_urls),
        results=result_urls,
        query_time_ms=round(elapsed_ms, 3),
        proximity_used=len(query_tokens) != 1,
    )