#!/usr/bin/env python3
"""Monthly count of experiments submitted to NCBI SRA (esearch db=sra, [PDAT])."""
import os
from common import get, load_config, month_bounds, update_metric

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"


def make_counter(api_key: str | None):
    def count(ym: str) -> int:
        first, last = (d.replace("-", "/") for d in month_bounds(ym))
        params = {"db": "sra", "term": f'"{first}"[PDAT] : "{last}"[PDAT]',
                  "rettype": "count", "retmode": "json"}
        if api_key:
            params["api_key"] = api_key
        return int(get(ESEARCH, params, min_interval=0.15 if api_key else 0.4)
                   ["esearchresult"]["count"])
    return count


def main():
    cfg = load_config()
    api_key = os.environ.get(cfg["ncbi_api_key_env"])
    for name, m in cfg["metrics"].items():
        if m["source"] == "sra":
            update_metric(name, "ncbi_sra_esearch", make_counter(api_key), cfg)


if __name__ == "__main__":
    main()
