/* TRENDFRIQ V2 — public, read-only, source-linked editorial interface. */
(() => {
  'use strict';
  const $ = (s, root=document) => root.querySelector(s);
  const app = $('#app');
  const state = {feed:[], countries:[], indicators:[], archiveManifest:{years:[],total:0,collections:[]}, archiveCache:{},route:'home',query:'',filter:'all',country:'all',year:'all',page:1};
  const categories = ['World','Finance','Technology','Brands','Economy'];
  const taxonomy = {finance:'Finance',technology:'Technology',brands:'Brands',economy:'Economy',world:'World'};
  const safe = v => String(v??'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const validUrl = u => {try{const x=new URL(u);return ['https:','http:'].includes(x.protocol)?x.href:'#'}catch{return '#'}};
  const shortDate = v=>{try{return new Intl.DateTimeFormat('en',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'}).format(new Date(v))}catch{return 'Undated'}};
  const yearOf = a => (a.published||'').slice(0,4);
  const artWord = {Finance:'MARKETS',Technology:'FUTURE',Brands:'BRANDS',Economy:'ECONOMY',World:'WORLD'};
  const slug = c => String(c||'World').toLowerCase().replace(/[^a-z]/g,'');
  const art = (a,cls='')=>{
    const image = validUrl(a.image||'');
    if(image!=='#') return `<div class="art art-photo ${cls}"><img src="${safe(image)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.hidden=true;this.parentElement.classList.add('image-error')"><span class="image-fallback">${safe(artWord[a.category]||'WORLD')}</span></div>`;
    return `<div class="art art-${slug(a.category)} ${cls}" aria-hidden="true"><span>${safe(artWord[a.category]||'WORLD')}</span></div>`;
  };
  const meta = a=>`<div class="meta">${safe(a.category||'World')} <span class="dot">·</span> ${safe(a.source||'Original source')} <span class="dot">·</span> ${shortDate(a.published)}</div>`;
  const storyUrl = a=>validUrl(a.url);
  const story = a=>`<article class="story-card"><a href="${safe(storyUrl(a))}" target="_blank" rel="noopener noreferrer" aria-label="Open original story: ${safe(a.title)}">${art(a,'art-cover')}</a><div style="margin-top:13px">${meta(a)}</div><h3><a href="${safe(storyUrl(a))}" target="_blank" rel="noopener noreferrer">${safe(a.title)}</a></h3>${a.summary?`<p>${safe(a.summary)}</p>`:''}<a class="text-link" target="_blank" rel="noopener noreferrer" href="${safe(storyUrl(a))}">Original report ↗</a></article>`;
  const section=(title,link)=>`<div class="section-heading"><div><div class="section-eyebrow">TRENDFRIQ / CURATED INTELLIGENCE</div><h2>${safe(title)}</h2></div>${link?`<a href="${link}">View all →</a>`:''}</div>`;
  const noStories = `<div class="empty-card"><h3>Stories will appear here.</h3><p>Collected headlines appear after the first successful GitHub Actions data refresh. We don't invent news or fill the feed with placeholder stories.</p><a class="text-link" href="#archive">Browse historical source collections →</a></div>`;
  const renderList=(arr,max)=>arr.length?`<div class="story-grid">${arr.slice(0,max).map(story).join('')}</div>`:noStories;
  const headline = a=>`<a href="${safe(storyUrl(a))}" target="_blank" rel="noopener noreferrer">${safe(a.title)}</a>`;
  function home(){
    const feed=[...state.feed].sort((a,b)=>Number(Boolean(b.image))-Number(Boolean(a.image))),lead=feed[0];
    const hero = lead ? `<a class="hero-card ${validUrl(lead.image||'')!=='#'?'hero-photo':''}" target="_blank" rel="noopener noreferrer" href="${safe(storyUrl(lead))}">${validUrl(lead.image||'')!=='#'?`<img class="hero-image" src="${safe(validUrl(lead.image))}" alt="" fetchpriority="high" referrerpolicy="no-referrer" onerror="this.remove();this.parentElement.classList.remove('hero-photo')">`: ''}<div class="hero-text">${meta(lead)}<h1>${safe(lead.title)}</h1><p>${safe(lead.summary||'Explore the original reporting from the publisher.')}</p><span class="text-link">Read original report ↗</span></div></a>` : `<div class="hero-card"><div class="hero-text"><div class="meta">FINANCE · TECHNOLOGY · BRANDS · WORLD</div><h1>The world in perspective.</h1><p>Independent, source-linked intelligence across global markets, business, technology and history.</p><a href="#archive" class="text-link">Explore our archive →</a></div></div>`;
    const small = feed.slice(1,4).map(a=>`<article class="lead-small"><a href="${safe(storyUrl(a))}" target="_blank" rel="noopener noreferrer">${art(a)}</a><div>${meta(a)}<h3>${headline(a)}</h3></div></article>`).join('');
    const side=small||`<div class="empty-card"><h3>Every story starts with a source.</h3><p>More global headlines will appear when the scheduled collector has run.</p></div>`;
    let out=`<div class="section-eyebrow">THE GLOBAL EDITION · INDEPENDENT INTELLIGENCE</div><div class="hero-grid">${hero}<div class="side-leads">${side}</div></div>`;
    out+=`<div class="front-columns"><div>${section('The latest intelligence','#latest')}${renderList(feed.slice(4),9)}</div><aside class="aside"><h3>On the radar</h3>${feed.slice(0,6).map((a,i)=>`<div class="rank-item"><span class="rank-num">${i+1}</span><div><h4>${headline(a)}</h4>${meta(a)}</div></div>`).join('')||'<p class="count">Headlines are collected automatically from external sources.</p>'}</aside></div>`;
    out+=`<div class="feature-strip">${section('Across the world','#world')}<div class="compact-grid">${['Finance','Technology','Brands','World'].map(cat=>{const a=feed.find(i=>i.category===cat);return `<article class="compact-card"><div class="meta">${cat.toUpperCase()}</div><h3>${a?headline(a):'Explore '+cat.toLowerCase()+' intelligence'}</h3><a class="text-link" href="#${cat.toLowerCase()}">View section →</a></article>`}).join('')}</div></div>`;
    out+=`<div class="feature-strip">${section('From the archive','#archive')}<p class="count">A growing collection of source-linked stories, alongside access to historical newspaper libraries and original records.</p><a class="text-link" href="#archive">Explore the archive →</a></div>`;
    app.innerHTML=out;
  }
  function listing(route){
    const title = route==='latest'?'Latest intelligence':({finance:'Global finance',technology:'Technology & innovation',brands:'Brands & business',economy:'World economies',world:'Around the world'}[route]||'Intelligence');
    let list = route==='latest'?state.feed:state.feed.filter(a=>a.category===taxonomy[route]);
    if(state.query)list=list.filter(a=>`${a.title} ${a.summary} ${a.source} ${a.topic}`.toLowerCase().includes(state.query.toLowerCase()));
    if(state.filter!=='all')list=list.filter(a=>a.category===state.filter);
    const pageSize=18,max=Math.max(1,Math.ceil(list.length/pageSize));state.page=Math.min(Math.max(1,state.page),max);
    const page=list.slice((state.page-1)*pageSize,state.page*pageSize);
    app.innerHTML=`<div class="page-heading"><div class="section-eyebrow">THE WORLD · REPORTED & LINKED</div><h1>${safe(title)}</h1><p>Explore headlines from original publications. Select any story to continue reading at its source.</p></div><div class="page-layout"><div>${section(`${list.length} stories`,'')}${renderList(page,100)}${pager(state.page,max)}</div><aside class="filter-box"><h3>Refine your view</h3><label for="topic-filter">Category</label><select id="topic-filter"><option value="all">All categories</option>${categories.map(c=>`<option value="${c}" ${state.filter===c?'selected':''}>${c}</option>`).join('')}</select><label for="keyword-filter">Search headlines</label><input id="keyword-filter" type="search" value="${safe(state.query)}" placeholder="Search this collection"><p class="count">Each story links to its publisher. We do not republish full article texts.</p><a class="text-link" href="#archive">Visit historical archive →</a></aside></div>`;
    $('#topic-filter').addEventListener('change',e=>{state.filter=e.target.value;state.page=1;listing(route)});
    $('#keyword-filter').addEventListener('change',e=>{state.query=e.target.value.trim();state.page=1;listing(route)});
    wirePager(()=>listing(route));
  }
  function pager(page,max){if(max<2)return '';return `<div class="paging"><button id="page-prev" ${page===1?'disabled':''}>← Previous</button><span>Page ${page} / ${max}</span><button id="page-next" ${page===max?'disabled':''}>Next →</button></div>`}
  function wirePager(callback){const prev=$('#page-prev'),next=$('#page-next');if(prev)prev.addEventListener('click',()=>{state.page--;callback();window.scrollTo({top:160,behavior:'smooth'})});if(next)next.addEventListener('click',()=>{state.page++;callback();window.scrollTo({top:160,behavior:'smooth'})})}
  function economy(){
    const all=state.countries;const filtered=state.country==='all'?all:all.filter(c=>c.code===state.country);
    const byCode={};for(const x of state.indicators){byCode[x.code]??={};byCode[x.code][x.label]=x}
    app.innerHTML=`<div class="page-heading"><div class="section-eyebrow">DATA · WORLD BANK</div><h1>Economies of the world.</h1><p>Compare the most recently available annual GDP growth and inflation indicators, not live financial market prices.</p></div><div class="section-heading"><h2>Country indicators</h2><span class="count">${all.length} countries & territories indexed</span></div><div class="field" style="max-width:360px"><label for="country-picker">Select country</label><select id="country-picker"><option value="all">All available countries</option>${all.map(c=>`<option value="${safe(c.code)}" ${state.country===c.code?'selected':''}>${safe(c.name)}</option>`).join('')}</select></div><div style="overflow-x:auto"><table class="country-table"><thead><tr><th>Country or economy</th><th>GDP growth</th><th>Inflation</th><th>World Bank data</th></tr></thead><tbody>${filtered.slice(0,state.country==='all'?260:1).map(c=>{const v=byCode[c.code]||{};const g=v['GDP growth'],f=v['Inflation'];return `<tr><td>${safe(c.name)}</td><td>${g?`${safe(g.display)} <small>(${safe(g.year)})</small>`:'—'}</td><td>${f?`${safe(f.display)} <small>(${safe(f.year)})</small>`:'—'}</td><td><a target="_blank" rel="noopener noreferrer" href="${safe(validUrl(g?.url||f?.url||'https://data.worldbank.org/'))}">Source ↗</a></td></tr>`}).join('')||'<tr><td colspan="4">Country data will appear after the first successful collection.</td></tr>'}</tbody></table></div><p class="data-disclaimer">Data periods differ by country; values are annual observations from the World Bank, not real-time releases. Some locations may have missing values.</p><div class="feature-strip">${section('Economic developments','#latest')}${renderList(state.feed.filter(a=>a.category==='Economy'),6)}</div>`;
    $('#country-picker').addEventListener('change',e=>{state.country=e.target.value;economy()});
  }
  async function loadYear(year){
    if(!/^\d{4}$/.test(String(year)))return [];
    if(state.archiveCache[year])return state.archiveCache[year];
    try{const r=await fetch(`data/archive/${year}.json`,{cache:'no-store'});if(!r.ok)throw Error('Year not found');const v=await r.json();state.archiveCache[year]=Array.isArray(v)?v:[];return state.archiveCache[year]}catch{return []}
  }
  async function archive(){
    const m=state.archiveManifest,years=m.years||[];
    const yearOptions=`<option value="all">All collected years</option>${years.map(x=>`<option value="${safe(x.year)}" ${state.year===String(x.year)?'selected':''}>${safe(x.year)} · ${x.count} records</option>`).join('')}`;
    app.innerHTML=`<div class="archive-page"><div class="archive-mast"><div class="section-eyebrow">A HISTORY OF WHAT MATTERS</div><h1>The Archive</h1><p>Original Sources · Historical Record · Global Memory</p></div><div class="archive-note"><strong>Two kinds of history:</strong> TRENDFRIQ preserves headlines collected since its archive was enabled. For older centuries, explore external digitized newspaper collections below. Not every year, publication or country has surviving digital records.</div><div class="archive-search"><div class="field"><label for="archive-query">Search collected stories</label><input id="archive-query" placeholder="Headline, publication, subject…" value="${safe(state.query)}"></div><div class="field"><label for="archive-year">Collected publication year</label><select id="archive-year">${yearOptions}</select></div><div class="field"><label for="archive-topic">Category</label><select id="archive-topic"><option value="all">All categories</option>${categories.map(c=>`<option ${state.filter===c?'selected':''} value="${c}">${c}</option>`).join('')}</select></div></div><div class="archive-timeline"><span class="meta" style="margin-right:12px">HISTORICAL COLLECTIONS</span>${['1700–1799','1800–1899','1900–1999','2000–today'].map(x=>`<button class="century" data-period="${x}">${x}</button>`).join('')}</div><div id="collected-stories"><div class="loading">Reading stored archive records…</div></div><div class="feature-strip">${section('Historic newspaper libraries','')}<p class="count">Open external custodial collections to search records from the 1700s onward, where available. Subscription access may be required.</p><div class="archive-index">${(m.collections||[]).map(c=>`<article class="archive-library"><div class="meta">${safe(c.region)} · ${safe(c.period)}</div><h3>${safe(c.name)}</h3><p>${safe(c.description)}</p><a href="${safe(validUrl(c.url))}" target="_blank" rel="noopener noreferrer">Explore original collection ↗</a></article>`).join('')||'<p class="count">Historical collection links will appear when the first refresh completes.</p>'}</div></div></div>`;
    $('#archive-query').addEventListener('change',e=>{state.query=e.target.value.trim();state.page=1;updateArchive()});
    $('#archive-year').addEventListener('change',e=>{state.year=e.target.value;state.page=1;updateArchive()});
    $('#archive-topic').addEventListener('change',e=>{state.filter=e.target.value;state.page=1;updateArchive()});
    document.querySelectorAll('.century').forEach(b=>b.addEventListener('click',()=>{
      const period=b.dataset.period,query=encodeURIComponent('newspapers '+period);
      window.open(`https://www.europeana.eu/en/search?query=${query}`,'_blank','noopener,noreferrer');
    }));
    await updateArchive();
  }
  async function updateArchive(){
    const el=$('#collected-stories');if(!el)return;
    const years=state.year==='all'?(state.archiveManifest.years||[]).map(x=>x.year):[state.year];
    const records=(await Promise.all(years.map(loadYear))).flat();
    let filtered=records.filter(a=>(state.filter==='all'||a.category===state.filter)&&(!state.query||`${a.title} ${a.summary} ${a.source} ${a.topic}`.toLowerCase().includes(state.query.toLowerCase())));
    filtered.sort((a,b)=>String(b.published).localeCompare(String(a.published)));
    const pageSize=18,max=Math.max(1,Math.ceil(filtered.length/pageSize));state.page=Math.min(state.page,max);
    const page=filtered.slice((state.page-1)*pageSize,state.page*pageSize);
    el.innerHTML=`${section(`Collected news · ${filtered.length} records`,'')}<div class="archive-grid">${page.map(a=>`<article class="archive-item">${art(a)}<div style="margin-top:12px">${meta(a)}</div><h3>${headline(a)}</h3><p>${safe(a.summary||'Read the original report at the publisher.')}</p><a class="text-link" href="${safe(storyUrl(a))}" target="_blank" rel="noopener noreferrer">View source ↗</a></article>`).join('')}</div>${page.length?'':`<div class="empty-card"><h3>No collected stories for this selection.</h3><p>The permanent collection starts when the new GitHub Action successfully saves data. Historical materials are available through the external library links below.</p></div>`}${pager(state.page,max)}`;
    wirePager(updateArchive);
  }
  function nav(){
    let route=(location.hash||'#home').slice(1).toLowerCase().split('?')[0];if(!['home','latest','finance','technology','brands','economy','world','archive'].includes(route))route='home';
    if(route!==state.route){state.filter='all';state.page=1;state.query=''}state.route=route;
    document.querySelectorAll('[data-route]').forEach(el=>{el.classList.toggle('active',el.dataset.route===route);if(el.dataset.route===route)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current')});
    if(route==='home')home();else if(route==='economy')economy();else if(route==='archive')archive();else listing(route);
    window.scrollTo({top:0,behavior:'instant'});
  }
  async function boot(){
    const saved=localStorage.getItem('trendfriq-theme');document.documentElement.dataset.theme=saved==='dark'?'dark':'light';
    $('#theme-button').addEventListener('click',()=>{const next=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=next;localStorage.setItem('trendfriq-theme',next)});
    $('#menu-button').addEventListener('click',()=>{$('.primary-nav').scrollIntoView({behavior:'smooth'})});
    $('#search-button').addEventListener('click',()=>{$('#search-panel').hidden=!$('#search-panel').hidden;if(!$('#search-panel').hidden)$('#site-search').focus()});
    const search=()=>{state.query=$('#site-search').value.trim();state.page=1;state.filter='all';$('#search-panel').hidden=true;if(location.hash==='#latest')listing('latest');else {location.hash='#latest';setTimeout(()=>listing('latest'),0)}};
    $('#search-submit').addEventListener('click',search);$('#site-search').addEventListener('keydown',e=>{if(e.key==='Enter')search()});
    $('#date-display').textContent=new Intl.DateTimeFormat('en',{weekday:'long',year:'numeric',month:'long',day:'numeric'}).format(new Date());
    $('#copyright-year').textContent=new Date().getFullYear();
    const [news,archives]=await Promise.allSettled([fetch('data/latest.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('feed unavailable');return r.json()}),fetch('data/archive/manifest.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('archive unavailable');return r.json()})]);
    if(news.status==='fulfilled'){state.feed=news.value.articles||[];state.countries=news.value.countries||[];state.indicators=news.value.indicators||[];state.lastUpdated=news.value.last_updated;const hot=state.feed[0];if(hot)$('#ticker-text').textContent=hot.title}
    if(archives.status==='fulfilled')state.archiveManifest=archives.value;
    window.addEventListener('hashchange',nav);nav();
    // Invisible periodic data check. No public refresh control, timestamp or sync indicator.
    setInterval(async()=>{try{const r=await fetch('data/latest.json',{cache:'no-store'});if(!r.ok)return;const d=await r.json();if(d.last_updated&&d.last_updated!==state.lastUpdated){state.lastUpdated=d.last_updated;state.feed=d.articles||[];state.countries=d.countries||[];state.indicators=d.indicators||[];if(state.route!=='archive')nav()}}catch{}},300000);
  }
  boot();
})();
