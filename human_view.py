"""Read-only rendering of the v0.4.0 casting record."""
from iching import cast_from_hex


def render_human(record: dict) -> str:
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
        f"Time: {record['timestamp'] or 'not provided'}",
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
    if record.get("solar_term"):
        rows.append(f"Solar term: {record['solar_term']}")
    lunar = (record.get("calendar") or {}).get("lunar")
    if lunar:
        leap = " (leap month)" if lunar["is_leap_month"] else ""
        rows.append(f"Lunar: {lunar['year']}-{lunar['month']:02d}-{lunar['day']:02d}{leap}")
    pillars = record.get("ganzhi")
    if pillars:
        rows.append("Four pillars: " + " ".join(pillars.get(k) or "-" for k in ("year", "month", "day", "hour")))
    return "\n".join(rows) + "\n"
