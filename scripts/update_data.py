#!/usr/bin/env python3
"""Collect linked headline metadata and World Bank indicators.

Latest feed is refreshed; archive is append-only in data/archive/YYYY.json.
GitHub Actions commits changed data back to the repository, then deploys.
No article bodies or publisher images are copied.
"""
from __future__ import annotations
import datetime as dt
import email.utils
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'config.json').read_text('utf-8'))
DATA = ROOT / 'data'
ARCHIVE = DATA / 'archive'
HEADERS = {'User-Agent': 'TRENDFRIQ-news-index/2.0 (source linked; contact repository owner)'}


def fetch(url, timeout=22):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=timeout) as res:
        return res.read()


def fetch_json(url):
    return json.loads(fetch(url))


def clean(value, limit=360):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', value or '')).strip()[:limit]


def read_json(path, default):
    try:
        return json.loads(path.read_text('utf-8'))
    except (OSError, ValueError):
        return default


def write_json(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(content, ensure_ascii=False, indent=2) + '\n'
    if not path.exists() or path.read_text('utf-8') != payload:
        path.write_text(payload, encoding='utf-8')


def news(topic):
    query = urllib.parse.quote(topic['query'])
    url = f'https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en'
    tree = ET.fromstring(fetch(url))
    records = []
    for item in tree.findall('.//channel/item')[:CONFIG['items_per_topic']]:
        title = clean(item.findtext('title', ''), 220)
        link = item.findtext('link', '').strip()
        if not title or not link.startswith('https://'):
            continue
        source_tag = item.find('source')
        source = clean(source_tag.text if source_tag is not None else 'News feed', 80)
        if title.endswith(' - ' + source):
            title = title[:-(len(source) + 3)]
        try:
            date = email.utils.parsedate_to_datetime(item.findtext('pubDate'))
            published = date.astimezone(dt.timezone.utc).isoformat().replace('+00:00', 'Z')
        except (TypeError, ValueError, AttributeError):
            continue  # Do not misdate undated records.
        desc = clean(item.findtext('description', ''))
        if not desc or title in desc:
            desc = ''
        records.append({
            'id': hashlib.sha256(link.encode()).hexdigest()[:22],
            'title': title, 'summary': desc, 'url': link,
            'source': source, 'published': published,
            'category': topic['category'], 'topic': topic['label'],
            'country': '', 'image': ''
        })
    return records


def economic_data(previous):
    countries = previous.get('countries', [])
    indicators = previous.get('indicators', [])
    try:
        response = fetch_json('https://api.worldbank.org/v2/country?format=json&per_page=400')
        parsed = []
        for c in response[1]:
            if c.get('region', {}).get('id') == 'NA' or not c.get('id'):
                continue
            parsed.append({'code': c['id'], 'name': c['name'],
                           'region': c.get('region', {}).get('value', '')})
        if parsed:
            countries = sorted(parsed, key=lambda c: c['name'])
    except Exception as exc:
        print('WARN country list:', exc, file=sys.stderr)
    names = {c['code']: c['name'] for c in countries}
    stored = {(i.get('code'), i.get('label')): i for i in indicators}
    for indicator in CONFIG['indicators']:
        try:
            code = indicator['code']
            # Collect several recent annual observations; retain most recent actual value per country.
            url = f'https://api.worldbank.org/v2/country/all/indicator/{code}?format=json&mrnev=1&per_page=20000'
            response = fetch_json(url)
            for row in response[1] or []:
                iso = row.get('countryiso3code')
                value = row.get('value')
                if not iso or iso not in names or value is None:
                    continue
                display = f'{value:,.1f}%' if indicator['format'] == 'percent' else str(round(value, 2))
                stored[(iso, indicator['label'])] = {
                    'code': iso, 'country': names[iso], 'label': indicator['label'],
                    'year': str(row['date']), 'value': value, 'display': display,
                    'url': f'https://data.worldbank.org/indicator/{code}?locations={iso}',
                    'source': 'World Bank'
                }
        except Exception as exc:
            print('WARN indicator:', indicator['label'], exc, file=sys.stderr)
    return countries, sorted(stored.values(), key=lambda i: (i['country'], i['label']))


def main():
    now = dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z')
    old = read_json(DATA / 'latest.json', {})
    history = read_json(DATA / 'archive' / 'manifest.json', {'years': [], 'total': 0})
    incoming = []
    successes = 0
    for topic in CONFIG['topics']:
        try:
            articles = news(topic)
            if articles:
                successes += 1
                incoming.extend(articles)
        except Exception as exc:
            print('WARN RSS:', topic['label'], exc, file=sys.stderr)
    # Existing archive is never replaced with just the newest feed; append by year.
    archive_records = {}
    for path in ARCHIVE.glob('[0-9][0-9][0-9][0-9].json'):
        old_records = read_json(path, [])
        archive_records[path.stem] = {a['id']: a for a in old_records if a.get('id')}
    added = 0
    # Seed the durable archive with previously visible records on the first upgrade.
    for record in incoming + old.get('articles', []):
        if not record.get('id') or not record.get('published'):
            continue
        year = record['published'][:4]
        group = archive_records.setdefault(year, {})
        if record['id'] not in group:
            group[record['id']] = record
            added += 1
    for year, entries in archive_records.items():
        write_json(ARCHIVE / f'{year}.json', sorted(entries.values(), key=lambda a: a['published'], reverse=True))
    years = sorted(archive_records, reverse=True)
    write_json(ARCHIVE / 'manifest.json', {
        'years': [{'year': y, 'count': len(archive_records[y])} for y in years],
        'total': sum(len(v) for v in archive_records.values()),
        'collections': CONFIG['history_collections']
    })
    # Site can display the last good feed on temporary source failure.
    all_articles = {a['id']: a for a in old.get('articles', []) if a.get('id')}
    for article in incoming:
        all_articles[article['id']] = article
    latest = sorted(all_articles.values(), key=lambda a: a.get('published', ''), reverse=True)[:CONFIG['front_page_items']]
    countries, indicators = economic_data(old)
    write_json(DATA / 'latest.json', {
        'last_updated': now if successes else old.get('last_updated'),
        'articles': latest, 'countries': countries, 'indicators': indicators,
        'source_count': successes
    })
    print(f'Feeds {successes}/{len(CONFIG["topics"])}; fresh {len(incoming)}; archive +{added}; total {sum(len(v) for v in archive_records.values())}; countries {len(countries)}')


if __name__ == '__main__':
    main()
