"""列出某书某页各节（每节一天）的节名与开头：python3 tools/show_days.py <book> <页slug> <起始节> <结束节(不含)>"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build import sent_units
from prepare_texts import read

book, slug, a, b = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
ch = next(c for c in read(ROOT / "sources" / book / "chapters.json") if c["slug"] == slug)
for i in range(a, min(b, len(ch["sections"]))):
    s = ch["sections"][i]
    text = "".join(s["paragraphs"])
    print(f"## 节 {i} 《{s['title']}》（{sum(len(sent_units(p)) for p in s['paragraphs'])} 句，{len(text)} 字）\n  {text[:260]}{'…' if len(text) > 260 else ''}")
