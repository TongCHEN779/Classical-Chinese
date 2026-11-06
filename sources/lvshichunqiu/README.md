# 吕氏春秋

采用维基文库书名页所列十二纪、八览、六论的简体显示版。各卷修订号、原文、篇目及带旧注的快照见 `chapters.json`；书内提要见 `intro.json`。阅读稿不导入维基注释或底本高诱夹注，题解、白话和折叠注释自撰。

每卷译注写入 `01.txt`。运行 `python3 -B tools/prepare_lvshichunqiu.py` 校验已注译段落，并生成原文尾段及 `progress.json`。续编从各卷的 `next_paragraph`、`next_text` 接起。
