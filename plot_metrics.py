#!/usr/bin/env python3
"""Generate PNG + SVG plots for every metric in data/, in light and dark themes.

  python plot_metrics.py            # all metrics -> plots/{light,dark}/<name>.{png,svg}
  python plot_metrics.py --summary  # also plots/{light,dark}/summary.{png,svg}

Each plot shows monthly values (bars, faint) and a 12-month rolling mean (line),
plus a cumulative-total panel. Reveal.js slides use the dark versions.
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent
CFG = json.load(open(ROOT / "config.json"))
DATA = ROOT / "data"
PLOTS = ROOT / "plots"

THEMES = {
    "light": {"bg": "white", "fg": "#222222", "bar": "#b8c4d6", "line": "#1f4e8c"},
    "dark":  {"bg": "none",  "fg": "#eeeeee", "bar": "#4a5568", "line": "#8ab4f8"},
}


def load(name: str) -> pd.DataFrame:
    """Load a metric. kind="monthly" (default): value is a per-month count and
    we derive rolling mean + cumulative. kind="cumulative": value is already a
    running total; the monthly panel shows the month-over-month increment."""
    meta = CFG["metrics"][name]
    df = pd.read_csv(DATA / f"{name}.csv", parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    if meta.get("kind") == "cumulative":
        df["cumulative"] = df["value"]
        df["value"] = df["cumulative"].diff().fillna(df["cumulative"]).clip(lower=0)
    else:
        # Drop the current (partial) month so the tail doesn't fake a decline.
        df = df[df["date"] < pd.Timestamp.today().to_period("M").to_timestamp()]
        df["cumulative"] = df["value"].cumsum()
    df["rolling"] = df["value"].rolling(12, min_periods=1).mean()
    return df


def style(ax, t):
    ax.set_facecolor(t["bg"] if t["bg"] != "none" else (0, 0, 0, 0))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(t["fg"])
    ax.tick_params(colors=t["fg"], labelsize=9)
    ax.yaxis.label.set_color(t["fg"])
    ax.title.set_color(t["fg"])
    ax.grid(axis="y", alpha=0.15, color=t["fg"])


def draw(ax, df, meta, t, cumulative=False):
    if cumulative:
        ax.plot(df["date"], df["cumulative"], color=t["line"], lw=2)
        ax.fill_between(df["date"], df["cumulative"], color=t["line"], alpha=0.15)
        ax.set_ylabel("cumulative")
    else:
        annual = len(df) > 1 and df["date"].diff().dt.days.median() >= 360
        if annual:  # sparse hand-curated series: one bar per year, no rolling mean
            ax.bar(df["date"], df["value"], width=300, color=t["bar"], lw=0, align="edge")
            ax.set_ylabel("new / year")
        else:
            ax.bar(df["date"], df["value"], width=25, color=t["bar"], lw=0)
            ax.plot(df["date"], df["rolling"], color=t["line"], lw=2, label="12-mo mean")
            ax.set_ylabel(meta["unit"] if meta.get("kind") != "cumulative" else "new / month")
    ax.set_xlim(df["date"].min(), df["date"].max())
    ax.set_ylim(bottom=0)
    style(ax, t)


def plot_metric(name, meta, theme):
    t = THEMES[theme]
    df = load(name)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.2))
    fig.patch.set_alpha(0 if t["bg"] == "none" else 1)
    if t["bg"] != "none":
        fig.patch.set_facecolor(t["bg"])
    draw(axes[0], df, meta, t)
    draw(axes[1], df, meta, t, cumulative=True)
    axes[0].set_title(meta["title"], loc="left", fontsize=11)
    axes[1].set_title("Cumulative", loc="left", fontsize=11)
    fig.tight_layout()
    save(fig, theme, name)


def plot_summary(theme):
    t = THEMES[theme]
    names = list(CFG["metrics"])
    ncol = 2
    nrow = -(-len(names) // ncol)
    fig, axes = plt.subplots(nrow, ncol, figsize=(11, 2.8 * nrow))
    fig.patch.set_alpha(0 if t["bg"] == "none" else 1)
    if t["bg"] != "none":
        fig.patch.set_facecolor(t["bg"])
    for ax, name in zip(axes.flat, names):
        meta = CFG["metrics"][name]
        draw(ax, load(name), meta, t, cumulative=True)
        ax.set_title(meta["title"], loc="left", fontsize=10)
    for ax in list(axes.flat)[len(names):]:
        ax.axis("off")
    fig.tight_layout()
    save(fig, theme, "summary")


def save(fig, theme, stem):
    out = PLOTS / theme
    out.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(out / f"{stem}.{ext}", dpi=150, transparent=(theme == "dark"))
    plt.close(fig)
    print(f"plots/{theme}/{stem}.{{png,svg}}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--summary", action="store_true", help="also build summary figure")
    p.add_argument("metrics", nargs="*", help="subset of metric names")
    a = p.parse_args()
    names = a.metrics or list(CFG["metrics"])
    for theme in THEMES:
        for n in names:
            if (DATA / f"{n}.csv").exists():
                plot_metric(n, CFG["metrics"][n], theme)
        if a.summary:
            plot_summary(theme)


if __name__ == "__main__":
    main()
