"""Synthetic markup tests; no network or copied scripture."""
import unittest
from tools.build_zhouyi import extract, BITS, PAGE_ALIASES


def fixture():
    def entries(values):
        return "<ul>" + "".join("<li>" + x + "</li>" for x in values) + "</ul>"
    labels = ["初九", "九二", "九三", "六四", "六五", "上六"]
    classic = entries(["泰：J"] + [x + "：L" for x in labels])
    image = entries(["I"] + ["i"] * 6)
    return entries(["易經：" + classic, "彖曰：" + entries(["T"]), "象曰：" + image])


class CorpusBuilderTests(unittest.TestCase):
    def test_structure(self):
        r = extract(fixture(), 11, "泰")
        self.assertEqual(r["judgment"], "J")
        self.assertEqual(r["lines"][4]["label"], "六五")
        self.assertEqual(len(r["line_images"]), 6)

    def test_source_variants(self):
        cases = [(10, "履", "履虎尾，J", "履虎尾，J"),
                 (12, "否", "否之匪人，J", "否之匪人，J"),
                 (13, "同人", "同人于野，J", "同人于野，J"),
                 (25, "無妄", "无妄：J", "J"),
                 (29, "坎", "習坎：J", "J"),
                 (32, "恆", "恆：J", "J")]
        for number, name, judgment, expected in cases:
            with self.subTest(number=number):
                html = fixture().replace("泰：J", judgment)
                old = ["初九", "九二", "九三", "六四", "六五", "上六"]
                import re
                labels = []
                for i, bit in enumerate(BITS[number]):
                    p = "九" if bit == "1" else "六"
                    labels.append("初"+p if i == 0 else "上"+p if i == 5 else p+"二三四五"[i-1])
                mapping = dict(zip(old, labels))
                html = re.sub("|".join(old), lambda m: mapping[m.group()], html)
                if number == 12:
                    html = re.sub(r"([初上][九六]|[九六][二三四五])：", r"\1，", html)
                self.assertEqual(extract(html, number, name)["judgment"], expected)
        self.assertEqual(PAGE_ALIASES, {"無妄": "无妄", "恆": "恒"})

    def test_bad_polarity(self):
        with self.assertRaises(ValueError):
            extract(fixture().replace("九三", "六三"), 11, "泰")

    def test_missing_section(self):
        with self.assertRaises(ValueError):
            extract(fixture().replace("彖曰", "unknown"), 11, "泰")


if __name__ == "__main__":
    unittest.main()
