"""Audit a staged Zhouyi corpus offline; never acquire randomness or network data."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from iching import _NAMES, _KING_WEN_MATRIX, _TRIGRAMS
from tools.build_zhouyi import extract, PIN, PAGE_ALIASES

BITS = {n: _TRIGRAMS[l][1] + _TRIGRAMS[u][1]
        for l, row in enumerate(_KING_WEN_MATRIX) for u, n in enumerate(row)}
EXPECTED = {
    "judgments": 64, "lines": 384, "special_lines": 2, "tuan": 64,
    "images": 64, "line_images": 384, "special_images": 2, "wenyan": 2,
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def read_json(path):
    def unique(pairs):
        result = {}
        for k, v in pairs:
            require(k not in result, f"duplicate JSON key: {k}")
            result[k] = v
        return result
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def check_record(record, number, name):
    require(record["number"] == number and record["name"] == name, "hexagram identity")
    for field in ("judgment", "tuan", "image"):
        require(nonempty(record[field]), f"empty {field}")
    require(isinstance(record["lines"], list) and len(record["lines"]) == 6, "six lines required")
    require(isinstance(record["line_images"], list) and len(record["line_images"]) == 6
            and all(map(nonempty, record["line_images"])), "six line images required")
    for position, (line, bit) in enumerate(zip(record["lines"], BITS[number]), 1):
        p = "九" if bit == "1" else "六"
        label = "初"+p if position == 1 else "上"+p if position == 6 else p+"二三四五"[position-2]
        require(line["position"] == position and line["label"] == label
                and nonempty(line["text"]), f"invalid line {position}")
    if number in (1, 2):
        special = record["special_line"]
        require(isinstance(special, dict) and special["label"] == ("用九" if number == 1 else "用六")
                and nonempty(special["text"]) and nonempty(special["image"]), "invalid special line")
        require(nonempty(record["wenyan"]), "missing Wenyan")
    else:
        require(record["special_line"] is None and record["wenyan"] is None, "unexpected special material")


def audit(stage):
    corpus_path, manifest_path = stage / "zhouyi.json", stage / "sources.json"
    corpus, manifest = read_json(corpus_path), read_json(manifest_path)
    require(corpus["schema_version"] == "0.1.0", "unsupported corpus schema")
    require(nonempty(manifest["source"]) and nonempty(manifest["license"])
            and nonempty(manifest["normalization"]), "missing provenance")
    require(manifest["license_url"] == "https://creativecommons.org/licenses/by-sa/4.0/", "unexpected license URL")
    records, pages = corpus["hexagrams"], manifest["pages"]
    require(len(records) == len(pages) == 64, "64 records and pages required")
    require({p.name for p in (stage / "raw").glob("*.html")} ==
            {f"{n:02d}.html" for n in range(1, 65)}, "raw snapshot inventory mismatch")
    counts = dict.fromkeys(EXPECTED, 0)
    failures, revisions = [], set()
    for n, name in enumerate(_NAMES, 1):
        try:
            record, page = records[n-1], pages[n-1]
            check_record(record, n, name)
            require(page["number"] == n and page["name"] == name, "manifest identity/order")
            revision = page["revision"]
            require(type(revision) is int and revision > 0 and revision not in revisions, "invalid/duplicate revision")
            revisions.add(revision)
            url = PIN + urlencode({"title": "周易/" + PAGE_ALIASES.get(name, name), "oldid": revision})
            require(page["url"] == url, "pinned source URL mismatch")
            raw = (stage / "raw" / f"{n:02d}.html").read_bytes()
            require(digest(raw) == page["html_sha256"], "raw SHA-256 mismatch")
            require(extract(raw.decode("utf-8"), n, name) == record, "snapshot/corpus projection mismatch")
            for key in ("judgments", "tuan", "images"):
                counts[key] += 1
            counts["lines"] += len(record["lines"])
            counts["line_images"] += len(record["line_images"])
            if record["special_line"]:
                counts["special_lines"] += 1
                counts["special_images"] += 1
            if record["wenyan"]:
                counts["wenyan"] += 1
        except Exception as exc:
            failures.append({"number": n, "name": name, "error": str(exc)})
    passed = not failures and counts == EXPECTED
    return {
        "status": "PASS" if passed else "FAIL",
        "scope": "offline structural and captured-source projection audit",
        "cross_edition_collation": "NOT_PERFORMED",
        "projection_check": "reuses acquisition parser; not independent textual transcription",
        "counts": counts,
        "expected_counts": EXPECTED,
        "text_units": sum(counts.values()),
        "passed_pages": 64 - len(failures),
        "failed": failures,
        "sha256": {"zhouyi.json": digest(corpus_path.read_bytes()),
                   "sources.json": digest(manifest_path.read_bytes())},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        parser.error("report must be a new file")
    try:
        result = audit(args.stage)
    except Exception as exc:
        result = {"status": "FAIL", "error": str(exc), "cross_edition_collation": "NOT_PERFORMED"}
    with args.report.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
