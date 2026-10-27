#!/usr/bin/env python3
"""Audit 肉蒲团: source coverage, chapter sequence, note anchors, rendered note buttons."""
import hashlib
import json
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build import parse_poems

flat = lambda t: re.sub(r'[\s/]', '', t)


def main():
    dest = ROOT / 'sources/roupotuan'
    progress = json.loads((dest / 'progress.json').read_text())
    chapters = [p for p in progress['pages'] if p['kind'] == 'chapter']
    assert [p['number'] for p in chapters] == list(range(1, 21))
    cache = {d['title']: d for f in (dest / 'wikisource/pages').glob('*.json') for d in [json.loads(f.read_text())]}
    total_notes = total_chars = 0
    for p in progress['pages']:
        sections = parse_poems(sorted((ROOT / 'src/roupotuan' / p['slug']).glob('*.txt')))
        assert sections, p['slug']
        assert all(c['t'] is None for s in sections for c in s['chunks']), p['slug']
        originals = ''.join(c['o'] for s in sections for c in s['chunks'])
        if 'source' in p:
            d = cache[p['source']['title']]
            assert d['revision'] == p['source']['revision']
            assert hashlib.sha256('\n'.join(b['text'] for b in d['blocks']).encode()).hexdigest() == p['source']['text_sha256']
            blocks = [b['text'] for b in d['blocks'] if not b['type'].startswith('h')]
            blocks = blocks[p.get('dropped_header_blocks', 0):] if not any(b['type'].startswith('h') for b in d['blocks']) else blocks
            assert flat(originals) == flat(''.join(blocks)), (p['slug'], 'coverage')
            assert flat(originals) and len(flat(originals)) == p['characters'], (p['slug'], 'characters')
        actual = 0
        seen = set()
        for s in sections:
            for c in s['chunks']:
                for n in c['notes']:
                    term = n.split('：', 1)[0]
                    bare = re.sub(r'（[^）]*）', '', term)
                    body = re.sub(r'（[^）]*）', '', c['o'])
                    assert term in c['o'] or all(t in body for t in re.split('[、，/]', bare)), (p['slug'], term, 'unanchored')
                    assert term not in seen, (p['slug'], term, 'repeat')
                    seen.add(term); actual += 1
        assert actual == p['notes'], (p['slug'], actual, p['notes'])
        if p['kind'] == 'chapter': assert actual > 0, p['slug']
        path = ROOT / 'roupotuan' / (p['slug'] + '.html')
        soup = BeautifulSoup(path.read_text(), 'html.parser')
        assert not soup.select('[data-t]'), p['slug']
        html_notes = 0
        for b in soup.select('button.note-btn'):
            if '注释' not in b.get_text(): continue
            t = soup.find(id=b['aria-controls'])
            assert t.has_attr('hidden'), p['slug']
            n = len(t.find_all('li', recursive=False))
            assert int(re.search(r'（(\d+)）', b.get_text()).group(1)) == n
            html_notes += n
        assert html_notes == actual, (p['slug'], 'rendered')
        for a in soup.select('a[href]'):
            href = a['href'].split('#')[0].split('?')[0]
            if href and not re.match(r'[a-z]+:', href):
                assert (path.parent / href).exists(), (path, href)
        total_notes += actual; total_chars += len(flat(originals))
    print(f'OK: 20 chapters, {len(progress["pages"])} pages, {total_chars} chars, {total_notes} notes')


if __name__ == '__main__':
    main()
