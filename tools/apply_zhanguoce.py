#!/usr/bin/env python3
"""Dump pending 战国策 units for authoring, validate authored JSON, or write it into src/.

  python3 tools/apply_zhanguoce.py dump SLUG OUT.txt
  python3 tools/apply_zhanguoce.py check SLUG UNITS.json
  python3 tools/apply_zhanguoce.py apply SLUG UNITS.json
UNITS.json: [{"number": 1, "intro": "...", "translation": "句¦句¦...", "notes": ["词：解释", ...]}, ...]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
import build
from zhenglun_changyan_common import source_parts

PROGRESS = ROOT / 'sources/zhanguoce/progress.json'


def load(slug):
    j = json.loads(PROGRESS.read_text())
    p = next(p for p in j['pages'] if p['slug'] == slug)
    s = json.loads((ROOT / p['source']['snapshot']).read_text())
    return j, p, s


def unit_parts(p, s, u):
    raw = '\n'.join(s['blocks'][i]['text'] for i in u['source_block_indices'])
    return source_parts(raw)


def dump(slug, out):
    j, p, s = load(slug)
    lines = [f'# {p["title"]}（{len(p["units"])}篇）', '']
    for n, u in enumerate(p['units'], 1):
        main, notes, _ = unit_parts(p, s, u)
        sents = build.split_sents(main)
        lines += [f'## 第{n}篇　{u["title"]}', f'（本篇{len(sents)}句；translation 须恰好分成 {len(sents)} 段）', '主文（夹注已移出）：', main, '句子切分：']
        lines += [f'  {k}. {x}' for k, x in enumerate(sents, 1)]
        lines += ['底本夹注（姚本/鲍本/正曰/札记，供理解；已自动作为“底本原注”写入注释，勿重抄）：']
        lines += [f'  - 第{x["main_offset"]}字后：{x["text"]}' for x in notes] or ['  （无）']
        if u.get('source_reference_notes'):
            lines += ['底本网页校注：'] + [f'  - {x}' for x in u['source_reference_notes']]
        lines.append('')
    if p['preface_block_indices']:
        lines += ['（本页卷首原注，将自动附于第1篇：' + s['blocks'][p['preface_block_indices'][0]]['text'] + '）']
    Path(out).write_text('\n'.join(lines) + '\n')
    print(slug, len(p['units']), 'units ->', out)


def check(slug, path):
    j, p, s = load(slug)
    data = json.loads(Path(path).read_text())
    bad = 0
    nums = [d['number'] for d in data]
    if nums != list(range(1, len(p['units']) + 1)):
        print('numbers must be 1..%d in order, got %s' % (len(p['units']), nums)); bad += 1
    for d in data:
        n = d['number']
        if not 1 <= n <= len(p['units']):
            continue
        u = p['units'][n - 1]
        main, notes, _ = unit_parts(p, s, u)
        want = len(build.split_sents(main))
        parts = d['translation'].split('¦')
        if len(parts) != want or any(not x.strip() for x in parts):
            print(n, u['title'], 'sentences: want', want, 'got', len(parts)); bad += 1
        if not d['intro'].strip() or '\n' in d['intro']:
            print(n, 'intro empty or multi-line'); bad += 1
        if not d['notes']:
            print(n, 'needs at least one editor note'); bad += 1
        for x in d['notes']:
            if '：' not in x or '\n' in x or len(build.split_notes(x)) != 1:
                print(n, 'bad note', x[:30]); bad += 1
    print('BAD', bad)
    return bad


def apply(slug, path):
    import write_zhanguoce
    if check(slug, path):
        sys.exit('refusing to apply: check failed')
    for d in json.loads(Path(path).read_text()):
        write_zhanguoce.add(slug, d['number'], d['intro'], d['translation'], d['notes'])


if __name__ == '__main__':
    cmd = sys.argv[1]
    {'dump': lambda: dump(sys.argv[2], sys.argv[3]), 'check': lambda: check(sys.argv[2], sys.argv[3]),
     'apply': lambda: apply(sys.argv[2], sys.argv[3])}[cmd]()
