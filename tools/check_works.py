#!/usr/bin/env python3
"""Audit 关汉卿杂剧、赵氏孤儿、倩女离魂、墙头马上、拜月亭、林兰香（原文＋题解＋基础注释）与声律启蒙（逐句白话）：
来源哈希、原文逐字覆盖、题解、注释词条、网页注释按钮数与渲染。"""
import json
import sys
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
import build
import prepare_works as prep
from prepare_zizhitongjian_fulu import strip_p

EXPECT = {'guanhanqing': (18, 81), 'zhaoshigu': (1, 6), 'qiannulihun': (1, 5), 'qiangtoumashang': (1, 4), 'baiyueting': (1, 5),
          'linlanxiang': (65, 65), 'shenglvqimeng': (2, 30)}


def audit(book):
    progress = json.loads((ROOT / f'sources/{book}/progress.json').read_text(encoding='utf8'))
    gloss = book in prep.GLOSS
    want_pages = prep.pages(book)
    assert [p['slug'] for p in progress['pages']] == [w[0] for w in want_pages], book
    nsec = nnotes = npairs = 0
    for p, (slug, label, srcname, want) in zip(progress['pages'], want_pages):
        src = prep.src(book, srcname)
        assert src['revision'] == p['source']['revision'] and src['text_sha256'] == p['source']['text_sha256'], (book, slug)
        got = build.parse_poems(sorted((ROOT / 'src' / book / slug).glob('*.txt')))
        assert [w['title'] for w in want] == [g['title'] for g in got], (book, slug, 'sections')
        pairs = []
        for w, g in zip(want, got):
            # 行尾空格在解析时会被去掉，故比较时忽略空白
            wtext = ''.join(w['paras']).replace('/', '').replace(' ', '')
            gtext = ''.join(c['o'] for c in g['chunks']).replace('/', '').replace(' ', '')
            if gloss:
                assert strip_p(wtext) == strip_p(gtext), (book, slug, g['title'], 'coverage')
            else:
                assert wtext == gtext, (book, slug, g['title'], 'original differs')
            assert g['intro'], (book, slug, g['title'], '题解')
            seen = set()
            for c in g['chunks']:
                if gloss:
                    assert c['t'] and len(c['t'].split('¦')) == len(build._frag_groups(build.split_sents(c['o']))), (book, slug, g['title'], c['o'][:20])
                    pairs.extend(build.split_pairs(c['o'], c['t']))
                else:
                    assert c['t'] is None, (book, slug, 'unexpected translation')
                for n in c['notes']:
                    term = n.split('：', 1)[0]
                    assert term in c['o'] and term not in seen, (book, slug, g['title'], n)
                    seen.add(term)
                nnotes += len(c['notes'])
        html = BeautifulSoup((ROOT / book / (slug + '.html')).read_text(), 'html.parser')
        if gloss:
            assert [(n.get_text(), n['data-t']) for n in html.select('.s[data-t]')] == [(o.replace('/', ''), t) for o, t in pairs], (book, slug, 'rendered pairs')
            npairs += len(pairs)
        rendered = 0
        for b in html.select('button.note-btn'):
            import re
            m = re.search(r'注释（(\d+)）', b.get_text())
            if not m:
                continue
            t = html.find(id=b['aria-controls'])
            assert t.has_attr('hidden') and int(m[1]) == len(t.find_all('li', recursive=False)), (book, slug, 'note button')
            rendered += int(m[1])
        assert rendered == sum(len(c['notes']) for g in got for c in g['chunks']), (book, slug, 'rendered notes')
        nsec += len(want)
    assert (len(progress['pages']), nsec) == EXPECT[book], (book, len(progress['pages']), nsec)
    if book != 'shenglvqimeng':
        tj = build.parse_poems(sorted((ROOT / 'src' / book / 'tijie').glob('*.txt')))
        assert tj and tj[0]['intro'], (book, 'tijie')
    return len(progress['pages']), nsec, npairs, nnotes


def main():
    for book in EXPECT:
        pages, secs, pairs, notes = audit(book)
        print(f'OK {book}: {pages} pages, {secs} sections, {notes} notes' + (f', {pairs} sentence pairs' if pairs else ''))


if __name__ == '__main__':
    main()
