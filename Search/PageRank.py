import json
import math
import os
import sys
from pathlib import Path
from urllib.parse import urljoin, urldefrag

from dotenv import load_dotenv
from lxml import etree
from lxml.html import fromstring

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent

load_dotenv(REPO_ROOT / ".env")

_doc_path = os.environ.get("DOC_PATH")
if not _doc_path:
    raise EnvironmentError("DOC_PATH environment variable is not set. Example: export DOC_PATH=./DEV")

DEV_PATH = Path(_doc_path)
if not DEV_PATH.is_absolute():
    DEV_PATH = REPO_ROOT / DEV_PATH

DOC_IDS_PATH = REPO_ROOT / "Indexer" / "doc_ids.json"
PAGERANK_OUTPUT = BASE_DIR / "pagerank.json"

# PageRank hyper-parameters
DAMPING = 0.85   # standard damping factor
ITERATIONS = 50     # power-iteration steps (converges well before this)
CONVERGENCE_THRESHOLD = 1e-6  # stop early if max change drops below this

def normalize_url(url: str) -> str:
    """Strip fragment and trailing slash so URLs compare consistently."""
    url, _ = urldefrag(url)
    return url.rstrip("/")


def extract_links(html_content: str, base_url: str) -> list[str]:
    """
    Parse HTML and return absolute, fragment-free URLs for every <a href>.
    Only keeps http/https links so we don't chase mailto:, javascript:, etc.
    """
    try:
        tree = fromstring(html_content.encode("utf-8"))
    except (etree.ParserError, ValueError):
        return []

    links = []
    for anchor in tree.findall(".//a"):
        href = anchor.get("href")
        if not href:
            continue
        try:
            resolved  = urljoin(base_url, href)
            normalized = normalize_url(resolved)
            if normalized.startswith("http"):
                links.append(normalized)
        except Exception:
            continue
    return links


def iter_all_files(root_folder: Path):
    """Yield every *.json file under root_folder (sorted, depth-1 subfolders)."""
    for subfolder in sorted(root_folder.iterdir()):
        if not subfolder.is_dir():
            continue
        for json_file in sorted(subfolder.glob("*.json")):
            yield json_file


# Link-graph construction
def build_link_graph(
    dev_path: Path,
    doc_ids_path: Path,
) -> tuple[dict[int, list[tuple[int, int]]], int]:
    """
    Returns
    -------
    in_links : dict  { target_doc_id -> [(src_doc_id, out_degree), ...] }
        For every target page, the list of (source page, source out-degree) pairs
        needed by the PageRank update step.
    N : int
        Total number of documents.
    """
    # Build url -> doc_id lookup from the pre-built mapping file
    with open(doc_ids_path, "r") as fh:
        raw = json.load(fh)

    url_to_id: dict[str, int] = {}
    for doc_id_str, url in raw.items():
        url_to_id[normalize_url(url)] = int(doc_id_str)

    all_doc_ids: set[int] = set(url_to_id.values())
    N = len(all_doc_ids)

    # out_links[src_id] = set of distinct target doc_ids that src links to
    out_links: dict[int, set[int]] = {doc_id: set() for doc_id in all_doc_ids}

    processed = 0
    for json_file in iter_all_files(dev_path):
        try:
            with open(json_file, "r") as fh:
                doc = json.load(fh)
        except (json.JSONDecodeError, OSError):
            continue

        url = normalize_url(doc.get("url", ""))
        html_content = doc.get("content", "")

        src_id = url_to_id.get(url)
        if src_id is None or not html_content:
            continue

        for link in extract_links(html_content, url):
            tgt_id = url_to_id.get(link)
            if tgt_id is not None and tgt_id != src_id:
                out_links[src_id].add(tgt_id)

        processed += 1
        if processed % 5000 == 0:
            print(f"  Processed {processed} documents...")

    print(f"  Finished processing {processed} documents.")

    # Invert the graph: in_links[target] = [(src, out_degree_of_src), ...]
    in_links: dict[int, list[tuple[int, int]]] = {doc_id: [] for doc_id in all_doc_ids}
    for src_id, targets in out_links.items():
        out_degree = len(targets)
        if out_degree == 0:
            continue
        for tgt_id in targets:
            in_links[tgt_id].append((src_id, out_degree))

    return in_links, N


# Power-iteration PageRank
def compute_pagerank(
    in_links: dict[int, list[tuple[int, int]]],
    damping: float = DAMPING,
    iterations: int = ITERATIONS,
    threshold: float = CONVERGENCE_THRESHOLD,
) -> dict[int, float]:
    """
    PageRank power iteration per the original Google formula (Brin & Page 1997).

    PR(A) = (1 - d) + d * Σ_{Ti -> A}  PR(Ti) / C(Ti)

    where d = damping factor (0.85), C(Ti) = out-degree of Ti.
    Initialise PR = 1 for all pages; converges when average PR = 1.
    """
    doc_ids = list(in_links.keys())

    # Start with PR = 1 for every page (lecture slide: "Guess PR(p) = 1")
    pagerank: dict[int, float] = {doc_id: 1.0 for doc_id in doc_ids}

    teleport = 1.0 - damping  # (1 - d), not divided by N

    for iteration in range(1, iterations + 1):
        new_pr: dict[int, float] = {}
        max_delta = 0.0

        for doc_id in doc_ids:
            rank_sum = sum(
                pagerank[src_id] / out_degree
                for src_id, out_degree in in_links[doc_id]
            )
            new_score = teleport + damping * rank_sum
            new_pr[doc_id] = new_score
            max_delta = max(max_delta, abs(new_score - pagerank[doc_id]))

        pagerank = new_pr

        if max_delta < threshold:
            print(f"  Converged after {iteration} iterations (max_delta={max_delta:.2e})")
            break
    else:
        print(f"  Completed {iterations} iterations (max_delta={max_delta:.2e})")

    return pagerank


if __name__ == "__main__":
    if not DOC_IDS_PATH.exists():
        print(f"Missing doc ID mapping: {DOC_IDS_PATH}")
        print("Run `python3 Indexer/Indexer.py` before computing PageRank.")
        sys.exit(1)

    print("Building link graph from DEV/ corpus...")
    in_links, N = build_link_graph(DEV_PATH, DOC_IDS_PATH)
    print(f"  Total documents: {N}")

    print("Running PageRank power iteration...")
    pagerank = compute_pagerank(in_links)

    # Sanity check: average PR should be ~1.0 (sum ≈ N)
    total = sum(pagerank.values())
    print(f"  Sum of all PR scores: {total:.6f}  (expected ≈ {N}, average ≈ 1.0)")

    top5 = sorted(pagerank.items(), key=lambda x: -x[1])[:5]
    print(f"  Top-5 doc IDs by PR: {top5}")

    # Save as {str(doc_id): score} — JSON keys must be strings
    output = {str(doc_id): score for doc_id, score in pagerank.items()}
    with open(PAGERANK_OUTPUT, "w") as fh:
        json.dump(output, fh)

    print(f"Saved PageRank scores → {PAGERANK_OUTPUT}")
