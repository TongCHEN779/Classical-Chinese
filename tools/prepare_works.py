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
import os
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
          'baiyueting': '拜月亭', 'linlanxiang': '林兰香', 'shenglvqimeng': '声律启蒙', 'yanzi': '晏子春秋', 'zhouyi': '周易',
          'lunyu': '论语', 'mengzi': '孟子', 'zhuangzi': '庄子', 'daodejing': '道德经'}
# 资治通鉴已整理的卷：周秦汉魏，再加宋齐梁陈隋（唐纪185-265暂缓）
ZTJJ_DONE = list(range(1, 295))
ZTJJ_RUN_START = (9, 69, 79, 119, 135, 145, 167, 177, 266, 272, 280, 286, 290)
GLOSS = {'shenglvqimeng', 'zizhitongjian', 'yanzi', 'zhouyi', 'lunyu', 'mengzi', 'zhuangzi', 'daodejing'}
PIECE = {'guanhanqing': 12000, 'zhaoshigu': 12000, 'qiannulihun': 12000, 'qiangtoumashang': 12000, 'baiyueting': 12000,
         'linlanxiang': 12000, 'shenglvqimeng': 4500, 'zizhitongjian': 6000, 'jinghuayuan': 12000, 'yanzi': 4500, 'zhouyi': 5000,
         'lunyu': 3000, 'mengzi': 4000, 'zhuangzi': 4500, 'daodejing': 2200}
MAXSEC = {'lunyu': 40, 'mengzi': 30, 'daodejing': 20}     # 每个作业片段最多的节数（章短而多）
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


LUNYU_NAMES = ['学而第一', '为政第二', '八佾第三', '里仁第四', '公冶长第五', '雍也第六', '述而第七', '泰伯第八', '子罕第九', '乡党第十',
               '先进第十一', '颜渊第十二', '子路第十三', '宪问第十四', '卫灵公第十五', '季氏第十六', '阳货第十七', '微子第十八', '子张第十九', '尧曰第二十']
MENGZI_NAMES = [a + b for a in ('梁惠王', '公孙丑', '滕文公', '离娄', '万章', '告子', '尽心') for b in ('上', '下')]
ZHUANGZI_NAMES = ['逍遥游', '齐物论', '养生主', '人间世', '德充符', '大宗师', '应帝王', '骈拇', '马蹄', '胠箧', '在宥', '天地', '天道', '天运', '刻意', '缮性', '秋水', '至乐',
                  '达生', '山木', '田子方', '知北游', '庚桑楚', '徐无鬼', '则阳', '外物', '寓言', '让王', '盗跖', '说剑', '渔父', '列御寇', '天下']


def _classics4_pages(book):
    """论语（每章一节）、孟子（每章一节）、庄子（每段一节）、道德经王弼本（经文，每章一节）。"""
    out = []
    if book == 'lunyu':
        for k, nm in enumerate(LUNYU_NAMES, 1):
            d = src(book, f'juan{k:02}.json')
            ps = [clean(b['text']) for b in d['blocks'] if b['type'] == 'p']
            out.append((f'juan{k:02}', nm, f'juan{k:02}.json', [{'title': f'第{cn(i)}章', 'paras': [t]} for i, t in enumerate(ps, 1)]))
    elif book == 'mengzi':
        for k, nm in enumerate(MENGZI_NAMES, 1):
            d = src(book, f'juan{k:02}.json')
            secs = []
            for b in d['blocks']:
                if b['type'] == 'h3':
                    secs.append({'title': f'第{cn(int(b["text"]))}章', 'paras': []})
                elif b['type'] == 'p' and b['text'] != '上一篇回目录下一篇':    # 末尾的网页导航文字不是正文
                    secs[-1]['paras'].append(clean(b['text']))
            out.append((f'juan{k:02}', nm, f'juan{k:02}.json', secs))
    elif book == 'zhuangzi':
        for k, nm in enumerate(ZHUANGZI_NAMES, 1):
            d = src(book, f'pian{k:02}.json')
            ps = [clean(b['text']) for b in d['blocks'] if b['type'] == 'p']
            part = '内篇' if k <= 7 else ('外篇' if k <= 22 else '杂篇')
            out.append((f'pian{k:02}', f'{part}·{nm}', f'pian{k:02}.json', [{'title': f'第{cn(i)}段', 'paras': [t]} for i, t in enumerate(ps, 1)]))
    else:
        d = src(book, 'main.json')
        chap, cur = [], None
        for b in d['blocks']:
            if b['type'] == 'h2':
                if not b['text'].endswith('章'):
                    break
                cur = []
                chap.append(cur)
            elif b['type'] == 'p' and cur is not None:
                if b['text'].startswith('王弼老子道德经二卷'):    # 第八十一章之后是晁说之、熊克的跋，不属经文
                    cur = None
                    continue
                cur.append(clean(b['text']))
        assert len(chap) == 81, len(chap)
        secs = [{'title': f'第{cn(i)}章', 'paras': [''.join(x)]} for i, x in enumerate(chap, 1)]
        out.append(('dao', '道经（第一至三十七章）', 'main.json', secs[:37]))
        out.append(('de', '德经（第三十八至八十一章）', 'main.json', secs[37:]))
    return out


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
    elif book == 'yanzi':
        names = ['内篇谏上', '内篇谏下', '内篇问上', '内篇问下', '内篇杂上', '内篇杂下', '外篇上', '外篇下']
        for k, nm in enumerate(names, 1):
            d = src(book, f'juan{k:02}.json')
            secs = []
            for b in d['blocks']:
                if b['type'] == 'h3' or (b['type'] == 'h2' and k <= 6):
                    secs.append({'title': clean(b['text']), 'paras': []})
                elif b['type'] == 'p':
                    secs[-1]['paras'].append(clean(b['text']).replace('\n', '/'))
            out.append((f'juan{k:02}', f'卷{cn(k)}·{nm}', f'juan{k:02}.json', secs))
    elif book in ('lunyu', 'mengzi', 'zhuangzi', 'daodejing'):
        out.extend(_classics4_pages(book))
    elif book == 'zhouyi':
        for i in range(1, 65):
            d = src(book, f'gua{i:02d}.json')
            bl = d['blocks']
            assert bl[0]['type'] == 'head' and bl[1]['type'] == 'p' and bl[1]['text'].endswith('上'), (i, bl[:2])
            name, xs = bl[0]['text'], bl[1]['text']
            secs, cur, mode = [], None, None
            for b in bl[2:]:
                if b['type'] == 'head':
                    mode = b['text']
                    assert mode in ('易经：', '彖曰：', '象曰：', '文言曰：'), (i, mode)
                    cur = {'title': {'易经：': '卦辞、爻辞', '彖曰：': '彖传', '象曰：': '象传', '文言曰：': '文言传'}[mode], 'paras': []}
                    secs.append(cur)
                    continue
                cur['paras'].append(clean(b['text']))
            out.append((f'gua{i:02d}', f'第{cn(i)}卦·{name}｜{xs}', f'gua{i:02d}.json', secs))
        for i, nm in enumerate(['系辞上', '系辞下', '说卦', '序卦', '杂卦'], 1):
            d = src(book, f'zhuan{i:02d}.json')
            secs = [{'title': f'第{cn(k)}节', 'paras': [clean(b['text'])]} for k, b in enumerate(d['blocks'], 1)]
            out.append((f'zhuan{i:02d}', f'易传·{nm}', f'zhuan{i:02d}.json', secs))
    elif book == 'zizhitongjian':
        for k in ZTJJ_DONE:
            d = src(book, f'juan{k:03d}.json')
            secs = ztjj_sections(d, 185 <= k <= 265)
            out.append((f'juan{k:03d}', f'卷{cn(k)}', f'juan{k:03d}.json', ztjj_year_split(k, secs) if k in ZTJJ_YEAR_SPLIT else secs))
    return out


YEAR_HEAD = re.compile(r'[（〈].*?西?元?前.*?[）〉]|[（〈][甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]')


def ztjj_body(t):
    """资治通鉴：去掉段首的校记脚注序号；按点校者的校改符号取定本：(…)为删去的误字，〔…〕为补入或改正的字。"""
    t = re.sub(r'^\d+', '', t.strip())
    t = re.sub(r'\([^)]*\)', '', t)
    t = t.replace('〔', '').replace('〕', '')
    return clean(t).replace('\n', '/')


# 卷首“【隋纪五】”之类的纪名标签：页标题已有，不收
ZTJJ_LABEL = r'^【[^】]*】◎?(?:[后前]?[梁唐晋汉周宋齐陈隋魏秦]纪[一二三四五六七八九十]+)?/?'


def ztjj_sections(d, strip_heads=False):
    secs, cur, wang_start = [], None, False

    def new(title, intro):
        nonlocal cur
        cur = {'title': re.sub(r'\s+', '', title).replace('（（', '（').replace('））', '）'), 'paras': [], 'intro': intro}
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
        elif t in ('p', 'dd', 'pre'):
            if ztjj_body(b['text']) != '_':
                cur['paras'].append(ztjj_body(b['text']))
        elif t == 'li' and cur['title'] == '校刊记':
            cur['paras'].append(clean(re.sub(r'^↑\s*', '', b['text'])).replace('\n', '/'))
    if secs and secs[0]['paras']:    # 卷首的“资治通鉴 第NNN卷”和随后的“卷第某”是原站页面标题，卷号已在页标题里，不收
        for pat in (r'^资治通鉴\s*第?\s*\d+卷/?', r'^卷第[一二三四五六七八九十百零〇]+/?', ZTJJ_LABEL):
            if secs[0]['paras']:
                secs[0]['paras'][0] = re.sub(pat, '', secs[0]['paras'][0])
                if not secs[0]['paras'][0]:
                    secs[0]['paras'].pop(0)
    for a, b in (zip(secs, secs[1:]) if strip_heads else ()):    # 原站在下一帝名下首年标题前另起一行帝号，被归到了上一节末尾：拿掉
        segs = a['paras'][-1].split('/') if a['paras'] else []
        if segs and len(segs[-1]) <= 40 and re.fullmatch(r'[^。！？，；：”’]*(?:皇帝|皇后)(?:[上中下]|之[上中下])?(?:之[上中下])?', segs[-1].replace(' ', '')) and not YEAR_HEAD.search(segs[-1]):
            if len(segs) > 1:
                a['paras'][-1] = '/'.join(segs[:-1])
            else:
                a['paras'].pop()
    for s_ in secs:
        s_['paras'] = [x for x in ('/'.join(y for y in p_.split('/') if not y.startswith('[[category')) for p_ in s_['paras']) if x]
    return [s_ for s_ in secs if s_['paras']]


# 魏纪（卷七十三至七十八）、宋纪、齐纪、梁纪里原站不分年的整卷：按“春，”起首的段（每年首事）把卷首之后分成年节
ZTJJ_YEAR_SPLIT = (set(range(73, 79)) | set(range(119, 135)) | set(range(136, 156)) | set(range(157, 167))
                   | {80} | set(range(82, 86)) | set(range(87, 96)) | {100, 101, 102} | set(range(104, 119))
                   | set(range(272, 288)) | {289, 291, 292}
                   | (set(range(185, 266)) - {188, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 216, 237, 244, 246, 252, 255} - set(range(185, 188)) - {189}))
ZTJJ_YEAR_STARTS = {75: ('夏，五月，以征西将军郭淮为车骑将军',), 78: ('秋，八月，乙酉，吴主立皇后朱氏',)}   # 这两卷有的年份首事不以“春”起，据正文人工定位
STEMS, BRANCHES = '甲乙丙丁戊己庚辛壬癸', '子丑寅卯辰巳午未申酉戌亥'


def cn_digits(y):
    return ''.join('〇一二三四五六七八九'[int(c)] for c in str(y))


YEAR_LINE = re.compile(r'[（(][甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥][，,、\s]|公元.{1,6}年$')


def ztjj_year_info(k, segs):
    """(各年首段下标, 各年标题, 各年标题行下标或 None)。年份链取自 catalog.json 的卷首“起…尽…”换算；
    原站在年首另起一行写着“帝号＋年号（干支，公元某年）”的，用它作节名并从正文拿掉，没有的才用“干支年（公元某年）”。"""
    import json as _j
    v = _j.loads((ROOT / 'sources/zizhitongjian/catalog.json').read_text(encoding='utf8'))['volumes'][k - 1]
    ys = list(range(v['start_year'], v['end_year'] + 1))
    orig = [i for i, x in enumerate(segs) if x.startswith('春，') or x.startswith(ZTJJ_YEAR_STARTS.get(k, ('\0',)))]
    if len(orig) != len(ys):    # 年首不都以“春”起的卷：改按原站的年份标题行定年首
        orig = [i for i, x in enumerate(segs) if len(x.strip()) <= 60 and YEAR_LINE.search(x.strip())]
    assert len(orig) == len(ys), (k, len(orig), len(ys))
    idx, titles, heads = [], [], []
    for j, (y, o) in enumerate(zip(ys, orig)):
        i = o
        floor = (orig[j - 1] + 1) if j else 1
        while i - 1 >= floor and len(segs[i - 1]) <= 60 and segs[i - 1][-1] not in '。！？”’；：，、':
            i -= 1    # 紧挨在年首前、不带句末标点的短行是原站的帝号或年份标题，归入该年
        h = next((x for x in range(o, i - 1, -1) if len(segs[x].strip()) <= 60 and YEAR_LINE.search(segs[x].strip())), None)
        idx.append(i)
        heads.append(h)
        titles.append(re.sub(r'\s+', '', segs[h].replace('〈', '（').replace('〉', '）')).replace('（（', '（').replace('））', '）').lstrip('◎') if h is not None
                      else f'{STEMS[(y - 4) % 10]}{BRANCHES[(y - 4) % 12]}年（公元{cn_digits(y)}年）')
    assert len(set(titles)) == len(titles), (k, titles)
    return idx, titles, heads


def ztjj_year_split(k, secs):
    assert len(secs) == 1 and secs[0]['title'] == '卷首', k
    segs = [x for p in secs[0]['paras'] for x in p.split('/')]
    idx, titles, heads = ztjj_year_info(k, segs)
    ends = idx[1:] + [len(segs)]
    out = [{'title': '卷首', 'paras': ['/'.join(segs[:idx[0]])], 'intro': True}]
    for t, a, b, h in zip(titles, idx, ends, heads):
        out.append({'title': t, 'paras': ['/'.join(x for n, x in enumerate(segs[a:b], a) if n != h)], 'intro': False})
    return out


def pieces(book):
    out, cur = [], None
    only = os.environ.get('ZTJJ_ONLY_VOLS')    # 如“79-118”：只给这些卷切分作业片段
    lo, hi = map(int, only.split('-')) if only else (0, 10 ** 9)
    for slug, label, srcname, secs in pages(book):
        if book == 'zizhitongjian' and not lo <= int(slug[4:]) <= hi:
            continue
        if book == 'yanzi' and slug == 'juan01':    # 卷一已整理合并
            continue
        for s in secs:
            n = sum(len(x) for x in s['paras'])
            if cur is None or (cur['chars'] + n > PIECE[book] and cur['chars'] > 0) or len(cur['secs']) >= MAXSEC.get(book, 10 ** 9) or (book == 'zizhitongjian' and int(slug[4:]) in ZTJJ_RUN_START and cur['secs'][-1][0] != slug):
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
            if book == 'zizhitongjian' and slug not in kept:
                continue    # 分批整理中尚未合并的卷
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
