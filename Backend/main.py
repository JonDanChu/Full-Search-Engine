from contextlib import asynccontextmanager
from time import perf_counter
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

# To reuse the functions defined in Search.py
from Search.Search import (
    DOC_ID_PATH,
    PAGERANK_PATH,
    build_doc_id_table,
    load_pagerank_scores,
    normalize_pagerank_scores,
    run_query,
    tokenize_query,
)

# These will be used to store data that is moved around the website
class SearchResult(BaseModel):
    url: str
    score: float


class SearchResponse(BaseModel):
    query: str
    total: int
    elapsed_ms: float
    results: list[SearchResult]

# Defines resources that are loaded during start up
# As supposed to during each search
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.doc_id_table = build_doc_id_table(DOC_ID_PATH)
    raw_pagerank = load_pagerank_scores(PAGERANK_PATH)
    app.state.pagerank_scores = normalize_pagerank_scores(raw_pagerank)
    yield # to show that it is the end of set up


app = FastAPI(
    title="Full Search Engine API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/search", response_model=SearchResponse)
def search(
    q: Annotated[str, Query(min_length=1, max_length=200)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> SearchResponse:
    query_tokens = tokenize_query(q)

    if not query_tokens:
        raise HTTPException(
            status_code=400,
            detail="The query does not contain any valid search terms.",
        )

    start = perf_counter()
    ranked_documents = run_query(query_tokens, app.state.pagerank_scores)
    elapse = (perf_counter() - start) * 1000

    results = [
        SearchResult(
            url=app.state.doc_id_table[doc_id],
            score=score,
        )
        for doc_id, score in ranked_documents[:limit]
        if doc_id in app.state.doc_id_table
    ]

    return SearchResponse(
        query=q,
        total=len(ranked_documents),
        elapsed_ms=round(elapse, 2),
        results=results,
    )