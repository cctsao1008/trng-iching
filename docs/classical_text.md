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
