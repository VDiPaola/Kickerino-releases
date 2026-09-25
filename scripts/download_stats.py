"""Record cumulative release download counts and render them as SVG charts.

Usage: python download_stats.py [output_dir]
"""

import csv
import json
import math
import os
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

REPO = os.environ.get("GITHUB_REPOSITORY", "VDiPaola/Kickerino-releases")
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/stats"
COUNTS = ["win_setup", "win_portable", "linux", "updates_win", "updates_linux"]
FIELDS = ["date", "latest_tag", *COUNTS]

LABELS = {
    "win_setup": "Windows Setup",
    "win_portable": "Windows Portable",
    "linux": "Linux AppImage",
    "updates_win": "Windows updates",
    "updates_linux": "Linux updates",
}

CHARTS = {
    "installs": {
        "title": "Installs",
        "subtitle": "Cumulative installer downloads across all versions",
        "series": [("win_setup", 0), ("win_portable", 1), ("linux", 2)],
    },
    "updates": {
        "title": "Updates",
        "subtitle": "Cumulative update package downloads across all versions",
        "series": [("updates_win", 0), ("updates_linux", 2)],
    },
}

THEMES = {
    "light": {
        "surface": "#fcfcfb",
        "border": "rgba(11,11,11,0.10)",
        "primary": "#0b0b0b",
        "secondary": "#52514e",
        "muted": "#898781",
        "grid": "#e1e0d9",
        "axis": "#c3c2b7",
        "series": ["#2a78d6", "#eb6834", "#1baf7a"],
    },
    "dark": {
        "surface": "#1a1a19",
        "border": "rgba(255,255,255,0.10)",
        "primary": "#ffffff",
        "secondary": "#c3c2b7",
        "muted": "#898781",
        "grid": "#2c2c2a",
        "axis": "#383835",
        "series": ["#3987e5", "#d95926", "#199e70"],
    },
}

FONT = 'system-ui, -apple-system, &quot;Segoe UI&quot;, Helvetica, Arial, sans-serif'
WIDTH, HEIGHT = 760, 340
LEFT, RIGHT, TOP, BOTTOM = 48, 150, 96, 40
LABEL_GAP = 16


def classify(asset_name):
    if asset_name.endswith("-Setup.exe"):
        return "win_setup"
    if asset_name.endswith("-Portable.zip"):
        return "win_portable"
    if asset_name.endswith(".AppImage"):
        return "linux"
    if asset_name.endswith(".nupkg"):
        return "updates_linux" if "-linux-" in asset_name else "updates_win"
    return None


def fetch_releases():
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "kickerino-download-stats"}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"

    releases, page = [], 1
    while True:
        url = f"https://api.github.com/repos/{REPO}/releases?per_page=100&page={page}"
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as response:
            batch = json.load(response)
        releases += [r for r in batch if not r["draft"] and r.get("published_at")]
        if len(batch) < 100:
            return sorted(releases, key=lambda r: r["published_at"])
        page += 1


def release_counts(release):
    counts = dict.fromkeys(COUNTS, 0)
    for asset in release["assets"]:
        if key := classify(asset["name"]):
            counts[key] += asset["download_count"]
    return counts


def backfill(releases):
    """Estimate history by counting each release's downloads on its publish date."""
    rows, totals = {}, dict.fromkeys(COUNTS, 0)
    for release in releases:
        for key, value in release_counts(release).items():
            totals[key] += value
        day = release["published_at"][:10]
        rows[day] = {"date": day, "latest_tag": release["tag_name"], **totals}
    return list(rows.values())


def snapshot(releases, day):
    totals = dict.fromkeys(COUNTS, 0)
    for release in releases:
        for key, value in release_counts(release).items():
            totals[key] += value
    return {"date": day, "latest_tag": releases[-1]["tag_name"], **totals}


def record(rows, row):
    if rows and rows[-1]["date"] == row["date"]:
        rows[-1] = row
    elif not rows or any(rows[-1][key] != row[key] for key in FIELDS[1:]):
        rows.append(row)


def read_rows(path):
    if not path.exists():
        return []
    with path.open(newline="") as file:
        return [{**row, **{key: int(row[key]) for key in COUNTS}} for row in csv.DictReader(file)]


def write_rows(path, rows):
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def nice_step(maximum, target_ticks=4):
    raw = max(maximum, 1) / target_ticks
    magnitude = 10 ** math.floor(math.log10(raw))
    for multiple in (1, 2, 5, 10):
        if raw <= multiple * magnitude:
            return max(1, int(multiple * magnitude))


def format_day(day, long_span):
    return day.strftime("%b %Y") if long_span else f"{day:%b} {day.day}"


def spread_labels(positions, top, bottom):
    """Push end labels apart vertically so they never overlap."""
    order = sorted(range(len(positions)), key=lambda i: positions[i])
    placed = list(positions)
    for previous, current in zip(order, order[1:]):
        placed[current] = max(placed[current], placed[previous] + LABEL_GAP)
    overflow = placed[order[-1]] - bottom
    if overflow > 0:
        for i in order:
            placed[i] = max(top, placed[i] - overflow)
    return placed


def render_chart(rows, chart, theme):
    t = THEMES[theme]
    series = chart["series"]
    days = [date.fromisoformat(row["date"]) for row in rows]
    span = max(1, (days[-1] - days[0]).days)
    first = date.fromordinal(days[-1].toordinal() - span)
    x0, x1, y0, y1 = LEFT, WIDTH - RIGHT, TOP, HEIGHT - BOTTOM

    peak = max(row[key] for row in rows for key, _ in series)
    step = nice_step(peak)
    y_max = max(step, math.ceil(peak / step) * step)

    def x(day):
        return x0 + (day - first).days / span * (x1 - x0)

    def y(value):
        return y1 - value / y_max * (y1 - y0)

    latest = rows[-1]
    total = sum(latest[key] for key, _ in series)
    summary = ", ".join(f"{LABELS[key]} {latest[key]:,}" for key, _ in series)
    description = (
        f"{chart['subtitle']} from {rows[0]['date']} to {latest['date']}. "
        f"Total {total:,}: {summary}."
    )

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc" font-family="{FONT}">',
        f'<title id="title">{escape(chart["title"])}</title>',
        f'<desc id="desc">{escape(description)}</desc>',
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="8" '
        f'fill="{t["surface"]}" stroke="{t["border"]}"/>',
        f'<text x="{x0}" y="34" font-size="16" font-weight="600" fill="{t["primary"]}">'
        f'{escape(chart["title"])}: {total:,}</text>',
        f'<text x="{x0}" y="56" font-size="13" fill="{t["secondary"]}">{escape(chart["subtitle"])}</text>',
    ]

    legend_x = x0
    for key, slot in series:
        out.append(
            f'<line x1="{legend_x}" y1="76" x2="{legend_x + 16}" y2="76" stroke="{t["series"][slot]}" '
            f'stroke-width="2" stroke-linecap="round"/>'
        )
        out.append(f'<text x="{legend_x + 22}" y="80" font-size="12" fill="{t["secondary"]}">{LABELS[key]}</text>')
        legend_x += 22 + len(LABELS[key]) * 6.2 + 18
    out.append(f'<line x1="{legend_x + 8}" y1="70" x2="{legend_x + 8}" y2="82" stroke="{t["muted"]}"/>')
    out.append(f'<text x="{legend_x + 16}" y="80" font-size="12" fill="{t["secondary"]}">Release</text>')

    for tick in range(0, y_max + 1, step):
        ty = y(tick)
        color = t["axis"] if tick == 0 else t["grid"]
        out.append(f'<line x1="{x0}" y1="{ty:.1f}" x2="{x1}" y2="{ty:.1f}" stroke="{color}"/>')
        out.append(
            f'<text x="{x0 - 8}" y="{ty + 4:.1f}" font-size="11" text-anchor="end" fill="{t["muted"]}" '
            f'style="font-variant-numeric: tabular-nums">{tick:,}</text>'
        )

    tick_count = min(5, span + 1)
    long_span = span > 180
    for i in range(tick_count):
        day = date.fromordinal(first.toordinal() + round(i * span / max(1, tick_count - 1)))
        anchor = "start" if i == 0 else "end" if i == tick_count - 1 else "middle"
        out.append(
            f'<text x="{x(day):.1f}" y="{y1 + 24}" font-size="11" text-anchor="{anchor}" '
            f'fill="{t["muted"]}">{format_day(day, long_span)}</text>'
        )

    previous_tag = None
    for row, day in zip(rows, days):
        if row["latest_tag"] != previous_tag:
            rx = x(day)
            out.append(
                f'<line x1="{rx:.1f}" y1="{y1 + 2}" x2="{rx:.1f}" y2="{y1 + 8}" stroke="{t["muted"]}">'
                f'<title>{escape(row["latest_tag"])} ({row["date"]})</title></line>'
            )
        previous_tag = row["latest_tag"]

    for key, slot in series:
        points = " ".join(f"{x(day):.1f},{y(row[key]):.1f}" for row, day in zip(rows, days))
        out.append(
            f'<polyline points="{points}" fill="none" stroke="{t["series"][slot]}" stroke-width="2" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
        )

    end_x = x(days[-1])
    end_ys = [y(latest[key]) for key, _ in series]
    label_ys = spread_labels(end_ys, y0 + 4, y1)
    for (key, slot), end_y, label_y in zip(series, end_ys, label_ys):
        out.append(
            f'<circle cx="{end_x:.1f}" cy="{end_y:.1f}" r="4" fill="{t["series"][slot]}" '
            f'stroke="{t["surface"]}" stroke-width="2"><title>{LABELS[key]}: {latest[key]:,}</title></circle>'
        )
        if abs(label_y - end_y) > 1:
            out.append(
                f'<polyline points="{end_x + 6:.1f},{end_y:.1f} {end_x + 10:.1f},{label_y:.1f} '
                f'{end_x + 14:.1f},{label_y:.1f}" fill="none" stroke="{t["muted"]}"/>'
            )
        out.append(
            f'<text x="{end_x + 16:.1f}" y="{label_y + 4:.1f}" font-size="12" fill="{t["secondary"]}">'
            f'<tspan font-weight="600" fill="{t["primary"]}">{latest[key]:,}</tspan> {LABELS[key]}</text>'
        )

    out.append("</svg>")
    return "\n".join(out) + "\n"


def picture(name, alt):
    return (
        "<picture>\n"
        f'  <source media="(prefers-color-scheme: dark)" srcset="{RAW_BASE}/{name}-dark.svg">\n'
        f'  <img alt="{alt}" src="{RAW_BASE}/{name}-light.svg">\n'
        "</picture>"
    )


def render_readme(rows):
    latest = rows[-1]
    installs = sum(latest[key] for key, _ in CHARTS["installs"]["series"])
    updates = sum(latest[key] for key, _ in CHARTS["updates"]["series"])
    table = "\n".join(f"| {LABELS[key]} | {latest[key]:,} |" for key in COUNTS)
    return f"""# Kickerino download stats

Cumulative downloads of Kickerino release files. A [GitHub Actions workflow](https://github.com/{REPO}/actions/workflows/download-stats.yml) updates this branch daily.

Back to the [main README](https://github.com/{REPO}).

## Installs

{picture("installs", f"Line chart of cumulative installer downloads over time. Total: {installs:,}.")}

## Updates

{picture("updates", f"Line chart of cumulative update package downloads over time. Total: {updates:,}.")}

## Current totals

As of {latest["date"]} (latest release: {latest["latest_tag"]}).

| Release file | Downloads |
|---|---|
{table}

## How the data is collected

- Totals include every release, not only the latest one.
- Installs count `Kickerino-win-Setup.exe`, `Kickerino-win-Portable.zip` and `Kickerino.AppImage`.
- Updates count the `.nupkg` packages downloaded by the auto-updater.
- Update checks (`releases.*.json` and `RELEASES`) are not counted.
- A row is added to [`downloads.csv`](downloads.csv) only when a total changes.
- History before daily tracking started is estimated by counting each release's downloads on its publish date.
"""


def main():
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "stats")
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "downloads.csv"

    releases = fetch_releases()
    if not releases:
        sys.exit("No published releases found.")

    rows = read_rows(csv_path) or backfill(releases)
    record(rows, snapshot(releases, datetime.now(timezone.utc).date().isoformat()))
    write_rows(csv_path, rows)

    for name, chart in CHARTS.items():
        for theme in THEMES:
            (out_dir / f"{name}-{theme}.svg").write_text(render_chart(rows, chart, theme), encoding="utf-8")
    (out_dir / "README.md").write_text(render_readme(rows), encoding="utf-8")
    print(f"Recorded {len(rows)} rows in {csv_path}")


if __name__ == "__main__":
    main()
