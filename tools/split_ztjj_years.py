#!/usr/bin/env python3
"""资治通鉴：把原站不分年的整卷（魏纪五至十、宋纪、齐纪、梁纪）里已整理好的“卷首”节拆成按年的节。

只在年首处切开：原文、白话、注释都不改，只把 chunk 在年界处一分为二，白话按句分、注释按词语所在分；
年节标题由 prepare_works.ztjj_year_split 生成，审计（check_zizhitongjian）与此保持一致。可重复运行。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
import build  # noqa: E402
import prepare_works as pw  # noqa: E402


HEADER_GLUED = {'资治通鉴 第150卷': ('《资治通鉴》第一百五十卷，卷第一百五十。', '《资治通鉴》第一百五十卷，卷第一百五十；')}


def parse(path):
    secs = []
    for ln in path.read_text(encoding='utf8').splitlines():
        if not ln.strip():
            continue
        if ln.startswith('# '):
            secs.append({'title': ln[2:].strip(), 'intro': '', 'chunks': []})
        elif ln.startswith('题解：'):
            secs[-1]['intro'] = ln[3:].strip()
        elif ln.startswith('原：'):
            o, t = (x.strip() for x in ln[2:].split('||', 1))
            secs[-1]['chunks'].append({'o': o, 't': t, 'notes': []})
        elif ln.startswith('注：'):
            secs[-1]['chunks'][-1]['notes'].append(ln[2:].strip())
        else:
            raise ValueError(f'{path}: {ln[:30]}')
    return secs


def dump(secs):
    lines = []
    for s in secs:
        lines.append('# ' + s['title'])
        if s['intro']:
            lines.append('题解：' + s['intro'])
        for c in s['chunks']:
            lines.append(f"原：{c['o']} || {c['t']}")
            lines += ['注：' + n for n in c['notes']]
        lines.append('')
    return '\n'.join(lines)


def split_chunk(c, k):
    """在去掉“/”后的第 k 个字处把 chunk 拆成两个；该处必须是句界。"""
    o = c['o']
    n = p = 0
    while n < k:
        if o[p] != '/':
            n += 1
        p += 1
    assert o[p] == '/' or o[p - 1] == '/', (o[max(0, p - 8):p + 8])
    left, right = o[:p].rstrip('/'), o[p:].lstrip('/')
    ss = build.split_sents(o)
    groups = build._frag_groups(ss)
    ts = c['t'].split('¦')
    assert len(ts) == len(groups), (len(ts), len(groups), o[:30])
    cum, cut = 0, None
    for gi, g in enumerate(groups):
        if cum == k:
            cut = gi
            break
        cum += len(''.join(ss[i] for i in g).replace('/', ''))
    if cut is None and any(o.startswith(h) for h in HEADER_GLUED):    # 卷首标题与首年首句连成一句，切开后左半另配一句标题白话
        lt, strip = next(v for h, v in HEADER_GLUED.items() if o.startswith(h))
        assert ts[0].strip().startswith(strip), ts[0][:40]
        ts = [ts[0].strip()[len(strip):]] + ts[1:]
        a = {'o': left, 't': lt, 'notes': []}
        b = {'o': right, 't': '¦'.join(ts), 'notes': []}
        for n_ in c['notes']:
            term = n_.split('：', 1)[0]
            (a if term in left else b)['notes'].append(n_)
        return a, b
    assert cut is not None, f'年界不在句界上：…{left[-12:]}|{right[:12]}…'
    a = {'o': left, 't': '¦'.join(ts[:cut]), 'notes': []}
    b = {'o': right, 't': '¦'.join(ts[cut:]), 'notes': []}
    for n_ in c['notes']:
        term = n_.split('：', 1)[0]
        (a if term in left else b)['notes'].append(n_)
    return a, b


def run(k):
    path = ROOT / 'src/zizhitongjian' / f'juan{k:03d}' / '01.txt'
    secs = parse(path)
    want = [s for s in pw.pages('zizhitongjian') if s[0] == f'juan{k:03d}'][0][3]
    if len(secs) == len(want) and [s['title'] for s in secs] == [w['title'] for w in want]:
        return 'already'
    assert len(secs) == 1 and secs[0]['title'] == '卷首', (k, [s['title'] for s in secs])
    old = secs[0]
    bounds, acc = [], 0
    for w in want:
        bounds.append(acc)
        acc += len(w['paras'][0].replace('/', ''))
    assert acc == sum(len(c['o'].replace('/', '')) for c in old['chunks']), k
    new = [{'title': w['title'], 'intro': old['intro'] if w['title'] == '卷首' else '', 'chunks': []} for w in want]
    pos, si = 0, 0
    for c in old['chunks']:
        while True:
            end = pos + len(c['o'].replace('/', ''))
            nxt = bounds[si + 1] if si + 1 < len(bounds) else None
            if nxt is not None and pos < nxt < end:
                a, b = split_chunk(c, nxt - pos)
                new[si]['chunks'].append(a)
                si += 1
                c, pos = b, nxt
                continue
            new[si]['chunks'].append(c)
            pos = end
            if nxt is not None and pos == nxt:
                si += 1
            break
    empty = [(s['title'], i) for s in new for i, c in enumerate(s['chunks']) if not c['notes']]
    path.write_text(dump(new), encoding='utf8')
    return f"{len(new)} sections, no-note chunks: {empty}" if empty else f'{len(new)} sections'


if __name__ == '__main__':
    for k in sorted(pw.ZTJJ_YEAR_SPLIT):
        try:
            print(k, run(k))
        except AssertionError as e:
            print(k, 'FAIL', e)
