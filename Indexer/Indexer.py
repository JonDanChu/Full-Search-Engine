from lxml import html
from urllib.parse import parse_qsl, urlparse, urljoin, urldefrag
import json
import os
import shutil
from threading import Lock

from pathlib import Path

from lxml import etree
from lxml.html import fromstring

from nltk.stem import PorterStemmer
from dotenv import load_dotenv

import re
import hashlib

import Posting

import sys
# add punkt if we want to stem the entire sentences

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent

load_dotenv(REPO_ROOT / ".env")

stemmer = PorterStemmer()

BATCH_CNT = 1000
PARTIAL_INDEX_PATH = Path("./PARTIAL")
_doc_path = os.environ.get("DOC_PATH")
if not _doc_path:
    raise EnvironmentError("DOC_PATH environment variable is not set. Example: export DOC_PATH=./DEV")

PARTIAL_INDEX_PATH = REPO_ROOT / "PARTIAL"
DOC_PATH = Path(_doc_path)
if not DOC_PATH.is_absolute():
    DOC_PATH = REPO_ROOT / DOC_PATH
TEST_CORPUS = REPO_ROOT / "practice"
DOC_IDS = BASE_DIR / "doc_ids.json"

###############################################################
#   Postings:
#      Key:
#       - token
#
#      Value:
#       - {
#           "df": number of documents containing the token,
#           "postings": [docID1, docID2, ...]
#         }
###############################################################

###############################################################
#   Near-duplicate detection (EC) — Lecture 11, slides 20-38
#
#   Fingerprint / Shingling algorithm:
#     1. Slide a window of _NGRAM_SIZE over the token list to
#        produce overlapping n-grams.
#     2. Hash each n-gram; keep those where hash % _MOD_SELECTOR == 0
#        (matches lecture example: H mod 4 = 0).
#     3. The resulting set of hash values is the document fingerprint.
#     4. Similarity S(A,B) = |F_A ∩ F_B| / |F_A ∪ F_B|  (Jaccard)
#     5. S(A,B) >= _SIMILARITY_THRESHOLD  =>  near-duplicate
#
#   Candidate lookup uses an inverted index over hash values so only
#   fingerprints that share at least one hash are fully compared.
###############################################################

_NGRAM_SIZE           = 3     # trigrams (lecture example uses 3-grams)
_MOD_SELECTOR         = 4     # keep hashes where h % 4 == 0
_SIMILARITY_THRESHOLD = 0.9   # Jaccard >= 0.9 => near-duplicate

def _compute_fingerprint(tokens: list) -> frozenset:
    fp = set()
    for i in range(len(tokens) - _NGRAM_SIZE + 1):
        ngram = " ".join(tokens[i:i + _NGRAM_SIZE])
        h = int(hashlib.md5(ngram.encode()).hexdigest(), 16)
        if h % _MOD_SELECTOR == 0:
            fp.add(h)
    return frozenset(fp)

class _NearDupIndex:
    def __init__(self):
        self._hash_to_fp_ids = {}   # hash value -> list of fingerprint indices
        self._stored_fps     = []   # list of stored frozensets

    def is_near_duplicate(self, fp: frozenset) -> bool:
        if not fp:
            return False
        # collect candidate indices via inverted lookup
        candidate_ids = set()
        for h in fp:
            for fp_id in self._hash_to_fp_ids.get(h, []):
                candidate_ids.add(fp_id)
        # full Jaccard check only for candidates that share at least one hash
        for fp_id in candidate_ids:
            stored = self._stored_fps[fp_id]
            intersection = len(fp & stored)
            union = len(fp | stored)
            if union > 0 and intersection / union >= _SIMILARITY_THRESHOLD:
                return True
        return False

    def add(self, fp: frozenset) -> None:
        fp_id = len(self._stored_fps)
        self._stored_fps.append(fp)
        for h in fp:
            self._hash_to_fp_ids.setdefault(h, []).append(fp_id)


def iter_all_files(rt_folder: Path):
    for subfolder in sorted(rt_folder.iterdir()):
        if not subfolder.is_dir():
            continue
        
        for json_file in sorted(subfolder.glob("*.json")):
            yield json_file

def scrape(html: str):
    try:
        tree = fromstring(html.encode("utf-8"))
    except etree.ParserError:
        print("failed to parse")
        return None
    
    return tree
    
def normalize(txt: list):
    # going to be a set for now since we aren't checking for the index of the
    # token itself
    # to check for the index:
    # - change set to a dictionary
    # - and save the token as the key and the value be a list of the
    #       indexes the token is found at

    tokens = []

    for tkn in txt:
        clean = re.sub(r"[^a-zA-Z0-9]", "", tkn)
        if len(clean) < 2:
            continue

        # stemmer will lowercase everything!
        stem = stemmer.stem(clean)

        tokens.append(stem)

    return tokens

def get_important_words(html: str) -> dict[str, int]:
    # Dictionary of the important sections that we want to watch out for
    # the numbers will be used as a overall multiplier for that word in 
    # the document
    IMPORTANT_TAGS = {
        "title" : 4,
        "h1" : 3.75, "h2" : 3.5, "h3" : 3.25, "h4" : 3,
        "b" : 2, "strong" : 2
    }

    imp_words = dict()

    tree = scrape(html)
    
    if tree is None:
        return None, None
    
    for tag, value in IMPORTANT_TAGS.items():
        for node in tree.iter(tag):
            words = node.text_content().split()
            tokens = normalize(words)
            
            for tkn in tokens:
                imp_words[tkn] = imp_words.get(tkn, 0) + value

    return tree, imp_words

def save_batch(batch_index, token_postings, output_dir: Path):
    save_location = output_dir / f"batch_{batch_index:03d}.json"
    save_location.parent.mkdir(parents = True, exist_ok = True)
    
    with open(save_location, "w") as file:

        for token, posting in sorted(token_postings.items()):
            # if change tokens to a number (hashed) then need to change the 
            # call to sorted, add a param (lambda function)
            
            sorted_token = {
                token : posting.export()
            }

            file.write(json.dumps(sorted_token) + "\n")

        print(f"Saved to {save_location}")

def save_docIDS(doc_id_dict):
    with open(DOC_IDS, "w") as file:
        file.write(json.dumps(doc_id_dict))
    
    print(f"Saved all docIDs")
    
def index_all(root_folder: Path):
    # clear the partial index directory if it exists
    if PARTIAL_INDEX_PATH.exists():
        for path in PARTIAL_INDEX_PATH.iterdir():
            shutil.rmtree(path) if path.is_dir() else path.unlink()

    if DOC_IDS.exists():
        DOC_IDS.unlink()
    
    doc_count = 0
    token_postings = dict()
    all_tokens = set()

    doc_id_dict = dict() #used to store [docId, url] to be saved in a file
	
    dup_index = _NearDupIndex()

    for json_file in iter_all_files(root_folder):
        try:
            with open(json_file, "r") as file:
                doc = json.load(file)
        except (json.JSONDecodeError, json.UnicodeDecodeError, OSError) as e:
            # print(f"Skipping {json_file}: {e}")
            continue

        html = doc.get("content", "")

        if html is None:
            continue
        
        tree, imp_words = get_important_words(html)

        if tree is None:
            continue

        try:
            txt = tree.text_content().split()

            tokens = normalize(txt)
        except Exception as e:
            print(f"Error scraping and/or tokenizing {json_file}: {e}")
            continue

        # near-duplicate detection (EC): skip pages whose SimHash fingerprint
        # is within _NEAR_DUP_THRESHOLD bits of an already-indexed page
        fp = _compute_fingerprint(tokens)
        if dup_index.is_near_duplicate(fp):
            # print(f"Skipping near-duplicate: {doc.get('url', '')}")
            continue
        dup_index.add(fp)

        doc_count += 1
        doc_id_dict[doc_count] = doc.get("url", "")

        all_tokens.update(tokens)
        
        index = 0
        for tkn in tokens: 
            if tkn in token_postings:
                token_postings[tkn].add_position(doc_count, index)
            else:
                importance = imp_words[tkn] if tkn in imp_words else 1
                token_postings[tkn] = Posting.Posting(freq = 1, newDoc = doc_count, pos = index, imp = importance)

            index += 1
        
        if (doc_count % BATCH_CNT) == 0:
            num_batch = doc_count // BATCH_CNT # floor division to guarentee int
            save_batch(num_batch, token_postings, PARTIAL_INDEX_PATH)

            token_postings = dict()
    
    if (doc_count % BATCH_CNT) != 0:
        num_batch = (doc_count // BATCH_CNT) + 1 # floor division to guarentee int
        save_batch(num_batch, token_postings, PARTIAL_INDEX_PATH)
    
    save_docIDS(doc_id_dict)

    return doc_count, len(all_tokens)


if __name__ == "__main__":
    if PARTIAL_INDEX_PATH.exists():
        shutil.rmtree(PARTIAL_INDEX_PATH)

    if "-t" in sys.argv:  
        num_doc, num_tkn = index_all(TEST_CORPUS)
        print(f"Number of documents indexed: {num_doc}\nNumber of unique tokens: {num_tkn}")

    else:
        num_doc, num_tkn = index_all(DOC_PATH)
        print(f"Number of documents indexed: {num_doc}\nNumber of unique tokens: {num_tkn}")
