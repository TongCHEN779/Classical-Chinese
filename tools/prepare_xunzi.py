"""Validate edited Xunzi chapters and refresh their publication manifest."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def prepare():
    source = ROOT / "sources/xunzi"
    catalog = json.loads((source / "catalog.json").read_text(encoding="utf8"))
    done, pending = [], []
    for p in catalog["pages"]:
        slug = p["slug"]
        files = sorted((ROOT / "src/xunzi" / slug).glob("*.txt"))
        if not files:
            pending.append(p["title"])
            continue
        witness = json.loads((source / "wikisource" / f"{slug}.json").read_text(encoding="utf8"))
        originals = [b["text"] for b in witness["blocks"]]
        sections = build.parse_poems(files)
        chunks = [c for sec in sections for c in sec["chunks"]]
        if (not sections or not all(s["intro"] for s in sections)
                or [c["o"] for c in chunks] != originals
                or digest("\n".join(originals)) != witness["text_sha256"]):
            raise ValueError(f"{slug}: 底本或题解未通过核验")
        count = 0
        for c in chunks:
            if not c["t"] or not build.has_sentence_pairs(c):
                raise ValueError(f"{slug}: 白话未与原句对齐：{c['o'][:40]}")
            count += len(build.split_sents(c["o"]))
        done.append(dict(slug=slug, title=p["title"], status="complete", sections=len(sections),
                         pairs=count, notes=sum(len(c["notes"]) for c in chunks),
                         original_sha256=digest("".join(originals)),
                         source={k: witness[k] for k in ("url", "revision")}))
    progress = dict(status="in_progress" if pending else "complete", catalog="catalog.json",
                    pages=done, next=pending[0] if pending else None)
    (source / "progress.json").write_text(json.dumps(progress, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(f"已核对 {len(done)} 项、{sum(p['pairs'] for p in done)} 句白话、{sum(p['notes'] for p in done)} 条注释。")


if __name__ == "__main__":
    prepare()
