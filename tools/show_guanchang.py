"""列出官场现形记某回的各段（编号即 annotations 里“段落”的序号）及原站自带的注：python3 tools/show_guanchang.py 001"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_three_novels import ROOT, source_lines
import json

slug = sys.argv[1]
ch = next(c for c in json.loads((ROOT / "sources/guanchang/chapters.json").read_text()) if c["slug"] == slug)
print("#", ch["title"])
j = -1
for ln in source_lines("guanchang", ch["blocks"], slug):
    if ln[:2] in ("原：", "诗："):
        j += 1
        print(f"段 {j}（{len(ln) - 2} 字{'，诗联' if ln[:2] == '诗：' else ''}）：{ln[2:]}")
    else:
        print("   原站已有", ln)
