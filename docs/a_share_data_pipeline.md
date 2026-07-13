# A 股日频数据管线

这个仓库的选股数据统一放在仓库根目录下的 `data/`，不会写入 `~/.qlib`。

```
data/
  raw/a_share/daily/       # 每只股票一份压缩复权日频 Parquet，可审计、可重建
  metadata/                # 每日股票清单快照和每次运行的失败清单
  qlib/cn_a_share/         # Qlib 二进制数据
  logs/                    # 定时任务日志
```

## 覆盖范围

数据来自东财公开的 A 股清单和历史日线接口。它不需要登录，也没有把账号、令牌或 Cookie 写入仓库。
接口说明可见 [AKShare 的 A 股历史数据文档](https://akshare.akfamily.xyz/data/stock/stock.html)。数据源可能限流或更改，管线会重试并在 `data/metadata/runs/` 中记录失败股票；不要把公共数据源视作交易所级数据。

| Qlib 股票池 | 代码前缀 | 用途 |
| --- | --- | --- |
| `buyable_main_chinext` | 600/601/603/605、000/001/002/003、300/301 | 主板 + 创业板，可作为模型选股和持仓范围 |
| `factor_main_chinext_star` | 上述代码，加 688/689 | 加入科创板，适合扩展因子或研究范围 |

北交所、B 股、ETF、指数、基金会被排除。`ST` 不会被静默删除，而是在 `data/metadata/universe_latest.json` 中以 `is_st` 标记；是否剔除它应由策略的可交易性规则决定。

## 首次下载

在仓库根目录运行：

```bash
python scripts/a_share_data_pipeline.py sync --scope factor --start 2015-01-01
```

首次任务会对主板、创业板和科创板逐只下载历史日线，可能需要较长时间。默认从 2015 年开始，兼顾模型训练所需样本与本机磁盘空间；磁盘充足时可通过 `--start 2010-01-01` 扩展。为避免“原始 CSV + Qlib 二进制”占满笔记本磁盘，可审计原始层采用 Zstandard 压缩的 Parquet 格式；它可安全重跑，已有股票只会重拉最近 45 个自然日并合并数据。想先验证整个流程而不下载全市场，可以运行：

```bash
python scripts/a_share_data_pipeline.py sync \
  --symbols 600519,300750,688981 --start 2020-01-01
```

若首次全市场回填被中断，可只补缺失的股票，随后单独从本地原始数据构建 Qlib 二进制：

```bash
python scripts/a_share_data_pipeline.py sync --scope factor --only-missing --skip-dump
python scripts/a_share_data_pipeline.py materialize
```

数据下载完成后，Qlib 路径为：

```python
import qlib

qlib.init(
    provider_uri="/Users/niyufei/Coding/qlib/data/qlib/cn_a_share",
    region="cn",
    kernels=1,  # macOS/Jupyter 下先使用单进程，确认流程后再提高
)
```

模型配置中的 `market` 应使用 `buyable_main_chinext`，而不是默认的 `csi300`。如果需要把科创板也纳入模型特征或训练范围，可显式使用 `factor_main_chinext_star`；策略持仓仍应限制为前者。

对应 YAML 的最小配置为：

```yaml
qlib_init:
  provider_uri: /Users/niyufei/Coding/qlib/data/qlib/cn_a_share
  region: cn
  kernels: 1
market: &market buyable_main_chinext
```

## 日常更新与数据质量

```bash
python scripts/a_share_data_pipeline.py sync
python scripts/a_share_data_pipeline.py status
```

默认使用前复权（`qfq`）价格，并且在 15:30 前只更新到上一个工作日，避免把未收盘日线写进训练集。只有明确需要盘中研究时，才使用 `--include-current-session`。每次日常更新重拉最近 45 天以修复迟到数据；每周应该做一次 `--force-full` 全量重拉，因为复权历史会在除权除息后被数据源重述。每次同步会从原始 Parquet 重新生成 Qlib 二进制数据，避免只追加日线而留下不一致的复权历史。

公共当前股票清单适合维护今天的“可买范围”，但并不能保证已退市股票的完整历史。因此，以它训练长期回测会有幸存者偏差风险。严肃研究需要补充有上市/退市区间与公告时点的商业数据或合规数据源；这条管线已经按日保存清单快照和运行记录，为后续替换数据源保留了审计入口。

## 因子就绪度测试

在首次训练或修改数据源后，先运行低资源的 Alpha158 就绪度测试：它会从主板、创业板、科创板各确定性抽样 8 只股票，检查 OHLCV/VWAP、两日远期标签、158 个 Alpha158 技术特征与两个股票池。报告写入 `data/metadata/factor_readiness.json`。

```bash
python scripts/validate_a_share_factor_readiness.py
```

这个测试验证“数据可以正确进入选股模型”，不验证因子有预测能力。通过后再用 `buyable_main_chinext` 训练 LightGBM 基线，并以样本外 IC、RankIC、换手和扣除成本后的回测决定是否保留或聚合因子。

下面的轻量试运行会用上述主板/创业板样本把 158 个因子交给 LightGBM 聚合，再计算独立测试段的 IC 和 RankIC。它只验证建模链路，不能据此挑股或评价策略收益。

```bash
python scripts/run_a_share_alpha158_pilot.py
```

结果写入 `data/metadata/alpha158_pilot.json`。在磁盘空间较紧时，不要直接对全市场物化因子矩阵；先确认这个试运行稳定，再设计分期训练与全市场评分作业。

## 短持有期量价 + 业绩质量研究

若策略目标是约 **3 个交易日**的快进快出、以量价关系为主，同时只在具备正向业绩基础的公司中选股，请使用可复现的研究脚本。它先下载带公告日期的年度 ROE、净利润、营收同比和净利润同比，再运行 **100 个预先声明**的候选策略：5 个基线组合，以及 19 个量价信号蓝图与 5 个质量覆盖层的 95 个固定组合。新增信号涵盖多期限动量/反转、突破位置、量能与换手、流动性、波动率、振幅、跳空、均线趋势与 ROE/营收/利润质量；2026 测试期不参与候选设计或选优。

```bash
python scripts/a_share_short_horizon_factor_research.py sync-fundamentals \
  --start-year 2022 --end-year 2025
python scripts/a_share_short_horizon_factor_research.py run
```

每个候选组合会在 `data/experiments/short_horizon/` 写入一个独立 JSON；同一批运行另有一个 `*_study.json` 汇总文件。记录包含因子权重、年报文件哈希、股票池、成本、发展期/测试期切分以及净收益、波动、回撤和胜率；汇总文件另提供全部 100 个策略按开发期风险调整分数排序的 `ranking_by_development`。候选组合只按 `2025-12-31` 以前的发展期结果选择，之后的测试期不会参与选优。

### 三日持有的迭代研究规范

短线研究的默认持有期是 **3 个本地交易日**。默认 `v1` 候选库运行完整的 100 个预先声明组合；`v2_microstructure` 保留这 100 个组合，并额外加入 10 组一/二日反转、收盘位置、一日量能/换手、短波动/振幅和 60 日趋势假设与 5 个质量覆盖层的交叉组合，共 150 个。每次 `run` 都会把候选库版本、指纹、因子权重、持有期、成本、开发期胜者、独立测试表现和晋级结论追加至 `data/experiments/short_horizon/strategy_registry.json`。注册表是追加式的：新一轮研究不能覆盖或重写旧结果。

`v3_quality_grid` 保留 V2 的全部候选，并增加 20 个不重复的 `quiet_long_trend` 质量网格组合。它把 ROE、营收、增长、综合和利润质量输入分别与 5%/10%/15%/20%/25% 权重交叉，排除 V2 中已有的 5 个等价组合。这样可区分“质量指标种类”与“质量权重”这两个假设；V3 仍须先只在开发期选择，再从未见过的收盘日开始前瞻观察。

`v4_freshness` 在 V3 基础上增加 6 个“营收质量 × 财报新鲜度”组合。财报新鲜度不是报告期的未来信息，而是每个收盘日距该股票最近一份**已生效公告**的天数的横截面反向排名；该公告仍严格在公告日后的下一交易日才生效。它用于检验较新的公开信息是否能改善短线候选的稳定性，任何结果都必须另行前瞻观察。

```bash
python scripts/a_share_short_horizon_factor_research.py run \
  --hold-days 3 --topk 20 \
  --iteration-label three_day_cycle_001
```

新假设应先固定为新库，再仅在开发期内筛选。以下是 V2 的开发期登记示例：它不读 2026，且没有测试段时强制保持研究状态。

```bash
python scripts/a_share_short_horizon_factor_research.py run \
  --candidate-library v2_microstructure \
  --start 2023-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --regime-filter breadth_5_above_20 \
  --open-cost 0.00012 --close-cost 0.00062 --research-only \
  --iteration-label three_day_v2_development_preregistration
```

默认选择规则按开发期的年化收益与回撤综合排序。若担心单一市场年份主导总收益，可显式使用 `--selection-policy positive_year_stability`：它要求至少两个开发年度均为正，并按“最差年度累计净收益 − 0.5 × 全开发期最大回撤”选择。这是新的研究轮次，必须与默认规则分开记录、分开前瞻观察，不能事后改写原轮次的胜者。

若要把开发期回撤作为硬风险约束，可使用 `--selection-policy positive_year_stability_mdd20`：除上述年度稳定性条件外，开发期最大回撤必须不差于 **-20%**，再按相同稳定性分数选优。它和较宽松规则是两个独立的研究假设；仅在已有历史段表现较好不构成晋级，仍需从未见过的收盘日开始积累前瞻纸面样本。

研究的 `TopK` 必须与要验证的组合数量一致。若准备验证 20 万元账户的“最多三只、每只 5%”执行规则，应明确使用 `--topk 3`；三只中必须至少三只具有完整的进/出场日线，不能在缺失报价时悄悄换成四只或把资金重分配。

如果较晚的测试区间已经被看过，只能作为历史诊断，绝不能晋级或替代正在纸面观察的策略。以下命令使用你的实际费率（买入 0.012%，卖出 0.062%）进行这种诊断，并将结果强制标为 `research_only_not_promoted`：

```bash
python scripts/a_share_short_horizon_factor_research.py run \
  --hold-days 3 --topk 3 --regime-filter breadth_5_above_20 \
  --open-cost 0.00012 --close-cost 0.00062 --research-only \
  --iteration-label three_day_top3_historical_diagnostic
```

可把收盘后计算出的市场广度作为独立的状态因子，例如只在质量股票池平均 5 日收益为正时做多：`--regime-filter breadth_5_positive`。未满足状态时的三日持有周期在回测中按持有现金的零收益计入，不会因为跳过交易而虚增年化收益。

不要把某个状态规则当作默认真理。可对一个已记录候选运行 `regime-audit`，一次比较 `always`、两种正广度和短期广度强于中期广度四种预定义规则；报告只按开发期排序并写入单独审计 JSON，不能用它回写已登记候选或把历史结果包装成前瞻收益。

```bash
python scripts/a_share_short_horizon_factor_research.py regime-audit \
  --candidate expanded_v3_quiet_long_trend_q15_revenue \
  --candidate-library v3_quality_grid \
  --start 2023-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062 \
  --selection-policy positive_year_stability_mdd20
```

当某轮策略在注册表中通过初测后，筛选命令必须带上它对应的状态条件，例如：

```bash
python scripts/a_share_short_horizon_factor_research.py screen \
  --candidate expanded_trend_ma_confirmation_q20_composite \
  --regime-filter breadth_5_above_20 --topk 20
```

筛选结果会显式写入 `regime_active`。当它为 `false` 时，不产生候选名单，`plan` 也会拒绝生成下单计划；这代表策略规定的空仓，而不是数据故障。

通过初测的策略不应马上被视为可实盘策略。每次收盘数据更新后，运行纸面观察器：它只在状态允许时追加一笔不可修改的模拟信号；三日后的本地日线齐全时，才用“下一日开盘买入、第三日收盘卖出”和研究成本结算实际样本外结果。

```bash
python scripts/a_share_short_horizon_factor_research.py monitor
```

信号和结算记录保存在 `data/experiments/short_horizon/three_day_paper_ledger.json`。若当日状态不满足策略条件，观察器只记录空仓状态，不创建纸面持仓。不要将纸面台账的未结算信号当作已实现收益。

开发期胜者可以进入**独立的前瞻纸面观察**，但仍不是已晋级策略。必须先显式登记第一个真正未见过的收盘日；`shadow-monitor` 只读此登记，写入与主策略完全分离的 `three_day_shadow_paper_ledger.json`，不会生成 `plan` 或任何下单指令：

```bash
python scripts/a_share_short_horizon_factor_research.py shadow-register \
  --iteration-id <development_only_iteration_id> --not-before 2026-07-14
python scripts/a_share_short_horizon_factor_research.py shadow-monitor
```

若该迭代已有历史测试周期，或者未显式指定开始日期，登记会被拒绝。这样可以防止把已经看过的历史行情伪装成前瞻纸面收益。

`report` 会将每个登记候选单独列出首个可用收盘日、信号数、结算数、待结算数和已结算累计净收益；不要把不同候选的收益混合成一个“组合结果”。

每次研究或纸面观察后，可生成面向人工复盘的汇总日志；它汇总所有迭代的开发/测试表现、晋级状态以及纸面信号和结算数量：

```bash
python scripts/a_share_short_horizon_factor_research.py report
```

日志默认写入 `data/experiments/short_horizon/three_day_research_report.md`。它是注册表和纸面台账的派生视图；策略判断始终以不可覆盖的 JSON 原始记录为准。

选择只使用 `--development-end` 以前的数据；测试段不参与因子权重或策略排名。一个开发期胜者只有在测试段至少有 20 个独立持有周期、累计净收益为正且最大回撤不差于 -20% 时，才会标为 `passed_initial_test`；否则仍是研究候选，不能进入后续实盘/模拟盘计划。每次新因子或新组合必须新开一轮并写明标签，不能在同一测试段反复调到满意为止。

日常迭代顺序是：收盘后更新数据 → 运行三日研究 → 查看注册表中新旧轮次的开发/测试差异 → 仅将通过初测的策略用于下一阶段模拟盘观察。未来有新的、未见过的交易日时，才把它加入新的测试观察；不要用已看过的 2026 测试结果反复改权重。

质量过滤的规则是：上一份已公告年报的加权 ROE 不低于 5%、归母净利润为正、营收同比和利润同比均为正。为避免未来函数，财报从**公告日后的下一个本地交易日**才生效。公共财报接口可能显示日后更正的历史数值，因此该处理比直接使用报告期安全，但仍不能替代商业级或交易所级的点时财务数据库。

### 小资金实盘/模拟盘基础执行规范

该规范仅用于把最新筛选结果转成可审计的**模拟盘或小仓执行计划**；不是买卖建议，也不会把当前研究回测包装成精确成交回测。默认规则如下，任何改动都会写入计划 JSON，不能在信号生成后临时改变：

| 项目 | 默认规范 |
| --- | --- |
| 默认资金 | 200,000 元 |
| 候选数 / 单股目标 | 最新榜单前 3 只；每只目标为总资金 5% |
| 总仓位上限 | 15% |
| 买入单位 | 100 股整手；股数和费用均向下约束，绝不超总仓位 |
| 佣金 | 买卖双向各 0.01%（万 1，即每 1 万元 1 元）；按用户给出的费率，默认没有最低 5 元 |
| 过户/结算费 | 买卖双向各 0.002% |
| 印花税 | 仅卖出，成交额的 0.05% |
| 现金处理 | 某一候选连一手也买不起时跳过且保留现金，不加仓给其余股票，也不自动替换低排名股票 |

证券交易印花税由出让方承担，按成交金额计税；现行减半政策自 2023-08-28 起实施。[印花税法](https://fgk.chinatax.gov.cn/zcfgk/c100009/c5193058/content.html) [减半征收公告](https://fgk.chinatax.gov.cn/zcfgk/c102416/c5211343/content.html) 中国结算公布的交易过户费为成交额的 0.02‰（即 0.002%）双向收取。[中国结算收费说明](https://www.chinaclear.cn/zdjs/editor_file/20220627143504384.pdf)

佣金采用你的“万 1”报价，因此没有把交易所经手费再额外叠加，以免把已经包含在券商报价里的费用重复计算。若交割单显示有单列费用或有最低佣金，应按实际券商规则覆盖，例如 `--commission-min 5`；上交所公开的 A 股经手费标准可作为复核依据，但它不是本工具的默认重复收费项。[上交所收费一览](https://www.sse.com.cn/services/tradingservice/charge/ssecharge/)

先生成包含收盘价参考的最新筛选，再生成计划：

```bash
python scripts/a_share_short_horizon_factor_research.py screen --topk 20
python scripts/a_share_short_horizon_factor_research.py plan \
  --screen-path data/experiments/short_horizon/<最新的_screen_*.json>
```

`plan` 默认只生成 20 万元方案；每个方案都会列出整手股数、买入占用资金、买卖两侧费用、实际仓位、剩余现金和因整手限制跳过的候选。需要临时覆盖资金时传入 `--capital`，例如 `--capital 120000`。计划中的 `reference_close` 只用于仓位测算；交易日必须以券商可见的实际价格重新核对，并只允许下调股数来遵守上限。

当前筛选与历史研究仍采用前复权日线，且缺少 Qlib 的复权恢复因子。故这个整手规划器可用于当日仓位和费用审计，但历史收益曲线尚不是精确的整手、税费、涨跌停和停牌成交模拟。

研究结果仅用于比较候选假设，不能作为收益承诺或直接实盘信号。当前数据为前复权价且缺少恢复因子，股票池也来自当前上市快照；结果不包含精确整手、税费、涨跌停、停牌和退市历史的成交模拟。

当前原始价格已是前复权价，管线尚未提供 Qlib 的复权恢复因子 `$factor`。因此 Alpha158 可以正常计算，但 Qlib 回测会以复权价执行，不能把 100 股整手、分红送配前后的成交细节视为精确模拟；严肃的可交易性回测需要补充原始价和恢复因子。

若正常 `sync` 因东财接口短暂不可用，但确认需要补入一个已收盘的交易日，可使用受审计的腾讯收盘行情恢复脚本。它只使用已有的本地股票池快照、只写入指定日期，并将源站、失败股票与 Qlib 重建结果记录在 `data/metadata/recoveries/`。东财恢复后，仍应执行一次正常 `sync` 覆盖并复核这一天。

```bash
python scripts/recover_a_share_close_from_tencent.py --date 2026-07-13
python scripts/a_share_data_pipeline.py status
```

东财个别股票的长周期前复权数据会在大额现金分红后出现负数价格。日常下载会自动拒绝此类无效 OHLC 行；已有历史数据可运行下面的本地修复命令。它会删除这些无法建模的日期，并以 Qlib 的缺失交易日形式重新生成二进制数据，同时在 `data/metadata/repairs/` 保存审计清单。

```bash
python scripts/a_share_data_pipeline.py sanitize
```

如果曾在收盘前运行旧版本管线，可不联网地移除未收盘日线并重建 Qlib 数据：

```bash
python scripts/a_share_data_pipeline.py prune-session
```

## 全量数据集验收

在建模前或数据源/转储逻辑发生改变后，运行全量审计。它逐个读取全部 Parquet 文件、逐字段比对全部 Qlib 二进制值、检查日历和股票池，并抽样用 Qlib 读取器和东财最新日线复核。结果写入 `data/metadata/dataset_audit.json`。

```bash
python scripts/audit_a_share_dataset.py
```

如果验收目标包含精确 A 股整手回测，应额外要求复权恢复因子：

```bash
python scripts/audit_a_share_dataset.py --require-restoration-factor
```

## 定时自动运行（macOS）

本机时区与中国大陆一致。默认命令安装两个 `launchd` 用户任务：工作日 18:30 增量更新，以及周五 20:00 的全量复权校正。若要在数据更新后自动追加三日纸面观察，可显式加入工作日 19:30 的观察任务：

```bash
python scripts/install_a_share_launchd.py install
python scripts/install_a_share_launchd.py install --with-short-horizon-monitor
python scripts/install_a_share_launchd.py status
```

纸面观察任务会先检查 18:30 数据同步所持有的管线锁；若同步仍在进行，最多等待 45 分钟，避免用旧收盘数据漏记当日信号。随后依次运行已晋级策略的 `monitor`、已登记研究候选的 `shadow-monitor` 和 `report`；它不会自动重跑因子搜索、修改策略权重或生成下单计划。日志在 `data/logs/`。需要移除定时任务时：

```bash
python scripts/install_a_share_launchd.py uninstall
```

定时任务不在休眠的电脑上补跑；若错过一次，手动执行 `sync` 即可恢复。若将来换成需要登录的专业数据服务，不要把令牌写进 YAML 或 Git；由系统钥匙串、环境变量或本地 `.env`（已忽略）提供即可。
