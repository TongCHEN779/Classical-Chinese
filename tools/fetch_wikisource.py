#!/usr/bin/env python3
"""Cache primary Wikisource text and revision provenance; never mark translations complete."""
import argparse, hashlib, json, re, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, unquote, urlparse
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
BOOKS = {'yuewei':'閱微草堂筆記','yantielun':'鹽鐵論','songlun':'宋論','huainanzi':'淮南子','liaozhai':'聊齋志異','xiaochuang':'醉古堂劍掃'}

def download(title, include_lists=False):
    url = 'https://zh.wikisource.org/zh-hans/' + quote(title, safe='/')
    for attempt in range(4):
        try:
            with urlopen(Request(url, headers={'User-Agent':'ClassicalChineseLibrary/1.0 (public-domain text research)'}), timeout=45) as r:
                body = r.read().decode('utf-8')
                actual = r.url
            break
        except Exception:
            if attempt == 3: raise
            time.sleep(2 ** attempt)
    soup = BeautifulSoup(body, 'html.parser')
    main = soup.select_one('#mw-content-text .mw-parser-output')
    if main is None: raise ValueError('Missing article body: ' + title)
    links=[]
    for a in main.select('a[href]'):
        path=unquote(urlparse(a['href']).path)
        for prefix in ['/wiki/','/zh-hans/','/zh/']:
            if path.startswith(prefix):
                t=path[len(prefix):]
                if t.startswith(title.split('/')[0]+'/') and 'redlink=1' not in a['href']:
                    links.append({'title':t,'label':a.get_text(' ',strip=True)})
                break
    revision = soup.select_one('a[href*="oldid="]')
    rev = re.search(r'oldid=(\d+)', revision['href']) if revision else None
    for node in main.select('.mw-editsection, .noprint, .ws-noexport, .navigation-not-searchable, .licenseContainer, .licensetpl, #toc, .toc, .header-container, .navbox, .wst-header, .catlinks, sup.reference'):
        node.decompose()
    blocks=[]
    for node in main.find_all(['h1','h2','h3','h4','p'] + (['li'] if include_lists else [])):
        if node.find_parent(['table','blockquote']): continue
        if include_lists and node.find_parent('li'): continue
        text=node.get_text('',strip=True).replace('\u3000','').strip()
        if text and not text.startswith(('此作品在','此清朝作品','此西汉作品','此頁面','此页面','取自“','检索自“')):
            blocks.append({'type':node.name,'text':text})
    unique_links = {}
    for link in links:
        unique_links.setdefault(link['title'], link)
    return {'title':title,'url':url,'resolved_url':actual,'revision':rev.group(1) if rev else None,'fetched_at':datetime.now(timezone.utc).isoformat(),'status':'source_cached_unreviewed','blocks':blocks,'links':list(unique_links.values()),'text_sha256':hashlib.sha256('\n'.join(x['text'] for x in blocks).encode()).hexdigest()}

def save(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--books',nargs='+',choices=BOOKS,default=list(BOOKS));parser.add_argument('--indexes-only',action='store_true');args=parser.parse_args()
    for slug in args.books:
        title=BOOKS[slug];dest=ROOT/'sources'/slug/'wikisource';index=download(title);save(dest/'index.json',index)
        print(slug, 'index',len(index['links']),'linked pages',flush=True)
        if args.indexes_only:continue
        jobs=[]
        for item in index['links']:
            if any(x in item['title'] for x in ['全覽','全览','版本信息']):continue
            key=hashlib.sha256(item['title'].encode()).hexdigest()[:16];path=dest/'pages'/(key+'.json')
            if path.exists():continue
            jobs.append((item['title'],path))
        errors=[]
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending={pool.submit(download,t,slug == 'xiaochuang'):(t,p) for t,p in jobs}
            for i,f in enumerate(as_completed(pending),1):
                t,p=pending[f]
                try:save(p,f.result())
                except Exception as e:errors.append({'title':t,'error':str(e)})
                if i%10==0 or i==len(jobs):print(slug,i,'/',len(jobs),'errors',len(errors),flush=True)
                time.sleep(.2)
        save(dest/'fetch-report.json',{'book':title,'cached_pages':len(list((dest/'pages').glob('*.json'))),'errors':errors,'translation_status':'not_completed_by_fetch','policy':'Original source cache only; existing edited source files and completion flags are untouched.'})
        if errors:raise RuntimeError(str(errors))

if __name__=='__main__':main()
