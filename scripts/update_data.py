#!/usr/bin/env python3
"""Refresh public, source-linked headlines and World Bank indicators.
Dependencies: Python standard library. Failures keep the last working snapshot.
This script does not scrape articles or use any private credentials.
"""
from __future__ import annotations
import datetime as dt
import email.utils
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
OUTPUT=ROOT/'data'/'latest.json'
HEADERS={'User-Agent':'TRENDFRIQ-public-intelligence/1.0 (+https://github.com/; RSS aggregator)'}

def fetch(url,timeout=16):
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=timeout) as response:
        return response.read()

def plain(s):
    s=re.sub(r'<[^>]*>',' ',s or '')
    s=re.sub(r'\s+',' ',s).strip()
    return s[:330]

def news_search(topic):
    query=urllib.parse.quote(topic['query'])
    return f'https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en'

def extract_entries(topic):
    root=ET.fromstring(fetch(news_search(topic)))
    result=[]
    for item in root.findall('.//channel/item')[:CONFIG.get('items_per_topic',8)]:
        title=plain(item.findtext('title',''))
        url=item.findtext('link','').strip()
        if not title or not url.startswith('https://'):continue
        publisher=item.find('source')
        source=plain(publisher.text if publisher is not None else 'Google News')
        date=item.findtext('pubDate')
        try:
            parsed=email.utils.parsedate_to_datetime(date).astimezone(dt.timezone.utc)
            published=parsed.isoformat().replace('+00:00','Z')
        except (TypeError,ValueError,AttributeError):
            published=dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00','Z')
        headline=title
        if source and title.endswith(' - '+source):headline=title[:-(len(source)+3)]
        desc=plain(item.findtext('description',''))
        # Google News descriptions include linked HTML snippets; avoid publishing duplicate titles.
        if headline in desc or len(desc)<45:desc='Read the original source for full details and reporting.'
        result.append({'id':hashlib.sha256((url or title).encode()).hexdigest()[:20],
          'title':headline,'summary':desc,'url':url,'source':source or 'Google News',
          'category':topic['category'],'topic':topic['label'],'published':published})
    return result

def world_bank(country,ind):
    url=f'https://api.worldbank.org/v2/country/{country["code"]}/indicator/{ind["code"]}?format=json&per_page=8'
    response=json.loads(fetch(url))
    if not isinstance(response,list) or len(response)<2 or not response[1]:return None
    for item in response[1]:
        val=item.get('value')
        if val is None:continue
        fmt=ind.get('format','number')
        display=(f'{val:,.1f}%' if fmt=='percent' else
                 f'${val/1_000_000_000:,.2f}T' if fmt=='usd_trillions' else
                 f'{val:,.2f}')
        return {'country':country['name'],'label':ind['label'],'year':str(item['date']),
                'display':display,'value':val,'source':'World Bank',
                'url':'https://data.worldbank.org/indicator/'+ind['code']+'?locations='+country['code']}
    return None

def main():
    old={}
    if OUTPUT.exists():
        try:old=json.loads(OUTPUT.read_text(encoding='utf-8'))
        except (ValueError,OSError):pass
    topics=CONFIG['topics']
    articles=[];succeeded=0;warnings=[]
    for topic in topics:
        try:
            records=extract_entries(topic)
            if records:articles.extend(records);succeeded+=1
            else:warnings.append(f'No items: {topic["label"]}')
        except Exception as exc:
            warnings.append(f'{topic["label"]}: {exc}')
            # Preserve previously collected stories for a feed that temporarily fails.
            articles.extend([a for a in old.get('articles',[]) if a.get('topic')==topic['label']])
    if not articles and not old.get('articles'):
        print('No articles retrieved: retaining empty snapshot',file=sys.stderr)
    by_id={a['id']:a for a in articles+old.get('articles',[])}
    entries=sorted(by_id.values(),key=lambda a:a.get('published',''),reverse=True)[:CONFIG.get('max_items',120)]
    indicators=[]
    fresh_indicators=0
    for country in CONFIG.get('countries',[]):
        for ind in CONFIG.get('indicators',[]):
            try:
                result=world_bank(country,ind)
                if result:
                    indicators.append(result)
                    fresh_indicators+=1
            except Exception as exc:warnings.append(f'World Bank {country["code"]}/{ind["code"]}: {exc}')
    # Preserve previously collected individual indicators on partial API outages.
    previous={(x.get('country'),x.get('label')):x for x in old.get('indicators',[])}
    current={(x.get('country'),x.get('label')):x for x in indicators}
    indicators=list({**previous,**current}.values())
    if not succeeded and not indicators and not old.get('articles'):
        print('No usable feeds or economic indicators available yet',file=sys.stderr)

    now=dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00','Z')
    output={'last_updated':now if succeeded or fresh_indicators else old.get('last_updated'),
            'articles':entries,'indicators':indicators,
            'topics':[t['label'] for t in topics],
            'feeds':[{'label':t['label'],'category':t['category']} for t in topics], 'news_sources_succeeded':succeeded}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Updated: {len(entries)} articles; {len(indicators)} economic indicators; {succeeded}/{len(topics)} feeds fetched')
    for w in warnings:print('WARN:',w,file=sys.stderr)

if __name__=='__main__':main()
