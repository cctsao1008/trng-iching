"""Offline Human View regression tests."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main
from human_view import render_human
from iching import cast_from_hex


def record(raw="a44916"):
    cast = cast_from_hex(raw)
    return {
        "schema_version": "0.4.0", "mode": "manual_reference_cast",
        "status": "cast_only", "timestamp": None,
        "randomness": {"source": "user_provided_reference", "raw_hex": raw},
        "hexagram": {
            "lines_bottom_to_top": cast["lines_bottom_to_top"],
            "moving_lines": cast["moving_lines"],
            **{k: {"number": cast[k]["number"], "name": cast[k]["display_name"]}
               for k in ("primary", "relating")},
        },
        "calendar": None, "solar_term": None, "ganzhi": None,
    }


class HumanViewTests(unittest.TestCase):
    def test_reference(self):
        out = render_human(record())
        self.assertIn("Primary 06: 天水訟", out)
        self.assertIn("Relating 44: 天風姤", out)
        self.assertIn("3  ---- ----  *       ---------", out)
        self.assertIn("* Line 3: Old Yin -> Yang", out)
        self.assertLess(out.index("6  ---------"), out.index("1  ---- ----"))

    def test_none_and_multiple(self):
        self.assertIn("Moving lines: none", render_human(record("249240")))
        out = render_human(record("000000"))
        self.assertEqual(out.count("* Line "), 6)
        self.assertIn("Old Yin -> Yang", out)
        self.assertIn("Old Yang -> Yin", render_human(record("ffffff")))

    def test_inconsistent(self):
        r = record()
        r["hexagram"]["moving_lines"] = []
        with self.assertRaises(ValueError):
            render_human(r)

    def test_save_and_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "cast.json"
            out = io.StringIO()
            with patch.object(main, "acquire_trng_bytes") as acquire:
                with contextlib.redirect_stdout(out):
                    self.assertEqual(main.main(["cast", "--hex", "a44916", "--audit",
                        "--view", "human", "--json-out", str(p)]), 0)
                saved = json.loads(p.read_text(encoding="utf-8"))
                self.assertIn("audit", saved)
                replay = io.StringIO()
                with contextlib.redirect_stdout(replay):
                    self.assertEqual(main.main(["view", "--input", str(p)]), 0)
                self.assertEqual(out.getvalue(), replay.getvalue())
                acquire.assert_not_called()

    def test_live_single_call_and_same_json(self):
        r = record()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "cast.json"
            with patch.object(main, "_live_cast", return_value={}) as live:
                with patch.object(main, "_present_cast_result", return_value=r):
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(main.main(["cast", "--view", "human",
                            "--json-out", str(p)]), 0)
                live.assert_called_once()
            self.assertEqual(json.loads(p.read_text()), r)


if __name__ == "__main__":
    unittest.main()
