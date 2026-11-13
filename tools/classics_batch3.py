#!/usr/bin/env python3
"""“经典名篇”第三批 37 篇的骨架生成、阅读辅助与检查。

  python3 tools/classics_batch3.py skeleton [slug ...]   由 sources/classic_list/wikisource/<slug>.json 生成 src 骨架（已存在且已填写的不覆盖）
  python3 tools/classics_batch3.py show SLUG             列出每个原文段的切句（白话必须与之一一对应）
  python3 tools/classics_batch3.py check SLUG            核验已填写的稿子：原文未改、句数对应、有题解与注释
  python3 tools/classics_batch3.py finalize              把已完成各篇登记进 entries.json（题解、原文摘要）

骨架每段写作“原：原文 || ”，等待填入“白话¦白话…”（每个以。！？；结束的原文句对应一句，¦ 分隔），段后可加“注：词语：解释”。
"""
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CL = ROOT / "sources/classic_list"
SRC = ROOT / "src/classic_list"

# slug, 篇名, 作者, 区块（整篇）或 [(节名, 区块)]（分节）
SPECS = [
    ("shaonian", "少年中国说", "［清］梁启超", list(range(0, 11))),
    ("bingmei", "病梅馆记", "［清］龚自珍", list(range(0, 4))),
    ("huangshan", "游黄山记", "［明］钱谦益", [
        ("游黄山记序", [1]), ("记之一", [3, 4]), ("记之二", [6]), ("记之三", [8]), ("记之四", [10]),
        ("记之五", [12]), ("记之六", [14]), ("记之七", [16]), ("记之八", [18]), ("记之九", [20])]),
    ("taishan", "登泰山记", "［清］姚鼐", list(range(0, 6))),
    ("zuozhongyi", "左忠毅公轶事", "［清］方苞", list(range(0, 4))),
    ("yuzhongzaji", "狱中杂记", "［清］方苞", list(range(0, 7))),
    ("jimei", "祭妹文", "［清］袁枚", list(range(0, 9))),
    ("qinshi", "秦士录", "［明］宋濂", [0]),
    ("maigan", "卖柑者言", "［明］刘基", list(range(0, 3))),
    ("shenlv", "深虑论", "［明］方孝孺", list(range(0, 4))),
    ("yurang", "豫让论", "［明］方孝孺", list(range(0, 4))),
    ("xiangci", "象祠记", "［明］王守仁", list(range(0, 2))),
    ("zunjingge", "尊经阁记", "［明］王守仁", list(range(0, 7))),
    ("xianbi", "先妣事略", "［明］归有光", list(range(0, 8))),
    ("canglang-gui", "沧浪亭记", "［明］归有光", list(range(0, 2))),
    ("canglang-su", "沧浪亭记", "［北宋］苏舜钦", list(range(0, 4))),
    ("hanhua", "寒花葬志", "［明］归有光", list(range(0, 3))),
    ("zhuxi", "任光禄竹溪记", "［明］唐顺之", list(range(0, 5))),
    ("xinling", "信陵君救赵论", "［明］唐顺之", list(range(0, 5))),
    ("huqiu", "虎丘记", "［明］袁宏道", list(range(0, 5))),
    ("manjing", "满井游记", "［明］袁宏道", list(range(0, 3))),
    ("yuejianglou", "阅江楼记", "［明］宋濂", list(range(0, 3))),
    ("mozhu", "墨竹赋", "［北宋］苏辙", [0]),
    ("shangzhongyong", "伤仲永", "［北宋］王安石", list(range(0, 3))),
    ("mengchang", "读孟尝君传", "［北宋］王安石", list(range(0, 2))),
    ("dasima", "答司马谏议书", "［北宋］王安石", list(range(0, 4))),
    ("changhen", "长恨歌", "［唐］白居易", [0]),
    ("changan", "长安古意", "［唐］卢照邻", [0]),
    ("xiaoyuan", "小园赋", "［北周］庾信", list(range(0, 6))),
    ("kushu", "枯树赋", "［北周］庾信", list(range(0, 7))),
    ("daleilei", "登大雷岸与妹书", "［南朝宋］鲍照", list(range(0, 7))),
    ("lingguan", "五代史伶官传序", "［北宋］欧阳修", list(range(0, 4))),
    ("daolouyuan", "待漏院记", "［北宋］王禹偁", list(range(0, 5))),
    ("pengdang", "朋党论", "［北宋］欧阳修", list(range(0, 5))),
    ("qiusheng", "秋声赋", "［北宋］欧阳修", list(range(1, 7))),
    ("fengle", "丰乐亭记", "［北宋］欧阳修", list(range(0, 4))),
    ("wucheng", "芜城赋", "［南朝宋］鲍照", list(range(0, 6))),
]
BY = {s[0]: s for s in SPECS}
END = "。！？；"


def cache(slug):
    return json.loads((CL / "wikisource" / f"{slug}.json").read_text(encoding="utf8"))


def paragraphs(text):
    """块文本 → 原文段：在句末标点后的空白处断段，其余空白去掉。"""
    parts = re.split(r"(?<=[。！？；])\s+", text.strip())
    return [re.sub(r"\s+", "", p).replace(":", "：") for p in parts if p.strip()]


def sections_of(spec):
    slug, title, author, sel = spec
    blocks = cache(slug)["blocks"]
    if sel and isinstance(sel[0], tuple):
        return [(t, [p for i in idxs for p in paragraphs(blocks[i]["text"])]) for t, idxs in sel]
    return [(title, [p for i in sel for p in paragraphs(blocks[i]["text"])])]


def src_path(slug):
    return SRC / slug / "001.txt"


def skeleton(slugs):
    for spec in SPECS:
        slug = spec[0]
        if slugs and slug not in slugs:
            continue
        path = src_path(slug)
        if path.exists() and "待写" not in path.read_text(encoding="utf8") and " || \n" not in path.read_text(encoding="utf8"):
            print("keep", slug)
            continue
        lines = []
        for title, paras in sections_of(spec):
            lines += ["# " + title, "题解：（待写）"]
            lines += [f"原：{p} || " for p in paras]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf8")
        print("skeleton", slug, sum(len(p) for _, ps in sections_of(spec) for p in ps), "字")


def parse(slug):
    import build
    return build.parse_poems([src_path(slug)])


def show(slug):
    import build
    for sec in parse(slug):
        print("##", sec["title"])
        for k, c in enumerate(sec["chunks"]):
            sents = build.split_sents(c["o"])
            print(f"段{k}（{len(sents)} 句）：" + " | ".join(sents))


def check(slug):
    import build
    spec = BY[slug]
    want = sections_of(spec)
    secs = parse(slug)
    assert [s["title"] for s in secs] == [t for t, _ in want], "节名不符"
    problems = []
    for sec, (title, paras) in zip(secs, want):
        if not sec["intro"] or "待写" in "".join(sec["intro"]):
            problems.append(f"{title}: 缺题解")
        got = [c["o"].replace("/", "") for c in sec["chunks"]]
        if got != paras:
            problems.append(f"{title}: 原文被改动（段数 {len(got)}/{len(paras)}）")
            continue
        for k, c in enumerate(sec["chunks"]):
            if not c["t"]:
                problems.append(f"{title} 段{k}: 缺白话")
                continue
            o, t = build.split_sents(c["o"]), c["t"].split("¦")
            if len(o) != len(t) or not all(x.strip() for x in t):
                problems.append(f"{title} 段{k}: 句数 原文{len(o)} 白话{len(t)}")
                continue
            if [x for x, _ in build.split_pairs(c["o"], c["t"])] != o:
                problems.append(f"{title} 段{k}: 会退回整段悬浮")
    notes = sum(len(c["notes"]) for sec in secs for c in sec["chunks"])
    chars = sum(len(p) for _, ps in want for p in ps)
    if notes < max(3, chars // 150):
        problems.append(f"注释偏少：{notes} 条 / {chars} 字")
    print(slug, "OK" if not problems else "有问题", f"（{notes} 条注）")
    for p in problems:
        print("  -", p)
    return not problems


def finalize():
    import build
    path = CL / "entries.json"
    entries = json.loads(path.read_text(encoding="utf8"))
    have = {e["slug"] for e in entries}
    for spec in SPECS:
        slug, title, author, sel = spec
        if slug in have:
            continue
        assert check(slug), slug
        secs = parse(slug)
        c = cache(slug)
        original = "".join(ch["o"].replace("/", "") for s in secs for ch in s["chunks"])
        src = {"url": c["url"], "revision": c["revision"], "label": "维基文库"}
        entry = {"title": title, "author": author, "slug": slug, "intro": secs[0]["intro"][0]}
        if isinstance(sel[0], tuple):
            entry["intro"] = "钱谦益游黄山后所作，序与九记依维基文库顺序全收。" if slug == "huangshan" else entry["intro"]
            entry["source"] = {**src, "after": "正文照录所列修订；题解、白话和释词为本库整理。"}
            entry["sections"] = [{"title": t, "source": dict(src)} for t, _ in sel]
            entry["redirects"] = {}
            entry["provenance"] = {"kind": "sectioned_cache", "cache": f"wikisource/{slug}.json",
                                   "section_blocks": [idxs for _, idxs in sel],
                                   "original_sha256": hashlib.sha256(original.encode()).hexdigest()}
        else:
            entry["source"] = {**src, "after": "正文照录所列修订；题解、白话和释词为本库整理。"}
            entry["provenance"] = {"kind": "cached_primary_text", "cache": f"wikisource/{slug}.json",
                                   "selected_blocks": sel, "original_sha256": hashlib.sha256(original.encode()).hexdigest()}
        entries.append(entry)
        print("add", slug)
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=1) + "\n", encoding="utf8")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "skeleton":
        skeleton(set(sys.argv[2:]))
    elif cmd == "show":
        show(sys.argv[2])
    elif cmd == "check":
        sys.exit(0 if check(sys.argv[2]) else 1)
    elif cmd == "finalize":
        finalize()
