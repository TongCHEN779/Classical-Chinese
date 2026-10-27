#!/usr/bin/env python3
"""Check source fidelity, translation alignment, rendered notes, and progress."""
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build import parse_poems, split_pairs, split_sents


def main():
    progress = json.loads((ROOT / 'sources/xiaochuang/progress.json').read_text())
    cached = {d['url']: d for p in (ROOT / 'sources/xiaochuang/wikisource/pages').glob('*.json')
              for d in [json.loads(p.read_text())]}
    translated_total = pair_total = note_total = 0
    for page in progress['pages']:
        slug = page['slug']
        source = cached[page['source']['url']]
        digest = hashlib.sha256('\n'.join(b['text'] for b in source['blocks']).encode()).hexdigest()
        assert digest == source['text_sha256'] == page['source']['text_sha256'], slug
        assert page['source']['revision'] == source['revision'], slug
        expected = [b['text'].replace('\n', ' ').replace('\r', '') for b in source['blocks']
                    if not b['type'].startswith('h')]
        sections = parse_poems(sorted((ROOT / 'src/xiaochuang' / slug).glob('*.txt')))
        chunks = [c for s in sections for c in s['chunks']]
        assert [c['o'] for c in chunks] == expected, (slug, 'source mismatch')
        text_chunks = [c for s in sections if s['title'] != '维基文库校勘记' for c in s['chunks']]
        assert len(text_chunks) == page['paragraphs'], slug
        assert sum(len(c['o']) for c in text_chunks) == page['characters'], slug
        assert len(chunks) - len(text_chunks) == page['collation_notes'], slug
        translated = [c for c in text_chunks if c['t'] is not None]
        pairs = []
        for chunk in translated:
            assert len(split_sents(chunk['o'])) == len(chunk['t'].split('¦')), (slug, chunk['o'])
            pairs.extend(split_pairs(chunk['o'], chunk['t']))
        notes = [n for c in text_chunks for n in c['notes']]
        assert len(translated) == page.get('translated_paragraphs', 0), slug
        assert len(pairs) == page.get('translation_pairs', 0), slug
        assert len(notes) == page.get('editor_notes', 0), slug
        assert all(c['t'] is None for s in sections if s['title'] == '维基文库校勘记' for c in s['chunks']), slug
        if page['status'] == 'annotated':
            assert len(translated) == len(text_chunks), slug
            assert all(c['notes'] for c in translated), slug
        else:
            assert not translated, slug
        output = ROOT / 'xiaochuang' / f'{slug}.html'
        html = BeautifulSoup(output.read_text(), 'html.parser')
        actual_pairs = [(n.get_text(), n['data-t']) for n in html.select('.s[data-t]')]
        assert actual_pairs == [(o.replace('/', ''), t) for o, t in pairs], (slug, 'rendered pairs')
        assert [n.get_text() for n in html.select('ul.notes.plain > li')] == notes, (slug, 'rendered notes')
        for button in html.select('button.note-btn'):
            match = re.search(r'注释（(\d+)）', button.get_text())
            if match:
                target = html.find(id=button['aria-controls'])
                assert int(match[1]) == len(target.find_all('li', recursive=False)), (slug, 'note count')
        hint = html.select_one('.hint').get_text()
        assert ('本卷已配逐句白话' in hint) if translated else ('白话与注释待整理' in hint), slug
        for anchor in html.select('a[href]'):
            link = urlparse(anchor['href'])
            if link.scheme or link.netloc:
                continue
            target = (output.parent / link.path).resolve() if link.path else output
            assert target.exists(), (slug, anchor['href'])
            if link.fragment:
                other = html if target == output.resolve() else BeautifulSoup(target.read_text(), 'html.parser')
                assert other.find(id=link.fragment), (slug, anchor['href'])
        translated_total += len(translated)
        pair_total += len(pairs)
        note_total += len(notes)
    index = BeautifulSoup((ROOT / 'xiaochuang/index.html').read_text(), 'html.parser')
    assert len(index.select('ul.vols a')) == len(progress['pages'])
    assert f'已配白话与编者注释{translated_total}段' in index.get_text()
    home = BeautifulSoup((ROOT / 'index.html').read_text(), 'html.parser')
    assert home.select_one('a[href="xiaochuang/index.html"]')
    print(f'{len(progress["pages"])} pages verified; {translated_total} translated paragraphs; '
          f'{pair_total} sentence pairs; {note_total} independent notes')


if __name__ == '__main__':
    main()
