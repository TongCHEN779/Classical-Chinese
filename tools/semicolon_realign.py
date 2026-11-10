#!/usr/bin/env python3
"""悬浮白话改为按句号、问号、叹号、分号（；）分段：把 src 里每个含“；”的原文句及其白话重新配对。

  python3 tools/semicolon_realign.py auto     译文分号数与原文一致的直接按“；”拆开；其余留下占位符并写出待办 todo/*.json
  python3 tools/semicolon_realign.py apply D  把 D/ 里已填 t_parts 的待办写回 src
  python3 tools/semicolon_realign.py left     列出尚未处理的占位符
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
OLD = re.compile(r"[^。！？]*[。！？]+[”’」』）]*|[^。！？]+$")
NEW = re.compile(r"[^。！？；]*[。！？；]+[”’」』）]*|[^。！？；]+$")
CLOSERS = '”’」』）'
TOKEN = re.compile(r'⟦(\w+)⟧')
SEP = re.compile(r'\s*\|\|\s*')
TAG = 't'    # 待办编号前缀，见 auto 的第二个参数


def ss(rx, s):
    return [x for x in rx.findall(s) if x.strip()]


def split_semi(b):
    """在“；”（连同其后的右引号、右括号）之后切开。"""
    out, cur, i = [], '', 0
    while i < len(b):
        cur += b[i]
        if b[i] == '；':
            while i + 1 < len(b) and b[i + 1] in CLOSERS:
                i += 1
                cur += b[i]
            out.append(cur)
            cur = ''
        i += 1
    if cur:
        out.append(cur)
    return out


def src_files():
    return sorted((ROOT / 'src').rglob('*.txt'))


def auto(tag='t'):
    todo, stats = {}, {'lines': 0, 'auto': 0, 'todo': 0, 'skipped_len': 0, 'no_pilcrow': 0}
    n = 0
    for f in src_files():
        lines = f.read_text(encoding='utf8').split('\n')
        changed = False
        for li, l in enumerate(lines):
            m = SEP.search(l, 2) if l.startswith('原：') else None
            if not m:
                continue
            o, t = l[2:m.start()], l[m.end():]
            sep = m.group(0)
            old_s = ss(OLD, o)
            if not any('；' in x for x in old_s):
                continue
            stats['lines'] += 1
            if '¦' not in t:
                stats['no_pilcrow'] += 1
                continue
            segs = t.split('¦')
            if len(segs) != len(old_s):
                stats['skipped_len'] += 1
                continue
            new_segs = []
            for a, b in zip(old_s, segs):
                parts = ss(NEW, a)
                if len(parts) == 1:
                    new_segs.append(b)
                    continue
                if b.count('；') == len(parts) - 1:
                    sp = split_semi(b)
                    if len(sp) == len(parts) and all(x.strip() for x in sp):
                        new_segs.extend(sp)
                        stats['auto'] += 1
                        continue
                n += 1
                tid = f'{tag}{n:05d}'
                todo[tid] = {'file': str(f.relative_to(ROOT)), 'line': li + 1, 'o_parts': parts, 't': b, 'n': len(parts)}
                new_segs.append(f'⟦{tid}⟧{b}')
                stats['todo'] += 1
            lines[li] = '原：' + o + sep + '¦'.join(new_segs)
            changed = True
        if changed:
            f.write_text('\n'.join(lines), encoding='utf8')
    out = BOOKS / 'todo'
    out.mkdir(exist_ok=True)
    (out / f'tasks_{tag}.json').write_text(json.dumps(todo, ensure_ascii=False, indent=1) + '\n', encoding='utf8')
    print(stats)


def apply(d, tasks_file='todo/tasks.json'):
    tasks = json.loads((ROOT / tasks_file).read_text(encoding='utf8'))
    done = {}
    for p in sorted(Path(d).glob('*.json')):
        for tid, parts in json.loads(p.read_text(encoding='utf8')).items():
            done[tid] = parts
    bad = []
    by_file = {}
    for tid, t in tasks.items():
        if tid in done:
            parts = done[tid]
            if len(parts) != t['n'] or not all(x.strip() for x in parts):
                bad.append(tid)
                continue
            by_file.setdefault(t['file'], []).append((tid, t, parts))
    n = 0
    for fn, items in by_file.items():
        f = ROOT / fn
        s = f.read_text(encoding='utf8')
        for tid, t, parts in items:
            key = f'⟦{tid}⟧' + t['t']
            assert key in s, (tid, fn)
            s = s.replace(key, '¦'.join(parts), 1)
            n += 1
        f.write_text(s, encoding='utf8')
    print('applied', n, 'bad', bad[:20], len(bad), 'missing', len(tasks) - len(done))


def apply2(d):
    """tasks2.json：整行替换白话（按文件与行号）。"""
    tasks = json.loads((BOOKS / 'todo/tasks2.json').read_text(encoding='utf8'))
    done = {}
    for p in sorted(Path(d).glob('*.json')):
        done.update(json.loads(p.read_text(encoding='utf8')))
    by_file, bad = {}, []
    for tid, t in tasks.items():
        parts = done.get(tid)
        if parts is None or len(parts) != t['n'] or not all(x.strip() for x in parts):
            bad.append(tid)
            continue
        by_file.setdefault(t['file'], []).append((t, parts))
    for fn, items in by_file.items():
        f = ROOT / fn
        lines = f.read_text(encoding='utf8').split('\n')
        for t, parts in items:
            l = lines[t['line'] - 1]
            o, old = l[2:].split(' || ', 1)
            assert old == t['t'], (fn, t['line'])
            lines[t['line'] - 1] = '原：' + o + ' || ' + '¦'.join(parts)
        f.write_text('\n'.join(lines), encoding='utf8')
    print('applied2', sum(len(v) for v in by_file.values()), 'bad', bad)


def left():
    c = 0
    for f in src_files():
        for li, l in enumerate(f.read_text(encoding='utf8').split('\n'), 1):
            if TOKEN.search(l):
                c += 1
    print('lines with placeholders:', c)


if __name__ == '__main__':
    m = sys.argv[1] if len(sys.argv) > 1 else ''
    {'auto': lambda: auto(sys.argv[2] if len(sys.argv) > 2 else 't'), 'left': left, 'apply2': lambda: apply2(sys.argv[2]),
     'apply3': lambda: apply(sys.argv[2], sys.argv[3])}.get(m, lambda: apply(sys.argv[2]))()
