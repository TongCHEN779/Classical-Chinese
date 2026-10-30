#!/usr/bin/env python3
"""Audit the 资治通鉴 catalogue (目录 only): 294 volumes, year chain 前403—959, appendix, rendered index."""
import hashlib
import json
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    cat = json.loads((ROOT / 'sources/zizhitongjian/catalog.json').read_text())
    idx = json.loads((ROOT / 'sources/zizhitongjian/index.json').read_text())
    raw = (ROOT / cat['source']['snapshot'].replace('index.json', 'index.html.snapshot')).read_text()
    assert hashlib.sha256(raw.encode()).hexdigest() == idx['raw_sha256']
    assert idx['revision'] == cat['source']['revision']
    vols = cat['volumes']
    assert [v['n'] for v in vols] == list(range(1, 295)) and cat['volumes_total'] == 294
    assert [v['slug'] for v in vols] == [f'juan{i:03}' for i in range(1, 295)]
    # 纪 groups: contiguous, cover everything once, volume names count up inside each 纪
    assert sum(j['volumes'] for j in cat['ji']) == 294 and len(cat['ji']) == 16
    pos = 1
    for j in cat['ji']:
        assert j['first'] == pos and j['last'] == pos + j['volumes'] - 1, j
        members = [v for v in vols if j['first'] <= v['n'] <= j['last']]
        assert all(v['ji'] == j['name'] for v in members)
        assert members[-1]['name'].startswith(j['name']) and len(members) == j['volumes']
        pos = j['last'] + 1
    # year chain: starts 前403 (戊寅), ends 959 (己未); each volume starts in or right after the previous year
    assert vols[0]['start_year'] == -403 and vols[0]['start_gz'] == '戊寅'
    assert vols[-1]['end_year'] == 959 and vols[-1]['end_gz'] == '己未'
    prev = None
    for v in vols:
        assert v['start_year'] <= v['end_year'] and v['start_year'] != 0 and v['end_year'] != 0, v['n']
        assert v['url'].endswith(f'%E5%8D%B7{v["n"]:03}') and v['revision'].isdigit() and v['status'] == 'catalog_only'
        if prev:
            nxt = 1 if prev['end_year'] == -1 else prev['end_year'] + 1
            assert v['start_year'] in (prev['end_year'], nxt), v['n']
        prev = v
    assert len(cat['appendix']) == 12 and all(a['label'] and a['url'] for a in cat['appendix'])
    # rendered index: 294 + 12 to-do cells in catalogue order, grouped by 纪
    html = BeautifulSoup((ROOT / 'zizhitongjian/index.html').read_text(), 'html.parser')
    cells = [li.get_text(' ', strip=True) for li in html.select('li.todo')]
    assert len(cells) == 294 + 12, len(cells)
    assert all('待整理' in c for c in cells)
    groups = [h.get_text(strip=True) for h in html.select('h3.grp')]
    assert len(groups) == 17, groups
    assert not (ROOT / 'src/zizhitongjian').exists(), 'catalogue stage: no volume text should exist yet'
    corrected = [v['n'] for v in vols if v['chain_corrected']]
    derived = [v['n'] for v in vols if v['derived_from_body']]
    print(f'OK: 294 volumes, 16 ji, 前403—959, {len(cat["appendix"])} appendix items; '
          f'{len(derived)} years from body headings, {len(corrected)} chain-corrected {corrected}')


if __name__ == '__main__':
    main()
