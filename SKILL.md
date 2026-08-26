---
name: everyday-genomics
description: Fetch and plot "everyday genomics" metrics (PubMed, ClinicalTrials.gov, NCBI SRA monthly counts) from the databio/everyday-genomics data API. Use when a slide, page, or figure needs an up-to-date "genomics is growing" chart, or when you need the underlying numbers.
---

# everyday-genomics data API

Monthly time series showing genomics entering everyday life. Data is refreshed
by GitHub Actions on the 2nd of each month and served as static files from
GitHub Pages, so any URL below is a stable, CORS-friendly API endpoint.

Base URL: `https://dev.databio.org/everyday-genomics/`

## Endpoints

| URL | What |
|---|---|
| `config.json` | Metric registry: `metrics.<name>.{title,unit,source,query}` |
| `data/<name>.csv` | Monthly series, columns `date,value,source,notes`, `date` is `YYYY-MM`, oldest first |
| `plots/light/<name>.svg` (or `.png`) | Static plot, white background: monthly bars + 12-mo mean, and cumulative panel |
| `plots/dark/<name>.svg` (or `.png`) | Same, transparent background, light text (for Reveal.js dark slides) |
| `plots/{light,dark}/summary.svg` | Multi-panel cumulative figure of every metric |

Metric names (list is authoritative in `config.json`):

- `pubmed_genomics`, `pubmed_crispr`, `pubmed_genetic_testing`: papers added to PubMed per month (Entrez date)
- `trials_gene_therapy`, `trials_crispr`, `trials_genetic`: studies first posted on ClinicalTrials.gov per month
- `sra_experiments`: experiments made public in NCBI SRA per month
- `fda_gene_therapies` (cumulative): FDA-approved cellular and gene therapy products
- `fda_companion_diagnostics` (cumulative): FDA-approved companion diagnostic indications
- `clinvar_variants` (cumulative): variant records in ClinVar
- `species_with_genomes` (cumulative): eukaryotic species with a chromosome-level assembly

Metric kinds (`config.json` `metrics.<name>.kind`):

- `monthly` (default): `value` is the count for that month; sum for cumulative.
  The last row is the current, partial month; drop it before plotting.
- `cumulative`: `value` is already the running total as of that month (e.g.
  approved products to date); diff for monthly increments. Do not sum.

## Get the numbers

```bash
curl -s https://dev.databio.org/everyday-genomics/data/pubmed_crispr.csv | tail -3
```

```python
import pandas as pd
df = pd.read_csv("https://dev.databio.org/everyday-genomics/data/pubmed_crispr.csv")
df = df.iloc[:-1]                 # drop partial current month
df["cumulative"] = df["value"].cumsum()
```

## Static image in a slide or page

```html
<img src="https://dev.databio.org/everyday-genomics/plots/dark/pubmed_crispr.svg" style="width:100%">
```

## Live Vega-Lite chart

Point `data.url` at a CSV; the chart stays current with no rebuild.

```html
<script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
<div id="chart"></div>
<script>
vegaEmbed("#chart", {
  $schema: "https://vega.github.io/schema/vega-lite/v5.json",
  data: {url: "https://dev.databio.org/everyday-genomics/data/pubmed_crispr.csv",
         format: {type: "csv", parse: {value: "number"}}},
  width: 500, height: 220,
  transform: [
    {filter: "datum.date < timeFormat(now(), '%Y-%m')"},            // drop partial month
    {window: [{op: "sum", field: "value", as: "cum"}], sort: [{field: "date"}]}
  ],
  mark: {type: "area", color: "#1f4e8c", opacity: 0.8},
  encoding: {
    x: {field: "date", type: "temporal", title: null},
    y: {field: "cum", type: "quantitative", title: "cumulative papers"}
  }
}, {actions: false});
</script>
```

Variations: use `mark: "bar"` with `y: {field: "value"}` for monthly counts; add
`{window: [{op: "mean", field: "value", as: "roll"}], frame: [-11, 0]}` for a
12-month rolling mean; overlay several metrics by loading each CSV in a
`layer` with a `calculate` transform that tags the series name. For dark
slides set `config: {background: null, axis: {labelColor: "#eee", titleColor: "#eee"}}`.

## Adding a metric

Edit `config.json` in https://github.com/databio/everyday-genomics: any PubMed
or ClinicalTrials.gov query string works as a new entry; the monthly workflow
backfills it from 2000. Other sources need a `scripts/update_<source>.py`; see
`CLAUDE.md` and `docs/future-sources.md`.
