#!/usr/bin/env python3
"""资治通鉴附录（四库全书本、四部丛刊本版本页除外）：缓存原文、切分作业片段、合并译注稿。

  python3 tools/prepare_zizhitongjian_fulu.py --fetch
  python3 tools/prepare_zizhitongjian_fulu.py --split WORKDIR
  python3 tools/prepare_zizhitongjian_fulu.py --merge WORKDIR
"""
import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from catalog_zizhitongjian import API, get
from fetch_wikisource import save

DEST = ROOT / 'sources/zizhitongjian/wikisource/fulu'
# slug -> (wikisource title, page title)
PAGES = [
    ('fulu01', '新註資治通鑑序', '新注资治通鉴序'),
    ('fulu02', '宋神宗資治通鑑序', '宋神宗资治通鉴序'),
    ('fulu03', '進書表', '进书表'),
    ('fulu04', '獎諭詔書', '奖谕诏书'),
    ('fulu05', '資治通鑑/校勘人姓名', '校勘人姓名'),
    ('fulu06', '資治通鑑釋例', '资治通鉴释例'),
    ('fulu07', '資治通鑑外紀', '资治通鉴外纪·序'),
] + [(f'fulu{7 + k:02}', f'資治通鑑外紀/卷{k + 3:02}', f'资治通鉴外纪·卷{"四五六七八九十"[k - 1]}') for k in range(1, 8)]
SPLIT_PUNCT = {'fulu08': True, 'fulu09': True}      # 外纪卷四、卷五：原站断句不全或全无标点，只补标点


def parse_html(title):
    j = json.loads(get(API, {'action': 'parse', 'page': title, 'prop': 'text|revid', 'variant': 'zh-hans', 'redirects': 1,
                              'disableeditsection': 1, 'format': 'json', 'formatversion': 2}))
    time.sleep(1.2)
    p = j['parse']
    soup = BeautifulSoup(p['text'], 'html.parser')
    main = soup.select_one('.mw-parser-output')
    for node in main.select('.noprint, .ws-noexport, .navigation-not-searchable, .licenseContainer, .licensetpl, #toc, .toc, '
                            '.header-container, .navbox, .wst-header, .catlinks, sup.reference, table.header, .mw-editsection, style, script'):
        node.decompose()
    blocks = []
    for node in main.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'li', 'dd']):
        if node.find_parent(['table', 'blockquote']) or node.find(['p', 'li', 'dd', 'dl', 'ul', 'ol']):
            continue                                     # only leaf blocks
        for br in node.find_all('br'):
            br.replace_with('\n')
        text = node.get_text('', strip=False).replace('　', '').strip()
        text = re.sub(r'[ \t]+', ' ', re.sub(r'\n\s*\n+', '\n', text)).strip()
        if not text or text.startswith(('此作品在', '此清朝作品', '此頁面', '此页面', '取自“', '检索自“', '姊妹计划')):
            continue
        blocks.append({'type': 'dd' if node.name == 'dd' else node.name, 'text': text})
    return p['revid'], blocks


def fetch():
    DEST.mkdir(parents=True, exist_ok=True)
    meta = []
    for slug, title, label in PAGES:
        revid, blocks = parse_html(title)
        h = hashlib.sha256('\n'.join(b['text'] for b in blocks).encode()).hexdigest()
        data = {'slug': slug, 'title': title, 'label': label, 'url': 'https://zh.wikisource.org/zh-hans/' + quote(title.replace(' ', '_'), safe='/'),
                'revision': str(revid), 'blocks': blocks, 'text_sha256': h}
        save(DEST / f'{slug}.json', data)
        print(slug, title, revid, len(blocks), sum(len(b['text']) for b in blocks))



PUNCT = '\n，。；：？！、．.,:;“”‘’「」『』（）()《》〈〉…—·‧/ 　〔〕□'
PUA = re.compile('[-]')
YEAR = re.compile(r'^=?([元二三四五六七八九十百]+年)$')
CHUNK_MAX = 6000


def load(slug):
    return json.loads((DEST / f'{slug}.json').read_text(encoding='utf8'))


def norm(t):
    return PUA.sub('〔缺字〕', t).replace(' ', '')


def strip_p(t):
    return ''.join(c for c in PUA.sub('缺字', t) if c not in PUNCT and c != '=')   # '=' is leaked wikitext heading markup


def sections(slug):
    """[{title, intro(bool), paras[str]}] for one page, in source order; the apparatus (校记) is the last section."""
    d = load(slug)
    bl = d['blocks']
    out = []
    n = int(slug[4:])

    def new(title, intro=False):
        out.append({'title': title, 'intro': intro, 'paras': []})
        return out[-1]

    if n <= 4:
        sec = new(d['label'], True)
        for b in bl:
            sec['paras'].append(norm(b['text']))
        if n == 2:
            sec['paras'] = sec['paras'][1:]                      # drop the bare title line
        if n == 4:
            sec['paras'] = sec['paras'][1:]
        return out
    if n == 5:
        sec = new('校勘人姓名', True)
        run = []
        def flush():
            if run:
                sec['paras'].append('；'.join(x.replace(' ', '、') for x in run) + '。')
                run.clear()
        for b in bl[1:]:
            if b['type'] == 'dd':
                run.append(norm(b['text']).replace('、', '、'))
            else:
                flush(); sec['paras'].append(norm(b['text']))
        flush()
        return out
    if n == 6:
        for b in bl:
            if b['type'] == 'h2':
                sec = new(b['text'].split('〈')[0], False)
                if len(out) == 1:
                    out[0]['intro'] = True
                if '〈' in b['text']:
                    sec['paras'].append(b['text'])
            else:
                sec['paras'].append(norm(b['text']))
        return out
    if n == 7:
        sec = None
        for b in bl:
            if b['type'] in ('h2', 'h3'):
                if b['text'] == '目录':
                    break
                sec = new(b['text'], True)
                if b['text'] == '资治通鉴外纪序':
                    out.pop()
                    sec = None
            elif b['type'] == 'p':
                if sec is None:
                    sec = new('序', True)
                sec['paras'].append(norm(b['text']))
        for s_ in out:
            s_['title'] = s_['title']
        return out
    # 外纪 卷四—卷十
    wang = None
    cur = None
    first_of = set()
    for b in bl:
        t, tx = b['type'], b['text']
        if tx == '校记' and t == 'h2':
            break
        if t in ('h1',):
            continue
        if t in ('h2', 'h3', 'h4') and YEAR.match(tx):
            cur = new(f'{wang}·{YEAR.match(tx)[1]}' if wang else YEAR.match(tx)[1])
            continue
        if t in ('h2', 'h3') and (tx.endswith('王') or re.match(r'^周纪', tx)):
            if tx.startswith('周纪'):
                cur = new(tx, True)
                wang = None
            else:
                wang = tx
                cur = new(wang, True)
            continue
        if t == 'p' and re.match(r'^周纪.{1,3}〈', tx):
            cur = new(tx.split('〈')[0], True)
            cur['paras'].append(norm(tx))
            continue
        if t == 'p' and len(tx) <= 6 and tx.endswith(('王', '王上', '王下', '王中')) and '，' not in tx:
            wang = tx; cur = new(wang, True)
            continue
        if cur is None:
            cur = new(d['label'], True)
        if t == 'p' or t == 'dd':
            lines = [x for x in tx.split('\n')]
            for ln in lines:
                ln = norm(ln.lstrip('□'))
                if not ln:
                    continue
                m = YEAR.match(ln)
                if m:
                    cur = new(f'{wang}·{m[1]}' if wang else m[1])
                    continue
                # a paragraph that opens with "N年" but has text (卷五以下) names its own section
                m = re.match(r'^([元二三四五六七八九十]+年)', ln)
                if m and cur['paras'] and t == 'p' and not cur['title'].endswith(m[1]) and n >= 9 and tx == ln:
                    cur = new(f'{wang}·{m[1]}' if wang else m[1])
                elif m and not cur['paras'] and cur['title'] == wang and tx == ln and n >= 9:
                    cur = new(f'{wang}·{m[1]}')
                cur['paras'].append(ln)
    # empty sections (a 王 heading with only year children) keep a title-only intro: drop them from paras but keep if needed
    kept = []
    for i, s_ in enumerate(out):
        if not s_['paras']:
            # merge the intro flag into the next section
            if i + 1 < len(out):
                out[i + 1]['intro'] = out[i + 1]['intro'] or s_['intro']
            continue
        kept.append(s_)
    out = kept
    lis = [b['text'] for b in bl if b['type'] == 'li' and b['text'].startswith('↑')]
    lis = [x.lstrip('↑ ').strip() for x in lis]
    if lis:
        out.append({'title': '校记', 'intro': True, 'paras': [norm(x) for x in lis]})
    return out


def all_pieces():
    """Greedy pieces of whole sections, ~CHUNK_MAX chars each; the small front pages share two pieces."""
    pieces = []
    for grp in (['fulu01', 'fulu02', 'fulu03', 'fulu04'], ['fulu05', 'fulu06', 'fulu07']):
        pieces.append({'pages': grp, 'secs': [(g, s_) for g in grp for s_ in sections(g)]})
    cur = None
    for k in range(8, 15):
        g = f'fulu{k:02}'
        for s_ in sections(g):
            n = sum(len(x) for x in s_['paras'])
            if cur is None or cur['chars'] + n > CHUNK_MAX:
                cur = {'pages': [], 'secs': [], 'chars': 0}
                pieces.append(cur)
            cur['secs'].append((g, s_)); cur['chars'] += n
            if g not in cur['pages']:
                cur['pages'].append(g)
    for i, p in enumerate(pieces, 1):
        p['name'] = f'p{i:02}'
        p['chars'] = sum(len(x) for _, s_ in p['secs'] for x in s_['paras'])
    return pieces


def split(work):
    work = Path(work)
    (work / 'in').mkdir(parents=True, exist_ok=True)
    (work / 'out').mkdir(exist_ok=True)
    plan = []
    for p in all_pieces():
        data = [{'page': g, 'title': s_['title'], 'intro': s_['intro'], 'paras': s_['paras']} for g, s_ in p['secs']]
        (work / 'in' / f"{p['name']}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf8')
        lines = []
        for i, x in enumerate(data, 1):
            lines.append(f"## 节{i}  {x['title']}  （{x['page']}）  题解：{'要写' if x['intro'] else '不写（intro 填空串）'}")
            lines += [f'  P{j}  {t}' for j, t in enumerate(x['paras'], 1)]
        (work / 'in' / f"{p['name']}.txt").write_text('\n'.join(lines) + '\n', encoding='utf8')
        plan.append({'name': p['name'], 'pages': p['pages'], 'chars': p['chars'], 'sections': len(data)})
    (work / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(len(plan), 'pieces', sum(x['chars'] for x in plan), 'chars', sum(x['sections'] for x in plan), 'sections')


def check_out(work, name):
    """Validate one piece's agent output against its input skeleton. Returns the list of problems."""
    import build
    work = Path(work)
    inp = json.loads((work / 'in' / f'{name}.json').read_text(encoding='utf8'))
    out = json.loads((work / 'out' / f'{name}.json').read_text(encoding='utf8'))
    bad = []
    if len(out) != len(inp):
        return [f'sections {len(out)} != {len(inp)}']
    npairs = nnotes = 0
    for k, (a, b) in enumerate(zip(inp, out), 1):
        tag = f'节{k} {a["title"]}'
        if b.get('title') != a['title']:
            bad.append(f'{tag}: title changed')
        if a['intro'] and not b.get('intro', '').strip():
            bad.append(f'{tag}: missing 题解')
        if not a['intro'] and b.get('intro', '').strip():
            bad.append(f'{tag}: 题解 must be empty')
        if '\n' in b.get('intro', ''):
            bad.append(f'{tag}: 题解 newline')
        if strip_p(''.join(c['o'] for c in b['chunks'])) != strip_p(''.join(a['paras'])):
            bad.append(f'{tag}: original text changed (beyond punctuation)')
        seen = set()
        for j, c in enumerate(b['chunks'], 1):
            o, t = c['o'], c['t']
            ctag = f'{tag} 段{j}'
            if '\n' in o or '||' in o or '¦' in o or not o.strip():
                bad.append(f'{ctag}: bad original'); continue
            groups = build._frag_groups(build.split_sents(o))
            if len(t.split('¦')) != len(groups) or any(not x.strip() for x in t.split('¦')):
                bad.append(f'{ctag}: {len(t.split("¦"))} translations for {len(groups)} sentences')
            if len(o) > 700:
                bad.append(f'{ctag}: chunk too long ({len(o)}), split it')
            if not c['notes'] and a['title'] != '校记':
                bad.append(f'{ctag}: no notes')
            for n in c['notes']:
                term = n.split('：', 1)[0]
                if '：' not in n or '\n' in n or term not in o:
                    bad.append(f'{ctag}: note term not in text: {n[:24]}')
                elif len(build.split_notes(n)) != 1:
                    bad.append(f'{ctag}: note splits into several: {n[:24]}')
                elif term in seen and a['title'] != '校记':
                    bad.append(f'{ctag}: repeated term {term}')
                seen.add(term)
            npairs += len(groups); nnotes += len(c['notes'])
    return bad if bad else [f'OK {name}: {len(out)} sections, {npairs} sentences, {nnotes} notes']


def merge(work):
    work = Path(work)
    plan = json.loads((work / 'plan.json').read_text(encoding='utf8'))
    pages = {}
    for p in plan:
        inp = json.loads((work / 'in' / f"{p['name']}.json").read_text(encoding='utf8'))
        res = check_out(work, p['name'])
        assert res[0].startswith('OK'), res
        out = json.loads((work / 'out' / f"{p['name']}.json").read_text(encoding='utf8'))
        for a, b in zip(inp, out):
            pages.setdefault(a['page'], []).append(b)
    root = ROOT / 'src/zizhitongjian'
    prog = []
    for slug, secs in sorted(pages.items()):
        d = root / slug
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob('*.txt'):
            old.unlink()
        lines = []
        for s_ in secs:
            lines.append('# ' + s_['title'])
            if s_.get('intro', '').strip():
                lines.append('题解：' + s_['intro'].strip())
            for c in s_['chunks']:
                lines.append(f"原：{c['o']} || {c['t']}")
                lines += ['注：' + n for n in c['notes']]
            lines.append('')
        (d / '01.txt').write_text('\n'.join(lines), encoding='utf8')
        src = load(slug)
        prog.append({'slug': slug, 'title': src['label'], 'sections': len(secs),
                     'source': {'title': src['title'], 'url': src['url'], 'revision': src['revision'], 'text_sha256': src['text_sha256']}})
    pj = ROOT / 'sources/zizhitongjian/progress.json'
    pj.write_text(json.dumps({'book': '资治通鉴·附录', 'scope': '新注序、宋神宗序、进书表、奖谕诏书、校勘人姓名、释例、外纪（序、卷四—十，含校记）；四库全书本及四部丛刊本版本页不收',
                              'pages': prog}, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(len(prog), 'pages')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--fetch', action='store_true')
    ap.add_argument('--split'); ap.add_argument('--merge')
    ap.add_argument('--check', nargs=2, metavar=('WORKDIR', 'PIECE'))
    a = ap.parse_args()
    if a.fetch:
        fetch()
    if a.split:
        split(a.split)
    if a.check:
        print('\n'.join(check_out(*a.check)))
    if a.merge:
        merge(a.merge)
