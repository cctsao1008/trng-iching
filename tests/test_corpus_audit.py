"""Offline checks for the independent corpus gate."""
import tempfile
import unittest
from pathlib import Path
from tools.validate_zhouyi import check_record, read_json, EXPECTED
from tools.build_zhouyi import extract
from test_corpus_builder import fixture


class CorpusAuditTests(unittest.TestCase):
    def test_record(self):
        record = extract(fixture(), 11, "泰")
        check_record(record, 11, "泰")
        record["lines"][2]["label"] = "六三"
        with self.assertRaises(ValueError):
            check_record(record, 11, "泰")

    def test_empty_image(self):
        record = extract(fixture(), 11, "泰")
        record["line_images"][0] = " "
        with self.assertRaises(ValueError):
            check_record(record, 11, "泰")

    def test_duplicate_json(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "test.json"
            p.write_text('{"a":1,"a":2}', encoding="utf-8")
            with self.assertRaises(ValueError):
                read_json(p)

    def test_expected_total(self):
        self.assertEqual(sum(EXPECTED.values()), 1026)
