#!/usr/bin/env python3
"""Audit source reconstruction, attribution metadata and rendered sentence pairs."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
import build
from zhenglun_changyan_common import load, source_parts, restore, digest
from check_liaozhai import Reader


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', type=Path)
    args = ap.parse_args()
    progress = load()
    rows = []
    for page in progress['pages']:
        if page.get('kind') == 'editorial':
            continue
        snapshot = json.loads((ROOT / page['source']['snapshot']).read_text())
        expected, completed, source_count, editor_count = [], 0, 0, 0
        for unit in page['units']:
            raw = snapshot['blocks'][unit['source_block_index']]['text']
            original, notes, format_breaks = source_parts(raw)
            assert digest(raw) == unit['raw_sha256']
            assert digest(original) == unit['main_sha256']
            assert notes == unit['source_notes']
            assert format_breaks == unit.get('format_breaks', [])
            assert restore(restore(original, notes), format_breaks) == raw
            path = ROOT / 'src/zhenglun-changyan' / page['slug'] / (unit['id'] + '.txt')
            if unit['status'] != 'complete':
                assert not path.exists(), path
                continue
            secs = build.parse_poems([path])
            assert len(secs) == 1 and secs[0]['intro'] and len(secs[0]['chunks']) == 1, path
            chunk = secs[0]['chunks'][0]
            assert chunk['o'] == original, path
            assert restore(restore(chunk['o'], notes), format_breaks) == raw, path
            translations = chunk['t'].split('¦')
            assert len(translations) == len(build.split_sents(original)) == unit['sentence_pairs'], path
            assert len(build.split_pairs(chunk['o'], chunk['t'])) == len(translations), path
            assert all(t.strip() for t in translations), path
            expected.extend(translations)
            source_notes = [f'底本夹注{k:02}（主文第{n["main_offset"]}字后）：' + n['text'] for k, n in enumerate(notes, 1)]
            assert chunk['notes'][:len(notes)] == source_notes, path
            assert len(notes) == unit['source_note_count'], path
            assert len(chunk['notes']) == unit['source_note_count'] + unit['editor_note_count'], path
            for line in path.read_text().splitlines():
                if line.startswith('注：'):
                    assert len(build.split_notes(line[2:])) == 1, (path, line)
            completed += 1
            source_count += len(notes)
            editor_count += unit['editor_note_count']
        if completed:
            reader = Reader()
            reader.feed((ROOT / 'zhenglun-changyan' / (page['slug'] + '.html')).read_text())
            assert reader.translations == expected, page['slug']
            assert len(reader.anchors) == completed, page['slug']
            for target, count in reader.buttons:
                assert reader.lists[target] == count, target
        if page.get('annotation_status') == 'complete':
            assert completed == len(page['units'])
        rows.append({'page': page['slug'], 'completed_units': completed, 'total_units': len(page['units']),
                     'sentence_pairs': len(expected), 'source_notes': source_count, 'editor_notes': editor_count})
    home = (ROOT / 'index.html').read_text()
    assert 'zhenglun-changyan/index.html' in home and '政论·昌言' in home
    assert 'book-search' in home
    result = {'pages': rows, 'source_reconstruction_matches': True, 'rendered_pairs_match': True,
              'note_counts_match': True, 'scope': 'Technical coverage; semantic completeness requires editorial reading.',
              'browser_visual_check': False, 'next': progress['next']}
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
