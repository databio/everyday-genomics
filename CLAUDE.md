# everyday-genomics

Monthly-updated metrics that genomics is entering everyday life; sibling of
`databio/stats`. See README.md for structure and commands.

- HARD RULE: machine-readable sources only. Every metric needs a script that
  fetches it from an API/CSV/stable table on a schedule and can backfill
  history. Never add hand-transcribed, press-release, or AI-researched
  numbers, and never copy values out of a figure. Decline and say why.
- `config.json` defines metrics; `scripts/common.py` holds the shared
  fetch/CSV loop (`update_metric`); one `scripts/update_<source>.py` per source.
- CSV convention: `date,value,source,notes`, monthly `YYYY-MM`, oldest first.
- Adding a source: write a `count(ym) -> int` function and call
  `update_metric(name, tag, count, cfg)`. Add to the workflow and README table.
- NCBI E-utilities: max 3 req/s without `NCBI_API_KEY`; `common.get` sleeps.
