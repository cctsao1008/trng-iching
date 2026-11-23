# TRNG I Ching

**TRNG I Ching** is a research-oriented workflow combining true random number generation, astronomical ephemerides, Chinese calendrical calculations, and documented I Ching methods. Its purpose is to establish a **consistent, transparent, and reproducible computational basis** for interpreting a cast.

The system keeps random sampling, astronomical facts, traditional rules, and contextual interpretation distinct.

## Core principles

- **Randomness determines the cast.** Use a single valid sample from a true random number generator (TRNG). Never redraw, filter, or replace a sample to obtain a preferred hexagram.
- **Astronomy provides temporal context.** Record the sampling time and derive astronomical events from clearly identified ephemerides. Astronomical conditions do not alter the TRNG-generated cast.
- **Python computes; ChatGPT interprets.** Python performs deterministic calculations, conversions, rule selection, and output formatting. ChatGPT uses the completed result to interpret classical texts and the question's context, rather than recalculating underlying data.
- **Sources complement and verify each other.** Assign clear roles to primary computation, independent cross-checks, and published calendar references. Do not average incompatible astronomical values or choose results to suit a preferred reading.
- **Conventions and provenance are explicit.** Identify time scales, coordinate systems, calendar boundaries, source versions, and the traditional I Ching method used. Never silently mix conventions from different schools.
- **The output is portable.** Present one structured, versioned JSON document through the terminal; no database or automatic storage of individual readings is required.

## Sources and references

| Source | Intended role |
| --- | --- |
| [TRNG.info](https://trng.info/) | True-random sample for the six-line cast |
| [NASA JPL](https://ssd.jpl.nasa.gov/) | Primary candidate for planetary and lunar ephemeris calculations |
| [IMCCE](https://www.imcce.fr/) / [INPOP](https://www.imcce.fr/inpop/) | Independent astronomical model and verification reference |
| [Taiwan Central Weather Administration](https://www.cwa.gov.tw/) and [Hong Kong Observatory](https://www.hko.gov.hk/) | Published Chinese calendar, solar-term, and lunar-event references |
| [US Naval Observatory](https://aa.usno.navy.mil/) | Supplementary reference for lunar phases and seasonal events |
| [Skyfield](https://rhodesmill.org/skyfield/) | Candidate Python tooling for local ephemeris and astronomical-event calculations |
| [Chinese calendar standard GB/T 33661-2017](https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=E107EA4DE9725EDF819F33C60A44B296) | Reference for modern Chinese lunisolar calendar definitions and calculation rules |

Source roles do not imply that every service is queried for every cast. Local, versioned ephemeris data can support deterministic calculations; independent references are used when validation is needed.

Related open-source work includes [iching-research-skill](https://github.com/ProfesseurHaipeng/iching-research-skill), which emphasizes transparent computation and textual provenance, and [zzkt/i-ching](https://github.com/zzkt/i-ching), which distinguishes randomness sources from casting methods. They are research references, not required runtime dependencies.

## Workflow

1. **Formulate the question** and its relevant time horizon in ChatGPT before sampling.
2. **Acquire one TRNG sample** and record client-side request/response timestamps, with explicit UTC and local-time representations.
3. **Process the data in Python:** derive six lines, moving lines, primary and relating hexagrams, astronomical events, Chinese calendar values, and any explicitly selected traditional mappings.
4. **Emit normalized JSON to standard output**, including source provenance, algorithm versions, conventions, and validity statuses. Missing or unsupported values must be identified rather than inferred.
5. **Provide the JSON to ChatGPT** for interpretation informed by classical sources, calendar context, and the question itself.

The question stays in the conversation and is not transmitted to randomness or astronomy providers. The tool does not automatically save readings.

## Astronomical and calendrical consistency

Astronomical events and traditional calendrical labels involve different kinds of rules. In particular, solar terms depend on a defined solar-longitude convention, while lunisolar dates depend on new-moon instants, civil-day assignment, and leap-month rules. Sexagenary year, month, day, and hour calculations require explicitly selected boundary conventions.

Results close to midnight, a solar-term transition, or another calendrical boundary require particular care. Independent sources should be compared using compatible time scales, reference frames, and stated precision before discrepancies are assessed.

## I Ching interpretation boundaries

The TRNG-derived hexagram remains separate from time-related traditional mappings. The twelve monthly hexagrams (十二消息卦), hexagram qi (卦氣), and Najia six-line divination (六爻納甲) are distinct traditions. When used, their source, school, and mapping rules must be identified; one must not silently override another.

The distinction between **astronomical facts**, **calendrical calculation**, **historical interpretation**, and **contemporary reflection** is fundamental. Reproducible computations do not establish that divination can reliably predict future events. This workflow supports cultural study and structured reflection, not a substitute for independent evidence in consequential decisions.
