# EvalGate

大模型功能上线前的评测与红队检查工具（Python 3.10+ 标准库实现，无第三方运行时依赖）。

> **项目定位**：个人开源项目。思路来自我在测试教育类 AI 问答与 AI 生图功能时遇到的问题：改一句提示词，接口照样返回 200，但边缘问题开始答错、JSON 字段缺失、安全红线松动。示例数据均为虚构的脱敏样例，**不包含任何公司数据或真实系统提示词**。

## 能做什么

| 断言类型 | 检查内容 | 实现方式 |
| :--- | :--- | :--- |
| `contains` / `not_contains` / `equals` | 关键信息是否出现、违禁内容是否出现 | 字符串匹配 |
| `json_schema` | 必填字段、字段类型（自动剥离 Markdown 代码块；布尔值不算数字） | 自实现的 JSON Schema 子集 |
| `hallucination` | 回答与参考原文的字词重合度（中文双字切分 + 英文词元） | 快速初筛，**看不出逻辑颠倒** |
| `llm_judge` | 让另一个模型判断回答是否与参考原文矛盾 | 需 `--judge`；未配置时标记为**跳过**，不会算作通过 |
| `redteam` | 敏感信息泄露 → 越狱话术 → 系统提示词泄露 → 是否明确拒绝（按此顺序判定） | 正则 + 可在用例里追加 `leak_markers` |
| `latency_max` | 响应耗时上限 | 计时 |

门禁规则：通过率低于阈值，或**任意一条红队用例失败**，都会阻断（`--fail-on-gate` 返回退出码 1）。`evalgate diff` 可以对比两次评测快照，找出从通过变成失败的用例。

## 快速上手

```bash
# 1. 用 Mock 演示数据跑通流程（只验证断言和报告格式，不代表任何模型表现）
python -m evalgate run --config examples/edu_assistant_eval.json --html report.html --json baseline.json

# 2. 接真实模型（任意 OpenAI 兼容接口），并开启 LLM 裁判
OPENAI_API_KEY=sk-... OPENAI_API_BASE=https://api.deepseek.com/v1 \
python -m evalgate run --config examples/edu_assistant_eval.json \
  --provider http --model deepseek-chat --judge \
  --html report.html --json candidate.json --fail-on-gate

# 3. 对比两次结果
python -m evalgate diff --baseline baseline.json --candidate candidate.json --fail-on-regression

# 单元测试
python -m unittest discover -s tests -v
```

> [!NOTE]
> Mock 模式下的报告会在页首明确标注「不代表任何真实模型的表现」。仓库中目前**还没有提交真实模型的评测报告**，后续会补充。

## 设计取舍

- **确定性断言优先，LLM 裁判为可选**：字符串、Schema、正则这类检查结果稳定、成本为零，适合放进每次 CI；LLM 裁判能发现逻辑矛盾，但有成本和波动，按需开启。
- **跳过 ≠ 通过**：没有配置裁判时，`llm_judge` 会在报告里显示为跳过并单独计数，避免"没检查却显示全绿"。
- **红队先查泄露再查拒绝**：模型嘴上说"不能"，但后面照样泄露了指令，也判失败。
- **零依赖**：只用标准库，便于在任何 CI 环境里直接运行。

## 已知局限

| 局限 | 说明 |
| :--- | :--- |
| 字词重合度看不出逻辑颠倒 | 把"2 小时以上免费"说成"2 小时以上扣费"仍会得到高分，需要配合 `llm_judge`（有回归测试锁定此行为） |
| 拒绝检测基于关键词 | 不同模型的拒绝措辞差异很大，可能误判；建议结合 `not_contains` 和 `leak_markers` 使用 |
| 红队题库很小 | 只有提示词注入、角色扮演越狱、隐私套取三类示例，远不能覆盖真实攻击面 |
| JSON Schema 只是子集 | 不支持嵌套对象校验、枚举、正则等完整规范 |
| 尚未在真实模型上系统评测 | 目前只有 Mock 演示数据和单元测试 |

## 目录结构

```text
evalgate/
├── evalgate/core/         # 用例加载、模型调用、评测引擎与版本对比
├── evalgate/assertions/   # 各类断言实现（含 llm_judge）
├── evalgate/reporters/    # 命令行与 HTML 报告
├── examples/              # 脱敏示例评测集
└── tests/                 # 单元测试（含自查发现的 bug 回归用例）
```

## License

MIT
