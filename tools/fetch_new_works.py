#!/usr/bin/env python3
"""缓存关汉卿杂剧、赵氏孤儿、倩女离魂、墙头马上、声律启蒙、林兰香的维基文库原文（含 h2/h3、p、dl 块）。

  python3 tools/fetch_new_works.py [slug ...]
"""
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from catalog_zizhitongjian import API, get

# slug -> [(页 slug, 维基文库标题)]
GHQ = [('douee', '感天动地窦娥冤'), ('luzhailang', '包待制智斬魯齋郎'), ('jiufengchen', '趙盼兒風月救風塵'),
       ('wangjiangting', '望江亭中秋切鱠'), ('hudiemeng', '包待制三勘蝴蝶夢'), ('jinxianchi', '杜蕊娘智賞金線池'),
       ('xietianxiang', '錢大尹智寵謝天香'), ('yujingtai', '溫太真玉鏡臺'), ('danbianduosuo', '尉遲恭單鞭奪槊'),
       ('danfenghui', '關大王獨赴單刀會'), ('feiyimeng', '錢大尹智勘緋衣夢'), ('wuhouyan', '劉夫人慶賞五侯宴'),
       ('kucunxiao', '鄧夫人苦痛哭存孝'), ('peidu', '山神廟裴度還帶'), ('chenmu', '狀元堂陳母教子'),
       ('xishumeng', '關張雙赴西蜀夢'), ('baiyueting', '閨怨佳人拜月亭'), ('tiaofengyue', '詐妮子調風月')]
SINGLE = {'zhaoshigu': '冤報冤趙氏孤兒', 'qiannulihun': '迷青瑣倩女離魂', 'qiangtoumashang': '裴少俊牆頭馬上',
          'shenglvqimeng': '聲律啓蒙', 'lihunji': '離魂記', 'luoshenfu': '洛神賦'}
LAST = [0.0]


def to_hans(lines):
    """<pre> 里的文字不过简繁转换：把这些行交给维基文库的 zh-hans 转换器（逐行成段）。"""
    if not lines:
        return []
    for attempt in range(5):
        try:
            j = json.loads(get(API, {'action': 'parse', 'text': '\n\n'.join(lines), 'contentmodel': 'wikitext', 'prop': 'text',
                                     'variant': 'zh-hans', 'disablelimitreport': 1, 'format': 'json', 'formatversion': 2}))
            break
        except Exception:
            if attempt == 4:
                raise
            time.sleep(4 * 2 ** attempt)
    out = [p_.get_text('', strip=True) for p_ in BeautifulSoup(j['parse']['text'], 'html.parser').select('.mw-parser-output > p')]
    assert len(out) == len(lines), (len(out), len(lines))
    return out


def fetch(title):
    wait = 1.2 - (time.monotonic() - LAST[0])
    if wait > 0:
        time.sleep(wait)
    for attempt in range(5):
        try:
            LAST[0] = time.monotonic()
            j = json.loads(get(API, {'action': 'parse', 'page': title, 'prop': 'text|revid', 'variant': 'zh-hans', 'redirects': 1,
                                     'disableeditsection': 1, 'format': 'json', 'formatversion': 2}))
            break
        except Exception:
            if attempt == 4:
                raise
            time.sleep(4 * 2 ** attempt)
    if 'parse' not in j:
        raise SystemExit(f'missing page: {title} {j.get("error")}')
    p = j['parse']
    main = BeautifulSoup(p['text'], 'html.parser').select_one('.mw-parser-output')
    for n in main.select('style, script, .noprint, .ws-noexport, .navigation-not-searchable, .licenseContainer, .licensetpl, #toc, .toc, '
                         '.header-container, .navbox, .wst-header, .catlinks, sup.reference, table.header, .mw-editsection'):
        n.decompose()
    blocks = []
    for node in main.find_all(['h2', 'h3', 'h4', 'p', 'dd', 'li', 'pre']):
        if node.find_parent(['table', 'li', 'pre']) or node.find(['p', 'dd', 'dl', 'li']):
            continue
        for br in node.find_all('br'):
            br.replace_with('\n')
        text = node.get_text('', strip=False).replace('　', '').strip()
        text = re.sub(r'[ \t]+', ' ', re.sub(r'\n\s*\n+', '\n', text)).strip()
        if not text or text.startswith(('此作品在', '此清朝作品', '此元朝作品', '此頁面', '此页面', '取自“', '检索自“', '姊妹计划')):
            continue
        blocks.append({'type': node.name, 'text': text})
    pre = [b for b in blocks if b['type'] == 'pre']
    for b, h in zip(pre, to_hans([b['text'] for b in pre])):
        b['text'] = h
    return {'title': p['title'], 'query': title, 'url': 'https://zh.wikisource.org/zh-hans/' + quote(p['title'].replace(' ', '_'), safe='/'),
            'revision': str(p['revid']), 'fetched_at': datetime.now(timezone.utc).isoformat(), 'blocks': blocks,
            'text_sha256': hashlib.sha256('\n'.join(b['text'] for b in blocks).encode()).hexdigest()}


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf8')


def main():
    want = set(sys.argv[1:])
    dest = ROOT / 'sources'
    jobs = []
    for slug, t in GHQ:
        jobs.append((dest / 'guanhanqing/wikisource' / f'{slug}.json', t))
    for slug, t in SINGLE.items():
        jobs.append((dest / slug / 'wikisource/main.json', t))
    jobs.append((dest / 'linlanxiang/wikisource/index.json', '林蘭香'))
    jobs.append((dest / 'linlanxiang/wikisource/congyu.json', '林蘭香/林蘭香叢語'))
    for k in range(1, 65):
        jobs.append((dest / 'linlanxiang/wikisource' / f'hui{k:02}.json', f'林蘭香/第{k:02}回'))
    jobs.append((dest / 'jinghuayuan/wikisource/index.json', '鏡花緣'))
    for k in range(1, 101):
        jobs.append((dest / 'jinghuayuan/wikisource' / f'hui{k:03d}.json', f'鏡花緣/第{k:03d}回'))
    for k in sorted(set(range(1, 185)) | set(range(266, 295))):
        jobs.append((dest / 'zizhitongjian/wikisource/juan' / f'juan{k:03d}.json', f'資治通鑑/卷{k:03d}'))
    for k in range(1, 9):
        jobs.append((dest / 'yanzi/wikisource' / f'juan{k:02}.json', '晏子春秋/卷' + '零一二三四五六七八'[k]))
    for path, t in jobs:
        if want and not any(w in str(path) for w in want):
            continue
        if path.exists():
            continue
        d = fetch(t)
        save(path, d)
        print(path.relative_to(dest), d['revision'], len(d['blocks']), sum(len(b['text']) for b in d['blocks']), flush=True)


if __name__ == '__main__':
    main()
