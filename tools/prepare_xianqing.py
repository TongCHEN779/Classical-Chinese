#!/usr/bin/env python3
"""Split cached Wikisource 閑情偶寄 (卷二至卷六) into work pieces and assemble site sources.

  python3 tools/prepare_xianqing.py --split WORKDIR
  python3 tools/prepare_xianqing.py --merge WORKDIR
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'sources/xianqing/wikisource/pages'
PIECE = 5500
# volume -> (title, [(部 key, 部 name, [chapter keys])])
VOLUMES = {
    2: ('词曲部下、演习部', [('詞曲部', '词曲部', ['賓白第四', '科諢第五', '格局第六']),
                           ('演習部', '演习部', ['選劇第一', '變調第二', '授曲第三', '教白第四', '脫套第五'])]),
    3: ('声容部', [('聲容部', '声容部', ['選姿第一', '修容第二', '治服第三', '習技第四'])]),
    4: ('居室部、器玩部', [('居室部', '居室部', ['房舍第一', '窗欄第二', '墻壁第三', '聯匾第四', '山石第五']),
                          ('器玩部', '器玩部', ['制度第一', '位置第二'])]),
    5: ('饮馔部、种植部', [('飲饌部', '饮馔部', ['蔬食第一', '谷食第二', '肉食第三']),
                          ('種植部', '种植部', ['木本第一', '藤本第二', '草本第三', '眾卉第四', '竹木第五'])]),
    6: ('颐养部', [('頤養部', '颐养部', ['行樂第一', '止憂第二', '調飲啜第三', '節色欲第四', '卻病第五', '療病第六'])]),
}


def tidy(text):
    """Drop source markers run into paragraphs: a leading chapter title (◎变调第二) or inline 款 labels (○鸭)."""
    text = re.sub(r'^◎[^\s]{2,6}?第[一二三四五六]', '', text)
    text = re.sub(r'^○(鸡)(?=鸡)', '', text)
    text = re.sub(r'○[^。！？，；：○]{1,8}$', '', text)
    return text


def fix_line(l):
    if not l.startswith('原：') or '||' not in l:
        return l
    o, t = l[2:].split('||', 1)
    o2 = tidy(o.strip())
    if o2 == o.strip():
        return l
    if re.search(r'○[^。！？，；：○]{1,8}$', o.strip()):
        t = '¦'.join(t.split('¦')[:-1])
    return '原：' + o2 + '||' + t


def drop_label_paragraphs(text):
    """Remove paragraphs that are only the label 小序 (with their 白话 and notes)."""
    out, skip = [], False
    for ln in text.split('\n'):
        if ln.startswith('原：小序'):
            skip = True
            continue
        if skip and ln.startswith('注：'):
            continue
        skip = False
        out.append(ln)
    return '\n'.join(out)


def load():
    out = {}
    for f in SRC.glob('*.json'):
        d = json.loads(f.read_text(encoding='utf8'))
        out[d['title']] = d
    # 維基文庫 演習部/脫套第五 mistakenly holds 選姿第一; use the Project Gutenberg text instead
    g = ROOT / 'sources/xianqing/gutenberg/tuotao.json'
    if g.exists():
        d = json.loads(g.read_text(encoding='utf8'))
        out[d['title']] = d
    return out


def clean(t):
    return re.sub(r'[◎○\s]', '', t)


def chapter_sections(d):
    """-> [(title-suffix, [paragraph...])]; first is 总论 (may be empty)."""
    blocks = d['blocks']
    name = d['title'].split('/')[-1]
    secs = [['总论', []]]
    first = True
    for b in blocks:
        text = b['text'].strip()
        if text in ('【原文】', '小序'):
            continue
        c = clean(text)
        if first:
            first = False
            if c.endswith(('第一', '第二', '第三', '第四', '第五', '第六')) and len(c) <= 6:
                continue   # chapter title
        is_head = text.startswith('○') or b['type'] == 'h3' or (b['type'] in ('h2', 'h1') and len(c) <= 8)
        if is_head and len(c) <= 12:
            secs.append([re.sub(r'\s+', ' ', re.sub(r'[◎○]', '', text)).strip(), []])
            continue
        secs[-1][1].append(tidy(re.sub(r'\s*\n\s*', '/', text)))
    if text_title_small(secs[0]) :
        pass
    return [(t, ps) for t, ps in secs if ps]


def text_title_small(_s):
    return False


def split(work):
    work = Path(work)
    (work / 'in').mkdir(parents=True, exist_ok=True)
    pages = load()
    plan, order = [], []
    for v, (vt, parts) in VOLUMES.items():
        entries = []
        for key, pname, chapters in parts:
            if key == '種植部':
                pd = pages['閑情偶寄/種植部']
                intro = [b['text'].strip() for b in pd['blocks'] if b['type'] == 'p']
                if intro:
                    entries.append((f'{pname}·小序', intro, pd, key))
            for ch in chapters:
                d = pages[f'閑情偶寄/{key}/{ch}']
                cname = clean(next(b['text'] for b in d['blocks'] if b['type'] in ('h1', 'h2', 'p') and clean(b['text']).startswith(ch[:1]) or True)) if False else None
                label = None
                for b in d['blocks'][:2]:
                    c = clean(b['text'])
                    if re.fullmatch(r'.{1,5}第[一二三四五六]', c):
                        label = c
                        break
                if label is None:
                    # chapter label is not in the text (e.g. 房舍第一 starts with 小序): use cached index label
                    idx = json.loads((ROOT / 'sources/xianqing/wikisource/index.json').read_text(encoding='utf8'))
                    label = next(l['label'] for l in idx['links'] if l['title'] == d['title'])
                for t, ps in chapter_sections(d):
                    entries.append((f'{label}·{t}', ps, d, f'{key}/{ch}'))
        # pieces
        cur, n, k = [], 0, 0
        pieces = []
        for e in entries:
            size = sum(len(p) for p in e[1])
            if cur and n + size > PIECE:
                pieces.append(cur); cur, n = [], 0
            cur.append(e); n += size
        pieces.append(cur)
        if len(pieces) > 1 and sum(len(p) for e in pieces[-1] for p in e[1]) < 1800:
            last = pieces.pop(); pieces[-1] += last
        for i, pc in enumerate(pieces, 1):
            name = f'v{v}_{i}'
            lines = []
            for title, ps, _d, _k in pc:
                lines += ['# ' + title] + ['原：' + p for p in ps] + ['']
            (work / 'in' / f'{name}.txt').write_text('\n'.join(lines), encoding='utf8')
            plan.append({'name': name, 'volume': v, 'chars': sum(len(p) for e in pc for p in e[1]),
                         'entries': [e[0] for e in pc]})
    (work / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(len(plan), 'pieces', sum(p['chars'] for p in plan), 'chars', sum(len(p['entries']) for p in plan), 'entries')


def merge(work):
    work = Path(work)
    plan = json.loads((work / 'plan.json').read_text(encoding='utf8'))
    pages = load()
    pj = ROOT / 'sources/xianqing/progress.json'
    prog = json.loads(pj.read_text(encoding='utf8'))
    for v, (vt, parts) in VOLUMES.items():
        out_dir = ROOT / 'src/xianqing' / f'juan{v:02d}'
        out_dir.mkdir(parents=True, exist_ok=True)
        for old in out_dir.glob('*.txt'):
            old.unlink()
        entries, n = [], 0
        for pc in [p for p in plan if p['volume'] == v]:
            text = (work / 'out' / f"{pc['name']}.txt").read_text(encoding='utf8')
            text = drop_label_paragraphs(text)
            text = '\n'.join(fix_line(l) for l in text.split('\n') if not (l.startswith('注：') and (l.startswith('注：○') or ('◎' in l and l.startswith('注：校：')))))
            text = re.sub('[\ue000-\uf8ff]', '〔缺字〕', text)
            for block in re.split(r'\n(?=# )', text.strip('\n')):
                if block.startswith('# 脱套第五·') and pc['name'] in ('v2_6', 'v2_7'):
                    continue   # these pieces were cut from the mistaken Wikisource page (a copy of 選姿第一)
                n += 1
                title = block.split('\n', 1)[0][2:].strip()
                f = out_dir / f'{n:03d}.txt'
                f.write_text(block.rstrip('\n') + '\n', encoding='utf8')
                entries.append({'id': f'{n:03d}', 'title': title, 'status': 'complete',
                                'source_file': f'src/xianqing/juan{v:02d}/{n:03d}.txt',
                                'review': {'source': 'wikisource', 'piece': pc['name']}})
        chapters = []
        for e in entries:
            ch = e['title'].split('·')[0]
            if not chapters or chapters[-1]['title'] != ch:
                chapters.append({'title': ch, 'entry_ids': []})
            chapters[-1]['entry_ids'].append(e['id'])
        srcs = []
        for key, pname, chs in parts:
            for ch in chs:
                d = pages[f'閑情偶寄/{key}/{ch}']
                srcs.append({'title': d['title'], 'url': d['url'], 'revision': d['revision'], 'text_sha256': d['text_sha256']})
            if key == '種植部':
                d = pages['閑情偶寄/種植部']
                srcs.append({'title': d['title'], 'url': d['url'], 'revision': d['revision'], 'text_sha256': d['text_sha256']})
        vol = next(x for x in prog['volumes'] if x['volume'] == v)
        vol.update({'status': 'complete', 'entries': entries, 'chapters': chapters, 'wikisource_sources': srcs})
        vol.pop('printed_start', None)
    prog['next_position'] = None
    pj.write_text(json.dumps(prog, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print('merged', sum(len(x.get('entries', [])) for x in prog['volumes']), 'entries')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--split'); ap.add_argument('--merge')
    a = ap.parse_args()
    if a.split: split(a.split)
    if a.merge: merge(a.merge)
