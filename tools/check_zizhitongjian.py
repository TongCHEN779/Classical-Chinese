#!/usr/bin/env python3
"""Audit 资治通鉴: the 294-volume catalogue (year chain 前403—959), the finished volumes 已整理各卷 and the appendix pages; the other volumes are 待整理."""
import hashlib
import json
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    import prepare_works as prep
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
    assert len(cat['appendix']) == 7 and all(a['label'] and a['url'] for a in cat['appendix'])
    # rendered index: the 294 volumes are 待整理 cells, grouped by 纪; the appendix pages are real pages
    html = BeautifulSoup((ROOT / 'zizhitongjian/index.html').read_text(), 'html.parser')
    cells = [li.get_text(' ', strip=True) for li in html.select('li.todo')]
    assert len(cells) == 294 - len(prep.ZTJJ_DONE), len(cells)
    assert all('待整理' in c for c in cells)
    groups = [h.get_text(strip=True) for h in html.select('h3.grp')]
    assert len(groups) == 17, groups
    assert sorted(x.name for x in (ROOT / 'src/zizhitongjian').iterdir()) == [f'fulu{k:02}' for k in range(1, 15)] + [f'juan{k:03}' for k in prep.ZTJJ_DONE], 'only the appendix and 已整理各卷 exist'
    audit_volumes()
    pages, sents, notes = audit_appendix()
    corrected = [v['n'] for v in vols if v['chain_corrected']]
    derived = [v['n'] for v in vols if v['derived_from_body']]
    print(f'OK: 294 volumes, 16 ji, 前403—959; appendix {pages} pages, {sents} sentence pairs, {notes} notes; '
          f'{len(derived)} years from body headings, {len(corrected)} chain-corrected {corrected}')


def audit_volumes():
    """已整理各卷（周纪、秦纪）：来源哈希、原文逐字（去标点）覆盖、句对、注释锚点与渲染。"""
    import build
    import prepare_works as prep
    from prepare_zizhitongjian_fulu import strip_p
    progress = json.loads((ROOT / 'sources/zizhitongjian/progress_juan.json').read_text(encoding='utf8'))
    want_pages = prep.pages('zizhitongjian')
    assert [p['slug'] for p in progress['pages']] == [w[0] for w in want_pages]
    for p, (slug, label, srcname, want) in zip(progress['pages'], want_pages):
        src = prep.src('zizhitongjian', srcname)
        assert src['revision'] == p['source']['revision'] and src['text_sha256'] == p['source']['text_sha256'], slug
        got = build.parse_poems(sorted((ROOT / 'src/zizhitongjian' / slug).glob('*.txt')))
        assert [w['title'] for w in want] == [g['title'] for g in got], (slug, 'sections')
        pairs = []
        for w, g in zip(want, got):
            assert strip_p(''.join(w['paras'])) == strip_p(''.join(c['o'] for c in g['chunks'])), (slug, g['title'], 'coverage')
            assert bool(g['intro']) == w['intro'], (slug, g['title'], '题解')
            seen = set()
            for c in g['chunks']:
                assert c['t'] and len(c['t'].split('¦')) == len(build._frag_groups(build.split_sents(c['o']))), (slug, g['title'], c['o'][:20])
                assert c['notes'] or g['title'] == '校刊记', (slug, g['title'], c['o'][:20])
                for n in c['notes']:
                    term = n.split('：', 1)[0]
                    assert term in c['o'] and (term not in seen or g['title'] == '校刊记'), (slug, g['title'], n)
                    seen.add(term)
                pairs.extend(build.split_pairs(c['o'], c['t']))
        html = BeautifulSoup((ROOT / 'zizhitongjian' / (slug + '.html')).read_text(), 'html.parser')
        assert [(n.get_text(), n['data-t']) for n in html.select('.s[data-t]')] == [(o.replace('/', ''), t) for o, t in pairs], (slug, 'rendered pairs')


def audit_appendix():
    """Each appendix page: source hash, coverage (punctuation aside), sentence alignment, notes, rendered HTML."""
    import build
    from prepare_zizhitongjian_fulu import load, sections, strip_p
    progress = json.loads((ROOT / 'sources/zizhitongjian/progress.json').read_text(encoding='utf8'))
    assert [p['slug'] for p in progress['pages']] == [f'fulu{k:02}' for k in range(1, 15)]
    npairs = nnotes = 0
    for p in progress['pages']:
        src = load(p['slug'])
        assert src['revision'] == p['source']['revision'] and src['text_sha256'] == p['source']['text_sha256'], p['slug']
        want = sections(p['slug'])
        got = build.parse_poems(sorted((ROOT / 'src/zizhitongjian' / p['slug']).glob('*.txt')))
        assert [w['title'] for w in want] == [g['title'] for g in got], (p['slug'], 'sections')
        pairs = []
        for w, g in zip(want, got):
            assert strip_p(''.join(w['paras'])) == strip_p(''.join(c['o'] for c in g['chunks'])), (p['slug'], g['title'], 'coverage')
            assert bool(g['intro']) == w['intro'], (p['slug'], g['title'], '题解')
            for c in g['chunks']:
                groups = build._frag_groups(build.split_sents(c['o']))
                assert c['t'] and len(c['t'].split('¦')) == len(groups), (p['slug'], g['title'], c['o'][:20])
                assert c['notes'] or g['title'] == '校记', (p['slug'], g['title'], c['o'][:20])
                assert all(n.split('：', 1)[0] in c['o'] for n in c['notes']), (p['slug'], g['title'], c['notes'])
                pairs.extend(build.split_pairs(c['o'], c['t']))
                nnotes += len(c['notes'])
        html = BeautifulSoup((ROOT / 'zizhitongjian' / (p['slug'] + '.html')).read_text(), 'html.parser')
        assert [(n.get_text(), n['data-t']) for n in html.select('.s[data-t]')] == [(o.replace('/', ''), t) for o, t in pairs], (p['slug'], 'rendered pairs')
        npairs += len(pairs)
    return len(progress['pages']), npairs, nnotes


if __name__ == '__main__':
    main()
