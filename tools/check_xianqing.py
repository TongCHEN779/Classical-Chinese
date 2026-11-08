#!/usr/bin/env python3
"""Audit 闲情偶寄卷二至卷六 (Wikisource): coverage, sentence alignment, notes, rendered pages."""
import json
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
import build
import prepare_xianqing as px

flat = lambda t: re.sub(r'[\s/]', '', t)


def main():
    pages = px.load()
    prog = json.loads((ROOT / 'sources/xianqing/progress.json').read_text())
    tot = {'entries': 0, 'paragraphs': 0, 'pairs': 0, 'notes': 0}
    for v, (vt, parts) in px.VOLUMES.items():
        secs = build.parse_poems(sorted((ROOT / 'src/xianqing' / f'juan{v:02d}').glob('*.txt')))
        want = []
        for key, pname, chapters in parts:
            if key == '種植部':
                want.append((f'{pname}·小序', [b['text'].strip() for b in pages['閑情偶寄/種植部']['blocks'] if b['type'] == 'p']))
            for ch in chapters:
                d = pages[f'閑情偶寄/{key}/{ch}']
                label = None
                for b in d['blocks'][:2]:
                    c = px.clean(b['text'])
                    if re.fullmatch(r'.{1,5}第[一二三四五六]', c): label = c; break
                if label is None:
                    idx = json.loads((ROOT / 'sources/xianqing/wikisource/index.json').read_text())
                    label = next(l['label'] for l in idx['links'] if l['title'] == d['title'])
                for t, ps in px.chapter_sections(d):
                    want.append((f'{label}·{t}', ps))
        assert [s['title'] for s in secs] == [w[0] for w in want], (v, 'section titles')
        for s, (_t, ps) in zip(secs, want):
            got = [c['o'] for c in s['chunks']]
            assert [flat(x) for x in got] == [flat(re.sub('[\ue000-\uf8ff]', '〔缺字〕', re.sub(r'\s*\n\s*', '/', x))) for x in ps], (v, s['title'], 'text')
            assert s['intro'] and len(s['intro']) == 1, (v, s['title'], 'intro')
            seen = set()
            for c in s['chunks']:
                assert c['t'] is not None and c['notes'], (v, s['title'], c['o'][:20])
                assert len(c['t'].split('¦')) == len(build._frag_groups(build.split_sents(c['o']))), (v, s['title'], c['o'][:20])
                for n in c['notes']:
                    term = n.split('：', 1)[0]
                    assert term == '校' or term not in seen, (v, s['title'], term, 'repeat')
                    seen.add(term)
                tot['paragraphs'] += 1; tot['notes'] += len(c['notes'])
                tot['pairs'] += len(build.split_pairs(c['o'], c['t']))
        tot['entries'] += len(secs)
        path = ROOT / 'xianqing' / f'juan{v:02d}.html'
        soup = BeautifulSoup(path.read_text(), 'html.parser')
        nb = 0
        for b in soup.select('button.note-btn'):
            m = re.search(r'注释（(\d+)）', b.get_text())
            if not m: continue
            t = soup.find(id=b['aria-controls'])
            assert t.has_attr('hidden') and int(m[1]) == len(t.find_all('li', recursive=False)), (v, 'button')
            nb += int(m[1])
        assert nb == sum(len(c['notes']) for s in secs for c in s['chunks']), (v, 'rendered notes')
    print('OK:', tot)


if __name__ == '__main__':
    main()
