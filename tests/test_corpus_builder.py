"""Synthetic markup tests; no network or copied scripture."""
import unittest
from tools.build_zhouyi import extract


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

    def test_bad_polarity(self):
        with self.assertRaises(ValueError):
            extract(fixture().replace("九三", "六三"), 11, "泰")

    def test_missing_section(self):
        with self.assertRaises(ValueError):
            extract(fixture().replace("彖曰", "unknown"), 11, "泰")


if __name__ == "__main__":
    unittest.main()
