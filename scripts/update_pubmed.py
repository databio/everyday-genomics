#!/usr/bin/env python3
"""Monthly PubMed publication counts for each `pubmed` metric in config.json.

Uses NCBI E-utilities esearch with rettype=count and an [edat] (Entrez date, when
the record was added; avoids the January pile-up of year-only [dp] dates)
range. Set NCBI_API_KEY to raise the rate limit from 3 to 10 req/s.
"""
import os
from common import get, load_config, month_bounds, update_metric

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"


def make_counter(query: str, api_key: str | None):
    def count(ym: str) -> int:
        first, last = (d.replace("-", "/") for d in month_bounds(ym))
        term = f'({query}) AND ("{first}"[edat] : "{last}"[edat])'
        params = {"db": "pubmed", "term": term, "rettype": "count", "retmode": "json"}
        if api_key:
            params["api_key"] = api_key
        return int(get(ESEARCH, params, min_interval=0.15 if api_key else 0.4)
                   ["esearchresult"]["count"])
    return count


def main():
    cfg = load_config()
    api_key = os.environ.get(cfg["ncbi_api_key_env"])
    for name, m in cfg["metrics"].items():
        if m["source"] != "pubmed":
            continue
        update_metric(name, "pubmed_esearch", make_counter(m["query"], api_key), cfg)


if __name__ == "__main__":
    main()
