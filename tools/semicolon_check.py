#!/usr/bin/env python3
"""分号改动之后的收尾：把译文分段个数与新分句不符的行整理出来。

  python3 tools/semicolon_check.py fix     可以确定的直接改（无“¦”的补上“¦”；段数等于小句数但检查器要求按“碎句并回”的合并）
  python3 tools/semicolon_check.py todo    写出 todo/tasks_w.json：旧规则下配对正常、新规则下失配的行，整行交人重配
"""
import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
sys.path.insert(0, str(ROOT))
import build  # noqa: E402

# 检查器按“碎句并回上一句”计句的书；其余书要求白话段数等于原文小句数，不能合并
MERGE_BOOKS = {'chuanxilu', 'donglinghualu', 'xianqing', 'zizhitongjian', 'zuozhuan', 'mengzi', 'lunyu', 'zhuangzi', 'daodejing', 'zhouyi', 'yanzi'}
OLD = re.compile(r"[^。！？]*[。！？]+[”’」』）]*|[^。！？]+$")
SEP = re.compile(r'\s*\|\|\s*')


def old_split(s):
    return [x for x in OLD.findall(s) if x.strip()]


def files():
    return sorted((ROOT / 'src').rglob('*.txt'))


def parse(l):
    m = SEP.search(l, 2) if l.startswith('原：') else None
    return (l[2:m.start()], m.group(0), l[m.end():]) if m else None


def old_ok(o, t):
    r = old_split(o)
    if len(r) <= 1:
        return True
    st = t.split('¦') if '¦' in t else old_split(t)
    return len(st) in (len(r), len(build._frag_groups(r)))


def fix():
    n = {'pilcrow': 0, 'merge': 0}
    for f in files():
        lines = f.read_text(encoding='utf8').split('\n')
        ch = False
        for i, l in enumerate(lines):
            p = parse(l)
            if not p or '⟦' in p[2]:
                continue
            o, sep, t = p
            raw = build.split_sents(o)
            if len(raw) <= 1:
                continue
            g = build._frag_groups(raw)
            if '¦' not in t:
                st = build.split_sents(t)
                if len(st) in (len(raw), len(g)):
                    if len(st) == len(raw) != len(g) and f.relative_to(ROOT).parts[1] in MERGE_BOOKS:
                        st = [''.join(st[k] for k in grp) for grp in g]
                    lines[i] = '原：' + o + sep + '¦'.join(st)
                    n['pilcrow'] += 1
                    ch = True
                continue
            segs = t.split('¦')
            if f.relative_to(ROOT).parts[1] in MERGE_BOOKS and len(segs) == len(raw) != len(g):
                lines[i] = '原：' + o + sep + '¦'.join(''.join(segs[k] for k in grp) for grp in g)
                n['merge'] += 1
                ch = True
        if ch:
            f.write_text('\n'.join(lines), encoding='utf8')
    print(n)


def todo():
    tasks, k = {}, 0
    for f in files():
        for ln, l in enumerate(f.read_text(encoding='utf8').split('\n'), 1):
            p = parse(l)
            if not p or '⟦' in p[2]:
                continue
            o, sep, t = p
            raw = build.split_sents(o)
            if len(raw) <= 1:
                continue
            g = build._frag_groups(raw)
            st = t.split('¦') if '¦' in t else None
            if st is not None and len(st) in (len(raw), len(g)):
                continue
            if st is None and len(build.split_sents(t)) in (len(raw), len(g)):
                continue
            if not old_ok(o, t):
                continue      # 旧规则下就已整段回退，不是这次改出来的
            k += 1
            tasks[f'w{k:04d}'] = {'file': str(f.relative_to(ROOT)), 'line': ln, 'o_parts': raw, 't': t, 'n': len(raw)}
    (BOOKS / 'todo/tasks_w.json').write_text(json.dumps(tasks, ensure_ascii=False, indent=1) + '\n', encoding='utf8')
    print(len(tasks), 'lines;', sum(v['n'] for v in tasks.values()), 'sentences')


if __name__ == '__main__':
    {'fix': fix, 'todo': todo}[sys.argv[1]]()
