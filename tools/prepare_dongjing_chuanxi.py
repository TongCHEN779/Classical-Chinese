#!/usr/bin/env python3
"""《东京梦华录》《传习录》：由缓存的维基文库原文切分作业片段，校验译注稿，并写入 src/。

  python3 tools/prepare_dongjing_chuanxi.py BOOK --split WORKDIR
  python3 tools/prepare_dongjing_chuanxi.py BOOK --check WORKDIR PIECE
  python3 tools/prepare_dongjing_chuanxi.py BOOK --merge WORKDIR        # BOOK = donglinghualu | chuanxilu
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
import prepare_zizhitongjian_fulu as fulu   # shared validator: check_out / strip_p / norm

PIECE = 6500
CN = '一二三四五六七八九十'
TITLES = {'donglinghualu': '东京梦华录', 'chuanxilu': '传习录'}
GROUP = {'以下门人徐爱录': '徐爱录', '以下门人陆澄录': '陆澄录', '以下门人薛侃录': '薛侃录', '门人陈九川录': '陈九川录',
         '以下门人黄修易录': '黄修易录', '以下门人黄省曾录': '黄省曾录', '此后黄以方录': '黄以方录'}
# 传习录页：(slug, 页名, [所含 h2])；h2 为卷内原站标题（“又”“二”依上文补全）
CX_PAGES = [
    ('shang1', '卷上·徐爱录（含引言、跋）', '卷上', ['徐爱引言', '以下门人徐爱录', '徐爱跋']),
    ('shang2', '卷上·陆澄录', '卷上', ['以下门人陆澄录']),
    ('shang3', '卷上·薛侃录', '卷上', ['以下门人薛侃录']),
    ('zhong1', '卷中·钱德洪序、答顾东桥书', '卷中', ['钱德洪序', '答顾东桥书']),
    ('zhong2', '卷中·答周道通、陆原静、欧阳崇一书', '卷中', ['答周道通书', '答陆原静书', '答陆原静书（又）', '答欧阳崇一']),
    ('zhong3', '卷中·答罗整庵、聂文蔚书及训蒙教约', '卷中', ['答罗整庵少宰书', '答聂文蔚', '答聂文蔚（二）', '训蒙大意示教读刘伯颂等', '教约']),
    ('xia1', '卷下·陈九川录、黄修易录', '卷下', ['门人陈九川录', '以下门人黄修易录']),
    ('xia2', '卷下·黄省曾录', '卷下', ['以下门人黄省曾录']),
    ('xia3', '卷下·黄以方录（含钱德洪跋）', '卷下', ['此后黄以方录', '钱德洪跋']),
]


def norm(t):
    """fulu.norm, plus leaked markup in the cached pages: a BOM in a heading, a stray '<' in 传习录 卷中."""
    return fulu.norm(t).replace('\ufeff', '').replace('<', '')


SRC = {'donglinghualu': ROOT / 'sources/donglinghualu/wikisource', 'chuanxilu': ROOT / 'sources/chuanxilu/wikisource'}


def src(book, name):
    return json.loads((SRC[book] / f'{name}.json').read_text(encoding='utf8'))


def dl_pages():
    """[(slug, 页名, 源文件名, [section])]"""
    out = []
    xu = src('donglinghualu', 'index')
    paras = [norm(b['text']) for b in xu['blocks'] if b['type'] == 'p']
    out.append(('xu', '序', 'index', [{'title': '序', 'paras': paras}]))
    for k in range(1, 11):
        name = '卷' + ('十' if k == 10 else CN[k - 1])
        d = src('donglinghualu', name)
        secs, cur = [], None
        for b in d['blocks']:
            if b['type'] == 'h2':
                cur = {'title': norm(b['text']), 'paras': []}; secs.append(cur)
            elif b['type'] == 'p':
                cur['paras'].append(norm(b['text']))
        assert all(s['paras'] for s in secs), name
        head = '、'.join(s['title'] for s in secs[:3])
        out.append((f'juan{k:02}', f"{name}｜{head}{'等' if len(secs) > 3 else ''}", name, secs))
    return out


def cx_pages():
    groups = {}          # h2 -> (卷, [section])
    for juan in ('卷上', '卷中', '卷下'):
        d = src('chuanxilu', juan)
        grp = None
        last = None
        n = None
        for b in d['blocks']:
            t = norm(b['text'])
            if b['type'] == 'h2':
                if t == '注释':
                    break
                if t == '又':
                    t = '答陆原静书（又）'
                elif t == '二':
                    t = '答聂文蔚（二）'
                grp = t
                groups[grp] = (juan, [])
                n = None
            elif b['type'] == 'h3':
                n = t
                tag = GROUP.get(grp, grp)
                groups[grp][1].append({'title': f'第{n}条·{tag}', 'paras': []})
            elif b['type'] == 'p':
                if n is None:
                    if not groups[grp][1]:
                        groups[grp][1].append({'title': grp, 'paras': []})
                groups[grp][1][-1]['paras'].append(norm(t))
    out = []
    for slug, label, juan, hs in CX_PAGES:
        secs = [s for h in hs for s in groups[h][1]]
        assert all(groups[h][0] == juan for h in hs), slug
        out.append((slug, label, juan, secs))
    assert set(h for p in CX_PAGES for h in p[3]) == set(groups), set(groups) ^ set(h for p in CX_PAGES for h in p[3])
    return out


def pages(book):
    return dl_pages() if book == 'donglinghualu' else cx_pages()


def pieces(book):
    out, cur = [], None
    for slug, label, srcname, secs in pages(book):
        for s in secs:
            n = sum(len(x) for x in s['paras'])
            if cur is None or (cur['chars'] + n > PIECE and cur['chars'] > 0):
                cur = {'secs': [], 'chars': 0}
                out.append(cur)
            cur['secs'].append((slug, s)); cur['chars'] += n
    for i, p in enumerate(out, 1):
        p['name'] = f'p{i:02}'
    return out


def split(book, work):
    work = Path(work)
    (work / 'in').mkdir(parents=True, exist_ok=True)
    (work / 'out').mkdir(exist_ok=True)
    plan = []
    for p in pieces(book):
        data = [{'page': g, 'title': s['title'], 'intro': True, 'paras': s['paras']} for g, s in p['secs']]
        (work / 'in' / f"{p['name']}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf8')
        lines = []
        for i, x in enumerate(data, 1):
            lines.append(f"## 节{i}  {x['title']}  （{x['page']}）  题解：要写")
            lines += [f'  P{j}  {t}' for j, t in enumerate(x['paras'], 1)]
        (work / 'in' / f"{p['name']}.txt").write_text('\n'.join(lines) + '\n', encoding='utf8')
        plan.append({'name': p['name'], 'chars': p['chars'], 'sections': len(data)})
    (work / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(len(plan), 'pieces', sum(x['chars'] for x in plan), 'chars', sum(x['sections'] for x in plan), 'sections')


def merge(book, work):
    work = Path(work)
    plan = json.loads((work / 'plan.json').read_text(encoding='utf8'))
    by_page = {}
    for p in plan:
        res = fulu.check_out(work, p['name'])
        assert res[0].startswith('OK'), res
        inp = json.loads((work / 'in' / f"{p['name']}.json").read_text(encoding='utf8'))
        out = json.loads((work / 'out' / f"{p['name']}.json").read_text(encoding='utf8'))
        for a, b in zip(inp, out):
            by_page.setdefault(a['page'], []).append(b)
    root = ROOT / 'src' / book
    prog = []
    for slug, label, srcname, secs in pages(book):
        d = root / slug
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob('*.txt'):
            old.unlink()
        lines = []
        for s in by_page[slug]:
            lines.append('# ' + s['title'])
            lines.append('题解：' + s['intro'].strip())
            for c in s['chunks']:
                lines.append(f"原：{c['o']} || {c['t']}")
                lines += ['注：' + n for n in c['notes']]
            lines.append('')
        (d / '01.txt').write_text('\n'.join(lines), encoding='utf8')
        sd = src(book, srcname)
        prog.append({'slug': slug, 'title': label, 'sections': len(by_page[slug]),
                     'source': {'title': sd['title'], 'url': sd['url'], 'revision': sd['revision'], 'text_sha256': sd['text_sha256']}})
    (ROOT / 'sources' / book / 'progress.json').write_text(
        json.dumps({'book': TITLES[book], 'pages': prog}, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(len(prog), 'pages')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('book', choices=TITLES)
    ap.add_argument('--split'); ap.add_argument('--merge')
    ap.add_argument('--check', nargs=2, metavar=('WORKDIR', 'PIECE'))
    a = ap.parse_args()
    if a.split:
        split(a.book, a.split)
    if a.check:
        print('\n'.join(fulu.check_out(*a.check)))
    if a.merge:
        merge(a.book, a.merge)
