# Reference data provenance and licensing

## Zhouyi

`zhouyi.json` is an extracted and structured transcription of the received
Zhouyi text from [Chinese Wikisource](https://zh.wikisource.org/wiki/周易).
The ancient work is public domain. Applicable modern editorial contributions
and this adapted transcription are distributed under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
Attribution: Chinese Wikisource contributors; see each pinned page URL in
`sources.json` for source and revision history. Changes: extraction from HTML,
separation of headings and passages, outer whitespace trimming, newline
joining, structured JSON arrangement; source characters and punctuation
retained where extracted. No endorsement is implied.

Source policy: https://zh.wikisource.org/wiki/Wikisource:版權信息

Corpus acquisition and captured-source projection audit: 64/64, 966 text units.
2026-11-25 extraction cleanup: removed a repeated Wikisource variant-tooltip CSS block from 32 ordinary line statements. Explicit inline variant annotations in ordinary lines are separated from the base reading; `text_with_variants` preserves the CSS-free annotated source string. Source revision IDs and captured HTML hashes remain unchanged. This is a lossless textual cleanup relative to the captured transcription (excluding CSS), not a fresh retrieval or edition collation.

Independent cross-edition collation was not performed. The historical
acquisition and audit tools remain available in Git history at
`6f09df4a6c5aff6e3537e5e47fe7ec6c02963685`.

## Other references

- `de440s.bsp`: NASA JPL DE440s, https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/de440s.bsp
- `calendar_reference.json`: Hong Kong Observatory Gregorian–Lunar conversion
  tables, https://www.hko.gov.hk/en/gts/time/conversion1_text.htm ; source
  details recorded in the JSON.

The Zhouyi license statement is not a blanket license for the JPL or HKO
reference files or the Python source code. Their respective source terms apply.
