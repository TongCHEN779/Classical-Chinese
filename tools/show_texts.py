"""列出某书某页若干节的各段切句：python3 tools/show_texts.py <book> <页slug> <起始节> <结束节(不含)>"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build import split_sents
from prepare_texts import read, sent_units

book, slug, a, b = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
ch = next(c for c in read(ROOT / "sources" / book / "chapters.json") if c["slug"] == slug)
for i in range(a, min(b, len(ch["sections"]))):
    s = ch["sections"][i]
    print(f"## 节 {i} 《{s['title']}》 分类：{'/'.join(s['path'])}")
    for j, p in enumerate(s["paragraphs"]):
        ss = sent_units(p)
        print(f"  段 {j}（{len(ss)} 句）：" + " | ".join(ss))
