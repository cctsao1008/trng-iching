# TRNG I Ching

**TRNG I Ching** is a research-oriented workflow that combines true random number generation, astronomical ephemerides, Chinese calendrical calculations, and documented I Ching methods. Its goal is to provide a **consistent, transparent, and reproducible computational basis** for interpretation.

The workflow separates objective data and deterministic calculations from symbolic and contextual interpretation.

## Principles

- **Randomness determines the cast.** Obtain an independent sample from a true random number generator (TRNG). Do not select, alter, or redraw a valid sample to obtain a preferred outcome.
- **Time and astronomy provide context.** Timestamp each sample and describe the astronomical conditions at that instant. Astronomical data must not silently change the TRNG-derived cast.
- **Python computes, ChatGPT interprets.** Python handles all specified calculations and conversions, including six-line casting, hexagram identification, calendrical information, and the selection of applicable textual rules. ChatGPT interprets the normalized result rather than recalculating it.
- **Sources are complementary, not interchangeable.** Distinguish primary sources, independent verification, calendrical reference data, and I Ching reference material. Do not average incompatible astronomical outputs or arbitrarily choose the result that fits an interpretation.
- **Methods are explicit and versioned.** Record source provenance, coordinate/time conventions, calendar boundaries, casting methods, and interpretation traditions. Do not silently combine incompatible schools.
- **Output is portable.** Produce one structured JSON result suitable for sharing across conversations. No database or per-reading file storage is required.

## Source roles

| Source | Intended role |
| --- | --- |
| [TRNG.info](https://trng.info/) | Independent random input for casting |
| [NASA JPL](https://ssd.jpl.nasa.gov/) ephemerides | Candidate primary astronomical reference for Sun, Moon, and relevant celestial positions |
| [IMCCE](https://www.imcce.fr/) | Independent astronomical cross-checks where needed |
| [Taiwan CWA](https://www.cwa.gov.tw/) / [Hong Kong Observatory](https://www.hko.gov.hk/) | Reference data for Chinese calendar dates, solar terms, and lunar events |
| [USNO](https://aa.usno.navy.mil/) | Existing prototype source and an optional reference for lunar/seasonal events |
| I Ching textual and software references | Documented casting, hexagram, textual, and traditional calendrical mapping conventions |

These are **roles under evaluation**, not a requirement to query every provider on every run. Astronomical calculations may use locally available, versioned ephemeris resources; independent checks are separate from normal casting.

## Workflow

1. **Define the question in ChatGPT before sampling**, including its relevant time horizon.
2. **Collect a single TRNG sample and timestamp it.**
3. **Calculate and normalize in Python:** the six lines, moving lines, primary and relating hexagrams, astronomical context, Chinese calendar information, and applicable I Ching mapping rules.
4. **Print structured JSON to the terminal.** Include the raw input, normalized results, provenance, versions, and explicit statuses for unavailable fields.
5. **Paste the JSON into ChatGPT** for a source-aware interpretation that distinguishes classical text, traditional symbolism, astronomical facts, and real-world evidence.

The question remains in the conversation; it is not submitted to TRNG or astronomical providers. The tool does not automatically store readings.

## Interpretation boundaries

Traditional methods such as the twelve monthly hexagrams (十二消息卦), hexagram qi (卦氣), and Najia six-line divination (六爻納甲) have different historical assumptions. When included, their calculations and texts must be labeled with the chosen method and source. They are not interchangeable with the TRNG-generated primary hexagram.

Accurate random samples, ephemerides, and calendar conversions **do not establish the predictive validity of divination**. Interpretations are a framework for cultural inquiry and reflection, not a substitute for independent evidence in financial, medical, legal, or other consequential decisions.

## Development and decisions

Architecture, implementation details, algorithm conventions, and the JSON contract are tracked in [GitHub Issues](https://github.com/cctsao1008/trng-iching/issues), starting with [Issue #1](https://github.com/cctsao1008/trng-iching/issues/1).
