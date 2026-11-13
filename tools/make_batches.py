#!/usr/bin/env python3
"""把 plan_jobs 的作业打包成批次，写 sources/BOOK/job_batches.json：python3 tools/make_batches.py BOOK [单作业上限字数=4500] [每批字数=11500]"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from plan_jobs import jobs

book = sys.argv[1]
mx = int(sys.argv[2]) if len(sys.argv) > 2 else 4500
per = int(sys.argv[3]) if len(sys.argv) > 3 else 11500
done = ROOT / "sources" / book / "annotations"
done.mkdir(parents=True, exist_ok=True)
batches, cur, size = [], [], 0
for j in jobs(book, mx):
    if (done / f"{j[0]}__{j[1]}.json").exists():
        continue
    if cur and size + j[3] > per:
        batches.append(cur)
        cur, size = [], 0
    cur.append(list(j))
    size += j[3]
if cur:
    batches.append(cur)
(ROOT / "sources" / book / "job_batches.json").write_text(json.dumps(batches, ensure_ascii=False), encoding="utf8")
print(book, len(batches), "批", sum(j[3] for b in batches for j in b), "字")
