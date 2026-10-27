#!/usr/bin/env python3
"""Split cached Wikisource 春秋左氏傳 into work pieces and assemble the site sources.

  python3 tools/prepare_zuozhuan.py --split WORKDIR   # writes WORKDIR/in/*.txt and plan.json
  python3 tools/prepare_zuozhuan.py --merge WORKDIR   # writes src/zuozhuan/* and progress.json from WORKDIR/out
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GONG = ['隱公', '桓公', '莊公', '閔公', '僖公', '文公', '宣公', '成公', '襄公', '昭公', '定公', '哀公']
GS = {'隱公': '隐公', '桓公': '桓公', '莊公': '庄公', '閔公': '闵公', '僖公': '僖公', '文公': '文公', '宣公': '宣公',
      '成公': '成公', '襄公': '襄公', '昭公': '昭公', '定公': '定公', '哀公': '哀公'}
SLUG = {'隱公': 'yin', '桓公': 'huan', '莊公': 'zhuang', '閔公': 'min', '僖公': 'xi', '文公': 'wen', '宣公': 'xuan',
        '成公': 'cheng', '襄公': 'xiang', '昭公': 'zhao', '定公': 'ding', '哀公': 'ai'}
REPUNCT = {'成公', '襄公', '昭公', '定公', '哀公'}   # source marks every clause with 。 or ．
PIECE = 6000     # chars per work piece
PAGE = 10500     # chars per page
SRC = ROOT / 'sources/zuozhuan/wikisource/pages'


def load():
    pages = {}
    for f in SRC.glob('*.json'):
        d = json.loads(f.read_text(encoding='utf8'))
        pages[d['title'].split('/')[-1]] = d
    return pages


def sections(pages, g):
    """[(heading, [(kind, text)...])] by year; kind is 经 or 传."""
    out = []
    kind = None
    for b in pages[g]['blocks']:
        if b['type'] == 'h2':
            if b['text'] == '斠勘':
                break
            out.append([b['text'], []])
            kind = None
        elif b['type'] == 'h3':
            kind = b['text']
        elif b['type'] == 'p' and out:
            out[-1][1].append((kind or '传', re.sub(r'\s*\n\s*', '/', b['text'].strip())))
    for _, ps in out:
        assert all(k in ('经', '传') for k, _ in ps), ps[:2]
    return out


def year_text(year, ps):
    """Group consecutive paragraphs of the same kind into `# 年·类` sections."""
    lines = []
    last = None
    for kind, text in ps:
        if kind != last:
            lines += ['', f'# {year}' if year == '悼公' else f'# {year}·{kind}']
            last = kind
        lines.append('原：' + text)
    return lines


def split(work):
    work = Path(work)
    (work / 'in').mkdir(parents=True, exist_ok=True)
    pages = load()
    plan = []
    xu = pages['序']
    lines = ['# 序'] + ['原：' + b['text'].strip() for b in xu['blocks'] if b['type'] == 'p']
    (work / 'in/xu.txt').write_text('\n'.join(lines) + '\n', encoding='utf8')
    plan.append({'name': 'xu', 'gong': '序', 'repunct': False, 'years': ['序'], 'chars': sum(len(l) - 2 for l in lines[1:])})
    for g in GONG:
        years = [(y, ps, sum(len(t) for _, t in ps)) for y, ps in sections(pages, g)]
        cur, n, k = [], 0, 0
        chunks = []
        for y in years:
            if cur and n + y[2] > PIECE:
                chunks.append(cur); cur, n = [], 0
            cur.append(y); n += y[2]
        chunks.append(cur)
        if len(chunks) > 1 and sum(y[2] for y in chunks[-1]) < 2500 and sum(y[2] for y in chunks[-2]) + sum(y[2] for y in chunks[-1]) <= 8200:
            last = chunks.pop()
            chunks[-1] += last
        for i, ch in enumerate(chunks, 1):
            name = f'{SLUG[g]}_{i}'
            body = []
            for y, ps, _ in ch:
                body += year_text(y, ps)
            (work / 'in' / f'{name}.txt').write_text('\n'.join(body[1:]) + '\n', encoding='utf8')
            plan.append({'name': name, 'gong': g, 'repunct': g in REPUNCT, 'years': [y for y, _, _ in ch],
                         'chars': sum(c for _, _, c in ch)})
    (work / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(len(plan), 'pieces', sum(p['chars'] for p in plan), 'chars')


def merge(work):
    work = Path(work)
    plan = json.loads((work / 'plan.json').read_text(encoding='utf8'))
    pages = load()
    out_root = ROOT / 'src/zuozhuan'
    prog = []
    # --- page plan: consecutive pieces of one 公 up to PAGE chars
    groups = []
    for p in plan:
        if groups and groups[-1][0]['gong'] == p['gong'] and p['gong'] != '序' and sum(x['chars'] for x in groups[-1]) + p['chars'] <= PAGE:
            groups[-1].append(p)
        else:
            groups.append([p])
    # a trailing remainder smaller than 3000 chars joins the previous page of the same 公
    merged = []
    for gr in groups:
        if merged and merged[-1][0]['gong'] == gr[0]['gong'] and sum(x['chars'] for x in gr) < 3000:
            merged[-1].extend(gr)
        else:
            merged.append(gr)
    counters = {}
    for gr in merged:
        g = gr[0]['gong']
        if g == '序':
            slug, title = 'xu', '杜预序'
        else:
            counters[g] = counters.get(g, 0) + 1
            total = sum(1 for m in merged if m[0]['gong'] == g)
            slug = SLUG[g] + (str(counters[g]) if total > 1 else '')
            ys = [y for p in gr for y in p['years']]
            title = GS[g] + ('' if total == 1 else f'（{ys[0].replace(GS[g], "")}—{ys[-1].replace(GS[g], "")}）')
        d = out_root / slug
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob('*.txt'):
            old.unlink()
        chars = 0
        for i, p in enumerate(gr, 1):
            text = (work / 'out' / f"{p['name']}.txt").read_text(encoding='utf8')
            (d / f'{i:02d}.txt').write_text(text if text.endswith('\n') else text + '\n', encoding='utf8')
            chars += p['chars']
        src = pages['序' if g == '序' else g]
        prog.append({'slug': slug, 'title': title, 'pieces': [p['name'] for p in gr], 'years': [y for p in gr for y in p['years']],
                     'characters': chars, 'repunctuated': gr[0]['repunct'],
                     'source': {'title': src['title'], 'url': src['url'], 'revision': src['revision'], 'text_sha256': src['text_sha256']}})
    pj = ROOT / 'sources/zuozhuan/progress.json'
    old = json.loads(pj.read_text(encoding='utf8')) if pj.exists() else {}
    old.update({'book': '春秋左氏传', 'pages': prog})
    pj.write_text(json.dumps(old, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(len(prog), 'pages')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--split'); ap.add_argument('--merge')
    a = ap.parse_args()
    if a.split: split(a.split)
    if a.merge: merge(a.merge)
