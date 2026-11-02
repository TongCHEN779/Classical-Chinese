#!/usr/bin/env python3
"""缓存维基文库《周易》各页（卦页的“易经/彖曰/象曰/文言曰”是嵌套列表，通用抓取器会丢，这里单独取）。

  python3 tools/fetch_zhouyi.py
每页存为 {title, url, revision, fetched_at, blocks, text_sha256}；blocks 为 {type, text}，
type：head（“易经：”“彖曰：”等小标题）、ul / ol（其下的条目，ol 为按爻序的条目）、p（其余段）。
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
from fetch_new_works import to_hans

HEXAGRAMS = ('乾坤屯蒙需訟師比小畜履泰否同人大有謙豫隨蠱臨觀噬嗑賁剝復无妄大畜頤大過坎離咸恒遯大壯晉明夷家人睽蹇解損益夬姤萃升困井革鼎震艮漸歸妹豐旅巽兌渙節中孚小過既濟未濟')
NAMES = ['乾', '坤', '屯', '蒙', '需', '訟', '師', '比', '小畜', '履', '泰', '否', '同人', '大有', '謙', '豫', '隨', '蠱', '臨', '觀', '噬嗑', '賁', '剝', '復', '无妄', '大畜', '頤', '大過', '坎', '離',
         '咸', '恒', '遯', '大壯', '晉', '明夷', '家人', '睽', '蹇', '解', '損', '益', '夬', '姤', '萃', '升', '困', '井', '革', '鼎', '震', '艮', '漸', '歸妹', '豐', '旅', '巽', '兌', '渙', '節', '中孚', '小過', '既濟', '未濟']
OTHERS = ['繫辭上', '繫辭下', '說卦', '序卦', '雜卦']
LAST = [0.0]


def text(n):
    return re.sub(r'\s+', '', n.get_text('', strip=True))


def fetch(title):
    wait = 1.2 - (time.monotonic() - LAST[0])
    if wait > 0:
        time.sleep(wait)
    LAST[0] = time.monotonic()
    j = json.loads(get(API, {'action': 'parse', 'page': title, 'prop': 'text|revid', 'variant': 'zh-hans', 'redirects': 1,
                             'disableeditsection': 1, 'format': 'json', 'formatversion': 2}))
    p = j['parse']
    main = BeautifulSoup(p['text'], 'html.parser').select_one('.mw-parser-output')
    for n in main.select('style, script, table, .variant-tooltip, .noprint, .ws-noexport, .navbox, .catlinks, sup.reference, .mw-editsection'):
        n.decompose()
    blocks = []
    for node in main.find_all(recursive=False):
        if node.name == 'p':
            t = text(node)
            if t and t not in ('\'', '"') and not t.startswith(('周易', '此作品')):
                blocks.append({'type': 'p', 'text': t})
        elif node.name == 'dl':
            t = text(node)
            if t:
                blocks.append({'type': 'head' if len(t) <= 15 and not re.search(r'[。，；：！？]', t) else 'p', 'text': t})
        elif node.name in ('ul', 'ol'):
            for li in node.find_all('li', recursive=False):
                head = li.find(['b', 'span'], recursive=False)
                kids = li.find_all(['ul', 'ol'], recursive=False)
                if kids:
                    h = text(head) if head else ''
                    if h:
                        blocks.append({'type': 'head', 'text': h})
                    for k in kids:
                        for x in k.find_all('li', recursive=False):
                            blocks.append({'type': k.name, 'text': text(x)})
                else:
                    blocks.append({'type': node.name, 'text': text(li)})
        elif node.name in ('h2', 'h3'):
            blocks.append({'type': 'head', 'text': text(node)})
    # <pre> 或列表里的文字不过简繁转换，这里已是 zh-hans 的结果，无需再转
    return {'title': p['title'], 'url': 'https://zh.wikisource.org/zh-hans/' + quote(p['title'].replace(' ', '_'), safe='/'),
            'revision': str(p['revid']), 'fetched_at': datetime.now(timezone.utc).isoformat(), 'blocks': blocks,
            'text_sha256': hashlib.sha256('\n'.join(b['text'] for b in blocks).encode()).hexdigest()}


def main():
    dest = ROOT / 'sources/zhouyi/wikisource'
    dest.mkdir(parents=True, exist_ok=True)
    for i, n in enumerate(NAMES + OTHERS):
        path = dest / (f'gua{i + 1:02d}.json' if i < 64 else f'zhuan{i - 63:02d}.json')
        if path.exists():
            continue
        d = fetch('周易/' + n)
        path.write_text(json.dumps(d, ensure_ascii=False, indent=1) + '\n', encoding='utf8')
        print(path.name, d['title'], d['revision'], len(d['blocks']), sum(len(b['text']) for b in d['blocks']), flush=True)


if __name__ == '__main__':
    main()
