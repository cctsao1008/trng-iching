# TRNG Hexagram Casting

**A transparent, reproducible hexagram casting tool for use with the I Ching.**

This repository implements **hexagram casting**, not the *I Ching* itself. The *I Ching* includes classical texts and interpretive traditions; this tool calculates the six lines, moving lines, primary hexagram, and relating hexagram. It optionally displays fixed classical passages as reference text; it does **not** provide interpretations or predictions.

Each cast starts with one true-random sample from TRNG.info. Python converts the sample into a hexagram and records astronomical and calendrical context for the time of the cast. The output is a traceable JSON record that can be used for I Ching study or interpretation.

**Randomness determines the hexagram; astronomy and calendars describe the time; interpretation is left to the user.** None of these steps silently changes the others.

## How a cast works

```text
        Run a live cast
                 |
                 v
     TRNG.info: one 3-byte sample
                 |
                 v
  Python: six lines → primary hexagram
           + moving lines → relating hexagram
                 |
                 +---------------------------+
                 |                           |
                 |                     Client receive time
                 |                           |
                 |                      JPL astronomy
                 |                    HKO lunar calendar
                 |                    four pillars (干支)
                 |                           |
                 +-------------+-------------+
                               |
                               v
                       Versioned JSON
                               |
                               v
             Optional I Ching reading
                 (human or AI)
```

### 1. A live random sample determines the hexagram

Each live cast requests exactly **3 bytes (24 bits)** from [TRNG.info](https://trng.info/). The **first 18 bits**, MSB first, are split into six 3-bit groups. The groups form the lines **bottom to top**. Each line value is `6 + number of 1 bits in its group`, reproducing the traditional three-coin probabilities.

| Value | Line | Role |
| --- | --- | --- |
| `6` | 老陰 / old yin | Broken, moving |
| `7` | 少陽 / young yang | Solid, still |
| `8` | 少陰 / young yin | Broken, still |
| `9` | 老陽 / old yang | Solid, moving |

The last six bits are discarded. Moving lines (`6` and `9`) produce the relating hexagram (之卦). Hexagram numbers use King Wen order.

**One command = one live sample.** No automatic retry, pseudorandom fallback, resampling, or silent switching to another provider.

### 2. Astronomy and calendars describe the moment

The cast timestamp is the **client's TRNG response receive time**, not the unknown hardware generation time. Python adds independent context:

- **Astronomy:** JPL **DE440s** + Skyfield calculate the Sun and Moon's geocentric apparent ecliptic longitudes at that instant and identify the **current solar term**. The ordinary cast does **not** calculate the exact solar-term transition time.
- **Lunar calendar:** official [Hong Kong Observatory](https://www.hko.gov.hk/en/gts/time/conversion1_text.htm) calendar reference, from pinned local month starts.
- **Four pillars:** year/month based on **Li Chun (315°)** and the twelve solar `Jie`; day changes at **00:00 UTC+08**; hours use civil two-hour periods. No true-solar-time correction. The HKO lunar year and the solar-term-based Ganzhi year can legitimately differ.

These are **descriptive time facts**, not inputs to the random casting algorithm.

### 3. Interpretation is separate

The program ends with a structured casting record. You can use that record in an *I Ching* reading—on your own or with an AI—but Python does not prescribe a reading method, evaluate whether a cast is favorable, or interpret classical passages. The recorded random input, hexagrams, moving lines, timestamp, and computed context should remain unchanged.

## Getting started

Requires Python and the dependencies in `requirements.txt`. The repository contains the pinned JPL kernel (`data/de440s.bsp`) and a local HKO reference file (`data/calendar_reference.json`).

```powershell
git clone https://github.com/cctsao1008/trng-iching.git
cd trng-iching
py -m pip install -r .\requirements.txt
```

1. Decide on a question if you intend to use the result for an *I Ching* reading.
2. Make **one** live cast:

   ```powershell
   py .\main.py cast
   ```

3. Confirm `mode == "live_trng_cast"` and `status == "complete"`.
4. Use the JSON for your own study or share it with ChatGPT alongside your question for optional interpretation.

The **alternative**, when you need technical traceability, is:

```powershell
py .\main.py cast --audit
```

**Do not run both commands for the same cast:** each invocation performs a *new* live TRNG request, not a different view of the previous sample. `--audit` prints the same compact fields **plus detailed evidence** for that single new cast.

### Example: compact JSON (v0.4.0)

The following is a real recorded sample presented using the compact v0.4.0 schema:

```json
{
  "schema_version": "0.4.0",
  "mode": "live_trng_cast",
  "status": "complete",
  "timestamp": "2026-11-24T19:26:29.939927+08:00",
  "randomness": {
    "source": "trng.info",
    "raw_hex": "a44916"
  },
  "hexagram": {
    "lines_bottom_to_top": [8, 7, 6, 7, 7, 7],
    "moving_lines": [3],
    "primary": {"number": 6, "name": "天水訟"},
    "relating": {"number": 44, "name": "天風姤"}
  },
  "calendar": {
    "lunar": {
      "year": 2026,
      "month": 10,
      "day": 16,
      "is_leap_month": false
    }
  },
  "solar_term": "小雪",
  "ganzhi": {
    "year": "丙午",
    "month": "己亥",
    "day": "壬寅",
    "hour": "庚戌"
  }
}
```

The compact JSON preserves the casting result and time context without including transport details, bit-level derivations, or dependency metadata.

## Human-readable view

The default commands still emit only JSON. For a single live cast with a
side-by-side ASCII diagram and a saved canonical record:

```powershell
py .\main.py cast --view human --json-out cast.json
```

Add `--audit` to save the full audit record. The destination must not already
exist. To redraw the same record offline, with no TRNG or time-context request:

```powershell
py .\main.py view --input cast.json
```

Lines are displayed top to bottom, numbered 6 to 1. An asterisk identifies
a moving line in the primary hexagram. Chinese names remain text; the strokes
use ASCII. For legacy Windows redirected streams, UTF-8 decoding may be needed.
If saving fails after acquisition, the command emits the JSON to stdout and
returns an error; do not redraw to bypass the failure. Add `--text` to the Human View command to display local classical reference
text (primary judgment, every moving line, and the relating judgment if
different; the special 用九/用六 passage is also displayed when applicable).
This is a display convention, not a rule for interpretation.

```powershell
py .\main.py view --input cast.json --text
```

For a new cast, add `--text` to `cast --view human --json-out <new-file>`.
No extra TRNG request or online text lookup is made. The JSON remains unchanged.

The local `data/zhouyi.json` contains the 64 hexagrams, 384 line statements,
special lines, Tuan, Images and Wenyan. Text is sourced from Chinese Wikisource;
`data/sources.json` identifies pinned revisions and source snapshot hashes.
See [data attribution and license](data/LICENSE.md). Structural and
captured-source consistency were audited; independent cross-edition collation
was not performed.

## JSON schema and audit mode

**v0.4.0 changes the public `cast` JSON layout**, not the randomness, hexagram, astronomical, lunar or Ganzhi computations.

| Default field | Meaning |
| --- | --- |
| `schema_version` | Cast output contract, `0.4.0` |
| `mode` | `live_trng_cast` or `manual_reference_cast` |
| `status` | `complete`, `partial`, or `cast_only` |
| `timestamp` | UTC+08 client receive time (or null for untimed manual input) |
| `randomness` | Provenance source and original 3-byte hex |
| `hexagram` | Bottom-to-top line values, moving positions (1-based), primary and relating names/numbers |
| `calendar.lunar` | Lunar year, month, day, leap-month flag |
| `solar_term` | Current solar-term name (not its exact changeover instant) |
| `ganzhi` | Year, month, day and hour pillars |
| `errors` | Present only when optional context lookup/calculation raises an error |

If requested, **`--audit` additionally includes `audit`** with the complete original engineering record:

| Audit section | Contents |
| --- | --- |
| `audit.capture` | UTC/local timestamps and their meaning |
| `audit.randomness` | TRNG endpoint, transport, raw hex, request and receive timestamps |
| `audit.cast` | Six-line conversion, line order, trigram details, original/relating hexagram bits and discarded bits |
| `audit.context.calendar` | HKO reference URLs, source SHA-256 and month-start data |
| `audit.context.astronomy` | JPL DE440s SHA-256, Skyfield version, coordinate conventions, Sun/Moon longitude and lunar phase angle |
| `audit.context.ganzhi` | Four-pillar derivation conventions and boundaries |

A `partial` cast **does not mean the random sample or hexagram was discarded**; it means required time context is incomplete. Stop and investigate the reported issue rather than requesting another cast to bypass it. A successful process exit alone is not proof of `status="complete"`.

A manually supplied `--hex` value is **not a live TRNG result**; without `--at`, it has `mode="manual_reference_cast"`, `status="cast_only"`, and null time context. This is for reference, not live acceptance.

Windows terminals may show Unicode escapes (`\uXXXX`) for Chinese text; JSON parsers decode these normally.

## Design and compatibility

- **Casting, not interpretation.** Python records a verifiable hexagram; any *I Ching* reading happens separately.
- **No hidden redraw.** A failed call never silently triggers another TRNG request.
- **Pinned provenance.** The local JPL kernel is SHA-256 checked; the HKO reference stores source hashes.
- **Concise default, complete audit.** Use `cast` for interpretation and `cast --audit` for engineering investigation.
- **Versioned public output.** Existing v0.3.0 consumers must adapt to the new v0.4.0 `cast` fields; `astronomy` and `calendar` reference commands retain their own outputs.

Other reference commands:

```powershell
py .\main.py calendar --date 2026-11-24
py .\main.py astronomy --at 2026-11-24T11:26:29Z --start 2026-11-01 --days 40
py .\main.py cast --hex a44916
```

On Windows, network acquisition uses PowerShell with the system proxy; elsewhere it uses Python `urllib`. The script never sends your question to the randomness provider. ChatGPT does not invoke the local script automatically.

## References and scope

The data pipeline uses [TRNG.info](https://trng.info/), [NASA JPL ephemerides](https://ssd.jpl.nasa.gov/), [Skyfield](https://rhodesmill.org/skyfield/), and the [Hong Kong Observatory](https://www.hko.gov.hk/en/gts/time/conversion1_text.htm).

**This tool produces a traceable casting record, not an *I Ching* interpretation or a scientifically validated forecast of future events.**
