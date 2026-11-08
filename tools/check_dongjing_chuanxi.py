#!/usr/bin/env python3
"""Audit 《东京梦华录》《传习录》: source hashes, coverage (punctuation aside), sentence alignment, notes, rendered HTML."""
import json
import sys
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
import build
import prepare_dongjing_chuanxi as prep
from prepare_zizhitongjian_fulu import strip_p

EXPECT = {'donglinghualu': {'pages': 11, 'sections': 87}, 'chuanxilu': {'pages': 9, 'sections': 346}}


def audit(book):
    progress = json.loads((ROOT / f'sources/{book}/progress.json').read_text(encoding='utf8'))
    want_pages = prep.pages(book)
    assert [p['slug'] for p in progress['pages']] == [w[0] for w in want_pages]
    npairs = nnotes = nsec = 0
    for p, (slug, label, srcname, want) in zip(progress['pages'], want_pages):
        src = prep.src(book, srcname)
        assert src['revision'] == p['source']['revision'] and src['text_sha256'] == p['source']['text_sha256'], slug
        assert p['title'] == label
        got = build.parse_poems(sorted((ROOT / 'src' / book / slug).glob('*.txt')))
        assert [w['title'] for w in want] == [g['title'] for g in got], (slug, 'sections')
        pairs = []
        for w, g in zip(want, got):
            assert strip_p(''.join(w['paras'])) == strip_p(''.join(c['o'] for c in g['chunks'])), (slug, g['title'], 'coverage')
            assert g['intro'], (slug, g['title'], '题解')
            seen = set()
            for c in g['chunks']:
                groups = build._frag_groups(build.split_sents(c['o']))
                assert c['t'] and len(c['t'].split('¦')) == len(groups), (slug, g['title'], c['o'][:20])
                assert c['notes'], (slug, g['title'], c['o'][:20])
                for n in c['notes']:
                    term = n.split('：', 1)[0]
                    assert term in c['o'] and term not in seen, (slug, g['title'], n)
                    seen.add(term)
                pairs.extend(build.split_pairs(c['o'], c['t']))
                nnotes += len(c['notes'])
        html = BeautifulSoup((ROOT / book / (slug + '.html')).read_text(), 'html.parser')
        assert [(n.get_text(), n['data-t']) for n in html.select('.s[data-t]')] == [(o.replace('/', ''), t) for o, t in pairs], (slug, 'rendered pairs')
        npairs += len(pairs); nsec += len(want)
    assert (len(progress['pages']), nsec) == (EXPECT[book]['pages'], EXPECT[book]['sections']), (book, len(progress['pages']), nsec)
    return len(progress['pages']), nsec, npairs, nnotes


def main():
    for book in ('donglinghualu', 'chuanxilu'):
        pages, secs, pairs, notes = audit(book)
        print(f'OK {book}: {pages} pages, {secs} sections, {pairs} sentence pairs, {notes} notes')


if __name__ == '__main__':
    main()
