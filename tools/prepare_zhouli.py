"""Generate the Zhouli reading texts from pinned witnesses and original annotations."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build import split_sents

BASE = ROOT / "sources/zhouli"
TITLES = ("天官冢宰", "地官司徒", "春官宗伯", "夏官司马", "秋官司寇", "冬官考工记")
GUIDES = (
    "天官以冢宰总领邦治。篇首列官属与员额，随后写大宰的治国纲领，以及宫廷膳饮、财货和内廷诸职。",
    "地官以司徒掌邦教。这里的教不只指教化，也连着土地、户籍、乡遂、市场与赋役；可留意各级组织怎样层层相接。",
    "春官以宗伯统领邦礼，从祭祀天地宗庙到朝聘、丧礼、乐舞，又载卜筮与史官之职。读时可先看大宗伯所列礼类，再读各官分工。",
    "夏官以司马掌邦政，重在军制、军训、田猎及兵马管理。开篇所列军、师、旅、卒、两、伍，是读后文的线索。",
    "秋官以司寇主管邦禁和刑狱。本篇还写到宾客接待、边关查验和盟约，展示司寇系统职掌的范围。",
    "今本冬官的位置由《考工记》补入。篇中由百工的分业说起，再谈车、兵器、礼器和营造等工艺，常把选材、尺寸和成品检验放在一起说明。",
)


# Additional reading landmarks for source pages with no internal headings.
OMIT = {"p02": {0, 172}, "p06": {80}}
LANDMARKS = {
    "p04": {1: "政官之属", 63: "政官之职"},
    "p05": {1: "刑官之属", 59: "刑官之职"},
    "p06": {9: "车制", 12: "轮人", 23: "舆人", 28: "辀人", 34: "攻金",
            52: "攻皮", 64: "设色与湅丝", 71: "玉、磬与矢", 76: "陶人与旊人",
            78: "梓人", 83: "庐人", 85: "匠人", 89: "车人", 91: "弓人"},
}


def load(slug):
    source = json.loads((BASE / f"{slug}.json").read_text(encoding="utf8"))
    blocks = source["blocks"]
    rows = [(i, b["type"], "".join(b["text"].split())) for i, b in enumerate(blocks)
            if i not in OMIT.get(slug, ())]
    return source, rows


def prepare():
    catalog = []
    for n, (title, guide) in enumerate(zip(TITLES, GUIDES), 1):
        slug = f"p{n:02}"
        source, rows = load(slug)
        path = BASE / f"{slug}-annotations.json"
        data = json.loads(path.read_text(encoding="utf8")) if path.exists() else {}
        annotations = data.get("段落", {})
        lines = [f"# {title}", f"题解：{data.get('题解') or guide}"]
        originals, translated, sentences, notes = [], 0, 0, 0
        allowed = {str(i) for i, tag, _ in rows if tag in ("p", "li")}
        unexpected = annotations.keys() - allowed - {str(i) for i in OMIT.get(slug, ())}
        if unexpected:
            raise ValueError((slug, unexpected))
        for i, tag, text in rows:
            if tag.startswith("h"):
                # The source repeats 大宗伯 above the 司几筵 entry.
                heading = "司几筵" if (slug, i) == ("p03", 10) else text
                lines.append(f"# {heading}")
                continue
            if tag not in ("p", "li"):
                raise ValueError((slug, i, tag))
            if heading := LANDMARKS.get(slug, {}).get(i):
                lines.append(f"# {heading}")
            originals.append(text)
            item = annotations.get(str(i), {})
            translations = item.get("译", [])
            if translations:
                if (len(split_sents(text)) != len(translations)
                        or any(not t.strip() or any(c in t for c in ("¦", "\n", "\r")) for t in translations)):
                    raise ValueError((slug, i, "句数或译文格式错误"))
                translated += 1
                sentences += len(translations)
                lines.append(f"原：{text} || {'¦'.join(translations)}")
            else:
                lines.append(f"原：{text}")
            for note in item.get("注", []):
                lines.append(f"注：{note}")
                notes += 1
        out = ROOT / "src/zhouli" / slug / "01.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines) + "\n", encoding="utf8")
        catalog.append(dict(slug=slug, title=title, url=source["url"], revision=source["revision"],
                            paragraphs=len(originals), translated=translated, sentences=sentences, notes=notes,
                            sha256=hashlib.sha256("\n".join(originals).encode()).hexdigest()))
    (BASE / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    return catalog


if __name__ == "__main__":
    for p in prepare():
        print(f"{p['title']}：{p['translated']}/{p['paragraphs']} 段，{p['sentences']} 句，{p['notes']} 条注")
