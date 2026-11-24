"""Explicit offline-build acquisition tool; never used by the cast CLI.

Fetch pinned MediaWiki parsed HTML, extract nested list sections, and fail
closed on unfamiliar markup. No generated or substituted scripture.
"""
import argparse
import hashlib
import json
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from iching import _NAMES, _KING_WEN_MATRIX, _TRIGRAMS

API = "https://zh.wikisource.org/w/api.php"
PIN = "https://zh.wikisource.org/w/index.php?"
PAGE_ALIASES = {"無妄": "无妄", "恆": "恒"}
INLINE_JUDGMENTS = {10: "履虎尾", 12: "否之", 13: "同人于"}
JUDGMENT_ALIASES = {25: ("無妄", "无妄"), 29: ("習坎", "坎"), 32: ("恆", "恒")}
SECTIONS = {"易經：": "classic", "彖曰：": "tuan", "象曰：": "image",
            "文言曰：": "wenyan"}
BITS = {number: _TRIGRAMS[lower][1] + _TRIGRAMS[upper][1]
        for lower, row in enumerate(_KING_WEN_MATRIX)
        for upper, number in enumerate(row)}


class Lists(HTMLParser):
    """Capture each list item with direct text and child list items."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.roots = []
        self.stack = []

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            node = {"text": [], "children": []}
            (self.stack[-1]["children"] if self.stack else self.roots).append(node)
            self.stack.append(node)
        elif tag == "br" and self.stack:
            self.stack[-1]["text"].append("\n")

    def handle_endtag(self, tag):
        if tag == "li" and self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if self.stack:
            self.stack[-1]["text"].append(data)


def direct(node):
    return "".join(node["text"]).strip()


def flatten(node):
    return "\n".join(filter(None, [direct(node), *(flatten(c) for c in node["children"])]))


def walk(nodes):
    for node in nodes:
        yield node
        yield from walk(node["children"])


def extract(html, number, name):
    parser = Lists()
    parser.feed(html)
    sections = {}
    for node in walk(parser.roots):
        key = SECTIONS.get(direct(node).replace(":", "："))
        if key:
            if key in sections:
                raise ValueError(f"duplicate section {key}")
            sections[key] = node["children"]
    for key in ("classic", "tuan", "image"):
        if not sections.get(key):
            raise ValueError(f"missing section {key}")
    # The classic and image sections each have a lead entry and six line
    # entries; Qian/Kun also have one special entry. Flatten only descendants
    # of an entry so multiline judgments and commentary are retained.
    classic = [flatten(x) for x in sections["classic"]]
    images = [flatten(x) for x in sections["image"]]
    count = 8 if number in (1, 2) else 7
    if len(classic) != count or len(images) != count:
        raise ValueError(f"unexpected entry counts: {len(classic)}, {len(images)}")
    judgment = classic[0]
    aliases = JUDGMENT_ALIASES.get(number, (name,))
    heading = re.match(r"(?:" + "|".join(map(re.escape, aliases)) + r")[:：]\s*", judgment)
    if heading:
        judgment_text = judgment[heading.end():]
    elif number in INLINE_JUDGMENTS and judgment.startswith(INLINE_JUDGMENTS[number]):
        judgment_text = judgment
    else:
        raise ValueError(f"judgment name mismatch: {judgment[:40]}")
    if not judgment_text.strip():
        raise ValueError("empty judgment")
    lines = []
    for i, value in enumerate(classic[1:7], 1):
        polarity = "九" if BITS[number][i-1] == "1" else "六"
        label = ("初" + polarity if i == 1 else "上" + polarity if i == 6
                 else polarity + "二三四五"[i-2])
        separator = r"[:：，,]" if number == 12 else r"[:：]"
        m = re.fullmatch(re.escape(label) + separator + r"\s*(.+)", value, re.S)
        if not m:
            raise ValueError(f"line {i} label mismatch: {value[:30]}")
        lines.append({"position": i, "label": label, "text": m.group(1)})
    special = None
    if count == 8:
        label = "用九" if number == 1 else "用六"
        m = re.fullmatch(label + r"[:：]\s*(.+)", classic[7], re.S)
        if not m:
            raise ValueError("special line mismatch")
        special = {"label": label, "text": m.group(1), "image": images[7]}
        if not sections.get("wenyan"):
            raise ValueError("missing Wenyan")
    if number not in (1, 2) and "wenyan" in sections:
        raise ValueError("unexpected Wenyan")
    tuan = "\n".join(flatten(x) for x in sections["tuan"])
    wenyan = "\n".join(flatten(x) for x in sections.get("wenyan", [])) or None
    if not all([tuan, *images, *(x["text"] for x in lines)]):
        raise ValueError("empty text")
    return {"number": number, "name": name, "judgment": judgment_text.strip(),
            "lines": lines, "tuan": tuan, "image": images[0],
            "line_images": images[1:7], "special_line": special, "wenyan": wenyan}


def fetch(name, revision=None):
    params = {"action": "parse", "prop": "text|revid", "format": "json", "formatversion": 2}
    title = "周易/" + PAGE_ALIASES.get(name, name)
    if revision is None:
        params["page"] = title
    else:
        params["oldid"] = revision
    req = Request(API + "?" + urlencode(params),
                  headers={"User-Agent": "trng-iching corpus builder/0.1 (https://github.com/cctsao1008/trng-iching)"})
    with urlopen(req, timeout=30) as response:
        raw = response.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError("oversized response")
    document = json.loads(raw)
    if "parse" not in document:
        error = document.get("error", {})
        raise ValueError(f"MediaWiki API: {error.get('code', 'unknown')}: {error.get('info', 'missing parse response')}")
    page = document["parse"]
    if page["title"] != title or (revision is not None and page["revid"] != revision):
        raise ValueError("source identity mismatch")
    html = page["text"]
    return html, page["revid"]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True, help="New output directory")
    p.add_argument("--pins", type=Path, help="Prior sources.json for pinned revision replay")
    p.add_argument("--resume", type=Path, help="Reuse verified HTML snapshots and revisions from an earlier stage")
    args = p.parse_args()
    cached = {}
    if args.resume:
        cached = {x["number"]: x for x in json.loads((args.resume / "sources.json").read_text(encoding="utf-8"))["pages"]}
    pins = {}
    if args.pins:
        pins = {x["number"]: x["revision"] for x in json.loads(args.pins.read_text(encoding="utf-8"))["pages"]}
        if set(pins) != set(range(1, 65)):
            p.error("pins must cover all 64 pages")
    args.out.mkdir(parents=True, exist_ok=False)
    raw_dir = args.out / "raw"
    raw_dir.mkdir()
    pages, records, failures = [], [], []
    for number, name in enumerate(_NAMES, 1):
        try:
            if number in cached:
                entry = cached[number]
                encoded = (args.resume / "raw" / f"{number:02d}.html").read_bytes()
                if (entry["name"] != name or hashlib.sha256(encoded).hexdigest() != entry["html_sha256"]
                        or (number in pins and pins[number] != entry["revision"])):
                    raise ValueError("cached source identity or checksum mismatch")
                html, revision = encoded.decode("utf-8"), entry["revision"]
            else:
                html, revision = fetch(name, pins.get(number))
                encoded = html.encode("utf-8")
            (raw_dir / f"{number:02d}.html").write_bytes(encoded)
            pages.append({"number": number, "name": name, "revision": revision,
                          "url": PIN + urlencode({"title": "周易/" + PAGE_ALIASES.get(name, name), "oldid": revision}),
                          "html_sha256": hashlib.sha256(encoded).hexdigest()})
            records.append(extract(html, number, name))
            print(f"PASS {number:02d} {name}")
        except Exception as exc:
            failures.append({"number": number, "name": name, "error": str(exc)})
            print(f"FAIL {number:02d} {name}: {exc}", file=sys.stderr)
        time.sleep(0.5)
    def write(name, data):
        (args.out / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write("sources.json", {"source": "Chinese Wikisource received text",
                           "license": "CC BY-SA 4.0 for applicable editorial contributions",
                           "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
                           "normalization": "HTML entity decoding; trim outer whitespace; newline between nested entries; preserve source characters",
                           "pages": pages})
    write("report.json", {"passed": len(records), "failed": failures})
    if failures or len(records) != 64:
        print("Corpus not published: resolve failures first.", file=sys.stderr)
        return 1
    write("zhouyi.json", {"schema_version": "0.1.0", "hexagrams": records})
    print("64/64 structural checks passed; textual collation still required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
