"""核验官场现形记某回的自撰注释：python3 tools/check_guanchang_job.py 001 → OK"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_three_novels import ROOT, source_lines, overlay

slug = sys.argv[1]
ch = next(c for c in json.loads((ROOT / "sources/guanchang/chapters.json").read_text()) if c["slug"] == slug)
lines = list(source_lines("guanchang", ch["blocks"], slug))
n_para = sum(1 for ln in lines if ln[:2] in ("原：", "诗："))
n_chars = sum(len(ln) - 2 for ln in lines if ln[:2] in ("原：", "诗："))
f = ROOT / "sources/guanchang/annotations" / f"{slug}.json"
d = json.loads(f.read_text(encoding="utf8"))
errs = []
try:
    out, head = overlay("guanchang", slug, lines)
except AssertionError as e:
    errs.append("格式：" + " ".join(map(str, e.args)))
else:
    n_notes = sum(len(p.get("注", [])) for p in d["段落"])
    if n_notes * 150 < n_chars * 0.6:
        errs.append(f"注太少：{n_chars} 字仅 {n_notes} 条（约每 150 字至少 1 条）")
    for p in d["段落"]:
        for x in p.get("注", []):
            if "\n" in x:
                errs.append("注里不能有换行")
if errs:
    print("\n".join(errs))
    sys.exit(1)
print("OK")
