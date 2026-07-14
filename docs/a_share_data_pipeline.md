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

若数据恢复或外部修补后审计报告提示原始 Parquet 的 `symbol` 字段为空，可运行纯本地修复。它只按文件名补齐缺失/空白代码；若发现非空代码与文件名不一致则立即失败，不会改写价格、日期或股票身份。修复清单写入 `data/metadata/repairs/`，并仅在确有修复时重建 Qlib 二进制。

```bash
python scripts/a_share_data_pipeline.py normalize-symbols
```

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

年度财报在三日策略中更新过慢；若要研究公告后的业绩变化，应另行下载**季度**报告，不能悄悄替换原年度质量数据。季度文件保留相同的公告日后下一交易日生效规则，并将加速度与上一年**同一财务季度**比较，避免把 Q1 与 Q4 的累计口径差异误当成基本面变化：

```bash
python scripts/a_share_short_horizon_factor_research.py sync-quarterly-fundamentals \
  --start-year 2019 --end-year 2026 --through-report-date 2026-03-31
python scripts/a_share_short_horizon_factor_research.py factor-diagnostic \
  --fundamentals data/raw/a_share/fundamentals/quarterly_quality.parquet \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062
```

这一步只诊断新季度信息的单因子关联，不能直接生成策略、前瞻观察或选股名单。只有在跨年度方向稳定后，才可把一个**预先声明**的季度公告因子库作为新的研究轮次；公开接口的历史值仍可能被后续更正，不能视为交易所级点时财务库。

季度报告未产生稳定三日信号时，可以把**业绩预告公告**作为独立事件源继续诊断。接口混有营收、每股收益和扣非利润等口径，脚本只保留“归属于上市公司股东的净利润”（`PREDICT_FINANCE_CODE=004`）的公告日和同比预测区间；再以区间中点表示预期方向、以区间宽度表示不确定性，并保留无需数值区间即可确定的“扭亏”二元事件。所有事件都严格等到公告后的下一本地交易日才允许使用。它不会改变季度质量门槛，也不会直接产生策略或选股名单：只在原本已合格的股票中，测量新鲜预告事件是否解释之后的完整三日收益。

```bash
python scripts/a_share_short_horizon_factor_research.py sync-performance-forecasts \
  --start-year 2019 --end-year 2026 --through-report-date 2026-06-30
python scripts/a_share_short_horizon_factor_research.py factor-diagnostic \
  --fundamentals data/raw/a_share/fundamentals/quarterly_quality.parquet \
  --performance-forecasts data/raw/a_share/fundamentals/performance_forecasts.parquet \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062 \
  --max-forecast-age-days 30
```

这是一项预先固定为“公告后 30 个日历日内”的开发期事件诊断；不要根据结果反复扩大窗口来寻找更好看的数值。公开源是当前快照，历史预告可被后续订正或遗漏，因此即使诊断方向稳定，也还需要独立的未见区间和前瞻纸面观察。

若季度和业绩预告都没有形成稳定的三日关联，可独立测试每日收盘后公开的**龙虎榜**事件。脚本只保存净买入额、龙虎榜成交额和流通市值构造的三个比例，以及同日不同上榜原因数；同一股票/日的多个原因按各比例的中位数聚合，避免把重复披露误加总。数据源会同时提供 `D1/D2/D5/D10` 等后续收益字段，下载和存储时都明确排除，不能进入任何评分。事件在当日收盘后形成信号、下一本地交易日开盘前可用，且只保留 3 个日历日；过期事件即使仍为了审计保留在行中，也不会参与横截面排名。

```bash
python scripts/a_share_short_horizon_factor_research.py sync-billboard-events \
  --start-year 2019 --end-year 2026
python scripts/a_share_short_horizon_factor_research.py factor-diagnostic \
  --fundamentals data/raw/a_share/fundamentals/quarterly_quality.parquet \
  --billboard-events data/raw/a_share/events/daily_billboard.parquet \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062 \
  --max-billboard-age-days 3
```

这同样只是单因子开发期诊断：当前公开接口可能回补、改写或漏掉历史上榜记录，且“当日收盘后可用于次日开盘”的时间假设尚未由交易所级逐笔披露源核验。因此通过诊断也只能进入独立未见区间和纸面观察，不能直接产生策略或实盘选股。

若开发期诊断显示某个**反向**方向在所有年份都一致，方向本身仍是事后形成的假设，不能回头把它的开发期收益当作验证。以“较低龙虎榜成交额/流通市值”为例，必须先把方向和引用的开发期诊断编号写死，再只在后续日期运行条件化事件留出期检查：

```bash
python scripts/a_share_short_horizon_factor_research.py billboard-holdout \
  --development-diagnostic-run-id 20260713T214915Z \
  --development-end 2025-12-31 --holdout-start 2026-01-01 \
  --end 2026-07-13 --hold-days 3 --topk 3 \
  --open-cost 0.00012 --close-cost 0.00062
```

该命令只在“质量合格且三日内出现龙虎榜事件”的股票中比较 Top‑3 与末 3，结果不是每日全市场策略，更不会写入策略注册表、生成名单或允许晋级。即便留出期方向一致，也只能据此预登记下一阶段的完整事件策略，并使用新的未来日期做纸面观察。

还可把**重要股东增减持公告**作为与量价独立的事件源。该数据的交易结束日可能早于公告日很多天，不能拿来反填信号；脚本只请求公告日、增/减持方向和变动占流通股比例，并严格从公告后的下一本地交易日才生效。它分别诊断净变动比例、增持比例、减持比例、同日事件数与新鲜度，窗口固定为 3 个日历日：

```bash
python scripts/a_share_short_horizon_factor_research.py sync-major-holder-events \
  --start-year 2019 --end-year 2026
python scripts/a_share_short_horizon_factor_research.py factor-diagnostic \
  --fundamentals data/raw/a_share/fundamentals/quarterly_quality.parquet \
  --major-holder-events data/raw/a_share/events/major_holder_changes.parquet \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062 \
  --max-major-holder-age-days 3
```

该事件是对已发生交易的公开报告而非实时资金流；公共快照还可能修订或遗漏。因此，无论诊断结果如何，都不能把持股变动的历史交易日期、当前价格或交易均价加入评分；只有公告后留出期也支持的、预注册的完整策略才可能进入纸面观察。

大宗交易是另一种收盘后公开的日频事件。接口同时附带上榜后 1/5/10/20 日涨跌幅，脚本在**请求层**排除这些后验字段，只保存成交额加权折溢率、成交额/流通市值和同日笔数；事件于当日收盘形成、下一本地交易日开盘前可用于评分，保留 3 个日历日：

```bash
python scripts/a_share_short_horizon_factor_research.py sync-block-trade-events \
  --start-year 2019 --end-year 2026
python scripts/a_share_short_horizon_factor_research.py factor-diagnostic \
  --fundamentals data/raw/a_share/fundamentals/quarterly_quality.parquet \
  --block-trade-events data/raw/a_share/events/block_trades.parquet \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062 \
  --max-block-trade-age-days 3
```

这只测试公开大宗成交在质量合格股票中的短期横截面关联，并不识别交易双方意图或可成交性；公开快照可能修订，且“当日收盘后可用于下一开盘”的时点需要交易所级发布流进一步验证。未通过跨年度稳定性时，不得通过切换折溢率方向、扩大窗口或补充事后价格字段来挽救结果。

北向个股净买卖在 2024 年后不再是连续可得的日度公开字段，涨停池公开接口也不能提供可靠的历史快照；两者不能作为当前三日策略的前瞻因子源。下一类独立假设使用仍持续披露的**融资融券交易明细**：每个本地交易日只保留融资净买入额（`RZJME`）最高的固定前 100 只 A 股，再用当天市值归一化融资净买入、融资买入和融资余额，并保留融资余额增速。未进入前 100 的股票是“未观察”，绝不写成零流入；报表自带的 `RCHANGE3DCP`、`RCHANGE5DCP`、`RCHANGE10DCP` 后验涨跌幅在请求、存储和评分三处均排除。

```bash
python scripts/a_share_short_horizon_factor_research.py sync-margin-financing-events \
  --start 2019-01-01 --end 2026-07-13 --top-n 100
python scripts/a_share_short_horizon_factor_research.py factor-diagnostic \
  --fundamentals data/raw/a_share/fundamentals/quarterly_quality.parquet \
  --margin-financing-events data/raw/a_share/events/margin_financing_top_flows.parquet \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062 \
  --max-margin-financing-age-days 0
```

融资明细在当日收盘形成，因此只用于下一本地交易日开盘前的评分；默认不会把它向后带入下一天。公共源可能滞后一两个本地交易日，清单会单列尚未发布的日期，不能用旧日流量冒充最新流量。即使诊断跨年通过，也必须继续经固定稳定性、Top‑3 可行性和新的未来纸面观察，不能直接生成选股名单。

首次全历史快照完成后，后续只获取新日期并合并到同一文件；新抓到的相同“股票/日期”会覆盖旧快照行，未重新请求的历史行保持不变。每次更新仍需查看清单中的 `source_not_published_dates`：

```bash
python scripts/a_share_short_horizon_factor_research.py sync-margin-financing-events \
  --start 2026-01-01 --merge-existing
```

机构调研明细源虽然带有公告日，但接口每页上限 50 条，并在约第 52 页持续返回 `9701`（服务器繁忙）；完整 2019–2025 快照无法稳定取得。因此它被记录为**来源不可用**，不得以短期片段替代完整开发期，更不能进入选股评分。

下一类独立假设是**首次股票回购计划公告**。公开清单一次覆盖 2005 年以来的 5,000 余条记录，脚本只请求首次计划记录日 `DIM_DATE`、计划回购占公告前一日总股本比例上限 `ZSZSX` 与计划金额上限 `JESX`；`UPDATEDATE`、实施进度、已回购股份与已回购金额都会在后续改变，故在请求、存储和评分中全部排除。公告时刻没有可靠的盘中时间，因此从公告后的下一本地交易日才生效，固定使用 3 个日历日窗口：

```bash
python scripts/a_share_short_horizon_factor_research.py sync-repurchase-plan-events
python scripts/a_share_short_horizon_factor_research.py factor-diagnostic \
  --fundamentals data/raw/a_share/fundamentals/quarterly_quality.parquet \
  --repurchase-events data/raw/a_share/events/repurchase_plans.parquet \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062 \
  --max-repurchase-age-days 3
```

回购计划事件在质量门后每年只有很少的非重叠 cohort；即使某一汇总指标看起来积极，也必须通过现有的至少 200 个 cohort、跨年度 Rank IC 与 Top‑3 可行性审计，不能凭小样本晋级。

另一类已核验的独立事件是**股东户数变动公告**。脚本按每个季度末拉取全市场快照，只请求股票代码、`HOLD_NOTICE_DATE`、股东户数增减比例和增减绝对值；季度末 `END_DATE` 只用于下载分片，绝不用于信号时点。`INTERVAL_CHRATE`、户均市值、户均持股、总市值和总股本均为价格或后续状态字段，在请求层排除；信号严格从公告后的下一本地交易日生效，窗口固定为 3 个日历日：

```bash
python scripts/a_share_short_horizon_factor_research.py sync-holder-count-events \
  --start-year 2019 --end-year 2025
python scripts/a_share_short_horizon_factor_research.py factor-diagnostic \
  --fundamentals data/raw/a_share/fundamentals/quarterly_quality.parquet \
  --holder-count-events data/raw/a_share/events/holder_count_changes.parquet \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062 \
  --max-holder-count-age-days 3
```

在固定开发期中，户数增减比例和绝对值的总体 Rank IC 均为负，且 Top‑3 净收益无法稳定跨年；新鲜度也未通过年度方向与回撤要求。因此三项户数因子均被淘汰，不能反向、扩窗或并入现有组合。

下一类独立假设是**股东股权质押公告**。历史快照按 `NOTICE_DATE` 分年下载；脚本只请求股票代码、公告日、质押股数 `PF_NUM` 和该公告记录披露的总股本占比 `PF_TSR`，把同一股票同一公告日的多笔质押聚合为总量、总占比和事件笔数。当前价、交易日、当前市值、预警/平仓线、解押状态与解押日期都在请求层排除。信号严格从公告后的下一本地交易日生效，窗口固定为 3 个日历日：

```bash
python scripts/a_share_short_horizon_factor_research.py sync-pledge-events \
  --start-year 2019 --end-year 2025
python scripts/a_share_short_horizon_factor_research.py factor-diagnostic \
  --fundamentals data/raw/a_share/fundamentals/quarterly_quality.parquet \
  --pledge-events data/raw/a_share/events/share_pledges.parquet \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062 \
  --max-pledge-age-days 3
```

这是当前公开源的历史快照，不是交易所级逐时点披露库；快照可能修订或漏收历史记录。在固定 2019–2025 开发期中，质押股数、总股本占比、事件笔数和新鲜度都取得了 374–399 个 cohort，但全部存在年度 Rank IC 反向且 Top‑3 最大回撤为 −51.3% 至 −61.8%，没有任何字段通过稳定性或可行性审计。因此这四项质押因子均被淘汰，不能反向、扩窗或并入选股评分和交易计划。

**沪深股通逐股日频持仓/净流入**不再是可用来源：交易所自 2024‑08‑19 起只在每日收市后公布总成交额和前十活跃证券，并改为每季度第五个交易日公布上季度末单只证券持股。它无法完整覆盖固定的 2019–2025 三日开发期，故不得用 2024 年前的片段、后续季度数或缺失值补零来研究或评分。

另一类独立假设是**分红送配预案公告**。脚本按 `PLAN_NOTICE_DATE` 分年下载，仅请求每十股税前现金分红 `PRETAX_BONUS_RMB` 和送转总比例 `BONUS_IT_RATIO`，并将同一股票同日记录聚合。方案进度、最新公告日、股权登记/除权日、股息率、财务字段和所有源内未来收益字段都在请求层排除；信号严格从预案公告后的下一本地交易日生效，窗口固定为 3 个日历日：

```bash
python scripts/a_share_short_horizon_factor_research.py sync-dividend-plan-events \
  --start-year 2019 --end-year 2025
python scripts/a_share_short_horizon_factor_research.py factor-diagnostic \
  --fundamentals data/raw/a_share/fundamentals/quarterly_quality.parquet \
  --dividend-plan-events data/raw/a_share/events/dividend_plans.parquet \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062 \
  --max-dividend-plan-age-days 3
```

固定开发期中，四项预案因子仅形成 4–124 个非重叠 cohort，未达到 200 个最低样本门槛；现金分红项还出现负的 Top‑3 净收益（−58.3%）和 −70.8% 最大回撤。全部四项均未通过稳定性和可行性审计，因此被淘汰，不能通过延长窗口、反向或合并其他因子来绕过样本不足。

季度财报的 `--through-report-date` 必须设为已经公开的最新报告期；例如 2026 年 7 月不能请求尚未披露的 2026‑06‑30 或之后报告。业绩预告使用同名参数时，可使用已出现预告公告的报告期，但不能把尚未公告的缺失值解释成负面信号。季度全历史请求较长时，可以按不重叠年份范围分别下载到临时 Parquet，再显式合并；合并前的分片不能单独作为研究数据。最终合并会按股票与报告期保留最早公告，并重新写入完整清单：

```bash
python scripts/a_share_short_horizon_factor_research.py sync-quarterly-fundamentals \
  --start-year 2019 --end-year 2020 --output data/raw/a_share/fundamentals/quarterly_2019_2020.parquet
python scripts/a_share_short_horizon_factor_research.py sync-quarterly-fundamentals \
  --start-year 2021 --end-year 2022 --output data/raw/a_share/fundamentals/quarterly_2021_2022.parquet
python scripts/a_share_short_horizon_factor_research.py sync-quarterly-fundamentals \
  --start-year 2023 --end-year 2024 --output data/raw/a_share/fundamentals/quarterly_2023_2024.parquet
python scripts/a_share_short_horizon_factor_research.py sync-quarterly-fundamentals \
  --start-year 2025 --end-year 2026 --through-report-date 2026-03-31 \
  --output data/raw/a_share/fundamentals/quarterly_2025_2026q1.parquet
python scripts/a_share_short_horizon_factor_research.py merge-quarterly-fundamentals \
  --input data/raw/a_share/fundamentals/quarterly_2019_2020.parquet \
  --input data/raw/a_share/fundamentals/quarterly_2021_2022.parquet \
  --input data/raw/a_share/fundamentals/quarterly_2023_2024.parquet \
  --input data/raw/a_share/fundamentals/quarterly_2025_2026q1.parquet
```

每个候选组合会在 `data/experiments/short_horizon/` 写入一个独立 JSON；同一批运行另有一个 `*_study.json` 汇总文件。记录包含因子权重、年报文件哈希、股票池、成本、发展期/测试期切分以及净收益、波动、回撤和胜率；汇总文件另提供全部 100 个策略按开发期风险调整分数排序的 `ranking_by_development`。候选组合只按 `2025-12-31` 以前的发展期结果选择，之后的测试期不会参与选优。

### 三日持有的迭代研究规范

短线研究的默认持有期是 **3 个本地交易日**。默认 `v1` 候选库运行完整的 100 个预先声明组合；`v2_microstructure` 保留这 100 个组合，并额外加入 10 组一/二日反转、收盘位置、一日量能/换手、短波动/振幅和 60 日趋势假设与 5 个质量覆盖层的交叉组合，共 150 个。每次 `run` 都会把候选库版本、指纹、因子权重、持有期、成本、开发期胜者、独立测试表现和晋级结论追加至 `data/experiments/short_horizon/strategy_registry.json`。注册表是追加式的：新一轮研究不能覆盖或重写旧结果。

`v3_quality_grid` 保留 V2 的全部候选，并增加 20 个不重复的 `quiet_long_trend` 质量网格组合。它把 ROE、营收、增长、综合和利润质量输入分别与 5%/10%/15%/20%/25% 权重交叉，排除 V2 中已有的 5 个等价组合。这样可区分“质量指标种类”与“质量权重”这两个假设；V3 仍须先只在开发期选择，再从未见过的收盘日开始前瞻观察。

`v4_freshness` 在 V3 基础上增加 6 个“营收质量 × 财报新鲜度”组合。财报新鲜度不是报告期的未来信息，而是每个收盘日距该股票最近一份**已生效公告**的天数的横截面反向排名；该公告仍严格在公告日后的下一交易日才生效。它用于检验较新的公开信息是否能改善短线候选的稳定性，任何结果都必须另行前瞻观察。

`v5_defensive` 保留 V4 的全部候选，再增加 30 个防御型延续组合：低 20 日实现波动、低 5 日平均振幅和两者并用的 3 个信号蓝图，分别与五类质量输入和 10%/15% 质量权重交叉。这里的低波动是同日合格股票横截面中的反向排名，区别于已有“中等波动”目标；全部数值在信号收盘时已知。该库专门检验三日持有的尾部回撤能否改善，仍必须经独立的前瞻纸面观察。

`v6_soft_risk` 保留 V5 的全部候选，再增加 40 个“软风险排序”组合：把收盘远离当日高点的回撤偏好、一日回撤，或其与低 20 日波动的组合直接计入延续分数。它源自最差 cohort 的描述性归因（最差组反而更接近日内高点），但不使用硬门槛、不开盘前未知的变量，也不从被拒绝的篮子中替换第四只股票。4 个信号蓝图均与五类质量输入和 10%/15% 质量权重做完整交叉；必须与旧库一起经长历史压力扫描。

```bash
python scripts/a_share_short_horizon_factor_research.py run \
  --hold-days 3 --topk 20 \
  --iteration-label three_day_cycle_001
```

V6 的三日 Top3 压力扫描示例（只用于研究记录，不登记前瞻策略）：

```bash
python scripts/a_share_short_horizon_factor_research.py run \
  --candidate-library v6_soft_risk \
  --start 2019-01-01 --end 2026-07-13 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --regime-filter always \
  --open-cost 0.00012 --close-cost 0.00062 \
  --selection-policy positive_year_stability_mdd20 --research-only
```

在设计下一轮候选前，可先运行 `factor-diagnostic`。它在**仅限开发期**的数据上，对所有已声明因子以及尚未进入候选库的短趋势、成交量/换手、流动性、波动形状、跳空反转、近期高点和日内强度字段，计算每个非重叠信号日的三日横截面 Rank IC、Top‑3 相对 Bottom‑3 的毛收益差，以及各自然年的汇总。它不产生策略、不会从因子排序自动选出赢家；后续组合仍必须预注册，并以未见日期验证。

诊断还会纳入三个公告后基本面变化字段：本年年报相对上一年报的 ROE 变化、营收同比加速度和利润同比加速度。它们均在**新年报公告后的下一个本地交易日**才进入截面，第一份缺少前期年报的记录保持为空；因此它们适合检验“业绩改善是否有短期延续”，不把随后披露的财报反填到历史日期。

```bash
python scripts/a_share_short_horizon_factor_research.py factor-diagnostic \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062
```

为避免只按一次平均 Rank IC 追逐偶然结果，应对已保存的诊断运行固定的跨年度稳定性审计。默认门槛不可按结果调整：至少 5 个自然年和 200 个非重叠 cohort、总体平均 Rank IC 为正、正 Rank IC cohort 占比高于 50%、Top‑3 相对末 3 的平均毛收益差为正，并且每个已观察自然年的平均 Rank IC 都为正。审计只记录“可提出独立假设”的因子，**不会**选择权重、生成策略、登记前瞻观察或给出选股名单：

```bash
python scripts/a_share_short_horizon_factor_research.py factor-stability-audit \
  --diagnostic data/experiments/short_horizon/<run_id>_factor_diagnostic.json
```

如只复核一个已声明因子，可显式限定名称，仍使用同一套门槛：

```bash
python scripts/a_share_short_horizon_factor_research.py factor-stability-audit \
  --diagnostic data/experiments/short_horizon/<run_id>_factor_diagnostic.json \
  --factor amplitude_low
```

结果写成独立、追加式的 `*_factor_stability_audit.json`，`report` 只汇总其审计结论。通过的因子仍必须另行预注册为完整策略，并从真正未见的未来收盘日开始积累纸面样本。

Rank IC 稳定也不等于反复持有 Top‑3 可以承受回撤。因此在组合任何通过关联审计的因子前，使用第二个固定门槛复核诊断本身的 Top‑3 重建：它要求关联审计通过、每个已观察自然年的 Top‑3 **净**累计收益为正、整体净累计收益为正，并且最大回撤不差于 −20%。成本、买入/卖出时点直接取自输入诊断，不能通过本命令改写：

```bash
python scripts/a_share_short_horizon_factor_research.py factor-topk-viability-audit \
  --diagnostic data/experiments/short_horizon/<run_id>_factor_diagnostic.json \
  --factor amplitude_low --factor amplitude_low_1 \
  --factor volatility_low_20 --factor volume_dry_up
```

这是开发期的单因子淘汰器，不是独立回测，也不是策略晋级。若它没有留下因子，不能为了寻找通过结果而改阈值或立刻换权重；应保留失败记录并研究一个预先声明、与既有量价字段独立的假设。

`v7_reversion_ic` 是一次明确标为**诊断驱动的历史敏感性研究**：它保留 V6 的候选，另加入 12 个“5 日回撤、缩量、高开强度、收盘回撤”组合，并分别使用仅质量门、5% 增长质量和 10% 综合质量。该方向来自开发期单因子诊断，因而即使长历史表现较好，也只能作为已见样本上的研究记录，不能自动登记前瞻观察或替换既有候选。

```bash
python scripts/a_share_short_horizon_factor_research.py run \
  --candidate-library v7_reversion_ic \
  --start 2019-01-01 --end 2026-07-13 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --regime-filter always \
  --open-cost 0.00012 --close-cost 0.00062 \
  --selection-policy positive_year_stability_mdd20 --research-only \
  --iteration-label v7_ic_guided_historical_diagnostic
```

扩展后的开发期诊断把此前未入库的 10 日反转列为唯一新的正向信号（3 日动量方向相反），因此 `v8_reversal_10_ic` 只预注册 12 个“10 日回撤、缩量、跳空”敏感性组合。它不与已拒绝的旧库重新竞赛，也不允许登记或前瞻晋级；其作用只是检验这个不同的反转窗口能否改善三日持有的稳定性。

```bash
python scripts/a_share_short_horizon_factor_research.py run \
  --candidate-library v8_reversal_10_ic \
  --start 2019-01-01 --end 2026-07-13 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --regime-filter always \
  --open-cost 0.00012 --close-cost 0.00062 \
  --selection-policy positive_year_stability_mdd20 --research-only \
  --iteration-label v8_ten_day_reversal_historical_diagnostic
```

`v9_compression_reversal_ic` 紧接 V8 的开发期单因子诊断，但不重复被否定的长趋势权重。它将低 5 日振幅、低当日振幅、低 20 日波动、缩量和 10 日回撤拆为 4 个压缩/反转蓝图，并与同样 3 种质量模式交叉，共 12 个组合。因为这些字段是根据同一开发期诊断选出的，V9 只能做历史敏感性记录，绝不登记或产生前瞻选股名单。

```bash
python scripts/a_share_short_horizon_factor_research.py run \
  --candidate-library v9_compression_reversal_ic \
  --start 2019-01-01 --end 2026-07-13 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --regime-filter always \
  --open-cost 0.00012 --close-cost 0.00062 \
  --selection-policy positive_year_stability_mdd20 --research-only \
  --iteration-label v9_compression_reversal_historical_diagnostic
```

如果固定权重因子库和市场状态都不能通过稳定性门槛，可使用三日滚动模型审计来**检验**有限非线性交互，而不是继续事后微调权重。它使用同一组收盘可知因子、下一交易日开盘进入和第 3 个交易日收盘退出；Ridge、浅层 LightGBM 回归和浅层 LightGBM LambdaRank 均在每个评估年开始前用此前最多 336 个非重叠信号日重新训练。训练样本对每个信号日用与收益标签无关的确定性哈希最多取 384 只股票；LambdaRank 只在训练样本内按每个信号日的后续收益分为五档，直接学习横截面排序，绝不把未来标签带入评分时点。

默认审计还将每种模型与三个**预先固定、收盘可知**的市场状态组合：始终交易、20 日广度为正、以及“20 日广度为正且波动不高于严格追溯的 75 分位”。这不是在全部状态中事后挑选；三种状态均来自已有的因子研究定义，并在同一开发期规则下和模型一起参与选择。停用状态时该轮完整按现金记录，不会用别的日期或股票替换。

2023–2025 仅用于模型/状态组合选择，2026 只作检查；任一组合必须每个开发年度为正且整体最大回撤不差于 −20% 才能在审计中标为合格。该命令只写入模型审计，绝不会登记策略或产生选股名单。

```bash
python scripts/a_share_short_horizon_model_research.py \
  --start 2019-01-01 --end 2026-07-13 \
  --development-start 2023-01-01 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062 \
  --train-window-rounds 336 --maximum-train-rows-per-signal 384
```

模型预测会在与未来收益合并**之前**形成完整 Top‑3；若其中任一股票后来缺少进出场报价，整组按现金记录而不会用第四只股票替换。汇总同时展示实际持仓周期比例，避免低频空仓被误读为模型优势。

固定权重 V9 未通过后，可额外检验一个更受限的聚合假设：只让模型读取已经通过固定跨年度单因子稳定性审计的 `amplitude_low`、`amplitude_low_1`、`volatility_low_20` 和 `volume_dry_up`。这不是把 V9 的失败组合换权重重测，而是一个单独、显式命名的受限模型特征集；其字段来自已完成的开发期诊断，因此整个运行始终是**历史敏感性审计**，即使结果为正也不能登记、晋级或产生选股名单。

```bash
python scripts/a_share_short_horizon_model_research.py \
  --feature-set v2_stable_price_volume \
  --fundamentals data/raw/a_share/fundamentals/quarterly_quality.parquet \
  --start 2019-01-01 --end 2026-07-13 \
  --development-start 2023-01-01 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062 \
  --train-window-rounds 336 --maximum-train-rows-per-signal 384
```

2023--2025 仍是唯一的配置选择区间；2026 只写入已经看过的隔离检查，不可据此追加字段、改变模型、选择状态或发出信号。审计 JSON 会记录 `feature_set`、字段清单和形成规则，方便与原始全量特征模型区分。

该受限特征集已在 2026-07-14 完成记录为 `20260714T002011Z`：9 个“模型 × 固定状态”组合均不合格。最接近的是 Ridge + `breadth_20_positive`，开发期三年均为正、累计净收益 +82.44%，但最大回撤为 −32.18%，违反 −20% 硬上限；其已见 2026 检查的 +17.18% 不参与选择，不能用来放松门槛。这个特征集至此淘汰，不再通过扩状态、调回撤线或按 2026 表现改变其字段来重复测试。

在继续扩展因子库前，可先运行“滚动候选选择审计”检验现有策略族是否经得起反复的时间切分。它在每个测试年度开始前，只用此前至少两个完整自然年的**已完成持有周期**从整库选出一个候选，再以紧接的完整年度作为隔离测试；跨年但在边界之后才退出的 cohort 不会进入训练。它不生成策略登记、纸面信号或选股名单：

```bash
python scripts/a_share_short_horizon_factor_research.py walk-forward-selection-audit \
  --candidate-library v2_microstructure \
  --start 2019-01-01 --end 2025-12-31 \
  --first-test-year 2021 --last-test-year 2025 \
  --hold-days 3 --topk 3 --regime-filter breadth_5_above_20 \
  --open-cost 0.00012 --close-cost 0.00062 \
  --selection-policy positive_year_stability_mdd20
```

该审计的每个下一年收益都不参与该折的候选选择；合并的样本外指标仅用于判断策略族的稳定性，不能被用来事后挑选胜者或替换已经登记的前瞻观察。若审计明确否定某个策略族，可以追加暂停记录，但不能改写过去的登记或收益记录。

新假设应先固定为新库，再仅在开发期内筛选。以下是 V2 的开发期登记示例：它不读 2026，且没有测试段时强制保持研究状态。

```bash
python scripts/a_share_short_horizon_factor_research.py run \
  --candidate-library v2_microstructure \
  --start 2023-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --regime-filter breadth_5_above_20 \
  --open-cost 0.00012 --close-cost 0.00062 --research-only \
  --iteration-label three_day_v2_development_preregistration
```

默认选择规则按开发期的年化收益与回撤综合排序。若担心单一市场年份主导总收益，可显式使用 `--selection-policy positive_year_stability`：开发期至少包含两个年度，且**每个**开发年度均为正，再按“最差年度累计净收益 − 0.5 × 全开发期最大回撤”选择。这是新的研究轮次，必须与默认规则分开记录、分开前瞻观察，不能事后改写原轮次的胜者。

若要把开发期回撤作为硬风险约束，可使用 `--selection-policy positive_year_stability_mdd20`：除上述“至少两个年度且每年为正”的稳定性条件外，开发期最大回撤必须不差于 **-20%**，再按相同稳定性分数选优。它和较宽松规则是两个独立的研究假设；仅在已有历史段表现较好不构成晋级，仍需从未见过的收盘日开始积累前瞻纸面样本。

这里的最大回撤以策略开始前的初始净值 `1.0` 作为首个高水位。因此，首个持有周期发生亏损时也会计入回撤，不能被首笔交易后的净值基数掩盖。

研究的 `TopK` 必须与要验证的组合数量一致。若准备验证 20 万元账户的“最多三只、每只 5%”执行规则，应明确使用 `--topk 3`；三只中必须至少三只具有完整的进/出场日线，不能在缺失报价时悄悄换成四只或把资金重分配。

如果较晚的测试区间已经被看过，只能作为历史诊断，绝不能晋级或替代正在纸面观察的策略。以下命令使用你的实际费率（买入 0.012%，卖出 0.062%）进行这种诊断，并将结果强制标为 `research_only_not_promoted`：

```bash
python scripts/a_share_short_horizon_factor_research.py run \
  --hold-days 3 --topk 3 --regime-filter breadth_5_above_20 \
  --open-cost 0.00012 --close-cost 0.00062 --research-only \
  --iteration-label three_day_top3_historical_diagnostic
```

可把收盘后计算出的市场广度作为独立的状态因子，例如只在质量股票池平均 5 日收益为正时做多：`--regime-filter breadth_5_positive`。未满足状态时的三日持有周期在回测中按持有现金的零收益计入，不会因为跳过交易而虚增年化收益。

不要把某个状态规则当作默认真理。可对一个已记录候选运行 `regime-audit`，一次比较 `always`、两种单周期正广度、短期广度强于中期广度，以及三种更保守的确认条件：`breadth_5_and_20_positive`（双周期为正）、`breadth_5_positive_and_above_20`（短期为正且强于中期）和 `breadth_5_above_20_and_20_positive`（双周期为正且短期更强）。报告只按开发期排序并写入单独审计 JSON，不能用它回写已登记候选或把历史结果包装成前瞻收益。

在广度审计不能稳定降低回撤后，状态库还预先声明了六个整体风险状态：正 20 日广度同时要求当日合格股票 20 日波动率中位数低于其**严格滞后一日**的 252 交易日中位数或 75 分位数；正广度同时要求一日横截面收益离散度低于严格滞后阈值；以及正广度叠加“多数股票站上 20 日均线”的两个组合条件。阈值至少需要 60 个历史交易日，缺少历史阈值时策略保持空仓。每个汇总都会同时记录总 cohort、实际成交 cohort、状态激活 cohort 及其比例，不能把多数时间空仓造成的低波动误读为策略本身有效。它们是统一的、收盘后可计算的风险状态敏感性网格，不是对历史结果挑出的止损规则；仍只能进行研究审计，且不自动获准前瞻使用。

```bash
python scripts/a_share_short_horizon_factor_research.py regime-audit \
  --candidate expanded_v3_quiet_long_trend_q15_revenue \
  --candidate-library v3_quality_grid \
  --start 2023-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062 \
  --selection-policy positive_year_stability_mdd20
```

若需要检验三日持仓中的个股尾部损失，可对固定候选运行 `loss-cap-audit`。它把无上限与 5%/8%/10% 的**收盘确认**损失上限并列比较：从入场日起，若某只股票的日收盘相对入场开盘跌破上限，则假设按该收盘退出，资金在本周期余下时间保持现金。它不是盘中止损成交，也不模拟跌停无法卖出；因此只能作为研究敏感性审计，绝不能直接应用到已有前瞻策略。

```bash
python scripts/a_share_short_horizon_factor_research.py loss-cap-audit \
  --candidate expanded_v5_defensive_low_range_q15_composite \
  --candidate-library v5_defensive \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --regime-filter breadth_5_above_20 \
  --open-cost 0.00012 --close-cost 0.00062 \
  --selection-policy positive_year_stability_mdd20
```

若最差 cohort 归因显示高开入场值得单独检验，可运行 `entry-gap-audit`。它并列比较无上限与次日开盘跳空 2%/4%/6% 上限：在开盘后，只有三只原定股票都不高于上限时才形成完整篮子；任一股票超过上限就整组空仓，绝不替换成事后挑出的第四只。跳空在开盘前不可知，因而这是执行敏感性审计，不是收盘信号因子或自动前瞻策略变更。

```bash
python scripts/a_share_short_horizon_factor_research.py entry-gap-audit \
  --candidate expanded_v5_defensive_low_range_q15_composite \
  --candidate-library v5_defensive \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --regime-filter always \
  --open-cost 0.00012 --close-cost 0.00062 \
  --selection-policy positive_year_stability_mdd20
```

若怀疑 Top‑3 实际上集中于同一价格波动簇，先运行 `basket-correlation-audit`，而不是从股票名称猜测行业。它逐个信号日计算三只股票截至该日收盘的 20 日两两收益相关性；只把**完整 20 日窗口**纳入汇总。相关性只是一种统计集中度代理，不会自动成为选股规则。

```bash
python scripts/a_share_short_horizon_factor_research.py basket-correlation-audit \
  --candidate expanded_v5_defensive_low_range_q15_composite \
  --candidate-library v5_defensive \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --regime-filter breadth_5_above_20 \
  --open-cost 0.00012 --close-cost 0.00062 --correlation-lookback 20
```

只有在相关性诊断形成假设后，才运行 `diversification-audit`。它把无约束与最大两两相关性 0.50/0.60/0.70 并列比较：在因子排名前 30 个股票中贪心选择完整三只，所有两两相关性都不高于上限；无法构成完整三只则该周期空仓。它不允许半仓或把空余资金转给未测试的第四只股票，且仍只能作为研究敏感性审计。

```bash
python scripts/a_share_short_horizon_factor_research.py diversification-audit \
  --candidate expanded_v5_defensive_low_range_q15_composite \
  --candidate-library v5_defensive \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --regime-filter breadth_5_above_20 \
  --open-cost 0.00012 --close-cost 0.00062 \
  --correlation-lookback 20 --diversification-candidate-pool 30 \
  --selection-policy positive_year_stability_mdd20
```

若风险控制的效果不明确，先用 `cohort-risk-audit` 归因最差完整三日 cohort。它逐只保留入场、退出、三日收益以及信号日的流动性、低波动、低振幅、质量和动量**横截面排名**；输出用于形成新假设，不能把个别名称反向变成交易黑名单。

```bash
python scripts/a_share_short_horizon_factor_research.py cohort-risk-audit \
  --candidate expanded_v5_defensive_low_range_q15_composite \
  --candidate-library v5_defensive \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --regime-filter breadth_5_above_20 \
  --open-cost 0.00012 --close-cost 0.00062 --worst-cohorts 10
```

`risk-gate-audit` 随后以一个小型、完整的资格门网格检验归因所得假设：`volatility_low_20` 和 `amplitude_low` 的最低横截面排名分别取无门、0.20、0.40，共 9 个组合。它们不改变因子分数；不满足门槛而凑不齐完整三只时，该周期空仓。若硬门显著恶化结果，应保留这个反证，而不是继续提高阈值。`cohort-risk-audit` 还会记录从信号日收盘到次日开盘的实际入场跳空；它是开盘时才可观察的执行变量，不会混入收盘已知的因子排名。

```bash
python scripts/a_share_short_horizon_factor_research.py risk-gate-audit \
  --candidate expanded_v5_defensive_low_range_q15_composite \
  --candidate-library v5_defensive \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --regime-filter breadth_5_above_20 \
  --open-cost 0.00012 --close-cost 0.00062 \
  --selection-policy positive_year_stability_mdd20
```

若多个候选都进入前瞻观察，先运行 `candidate-overlap-audit` 判断它们是否实质上选了同一批股票。它报告同一信号日的平均 Jaccard 重叠、完全相同篮子比例及三日净收益序列相关性；高重叠代表候选之间的证据不应被当作独立样本。同一因子库可重复传入 `--candidate`，跨因子库时必须显式使用 `--candidate-spec 因子库:候选名`，避免名称被误解为另一套权重。

```bash
python scripts/a_share_short_horizon_factor_research.py candidate-overlap-audit \
  --candidate-spec v2_microstructure:expanded_v2_quiet_long_trend_q15_growth \
  --candidate-spec v3_quality_grid:expanded_v3_quiet_long_trend_q15_revenue \
  --start 2023-01-01 --end 2026-07-13 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --regime-filter breadth_5_above_20 \
  --open-cost 0.00012 --close-cost 0.00062
```

若 `--end` 晚于 `--development-end`，报告会明确标注“测试期参与相似度”。这时它只能描述候选是否相似，不能用来选择权重、晋级策略或改写前瞻观察；若只需要开发期独立性证据，应令两个日期相同。

若补齐较早年度的年报，可把同一审计扩展到更长历史作为压力测试；结果必须额外标注为受“当前上市清单”幸存者偏差影响的稳健性证据，不能替代新的前瞻样本或用来追溯晋级。

长历史压力扫描允许并应当记录 `no_eligible_candidate`：若没有候选同时满足预设的跨年度与回撤约束，系统不会勉强登记赢家、不会创建前瞻观察，也不应事后放松门槛来得到一个看似可用的策略。

`report` 会在“未产生合格候选的压力扫描”章节列出这些淘汰结果，并在“市场状态审计”“收盘损失上限审计”“次日开盘跳空审计”“篮子相关性审计”“相关性分散化审计”“最差 Cohort 风险归因”和“波动/振幅资格门审计”章节保留固定候选的敏感性比较及合格数量，使长历史失败不会被后续研究日志掩盖。任何审计即使出现开发期胜者，也只是一条研究记录，不能自动晋级。

当某轮策略在注册表中通过初测后，筛选命令必须带上它对应的状态条件，例如：

```bash
python scripts/a_share_short_horizon_factor_research.py screen \
  --candidate expanded_trend_ma_confirmation_q20_composite \
  --regime-filter breadth_5_above_20 --topk 20
```

筛选结果会显式写入 `regime_active`。当它为 `false` 时，不产生候选名单，`plan` 也会拒绝生成下单计划；这代表策略规定的空仓，而不是数据故障。

通过初测的策略不应马上被视为可实盘策略。每次收盘数据更新后，运行纸面观察器：它只在状态允许时追加一笔不可修改的模拟信号；三日后的本地日线齐全时，才用“下一日开盘买入、第三日收盘卖出”和研究成本结算实际样本外结果。

```bash
python scripts/a_share_short_horizon_factor_research.py monitor \
  --not-before 2026-07-14
```

`--not-before` 必填，必须填写这个策略第一次**真正未见过**的收盘日。当前本地数据已看到 2026-07-13，因此通过初测的主策略最早只能从 2026-07-14 开始纸面观察；在 7 月 13 日或更早的本地数据上运行会返回 `not_started`，不会写入台账。信号和结算记录保存在 `data/experiments/short_horizon/three_day_paper_ledger.json`。若当日状态不满足策略条件，观察器只记录空仓状态，不创建纸面持仓。不要将纸面台账的未结算信号当作已实现收益。

开发期胜者可以进入**独立的前瞻纸面观察**，但仍不是已晋级策略。必须先显式登记第一个真正未见过的收盘日；`shadow-monitor` 只读此登记，写入与主策略完全分离的 `three_day_shadow_paper_ledger.json`，不会生成 `plan` 或任何下单指令：

```bash
python scripts/a_share_short_horizon_factor_research.py shadow-register \
  --iteration-id <development_only_iteration_id> --not-before 2026-07-14
python scripts/a_share_short_horizon_factor_research.py shadow-monitor
```

若该迭代已有历史测试周期，或者未显式指定开始日期，登记会被拒绝。这样可以防止把已经看过的历史行情伪装成前瞻纸面收益。

若发现收益、成本或风险指标的实现有误，或新的时间隔离稳健性审计否定了研究假设，不能删除或覆写已经登记的前瞻观察。应先暂停该轮次，再使用修正后的实现或新的、预先声明的假设重跑研究，并将新得到的迭代 ID 作为独立观察重新登记：

```bash
python scripts/a_share_short_horizon_factor_research.py shadow-suspend \
  --iteration-id <old_iteration_id> --reason "documented metric correction"
```

暂停记录是追加式的；`shadow-monitor` 会跳过被暂停的轮次，`report` 会列出原因和时间。只有修正后重新产生的、从真正未见收盘日开始的登记，才可以继续积累纸面样本。

`report` 会将每个登记候选单独列出首个可用收盘日、信号数、结算数、待结算数和已结算累计净收益；不要把不同候选的收益混合成一个“组合结果”。

每次研究或纸面观察后，可生成面向人工复盘的汇总日志；它汇总所有迭代的开发/测试表现、晋级状态以及纸面信号和结算数量：

```bash
python scripts/a_share_short_horizon_factor_research.py report
```

日志默认写入 `data/experiments/short_horizon/three_day_research_report.md`。它是注册表和纸面台账的派生视图；策略判断始终以不可覆盖的 JSON 原始记录为准。

选择只使用 `--development-end` 以前的数据；测试段不参与因子权重或策略排名。一个开发期胜者只有在测试段至少有 20 个独立持有周期、累计净收益为正且最大回撤不差于 -20% 时，才会标为 `passed_initial_test`；否则仍是研究候选，不能进入后续实盘/模拟盘计划。每次新因子或新组合必须新开一轮并写明标签，不能在同一测试段反复调到满意为止。

日常迭代顺序是：收盘后更新数据 → 运行三日研究 → 查看注册表中新旧轮次的开发/测试差异 → 仅将通过初测的策略用于下一阶段模拟盘观察。未来有新的、未见过的交易日时，才把它加入新的测试观察；不要用已看过的 2026 测试结果反复改权重。

### 2026-07-13 研究检查点

截至本地 2026-07-13 收盘，V7--V9 的固定权重反转/压缩组合均未通过开发期稳定性与 −20% 回撤门槛；回购、户数、质押和分红预案等独立事件因子也已按各自的样本量和跨年度审计淘汰。滚动模型审计仍仅是历史诊断：季度质量版本中唯一通过开发期规则的 Ridge + “20 日广度为正且波动不高于追溯 P75”组合，在已见的 2026 检查段净收益为 −0.48%，不能登记或替代现有策略。

因此本轮不对失败组合改方向、放松样本或回撤阈值，也不使用 2026 已见结果发明新的权重。注册表中唯一 `passed_initial_test` 的旧策略从 2026-07-14 起才允许主纸面观察；在该日期之后积累的信号和三日结算，才是下一次是否保留、暂停或重新设计假设的独立证据。此检查点不构成当前选股名单或买卖建议。

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

在建模前或数据源/转储逻辑发生改变后，运行全量审计。它逐个读取全部 Parquet 文件、逐字段比对全部 Qlib 二进制值、检查日历和股票池，并抽样用 Qlib 读取器和东财最新日线复核。审计还会将 `universe_latest.json` 的上市日期与每只本地股票的日线起止区间、`buyable_main_chinext`／`factor_main_chinext_star` 的 Qlib 区间逐一比对；这能证明本地保留股票不会在上市前或数据结束后被交易，并显示已结束交易区间的股票数量。它不能证明当前公共快照包含完整的历史退市名单，该限制会明确保留。结果写入 `data/metadata/dataset_audit.json`。

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
