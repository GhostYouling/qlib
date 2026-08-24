# Campaign265 v420 显式授权发布器计划报告

记录时间：2026-08-24 13:57:11（Asia/Singapore）。持续目标 `请持续迭代因子。` 仍为 active。

## 结论

Campaign265 已从“只能人工手写 v420”推进到“可由冻结发布器机械生成 v420”的断点，但真实授权和来源采集仍未发生。

新增 `scripts/a_share_three_day_walkforward_campaign265_v420_authorization.py`，默认只运行 `plan`。其当前结果为 `ready=true`、退出码 0、31/31 检查通过：九个权威文件指纹、原工作流 34/34 计划语义、1,699 个接受日、精确 1,700 次调用、请求序列摘要、六个真实尝试目的路径及 v420 目标均通过或确认不存在。

发布器没有 Token 或 provider 接口。未带确认参数的 `publish` 实际退出码为 2，错误码为 `explicit_v420_publication_required`，且零写入。只有操作者明确执行：

```bash
/Volumes/DIsk/Coding/anaconda3/bin/python3.12 \
  scripts/a_share_three_day_walkforward_campaign265_v420_authorization.py \
  publish --confirm-v420-publication
```

才会在独占、原子、目录描述符固定的条件下创建精确 v420。即便 v420 成功发布，也必须重新运行原工作流 `plan`；只有它继续 `ready=true` 且退出码 0，操作者再单独执行 `run --confirm-run`，才会开始一次性来源采集。发布 v420 本身不会创建 intent、加载 `.env`、导入 provider 或发请求。

## 失败与修复

本阶段保留四个基础设施失败：初版发布器误写了四个尝试路径；一个合并验证命令让后续 pytest 成功掩盖了 Black 的非零退出；扩展套件选中了 Campaign264 发布时固定的旧统一报告哈希断言；首次暂存检查发现两个 Markdown EOF 空白行，且后续 `diff --stat` 再次掩盖了前段非零退出。路径、格式和空白问题均已修复；旧生命周期测试保持不改，只在当前状态套件精确排除。

最终验证为：发布器 7 项测试通过；原工作流加发布器 20 项通过；Campaign264–265 当前跨阶段套件 73 项通过、2 个旧生命周期节点精确排除；Black、Ruff、JSON、Git diff 和 v14 台账链均通过。

## 研究边界

v420 文件仍不存在，原工作流仍不暴露 `run`。Candidate49 信号/执行账本仍为 0/0，哈希不变；没有历史回填、第二个前瞻候选、来源值、比较值、价格、收益、2024–2025 stress、当前评分、选股、仓位或订单。

Campaign265 当前会计为 36 次尝试：15 次值前科学尝试、21 次基础设施失败、完整因子尝试 0、收益读取开发试验 0；累计历史尝试 2,640，累计收益读取开发试验仍为 315。策略公式、方向、字段、日期、1.05 秒间隔、覆盖/唯一性门和一次性失败语义均未改变。
