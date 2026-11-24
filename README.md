# TRNG I Ching

**TRNG I Ching** is a research-oriented workflow combining true random number generation, astronomical ephemerides, Chinese calendrical calculations, and documented I Ching methods. Its purpose is to establish a **consistent, transparent, and reproducible computational basis** for interpreting a cast.

The system keeps random sampling, astronomical facts, traditional rules, and contextual interpretation distinct.

## Core principles

- **Randomness determines the cast.** Use a single valid sample from a true random number generator (TRNG). Never redraw, filter, or replace a sample to obtain a preferred hexagram.
- **Astronomy provides temporal context.** Record the sampling time and derive astronomical events from clearly identified ephemerides. Astronomical conditions do not alter the TRNG-generated cast.
- **Python collects and normalizes; ChatGPT interprets.** Python handles one TRNG acquisition and deterministic data conversions only. It does not select classical passages, lock the interpretation to a school, or produce judgments. ChatGPT uses the fixed cast as input for context-sensitive reading.
- **Sources complement and verify each other.** Assign clear roles to primary computation, independent cross-checks, and published calendar references. Do not average incompatible astronomical values or choose results to suit a preferred reading.
- **Conventions and provenance are explicit.** Identify time scales, coordinate systems, calendar boundaries, source versions, and the traditional I Ching method used. Never silently mix conventions from different schools.
- **Efficiency is a design requirement.** Reuse versioned official calendar tables for civil lunar dates; calculate precise astronomical events only where needed. Avoid repeated network requests, redundant computations, overlapping dependencies, and per-reading storage.
- **The output is portable.** Present one structured, versioned JSON document through the terminal; no database or automatic storage of individual readings is required.

## Sources and references

| Source | Intended role |
| --- | --- |
| [TRNG.info](https://trng.info/) | True-random sample for the six-line cast |
| [NASA JPL](https://ssd.jpl.nasa.gov/) | Pinned primary ephemeris reference for precise astronomical events |
| [IMCCE](https://www.imcce.fr/) / [INPOP](https://www.imcce.fr/inpop/) | Independent astronomical model and verification reference |
| [Hong Kong Observatory](https://www.hko.gov.hk/en/gts/time/conversion1_text.htm) and [Taiwan Central Weather Administration](https://www.cwa.gov.tw/) | Official Chinese lunar-calendar date lookup and independent calendrical reference |
| [US Naval Observatory](https://aa.usno.navy.mil/) | Supplementary reference for lunar phases and seasonal events |
| [Skyfield](https://rhodesmill.org/skyfield/) | Python tooling for locally computed solar terms and lunar-phase events |
| [Chinese calendar standard GB/T 33661-2017](https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=E107EA4DE9725EDF819F33C60A44B296) | Reference for modern Chinese lunisolar calendar definitions and calculation rules |

Official lunar-calendar reference data can be synchronized explicitly and then queried locally. Routine lunar-date lookups require neither a network request nor an ephemeris calculation. Source roles do not imply that every service is queried for every cast. Local, versioned ephemeris data can support deterministic calculations; independent references are used when validation is needed.

Related open-source work includes [iching-research-skill](https://github.com/ProfesseurHaipeng/iching-research-skill), which emphasizes transparent computation and textual provenance, and [zzkt/i-ching](https://github.com/zzkt/i-ching), which distinguishes randomness sources from casting methods. They are research references, not required runtime dependencies.

## Workflow

1. **Formulate the question** and its relevant time horizon in ChatGPT before sampling.
2. **Acquire one TRNG sample** and record client-side request/response timestamps, with explicit UTC and local-time representations.
3. **Process the data in Python:** derive the six lines, moving positions, original/relating hexagrams, and optional astronomy, calendar and four-pillars context. Missing local reference files do not invalidate the core cast.
4. **Emit versioned JSON to standard output** (schema 0.3.0) containing the deterministic cast plus independent optional contexts. Use `--audit` to expand raw bit groups, source fingerprints and detailed conventions; never fabricate missing values.
5. **Provide the JSON to ChatGPT** for classical-text reference, school/method choice, and context-sensitive interpretation. GPT may interpret the same cast differently for different questions but must not change the Python-generated lines or hexagrams.

The question stays in the conversation and is not transmitted to randomness or astronomy providers. The tool does not automatically save readings.

## CLI usage and versioned data contract

Run the script from the repository root, or call it by absolute path.
Default JPL and HKO reference paths resolve relative to the Python script,
not the shell's current directory. This supports separate work/home PCs.

```powershell
py .\main.py cast
py .\main.py cast --hex 02c60a
py .\main.py cast --hex 02c60a --at 2026-11-23T05:01:47.094054Z
py .\main.py cast --hex 02c60a --at 2026-11-23T05:01:47.094054Z --audit
```

Live `cast` makes **exactly one TRNG.info request**, never redraws or uses
a PRNG fallback, and attempts independently available local time context.
The `--hex` commands use fixed offline input and never contact TRNG.info.
Manual input must be exactly six hex digits; `--at` requires a timezone.

All `cast` invocations use schema **0.3.0**, with `schema_version`, `mode`,
`status`, `capture`, `randomness`, `cast` and `context` sections.
The `cast` section has six numeric lines ordered bottom to top, moving-line
positions and King Wen original/relating hexagram identifiers. It contains
**no** Zhu Xi passage-selection, classical texts, or `interpretation` block.
The `context` section has independent `calendar`, `astronomy` and `ganzhi`
statuses. Missing optional sources produce `partial` output with errors,
but do not invalidate a successful core cast or cause resampling.
Without `--at`, manual mode returns `cast_only` and `not_requested` contexts.
With all requested references, the result is `complete`.

The default JSON omits verbose bit and reference metadata; `--audit`
includes the used/discarded bits, six three-bit groups, pinned-source
provenance, and calendrical conventions. Both modes encode the same cast.
Input-validation errors exit nonzero rather than emitting a false cast.
The script does not call GPT, store readings, or include an interpretation
engine. This version intentionally supersedes legacy 0.1/0.2 preflight JSON.
## Astronomical and calendrical consistency

Solar/lunar positions and traditional calendrical labels involve different kinds of rules. In particular, solar terms depend on a defined solar-longitude convention, while lunisolar dates depend on new-moon instants, civil-day assignment, and leap-month rules. Sexagenary year, month, day, and hour calculations require explicitly selected boundary conventions.

Results close to midnight, a solar-term transition, or another calendrical boundary require particular care. Independent sources should be compared using compatible time scales, reference frames, and stated precision before discrepancies are assessed.

## I Ching interpretation boundaries

The TRNG-derived hexagram remains separate from time-related traditional mappings. The twelve monthly hexagrams (十二消息卦), hexagram qi (卦氣), and Najia six-line divination (六爻納甲) are distinct traditions. When used, their source, school, and mapping rules must be identified; one must not silently override another.

The distinction between **astronomical facts**, **calendrical calculation**, **historical interpretation**, and **contemporary reflection** is fundamental. Reproducible computations do not establish that divination can reliably predict future events. This workflow supports cultural study and structured reflection, not a substitute for independent evidence in consequential decisions.
