#!/usr/bin/env python3
"""Cumulative count of FDA-cleared/approved companion diagnostic indications.

Scrapes the FDA list of companion diagnostic devices (two HTML tables; one row
per device x indication/drug) and takes the first approval date in each row's
PMA/510(k) column. One fetch gives the full history, so every run rebuilds the
cumulative monthly series and merges it over the existing CSV (existing months
are kept if the fetch fails). Parsed rows are saved to
data/<metric>_rows.csv for provenance."""
from io import StringIO
import csv
import re

import pandas as pd
import requests

from common import DATA_DIR, current_month, load_config, months, read_csv, write_csv, log

URL = ("https://www.fda.gov/medical-devices/in-vitro-diagnostics/"
       "list-cleared-or-approved-companion-diagnostic-devices-in-vitro-and-imaging-tools")
SOURCE_TAG = "fda_companion_diagnostics_list"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120.0 Safari/537.36")
DATE_RE = re.compile(r"(\d\d)/\s*(\d\d)/\s*(\d{4})")


def fetch_tables() -> list[pd.DataFrame]:
    r = requests.get(URL, headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    return pd.read_html(StringIO(r.text))


def first_date(text: str) -> str | None:
    """YYYY-MM-DD of the first date in a PMA/510(k) cell (original approval;
    later supplements are listed after it)."""
    m = DATE_RE.search(str(text))
    if not m:
        return None
    mo, d, y = m.groups()
    if int(y) < 1000:  # e.g. "08/22/0218" typo on the FDA page
        log.warning("Suspicious year %r in %r; assuming 20%s", y, text, y[2:])
        y = "20" + y[2:]
    return f"{y}-{mo}-{d}"


def parse_rows(tables: list[pd.DataFrame]) -> list[dict]:
    rows = []
    for t in tables:
        cols = list(t.columns)
        date_col = next(c for c in cols if "Date" in str(c))
        ind_col = next(c for c in cols if "Indication" in str(c))
        drug_col = next((c for c in cols if "Drug" in str(c)), None)
        for _, r in t.iterrows():
            d = first_date(r[date_col])
            if not d:
                log.warning("No date in row: %r", r[date_col])
                continue
            rows.append({
                "device": str(r[cols[0]]).strip(),
                "indication": str(r[ind_col]).strip(),
                "drug": str(r[drug_col]).strip() if drug_col else "",
                "approval": str(r[date_col]).strip(),
                "approval_date": d,
            })
    # distinct (device, indication, drug) rows
    seen, out = set(), []
    for r in rows:
        key = (r["device"], r["indication"], r["drug"])
        if key not in seen:
            seen.add(key)
            out.append(r)
    return sorted(out, key=lambda r: r["approval_date"])


def write_rows(name: str, rows: list[dict]) -> None:
    path = DATA_DIR / f"{name}_rows.csv"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    log.info("Wrote %s (%d rows)", path.name, len(rows))


def short_name(device: str) -> str:
    return re.sub(r"\s*\(.*$", "", device).strip()


def main():
    cfg = load_config()
    for name, m in cfg["metrics"].items():
        if m["source"] != "fda_companion_diagnostics":
            continue
        existing = read_csv(name)
        try:
            rows = parse_rows(fetch_tables())
            if len(rows) < 100:
                raise RuntimeError(f"only {len(rows)} rows parsed, page layout changed?")
        except Exception as e:
            log.warning("%s: fetch failed (%s); keeping existing data", name, e)
            write_csv(name, existing)
            continue
        write_rows(name, rows)
        by_month: dict[str, list[str]] = {}
        for r in rows:
            by_month.setdefault(r["approval_date"][:7], []).append(short_name(r["device"]))
        total = 0
        for ym in months(min(by_month), current_month()):
            names = by_month.get(ym, [])
            total += len(names)
            notes = "; ".join(dict.fromkeys(names)) if names else ""
            existing[ym] = {"date": ym, "value": total, "source": SOURCE_TAG, "notes": notes}
        write_csv(name, existing)


if __name__ == "__main__":
    main()
