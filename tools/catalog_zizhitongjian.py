#!/usr/bin/env python3
"""Build the 资治通鉴 catalogue (目录) from Wikisource; no volume text is cached or edited.

Writes sources/zizhitongjian/{index.json,index.html.snapshot,catalog.json}.
"""
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from fetch_wikisource import download, save

DEST = ROOT / 'sources/zizhitongjian'
API = 'https://zh.wikisource.org/w/api.php'
UA = {'User-Agent': 'ClassicalChineseLibrary/1.0 (public-domain text research)'}
TITLE = '資治通鑑'
GAN = {'閼逢': 0, '旃蒙': 1, '柔兆': 2, '強圉': 3, '著雍': 4, '屠維': 5, '上章': 6, '重光': 7, '玄黓': 8, '昭陽': 9}
ZHI = {'困敦': 0, '赤奮若': 1, '攝提格': 2, '單閼': 3, '執徐': 4, '大荒落': 5, '敦牂': 6, '協洽': 7, '涒灘': 8, '作噩': 9,
       '閹茂': 10, '大淵獻': 11}
ALIAS = {'阏逢': '閼逢', '强圉': '強圉', '屠维': '屠維', '玄默': '玄黓', '昭阳': '昭陽', '赤奋若': '赤奮若', '摄提格': '攝提格',
         '单阏': '單閼', '执徐': '執徐', '协洽': '協洽', '涒滩': '涒灘', '阉茂': '閹茂', '大渊献': '大淵獻', '彊圉': '強圉',
         '作鄂': '作噩', '單閼': '單閼', '玄黓': '玄黓', '尽': '盡', '閹茂': '閹茂'}
DIGIT = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}


def get(url, params=None, data=None):
    for attempt in range(5):
        try:
            if data is not None:
                req = Request(url, data=urlencode(data).encode(), headers=UA)
            else:
                req = Request(url + ('?' + urlencode(params) if params else ''), headers=UA)
            return urlopen(req, timeout=60).read().decode('utf8')
        except Exception:
            if attempt == 4:
                raise
            time.sleep(15 * 2 ** attempt)   # Wikimedia answers 429 when requests come too fast


def cn_number(s):
    s = s.strip()
    if '百' in s:
        a, b = s.split('百')
        return (DIGIT.get(a, 1) if a else 1) * 100 + (cn_number(b) if b else 0)
    if '十' in s:
        a, b = s.split('十')
        return (DIGIT.get(a, 1) if a else 1) * 10 + (DIGIT.get(b, 0) if b else 0)
    return DIGIT[s]


def norm(s):
    for k, v in ALIAS.items():
        s = s.replace(k, v)
    return s


TIANGAN = '甲乙丙丁戊己庚辛壬癸'
DIZHI = '子丑寅卯辰巳午未申酉戌亥'
MONTH = re.compile(r'(閏|闰)?[正冬臘腊一二三四五六七八九十]+月$')
CANON = {}
for _i in range(60):
    _g = [k for k, v in GAN.items() if v == _i % 10][0]
    _z = [k for k, v in ZHI.items() if v == _i % 12][0]
    CANON[_i] = _g + _z


def split_month(span):
    span = norm(span.replace('\u3000', '').replace('□', '').replace('（戎申）', ''))
    m = MONTH.search(span)
    return (span[:m.start()], m.group(0)) if m else (span, None)


def ganzhi_index(span):
    """'著雍攝提格' -> 0-59 sexagenary index. Wikisource carries OCR typos, so the nearest of the 60 valid
    stem+branch combinations wins (the stem/branch parity rule already rules out most mistakes)."""
    import difflib
    if len(span) == 2 and span[0] in TIANGAN and span[1] in DIZHI:   # plain 干支 such as 丁未
        return next(i for i in range(60) if TIANGAN[i % 10] + DIZHI[i % 12] == span)
    span, _month = split_month(span)
    best = max(range(60), key=lambda i: difflib.SequenceMatcher(None, span, CANON[i]).ratio())
    ratio = difflib.SequenceMatcher(None, span, CANON[best]).ratio()
    if ratio < 0.6:
        raise ValueError(span)
    return best


def is_canonical(span):
    return split_month(span)[0] == CANON[ganzhi_index(span)]


def year_of(index, near):
    """The year (negative = BC, no year 0) with this ganzhi index closest to `near`."""
    best = None
    for y in range(near - 30, near + 31):
        astro = y if y > 0 else y + 1
        if y != 0 and (astro - 4) % 60 == index and (best is None or abs(y - near) < abs(best - near)):
            best = y
    return best


def raw_wikitext(titles):
    out = {}
    for i in range(0, len(titles), 40):
        chunk = titles[i:i + 40]
        j = json.loads(get(API, {'action': 'query', 'prop': 'revisions', 'rvprop': 'content|ids', 'rvslots': 'main',
                                  'rvsection': 0, 'titles': '|'.join(chunk), 'format': 'json', 'formatversion': 2}))
        for p in j['query']['pages']:
            r = p['revisions'][0]
            out[p['title'].replace(' ', '_') if False else p['title']] = {'revid': r['revid'], 'text': r['slots']['main']['content']}
        time.sleep(0.5)
    return out


def simplify(lines):
    """Convert strings with MediaWiki's own zh-hans conversion; one line per input."""
    marker = '\n'.join(f'{i}|{s}' for i, s in enumerate(lines))
    j = json.loads(get(API, data={'action': 'parse', 'text': marker, 'contentmodel': 'wikitext', 'prop': 'text',
                                  'variant': 'zh-hans', 'disablelimitreport': 1, 'format': 'json', 'formatversion': 2}))
    text = BeautifulSoup(j['parse']['text'], 'html.parser').get_text('\n')
    res = {}
    for ln in text.split('\n'):
        m = re.match(r'^(\d+)\|(.*)$', ln.strip())
        if m:
            res[int(m[1])] = m[2]
    assert len(res) == len(lines), (len(res), len(lines))
    return [res[i] for i in range(len(lines))]


_CACHE_PATH = Path('/tmp/zztj_cache.json')
_CACHE = json.loads(_CACHE_PATH.read_text()) if _CACHE_PATH.exists() else {}


def cached(key, fn):
    """Development convenience: remember slow API answers so a failed run can resume."""
    if key not in _CACHE:
        _CACHE[key] = fn()
        _CACHE_PATH.write_text(json.dumps(_CACHE, ensure_ascii=False))
    return _CACHE[key]


def to_cn(n):
    digits = '零一二三四五六七八九'
    if n < 10:
        return digits[n]
    if n < 20:
        return '十' + (digits[n - 10] if n > 10 else '')
    return digits[n // 10] + '十' + (digits[n % 10] if n % 10 else '')


def parse_header(text):
    """Volume name as written in the header (when present) and the year span of the volume.

    Two source forms: '起X，盡Y，凡N年' and the one-span form 'X，N年'."""
    m = re.search(r'\|\s*section\s*=\s*(.+)', text)
    sec = re.sub(r'<br\s*/?>', ' ', m.group(1).strip()) if m else ''
    nm = re.search(r'([^\s　]*紀[^\s　]*)\s*$', sec)
    r = re.search(r'起([^，,。]+)[，,]\s*[盡尽]([^，,。]+)[，,]\s*凡([^。\'}]+?)年', text)
    if r:
        return (nm.group(1) if nm else None), {'start': r.group(1), 'end': r.group(2), 'years': r.group(3).strip(), 'text': r.group(0)}
    r = re.search(r'(?:notes\s*=|】[\s　]*)([^，,。\s|}=】]{4,8})[，,]\s*([一二三四五六七八九十百]+)年', text)
    if r:
        return (nm.group(1) if nm else None), {'start': r.group(1), 'end': None, 'years': r.group(2), 'text': r.group(0)}
    return (nm.group(1) if nm else None), None


POS = {'〇': 0, '零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
YEAR_MARK = re.compile(r'([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])[，、,]\s*(?:公元|西元)(前?)([〇零一二三四五六七八九0-9]+)年')


def body_years(title):
    """Years (ganzhi, year) named by the year headings in the body, for volumes whose header has no 起…盡 line."""
    j = json.loads(get(API, {'action': 'query', 'prop': 'revisions', 'rvprop': 'content', 'rvslots': 'main', 'titles': title,
                              'format': 'json', 'formatversion': 2}))
    time.sleep(1.2)
    text = j['query']['pages'][0]['revisions'][0]['slots']['main']['content']
    found = []
    for gz, bc, digits in YEAR_MARK.findall(text):
        y = int(''.join(str(POS.get(ch, ch)) for ch in digits))
        found.append((gz, -y if bc else y))
    return found


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    idx = download(TITLE)
    raw = get('https://zh.wikisource.org/wiki/' + quote(TITLE, safe='/'))
    (DEST / 'index.html.snapshot').write_text(raw)
    idx['raw_snapshot'] = 'sources/zizhitongjian/index.html.snapshot'
    idx['raw_sha256'] = hashlib.sha256(raw.encode()).hexdigest()
    save(DEST / 'index.json', idx)
    soup = BeautifulSoup(raw, 'html.parser')
    main_el = soup.select_one('#mw-content-text .mw-parser-output')
    groups, cur = [], None
    for el in main_el.descendants:
        name = getattr(el, 'name', None)
        if name == 'h2':
            cur = {'ji': el.get_text(strip=True), 'items': []}
            groups.append(cur)
        elif name == 'a' and cur is not None and el.get('href', '').startswith('/wiki/'):
            from urllib.parse import unquote
            t = unquote(el['href'][len('/wiki/'):]).replace('_', ' ')
            cur['items'].append((t, el.get_text(strip=True)))
    ji_groups = [g for g in groups if g['ji'] != '附録']
    appendix = next(g for g in groups if g['ji'] == '附録')
    appendix['items'] = [x for x in appendix['items'] if 'zh.wikipedia' not in x[0] and x[1] != '公有领域' and 'http' not in x[0]]
    vol_titles = [t for g in ji_groups for t, _ in g['items']]
    assert vol_titles == [f'{TITLE}/卷{i:03}' for i in range(1, 295)], 'volume links are not 卷001..卷294 in order'
    heads = raw_wikitext(vol_titles + [t for t, _ in appendix['items']])
    raws = []
    for g in ji_groups:
        for t, _label in g['items']:
            h = heads[t]
            hdr_name, rng = parse_header(h['text'])
            for sec_no in (1, 2):
                if rng:
                    break

                def fetch_section(t=t, sec_no=sec_no):
                    j = json.loads(get(API, {'action': 'query', 'prop': 'revisions', 'rvprop': 'content', 'rvslots': 'main',
                                              'rvsection': sec_no, 'titles': t, 'format': 'json', 'formatversion': 2}))
                    time.sleep(1.2)
                    try:
                        return j['query']['pages'][0]['revisions'][0]['slots']['main']['content'][:800]
                    except (KeyError, IndexError):
                        return ''
                _, rng = parse_header('|section=' + (hdr_name or '') + '\n' + cached(f'sec{sec_no}:{t}', fetch_section))
            derived = False
            if not rng:      # no 起…盡 line anywhere in the header: use the year headings found in the body
                marks = [tuple(m) for m in cached(f'body:{t}', lambda: body_years(t))]
                assert marks, (t, 'no year headings in the body either')
                lo, hi = min(marks, key=lambda m: m[1]), max(marks, key=lambda m: m[1])
                rng = {'start': lo[0], 'end': hi[0], 'years': '', 'text': f'（据正文年份标目：{lo[0]}{lo[1]}年至{hi[0]}{hi[1]}年）',
                       'fixed': (lo[1], hi[1])}
                derived = True
            seq = sum(1 for x in raws if x['ji'] == g['ji']) + 1
            name = f'{g["ji"]}{to_cn(seq)}'
            if hdr_name:
                tr = str.maketrans('晋汉后陈齐纪', '晉漢後陳齊紀')
                assert name in hdr_name.translate(tr), (t, hdr_name, name)
            nyears = cn_number(rng['years']) if rng['years'] else None
            raws.append({'n': int(t[-3:]), 'ji': g['ji'], 'title': t, 'name': name, 'revision': h['revid'], 'rng': rng,
                         'derived': derived, 'si': ganzhi_index(rng['start']),
                         'ei': ganzhi_index(rng['end']) if rng['end'] else None, 'nyears': nyears})

    def gz_year(y):
        return ((y if y > 0 else y + 1) - 4) % 60

    def nxt(y):
        return 1 if y == -1 else y + 1

    def forward(index, start):
        y = start
        for _ in range(200):
            if y != 0 and gz_year(y) == index:
                return y
            y = nxt(y)
        raise ValueError(index)

    vols, notes_diff = [], []
    prev_end = None
    for k_, r in enumerate(raws):
        rng = r['rng']
        corrected = False
        if prev_end is None:
            y0 = -403
            assert gz_year(y0) == r['si'], r
        else:
            prefer = [prev_end, nxt(prev_end)] if vols[-1]['end_month'] else [nxt(prev_end), prev_end]
            ok_start = [y for y in prefer if gz_year(y) == r['si']]
            y0 = ok_start[0] if ok_start else prefer[0]
            corrected |= not ok_start
        nxt_si = raws[k_ + 1]['si'] if k_ + 1 < len(raws) else None
        cands = []
        if r['derived']:
            cands.append(rng['fixed'][1])
        else:
            cands.append(forward(r['ei'], y0) if r['ei'] is not None else None)
            if r['nyears']:
                y = y0
                for _ in range(r['nyears'] - 1):
                    y = nxt(y)
                cands.append(y)
        cands = [c for c in cands if c is not None]

        def consistent(y):
            return nxt_si is None or gz_year(y) == nxt_si or gz_year(nxt(y)) == nxt_si
        good = [c for c in cands if consistent(c) and c >= y0]
        if good:
            y1 = good[0]
            corrected |= y1 != cands[0]
        else:       # both readings contradict the next volume's start: end where that volume begins
            c3 = forward(nxt_si, y0)
            alts = [c3, c3 - 1 if c3 != 1 else -1]
            ref = cands[-1]
            y1 = min(alts, key=lambda y: abs(y - ref))
            corrected = True
        span_years = y1 - y0 + 1 - (1 if y0 < 0 <= y1 else 0)
        if r['nyears'] and span_years != r['nyears']:
            notes_diff.append((f'{r["n"]:03}', span_years, r['nyears'], rng['text']))
        prev_end = y1
        ei = gz_year(y1)
        sm = split_month(rng['start'])[1]
        em = split_month(rng['end'] or '')[1]
        vols.append({'n': r['n'], 'ji': r['ji'], 'title': r['title'], 'name_trad': r['name'], 'revision': r['revision'],
                     'range_trad': rng['text'], 'span_years': span_years, 'stated_years': r['nyears'], 'start_year': y0, 'end_year': y1,
                     'start_ganzhi': CANON[gz_year(y0)], 'end_ganzhi': CANON[ei],
                     'start_gz': TIANGAN[gz_year(y0) % 10] + DIZHI[gz_year(y0) % 12], 'end_gz': TIANGAN[ei % 10] + DIZHI[ei % 12], 'start_month': sm, 'end_month': em,
                     'derived_from_body': r['derived'], 'chain_corrected': corrected,
                     'source_typo': not (is_canonical(rng['start']) and (not rng['end'] or is_canonical(rng['end'])))})
    print('span differences (computed vs stated):', notes_diff)
    print('derived from body:', [v['n'] for v in vols if v['derived_from_body']])
    print('chain-corrected:', [v['n'] for v in vols if v['chain_corrected']])
    assert len(vols) == 294 and vols[-1]['end_year'] == 959, (len(vols), vols[-1])
    # simplified strings via MediaWiki's own conversion
    strings = [g['ji'] for g in ji_groups] + [v['name_trad'] for v in vols] + [v['range_trad'] for v in vols] + [l for _, l in appendix['items']]
    simp = simplify(strings)
    k = len(ji_groups)
    ji_simple = dict(zip([g['ji'] for g in ji_groups], simp[:k]))
    for i, v in enumerate(vols):
        v['name'] = simp[k + i]
        v['range'] = simp[k + 294 + i]
    app = []
    for (t, label), s in zip(appendix['items'], simp[k + 588:]):
        info = heads.get(t)
        app.append({'title': t, 'label': s, 'revision': info['revid'] if info else None,
                    'url': 'https://zh.wikisource.org/zh-hans/' + quote(t.replace(' ', '_'), safe='/()')})
    catalog = {
        'book': '资治通鉴', 'author': '［宋］司马光 撰，［元］胡三省 音注', 'volumes_total': 294,
        'source': {'title': TITLE, 'url': idx['url'], 'revision': idx['revision'], 'snapshot': 'sources/zizhitongjian/index.json'},
        'scope': '仅目录：纪、卷次、卷名、起止纪年（干支、年数、公元年）；正文、白话、注释尚未整理',
        'ji': [{'name': ji_simple[g['ji']], 'first': int(g['items'][0][0][-3:]), 'last': int(g['items'][-1][0][-3:]),
                'volumes': len(g['items'])} for g in ji_groups],
        'volumes': [{'n': v['n'], 'slug': f'juan{v["n"]:03}', 'ji': ji_simple[v['ji']], 'name': v['name'], 'range': v['range'],
                     'span_years': v['span_years'], 'stated_years': v['stated_years'], 'start_year': v['start_year'], 'end_year': v['end_year'],
                     'start_ganzhi': v['start_ganzhi'], 'end_ganzhi': v['end_ganzhi'], 'start_gz': v['start_gz'], 'end_gz': v['end_gz'], 'start_month': v['start_month'], 'end_month': v['end_month'],
                     'source_typo': v['source_typo'], 'derived_from_body': v['derived_from_body'], 'chain_corrected': v['chain_corrected'],
                     'url': 'https://zh.wikisource.org/zh-hans/' + quote(v['title'].replace(' ', '_'), safe='/'),
                     'revision': str(v['revision']), 'status': 'catalog_only'} for v in vols],
        'appendix': app,
    }
    save(DEST / 'catalog.json', catalog)
    print('volumes', len(vols), 'ji', [(j['name'], j['first'], j['last']) for j in catalog['ji']])
    print('appendix', [(a['label'], a['revision']) for a in app])
    print(catalog['volumes'][0], catalog['volumes'][-1], sep='\n')


if __name__ == '__main__':
    main()
