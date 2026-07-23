import json
import heapq
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REPO_ROOT = BASE_DIR.parent

PARTIAL_INDEXES = REPO_ROOT / "PARTIAL"
COMPLETE_INDEX = BASE_DIR / "index"
PRACTICE_INDEX = BASE_DIR / "practice-index"

def upload_index(path):

    with open(path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                for word, postings in data.items():
                    yield word, postings
            except json.JSONDecodeError as exc:
                print(f"[warning] Skipping malformed JSON on line {lineno}: {exc}", file=sys.stderr)

def merge_indexes(input_folder: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    partial_indexes = input_folder.glob("*.json")
    streams = [upload_index(f) for f in partial_indexes]

    heap = []
    nexts = []
    for i, stream in enumerate(streams):
        entry = next(stream, None)
        nexts.append(entry)
        if entry:
            heapq.heappush(heap, (entry[0], i))

    current_letter = None
    out = None

    try:
        while heap:
            word, i = heapq.heappop(heap)
            _, postings = nexts[i]

            merged_postings = {
                "df": int(postings["df"]),
                "postings": postings["docDict"],
            }

            while heap and heap[0][0] == word:
                _, j = heapq.heappop(heap)
                _, other_postings = nexts[j]

                # need to work on reconstruction, docId's will be strings not ints!!
                merged_postings["df"] += int(other_postings["df"])

                merged_postings["postings"] = merged_postings["postings"] | other_postings["docDict"]

                entry = next(streams[j], None)
                nexts[j] = entry
                if entry:
                    heapq.heappush(heap, (entry[0], j))

            entry = next(streams[i], None)
            nexts[i] = entry
            if entry:
                heapq.heappush(heap, (entry[0], i))

            # open a new file whenever the first letter of the token changes
            letter = word[0].lower() if word[0].isalpha() else "0"
            if letter != current_letter:
                if out:
                    out.close()
                current_letter = letter
                out = open(output_dir / f"index_{letter}.json", "w")

            out.write("{" + json.dumps(word) + ": " + json.dumps(merged_postings) + "}\n")
    finally:
        if out:
            out.close()

    # if len(sys.argv) < 2:
    #     print("Usage: python3 Combiner.py input1.json input2.json ...")
    #     sys.exit(1)

if __name__ == "__main__":

    if "-t" in sys.argv:  
        print(f"Merging files into {PRACTICE_INDEX}/...")
        merge_indexes(PARTIAL_INDEXES, PRACTICE_INDEX)
        print("Done.")

    else:
        print(f"Merging files into {COMPLETE_INDEX}/...")
        merge_indexes(PARTIAL_INDEXES, COMPLETE_INDEX)
        print("Done.")
