"""Deterministic 18-bit I Ching three-coin cast and King Wen mappings.

All line arrays run bottom-to-top. No randomness, clocks, I/O, or interpretation
is performed inside this module.
"""

from __future__ import annotations

import re

# Trigrams in the conventional upper/lower 8x8 King Wen lookup order.
# Each triple is encoded bottom-to-top, yin=0, yang=1.
_TRIGRAMS = (
    ("乾", "111"), ("兌", "110"), ("離", "101"), ("震", "100"),
    ("巽", "011"), ("坎", "010"), ("艮", "001"), ("坤", "000"),
)

# Rows: lower trigram; columns: upper trigram; both use _TRIGRAMS order.
# Correspondence: https://en.wikipedia.org/wiki/Hexagram_(I_Ching)
_KING_WEN_MATRIX = (
    (1, 43, 14, 34, 9, 5, 26, 11),
    (10, 58, 38, 54, 61, 60, 41, 19),
    (13, 49, 30, 55, 37, 63, 22, 36),
    (25, 17, 21, 51, 42, 3, 27, 24),
    (44, 28, 50, 32, 57, 48, 18, 46),
    (6, 47, 64, 40, 59, 29, 4, 7),
    (33, 31, 56, 62, 53, 39, 52, 15),
    (12, 45, 35, 16, 20, 8, 23, 2),
)

# Traditional Chinese names in King Wen sequence (1..64).
_NAMES = (
    "乾", "坤", "屯", "蒙", "需", "訟", "師", "比",
    "小畜", "履", "泰", "否", "同人", "大有", "謙", "豫",
    "隨", "蠱", "臨", "觀", "噬嗑", "賁", "剝", "復",
    "無妄", "大畜", "頤", "大過", "坎", "離", "咸", "恆",
    "遯", "大壯", "晉", "明夷", "家人", "睽", "蹇", "解",
    "損", "益", "夬", "姤", "萃", "升", "困", "井",
    "革", "鼎", "震", "艮", "漸", "歸妹", "豐", "旅",
    "巽", "兌", "渙", "節", "中孚", "小過", "既濟", "未濟",
)
_HEX = re.compile(r"[0-9a-fA-F]{6}\Z")

if sorted(number for row in _KING_WEN_MATRIX for number in row) != list(range(1, 65)):
    raise RuntimeError("King Wen matrix must contain each number 1..64 exactly once")
if len(_NAMES) != 64:
    raise RuntimeError("King Wen name table must have 64 entries")

_TRIGRAM_INDEX = {bits: i for i, (_, bits) in enumerate(_TRIGRAMS)}


def _hexagram(bits_bottom_to_top: str) -> dict:
    if len(bits_bottom_to_top) != 6 or any(c not in "01" for c in bits_bottom_to_top):
        raise ValueError("A hexagram requires exactly six yin/yang bits")
    lower = _TRIGRAM_INDEX[bits_bottom_to_top[:3]]
    upper = _TRIGRAM_INDEX[bits_bottom_to_top[3:]]
    number = _KING_WEN_MATRIX[lower][upper]
    lower_name, upper_name = _TRIGRAMS[lower][0], _TRIGRAMS[upper][0]
    trigram_images = ("天", "澤", "火", "雷", "風", "水", "山", "地")
    display = (
        f"{upper_name}為{trigram_images[upper]}"
        if lower == upper
        else f"{trigram_images[upper]}{trigram_images[lower]}{_NAMES[number - 1]}"
    )
    return {
        "number": number,
        "name": _NAMES[number - 1],
        "display_name": display,
        "unicode": chr(0x4DC0 + number - 1),
        "bits_bottom_to_top": bits_bottom_to_top,
        "lower_trigram": lower_name,
        "upper_trigram": upper_name,
    }


def cast_from_hex(raw_hex: str) -> dict:
    """Map three bytes to six traditional three-coin lines (first = bottom)."""
    if not isinstance(raw_hex, str) or _HEX.fullmatch(raw_hex) is None:
        raise ValueError("Cast requires exactly 6 hexadecimal digits (3 bytes)")
    bits = f"{int(raw_hex, 16):024b}"
    groups = [bits[i:i + 3] for i in range(0, 18, 3)]
    lines = [6 + group.count("1") for group in groups]
    moving = [index for index, value in enumerate(lines, 1) if value in (6, 9)]
    original_bits = "".join("1" if line in (7, 9) else "0" for line in lines)
    changed_bits = "".join(
        "1" if line in (6, 7) else "0" for line in lines
    )
    return {
        "method": "three_coins_18bit_msb_first",
        "raw_hex": raw_hex.lower(),
        "bits_used": bits[:18],
        "bits_discarded": bits[18:],
        "triples_bottom_to_top": groups,
        "lines_bottom_to_top": lines,
        "moving_lines": moving,
        "primary": _hexagram(original_bits),
        "relating": _hexagram(changed_bits),
        "text_selection_status": "targets_selected_text_not_bundled",
        "text_selection": select_text_targets(
            primary=_hexagram(original_bits),
            relating=_hexagram(changed_bits),
            moving_lines=moving,
        ),
    }



def select_text_targets(
    *, primary: dict, relating: dict, moving_lines: list[int]
) -> dict:
    """Select references, not text, under Zhu Xi's 考變占 seven cases.

    Rule reference: 易學啟蒙 考變占第四, as transmitted in
    易學啟蒙通釋 (四庫全書本)/卷下. No copyrighted translation or
    classical text corpus is bundled; 3-moving-line case returns both
    judgments without imposing an unverified primary/secondary priority.
    """
    changed = sorted(set(moving_lines))
    if len(changed) != len(moving_lines) or any(
        not isinstance(number, int) or not 1 <= number <= 6
        for number in changed
    ):
        raise ValueError("Moving-line positions must be unique integers 1..6")
    still = [number for number in range(1, 7) if number not in changed]
    count = len(changed)

    def ref(hexagram: dict, text_type: str, *, line: int | None = None,
            priority: str = "selected") -> dict:
        target = {
            "hexagram_number": hexagram["number"],
            "hexagram_name": hexagram["display_name"],
            "text_type": text_type,
            "role": priority,
        }
        if line is not None:
            target["line_number"] = line
        return target

    if count == 0:
        targets = [ref(primary, "hexagram_judgment")]
    elif count == 1:
        targets = [ref(primary, "line_statement", line=changed[0])]
    elif count == 2:
        targets = [
            ref(primary, "line_statement", line=number,
                priority="primary" if number == changed[-1] else "secondary")
            for number in changed
        ]
    elif count == 3:
        targets = [
            ref(primary, "hexagram_judgment", priority="zhen_original"),
            ref(relating, "hexagram_judgment", priority="hui_relating"),
        ]
    elif count == 4:
        targets = [
            ref(relating, "line_statement", line=number,
                priority="primary" if number == still[0] else "secondary")
            for number in still
        ]
    elif count == 5:
        targets = [ref(relating, "line_statement", line=still[0])]
    elif primary["number"] == 1:
        targets = [ref(primary, "use_nine")]
    elif primary["number"] == 2:
        targets = [ref(primary, "use_six")]
    else:
        targets = [ref(relating, "hexagram_judgment")]
    return {
        "ruleset": "zhu_xi_yixue_qimeng_kaobian_zhan_v1",
        "number_of_moving_lines": count,
        "source_title": "易學啟蒙・考變占第四",
        "source_reference": (
            "https://zh.wikisource.org/zh-hant/"
            "%E6%98%93%E5%AD%B8%E5%95%9F%E8%92%99%E9%80%9A%E9%87%8B_"
            "%28%E5%9B%9B%E5%BA%AB%E5%85%A8%E6%9B%B8%E6%9C%AC%29/%E5%8D%B7%E4%B8%8B"
        ),
        "targets": targets,
        "status": "references_only_classical_text_not_bundled",
    }
