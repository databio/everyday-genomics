#!/usr/bin/env python3
"""Monthly count of newly registered studies on ClinicalTrials.gov matching a
query (API v2, filtered by StudyFirstPostDate)."""
from common import get, load_config, month_bounds, update_metric

API = "https://clinicaltrials.gov/api/v2/studies"


def make_counter(query: str):
    def count(ym: str) -> int:
        first, last = month_bounds(ym)
        params = {
            "query.term": query,
            "filter.advanced": f"AREA[StudyFirstPostDate]RANGE[{first},{last}]",
            "countTotal": "true", "pageSize": 1, "fields": "NCTId",
        }
        return int(get(API, params, min_interval=0.3)["totalCount"])
    return count


def main():
    cfg = load_config()
    for name, m in cfg["metrics"].items():
        if m["source"] == "clinicaltrials":
            update_metric(name, "clinicaltrials_gov_v2", make_counter(m["query"]), cfg)


if __name__ == "__main__":
    main()
