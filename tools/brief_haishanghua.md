# 海上花列传：只写注释（不写白话）

BOOK=haishanghualiezhuan。作业批次见 `sources/haishanghualiezhuan/job_batches.json` 的第 K 项（从 0 数起），每项是若干作业 `[页slug, 起始节, 结束节, 字数]`（结束节不含）。

- 先读 `tools/annotation_guide.md`，但本书**不写白话**：每段落只写 `"注"`，`"译"` 一律给空数组 `[]`；"题解"仍要写。
- 每个作业：`python3 tools/show_texts.py haishanghualiezhuan 页slug 起始节 结束节` 看原文；用 Write 写 `sources/haishanghualiezhuan/annotations/<页slug>__<起始节>.json`；再 `python3 tools/check_job.py haishanghualiezhuan 页slug 起始节 结束节` 须输出 OK。
- 题解：一两句话，概括本回情节与人物，不抄原文。
- 注释：每约 250 字原文至少一条。对话为吴语（苏白），重点注吴语词汇与口语（如“俚”“耐”“倪”“阿”“啥”“勒浪”“末事”等，首次出现时点明义）、清末上海长三堂子的行话与规矩（“叫局”“出局”“碰和”“吃酒”“打茶会”“相帮”“大姐”“清倌人”“把势”等）、器物称谓、官场与商场称谓、地名（今地有把握才写）、典故与诗词。不确定写“待考”，不要编造。
- 不改原文；只创建你自己的 annotations 文件。完成后只回复一行：已完成的文件名与 OK。
