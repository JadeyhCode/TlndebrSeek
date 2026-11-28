# 外部评测子集（P4 benchadapt）

## GSM8K 官方 test 子集（20 题）

- 来源：`https://github.com/openai/grade-school-math` 的 `grade_school_math/data/test.jsonl`
- 许可：MIT（仓库 LICENSE）
- 全量文件 sha256：`3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14`
- 子集规则：按原文件顺序**每隔 65 题取 1 题**，取前 20 题（确定性，未看题目挑题）
- 子集 sha256：`8657d8f1ba5e59430bcfc4ad48d44ff5b038705ca19a6bcb6aa09b9ccb47a88f`
- 子集文件：`gsm8k_test20.jsonl`（官方字段 `question` / `answer` 原样保留）

### 污染检查口径

- `tools/benchadapt.py` 会逐题做**精确问题文本**检索（排除本数据文件与 `_t/`），并报命中文件；
- 另做 5-gram 抽样（问题归一化后的连续 5 词）在 `patterns.txt`/`relations.txt`/`docs/`/`tools/` 的命中数；
- 本子集**未**参与任何调参/训练；首跑读数按原样报告，不挑题、不改期望值。
- 未接入 bAbI（本轮只做 GSM8K 子集；bAbI 数据获取/许可下一轮处理）。
