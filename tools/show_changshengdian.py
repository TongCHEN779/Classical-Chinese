"""列出《长生殿》某几出的各块原文：python3 tools/show_changshengdian.py <起始出序号(1起)> <结束出序号(含)>"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_changshengdian import BASE, read

a, b = int(sys.argv[1]), int(sys.argv[2])
for ch in read(BASE / "chapters.json")[a - 1:b]:
    print(f"## {ch['slug']} {ch['title']}（{len(ch['blocks'])} 块）")
    for j, blk in enumerate(ch["blocks"]):
        print(f"  块 {j}［{blk['kind']}］{blk['text']}")
