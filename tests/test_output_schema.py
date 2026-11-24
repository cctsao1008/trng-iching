"""Offline schema checks: never call TRNG.info or the JPL/HKO services."""

import contextlib
import copy
import io
import json
import unittest
from unittest.mock import patch

import main
from iching import cast_from_hex


def _reference_result(*, audit=False):
    return {
        "schema_version": "0.3.0",
        "mode": "live_trng_cast",
        "status": "complete",
        "capture": {
            "cast_time_utc": "2026-11-24T11:26:29.939927Z",
            "cast_time_utc_plus_8": "2026-11-24T19:26:29.939927+08:00",
            "cast_time_source": "trng_client_receive_time",
        },
        "randomness": {
            "source": "trng.info",
            "raw_hex": "a44916",
            "source_endpoint": "https://api.trng.info/random/bytes?length=3",
            "request_time_utc": "2026-11-24T11:26:28Z",
            "receive_time_utc": "2026-11-24T11:26:29Z",
        },
        "cast": cast_from_hex("a44916", audit=audit),
        "context": {
            "calendar": {
                "status": "official_reference_lookup",
                "lunar": {
                    "year": 2026, "month": 10, "day": 16,
                    "is_leap_month": False, "month_start_date": "2026-11-09",
                },
                "provenance": {"provider": "Hong Kong Observatory"},
            },
            "astronomy": {
                "status": "calculated",
                "current_solar_term": {"name_zh_tw": "小雪"},
                "sun_apparent_ecliptic_longitude_degrees": 242.190844629,
            },
            "ganzhi": {
                "status": "calculated",
                "year": "丙午", "month": "己亥",
                "day": "壬寅", "hour": "庚戌",
            },
        },
    }


def _run_cast_with_mock(args, result):
    output = io.StringIO()
    with patch.object(main, "_live_cast", return_value=result) as live:
        with contextlib.redirect_stdout(output):
            code = main.main(args)
    return code, json.loads(output.getvalue()), live.call_count


class CastPresentationTests(unittest.TestCase):
    def test_compact_live_cast(self):
        original = _reference_result()
        before = copy.deepcopy(original)
        compact = main._present_cast_result(original, audit=False)
        self.assertEqual(original, before)
        self.assertEqual(compact["schema_version"], "0.4.0")
        self.assertEqual(compact["mode"], "live_trng_cast")
        self.assertEqual(compact["timestamp"], "2026-11-24T19:26:29.939927+08:00")
        self.assertEqual(compact["randomness"], {"source": "trng.info", "raw_hex": "a44916"})
        self.assertEqual(compact["hexagram"]["lines_bottom_to_top"], [8, 7, 6, 7, 7, 7])
        self.assertEqual(compact["hexagram"]["moving_lines"], [3])
        self.assertEqual(compact["hexagram"]["primary"], {"number": 6, "name": "天水訟"})
        self.assertEqual(compact["hexagram"]["relating"], {"number": 44, "name": "天風姤"})
        self.assertEqual(compact["calendar"]["lunar"]["day"], 16)
        self.assertEqual(compact["solar_term"], "小雪")
        self.assertEqual(compact["ganzhi"]["hour"], "庚戌")
        self.assertNotIn("audit", compact)
        self.assertNotIn("source_endpoint", compact["randomness"])

    def test_audit_preserves_full_details(self):
        result = _reference_result(audit=True)
        code, payload, calls = _run_cast_with_mock(["cast", "--audit"], result)
        self.assertEqual((code, calls), (0, 1))
        self.assertEqual(payload["schema_version"], "0.4.0")
        self.assertEqual(payload["audit"]["randomness"]["source_endpoint"],
                         "https://api.trng.info/random/bytes?length=3")
        self.assertEqual(payload["audit"]["cast"]["bits_used"], "101001000100100100")
        self.assertEqual(payload["audit"]["context"]["astronomy"]
                         ["sun_apparent_ecliptic_longitude_degrees"], 242.190844629)

    def test_default_cli_uses_compact_projection_once(self):
        code, payload, calls = _run_cast_with_mock(["cast"], _reference_result())
        self.assertEqual((code, calls), (0, 1))
        self.assertNotIn("audit", payload)
        self.assertEqual(payload["hexagram"]["primary"]["number"], 6)

    def test_partial_retains_diagnostics_and_valid_day_hour(self):
        result = _reference_result()
        result["status"] = "partial"
        result["context"]["astronomy"] = {"status": "unavailable"}
        result["context"]["ganzhi"].update(
            {"status": "partial", "year": None, "month": None}
        )
        result["errors"] = [{"component": "astronomy", "error": "missing kernel"}]
        payload = main._present_cast_result(result, audit=False)
        self.assertIsNone(payload["solar_term"])
        self.assertIsNone(payload["ganzhi"]["year"])
        self.assertEqual(payload["ganzhi"]["day"], "壬寅")
        self.assertEqual(payload["status"], "partial")
        self.assertEqual(payload["errors"], result["errors"])

    def test_manual_cast_without_timestamp_is_never_live(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main.main(["cast", "--hex", "a44916"])
        payload = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(payload["mode"], "manual_reference_cast")
        self.assertEqual(payload["status"], "cast_only")
        self.assertIsNone(payload["timestamp"])
        self.assertIsNone(payload["calendar"])
        self.assertIsNone(payload["solar_term"])
        self.assertIsNone(payload["ganzhi"])


if __name__ == "__main__":
    unittest.main()
