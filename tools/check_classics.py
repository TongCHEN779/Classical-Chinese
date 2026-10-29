#!/usr/bin/env python3
"""Audit the ten collected essays against cached witnesses and sentence-level HTML."""
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build


def normalize(text):
    return re.sub(r'\s+', '', text).translate(str.maketrans({
        '﹗': '！', '﹖': '？', '﹔': '；', '﹕': '：', '?': '？', '!': '！', ';': '；'}))


def main():
    entries = json.loads((ROOT / 'sources/classic_list/entries.json').read_text())
    expected = ['jinshi', 'bao', 'xiangji', 'yueyang', 'tengwang',
                'bie', 'hen', 'diwang', 'baixing', 'zhishi']
    assert [e['slug'] for e in entries] == expected, 'collection order or membership changed'
    assert all('href' not in e for e in entries), 'obsolete external-reading entry'
    assert entries[8]['author'] == '［明］王鏊'
    assert entries[9]['author'] == '［明］王守仁'
    sentence_count = note_count = 0
    for entry in entries:
        slug = entry['slug']
        sections = build.parse_poems(sorted((ROOT / 'src/classic_list' / slug).glob('*.txt')))
        assert len(sections) == 1 and sections[0]['intro'], (slug, 'missing introduction')
        chunks = sections[0]['chunks']
        assert chunks and any(c['notes'] for c in chunks), (slug, 'missing notes')
        original = ''.join(c['o'].replace('/', '') for c in chunks)
        provenance = entry['provenance']
        assert hashlib.sha256(original.encode()).hexdigest() == provenance['original_sha256'], (slug, 'original digest')
        if provenance['kind'] == 'existing_edited_source':
            source_sections = build.parse_poems(sorted((ROOT / provenance['path']).glob('*.txt')))
            source = next(s for s in source_sections if s['title'] == provenance['title'])
            witness = ''.join(c['o'].replace('/', '') for c in source['chunks'])
            without_additions = original
            for addition in ('时六年九月十五日。', '请洒潘江，各倾陆海云尔。'):
                if addition not in witness:
                    without_additions = without_additions.replace(addition, '')
            assert without_additions == witness, (slug, 'reused text differs')
            reference = json.loads((ROOT / 'sources/classic_list' / provenance['wikisource_reference']).read_text())
            reference_text = ''.join(b['text'] for b in reference['blocks'])
            for addition in ('时六年九月十五日。', '请洒潘江，各倾陆海云尔。'):
                if addition in original and addition not in witness:
                    assert addition in reference_text, (slug, 'addition absent from Wikisource')
        else:
            cached = json.loads((ROOT / 'sources/classic_list' / provenance['cache']).read_text())
            raw = '\n'.join(b['text'] for b in cached['blocks'])
            assert hashlib.sha256(raw.encode()).hexdigest() == cached['text_sha256'], (slug, 'source cache digest')
            witness = normalize(raw)
            if slug == 'xiangji':
                witness = witness.replace('一作“逐”', '')
            assert normalize(original) == witness, (slug, 'original differs from complete witness')
        pairs = []
        for chunk in chunks:
            assert chunk['t'], (slug, 'missing translation')
            originals = build.split_sents(chunk['o'])
            translations = chunk['t'].split('¦')
            assert len(originals) == len(translations), (slug, 'sentence count mismatch')
            assert all(t.strip() for t in translations), (slug, 'empty translation')
            rendered_pairs = build.split_pairs(chunk['o'], chunk['t'])
            assert [o for o, _t in rendered_pairs] == originals, (slug, 'paragraph fallback')
            pairs.extend((o.replace('/', ''), t) for o, t in rendered_pairs)
        html = BeautifulSoup((ROOT / 'classic_list' / f'{slug}.html').read_text(), 'html.parser')
        actual = [(span.get_text(), span['data-t']) for span in html.select('.s[data-t]')]
        assert actual == pairs, (slug, 'HTML differs from sentence pairs')
        assert not html.select('p.v.nv, p.v.dr'), (slug, 'untranslated passage')
        assert all(len(build.split_sents(o)) == 1 for o, t in actual), (slug, 'multi-sentence hover')
        for button in html.select('.note-btn'):
            target = html.find(id=button['aria-controls'])
            assert target is not None and target.has_attr('hidden'), (slug, 'uncollapsed notes')
            count = re.search(r'注释（(\d+)）', button.get_text())
            if count:
                assert int(count[1]) == len(target.find_all('li', recursive=False)), (slug, 'note count')
        for a in html.select('a[href]'):
            url = urlparse(a['href'])
            if not url.scheme:
                dest = (ROOT / 'classic_list' / unquote(url.path)).resolve()
                assert dest.exists(), (slug, 'missing local link', a['href'])
        sentence_count += len(actual)
        note_count += sum(len(c['notes']) for c in chunks)
    index = BeautifulSoup((ROOT / 'classic_list/index.html').read_text(), 'html.parser')
    assert [a['href'] for a in index.select('.vols a')] == [s + '.html' for s in expected]
    home = BeautifulSoup((ROOT / 'index.html').read_text(), 'html.parser')
    assert len(home.select('a[href="classic_list/index.html"]')) == 1
    print(f'OK: 10 complete local essays, {sentence_count} sentence hovers, {note_count} notes; sources and links match')


if __name__ == '__main__':
    main()
