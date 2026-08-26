#!/usr/bin/env python3
"""Cumulative count of eukaryotic species with at least one chromosome-level
genome assembly, from GoaT (Genomes on a Tree, Sanger) API v2.

Each month's value is the number of species matching the metric's query with
assembly_date on or before the last day of that month, so one run backfills
the full history. GoaT requires the query to be fully percent-encoded."""
from urllib.parse import quote

from common import get, load_config, month_bounds, update_metric

API = "https://goat.genomehubs.org/api/v2/count"
DEFAULT_QUERY = "tax_tree(2759) AND assembly_level=chromosome"


def make_counter(query: str):
    def count(ym: str) -> int:
        _, last = month_bounds(ym)
        q = f"{query} AND assembly_date<={last}"
        url = f"{API}?query={quote(q, safe='')}&result=taxon&taxonomy=ncbi"
        data = get(url, {}, min_interval=0.5)
        if not data.get("status", {}).get("success", False):
            raise RuntimeError(f"GoaT error: {data}")
        return int(data["count"])
    return count


def main():
    cfg = load_config()
    for name, m in cfg["metrics"].items():
        if m["source"] == "goat":
            update_metric(name, "goat_api_v2", make_counter(m.get("query", DEFAULT_QUERY)), cfg)


if __name__ == "__main__":
    main()
