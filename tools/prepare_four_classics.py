#!/usr/bin/env python3
"""Fetch four public-domain Wikisource editions, then prepare annotated reading texts."""
import argparse
import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from fetch_wikisource import ROOT, download as download_index, save
from urllib.request import Request, urlopen
from urllib.parse import quote
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import time
import threading
FETCH_LOCK = threading.Lock()
LAST_FETCH = 0.0

def download(title):
    url = "https://zh.wikisource.org/zh-hans/" + quote(title, safe="/")
    for attempt in range(6):
        try:
            global LAST_FETCH
            with FETCH_LOCK:
                time.sleep(max(0, 1.1 - (time.monotonic() - LAST_FETCH)))
                LAST_FETCH = time.monotonic()
            with urlopen(Request(url, headers={"User-Agent":"ClassicalChineseLibrary/1.0"}), timeout=45) as r:
                body, actual = r.read().decode("utf8"), r.url
            break
        except Exception:
            if attempt == 5: raise
            time.sleep(5 * 2 ** attempt)
    soup = BeautifulSoup(body, "html.parser")
    main = soup.select_one("#mw-content-text .mw-parser-output")
    rev = soup.select_one("a[href*=\"oldid=\"]")
    revision = re.search(r"oldid=(\d+)", rev["href"]).group(1) if rev else None
    display_title = ''
    for cell in main.select('table th, table td'):
        label = cell.get_text(' ', strip=True)
        if re.match(r'^第[一二三四五六七八九十百零〇0-9]+[回本]', label) and len(label) < 100:
            display_title = label
    # Header tables are navigation; blockquotes and poem containers are literary text.
    for node in main.select(".mw-editsection, .noprint, .ws-noexport, .navigation-not-searchable, .licenseContainer, .licensetpl, #toc, .toc, .header-container, .navbox, .wst-header, .catlinks, sup.reference"):
        node.decompose()
    blocks=[]
    for node in main.find_all(["h1","h2","h3","h4","p","dl"]):
        if node.find_parent(["table","dl"]): continue
        for br in node.find_all("br"): br.replace_with("\n")
        text=node.get_text("",strip=False).replace("\u3000", "").strip()
        if text and not text.startswith(("此作品在","此清朝作品","此明朝作品","此元朝作品","此頁面","此页面","取自“","检索自“")):
            blocks.append({"type":node.name,"text":text})
    return {"title":title,"url":url,"resolved_url":actual,"revision":revision,"fetched_at":datetime.now(timezone.utc).isoformat(),"status":"source_cached_unreviewed","extractor":"four-classics-v2","display_title":display_title,"blocks":blocks,"text_sha256":hashlib.sha256("\n".join(b["text"] for b in blocks).encode()).hexdigest()}


BOOKS = {'xixiangji': ('西廂記', 5), 'xiyouji': ('西遊記', 100),
         'shuihuzhuan': ('水滸傳_(120回本)', 120), 'sanguoyanyi': ('三國演義', 120)}

def fetch():
    jobs = []
    for slug, (title, count) in BOOKS.items():
        dest = ROOT / 'sources' / slug / 'wikisource'
        index_path = dest / 'index.json'
        if not index_path.exists() or json.loads(index_path.read_text())['title'] != title:
            save(index_path, download_index(title))
        index = json.loads(index_path.read_text())
        links = [x for x in index['links'] if re.search(r'/第[0-9]+[回本]$', x['title'])]
        if len(links) != count:
            raise ValueError((slug, len(links), count, index['links'][:5]))
        links += [x for x in index['links'] if x['title'].split('/')[-1] in ('序','引首','附錄','凡例','讀《三國志》法')]
        for link in links:
            key = hashlib.sha256(link['title'].encode()).hexdigest()[:16]
            path = dest / 'pages' / (key + '.json')
            if not path.exists() or json.loads(path.read_text()).get('extractor') != 'four-classics-v2': jobs.append((slug, link['title'], path))
    errors = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(download, t): (s,t,p) for s,t,p in jobs}
        for n, f in enumerate(as_completed(futures), 1):
            s,t,p = futures[f]
            try: save(p, f.result())
            except Exception as e: errors.append({'book':s,'title':t,'error':str(e)})
            if n % 20 == 0 or n == len(jobs): print(n, '/',len(jobs),'errors',len(errors),flush=True)
    save(ROOT/'sources/four-classics-fetch-report.json', {'errors': errors, 'requested_pages':len(jobs)})
    if errors: raise RuntimeError(errors)



def normalize(text):
    """Ignore display whitespace and the reading format's explicit verse line breaks."""
    return re.sub(r'[\s/]', '', text)


def prepare():
    from four_classics_notes import META, glossary
    for slug, (wiki_title, count) in BOOKS.items():
        dest = ROOT / 'sources' / slug
        meta = META[slug]
        cache = {d['title']:d for p in (dest/'wikisource/pages').glob('*.json')
                 for d in [json.loads(p.read_text())]}
        index = json.loads((dest/'wikisource/index.json').read_text())
        chapter_links = [x for x in index['links'] if re.search(r'/第[0-9]+[回本]$',x['title'])]
        assert len(chapter_links) == count
        front_links = [x for x in index['links'] if x['title'].split('/')[-1] in ('序','引首','凡例','讀《三國志》法')]
        back_links = [x for x in index['links'] if x['title'].endswith('/附錄')] if slug != 'xiyouji' else []  # 附錄 duplicates 第九回 verbatim
        pages = []
        intro_lines = ['# 全书题解'] + ['题解：'+heading+'。'+text for heading,text in meta['essays']]
        target = ROOT/'src'/slug/'tijie'/'01.txt'
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text('\n'.join(intro_lines)+'\n',encoding='utf8')
        pages.append({'slug':'tijie','title':'全书题解','kind':'editorial','paragraphs':0,'notes':0,'essays':len(meta['essays'])})
        terms = glossary(slug)
        used_terms = set()
        for item in front_links + chapter_links + back_links:
            source = cache[item['title']]
            assert source.get('extractor') == 'four-classics-v2', source['title']
            assert source['revision'] and source['blocks']
            assert source['text_sha256'] == hashlib.sha256('\n'.join(b['text'] for b in source['blocks']).encode()).hexdigest()
            match = re.search(r'/第([0-9]+)[回本]$',source['title'])
            n = int(match.group(1)) if match else None
            page_slug = f'{n:03d}' if n else {'序':'xu','引首':'yinshou','凡例':'fanli','讀《三國志》法':'dufa','附錄':'fulu'}[source['title'].split('/')[-1]]
            title = source.get('display_title') or item['label']
            # display_title may come from a prev/next header cell; keep it only if it is this page's own label
            if source.get('display_title') and not re.sub(r'\s','',source['display_title']).startswith(re.sub(r'\s','',item['label'])): title = item['label']
            if slug == 'xixiangji':
                part_titles = ['张君瑞闹道场','崔莺莺夜听琴','张君瑞害相思','草桥店梦莺莺','张君瑞庆团圆']
                title = item['label'] + ' ' + part_titles[n-1]
            lines = ['# '+title]
            if slug == 'xixiangji': lines += ['题解：'+meta['part_intros'][n-1]]
            if not n:
                lines += ['题解：本页为所选维基文库版本的原有附属文字，作者立场及判断属于原文；与本网站编者自撰的全书题解分开阅读。']
            if n == 1 and slug == 'sanguoyanyi':
                # This poem is printed on the main work page rather than chapter 1.
                lines += ['题解：卷首《临江仙》另见“卷首词”页；原站将此词置于全书目录前，本回正文不重复插入。']
            seen = set()
            paragraph_count = note_count = 0
            raw_originals, emitted_originals = [], []
            heading_count = 0
            for block in source['blocks']:
                text = block['text'].strip()
                if block['type'].startswith('h'):
                    heading_count += 1
                    lines += ['', '# '+text]
                    continue
                raw_originals.append(text)
                # Explicit verse line breaks render as <br>; never drop blockquotes/dl poetry.
                text = re.sub(r'\s*\n\s*','/',text).strip('/')
                if slug == 'xixiangji':
                    chunks = re.findall(r'(?:【[^】]+】)+[^【]*|^[^【]+',text)
                else:
                    chunks = [text]
                for chunk in chunks:
                    chunk = chunk.strip()
                    if not chunk: continue
                    paragraph_count += 1
                    emitted_originals.append(chunk)
                    lines += ['原：'+chunk]
                    matches = []
                    occupied = []
                    for term in sorted(terms, key=lambda t:(-len(t),t)):
                        if term in seen: continue
                        found = None
                        for m in re.finditer(re.escape(term),chunk):
                            if term == '太公' and m.start() and chunk[m.start()-1] == '姜': continue
                            if term == '司马' and re.match(r'[懿师昭孚炎攸望亮]',chunk[m.end():]): continue
                            if any(m.start() < end and m.end() > start for start,end in occupied): continue
                            found = m; break
                        if found:
                            occupied.append(found.span())
                            matches.append((found.start(),term))
                    for _,term in sorted(matches):
                        lines += ['注：'+term+'：'+terms[term]]
                        seen.add(term);used_terms.add(term);note_count += 1
                    lines.append('')
            assert normalize(''.join(raw_originals)) == normalize(''.join(emitted_originals)),source['title']
            target = ROOT/'src'/slug/page_slug/'01.txt'
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text('\n'.join(lines)+'\n',encoding='utf8')
            pages.append({'slug':page_slug,'title':title,'kind':'chapter' if n else 'front_or_back_matter',
                          'number':n,'paragraphs':paragraph_count,'characters':len(normalize(''.join(raw_originals))),
                          'headings':heading_count,'notes':note_count,
                          'source':{k:source[k] for k in ['title','url','revision','text_sha256']}})
        # Retain the novel's opening lyric, with actual line breaks and attribution.
        if slug == 'sanguoyanyi':
            poem = '滚滚长江东逝水，浪花淘尽英雄。是非成败转头空。青山依旧在，几度夕阳红。/白发渔樵江渚上，惯看秋月春风。一壶浊酒喜相逢。古今多少事，都付笑谈中。'
            target = ROOT/'src'/slug/'juanshou'/'01.txt';target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text('# 卷首词｜临江仙·杨慎\n题解：此词据原站主页所列《临江仙》收录，另立一页以保留其位于全书目录前的层次。原站正文块将词牌、作者与词句连写，此处拆分署名，并依词调补标句读、分片。\n原：'+poem+'\n注：临江仙：词牌名，此首为明代杨慎所作，后被置于通行本《三国演义》卷首。\n注：渚：水中的小块陆地。\n注：江渚：江中小洲或江边水际。\n',encoding='utf8')
            pages.insert(1,{'slug':'juanshou','title':'卷首词｜临江仙·杨慎','kind':'opening_lyric','paragraphs':1,'notes':3,
                            'source':{k:index[k] for k in ['title','url','revision','text_sha256']}})
            raw = next(b['text'] for b in index['blocks'] if b['text'].startswith('临江仙'))
            assert re.sub(r'[^\w]','',(raw[len('临江仙杨慎'):])) == re.sub(r'[^\w]','',poem)
        progress = {'book':meta['title'],'date':'2026-10-27','status':'full_text_with_basic_annotations',
                    'chapter_count':count,'translation_status':'not_requested','annotation_status':'basic_glossary',
                    'annotation_policy':'Editor-authored basic glossary, attached at the first matching occurrence per page; not an exhaustive contextual commentary. Some chapters may have no new rare-word explanations.',
                    'scan_collation_status':'not_done','unique_glossary_terms':len(used_terms),'pages':pages}
        save(dest/'progress.json',progress)
        save(dest/'glossary.json',{t:terms[t] for t in sorted(used_terms)})
        total_notes=sum(p['notes'] for p in pages)
        total_paras=sum(p['paragraphs'] for p in pages)
        description = f'''# {meta['title']}：原文、题解与基础注释

- 底本：[维基文库]({index['url']})，{count}{meta['unit']}正文全部收录，卷前卷后材料以进度文件为准。
- {meta['intro']}
- 全书题解为编者自撰；基础词条从 `tools/four_classics_notes.py` 维护，按各页首次出现位置附于原文段后，同页不反复加注。已使用{len(used_terms)}种词条，合计{total_notes}条随段注释、{total_paras}个原文段。
- 本次不配白话译文。基础注释覆盖常见阅读障碍，不冒充逐字穷尽的全注本；尤其多义词仍须联系上下文阅读。
- `wikisource/index.json`、`wikisource/pages/` 保留原文快照、URL、修订号、提取时间及正文SHA-256。段落与诗赞均保存，诗词换行在阅读源稿中以 `/` 标示；《西厢记》长段另按曲牌、科白拆段。
- 正文据原站简体显示版，未据刊本影印逐字校勘；不使用本地现代注译PDF的释文，不擅自补缺改字。
- `progress.json` 记录实际页数、篇章、词条计数和基础注释状态；原文缓存完成与注释深度分别标记。
- 重抓取：`python3 tools/prepare_four_classics.py --fetch`。重生成：`python3 tools/prepare_four_classics.py --prepare`。新增人工逐段校注后，不应未经合并直接重生成覆盖。
'''
        (dest/'README.md').write_text(description,encoding='utf8')
        print(slug,count,'chapters',len(pages),'pages',total_paras,'paragraphs',total_notes,'notes',flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    if args.fetch: fetch()
    if args.prepare: prepare()
