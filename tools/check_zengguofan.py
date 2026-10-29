#!/usr/bin/env python3
"""Check full source coverage, editorial completion, sentence hovers and source provenance."""
import hashlib
import json
import sys
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build
from tools.prepare_zengguofan import normalize, sections


def main():
    base = ROOT / 'sources/zengguofan'
    progress = json.loads((base / 'progress.json').read_text())
    assert progress['status'] == 'complete', '全书注译未完成'
    assert progress['annotated_units'] == progress['units'] == 79
    sentences = notes = annotated = letters = 0
    for n, page in enumerate(progress['pages'], 1):
        source = json.loads((base / f'wikisource/{n}.json').read_text())
        annotations = json.loads((base / f'annotations/{n}.json').read_text())
        assert set(annotations) == {str(i) for i in range(len(source['blocks']))}, '注译块应与底本逐一覆盖'
        for i, block in enumerate(source['blocks']):
            key = 'translation' if block['type'] == 'p' else 'intro'
            assert annotations[str(i)].get(key, '').strip(), (n, i, '缺译文或题解')
        assert hashlib.sha256('\n'.join(b['text'] for b in source['blocks']).encode()).hexdigest() == source['text_sha256']
        files = sorted((ROOT / 'src/zengguofan' / page['slug']).glob('*.txt'))
        expected = sections(source)
        assert len(files) == len(expected) == len(page['units'])
        all_pairs = []
        for f, unit, state in zip(files, expected, page['units']):
            result = build.parse_poems([f])
            assert len(result) == 1
            sec = result[0]
            assert sec['title'] == unit['title'], f
            assert [c['o'] for c in sec['chunks']] == [normalize(t) for _, t in unit['blocks']], f
            assert sec['intro'], f
            assert not any('待整理' in text or '待注译' in text for text in sec['intro']), f
            complete = all(c['t'] is not None for c in sec['chunks'])
            assert complete and state['status'] == 'annotated', f
            assert complete == (state['status'] == 'annotated'), f
            if unit['level'] == 'h2':
                letters += 1
                annotated += complete
            local_notes = sum(len(c['notes']) for c in sec['chunks'])
            notes += local_notes
            assert local_notes > 0, (f, '缺少独立注释')
            assert local_notes == state['notes']
            local_pairs = []
            for chunk in sec['chunks']:
                if chunk['t'] is None:
                    continue
                pairs = build.split_pairs(chunk['o'], chunk['t'])
                assert len(pairs) == len(build.split_sents(chunk['o'])) == len(chunk['t'].split('¦')), f
                assert all(o.strip() and t.strip() for o, t in pairs), f
                local_pairs.extend(pairs)
            assert len(local_pairs) == state['sentences'], f
            sentences += len(local_pairs)
            all_pairs.extend(local_pairs)
        soup = BeautifulSoup((ROOT / 'zengguofan' / (page['slug'] + '.html')).read_text(), 'html.parser')
        assert len(soup.select('section.entry')) == len(expected)
        rendered = [(s.get_text(), s['data-t']) for s in soup.select('span.s')]
        assert rendered == all_pairs, page['slug']
        assert len(soup.select('ul.notes.plain > li')) == sum(u['notes'] for u in page['units'])
        assert soup.find('a', href=source['url'])
        assert source['revision'] in soup.get_text()
    assert letters == progress['letters']
    assert letters == annotated == 70
    assert annotated == progress['annotated_letters']
    assert sentences == progress['annotated_sentences']
    assert notes == progress['notes']
    home = BeautifulSoup((ROOT / 'index.html').read_text(), 'html.parser')
    assert home.find('a', href='zengguofan/index.html')
    print(f'曾国藩家书：三章70封及9项附文全部注译；{sentences}句对，{notes}条注；底本逐块覆盖、题解与网页悬浮逐项一致。')


if __name__ == '__main__':
    main()
