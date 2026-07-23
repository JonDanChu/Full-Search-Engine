import json
import re
import sys
import os
from pathlib import Path
import time
import math
from nltk.stem import PorterStemmer
from dotenv import load_dotenv

try:
    from . import Proximity, Cossim, Bigram, Importance
except ImportError:
    import Proximity, Cossim, Bigram, Importance

INVERTED_INDEX = Path("./inverted-index.json")
DOC_PATH = Path("./DEV")
DOC_ID_PATH = Path("./Indexer/doc_ids.json")

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent

load_dotenv(REPO_ROOT / ".env")

INVERTED_INDEX = REPO_ROOT / "Combiner" / "index"
_doc_path = os.environ.get("DOC_PATH")
if not _doc_path:
    raise EnvironmentError("DOC_PATH environment variable is not set. Example: export DOC_PATH=./DEV")

PAGERANK_PATH = BASE_DIR / "pagerank.json"
DOC_PATH = Path(_doc_path)
if not DOC_PATH.is_absolute():
    DOC_PATH = REPO_ROOT / DOC_PATH
DOC_ID_PATH = REPO_ROOT / "Indexer" / "doc_ids.json"
PROXIMITY_WEIGHT = 0.35
BIGRAM_WEIGHT = 0.10
IMPORTANCE_WEIGHT = 0.20
PAGERANK_WEIGHT = 0.10

stemmer = PorterStemmer()

# Query flow:
# 1. tokenize the query
# 2. load postings for the query terms
# 3. intersect candidate docs
# 4. rank the results by proximity and tf-idf (TODO)


def get_query():
    # read a raw query string from the command line
    query = input("Query: ")
    return query

def normalize_token(token: str) -> str | None:
    # match the same normalization pipeline used during indexing so query terms and indexed terms are comparable
    clean = re.sub(r"\W+", "", token)
    if len(clean) < 2:
        return None

    return stemmer.stem(clean)

def tokenize_query(query: str) -> list[str]:
    # split the query into terms, drop literal AND operators, and normalize the remaining tokens for dictionary lookup in the inverted index
    tokens = query.split()
    normalized_tokens = []

    for token in tokens:
        if token.upper() == "AND":
            continue

        stem = normalize_token(token)
        if stem:
            normalized_tokens.append(stem)

    return normalized_tokens

def intersect_doc_ids(postings_lists: list[dict]) -> list[int]:
    # intersect doc-ID sets so ranking only scores documents that contain every query term
    if not postings_lists:
        return []

    doc_sets = [
        {int(doc_id) for doc_id in postings["postings"]}
        for postings in postings_lists
    ]

    return sorted(set.intersection(*doc_sets))

def build_doc_id_table(doc_id_path: Path) -> dict[int, str]:
    try:
        with open(doc_id_path, "r") as file:
            doc = json.load(file)
    except (json.JSONDecodeError, json.UnicodeDecodeError, OSError):
        print("Error building docID table")

    return {int(id): url for id, url in doc.items()}

def load_pagerank_scores(path: Path) -> dict[int, float]:
    if not path.exists():
        return {}

    try:
        with open(path, "r") as file:
            doc = json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}

    try:
        return {
            int(doc_id): float(score)
            for doc_id, score in doc.items()
        }
    except (TypeError, ValueError):
        return {}

def normalize_pagerank_scores(raw_scores: dict[int, float]) -> dict[int, float]:
    if not raw_scores:
        return {}

    max_score = max(raw_scores.values())
    if max_score <= 0:
        return {}

    return {
        doc_id: score / max_score
        for doc_id, score in raw_scores.items()
    }

def get_result_urls(doc_ids: list[tuple[int, float]], doc_id_table: dict[int, str]) -> list[str]:
    # Params: doc_ids - includes score in the second index of the tuple
    # map ranked document IDs back to URLs for display
    return [doc_id_table[doc_id] for doc_id, _ in doc_ids[:5] if doc_id in doc_id_table]

def load_query_postings(index_dir: Path, query_tokens: list[str]) -> dict[str, dict]:
    # group tokens by first letter so each per-letter file is opened at most once
    by_letter = {}
    for token in query_tokens:
        letter = token[0].lower() if token[0].isalpha() else "0"
        by_letter.setdefault(letter, set()).add(token)

    postings_by_token = {}

    for letter, tokens in by_letter.items():
        index_file = index_dir / f"index_{letter}.json"
        if not index_file.exists():
            continue

        remaining = set(tokens)
        with open(index_file, "r") as file:
            for line in file:
                if not remaining:
                    break

                entry = json.loads(line)
                token, postings = next(iter(entry.items()))

                # save postings for any query token we encounter, and stop early once every query token has been found.
                if token in remaining:
                    postings_by_token[token] = postings
                    remaining.remove(token)

    return postings_by_token

def get_postings_in_query_order(query_tokens: list[str], postings_by_token: dict[str, dict]) -> list[dict]:
    # preserve the original query-term order so scoring logic sees term positions in the same order the user typed them
    ordered_postings = []
    
    for token in query_tokens:
        if token not in postings_by_token:
            print(f"No results for token: {token}")
            return []

        ordered_postings.append(postings_by_token[token])

    # print(f"From get_postings_in_query_order\n{ordered_postings[:3]}")

    return ordered_postings

def score_document(
    doc_id: int,
    query_vec: list[float] | None,
    pagerank_scores: dict[int, float],
    doc_infos: list[dict | None],
    prox_flag: bool,
) -> tuple[float, int]:
    # Params:
    #   For this document D
    #   doc_infos: All of the query tkns T and their posting info for D
    # ------------------------------------------------------------------
    # Score one candidate document by combining:
    # - cosine similarity over the unigram postings
    # - proximity for multi-term queries
    # - a bigram phrase boost for adjacent query-term matches
    # - formatting importance from indexed title/header/bold text
    # - a small PageRank authority boost
    
    cossim_score = Cossim.get_cossim(query_vec, doc_infos)
    
    proximity_score = 0.0
    best_span = 0

    if prox_flag:
        best_span = Proximity.get_best_span(doc_infos)
        proximity_score = PROXIMITY_WEIGHT * (1.0 / (1 + best_span))
    
    bigram_boost = Bigram.get_bigram_boost(doc_infos, per_match_boost = BIGRAM_WEIGHT)
    pagerank_score = PAGERANK_WEIGHT * pagerank_scores.get(doc_id, 0.0)
      
    importance_score = IMPORTANCE_WEIGHT * math.log1p(Importance.get_imp(doc_infos))
    
    final_score = cossim_score + proximity_score + bigram_boost + importance_score + pagerank_score
    
    return final_score, best_span

def rank_results(
    query_tokens: list[str],
    pagerank_scores: dict[int, float],
    doc_ids: list[int],
    postings_by_token: list[dict],
) -> list[tuple[int, float]]:
    # Params:
    # doc_ids: list of all documents the query tokens can be found in
    #           sorted by number of query terms found in that document
    #
    # score and sort all candidate documents that survived Boolean intersection
    ranked_docs = []

    # print(f"in rank_results: postings_by_token{len(postings_by_token)}\ndoc_ids{doc_ids[:2]}\nq-tokens{query_tokens}")
    
    # Consider filtering out docs, but end up missing important ones
    #   too difficult to filter
    # num_docs = min(len(doc_ids), 20) # only the top 20 docs or what ever in the list should be considered
    # we only need the top 5 any ways
    # print(f"num_docs - {num_docs}")
    
    df_dict = {
        tkn: int(post["df"])
        for tkn, post in zip(query_tokens, postings_by_token)
    }
    query_vec = Cossim.build_query_vector(query_tokens, df_dict)
    prox_f = len(query_tokens) != 1

    for doc_id in doc_ids:
        doc_infos = []
        for postings in postings_by_token:
            # each postings dictionary is keyed by doc ID as a string
            doc_info = postings["postings"].get(str(doc_id))
            
            # Note: if doc_info is None, still add to the list to show word isn't present
            
            doc_infos.append(doc_info)

        
        score, best_span = score_document(
            doc_id,
            query_vec,
            pagerank_scores,
            doc_infos,
            prox_f,
        )
        ranked_docs.append((doc_id, score, best_span))

    # sort by score first, then by smaller span, then by doc ID for a stable tiebreaker
    ranked_docs.sort(key = lambda item: (-item[1], item[2], item[0]))
    return [(doc_id, score) for doc_id, score, _ in ranked_docs]

def run_query(
    query_tokens: list[str],
    pagerank_scores: dict[int, float] | None = None,
) -> list[tuple[int, float]]:
    # run the retrieval pipeline end to end for a normalized query:
    # load postings, intersect candidates, then rank them.
    if pagerank_scores is None:
        pagerank_scores = {}

    postings_by_token = load_query_postings(INVERTED_INDEX, query_tokens)
    postings = get_postings_in_query_order(query_tokens, postings_by_token)

    if not postings:
        return []

    candidate_docs = intersect_doc_ids(postings)
    if not candidate_docs:
        return []

    return rank_results(query_tokens, pagerank_scores, candidate_docs, postings)

def print_results(result_doc_ids: list[tuple[int, float]], doc_id_table) -> None:
    # result_doc_ids - now includes score as the second index of the tuple
    # resolve ranked document IDs back to URLs and print the first page
    result_urls = get_result_urls(result_doc_ids, doc_id_table)

    print(f"Showing top {min(5, len(result_urls))} of {len(result_doc_ids)} documents found")

    for url, res_doc in zip(result_urls, result_doc_ids):
        print(f"{res_doc[1]:.4f} - {url}")


if __name__ == "__main__":
    # Load all the precomputed data/indexes before 
    # reading the query bc timer starts after 
    # query has been entered!!

    doc_id_table = build_doc_id_table(DOC_ID_PATH)
    pagerank_scores = normalize_pagerank_scores(load_pagerank_scores(PAGERANK_PATH))

    while True:
        query = get_query()
        if query.strip().lower() in ("exit", "quit", ""):
            break

        start = time.perf_counter()
        query_tokens = tokenize_query(query)

        if not query_tokens:
            print("Invalid query: no search terms provided")
            continue

        result = run_query(query_tokens, pagerank_scores)
        elapsed = time.perf_counter() - start
        print(f"Query time: {elapsed * 1000:.2f} ms")
        if result:
            print_results(result, doc_id_table)
        else:
            print("No documents matched all query terms.")
