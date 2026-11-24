# TRNG I Ching

**TRNG I Ching v0.3.0** is a small, auditable Python data pipeline for I Ching casting. It obtains one true-random sample from TRNG.info, deterministically computes six lines and the King Wen hexagram(s), and attaches documented astronomical, lunar-calendar and four-pillars context. **Python does not interpret the cast; ChatGPT does.**

**Current status:** Live end-to-end integration **PASS** on Windows (2026-11-24, commit `8f85d7a`). See [Issue #1](https://github.com/cctsao1008/trng-iching/issues/1) for the acceptance record. No further draw is required to confirm this milestone.

## Quick start (Windows)

Install the pinned Python dependency once in the interpreter used by `py`:

```powershell
cd E:\trng-iching
py -m pip install -r .\requirements.txt
```

The repository already contains `de440s.bsp` (JPL DE440s) and `calendar_reference.json` (HKO reference). Their default paths resolve relative to `main.py`, so a separate checkout also works at `D:\my-github\trng-iching`.

**For each new question, formulate the question and time horizon *before* drawing. Then execute exactly one of the following commands (not both):**

```powershell
# Recommended: complete data and provenance
py .\main.py cast --audit
```

Or, if less detailed JSON is preferred:

```powershell
py .\main.py cast
```

Every execution of `cast` without `--hex` requests a **new** three-byte sample from TRNG.info. `--audit` only changes output detail, not the number of draws. Never redraw because a hexagram looks unfavorable, or to bypass an error.

After the command, check that the JSON has `schema_version: "0.3.0"`, `mode: "live_trng_cast"` and **`status: "complete"`**. Then copy the **entire JSON** into the same ChatGPT conversation as the previously stated question. Example request:

> 請根據以下 trng-iching v0.3.0 JSON 解讀我剛才提出的問題。先確認本卦、之卦與動爻，再選擇適合的《周易》經文與解卦方法，清楚區分傳統象徵解讀、天文曆法事實與實際決策證據。不得自行更動 Python 的卦象。（貼上完整 JSON）

ChatGPT does not execute this CLI automatically. The user runs Python on their PC and supplies the result for interpretation. The question itself is not sent to TRNG.info.

## Live-only, fail-fast operating policy

- **Only real online end-to-end runs count for acceptance.** Do not use simulated/fixed-hex/offline tests to claim a PASS.
- **Exactly one TRNG request per cast.** There is no automatic retry, resampling or pseudorandom fallback.
- **STOP on any failure.** An HTTP error, nonzero process exit, unparseable JSON, bad six-line conversion, missing context, or top-level `partial` is not an accepted full reading. Diagnose the same failure before any new cast; do not use a new sample to hide it.
- **A zero exit code alone is insufficient.** The application can correctly serialize a valid cast with `status=partial` and exit zero. For strict acceptance, require `complete` and all three context components: `calendar.status=official_reference_lookup`, `astronomy.status=calculated` and `ganzhi.status=calculated`.

The following **alternative** PowerShell snippet performs one live acquisition and checks the strict context gate in the same block. Use it **instead of**, not after, the quick-start `cast` command:

```powershell
& {
    Set-Location E:\trng-iching
    $json = (& py .\main.py cast --audit) -join "`n"
    if ($LASTEXITCODE -ne 0) { throw 'STOP: Online cast failed' }
    $r = $json | ConvertFrom-Json -ErrorAction Stop
    Write-Output $json
    if ($r.schema_version -ne '0.3.0' -or
        $r.mode -ne 'live_trng_cast' -or
        $r.randomness.source -ne 'trng.info' -or
        $r.status -ne 'complete' -or
        $r.context.calendar.status -ne 'official_reference_lookup' -or
        $r.context.astronomy.status -ne 'calculated' -or
        $r.context.ganzhi.status -ne 'calculated') {
        throw 'STOP: Incomplete online integration result'
    }
    Write-Host '[PASS] LIVE CONTEXT GATE'
}
```

This snippet checks schema, source and context availability; the formal acceptance also verified the actual sample's six-line derivation. A standalone `Write-Host '[PASS]'` outside this block is **not** proof that an earlier command passed.

## What the pipeline returns

| JSON field | Meaning |
| --- | --- |
| `capture` | UTC receive time and UTC+08:00 local time; client receive time is **not** claimed to be TRNG hardware generation time |
| `randomness` | TRNG provider, raw six-digit hexadecimal sample and request/receive timestamps; `--audit` adds transport details |
| `cast` | Six lines **bottom-to-top**, moving positions, primary and relating King Wen hexagrams; `--audit` adds bit groups and provenance |
| `context.calendar` | HKO-based official lunar-date lookup from the local reference file |
| `context.astronomy` | Sun/moon apparent ecliptic longitudes and current solar term from locally pinned JPL DE440s with Skyfield |
| `context.ganzhi` | Year/month/day/hour pillars under stated boundaries: Li Chun solar year, solar-Jie month, UTC+08:00 midnight day and civil two-hour bins |
| `status` | `complete` when requested context is available; `partial` when some context is missing; manual no-time references may be `cast_only` |
| `errors` | Component-specific failures, if any |

### Fixed casting algorithm

1. Request **three random bytes** and preserve the six-digit hex string.
2. Read the first **18 bits MSB-first** in six groups of three, **bottom-to-top**. Each line is `6 + popcount(three_bits)`, yielding 6/7/8/9. Ignore the remaining six bits.
3. Lines with values **6 or 9** move. Flip only those lines for the relating hexagram. With no moving lines, primary and relating hexagrams are identical.
4. Map primary and relating six-line patterns to the King Wen numbering and trigrams. Astronomical/calendar data add context only; they **do not alter the drawn hexagram**.

The Python program does **not** implement Zhu Xi passage selection, store an I Ching text corpus, decide an interpretive school, provide advice, call a GPT API or automatically store readings. Classical quotation, interpretation method and situation-specific reasoning belong to GPT.

### Windows console and network behavior

- Windows uses built-in PowerShell's HTTP client with the system web proxy and integrated Windows credentials to acquire the one TRNG sample; other platforms use Python `urllib`. This is a **platform choice before the request**, not a retry after a failed connection.
- JSON output is ASCII-safe (`ensure_ascii=True`). Chinese names and hexagram glyphs may appear as standard `\uXXXX` escapes in the terminal; parsing JSON restores them. This avoids Windows `cp950` encoding failures.
- Local JPL and HKO references are not fetched over HTTP for every cast. The pinned ephemeris and calendar index provide reproducible local computations and lookups.

## Sources and background

| Source | Role |
| --- | --- |
| [TRNG.info](https://trng.info/) | Online source for one true-random sample |
| [NASA JPL](https://ssd.jpl.nasa.gov/) | Pinned `de440s.bsp` astronomical ephemeris |
| [Skyfield](https://rhodesmill.org/skyfield/) | Astronomical calculations; pinned in `requirements.txt` (`skyfield==1.55`) |
| [Hong Kong Observatory](https://www.hko.gov.hk/en/gts/time/conversion1_text.htm) | Official lunar-calendar dates compiled into `calendar_reference.json` |
| [Taiwan Central Weather Administration](https://www.cwa.gov.tw/), [US Naval Observatory](https://aa.usno.navy.mil/), [IMCCE/INPOP](https://www.imcce.fr/inpop/) | Optional independent research references, not required live API calls |
| [GB/T 33661-2017](https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=E107EA4DE9725EDF819F33C60A44B296) | Reference standard for Chinese lunisolar calendar definitions |

Other CLI subcommands (`calendar`, `calendar-sync`, `astronomy`) serve explicit reference lookup/synchronization or research; they are **not** substitutes for the required live TRNG cast or its online acceptance. The legacy `--hex` option remains available for explicit manual reference/replay, but **is not used for acceptance testing**.

Solar longitude, lunar calendar date and sexagenary pillars use different boundaries and conventions, which must not be silently mixed. Near solar terms or civil-date boundaries, interpret the timestamp and conventions carefully. Divination is a cultural and reflective practice and is not validated evidence for forecasting stock prices or making other consequential decisions.
