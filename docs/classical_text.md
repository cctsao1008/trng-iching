# Classical text acquisition (P2B)

Run explicitly from the repository root:

```powershell
py .\tools\build_zhouyi.py --out .\zhouyi_stage
```

The directory must not exist. The builder obtains the 64 individual Chinese
Wikisource pages through the MediaWiki API, stores parsed HTML snapshots and
revision IDs, and emits a report. It publishes a candidate JSON only if all
64 structural checks pass. This is not a textual collation or approval.
The parser is deliberately strict; inspect failed source HTML rather than
inventing text or weakening checks. It has not yet been tested against live
API markup. The casting CLI does not invoke this tool.

Replay pinned revisions into a fresh directory with
`--pins .\zhouyi_stage\sources.json`. MediaWiki rendering can change even
for the same revision; the stored HTML hashes identify the captured snapshots.

Source: https://zh.wikisource.org/wiki/周易
Ancient text is public domain; applicable modern Wikisource editorial
contributions are CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/).
Retain the source manifest and attribution with any redistributed corpus.
No third-party NC-SA dataset is imported.

Do not commit the staging directory as a canonical corpus until P2C checks
and source collation are complete.

## Resume a partial acquisition

```powershell
py .\tools\build_zhouyi.py --resume .\zhouyi_stage --out .\zhouyi_stage_v2
```

Cached HTML snapshots are reused only after SHA-256 verification. The builder
fetches missing pages only, retaining the original revisions of cached pages.
Explicit exceptions cover source page aliases, inline judgments, 習坎 and the
comma-delimited 否 line labels. Original judgment text is preserved when no
separate heading exists. Other structural checks remain unchanged.

## P2C offline audit

```powershell
py .\tools\validate_zhouyi.py --stage .\zhouyi_stage_v2 --report .\zhouyi_audit.json
```
The gate checks the 64 pinned source entries, raw snapshot hashes, all
1,026 text units (including the two special-line images and two Wenyan
sections), independent field/line-label checks, and exact reproduction
using the original extraction parser. It does not independently verify
the parser's transcription or collate another edition. A PASS is not
a claim of cross-edition textual correctness. Keep staging files intact.
