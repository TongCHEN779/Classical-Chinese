#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild source-preserving reading text from cached Wikisource and editorial annotations."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build import split_pairs, split_sents

BASE = ROOT / 'sources/zengguofan'
CHAPTERS = ('治学篇', '修身篇', '齐家篇')


def normalize(text):
    # Source often puts a full stop inside an in-sentence parenthetical gloss.
    # Remove only those gloss full stops, without changing a single character of wording.
    text = re.sub(r'\([^()]*\)', lambda m: m[0].replace('。', ''), text)
    # Two source paragraphs end with a stray quote or middle dot after a full stop.
    return re.sub(r'(?<=[。！？])[‘·]$', '', text)


def sections(data):
    result = []
    for i, block in enumerate(data['blocks']):
        if block['type'].startswith('h'):
            result.append({'index': i, 'title': block['text'], 'level': block['type'], 'blocks': []})
        else:
            if not result:
                raise ValueError('Text before first heading')
            result[-1]['blocks'].append((i, block['text']))
    return result


def main():
    progress = {'title': '曾国藩家书', 'edition': '维基文库三章分类辑录本', 'pages': []}
    for n, chapter in enumerate(CHAPTERS, 1):
        source = json.loads((BASE / f'wikisource/{n}.json').read_text())
        annotations = json.loads((BASE / f'annotations/{n}.json').read_text())
        page = {'slug': f'part{n:02d}', 'title': f'第{n}章 {chapter}',
                'source': {k: source[k] for k in ('title', 'url', 'revision', 'text_sha256')}, 'units': []}
        for k, unit in enumerate(sections(source), 1):
            complete = bool(unit['blocks']) and all('translation' in annotations.get(str(i), {}) for i, _ in unit['blocks'])
            editorial = annotations.get(str(unit['index']), {})
            intro = editorial.get('intro', '本条原文已据维基文库收录；逐句白话、篇目题解与词条注释待整理。')
            if complete and 'intro' not in editorial:
                raise ValueError('Complete unit without introduction')
            lines = ['# ' + unit['title'], '题解：' + intro]
            count = notes = 0
            for i, text in unit['blocks']:
                ann = annotations.get(str(i), {})
                original = normalize(text)
                translation = ann.get('translation')
                if translation is not None:
                    pairs = split_pairs(original, translation)
                    if len(pairs) != len(split_sents(original)) or len(translation.split('¦')) != len(pairs):
                        raise ValueError(f'{n}:{i}: misaligned sentences {len(split_sents(original))} vs {len(translation.split("¦"))}')
                    count += len(pairs)
                lines.append('原：' + original + (' || ' + translation if translation is not None else ''))
                for note in ann.get('notes', []):
                    lines.append('注：' + note)
                    notes += 1
                lines.append('')
            out = ROOT / f'src/zengguofan/part{n:02d}/{k:03d}.txt'
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text('\n'.join(lines) + '\n')
            page['units'].append({'number': k, 'title': unit['title'], 'source_block': unit['index'],
                                  'heading_level': unit['level'], 'status': 'annotated' if complete else 'original_only',
                                  'sentences': count, 'notes': notes})
        progress['pages'].append(page)
    progress['letters'] = sum(u['heading_level'] == 'h2' for p in progress['pages'] for u in p['units'])
    progress['annotated_letters'] = sum(u['heading_level'] == 'h2' and u['status'] == 'annotated' for p in progress['pages'] for u in p['units'])
    progress['units'] = sum(len(p['units']) for p in progress['pages'])
    progress['annotated_units'] = sum(u['status'] == 'annotated' for p in progress['pages'] for u in p['units'])
    progress['status'] = 'complete' if progress['annotated_units'] == progress['units'] else 'in_progress'
    progress['annotated_sentences'] = sum(u['sentences'] for p in progress['pages'] for u in p['units'])
    progress['notes'] = sum(u['notes'] for p in progress['pages'] for u in p['units'])
    (BASE / 'progress.json').write_text(json.dumps(progress, ensure_ascii=False, indent=2) + '\n')
    print({k:v for k,v in progress.items() if k != 'pages'})


if __name__ == '__main__':
    main()
