# Everyday genomics metrics

Tracks indicators that genomics is becoming part of everyday life, refreshed
monthly by GitHub Actions and served via GitHub Pages so slides and web pages
can embed plots that stay up to date.

Live: https://dev.databio.org/everyday-genomics/

## Rule: machine-readable sources only

Every metric must be fetched by a script from a stable, machine-readable
source (API, CSV/JSON download, or a stable HTML table) on a schedule, with a
backfillable history. No hand-transcribed numbers, no press-release milestones,
no AI-researched figures, no values copied from a figure. If a metric can only
be sourced that way (e.g. DTC genetic test sales), it does not belong in this
repo. See `docs/future-sources.md` for what qualifies.

## Metrics

| Metric | Source | Script |
|---|---|---|
| `pubmed_genomics`, `pubmed_crispr`, `pubmed_genetic_testing` | PubMed E-utilities, papers by month added to PubMed (Entrez date) | `scripts/update_pubmed.py` |
| `trials_gene_therapy`, `trials_crispr`, `trials_genetic` | ClinicalTrials.gov API v2, studies by first-post month | `scripts/update_clinicaltrials.py` |
| `sra_experiments` | NCBI SRA E-utilities, experiments by publication month | `scripts/update_sra.py` |
| `fda_gene_therapies` (cumulative) | FDA CBER approved cellular & gene therapy list, dated from each product page; cord-blood products excluded | `scripts/update_fda_gene_therapies.py` |
| `fda_companion_diagnostics` (cumulative) | FDA companion diagnostics list, by approval date | `scripts/update_fda_companion_diagnostics.py` |
| `clinvar_variants` (cumulative) | ClinVar E-utilities, variant records by creation date | `scripts/update_clinvar.py` |
| `species_with_genomes` (cumulative) | GoaT API, eukaryotic species with a chromosome-level assembly by assembly date | `scripts/update_species_genomes.py` |

Metric definitions (query strings, titles, units) live in `config.json`. To add
a PubMed or ClinicalTrials metric, add an entry there and run the script.

## Data format

`data/<metric>.csv`, one row per month, oldest first:

```
date,value,source,notes
2020-01,412,pubmed_esearch,
```

Each run fetches missing months from `backfill_start` and refetches the last
`refresh_months` (indexing lags, so recent months grow).

Metrics with `"kind": "cumulative"` in `config.json` store a running total
instead of a monthly count (plots and `index.html` handle both).

## Using the data

See [SKILL.md](SKILL.md) for a full API reference with pandas and Vega-Lite examples.

Stable URLs, fetchable from anywhere:

- CSV: `https://dev.databio.org/everyday-genomics/data/<metric>.csv`
- Static plots: `https://dev.databio.org/everyday-genomics/plots/{light,dark}/<metric>.{svg,png}`
  and `.../plots/{light,dark}/summary.svg`. Dark plots have a transparent
  background for Reveal.js slides.
- Live charts: `index.html` renders every metric with Vega-Lite from the CSVs.

## Commands

```bash
pip install -r requirements.txt
NCBI_API_KEY=... python scripts/update_pubmed.py   # key optional, raises rate limit
python scripts/update_sra.py
python scripts/update_clinicaltrials.py
python scripts/update_fda_gene_therapies.py
python scripts/update_fda_companion_diagnostics.py
python scripts/update_clinvar.py
python scripts/update_species_genomes.py
python plot_metrics.py --summary
```

## Automation

`.github/workflows/update-data.yml` runs on the 2nd of each month, runs all
update scripts, regenerates plots, and commits. Optional secret: `NCBI_API_KEY`.

## Caveats

- PubMed metrics use the Entrez date (when the record was indexed), not the
  publication date, because year-only publication dates pile into January.
- The current month is always partial and is refetched on the next run.
- FDA gene therapies: 5 early products have approval dates hard-coded in the
  script (FDA archives old letters behind a JS wall). Provenance caches in
  `data/fda_*_products.csv` / `data/fda_*_rows.csv`.
- ClinVar counts are by record creation date, so deleted/merged variants are
  not counted retrospectively (early years read lower than contemporaneous
  ClinVar reports).
