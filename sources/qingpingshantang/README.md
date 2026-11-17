# 清平山堂话本

- 底本：明嘉靖年间洪楩“清平山堂”刊印的话本集（原称《六十家小说》，今存残本）。
- 原文取自中文维基文库《清平山堂话本》（总目录页 `清平山堂話本`，子页 `/01`…`/25`，取页时间见 `chapters.json` 的各页修订号），经 `tools/fetch_vernacular.py fetch/prepare qingpingshantang` 生成 `src/qingpingshantang/p001…p025/01.txt` 与 `pages.json`；未据影印本逐字校勘。
- 维基文库目录列了 27 篇，最后两篇《霅川萧琛贬霸王》《李元吴江救朱蛇》没有正文（页面为空），所以只收 25 篇。ctext 上这部书（res=575039 与 745516）一个版本同样只有 25 篇，另一个版本是字符识别的乱码（逐字错得很多），不能用，两篇暂缺。
- 题解与注释为本库自撰，写在 `notes/<页>.json`，由 `build.py` 的 `overlay_notes` 叠加；检查用 `python3 tools/check_novel_notes.py qingpingshantang <页>`；简要见 `tools/brief_qingping.md`。不设白话。
