# trendfriq. — Automated intelligence dashboard

A read-only public dashboard for finance, brands, technology and country/economic developments. Deploys to **GitHub Pages** and collects public data using **GitHub Actions**.

## What it actually does

- Fetches source-linked news headlines from Google News RSS searches across 8 configurable topics.
- Fetches GDP growth and inflation observations for Bangladesh, India and the United States from the World Bank Indicators API.
- Refreshes **on GitHub Actions every 15 minutes (best effort)** and redeploys the site. GitHub may delay or skip scheduled runs.
- Browsers check the newly published JSON every 5 minutes while the page is open. The reader can also tap Refresh.
- Displays the last collection timestamp and shows a delayed-data warning after an hour.
- Search, filter, mobile navigation, dark/light mode, and device-local bookmarks. Visitors cannot edit published content.

**Important:** This is *near-current headline aggregation*, not a second-by-second live market-data terminal. World Bank indicator releases are periodic and can represent prior calendar years. Company revenue figures, real-time share prices and instantaneous alerts are not included. They need separately licensed financial APIs and sometimes a backend.

## Publish with GitHub

1. Extract the ZIP and upload **all** its contents, including the hidden `.github` directory, to the **root** of a new **public** GitHub repository. Name it `trendfriq` (or another repository name). Use the `main` branch.
2. Go to **Settings → Pages → Build and deployment → Source → GitHub Actions**.
3. Open **Actions → Refresh intelligence and deploy website → Run workflow** once. Confirm that both the `build` and `deploy` jobs succeed.
4. Open **Settings → Pages** to find the public website URL, normally `https://YOUR-USERNAME.github.io/trendfriq/`.
5. Allow the scheduled workflow to run automatically. GitHub may throttle or delay frequent jobs; if so, change the cron schedule to hourly.

## Customize monitored subjects (owner only)

Edit `config.json` **in the GitHub repository** and commit the change. In `topics`, update `label`, `category` (`Finance`, `Brands`, `Technology`, `Economy`) and Google News RSS `query`. Modify `countries` and `indicators` to control World Bank cards. No visitor-facing editing interface is present.

Edit the appearance via `assets/style.css`, or page structure in `index.html`. The scripts and configuration are not uploaded as part of the published site; only `index.html`, `assets/` and generated `data/latest.json` are deployed.

## Updating locally / testing

Requires Python 3.10+ and standard library only:

```bash
python scripts/update_data.py
python -m http.server 8000
```

Then open `http://localhost:8000`. Running the updater needs internet access. Before the first successful run the website truthfully shows no stories instead of fabricated data.

## Data and safety

- Headlines are fetched from Google News RSS; original source links are shown. Google News links may redirect.
- Macro observations come from the World Bank; their release years are explicitly shown.
- Source availability and RSS terms may change. The updater retains the last known snapshot if a feed fails. A green system indicator is **not** evidence of real-time price data.
- The repository **must contain no API keys**, private credentials or confidential content. GitHub Pages is public. Visitors can read the front-end code and public JSON, but cannot modify the repository without GitHub write permission.
- This is an information discovery tool, not financial advice. Validate financial facts against company filings and official exchanges.

## Project structure

```
index.html                    Website shell
assets/style.css              Theme and responsive layout
assets/app.js                 Public reader and search/filters
assets/favicon.svg            Icon
config.json                   Owner-managed topics/countries
scripts/update_data.py        Scheduled data collector
.github/workflows/update-and-deploy.yml    Fetch + deploy workflow
data/latest.json              Initial JSON, refreshed during build
```

Website brand name is provisional; legal trademark/domain availability not guaranteed.
