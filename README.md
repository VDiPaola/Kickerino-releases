# Kickerino download stats

Cumulative downloads of Kickerino release files. A [GitHub Actions workflow](https://github.com/VDiPaola/Kickerino-releases/actions/workflows/download-stats.yml) updates this branch daily.

Back to the [main README](https://github.com/VDiPaola/Kickerino-releases).

## Installs

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/VDiPaola/Kickerino-releases/stats/installs-dark.svg">
  <img alt="Line chart of cumulative installer downloads over time. Total: 78." src="https://raw.githubusercontent.com/VDiPaola/Kickerino-releases/stats/installs-light.svg">
</picture>

## Updates

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/VDiPaola/Kickerino-releases/stats/updates-dark.svg">
  <img alt="Line chart of cumulative update package downloads over time. Total: 26." src="https://raw.githubusercontent.com/VDiPaola/Kickerino-releases/stats/updates-light.svg">
</picture>

## Current totals

As of 2026-09-25 (latest release: v1.1.9).

| Release file | Downloads |
|---|---|
| Windows Setup | 61 |
| Windows Portable | 13 |
| Linux AppImage | 4 |
| Windows updates | 26 |
| Linux updates | 0 |

## How the data is collected

- Totals include every release, not only the latest one.
- Installs count `Kickerino-win-Setup.exe`, `Kickerino-win-Portable.zip` and `Kickerino.AppImage`.
- Microsoft Store installs are not included.
- Updates count the `.nupkg` packages downloaded by the auto-updater.
- Update checks (`releases.*.json` and `RELEASES`) are not counted.
- A row is added to [`downloads.csv`](downloads.csv) only when a total changes.
- History before daily tracking started is estimated by counting each release's downloads on its publish date.
