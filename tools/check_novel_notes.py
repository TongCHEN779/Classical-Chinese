"""核验白话小说某回的自撰题解与注释：python3 tools/check_novel_notes.py <书slug> <回号> [每多少字至少一条=150]  → OK"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
book, slug = sys.argv[1], sys.argv[2]
per = int(sys.argv[3]) if len(sys.argv) > 3 else 150
lines = []
for f in sorted((ROOT / "src" / book / slug).glob("*.txt")):
    lines += [ln[2:].replace("/", "") for ln in f.read_text(encoding="utf8").splitlines() if ln[:2] in ("原：", "诗：")]
chars = sum(map(len, lines))
f = ROOT / "sources" / book / "notes" / f"{slug}.json"
errs = []
try:
    d = json.loads(f.read_text(encoding="utf8"))
except Exception as e:
    print("JSON 读不出：", e)
    sys.exit(1)
if not str(d.get("题解", "")).strip():
    errs.append("缺题解")
notes = d.get("注", [])
if not isinstance(notes, list):
    errs.append("“注”应为数组")
    notes = []
seen = set()
ptr = 0
for x in notes:
    if not isinstance(x, str) or "：" not in x or "\n" in x:
        errs.append(f"注格式应为单行“词语：解释”：{str(x)[:24]}")
        continue
    w, expl = x.split("：", 1)
    w = w.strip()
    if not w or not expl.strip():
        errs.append(f"注格式：{x[:24]}")
    elif not any(w in ln for ln in lines):
        errs.append(f"注的词语不在本回原文（须是连续出现的字串）：{w}")
    if x in seen:
        errs.append(f"重复的注：{w}")
    seen.add(x)
if chars >= per and len(notes) * per < chars * 0.6:
    errs.append(f"注太少：{chars} 字仅 {len(notes)} 条（约每 {per} 字至少 1 条）")
if errs:
    print("\n".join(errs[:30]))
    sys.exit(1)
print("OK")
