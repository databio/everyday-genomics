#!/usr/bin/env python3
"""Cumulative number of ClinVar variant records (VCV accessions) as of the end
of each month, for each `clinvar` metric in config.json.

Uses E-utilities esearch on db=clinvar with `all[filter]` (excludes
retired/replaced records) restricted to records whose creation date [CDAT] is
on or before the last day of the month, so one cheap count call per month
gives the full history. This is retrospective: variants later deleted or
merged are not counted, so past months are slightly lower than the live count
was at the time. The archived monthly XML releases carry no record count in
their header and the release-notes PDFs only report submitted (SCV) records,
so they are not used. Set NCBI_API_KEY to raise the rate limit to 10 req/s.
"""
import os
from common import get, load_config, month_bounds, update_metric

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
DEFAULT_METRICS = {"clinvar_variants": {}}


def make_counter(query: str, api_key: str | None):
    def count(ym: str) -> int:
        _, last = month_bounds(ym)
        term = f'all[filter] AND ("1900/01/01"[cdat] : "{last.replace("-", "/")}"[cdat])'
        if query:
            term = f"({query}) AND {term}"
        params = {"db": "clinvar", "term": term, "rettype": "count", "retmode": "json"}
        if api_key:
            params["api_key"] = api_key
        return int(get(ESEARCH, params, min_interval=0.15 if api_key else 0.4)
                   ["esearchresult"]["count"])
    return count


def main():
    cfg = load_config()
    api_key = os.environ.get(cfg.get("ncbi_api_key_env", "NCBI_API_KEY"))
    metrics = {n: m for n, m in cfg["metrics"].items() if m.get("source") == "clinvar"}
    for name, m in (metrics or DEFAULT_METRICS).items():
        update_metric(name, "clinvar_esearch_cdat", make_counter(m.get("query", ""), api_key), cfg)


if __name__ == "__main__":
    main()
