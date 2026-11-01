#!/usr/bin/env python3
"""关汉卿杂剧、赵氏孤儿、倩女离魂、墙头马上、拜月亭、林兰香（原文＋题解＋基础注释）与声律启蒙（逐句白话）：
由 sources/*/wikisource 的缓存切分作业片段，校验译注稿，写入 src/。

  python3 tools/prepare_works.py BOOK --split WORKDIR
  python3 tools/prepare_works.py BOOK --check WORKDIR PIECE
  python3 tools/prepare_works.py BOOK --merge WORKDIR
BOOK = guanhanqing | zhaoshigu | qiannulihun | qiangtoumashang | baiyueting | linlanxiang | shenglvqimeng
原文类稿件（plain）：o 去掉“/”后须与原站文字逐字一致，不得改一字一标点；声律启蒙（gloss）：去标点后一致，另配逐句白话。
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
import prepare_zizhitongjian_fulu as fulu

CN = '一二三四五六七八九十'
GHQ_SLUGS = ['douee', 'luzhailang', 'jiufengchen', 'wangjiangting', 'hudiemeng', 'jinxianchi', 'xietianxiang', 'yujingtai', 'danbianduosuo',
             'danfenghui', 'feiyimeng', 'wuhouyan', 'kucunxiao', 'peidu', 'chenmu', 'xishumeng', 'baiyueting', 'tiaofengyue']
PLAY_NAMES = dict(zip(GHQ_SLUGS, '感天动地窦娥冤 包待制智斩鲁斋郎 赵盼儿风月救风尘 望江亭中秋切鲙 包待制三勘蝴蝶梦 杜蕊娘智赏金线池 钱大尹智宠谢天香 温太真玉镜台 尉迟恭单鞭夺槊 关大王独赴单刀会 钱大尹智勘绯衣梦 刘夫人庆赏五侯宴 邓夫人苦痛哭存孝 山神庙裴度还带 状元堂陈母教子 关张双赴西蜀梦 闺怨佳人拜月亭 诈妮子调风月'.split()))
SINGLE_NAMES = {'zhaoshigu': '冤报冤赵氏孤儿', 'qiannulihun': '迷青琐倩女离魂', 'qiangtoumashang': '裴少俊墙头马上', 'baiyueting': '闺怨佳人拜月亭'}
TITLES = {'jinghuayuan': '镜花缘', 'zizhitongjian': '资治通鉴（卷一至卷七十八）', 'guanhanqing': '关汉卿杂剧', 'zhaoshigu': '赵氏孤儿', 'qiannulihun': '倩女离魂', 'qiangtoumashang': '墙头马上',
          'baiyueting': '拜月亭', 'linlanxiang': '林兰香', 'shenglvqimeng': '声律启蒙'}
# 资治通鉴已整理的卷：周秦汉魏，再加宋齐梁陈隋（晋纪79-118、唐纪185-265、五代266-294暂缓）
ZTJJ_DONE = sorted(set(range(1, 79)) | set(range(119, 185)))
ZTJJ_RUN_START = (9, 69, 119, 135, 145, 167, 177, 266, 272, 280, 286, 290)
GLOSS = {'shenglvqimeng', 'zizhitongjian'}
PIECE = {'guanhanqing': 12000, 'zhaoshigu': 12000, 'qiannulihun': 12000, 'qiangtoumashang': 12000, 'baiyueting': 12000,
         'linlanxiang': 12000, 'shenglvqimeng': 4500, 'zizhitongjian': 6000, 'jinghuayuan': 12000}
MIN_NOTE_CHARS = {'linlanxiang': 220, 'jinghuayuan': 300}      # 平均每多少字至少一条注（其余 600）


def cn(n):
    if n >= 100:
        h, r = divmod(n, 100)
        if r == 0:
            return CN[h - 1] + '百'
        if r < 10:
            return CN[h - 1] + '百零' + CN[r - 1]
        t, u = divmod(r, 10)
        return CN[h - 1] + '百' + CN[t - 1] + '十' + (CN[u - 1] if u else '')
    return CN[n - 1] if n <= 10 else ('十' + CN[n - 11] if n < 20 else CN[n // 10 - 1] + '十' + (CN[n % 10 - 1] if n % 10 else ''))


def src(book, name):
    d = {'baiyueting': ('guanhanqing', 'baiyueting.json')}.get(book)
    path = ROOT / 'sources' / (d[0] if d else book) / 'wikisource' / (d[1] if d else name)
    if book == 'zizhitongjian':
        path = ROOT / 'sources/zizhitongjian/wikisource/juan' / name
    return json.loads(path.read_text(encoding='utf8'))


def clean(t):
    # 原站录入残留的维基标记（{{--|、}}）不属于曲文，一并去掉
    t = fulu.PUA.sub('〔缺字〕', t)
    for junk in ('\ufeff', '\u3000', '{{--|', '}}'):
        t = t.replace(junk, '')
    t = re.sub(r'\s*Template:FOOTER\s*$', '', t)      # 林兰香第三十六回末的网页模板残留
    return t.strip()


def play_sections(d):
    secs = []
    for b in d['blocks']:
        if b['type'] in ('h2', 'h3'):
            secs.append({'title': clean(b['text']), 'paras': []})
        elif b['type'] in ('p', 'dd'):
            if not secs:
                secs.append({'title': '开场', 'paras': []})
            secs[-1]['paras'].append(clean(b['text']).replace('\n', '/'))
    return [s for s in secs if s['paras']]


def pages(book):
    """[(slug, 页名, 来源 json 名, [section])]；每页 section 的 title 在页内唯一。"""
    out = []
    if book == 'guanhanqing':
        for slug in GHQ_SLUGS:
            d = src(book, slug + '.json')
            out.append((slug, PLAY_NAMES[slug], slug + '.json', play_sections(d)))
    elif book in ('zhaoshigu', 'qiannulihun', 'qiangtoumashang', 'baiyueting'):
        d = src(book, 'main.json')
        out.append(('zhengwen', SINGLE_NAMES[book], 'main.json', play_sections(d)))
    elif book == 'shenglvqimeng':
        d = src(book, 'main.json')
        juan = ''
        secs = {'卷上': [], '卷下': []}
        cur = None
        for b in d['blocks']:
            if b['type'] == 'h2':
                juan = b['text']
            elif b['type'] == 'h3':
                cur = {'title': clean(b['text']), 'paras': []}
                secs[juan].append(cur)
            elif b['type'] == 'p':
                # 原站按“ /”标出对句换行，转成一整段
                cur['paras'].append(clean(re.sub(r'\s*/\s*', '', b['text'].replace('\n', ''))))
        out.append(('shang', '卷上', 'main.json', secs['卷上']))
        out.append(('xia', '卷下', 'main.json', secs['卷下']))
    elif book == 'linlanxiang':
        cg = src(book, 'congyu.json')
        out.append(('congyu', '林兰香丛语', 'congyu.json',
                    [{'title': '林兰香丛语', 'paras': [clean(b['text']).replace('\n', '/') for b in cg['blocks'] if b['type'] == 'p']}]))
        for k in range(1, 65):
            d = src(book, f'hui{k:02}.json')
            h = clean(d['blocks'][0]['text'])
            assert h.startswith(f'第{cn(k)}回'), (k, h)
            body = h[len(f'第{cn(k)}回'):]
            title = f'第{cn(k)}回　{body[:len(body) // 2]}　{body[len(body) // 2:]}' if len(body) in (14, 16, 18, 20, 22, 24) else f'第{cn(k)}回　{body}'
            paras = [clean(b['text']).replace('\n', '/') for b in d['blocks'][1:] if b['type'] in ('p', 'dd')]
            out.append((f'{k:03d}', title, f'hui{k:02}.json', [{'title': title, 'paras': paras}]))
    elif book == 'jinghuayuan':
        idx = [clean(b['text']) for b in src(book, 'index.json')['blocks'] if b['type'] == 'li']
        assert len(idx) == 100, len(idx)
        for k in range(1, 101):
            head = idx[k - 1]
            m = re.fullmatch(r'第.+?回\s*(.+)', head)
            body = m.group(1).replace(' ', '')
            title = f'第{cn(k)}回　{body[:len(body) // 2]}　{body[len(body) // 2:]}' if len(body) % 2 == 0 else f'第{cn(k)}回　{body}'
            d = src(book, f'hui{k:03d}.json')
            paras = [clean(b['text']).replace('\n', '/') for b in d['blocks'] if b['type'] == 'p']
            out.append((f'{k:03d}', title, f'hui{k:03d}.json', [{'title': title, 'paras': paras}]))
    elif book == 'zizhitongjian':
        for k in ZTJJ_DONE:
            d = src(book, f'juan{k:03d}.json')
            secs = ztjj_sections(d)
            out.append((f'juan{k:03d}', f'卷{cn(k)}', f'juan{k:03d}.json', ztjj_year_split(k, secs) if k in ZTJJ_YEAR_SPLIT else secs))
    return out


YEAR_HEAD = re.compile(r'[（〈].*?西?元?前.*?[）〉]|[（〈][甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]')


def ztjj_body(t):
    """资治通鉴：去掉段首的校记脚注序号；按点校者的校改符号取定本：(…)为删去的误字，〔…〕为补入或改正的字。"""
    t = re.sub(r'^\d+', '', t.strip())
    t = re.sub(r'\([^)]*\)', '', t)
    t = t.replace('〔', '').replace('〕', '')
    return clean(t).replace('\n', '/')


def ztjj_sections(d):
    secs, cur, wang_start = [], None, False

    def new(title, intro):
        nonlocal cur
        cur = {'title': title, 'paras': [], 'intro': intro}
        secs.append(cur)
    new('卷首', True)
    for b in d['blocks']:
        t, tx = b['type'], clean(b['text'])
        if t in ('h2', 'h3'):
            if tx == '校刊记':
                new('校刊记', True)
            elif YEAR_HEAD.search(tx):
                new(tx.replace('〈', '（').replace('〉', '）'), wang_start)
                wang_start = False
            else:
                wang_start = True
        elif t in ('p', 'dd'):
            if ztjj_body(b['text']) != '_':
                cur['paras'].append(ztjj_body(b['text']))
        elif t == 'li' and cur['title'] == '校刊记':
            cur['paras'].append(clean(re.sub(r'^↑\s*', '', b['text'])).replace('\n', '/'))
    return [s_ for s_ in secs if s_['paras']]


# 魏纪（卷七十三至七十八）、宋纪、齐纪、梁纪里原站不分年的整卷：按“春，”起首的段（每年首事）把卷首之后分成年节
ZTJJ_YEAR_SPLIT = set(range(73, 79)) | set(range(119, 135)) | set(range(136, 156)) | set(range(157, 167))
ZTJJ_YEAR_STARTS = {75: [2, 11, 20, 31, 56, 66, 89], 78: [2, 10, 37]}   # 这两卷有的年份首事不以“春”起，据正文人工定位
STEMS, BRANCHES = '甲乙丙丁戊己庚辛壬癸', '子丑寅卯辰巳午未申酉戌亥'


def cn_digits(y):
    return ''.join('〇一二三四五六七八九'[int(c)] for c in str(y))


def ztjj_year_info(k, segs):
    """(各年首段在 segs 中的下标, 各年标题)。年份链取自 catalog.json 的卷首“起…尽…”换算。"""
    import json as _j
    v = _j.loads((ROOT / 'sources/zizhitongjian/catalog.json').read_text(encoding='utf8'))['volumes'][k - 1]
    ys = list(range(v['start_year'], v['end_year'] + 1))
    idx = list(ZTJJ_YEAR_STARTS.get(k) or [i for i, x in enumerate(segs) if x.startswith('春，')])
    assert len(idx) == len(ys), (k, len(idx), len(ys))
    for j, i in enumerate(idx):    # 紧挨在年首前、不带句末标点的短行是原站的帝号或年份标题，归入该年
        floor = (idx[j - 1] + 1) if j else 2
        while i - 1 >= floor and len(segs[i - 1]) <= 40 and segs[i - 1][-1] not in '。！？”’；：，、':
            i -= 1
        idx[j] = i
    titles = [f'{STEMS[(y - 4) % 10]}{BRANCHES[(y - 4) % 12]}年（公元{cn_digits(y)}年）' for y in ys]
    return idx, titles


def ztjj_year_split(k, secs):
    assert len(secs) == 1 and secs[0]['title'] == '卷首', k
    segs = [x for p in secs[0]['paras'] for x in p.split('/')]
    idx, titles = ztjj_year_info(k, segs)
    cuts = [0] + idx + [len(segs)]
    out = [{'title': '卷首', 'paras': ['/'.join(segs[:idx[0]])], 'intro': True}]
    for j, t in enumerate(titles):
        out.append({'title': t, 'paras': ['/'.join(segs[cuts[j + 1]:cuts[j + 2]])], 'intro': False})
    return out


def pieces(book):
    out, cur = [], None
    for slug, label, srcname, secs in pages(book):
        for s in secs:
            n = sum(len(x) for x in s['paras'])
            if cur is None or (cur['chars'] + n > PIECE[book] and cur['chars'] > 0) or (book == 'zizhitongjian' and int(slug[4:]) in ZTJJ_RUN_START and cur['secs'][-1][0] != slug):
                cur = {'secs': [], 'chars': 0}
                out.append(cur)
            cur['secs'].append((slug, s, label)); cur['chars'] += n
    for i, p in enumerate(out, 1):
        p['name'] = f'p{i:02}'
    return out


def split(book, work):
    work = Path(work)
    (work / 'in').mkdir(parents=True, exist_ok=True)
    (work / 'out').mkdir(exist_ok=True)
    plan = []
    for p in pieces(book):
        data = [{'page': g, 'label': lb, 'title': s['title'], 'intro': s.get('intro', True), 'paras': s['paras']} for g, s, lb in p['secs']]
        (work / 'in' / f"{p['name']}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf8')
        lines = []
        for i, x in enumerate(data, 1):
            lines.append(f"## 节{i}  {x['title']}  （{x['label']}）  题解：{'要写' if x['intro'] else '不写（intro 填空串）'}")
            lines += [f'  P{j}  {t}' for j, t in enumerate(x['paras'], 1)]
        (work / 'in' / f"{p['name']}.txt").write_text('\n'.join(lines) + '\n', encoding='utf8')
        plan.append({'name': p['name'], 'chars': p['chars'], 'sections': len(data)})
    (work / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(len(plan), 'pieces', sum(x['chars'] for x in plan), 'chars', sum(x['sections'] for x in plan), 'sections')


def check_plain(book, work, name):
    import build
    work = Path(work)
    inp = json.loads((work / 'in' / f'{name}.json').read_text(encoding='utf8'))
    out = json.loads((work / 'out' / f'{name}.json').read_text(encoding='utf8'))
    if len(out) != len(inp):
        return [f'sections {len(out)} != {len(inp)}']
    bad, nn = [], 0
    for k, (a, b) in enumerate(zip(inp, out), 1):
        tag = f'节{k} {a["title"]}'
        if b.get('title') != a['title']:
            bad.append(f'{tag}: title changed')
        if not b.get('intro', '').strip() or '\n' in b['intro']:
            bad.append(f'{tag}: 题解 missing or multi-line')
        want = ''.join(a['paras'])
        got = ''.join(c['o'] for c in b['chunks'])
        if got.replace('/', '') != want.replace('/', ''):
            i = next((i for i, (x, y) in enumerate(zip(got.replace('/', ''), want.replace('/', ''))) if x != y), min(len(got), len(want)))
            bad.append(f'{tag}: original differs near char {i}: …{want.replace("/", "")[max(0, i - 8):i + 12]}…')
        notes = 0
        seen = set()
        for j, c in enumerate(b['chunks'], 1):
            o = c['o']
            if '\n' in o or '||' in o or not o.strip():
                bad.append(f'{tag} 段{j}: bad original'); continue
            if len(o) > 700:
                bad.append(f'{tag} 段{j}: chunk too long ({len(o)}), split at a sentence or line end')
            for n in c.get('notes', []):
                term = n.split('：', 1)[0]
                if '：' not in n or '\n' in n or term not in o:
                    bad.append(f'{tag} 段{j}: note term not in text: {n[:24]}')
                elif len(build.split_notes(n)) != 1:
                    bad.append(f'{tag} 段{j}: note splits into several: {n[:24]}')
                elif term in seen:
                    bad.append(f'{tag} 段{j}: repeated term {term}')
                seen.add(term); notes += 1
        need = max(1, -(-len(want.replace('/', '')) // MIN_NOTE_CHARS.get(book, 600)))
        if notes < need:
            bad.append(f'{tag}: only {notes} notes, need at least {need}')
        nn += notes
    return bad if bad else [f'OK {name}: {len(out)} sections, {nn} notes']


def check_out(book, work, name):
    return fulu.check_out(work, name) if book in GLOSS else check_plain(book, work, name)


def merge(book, work):
    work = Path(work)
    plan = json.loads((work / 'plan.json').read_text(encoding='utf8'))
    by_page = {}
    pj = ROOT / 'sources' / book / ('progress_juan.json' if book == 'zizhitongjian' else 'progress.json')
    kept = {x['slug']: x for x in json.loads(pj.read_text(encoding='utf8')).get('pages', [])} if pj.exists() else {}
    for p in plan:
        if not (work / 'out' / f"{p['name']}.json").exists():
            continue  # 此前已合并的片段：保留 src 与 progress 中的现状
        res = check_out(book, work, p['name'])
        assert res[0].startswith('OK'), res
        inp = json.loads((work / 'in' / f"{p['name']}.json").read_text(encoding='utf8'))
        out = json.loads((work / 'out' / f"{p['name']}.json").read_text(encoding='utf8'))
        for a, b in zip(inp, out):
            by_page.setdefault(a['page'], []).append(b)
    root = ROOT / 'src' / book
    prog = []
    for slug, label, srcname, secs in pages(book):
        if slug not in by_page:
            assert slug in kept and (root / slug / '01.txt').exists(), slug
            prog.append(kept[slug])
            continue
        d = root / slug
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob('*.txt'):
            old.unlink()
        lines = []
        for s in by_page[slug]:
            lines.append('# ' + s['title'])
            if s.get('intro', '').strip():
                lines.append('题解：' + s['intro'].strip())
            for c in s['chunks']:
                lines.append(f"原：{c['o']} || {c['t']}" if book in GLOSS else f"原：{c['o']}")
                lines += ['注：' + n for n in c.get('notes', [])]
            lines.append('')
        (d / '01.txt').write_text('\n'.join(lines), encoding='utf8')
        sd = src(book, srcname)
        prog.append({'slug': slug, 'title': label, 'sections': len(by_page[slug]),
                     'source': {'title': sd['title'], 'url': sd['url'], 'revision': sd['revision'], 'text_sha256': sd['text_sha256']}})
    pj.parent.mkdir(parents=True, exist_ok=True)
    old = json.loads(pj.read_text(encoding='utf8')) if pj.exists() else {}
    old.update({'book': TITLES[book], 'pages': prog})
    pj.write_text(json.dumps(old, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
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
        print('\n'.join(check_out(a.book, *a.check)))
    if a.merge:
        merge(a.book, a.merge)
