#!/usr/bin/env python3
"""Cache Shiliju edition 战国策 pages (variant JSON + raw HTML) and register their units in progress.json.

  python3 tools/cache_zhanguoce.py zhao01 zhao02 ...
"""
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from fetch_wikisource import download, save
from zhenglun_changyan_common import source_parts, digest

PROGRESS = ROOT / 'sources/zhanguoce/progress.json'
BASE = '戰國策_(士禮居叢書本)'
STATES = {'zhao': ('趙', '赵策'), 'wei': ('魏', '魏策'), 'han': ('韓', '韩策'), 'yan': ('燕', '燕策')}
NUM = '一二三四五六七八九十'
ORDER = ([f'xu{i:02}' for i in range(1, 7)] + ['dongzhou', 'xizhou'] + [f'qin{i:02}' for i in range(1, 6)] + [f'qi{i:02}' for i in range(1, 7)]
         + [f'chu{i:02}' for i in range(1, 5)] + [f'zhao{i:02}' for i in range(1, 5)] + [f'wei{i:02}' for i in range(1, 5)]
         + [f'han{i:02}' for i in range(1, 4)] + [f'yan{i:02}' for i in range(1, 4)] + [f'fu{i:02}' for i in range(1, 7)])
HEADERS = {'User-Agent': 'ClassicalChineseLibrary/1.0 (public-domain text research)'}


def raw_html(title):
    url = 'https://zh.wikisource.org/wiki/' + quote(title, safe='/')
    for attempt in range(5):
        try:
            return urlopen(Request(url, headers=HEADERS), timeout=60).read().decode('utf8')
        except Exception:
            if attempt == 4:
                raise
            time.sleep(3 * 2 ** attempt)


def reference_notes(html):
    soup = BeautifulSoup(html, 'html.parser')
    main = soup.select_one('#mw-content-text .mw-parser-output')
    texts = {li['id']: li.get_text(' ', strip=True).lstrip('↑ ').strip() for li in main.select('ol.references li[id]')}
    out = []
    tags = [h for h in main.select('h2, h3') if h.get_text(strip=True) != '注释']
    kind = 'h2' if any(h.name == 'h2' for h in tags) else 'h3'
    h2s = [h for h in tags if h.name == kind]
    for ref in main.select('sup.reference'):
        note_id = ref.select_one('a')['href'].lstrip('#')
        h2 = ref.find_parent(kind) or ref.find_previous(kind)
        out.append({'id': note_id, 'heading': h2.get_text(strip=True) if h2 else '', 'unit_index': h2s.index(h2) if h2 in h2s else None, 'text': texts[note_id]})
    return out


def cache(slug):
    state, n = re.match(r'([a-z]+)(\d+)', slug).groups()
    zh, label = STATES[state]
    title = f'{BASE}/{zh}/{NUM[int(n) - 1]}'
    data = download(title)
    html = raw_html(title)
    raw_path = ROOT / 'sources/zhanguoce/wikisource' / f'{slug}.html.snapshot'
    raw_path.write_text(html)
    data['raw_snapshot'] = f'sources/zhanguoce/wikisource/{slug}.html.snapshot'
    data['raw_sha256'] = digest(raw_path.read_text())
    data['source_reference_notes'] = reference_notes(html)
    path = ROOT / 'sources/zhanguoce/wikisource' / f'{slug}.json'
    save(path, data)
    return title, label, data, path


def register(slug, label, title, data):
    blocks = data['blocks']
    page = {'slug': slug, 'title': f'{label}{NUM[int(re.search(r"\d+", slug).group()) - 1]}', 'kind': 'body',
            'source': {'url': data['url'], 'revision': data['revision'], 'snapshot': f'sources/zhanguoce/wikisource/{slug}.json'},
            'preface_block_indices': [], 'units': [], 'annotation_status': 'pending'}
    unit_type = 'h2' if any(b['type'] == 'h2' and b['text'] != '注释' for b in blocks) else 'h3'
    page['unit_heading_type'] = unit_type
    refs = [i for i, b in enumerate(blocks) if b['type'] == 'h2' and b['text'] == '注释']
    if refs:
        page['source_reference_heading_indices'] = refs
    cur = None
    for i, b in enumerate(blocks):
        if b['type'] in ('h2', 'h3'):
            if b['text'] == '注释':
                cur = None
                continue
            cur = {'id': f'{len(page["units"]) + 1:03}', 'title': b['text'], 'source_block_indices': [], 'status': 'pending'}
            page['units'].append(cur)
        elif b['type'] == 'p':
            if cur is None:
                page['preface_block_indices'].append(i)
            else:
                cur['source_block_indices'].append(i)
        else:
            raise ValueError((slug, i, b['type']))
    # headings with no text at all (e.g. a bare 斠勘 label) are not units
    empty = [u for u in page['units'] if not u['source_block_indices']]
    if empty:
        titles = {u['title'] for u in empty}
        page['empty_heading_indices'] = [i for i, b in enumerate(blocks) if b['type'] == unit_type and b['text'] in titles
                                         and not any(blocks[j]['type'] == 'p' for j in range(i + 1, min(i + 2, len(blocks))))]
        page['units'] = [u for u in page['units'] if u['source_block_indices']]
        for k, u in enumerate(page['units'], 1):
            u['id'] = f'{k:03}'
    for u in page['units']:
        raw = '\n'.join(blocks[i]['text'] for i in u['source_block_indices'])
        main, notes, breaks = source_parts(raw)
        u.update(raw_sha256=digest(raw), main_sha256=digest(main), source_notes=notes, format_breaks=breaks)
    # attach the page's footnotes to the unit whose heading or text carries the reference marker
    heads = [u['title'] for u in page['units']]
    for note in data['source_reference_notes']:
        assert note['unit_index'] is not None and note['unit_index'] < len(page['units']), (slug, note['heading'])
        page['units'][note['unit_index']].setdefault('source_reference_notes', []).append(note['text'])
    if page['preface_block_indices']:
        page['preface_note_count'] = len(page['preface_block_indices'])
    return page


def main():
    prog = json.loads(PROGRESS.read_text())
    for slug in sys.argv[1:]:
        title, label, data, path = cache(slug)
        page = register(slug, label, title, data)
        print(slug, title, 'revision', data['revision'], 'blocks', len(data['blocks']), 'units', len(page['units']),
              'preface', page['preface_block_indices'], 'refs', len(data['source_reference_notes']))
        prog['pages'] = [p for p in prog['pages'] if p['slug'] != slug]
        # insert before the first fu page, after the last body page
        prog['pages'].append(page)
        prog['pages'].sort(key=lambda p: ORDER.index(p['slug']))
        time.sleep(1)
    PROGRESS.write_text(json.dumps(prog, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
