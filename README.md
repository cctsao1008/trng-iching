# TRNG Hexagram Casting

**A transparent, reproducible hexagram casting tool for use with the I Ching.**

One physical random sample determines the hexagram. Independently calculated astronomical and calendrical information describes the moment of casting. A fixed local collection of classical reference text provides context for human or AI interpretation.

This is a **casting tool**, not an interpretation or prediction engine.

**Randomness determines the hexagram; astronomy and calendars describe the time; classical text provides a reference; interpretation is left to the reader.**

```text
TRNG.info ──> Six lines ──> Primary / relating hexagrams
                                  |
Client receive time ──> JPL / HKO / Ganzhi
                                  |
                          Casting record
                           /           \
                      JSON          Human View <── Zhouyi text
                           \           /
                         Human or AI reading
```

## Quick start

```powershell
git clone https://github.com/cctsao1008/trng-iching.git
cd trng-iching
py -m pip install -r .\requirements.txt
```

Make one live cast and display the hexagrams and classical text while saving the complete audit JSON:

```powershell
py .\main.py cast --audit --view human --text --json-out cast_audit.json
```

Confirm `Mode: live_trng_cast | Status: complete`. Share the saved JSON with an AI alongside your question, or study the result yourself.

The output filename must be new; existing cast records are not overwritten.

### Example: Human View

Actual recorded sample, displayed offline using the same saved cast:

```text
Hexagram Casting
Time: 2026-11-24T20:07:13.986461+08:00
Source: trng.info / 93e182
Mode: live_trng_cast | Status: complete

Primary 11: 地天泰
Relating 60: 水澤節

   PRIMARY            RELATING
6  ---- ----          ---- ----
5  ---- ----  *       ---------
4  ---- ----          ---- ----
3  ---------  *       ---- ----
2  ---------          ---------
1  ---------          ---------

* Line 3: Old Yang -> Yin
* Line 5: Old Yin -> Yang
Solar term: 小雪
Lunar: 2026-10-16
Four pillars: 丙午 己亥 壬寅 庚戌

Classical Text / 周易
本卦 11 泰：小往大來，吉亨。
九三：无平不陂，无往不復，艱貞无咎。勿恤其孚，于食有福。
六五：帝乙歸妹，以祉，元吉。
之卦 60 節：亨。苦節不可貞。
```

The terminal also prints the pinned source URLs for the displayed passages. Lines are drawn from top to bottom; line 1 is the bottom line. An asterisk marks a moving line.

### Reopen the same cast

```powershell
py .\main.py view --input cast_audit.json --text
```

This reads the existing JSON and local text without contacting TRNG.info or recalculating the time context.

## Commands

Choose **one** live casting command for each cast.

| Command (after `py .\main.py`) | Output |
| --- | --- |
| `cast` | Compact JSON |
| `cast --audit` | JSON with full technical provenance |
| `cast --view human --json-out cast.json` | ASCII hexagrams + saved compact JSON |
| `cast --view human --text --json-out cast.json` | ASCII hexagrams and classical text + saved compact JSON |
| `view --input cast.json` | Offline ASCII hexagrams |
| `view --input cast.json --text` | Offline ASCII hexagrams and classical text |

Add `--audit` to a live Human View command to save full audit JSON instead. The `--text` option is for Human View only and never changes JSON.

**Every invocation of live `cast` obtains a new sample.** Use `view` to revisit an existing cast, not another live command. If saving fails after acquisition, JSON is emitted to stdout and the command returns an error; do not redraw to bypass a failure.

## How casting works

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

### 3. Classical text is a reference, not a reading method

The bundled corpus contains 64 hexagram judgments, 384 line statements, 用九 and 用六, 彖傳, 大象傳, 小象傳, the two special-line images and 文言傳 (966 text units). The optional text display shows the primary judgment, all moving-line statements, the applicable special passage for all-moving Qian or Kun, and the relating judgment when different.

These are display conventions, not prescribed interpretation rules. The corpus is a pinned Chinese Wikisource received-text transcription; original source characters are retained. See [data provenance and licensing](data/LICENSE.md) and [source revisions](data/sources.json). Structural and captured-source consistency were audited; independent cross-edition collation was not performed.

## JSON schema and audit mode

The public casting record uses schema `0.4.0`. Human View is a separate presentation of the same record.

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

### Compact JSON example

The compact projection of the same recorded cast:

```json
{
  "schema_version": "0.4.0",
  "mode": "live_trng_cast",
  "status": "complete",
  "timestamp": "2026-11-24T20:07:13.986461+08:00",
  "randomness": {
    "source": "trng.info",
    "raw_hex": "93e182"
  },
  "hexagram": {
    "lines_bottom_to_top": [7, 7, 9, 8, 6, 8],
    "moving_lines": [3, 5],
    "primary": {"number": 11, "name": "地天泰"},
    "relating": {"number": 60, "name": "水澤節"}
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

## Repository layout

```text
trng-iching/
├── main.py                  CLI
├── sources.py               TRNG acquisition
├── iching.py                Hexagram conversion
├── astronomy.py             JPL astronomy
├── lunisolar.py             Lunar calendar and Ganzhi
├── human_view.py            ASCII and classical text
├── requirements.txt
├── README.md
├── .gitignore
└── data/
    ├── de440s.bsp            Pinned JPL ephemeris
    ├── calendar_reference.json
    ├── zhouyi.json
    ├── sources.json
    └── LICENSE.md
```

## Reference commands

These commands do not acquire TRNG randomness:

```powershell
py .\main.py calendar --date 2026-11-24
py .\main.py astronomy --at 2026-11-24T11:26:29Z --start 2026-11-01 --days 40
py .\main.py cast --hex a44916
```

On Windows, live acquisition uses PowerShell with the system proxy; elsewhere it uses Python `urllib`. The question is never sent to the randomness provider. Classical text, astronomy and calendar lookups for a normal cast use local reference files.

## References

[TRNG.info](https://trng.info/) · [NASA JPL ephemerides](https://ssd.jpl.nasa.gov/) · [Skyfield](https://rhodesmill.org/skyfield/) · [Hong Kong Observatory](https://www.hko.gov.hk/en/gts/time/conversion1_text.htm) · [Chinese Wikisource — Zhouyi](https://zh.wikisource.org/wiki/周易)

This tool does not establish the scientific validity of divination or forecast future events.
