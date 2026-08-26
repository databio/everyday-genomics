"""Shared helpers: config, CSV I/O, month iteration, rate-limited HTTP."""
from datetime import date
from pathlib import Path
import csv
import json
import logging
import os
import time

import requests

ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT / "config.json"
DATA_DIR = ROOT / "data"
FIELDS = ["date", "value", "source", "notes"]

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("everyday-genomics")

_session = requests.Session()
_session.headers["User-Agent"] = "everyday-genomics/0.1 (github.com/databio/everyday-genomics)"


def load_config() -> dict:
    with open(CONFIG_FILE) as f:
        return json.load(f)


def get(url: str, params: dict, min_interval: float = 0.4, retries: int = 4) -> dict:
    """GET JSON with a polite delay and simple retry on 429/5xx."""
    for attempt in range(retries):
        time.sleep(min_interval)
        r = _session.get(url, params=params, timeout=60)
        if r.status_code == 429 or r.status_code >= 500:
            wait = 2 ** attempt
            log.warning("HTTP %s from %s, retrying in %ss", r.status_code, url, wait)
            time.sleep(wait)
            continue
        r.raise_for_status()
        data = r.json()
        if "error" in data:  # NCBI returns 200 with an error body on rate limit
            log.warning("API error: %s, retrying", data["error"])
            time.sleep(2 ** attempt)
            continue
        return data
    raise RuntimeError(f"Giving up on {url}")


def months(start: str, end: str) -> list[str]:
    """All YYYY-MM strings from start through end inclusive."""
    y, m = (int(x) for x in start.split("-"))
    ey, em = (int(x) for x in end.split("-"))
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def month_bounds(ym: str) -> tuple[str, str]:
    """(first_day, last_day) as YYYY-MM-DD for a YYYY-MM month."""
    y, m = (int(x) for x in ym.split("-"))
    first = date(y, m, 1)
    last = date(y + (m == 12), (m % 12) + 1, 1)
    last = date.fromordinal(last.toordinal() - 1)
    return first.isoformat(), last.isoformat()


def current_month() -> str:
    return date.today().strftime("%Y-%m")


def shift_month(ym: str, delta: int) -> str:
    y, m = (int(x) for x in ym.split("-"))
    idx = y * 12 + (m - 1) + delta
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


def read_csv(name: str) -> dict[str, dict]:
    path = DATA_DIR / f"{name}.csv"
    if not path.exists():
        return {}
    with open(path, newline="") as f:
        return {row["date"]: row for row in csv.DictReader(f)}


def write_csv(name: str, rows: dict[str, dict]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / f"{name}.csv"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for ym in sorted(rows):
            row = {k: rows[ym].get(k, "") for k in FIELDS}
            w.writerow(row)
    log.info("Wrote %s (%d rows)", path.relative_to(ROOT), len(rows))


def months_to_fetch(existing: dict, cfg: dict) -> list[str]:
    """Months missing from the CSV, plus the trailing `refresh_months` window
    (recent months keep growing as records are indexed/posted)."""
    end = current_month()
    refresh = set(months(shift_month(end, -cfg["refresh_months"]), end))
    wanted = months(cfg["backfill_start"], end)
    return [m for m in wanted if m not in existing or m in refresh]


def update_metric(name: str, source_tag: str, count_fn, cfg: dict) -> None:
    """Generic update loop: fetch missing/refresh months via count_fn(ym) -> int."""
    rows = read_csv(name)
    todo = months_to_fetch(rows, cfg)
    log.info("%s: fetching %d months", name, len(todo))
    for ym in todo:
        try:
            value = count_fn(ym)
        except Exception as e:  # keep going; leave the month for next run
            log.warning("%s %s failed: %s", name, ym, e)
            continue
        old = rows.get(ym, {})
        rows[ym] = {"date": ym, "value": value, "source": source_tag,
                    "notes": old.get("notes", "")}
    write_csv(name, rows)
