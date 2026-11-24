# TRNG I Ching · 真隨機易經

> **Let physical randomness choose the hexagram. Let astronomy record the moment. Let interpretation remain open.**
>
> **讓真實物理世界的隨機性決定卦象，讓可驗證的天文曆法記錄當下，讓人與 AI 自由探索卦象和問題之間的意義。**

## Why this exists · 專案的靈魂

The *I Ching* is an ancient way of asking questions through change and symbols. This project brings that practice into conversation with **physical randomness, modern astronomy, reproducible computation, and AI**—without pretending that these are the same thing.

A hexagram is not selected by a language model, a hidden prediction rule, or the answer someone hopes to receive. It comes from **one real, external TRNG sample**. At the moment that sample is received, **JPL astronomy, an official lunar calendar, and the sexagenary cycle describe the surrounding time**. Only after these facts are fixed does a person bring their question to ChatGPT.

**The boundaries are the point:**

- **Chance is not steered.** Neither Python nor GPT gets to pick or reroll a more desirable hexagram.
- **Time is context, not a cause of the cast.** Astronomical and calendrical facts describe the moment; they never modify the random bits or the six lines.
- **Meaning is not preprogrammed.** Python calculates and records; interpretation belongs to the dialogue between the questioner and AI. There is no mandatory school, reading plan, counter-reading, or action checklist.

The purpose is not to build a fortune-telling machine with predetermined answers. It is to build a **traceable meeting point between an unpredictable event, a precisely described moment, a human question, and open-ended thought**.

這個工具最重要的不是「替人決定未來」，而是**不預設結果、不竄改卦象、不把解釋寫死**：以真亂數起卦，以天文曆法記時，最後保留探索與思考的自由。

## How a cast works

```text
             A question
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
                  Human question + ChatGPT
                     (free interpretation)
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

### 3. Interpretation stays open

Python does **not** select scripture, decide whether a cast is favorable, or impose a reading method. You can give the JSON and your question to ChatGPT and explore the result freely. The only essential integrity boundary is that the original random input, hexagrams, moving lines, timestamps, and computed facts **must not be silently rewritten**.

No mandatory interpretation protocol or predetermined conclusion is built into the project.

## Getting started

Requires Python and the dependencies in `requirements.txt`. The repository contains the pinned JPL kernel (`de440s.bsp`) and a local HKO reference file (`calendar_reference.json`).

```powershell
git clone https://github.com/cctsao1008/trng-iching.git
cd trng-iching
py -m pip install -r .\requirements.txt
```

1. Decide what you want to ask.
2. Make **one** live cast:

   ```powershell
   py .\main.py cast
   ```

3. Confirm `mode == "live_trng_cast"` and `status == "complete"`.
4. Share the JSON with ChatGPT alongside your question.

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

The JSON gives GPT the question's **fixed inputs and time context** without flooding its interpretation with request transport, bit-level derivation, and dependency metadata.

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

- **Deterministic data, open-ended interpretation.** Preserve the separation between generation, time context and meaning.
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

Offline projection regression tests, with **no TRNG request**:

```powershell
py -m unittest discover -s tests -v
```

On Windows, network acquisition uses PowerShell with the system proxy; elsewhere it uses Python `urllib`. The script never sends your question to the randomness provider. ChatGPT does not invoke the local script automatically.

## References and scope

The data pipeline uses [TRNG.info](https://trng.info/), [NASA JPL ephemerides](https://ssd.jpl.nasa.gov/), [Skyfield](https://rhodesmill.org/skyfield/), and the [Hong Kong Observatory](https://www.hko.gov.hk/en/gts/time/conversion1_text.htm).

Independent research references include [Taiyin Ephemeris](https://github.com/RedSC1/taiyin-ephemeris), [stem-branch](https://github.com/h4x0r/stem-branch), and [Chinese Calendar Dataset](https://github.com/Kuangchujia/chinese-calendar-dataset). They do not silently replace the pinned computational sources. [I Ching Research Skill](https://github.com/ProfesseurHaipeng/iching-research-skill) and [I Ching Today](https://iching.today/method) provide optional cultural/methodological background, **not compulsory interpretation rules**.

**This is an experiment in transparent casting and reflective interpretation, not a scientifically validated method of forecasting events.** A symbol may invite insight; it does not replace evidence in consequential real-world decisions.
