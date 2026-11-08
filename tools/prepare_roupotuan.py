#!/usr/bin/env python3
"""Build reading-text skeletons for 肉蒲团 from the cached Wikisource pages.

Only the original text is written here; notes are added by hand afterwards, so this
script refuses to run when annotated files already exist.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from four_classics_notes import META

SLUG = 'roupotuan'
CN = '一二三四五六七八九十'


def cn_num(n):
    return CN[n - 1] if n <= 10 else '十' + CN[n - 11] if n < 20 else '二十'


def main():
    dest = ROOT / 'sources' / SLUG
    cache = {}
    for f in (dest / 'wikisource/pages').glob('*.json'):
        d = json.loads(f.read_text(encoding='utf8'))
        cache[d['title']] = d
    index = json.loads((dest / 'wikisource/index.json').read_text(encoding='utf8'))
    for f in (ROOT / 'src' / SLUG).glob('*/01.txt'):
        if '\n注：' in f.read_text(encoding='utf8') and '--force' not in sys.argv:
            raise SystemExit('annotated files exist; refusing to overwrite')
    mulu = [b['text'] for b in cache['肉蒲團/目錄']['blocks']]
    titles = {}
    for i, t in enumerate(mulu):
        m = re.fullmatch(r'第(.+)回', t)
        if m and i + 1 < len(mulu):
            titles['第' + m.group(1) + '回'] = mulu[i + 1]

    def split_title(t):
        t = t.strip()
        if re.search(r'\s', t):
            return '　'.join(re.split(r'\s+', t))
        assert len(t) % 2 == 0, t
        return t[:len(t) // 2] + '　' + t[len(t) // 2:]

    pages = []
    meta = META[SLUG]
    tj = ['# 全书题解'] + ['题解：' + h + '。' + t for h, t in meta['essays']]
    (ROOT / 'src' / SLUG / 'tijie').mkdir(parents=True, exist_ok=True)
    (ROOT / 'src' / SLUG / 'tijie/01.txt').write_text('\n'.join(tj) + '\n', encoding='utf8')
    pages.append({'slug': 'tijie', 'title': '全书题解', 'kind': 'editorial', 'paragraphs': 0, 'notes': 0,
                  'essays': len(meta['essays'])})
    order = [('xu', '肉蒲團/序', None)] + [(f'{n:03d}', f'肉蒲團/第{cn_num(n)}回', n) for n in range(1, 21)]
    for slug, wt, n in order:
        d = cache[wt]
        assert d['text_sha256'] == hashlib.sha256('\n'.join(b['text'] for b in d['blocks']).encode()).hexdigest()
        blocks = list(d['blocks'])
        if n:
            label = '第' + cn_num(n) + '回'
            title_text = titles[label]
            drop = 0
            while drop < len(blocks) and (re.fullmatch(r'肉蒲团一名觉后禅卷之.+', blocks[drop]['text'])
                                          or blocks[drop]['text'] == label
                                          or re.sub(r'\s', '', blocks[drop]['text']) == re.sub(r'\s', '', title_text)):
                drop += 1
            assert drop in (0, 2, 3), (n, drop)
            blocks = blocks[drop:]
            title = label + '　' + split_title(title_text)
            lines = ['# ' + title]
        else:
            title = '序'
            lines = ['# 序', '题解：本页为所选维基文库版本的原有序文，署“宝永乙酉”（1705）俦翠楼主人；作者立场属于原文，与本网站编者自撰的全书题解分开阅读。']
        count = chars = 0
        for b in blocks:
            text = b['text'].strip()
            if b['type'].startswith('h'):
                lines += ['', '# ' + text]
                continue
            text = re.sub(r'\s*\n\s*', '/', text).strip('/')
            lines += ['原：' + text, '']
            count += 1
            chars += len(re.sub(r'[\s/]', '', text))
        out = ROOT / 'src' / SLUG / slug / '01.txt'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text('\n'.join(lines) + '\n', encoding='utf8')
        pages.append({'slug': slug, 'title': title, 'kind': 'chapter' if n else 'front_or_back_matter', 'number': n,
                      'paragraphs': count, 'characters': chars, 'notes': 0,
                      'dropped_header_blocks': len(d['blocks']) - len(blocks),
                      'source': {k: d[k] for k in ['title', 'url', 'revision', 'text_sha256']}})
    progress = {'book': meta['title'], 'date': '2026-10-27', 'status': 'text_collected_notes_pending',
                'chapter_count': 20, 'translation_status': 'not_requested', 'annotation_status': 'pending',
                'scan_collation_status': 'not_done', 'pages': pages}
    (dest / 'progress.json').write_text(json.dumps(progress, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(len(pages), 'pages', sum(p['paragraphs'] for p in pages), 'paragraphs', sum(p.get('characters', 0) for p in pages), 'chars')


if __name__ == '__main__':
    main()
