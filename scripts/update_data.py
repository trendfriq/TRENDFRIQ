#!/usr/bin/env python3
"""Collect linked headline metadata and World Bank indicators.

Latest feed is refreshed; archive is append-only in data/archive/YYYY.json.
GitHub Actions commits changed data back to the repository, then deploys.
No article bodies or publisher image files are copied. Image URLs point to publishers.
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
from html.parser import HTMLParser
from html import unescape
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'config.json').read_text('utf-8'))
DATA = ROOT / 'data'
ARCHIVE = DATA / 'archive'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; TRENDFRIQ/2.1; public RSS metadata index)'}
IMAGE_NS = {'media': 'http://search.yahoo.com/mrss/', 'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd'}
ALLOWED_IMAGE_EXT = ('.jpg', '.jpeg', '.png', '.webp', '.avif')



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



def image_url(value):
    """Accept only absolute HTTPS photographs (not favicons, trackers or data URLs)."""
    if not value:
        return ''
    url = unescape(str(value)).strip()
    try:
        u = urllib.parse.urlsplit(url)
        if u.scheme != 'https' or not u.hostname or u.username or u.password:
            return ''
        if u.hostname.lower() in {'localhost', '127.0.0.1', '::1'}:
            return ''
        if any(part in (u.path or '').lower() for part in ('favicon', '1x1', 'pixel.gif', 'tracking', 'spacer.gif', '/logo')):
            return ''
        if (u.path or '').lower().endswith(('.svg', '.ico', '.gif')):
            return ''
        return url[:1800]
    except ValueError:
        return ''


class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.image = ''
        self.canonical = ''
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == 'meta':
            key = (d.get('property') or d.get('name') or '').lower()
            if key in ('og:image', 'og:image:url', 'twitter:image', 'twitter:image:src') and not self.image:
                self.image = image_url(urllib.parse.urljoin(self.canonical or '', d.get('content', '')))
        if tag == 'link' and d.get('rel', '').lower() == 'canonical':
            self.canonical = d.get('href', '')


def extract_image_from_item(item):
    """Read RSS Media RSS/enclosure/description image URLs without copying assets."""
    candidates = []
    for node in item.iter():
        local = node.tag.split('}')[-1].lower()
        if local in ('thumbnail', 'content'):
            url = node.attrib.get('url', '')
            if local == 'thumbnail' or node.attrib.get('medium') == 'image' or node.attrib.get('type', '').startswith('image/'):
                candidates.append(url)
        if local == 'enclosure' and node.attrib.get('type', '').startswith('image/'):
            candidates.append(node.attrib.get('url', ''))
    html = ' '.join((node.text or '') for node in item.iter() if node.tag.split('}')[-1].lower() in ('description','encoded','summary','content'))
    for m in re.finditer(r'<img[^>]+(?:src|data-src)=[\"\']([^\"\']+)', html, re.I):
        candidates.append(m.group(1))
    for url in candidates:
        result = image_url(url)
        if result:
            return result
    return ''


def article_metadata(url):
    """Best effort publisher Open Graph photo; skip Google-hosted article pages."""
    try:
        req = urllib.request.Request(url, headers={**HEADERS, 'Accept': 'text/html,application/xhtml+xml'})
        with urllib.request.urlopen(req, timeout=5) as res:
            final_url = res.geturl()
            if 'news.google.com' in urllib.parse.urlsplit(final_url).hostname.lower():
                return '', ''
            ctype = res.headers.get('content-type', '').lower()
            if 'html' not in ctype:
                return '', ''
            text = res.read(160000).decode('utf-8', errors='replace')
        parser = MetadataParser()
        parser.feed(text)
        return parser.image, final_url
    except (OSError, ValueError, HTTPError, URLError, TimeoutError):
        return '', ''


def publisher_news():
    """Publisher-authored RSS feeds often carry real hero photographs; no scrapers or stock images."""
    feeds = [
        ('BBC News', 'World', 'https://feeds.bbci.co.uk/news/world/rss.xml'),
        ('BBC Business', 'Finance', 'https://feeds.bbci.co.uk/news/business/rss.xml'),
        ('BBC Technology', 'Technology', 'https://feeds.bbci.co.uk/news/technology/rss.xml'),
        ('The Guardian', 'World', 'https://www.theguardian.com/world/rss'),
        ('The Guardian', 'Economy', 'https://www.theguardian.com/business/economics/rss'),
        ('TechCrunch', 'Technology', 'https://techcrunch.com/feed/'),
        ('The Verge', 'Technology', 'https://www.theverge.com/rss/index.xml'),
        ('The Guardian', 'Technology', 'https://www.theguardian.com/uk/technology/rss'),
        ('The Guardian', 'Brands', 'https://www.theguardian.com/business/rss'),
        ('NPR', 'World', 'https://feeds.npr.org/1004/rss.xml'),
    ]
    items = []
    successes = 0
    for publisher, category, feed_url in feeds:
        try:
            root = ET.fromstring(fetch(feed_url, timeout=12))
            nodes = root.findall('.//channel/item')
            if not nodes: # Atom feed
                nodes = root.findall('.//{http://www.w3.org/2005/Atom}entry')
            if nodes: successes += 1
            for item in nodes[:10]:
                title = clean(item.findtext('title') or item.findtext('{http://www.w3.org/2005/Atom}title'), 220)
                link = item.findtext('link', '').strip()
                if not link:
                    atom_link = item.find('{http://www.w3.org/2005/Atom}link')
                    link = atom_link.attrib.get('href', '') if atom_link is not None else ''
                if not title or not link.startswith('https://'): continue
                raw_date = item.findtext('pubDate') or item.findtext('{http://www.w3.org/2005/Atom}published') or item.findtext('{http://www.w3.org/2005/Atom}updated')
                try:
                    date = email.utils.parsedate_to_datetime(raw_date) if raw_date and ',' in raw_date else dt.datetime.fromisoformat((raw_date or '').replace('Z', '+00:00'))
                    published = date.astimezone(dt.timezone.utc).isoformat().replace('+00:00', 'Z')
                except (ValueError, TypeError, AttributeError): continue
                summary = clean(item.findtext('description') or item.findtext('{http://www.w3.org/2005/Atom}summary'), 360)
                items.append({'id': hashlib.sha256(link.encode()).hexdigest()[:22], 'title': title,
                              'summary': summary, 'url': link, 'source': publisher,
                              'published': published, 'category': category, 'topic': publisher,
                              'country': '', 'image': extract_image_from_item(item)})
        except Exception as exc:
            print('WARN publisher RSS:', publisher, str(exc)[:200], file=sys.stderr)
    return items, successes

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
            'country': '', 'image': extract_image_from_item(item)
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
    direct_articles, direct_successes = publisher_news()
    incoming.extend(direct_articles)
    successes += direct_successes
    # Enrich a limited number of direct publisher stories with their Open Graph image.
    # Never replace a verified image with a blank result. Google News often prevents
    # resolving the original publisher URL; such records intentionally keep a fallback.
    examined = 0
    for article in sorted(incoming, key=lambda a: a.get('published', ''), reverse=True):
        if article.get('image') or examined >= 28:
            continue
        if 'news.google.com' in urllib.parse.urlsplit(article['url']).hostname.lower():
            continue
        examined += 1
        img, canonical = article_metadata(article['url'])
        if img:
            article['image'] = img
    # Existing archive is never replaced with just the newest feed; append by year.
    archive_records = {}
    for path in ARCHIVE.glob('[0-9][0-9][0-9][0-9].json'):
        old_records = read_json(path, [])
        archive_records[path.stem] = {a['id']: a for a in old_records if a.get('id')}
    # Never generate AI images. Reuse existing publisher image URLs from the archive.
    known_images = {a["id"]: a["image"] for year in archive_records.values() for a in year.values() if a.get("id") and a.get("image") and str(a["image"]).startswith("https://")}
    for article in incoming:
        if not article.get("image") and article["id"] in known_images:
            article["image"] = known_images[article["id"]]
            article["image_type"] = "source"
    added = 0
    # Seed the durable archive with previously visible records on the first upgrade.
    for record in incoming + old.get('articles', []):
        if not record.get('id') or not record.get('published'):
            continue
        year = record['published'][:4]
        group = archive_records.setdefault(year, {})
        if record['id'] not in group:
            if record.get('image_type') == 'ai':
                record['image'] = ''
                record.pop('image_type', None)
            group[record['id']] = record
            added += 1
        elif record.get('image') and str(record['image']).startswith('https://') and not group[record['id']].get('image'):
            group[record['id']]['image'] = record['image']
            group[record['id']]['image_type'] = 'source'
    # Never display legacy generated AI artwork.
    for entries in archive_records.values():
        for record in entries.values():
            if record.get('image_type') == 'ai' or str(record.get('image','')).startswith('assets/generated/'):
                record['image'] = ''
                record.pop('image_type', None)
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
    for record in all_articles.values():
        if record.get('image_type') == 'ai' or str(record.get('image','')).startswith('assets/generated/'):
            record['image'] = ''
            record.pop('image_type', None)
    for article in incoming:
        if article['id'] in all_articles and str(all_articles[article['id']].get('image','')).startswith('https://') and not article.get('image'):
            article['image'] = all_articles[article['id']]['image']
            article['image_type'] = 'source'
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
