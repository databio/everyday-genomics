# Candidate future sources

Feasibility survey (Aug 2026) for metrics not yet in v1. "Easy" = fetchable
by a monthly cron script.

| Metric | Feasibility | Source | Approach |
|---|---|---|---|
| FDA-approved cellular & gene therapy products | Easy | https://www.fda.gov/vaccines-blood-biologics/cellular-gene-therapy-products/approved-cellular-and-gene-therapy-products (one HTML table, ~53 rows; needs browser User-Agent) | `pandas.read_html`, diff product list against stored list to log new approvals by month; approval dates on per-product pages |
| FDA companion diagnostics | Easy | https://www.fda.gov/medical-devices/in-vitro-diagnostics/list-cleared-or-approved-companion-diagnostic-devices-in-vitro-and-imaging-tools (2 HTML tables, ~234 rows, approval date in last column) | `read_html`, regex `\((\d\d/\d\d/\d{4})\)` for dates -> full cumulative series from one fetch |
| ClinVar variants | Easy | esearch `db=clinvar&term=all[filter]` (current count ~4.56M); monthly archived releases at https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/ for backfill | one esearch call per month, append; backfill from archived release headers |
| Eukaryotic species with reference genomes | Easy | GoaT API `https://goat.genomehubs.org/api/v2/count?query=tax_tree(2759) AND assembly_level=chromosome&result=taxon&taxonomy=ncbi` (~9,205 species); fully percent-encode the query | monthly count; for history filter on `assembly_date` |
| Google Trends ("DNA test", "CRISPR") | Not machine-readable (no official API; relative values) | `trendspy` (pytrends is archived/broken); values relative within window | refetch the full 5-y window each run and overwrite; alternative: Wikipedia pageviews API (official, stable) |
| Approved GM crop events | Medium | ISAAA https://www.isaaa.org/gmapprovaldatabase/eventslist/default.asp ("657 Events" header); USDA APHIS petitions table for US-only | regex the events count monthly; time series needs per-event scraping |
| Cumulative DTC genetic tests sold | Not machine-readable | Company press releases / 10-Ks only (AncestryDNA >30M; 23andMe ~14M FY2023, stale post-bankruptcy) | quarterly `claude-code-action` search + PR for human review; store as step function with source URL |
