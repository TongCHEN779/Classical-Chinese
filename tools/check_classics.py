#!/usr/bin/env python3
"""Audit collected essays against cached witnesses and sentence-level HTML."""
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
sys.path.insert(0, str(ROOT))
import build


def normalize(text):
    return re.sub(r'\s+', '', text).translate(str.maketrans({
        '﹗': '！', '﹖': '？', '﹔': '；', '﹕': '：', '?': '？', '!': '！', ';': '；', ':': '：'}))


def check_witness(slug, provenance, original):
    if provenance['kind'] == 'existing_edited_source':
        source_sections = build.parse_poems(sorted((ROOT / provenance['path']).glob('*.txt')))
        source = next(s for s in source_sections if s['title'] == provenance['title'])
        witness = ''.join(c['o'].replace('/', '') for c in source['chunks'])
        without_additions = original
        for addition in ('时六年九月十五日。', '请洒潘江，各倾陆海云尔。'):
            if addition not in witness:
                without_additions = without_additions.replace(addition, '')
        assert without_additions == witness, (slug, 'reused text differs')
        if 'wikisource_reference' not in provenance:
            assert original == witness, (slug, 'reused text changed')
        else:
            reference = json.loads((ROOT / 'sources/classic_list' / provenance['wikisource_reference']).read_text())
            reference_text = ''.join(b['text'] for b in reference['blocks'])
            for addition in ('时六年九月十五日。', '请洒潘江，各倾陆海云尔。'):
                if addition in original and addition not in witness:
                    assert addition in reference_text, (slug, 'addition absent from Wikisource')
    else:
        cached = json.loads((ROOT / 'sources/classic_list' / provenance['cache']).read_text())
        raw = '\n'.join(b['text'] for b in cached['blocks'])
        assert hashlib.sha256(raw.encode()).hexdigest() == cached['text_sha256'], (slug, 'source cache digest')
        if 'selected_blocks' in provenance:
            raw = ''.join(cached['blocks'][i]['text'] for i in provenance['selected_blocks'])
        if provenance.get('normalization') == 'wiki_main_no_apparatus_v1':
            raw = re.sub('一作“[^”]*”', '', raw)
            raw = re.sub('〈[^〉]*〉', '', raw)
            raw = raw.replace('（', '').replace('）', '')
        if provenance.get('normalization') == 'unpunctuated_couplets':
            a, b = [cached['blocks'][i]['text'] for i in provenance['selected_blocks']]
            raw = a + ''.join((s[:5] + '，' + s[5:] if len(s) > 5 else s) + '。' for s in b.splitlines())
        witness = normalize(raw)
        if slug == 'xiangji':
            witness = witness.replace('一作“逐”', '')
        assert normalize(original) == witness, (slug, 'original differs from complete witness')


def main():
    entries = json.loads((ROOT / 'sources/classic_list/entries.json').read_text())
    expected = ['jinshi', 'bao', 'xiangji', 'yueyang', 'tengwang',
                'bie', 'hen', 'diwang', 'baixing', 'zhishi',
                'lanting', 'taohuayuan', 'chibi', 'chushi', 'guoqin',
                'chenqing', 'liuguo', 'zuiweng', 'afang', 'lihunji', 'luoshenfu', 'jianshisi',
                'guotuotuo', 'kongque', 'pipa', 'yanci', 'baochan', 'dongyang',
                'shizhong',
                'loushi', 'ailian', 'yongzhou', 'huxinting',
                'aijiangnan', 'yugu', 'yusong', 'maiyou', 'yuchen',
                'shaonian', 'bingmei', 'huangshan', 'taishan', 'zuozhongyi', 'yuzhongzaji', 'jimei', 'qinshi', 'maigan', 'shenlv', 'yurang', 'xiangci', 'zunjingge', 'xianbi', 'canglang-gui', 'canglang-su', 'hanhua', 'zhuxi', 'xinling', 'huqiu', 'manjing', 'yuejianglou', 'mozhu', 'shangzhongyong', 'mengchang', 'dasima', 'changhen', 'changan', 'xiaoyuan', 'kushu', 'daleilei', 'lingguan', 'daolouyuan', 'pengdang', 'qiusheng', 'fengle', 'wucheng']
    assert [e['slug'] for e in entries] == expected, 'collection order or membership changed'
    assert all('href' not in e for e in entries), 'obsolete external-reading entry'
    assert entries[8]['author'] == '［明］王鏊'
    assert entries[9]['author'] == '［明］王守仁'
    sentence_count = note_count = 0
    root_cl = ROOT / 'sources/classic_list'
    for entry in entries:
        slug = entry['slug']
        sections = build.parse_poems(sorted((ROOT / 'src/classic_list' / slug).glob('*.txt')))
        assert len(sections) == (len(entry['sections']) if 'sections' in entry else 3 if slug == 'guoqin' else 1), (slug, 'missing section')
        assert all(s['intro'] for s in sections), (slug, 'missing introduction')
        if slug == 'guoqin':
            assert [s['title'] for s in sections] == ['上篇', '中篇', '下篇']
        chunks = [c for s in sections for c in s['chunks']]
        assert chunks and any(c['notes'] for c in chunks), (slug, 'missing notes')
        original = ''.join(c['o'].replace('/', '') for c in chunks)
        provenance = entry['provenance']
        assert hashlib.sha256(original.encode()).hexdigest() == provenance['original_sha256'], (slug, 'original digest')
        if provenance['kind'] == 'grouped_witness':
            root = ROOT / 'sources/classic_list'
            catalog = json.loads((root / provenance['cache']).read_text())
            titles = [b['text'] for b in catalog['blocks']]
            assert hashlib.sha256('\n'.join(titles).encode()).hexdigest() == catalog['text_sha256']
            assert len(titles) == 8 and titles == [s['title'] for s in sections] == [s['title'] for s in entry['sections']]
            assert entry['source']['revision'] == catalog['revision']
            for section, record in zip(sections, entry['sections'], strict=True):
                p = record['provenance']
                cached = json.loads((root / p['cache']).read_text())
                raw = '\n'.join(b['text'] for b in cached['blocks'])
                assert hashlib.sha256(raw.encode()).hexdigest() == cached['text_sha256']
                assert record['source']['revision'] == cached['revision']
                assert record['source']['url'] == cached['url']
                expected_text = ''.join(cached['blocks'][i]['text'] for i in p['selected_blocks'])
                assert expected_text == ''.join(c['o'] for c in section['chunks'])
                assert hashlib.sha256(expected_text.encode()).hexdigest() == p['original_sha256']
                assert any(c['notes'] for c in section['chunks'])
        elif provenance['kind'] == 'sectioned_cache':
            cached = json.loads((root_cl / provenance['cache']).read_text())
            raw = '\n'.join(b['text'] for b in cached['blocks'])
            assert hashlib.sha256(raw.encode()).hexdigest() == cached['text_sha256'], (slug, 'source cache digest')
            for section, idxs in zip(sections, provenance['section_blocks'], strict=True):
                expected_text = ''.join(cached['blocks'][i]['text'] for i in idxs)
                assert normalize(''.join(c['o'] for c in section['chunks'])) == normalize(expected_text), (slug, section['title'], 'section text differs')
        elif provenance['kind'] == 'collected_works':
            assert [r['author'] for r in entry['sections']] == ['［宋］苏洵', '［宋］苏辙', '［宋］苏轼']
            for section, record in zip(sections, entry['sections'], strict=True):
                assert section['title'] == record['title']
                text = ''.join(c['o'].replace('/', '') for c in section['chunks'])
                assert hashlib.sha256(text.encode()).hexdigest() == record['provenance']['original_sha256']
                check_witness(slug, record['provenance'], text)
        else:
            check_witness(slug, provenance, original)
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
        html = BeautifulSoup((BOOKS / 'classic_list' / f'{slug}.html').read_text(), 'html.parser')
        if 'sections' in entry:
            assert [a['href'] for a in html.select('.toc a[href^="#"]')] == [f'#e{i}' for i in range(1, len(sections) + 1)]
            assert [a['href'] for a in html.select('section.entry .source-note a')] == [e['source']['url'] for e in entry['sections']]
            for old, target in entry['redirects'].items():
                redirect = BeautifulSoup((BOOKS / 'classic_list' / f'{old}.html').read_text(), 'html.parser')
                assert redirect.select_one('meta[http-equiv="refresh"]')['content'] == '0; url=' + target
                assert redirect.find('a', href=target)
                assert html.find(id=target.split('#', 1)[1])
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
                dest = (BOOKS / 'classic_list' / unquote(url.path)).resolve()
                assert dest.exists(), (slug, 'missing local link', a['href'])
        sentence_count += len(actual)
        note_count += sum(len(c['notes']) for c in chunks)
    index = BeautifulSoup((BOOKS / 'classic_list/index.html').read_text(), 'html.parser')
    assert [a['href'] for a in index.select('.vols a')] == [s + '.html' for s in expected]
    home = BeautifulSoup((ROOT / 'index.html').read_text(), 'html.parser')
    assert len(home.select('a[href="books/classic_list/index.html"]')) == 1
    print(f'OK: {len(entries)} local works, {sentence_count} sentence hovers, {note_count} notes; sources and links match')


if __name__ == '__main__':
    main()
