#!/usr/bin/env python3
"""缓存维基文库上的白话小说、话本、笔记、元杂剧与明清传奇原文，写入 sources/<slug>/chapters.json，
并生成 src/<slug>/<页>/01.txt、sources/<slug>/pages.json（供 build.py 的 _orig_spec 使用），页首提要并入 sources/wiki_intros.json。
这批书只收原文；维基文库页面上自带的注释（〈…〉小字、页内脚注）一并保留，不另行撰写。

  python3 tools/fetch_vernacular.py fetch [slug ...]     取各卷/回页面（可断点续传；不带 slug 取全部）
  python3 tools/fetch_vernacular.py prepare [slug ...]   生成 src 与 pages.json、写入简介
  python3 tools/fetch_vernacular.py authors              打印各书维基文库页面上的作者链接（核对作者用）

每书一项：slug: (书名, 维基文库页名, 取页方式)。取页方式：
  links：总目录页上该书各子页的链接顺序（页面标题取链接文字）；single：整书一页（杂剧），每个折/楔子为一节。
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote, unquote
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fetch_wenxuan import fetch
from fetch_orig import items
from fetch_quantangwen import sections_of, clean_markup

BOOKS = {
    # 元杂剧（元曲选，每剧一页）
    "wutongyu": ("梧桐雨", "唐明皇秋夜梧桐雨", "single"),
    "hangongqiu": ("汉宫秋", "破幽夢孤雁漢宮秋", "single"),
    "jianfubei": ("荐福碑", "半夜雷轟薦福碑", "single"),
    "qingshanlei": ("青衫泪", "江州司馬青衫淚", "single"),
    "wangcandenglou": ("王粲登楼", "醉思鄉王粲登樓", "single"),
    "likuifujing": ("李逵负荆", "梁山泊李逵負荊", "single"),
    "kanqiannu": ("看钱奴", "看錢奴買冤家債主", "single"),
    "qiuhuxiqi": ("秋胡戏妻", "魯大夫秋胡戲妻", "single"),
    "chenzhoudimi": ("陈州粜米", "包待制陳州糶米", "single"),
    # 长篇小说
    "fengshenyanyi": ("封神演义", "封神演義", "links"),
    "dongzhoulieguozhi": ("东周列国志", "東周列國志", "links"),
    "suitangyanyi": ("隋唐演义", "隋唐演義", "links"),
    "yingliezhuan": ("英烈传", "英烈傳", "links"),
    "yangjiafu": ("杨家府演义", "楊家府世代忠勇通俗演義", "links"),
    "xiyangji": ("三宝太监西洋记通俗演义", "三寶太監西洋記", "links"),
    "canxuanwudaishi": ("残唐五代史演义传", "殘唐五代史演義傳", "links"),
    "chanzhenyishi": ("禅真逸史", "禪真逸史", "links"),
    # 短篇小说集与笔记
    "jiandengxinhua": ("剪灯新话", "剪燈新話", "links"),
    "jiandengyuhua": ("剪灯余话", "剪燈餘話", "links"),
    "shidiantou": ("石点头", "石點頭", "links"),
    "xihuerji": ("西湖二集", "西湖二集", "links"),
    "qingshi": ("情史", "情史", "links"),
    "gujintangai": ("古今谭概", "古今譚槩", "links"),
    # 明清传奇
    "zixiaoji": ("紫箫记", "紫簫記", "links"),
    "zichaiji": ("紫钗记", "紫釵記", "links"),
    "nankeji": ("南柯记", "南柯記", "links"),
    "handanji": ("邯郸记", "邯鄲記", "links"),
    "pipaji": ("琵琶记", "琵琶記", "links"),
    "jingchaiji": ("荆钗记", "荊釵記", "links"),
    "baituji": ("白兔记", "白兔記", "single"),
    "shagouji": ("杀狗记", "殺狗記", "links"),
    "huanshaji": ("浣纱记", "浣紗記", "links"),
    "yixiaji": ("义侠记", "義俠記", "links"),
    "jiaohongji": ("娇红记", "嬌紅記", "single"),
    "yuzanji": ("玉簪记", "玉簪記", "links"),
    "hongliji": ("红梨记", "紅梨記", "single"),
    "youguiji": ("幽闺记", "幽閨記", "single"),
    "dongguoji": ("东郭记", "東郭記", "links"),
    # 清代小说
    "xingshiyinyuan": ("醒世姻缘传", "醒世姻緣傳", "links"),
    "qiludeng": ("歧路灯", "歧路燈", "links"),
    "lvyexianzong": ("绿野仙踪", "綠野仙蹤", "links"),
    "guwangyan": ("姑妄言", "姑妄言", "links"),
    "zibuyu": ("子不语", "子不語", "links"),
    "xuzibuyu": ("续子不语", "續子不語", "links"),
    "sanxiawuyi": ("三侠五义", "三俠五義", "links"),
    "xiaowuyi": ("小五义", "小五義", "links"),
    "shigongan": ("施公案", "施公案", "links"),
    "ernvyingxiongzhuan": ("儿女英雄传", "兒女英雄傳", "links"),
    "pinhuabaojian": ("品花宝鉴", "品花寶鑒", "links"),
    "huayuehen": ("花月痕", "花月痕", "links"),
    "haishanghualiezhuan": ("海上花列传", "海上花列傳", "links"),
    # 维基文库没有、取自 ctext 的两部（抓取见 tools/fetch_ctext_books.py；这里只供 prepare 生成页面）
    "beisongzhizhuan": ("北宋志传", None, "ctext"),
    "xingshiyan": ("型世言", None, "ctext"),
    # 六十种曲中不与上面重复的各剧（lsz_ 前缀：只作《六十种曲》的材料，不单独成书；prepare 时跳过）
    "lsz_qianjinji": ("千金记", "千金記", "links"), "lsz_bayiji": ("八义记", "八義記", "links"),
    "lsz_sanyuanji": ("三元记", "三元記", "links"), "lsz_beixixiang": ("北西厢", "北西廂記", "links"),
    "lsz_hongfuji": ("红拂记", "紅拂記", "links"), "lsz_huanhunji": ("还魂记", "牡丹亭", "links"),
    "lsz_nanxixiang": ("南西厢", "南西廂記", "links"), "lsz_yujingtaiji": ("玉镜台记", "玉鏡臺記", "links"),
    "lsz_huaixiangji": ("怀香记", "懷香記", "links"), "lsz_yuheji": ("玉合记", "玉合記", "links"),
    "lsz_sixiji": ("四喜记", "四喜記", "links"), "lsz_xiuruji": ("绣襦记", "繡襦記", "links"),
    "lsz_xilouji": ("西楼记", "西樓記", "links"), "lsz_jinqueji": ("金雀记", "金雀記", "links"),
    "lsz_shuihuji": ("水浒记", "水滸記", "links"), "lsz_guanyuanji": ("灌园记", "灌園記", "links"),
    "lsz_zhongyuji": ("种玉记", "種玉記", "links"), "lsz_shuangleiji": ("双烈记", "雙烈記", "links"),
    "lsz_shihouji": ("狮吼记", "獅吼記", "links"), "lsz_tanhuaji": ("昙花记", "曇花記", "links"),
    "lsz_longgaoji": ("龙膏记", "龍膏記", "links"), "lsz_jiexiaji": ("节侠记", "節俠記", "links"),
    "lsz_shuoyuanhuanhunji": ("硕园订本还魂记", "碩園訂本還魂記", "links"),
}
# 已收入《六十种曲》的剧：只作该书的材料（sources/<slug>/chapters.json），不单独成书，prepare 时跳过
IN_LIUSHIZHONGQU = {"zixiaoji", "zichaiji", "nankeji", "handanji", "pipaji", "jingchaiji", "baituji", "shagouji", "huanshaji",
                    "yixiaji", "yuzanji", "hongliji", "youguiji", "dongguoji"}
NOTE = re.compile(r"〈[^〈〉]*〉")


def tidy(t):
    return re.sub(r"[\s　]+", " ", t).strip()


def toc_of(wiki):
    """总目录页上，指向 wiki/ 子页的链接：[(维基页名, 链接文字)]，按页面顺序、去重。"""
    page = fetch(wiki, retries=8)
    root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
    out = []
    for a in root.select("a"):
        h = unquote(a.get("href", ""))
        if h.startswith("/wiki/" + wiki + "/") and "#" not in h and "action=edit" not in h:
            wt = h[6:].replace("_", " ")
            if wt not in [x[0] for x in out]:
                out.append((wt, tidy(a.get_text())))
    return out, page


def page_title(label, fallback):
    t = tidy(label) or fallback
    t = re.sub(r"^第[0-9一二三四五六七八九十百零〇 ]+[回出卷折]", lambda m: m.group(0).replace(" ", ""), t)
    if re.fullmatch(r"[一二三四五六七八九十百零〇]+", t):
        t = "卷" + t
    return t


def refs_of(root):
    """页内脚注（ol.references）的文字，取出后另存；正文里的脚注标号由 items() 去掉。"""
    out = []
    for li in root.select("ol.references li"):
        t = tidy(re.sub(r"^\s*[↑^]\s*", "", li.get_text(" ")))
        t = re.sub(r"\s*↑\s*", "", t)
        if t:
            out.append(t)
    return out


def do_fetch(want):
    for slug, (title, wiki, mode) in BOOKS.items():
        if (want and slug not in want) or mode == "ctext":
            continue
        d = ROOT / "sources" / slug
        d.mkdir(parents=True, exist_ok=True)
        cache = d / "chapters.json"
        done = {c["slug"]: c for c in json.loads(cache.read_text(encoding="utf8"))} if cache.exists() else {}
        if mode == "single":
            jobs = [("p001", title, wiki)]
        else:
            toc, _ = toc_of(wiki)
            jobs = [(f"p{i:03d}", page_title(lab, wt.rsplit("/", 1)[-1]), wt) for i, (wt, lab) in enumerate(toc, 1)]
            if not jobs:                          # 没有子页：整剧在一页里，按标题分节
                print("NO LINKS → 单页", slug, wiki, flush=True)
                jobs = [("p001", title, wiki)]
        print(slug, title, len(jobs), "页", flush=True)
        for i, (pslug, ptitle, wt) in enumerate(jobs, 1):
            if pslug in done:
                continue
            try:
                page = fetch(wt, retries=8)
            except Exception as e:
                print("SKIP", slug, pslug, wt, type(e).__name__, flush=True)
                continue
            root = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
            refs = refs_of(root)
            secs = sections_of(list(items(root)))
            if mode == "links" and len(secs) == 1 and secs[0]["title"] in ("正文", ""):
                secs[0]["title"] = ptitle
            done[pslug] = {"slug": pslug, "title": ptitle, "head": "", "url": "https://zh.wikisource.org/zh-hans/" + quote(wt),
                           "revision": str(page["revid"]), "heads": [], "sections": secs, **({"refs": refs} if refs else {})}
            print(slug, pslug, ptitle[:24], len(secs), sum(len(p) for s in secs for p in s["paragraphs"]), flush=True)
            if i % 10 == 0:
                cache.write_text(json.dumps(list(done.values()), ensure_ascii=False, indent=1) + "\n", encoding="utf8")
        cache.write_text(json.dumps(list(done.values()), ensure_ascii=False, indent=1) + "\n", encoding="utf8")


def book_intro(wiki):
    page = fetch(wiki, retries=8)
    r = BeautifulSoup(page["text"], "html.parser").select_one(".mw-parser-output")
    tbs = r.find_all("table", recursive=False)
    div = r.find("div", recursive=False)
    if div:
        tbs += div.find_all("table", recursive=False)
    best = ""
    for tb in tbs:
        for br in tb.find_all("br"):
            br.replace_with("\n")
        for p in tb.find_all("p"):
            p.append("\n")
        txt = re.sub(r"\[\d+\]", "", tb.get_text(""))
        txt = "\n".join(re.sub(r"\s+", "", l) for l in txt.split("\n") if l.strip())
        txt = re.sub(r"^姊妹计划:[^《“]*", "", txt)
        txt = re.sub(r"\n?维基百科条目：[^\n]*", "", txt)
        txt = re.sub(r"姊妹计划:.*$", "", txt).strip()
        if len(txt) > len(best) and len(txt) > 40 and not re.match(r"^(←|<|作者)", txt):
            best = txt
    return best, str(page["revid"])


def do_prepare(want):
    wi_path = ROOT / "sources/wiki_intros.json"
    wi = json.loads(wi_path.read_text(encoding="utf8"))
    for slug, (title, wiki, mode) in BOOKS.items():
        if (want and slug not in want) or slug.startswith("lsz_") or slug in IN_LIUSHIZHONGQU:
            continue
        src_json = ROOT / "sources" / slug / "chapters.json"
        if not src_json.exists():
            print("MISSING", slug)
            continue
        chapters = json.loads(src_json.read_text(encoding="utf8"))
        chapters.sort(key=lambda c: c["slug"])
        out_dir = ROOT / "src" / slug
        pages, kept = [], []
        for ch in chapters:
            secs = []
            for s in ch["sections"]:
                paras = [clean_markup(p).strip() for p in s["paragraphs"]]
                paras = [p for p in paras if re.search(r"[一-鿿]", p)]
                if paras:
                    secs.append({**s, "paragraphs": paras})
            refs = [clean_markup(r).strip() for r in ch.get("refs", []) if re.search(r"[一-鿿]", r)]
            if not secs:
                print("EMPTY", slug, ch["slug"], ch["title"])
                continue
            if refs:                                   # 页内脚注：作为该页末节的小注，渲成灰色小字
                secs[-1]["paragraphs"] = secs[-1]["paragraphs"] + ["〈注：" + "；".join(refs) + "〉"]
                ch.pop("refs", None)                   # 已并入正文，免得重复运行时再并一次
            ch["sections"] = secs
            d = out_dir / ch["slug"]
            d.mkdir(parents=True, exist_ok=True)
            lines = []
            for s in secs:
                lines.append("# " + s["title"])
                lines += ["原：" + p for p in s["paragraphs"]]
                lines.append("")
            (d / "01.txt").write_text("\n".join(lines), encoding="utf8")
            pages.append([ch["slug"], ch["title"], None])
            kept.append(ch)
        n = len(pages)
        if n > 60:                                     # 篇幅长的书按五十页一组分段，组名“第1至第50回”
            numbered = [p for p in pages if re.match(r"^第.+[回出]", p[1])]
            unit = "出" if numbered and "出" in numbered[0][1][:8] else "回"
            for j, p in enumerate(numbered):
                lo = j // 50 * 50 + 1
                p[2] = f"第{lo}至第{min(lo + 49, len(numbered))}{unit}"
        (ROOT / "sources" / slug / "chapters.json").write_text(json.dumps(kept, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
        (ROOT / "sources" / slug / "pages.json").write_text(json.dumps(pages, ensure_ascii=False, indent=1) + "\n", encoding="utf8")
        print(slug, title, n, "页", sum(len(p) for c in kept for s in c["sections"] for p in s["paragraphs"]), "字")
        if wiki and (slug not in wi or wi[slug].get("auto")):
            txt, rev = book_intro(wiki)
            if txt:
                wi[slug] = {"wikisource_title": wiki, "revision": rev, "url": "https://zh.wikisource.org/zh-hans/" + quote(wiki),
                            "text": txt, "verbatim": True}
                print("  intro", len(txt))
    wi_path.write_text(json.dumps(wi, ensure_ascii=False, indent=1), encoding="utf8")


def do_authors():
    for slug, (title, wiki, mode) in BOOKS.items():
        page = fetch(wiki, retries=8)
        r = BeautifulSoup(page["text"], "html.parser")
        au = [unquote(a["href"])[6:].replace("Author:", "") for a in r.select('a[href^="/wiki/Author:"]')]
        print(slug, title, au[:4], flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "fetch"
    rest = set(sys.argv[2:])
    {"fetch": do_fetch, "prepare": do_prepare}.get(cmd, lambda w: do_authors())(rest)
