# 吕氏春秋

采用维基文库书名页所列十二纪、八览、六论的简体显示版。各卷修订号、原文、篇目及带旧注的快照见 `chapters.json`；书内提要见 `intro.json`。阅读稿不导入维基注释或底本高诱夹注，题解、白话和折叠注释自撰。

每卷译注写入 `01.txt`。运行 `python3 -B tools/prepare_lvshichunqiu.py` 校验各卷译注并生成 `progress.json`；若某卷尚有未译段落，会生成 `02-original.txt` 原文尾段，续编从 `next_paragraph`、`next_text` 接起。

二十六卷（十二纪、八览、六论）已全部译注。
