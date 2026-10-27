#!/usr/bin/env python3
"""Prepare an explicitly original-only edition from the retained Wikisource cache."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'sources/xiaochuang'
NAMES = ['集醒', '集情', '集峭', '集灵', '集素', '集景', '集韵', '集奇', '集绮', '集豪', '集法', '集倩']
CN = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二']


def main():
    for path in (ROOT / 'src/xiaochuang').glob('*/*.txt'):
        if '||' in path.read_text(encoding='utf8'):
            raise RuntimeError(f'Refusing to replace annotated edition or reset its progress: {path}')
    cache = {d['title']: d for p in (DEST / 'wikisource/pages').glob('*.json')
             for d in [json.loads(p.read_text(encoding='utf8'))]}
    items = [('yin', '引', '引'), ('zixu', '自叙', '自敘'), ('fanli', '凡例', '凡例')]
    items += [(f'juan{n:02d}', f'卷{CN[n-1]}·{name}', f'卷{n}') for n, name in enumerate(NAMES, 1)]
    pages = []
    for slug, title, suffix in items:
        source = cache['醉古堂劍掃/' + suffix]
        assert source['revision'] and source['blocks']
        assert source['text_sha256'] == hashlib.sha256('\n'.join(b['text'] for b in source['blocks']).encode()).hexdigest()
        lines, originals = [], []
        number = 0
        current_heading = ''
        in_collation = False
        collation = []
        for block in source['blocks']:
            text = block['text'].replace('\n', ' ').replace('\r', '')
            if block['type'].startswith('h'):
                if text == '校勘记':
                    in_collation = True
                else:
                    current_heading = text
                continue
            if in_collation:
                collation.append(text)
                continue
            number += 1
            originals.append(text)
            label = f'{number:03d}｜{text[:16]}' if suffix.startswith('卷') else f'{number:03d}｜{current_heading or title}'
            lines += ['# ' + label, '原：' + text, '']
        if collation:
            lines += ['# 维基文库校勘记', '题解：以下为原站校勘记，依原站顺序收录；箭头为原站回链符号，具体对应位置请参看页末来源链接。']
            lines += ['原：' + t for t in collation]
            lines.append('')
        target = ROOT / 'src/xiaochuang' / slug / '001.txt'
        target.parent.mkdir(parents=True, exist_ok=True)
        content = '\n'.join(lines)
        if target.exists() and '||' in target.read_text(encoding='utf8'):
            raise RuntimeError(f'Refusing to overwrite edited source: {target}')
        target.write_text(content, encoding='utf8')
        pages.append({'slug': slug, 'title': title, 'status': 'original_only',
                      'paragraphs': len(originals), 'characters': sum(map(len, originals)),
                      'collation_notes': len(collation),
                      'source': {'url': source['url'], 'revision': source['revision'],
                                 'text_sha256': source['text_sha256']}})
    assert next(p for p in pages if p['slug'] == 'fanli')['paragraphs'] == 9
    progress = {'book': '小窗幽记', 'source_title': '醉古堂劍掃', 'date': '2026-10-27',
                'status': 'original_only', 'translation_status': 'not_started',
                'annotation_status': 'not_started', 'scan_collation_status': 'not_done',
                'pages': pages}
    (DEST / 'progress.json').write_text(json.dumps(progress, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(len(pages), 'pages;', sum(p['paragraphs'] for p in pages), 'paragraphs;',
          sum(p['characters'] for p in pages), 'characters;', sum(p['collation_notes'] for p in pages), 'source collation notes')


if __name__ == '__main__':
    main()
