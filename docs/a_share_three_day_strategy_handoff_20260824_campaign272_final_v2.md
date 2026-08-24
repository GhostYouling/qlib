# A 股三日短线研究交接：Campaign272 最终修正版

Campaign272 已完成 `c271_01 issuer_brand_product_public_search_attention_state` 的单一零网络、零行来源合同审查。七项合取门全部失败：点时发行人/实体/子公司/品牌/产品身份、事前查询篮子、固定平台/地域/采样人口、不可变 2019–2023 搜索档案、公开/修订时钟、全发行人真实零/缺失分母，以及后续三日 walk-forward 协议都不能由当前已接纳的本地来源同时闭合。

该概念已经终止且没有成为因子。公式、方向、平台、地域、查询篮子、采样窗口、来源字段、候选值、比较值和预测结论均为空。不得换用网站、App、电商、招聘或社交平台，也不得在来源暴露后改选品牌、产品、关键词、地域、窗口、阈值或方向。

有效台账为 `data/experiments/short_horizon/historical_walkforward/campaign_272/research_attempt_ledger_v6.json`，SHA-256 `aeda5b6294adbd17c76e25b28838db689abb38b06cd6d332b373ad4b3707d110`，链头 `4541baa46ad21e9d350fd49b46aa1574e805c2d35029511e964b7648d2ae82c2`。共 14 次尝试：7 次值前科学合同门和 7 次基础设施失败；累计历史研究尝试 2,767，收益读取开发试验保持 315，定义/比较库保持 `162/143`。

最后两次基础设施失败分别是最终 JSON glob 漏掉 `campaign_272` 命名文档，以及同步统一报告的合并补丁因上下文不精确在写入前被拒绝。两者都已追加保留并由双模式去重 JSON 验证和独立小补丁恢复，没有重算科学值。

最终验证为：Campaign272 聚焦测试 7/7；Campaign265–272 与 Candidate49 跨阶段回归 230 passed、5 个历史可变报告哈希节点精确排除；Black、Ruff、最终 13 份 Campaign272 JSON、v1–v6 追加链及 `git diff --check` 通过。旧生命周期文件未改写。

Candidate49 仍是唯一前瞻候选。2026-08-24 的 `stock_basic_invalid_ts_code` 已失败关闭，禁止同日重试或重请求失败响应；保留 `/Volumes/DIsk/qlib-a-share-tushare-daily-2026-08-24`，信号/执行账本保持 0/0。`.env` 仅验证普通文件、0600、Git 忽略和一个非空 Token 赋值，没有读取、打印或散列秘密。

下一步 Campaign273 只能先冻结一个经济上独立的有限概念目录，再做目标库存审查；禁止 Candidate49 历史回填、第二个前瞻候选、当前评分、选股、仓位、订单或投资建议。持续目标保持 `active`。
