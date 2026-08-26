#!/usr/bin/env python3
"""Cumulative count of FDA-approved cellular and gene therapy products (CBER
list), by month of first approval. Cord-blood products (HPC, Cord Blood) are
excluded so this counts gene and cell therapies proper.

Product approval dates come from each product's FDA page (earliest
"<Month D, YYYY> Approval Letter"). Pages for older products move their early
letters to an archive-it mirror behind a JS challenge, so those dates are
hard-coded in KNOWN_DATES. Dates are cached in
data/fda_gene_therapies_products.csv so only new products are fetched; edit
that file to correct a date by hand."""
import csv
import html
import re
import sys
import time
from datetime import datetime

import requests

from common import DATA_DIR, current_month, log, months, read_csv, write_csv

METRIC = "fda_gene_therapies"
SOURCE_TAG = "fda_cber_cgt_list"
LIST_URL = ("https://www.fda.gov/vaccines-blood-biologics/cellular-gene-therapy-products/"
            "approved-cellular-and-gene-therapy-products")
CACHE = DATA_DIR / f"{METRIC}_products.csv"
CACHE_FIELDS = ["product", "approval_date", "url", "excluded"]
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120.0 Safari/537.36")
MONTH_RE = (r"(January|February|March|April|May|June|July|August|September|"
            r"October|November|December) \d{1,2}, \d{4}")

# Original approval dates for products whose FDA page only links archived
# (un-scrapable) letters. Key = trade name (first word of the table entry).
KNOWN_DATES = {
    "PROVENGE": "2010-04-29",
    "LAVIV": "2011-06-21",
    "GINTUIT": "2012-03-09",
    "IMLYGIC": "2015-10-27",
    "MACI": "2016-12-13",
}
ARCHIVED_MARK = "older than three years"

_s = requests.Session()
_s.headers["User-Agent"] = UA


def fetch(url: str) -> str:
    time.sleep(0.5)
    r = _s.get(url, timeout=60)
    r.raise_for_status()
    return r.text


def strip_tags(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s)))


def list_products() -> list[tuple[str, str]]:
    """(product name, absolute url) for every row of the FDA table."""
    page = fetch(LIST_URL)
    out = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        m = re.search(r'<a href="([^"]+)"[^>]*>(.*?)</a>', row, re.S)
        if not m:
            continue
        href, name = m.group(1), strip_tags(m.group(2)).strip()
        if href.startswith("/"):
            href = "https://www.fda.gov" + href
        out.append((name, href))
    return out


def is_cord_blood(name: str) -> bool:
    return "cord blood" in name.lower()


def trade_name(product: str) -> str:
    return re.split(r"[\s(,]", product.strip())[0].rstrip("\u2122\u00ae").upper()


def approval_date(name: str, url: str) -> str | None:
    """Earliest 'Month D, YYYY Approval Letter' on the product page -> YYYY-MM-DD."""
    if trade_name(name) in KNOWN_DATES:
        return KNOWN_DATES[trade_name(name)]
    text = strip_tags(fetch(url))
    if ARCHIVED_MARK in text:
        log.warning("%s: %s has archived letters; add it to KNOWN_DATES", METRIC, name)
        return None
    dates = []
    for m in re.finditer(MONTH_RE + r"\s+Approval Letter", text):
        dates.append(datetime.strptime(m.group(0).rsplit(" Approval", 1)[0], "%B %d, %Y"))
    if not dates:
        # some pages say "Approval Date: Month D, YYYY" or "Approved: ..."
        m = re.search(r"Approv(?:al Date|ed)[:\s]+(" + MONTH_RE + ")", text)
        if m:
            dates.append(datetime.strptime(m.group(1), "%B %d, %Y"))
    return min(dates).strftime("%Y-%m-%d") if dates else None


def read_cache() -> dict[str, dict]:
    if not CACHE.exists():
        return {}
    with open(CACHE, newline="") as f:
        return {r["product"]: r for r in csv.DictReader(f)}


def write_cache(rows: dict[str, dict]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with open(CACHE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CACHE_FIELDS)
        w.writeheader()
        for name in sorted(rows):
            w.writerow({k: rows[name].get(k, "") for k in CACHE_FIELDS})


def main() -> int:
    try:
        products = list_products()
    except Exception as e:
        log.warning("%s: could not fetch FDA list (%s); keeping existing data", METRIC, e)
        return 0
    if len(products) < 10:
        log.warning("%s: only %d products parsed; page layout changed? keeping data",
                    METRIC, len(products))
        return 0

    cache = read_cache()
    for name, url in products:
        row = cache.setdefault(name, {"product": name, "url": url, "approval_date": "",
                                      "excluded": ""})
        row["url"] = url
        if is_cord_blood(name):
            row["excluded"] = "cord_blood"
            continue
        if row.get("approval_date"):
            continue
        try:
            d = approval_date(name, url)
        except Exception as e:
            log.warning("%s: %s fetch failed: %s", METRIC, name, e)
            continue
        if d:
            row["approval_date"] = d
            log.info("%s: %s approved %s", METRIC, name, d)
        else:
            log.warning("%s: no approval date found for %s (%s)", METRIC, name, url)
    write_cache(cache)

    listed = {n for n, _ in products}
    dated = [r for r in cache.values() if r["product"] in listed
             and not r.get("excluded") and r.get("approval_date")]
    excluded = sorted(r["product"] for r in cache.values() if r.get("excluded"))
    log.info("%s: %d products counted, %d excluded (%s)", METRIC, len(dated),
             len(excluded), "; ".join(excluded))
    if not dated:
        log.warning("%s: no dated products; keeping existing data", METRIC)
        return 0

    by_month: dict[str, list[str]] = {}
    for r in dated:
        by_month.setdefault(r["approval_date"][:7], []).append(
            r["product"].split(" (")[0])

    rows = read_csv(METRIC)
    start = min(min(by_month), min(rows)) if rows else min(by_month)
    total = 0
    for ym in months(start, current_month()):
        new = sorted(by_month.get(ym, []))
        total += len(new)
        old = rows.get(ym, {})
        # never let a fetch hiccup lower a previously recorded count
        value = max(total, int(old["value"])) if old.get("value") else total
        rows[ym] = {"date": ym, "value": value, "source": SOURCE_TAG,
                    "notes": "; ".join(new) if new else old.get("notes", "")}
    write_csv(METRIC, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
