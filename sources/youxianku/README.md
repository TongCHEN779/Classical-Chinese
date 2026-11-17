# 游仙窟

- 原文取自中文维基文库《遊仙窟》（单页），全书 1 页，经 `tools/fetch_vernacular.py fetch/prepare youxianku` 生成 `src/youxianku/…/01.txt` 与 `pages.json`；未据影印本逐字校勘。
- 题解与注释为本库自撰，写在 `notes/<页>.json`，由 `build.py` 的 `overlay_notes` 叠加；检查用 `python3 tools/check_novel_notes.py youxianku <页>`；简要见 `tools/brief_five.md`。逐句白话写在 `gloss/p001__<起段>.json`（8 个区间文件，共 225 段，由 `overlay_gloss` 叠加；检查 `python3 tools/gloss_book.py check youxianku p001`；简要见 `tools/brief_gloss_youxianku.md`）。
