#!/usr/bin/env python3
"""资治通鉴整理后的两项版式调整（可重复运行）：

1. 各卷“卷首”节不再收原站页面标题“资治通鉴 第NNN卷”：从原文第一段去掉，白话开头对应的“《资治通鉴》第N卷”也去掉，
   只为这一行而写的注（词语以“资治通鉴”开头）一并去掉；
2. 按年分节的卷（见 prepare_works.ZTJJ_YEAR_SPLIT）：节名改用原站年首的标题行（如“烈祖明皇帝中之下青龙三年（乙卯，公元二三五年）”），
   原先收在正文里的同一标题行从正文拿掉（白话开头的标题翻译去掉；只落在标题上的注改挂到该年首句，写成一条）。
并把来源有更新的卷在 progress_juan.json 里的版本号、哈希同步。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
import build  # noqa: E402
import prepare_works as pw  # noqa: E402
from split_ztjj_years import dump, parse  # noqa: E402

VOL_LINE = re.compile(r'^资治通鉴\s*第?\s*\d+卷/?')
VOL_T = re.compile(r'^《?资治通鉴》?第[一二三四五六七八九十百零〇]+卷[，。：；、]?')


VOL_LINE2 = re.compile(r'^卷第[一二三四五六七八九十百零〇]+/?')
VOL_T2 = re.compile(r'^卷第[一二三四五六七八九十百零〇]+[，。：；、]?')


def strip_vol_line(sec):
    """页面标题“资治通鉴 第NNN卷”和随后的“卷第某”都不收：卷号已在页标题里。"""
    c = sec['chunks'][0]
    m = VOL_LINE.match(c['o'])
    m2 = None if m else VOL_LINE2.match(c['o'])
    if not (m or m2):
        return False
    o = c['o'][(m or m2).end():]
    ts = c['t'].split('¦')
    ts[0] = (VOL_T if m else VOL_T2).sub('', ts[0].strip())
    if m:    # 同时去掉紧随其后的“卷第某”
        m3 = VOL_LINE2.match(o)
        if m3:
            o = o[m3.end():]
            ts[0] = VOL_T2.sub('', ts[0])
    c['notes'] = [n for n in c['notes'] if not re.match(r'^卷第', n.split('：', 1)[0])]
    c['notes'] = [n for n in c['notes'] if not re.match(r'^(《?资治通鉴》?\s*)?第?\d+卷', n.split('：', 1)[0])]
    if not o.strip():
        assert len(ts) == 1 and not ts[0].strip('，。'), (c['t'],)
        sec['chunks'].pop(0)
    else:
        assert ts[0], c['t']
        c['o'], c['t'] = o, '¦'.join(ts)
    return True


def strip_heading(sec, title):
    c = sec['chunks'][0]
    segs = c['o'].split('/')
    if re.sub(r'\s+', '', segs[0]).lstrip('◎') != title:
        return False
    assert len(segs) > 1, title
    rest = '/'.join(segs[1:])
    ts = c['t'].split('¦')
    t0 = re.sub(r'^[^（）]*（[^）]*）[，、]?', '', ts[0].strip(), count=1)
    if t0 == ts[0].strip():    # 标题行没有括注的写法
        t0 = re.sub(r'^[^。]*。', '', ts[0].strip(), count=1)
    assert t0 and t0 != ts[0].strip(), (title, ts[0][:40])
    ts[0] = t0
    keep, moved = [], []
    for n in c['notes']:
        term = n.split('：', 1)[0]
        (keep if term in rest else moved).append(n)
    if moved:
        anchor = rest[:rest.index('，', 2)]
        assert anchor in rest and anchor not in [n.split('：', 1)[0] for s_ in [sec] for k in s_['chunks'] for n in k['notes']], (title, anchor)
        parts = []
        for n in moved:
            term, expl = n.split('：', 1)
            parts.append(term + '，' + expl.rstrip('。').replace('：', '，'))
        note = anchor + '：' + '；'.join(parts) + '。'
        assert len(build.split_notes(note)) == 1, note
        keep.insert(0, note)
    c['o'], c['t'], c['notes'] = rest, '¦'.join(ts), keep
    return True


def run(k):
    path = ROOT / 'src/zizhitongjian' / f'juan{k:03d}' / '01.txt'
    secs = parse(path)
    changed = strip_vol_line(secs[0])
    if k in pw.ZTJJ_YEAR_SPLIT:
        want = [s for s in pw.pages('zizhitongjian') if s[0] == f'juan{k:03d}'][0][3]
        assert len(secs) == len(want), (k, len(secs), len(want))
        for s, w in zip(secs[1:], want[1:]):
            if s['title'] != w['title']:
                s['title'] = w['title']
                changed = True
            changed |= strip_heading(s, w['title'])
    empty = [(s['title'], i) for s in secs for i, c in enumerate(s['chunks']) if not c['notes']]
    if changed:
        path.write_text(dump(secs), encoding='utf8')
    return ('changed' if changed else 'same') + (f' NO-NOTE {empty}' if empty else '')


def sync_progress():
    pj = ROOT / 'sources/zizhitongjian/progress_juan.json'
    d = json.loads(pj.read_text(encoding='utf8'))
    n = 0
    for p in d['pages']:
        sd = pw.src('zizhitongjian', p['slug'] + '.json')
        new = {'title': sd['title'], 'url': sd['url'], 'revision': sd['revision'], 'text_sha256': sd['text_sha256']}
        if p['source'] != new:
            p['source'] = new
            n += 1
    pj.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    return n


if __name__ == '__main__':
    for k in pw.ZTJJ_DONE:
        try:
            r = run(k)
            if r != 'same':
                print(k, r)
        except AssertionError as e:
            print(k, 'FAIL', e)
    print('progress updated:', sync_progress())
