#!/usr/bin/env python3
"""Check the five-volume Shangjunshu edition against retained Wikisource sources."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build
from tools.check_liaozhai import Reader, source_entries

EXPECTED = [
    ['更法第一', '垦令第二', '农战第三', '去彊第四'],
    ['说民第五', '算地第六', '开塞第七'],
    ['壹言第八', '错法第九', '战法第十', '立本第十一', '兵守第十二', '靳令第十三', '修权第十四'],
    ['徕民第十五', '刑约第十六', '赏刑第十七', '画策第十八'],
    ['境内第十九', '弱民第二十', '御盗第二十一', '外内第二十二', '君臣第二十三', '禁使第二十四', '慎法第二十五', '定分第二十六'],
]
LOST = {'刑约第十六', '御盗第二十一'}


def check():
    progress = json.loads((ROOT / 'sources/shangjunshu/progress.json').read_text())
    assert progress['status'] == 'complete'
    catalog = json.loads((ROOT / 'sources/shangjunshu/wikisource/catalog.json').read_text())
    raw = (ROOT / catalog['raw_snapshot']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == catalog['raw_sha256']
    assert len(catalog['volume_catalog']) == 5
    report = {'book': '商君书', 'volumes': []}
    for v, titles, catalog_text in zip(progress['volumes'], EXPECTED, catalog['volume_catalog']):
        assert v['status'] == 'complete'
        assert [e['title'] for e in v['entries']] == titles
        assert all(title in catalog_text for title in titles)
        source = json.loads((ROOT / v['source']['snapshot']).read_text())
        assert source['revision'] == v['source']['revision']
        assert source['text_sha256'] == hashlib.sha256('\n'.join(b['text'] for b in source['blocks']).encode()).hexdigest()
        originals = source_entries(source)
        assert list(originals) == [t for t in titles if t != '刑约第十六']
        total_p = total_s = total_n = 0
        expected_pairs = []
        for e in v['entries']:
            path = ROOT / 'src/shangjunshu' / f"juan{v['volume']:02d}" / (e['id'] + '.txt')
            sections = build.parse_poems([path])
            assert len(sections) == 1, path
            sec = sections[0]
            assert sec['title'] == e['title'] and sec['intro'], path
            assert e['status'] == ('lost' if e['title'] in LOST else 'complete'), path
            chunks = sec['chunks']
            if e['title'] != '刑约第十六':
                assert any(c['notes'] for c in chunks), path
            assert [c['o'] for c in chunks] == originals.get(e['title'], []), path
            if e['title'] == '刑约第十六':
                assert not chunks and e['source']['kind'] == 'catalog_lost_entry', path
            if e['title'] == '御盗第二十一':
                assert len(chunks) == 1 and chunks[0]['o'] == '[内容及篇目俱亡]', path
            p = s = n = 0
            for c in chunks:
                assert c['t'], path
                count = len(build.split_sents(c['o']))
                assert len(c['t'].split('¦')) == count, path
                pairs = build.split_pairs(c['o'], c['t'])
                assert len(pairs) == count, path
                assert all(t.strip() for _, t in pairs), path
                expected_pairs.extend(t for _, t in pairs)
                p += 1
                s += count
                n += len(c['notes'])
            assert (p, s, n) == (e['paragraphs'], e['sentence_pairs'], e['notes']), path
            for line in path.read_text().splitlines():
                if line.startswith('注：'):
                    assert len(build.split_notes(line[2:])) == 1, (path, line)
            total_p += p
            total_s += s
            total_n += n
        reader = Reader()
        reader.feed((ROOT / 'shangjunshu' / f"juan{v['volume']:02d}.html").read_text())
        assert reader.translations == expected_pairs
        assert len(reader.ids) == len(set(reader.ids))
        assert len(reader.anchors) == len(titles) and set(reader.anchors) <= set(reader.ids)
        assert all(reader.lists[key] == count for key, count in reader.buttons)
        report['volumes'].append({'volume': v['volume'], 'catalog_entries': len(titles),
                                  'extant_chapters': len([t for t in titles if t not in LOST]),
                                  'paragraphs_including_loss_marker': total_p,
                                  'sentence_pairs_including_loss_marker': total_s,
                                  'notes': total_n})
    assert sum(v['extant_chapters'] for v in report['volumes']) == 24
    report.update(source_coverage_match=True, sentence_pairs_match=True, note_counts_match=True,
                  lost_chapters=sorted(LOST), browser_visual_check=False)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = check()
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
