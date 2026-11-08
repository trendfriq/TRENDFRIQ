# TRENDFRIQ v2 — Editorial Global Intelligence

A GitHub Pages, **read-only** public news index with an editorial homepage, light and dark mode, source-linked coverage, worldwide World Bank country indicators, and a growing chronological archive.

**Important scope:** New collected records can be permanently retained in the repository from the time this workflow starts. Historical stories from the 1700s are **not already in the stored archive**. External historical newspaper collection links are provided, with availability and licensing decided by those institutions. This version cannot guarantee full global news coverage or market tick-by-tick realtime data.

## Installing into your existing repository

Your repository: `https://github.com/trendfriq/TRENDFRIQ`

1. **Back up your repository** using Code → Download ZIP.
2. Open this download and upload the **contents** of the `TRENDFRIQ_V2` folder to the repository root. Replace the existing `index.html`, `config.json`, `assets` and `scripts` files with the new versions. Ensure hidden `.github` folder is included.
3. **Delete your previous workflow file** `.github/workflows/refresh.yml` if present. Also delete the old `.github/workflows/update-and-deploy.yml` before uploading the replacement if GitHub's browser uploader cannot overwrite it reliably. The final repo should have **one** TRENDFRIQ workflow: `.github/workflows/update-and-deploy.yml`.
4. Open **Settings → Actions → General → Workflow permissions** and choose **Read and write permissions** if available. GitHub Pages access must also be enabled, and `main` must be your default branch. In a public repository this allows the workflow's `GITHUB_TOKEN` to commit the newly collected archive data.
5. Open **Settings → Pages → Build and deployment → Source = GitHub Actions**.
6. Go to **Actions → Refresh intelligence and deploy website → Run workflow**. Review both the `Fetch and append public data` and `Preserve archive in repository` steps, as well as deployment.
7. Confirm `data/archive/manifest.json` and `data/archive/YYYY.json` are updated with records in the repository. The archive is not persistent if the workflow's commit fails.
8. Open `https://trendfriq.github.io/TRENDFRIQ/` and hard refresh.

## File layout

- `index.html`: semantic document, header, navigation, footer.
- `assets/style.css`: editorial layout and themes.
- `assets/app.js`: client-side magazine, archive and country views.
- `scripts/update_data.py`: Python standard-library collector; Google News RSS search and World Bank API.
- `config.json`: topic search queries, economic indicator definitions and historical library links.
- `data/latest.json`: newest source-linked headlines and worldwide economic indicator snapshot.
- `data/archive/YYYY.json`: archived collected articles, grouped by the **publication year** of the original story, not the collection date.
- `data/archive/manifest.json`: year counts and historical library links.
- `.github/workflows/update-and-deploy.yml`: scheduled collection, commit of archive, and Pages deployment.

## Automation and permanence

- Runs at minutes 7, 22, 37 and 52 of each hour, **best effort**, plus manual runs and source-code commits.
- Website checks for the next snapshot silently every five minutes while open. No public sync times, refresh buttons or backend controls.
- Each run deduplicates on a hash of the source URL and **appends to annual archive files**. Files are committed to the main repository branch; re-running doesn't erase older records.
- News source feed limits, access failures and regional language biases limit actual coverage. Google News RSS is an aggregator, not a guaranteed authoritative or comprehensive news archive. No full copyrighted article texts are stored.
- For a large global archive, Git repository size, performance and GitHub Actions resource constraints will eventually require a managed database and archival storage. Consider a paid, backed-up PostgreSQL service for long-term operation.
- GitHub Pages site, data and public repository files are publicly accessible. Credentials and private data must never be stored in these files.

## Historical records

The archive distinguishes **collected news** (stored locally) from **historical libraries** (external links). Digitized 18th-century papers are not automatically imported. Search access and scan color at those external sites are determined by the provider. The local Archive view is grayscale; outgoing original pages are not modified.

## Adjustments

- Edit `config.json` topics to broaden or focus collection. Leave cross-region topics to maintain global scope.
- Change typography or colors in `assets/style.css`. Uses Cormorant Garamond + DM Sans from Google Fonts with local fallback.
- Dark mode is selected by the viewer and persisted using local browser storage.
- No public editing UI exists. Readers can navigate and search, but cannot modify the published site.

## Testing

```bash
python -m py_compile scripts/update_data.py
node --check assets/app.js
python scripts/update_data.py
```

The last command needs outbound network access. It should generate real `data` content and is not required on a local machine when GitHub Actions is configured. **Data collectors and automated Git commits must be monitored; a green Pages deployment alone is not proof a particular data source succeeded.**
