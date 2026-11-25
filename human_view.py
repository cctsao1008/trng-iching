"""Read-only rendering of the v0.4.0 casting record."""
import json
from datetime import datetime
from pathlib import Path

from iching import cast_from_hex

DATA = Path(__file__).resolve().parent / "data"


def _classical_rows(h):
    corpus = json.loads((DATA / "zhouyi.json").read_text(encoding="utf-8"))
    sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    if corpus["schema_version"] != "0.1.0":
        raise ValueError("Unsupported classical text schema")
    records = corpus["hexagrams"]
    pages = sources["pages"]
    if len(records) != 64 or len(pages) != 64:
        raise ValueError("Incomplete classical text corpus")
    def lookup(number):
        record, source = records[number-1], pages[number-1]
        if record["number"] != number or source["number"] != number or record["name"] != source["name"]:
            raise ValueError("Classical text identity mismatch")
        return record, source

    primary, primary_source = lookup(h["primary"]["number"])
    relating, relating_source = lookup(h["relating"]["number"])
    rows = ["", "Classical Text / 周易",
            f"本卦 {primary['number']:02d} {primary['name']}：{primary['judgment']}"]
    for position in h["moving_lines"]:
        line = primary["lines"][position-1]
        if line["position"] != position:
            raise ValueError("Classical line position mismatch")
        rows.append(f"{line['label']}：{line['text']}")
    if len(h["moving_lines"]) == 6 and primary["special_line"] is not None:
        special = primary["special_line"]
        rows.append(f"{special['label']}：{special['text']}")
    if relating["number"] != primary["number"]:
        rows.append(f"之卦 {relating['number']:02d} {relating['name']}：{relating['judgment']}")
    rows.append("Source: Chinese Wikisource / 周易")
    rows.append(f"  {primary['name']}: {primary_source['url']}")
    if relating["number"] != primary["number"]:
        rows.append(f"  {relating['name']}: {relating_source['url']}")
    return rows


def _calendar_rows(record: dict) -> list[str]:
    """Present the civil and lunar dates without changing the cast record."""
    rows = []
    stamp = record.get("timestamp")
    instant = datetime.fromisoformat(stamp.replace("Z", "+00:00")) if stamp else None
    if instant is not None:
        weekday = "一二三四五六日"[instant.weekday()]
        rows.append(f"Gregorian    : {instant.year}年{instant.month}月{instant.day}日（星期{weekday}）")
    lunar = (record.get("calendar") or {}).get("lunar")
    if lunar:
        # Lunar year follows the lunar new year, not the solar Li Chun boundary.
        year_index = lunar["year"] - 1984
        year = "甲乙丙丁戊己庚辛壬癸"[year_index % 10] + "子丑寅卯辰巳午未申酉戌亥"[year_index % 12]
        month = ("正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二")[lunar["month"] - 1]
        day = (
            "初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
            "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
            "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十",
        )[lunar["day"] - 1]
        leap = "閏" if lunar["is_leap_month"] else ""
        rows.append(f"Lunar        : {year}年{leap}{month}月{day}")
    if instant is not None:
        offset = instant.strftime("%z")
        zone = f"UTC{offset[:3]}:{offset[3:]}" if offset else "timezone not provided"
        rows.append(f"Time         : {instant:%H:%M:%S} ({zone})")
    else:
        rows.append("Time         : not provided")
    if record.get("solar_term"):
        rows.append(f"Solar term   : {record['solar_term']}")
    pillars = record.get("ganzhi")
    if pillars:
        rows.append("Four pillars : " + " ".join(
            (pillars[key] + suffix) if pillars.get(key) else "-"
            for key, suffix in (("year", "年"), ("month", "月"), ("day", "日"), ("hour", "時"))
        ))
    return rows


def render_human(record: dict, *, classical: bool = False) -> str:
    if not isinstance(record, dict) or record.get("schema_version") != "0.4.0":
        raise ValueError("Human View requires a v0.4.0 cast record")
    h = record["hexagram"]
    lines = h["lines_bottom_to_top"]
    expected = cast_from_hex(record["randomness"]["raw_hex"])
    if (lines != expected["lines_bottom_to_top"]
            or h["moving_lines"] != expected["moving_lines"]
            or any(h[k] != {"number": expected[k]["number"],
                            "name": expected[k]["display_name"]}
                   for k in ("primary", "relating"))):
        raise ValueError("Inconsistent cast record")
    def stroke(yang):
        return "---------" if yang else "---- ----"

    rows = [
        "Hexagram Casting",
        f"Source: {record['randomness']['source']} / {record['randomness']['raw_hex']}",
        f"Mode: {record['mode']} | Status: {record['status']}",
        "",
        f"Primary {h['primary']['number']:02d}: {h['primary']['name']}",
        f"Relating {h['relating']['number']:02d}: {h['relating']['name']}",
        "",
        "   PRIMARY            RELATING",
    ]
    for i in range(5, -1, -1):
        n = lines[i]
        mark = "*" if n in (6, 9) else " "
        rows.append(f"{i+1}  {stroke(n in (7,9))}  {mark}       {stroke(n in (6,7))}")
    rows.append("")
    moving = h["moving_lines"]
    if not moving:
        rows.append("Moving lines: none")
    else:
        for i in moving:
            change = "Old Yin -> Yang" if lines[i-1] == 6 else "Old Yang -> Yin"
            rows.append(f"* Line {i}: {change}")
    rows.append("")
    rows.extend(_calendar_rows(record))
    if classical:
        rows.extend(_classical_rows(h))
    return "\n".join(rows) + "\n"
