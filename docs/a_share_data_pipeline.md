# A 股日频数据管线

这个仓库的选股数据统一放在仓库根目录下的 `data/`，不会写入 `~/.qlib`。

```
data/
  raw/a_share/daily/       # 每只股票一份原始价 + 点时复权因子 Parquet，可审计、可重建
  metadata/                # 每日股票清单快照和每次运行的失败清单
  qlib/cn_a_share/         # Qlib 二进制数据
  logs/                    # 定时任务日志
```

## 覆盖范围

默认清单和日线来自东财公开接口；当东财历史接口限流或断连时，可用免费、匿名登录的 BaoStock 日线作为独立恢复源。两者都不需要用户账号、令牌或 Cookie。
接口说明可见 [AKShare 的 A 股历史数据文档](https://akshare.akfamily.xyz/data/stock/stock.html)。数据源可能限流或更改，管线会重试并在 `data/metadata/runs/` 中记录失败股票；不要把公共数据源视作交易所级数据。

| Qlib 股票池 | 代码前缀 | 用途 |
| --- | --- | --- |
| `buyable_main_chinext` | 600/601/603/605、000/001/002/003、300/301 | 主板 + 创业板，可作为模型选股和持仓范围 |
| `factor_main_chinext_star` | 上述代码，加 688/689 | 加入科创板，适合扩展因子或研究范围 |

北交所、B 股、ETF、指数、基金会被排除。`ST` 不会被静默删除，而是在 `data/metadata/universe_latest.json` 中以 `is_st` 标记；是否剔除它应由策略的可交易性规则决定。

## 首次下载

在仓库根目录运行：

```bash
python scripts/a_share_data_pipeline.py sync --scope factor --start 2015-01-01 \
  --adjust point_in_time
```

首次任务会对主板、创业板和科创板逐只下载历史日线，可能需要较长时间。默认从 2015 年开始，兼顾模型训练所需样本与本机磁盘空间；磁盘充足时可通过 `--start 2010-01-01` 扩展。为避免“原始 CSV + Qlib 二进制”占满笔记本磁盘，可审计原始层采用 Zstandard 压缩的 Parquet 格式；它可安全重跑，已有股票只会重拉最近 45 个自然日并合并数据。想先验证整个流程而不下载全市场，可以运行：

```bash
python scripts/a_share_data_pipeline.py sync \
  --symbols 600519,300750,688981 --start 2020-01-01
```

若首次全市场回填被中断，可只补缺失的股票，随后单独从本地原始数据构建 Qlib 二进制：

```bash
python scripts/a_share_data_pipeline.py sync --scope factor --only-missing --skip-dump \
  --adjust point_in_time
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

默认使用 `point_in_time`：下载未复权 OHLCV，以每个收盘时已经公开的 `pct_chg` 串成连续价格指数；同日 `factor = adjusted_price / raw_price`，并用同一个 factor 调整 VWAP、反向调整成交量。它不会用后来发生的分红送转去重写更早的价格，且可以从 Qlib 复权价还原实际成交价。`qfq`/`hfq` 仅保留给源数据排错，不能通过研究物化门槛。

在 15:30 前只更新到上一个工作日，避免把未收盘日线写进训练集。只有明确需要盘中研究时，才使用 `--include-current-session`。日常更新重拉最近 45 天并从整只股票的原始收益链重新计算 factor；不再需要为了未来公司行动每周重述全部历史。

若东财接口持续断连，可整库切换 BaoStock；同一份研究数据不允许股票间混用日线源。BaoStock 使用独立进程连接，`--workers 3` 为保守默认值：

```bash
python -m pip install baostock==0.9.3
python scripts/a_share_data_pipeline.py sync --scope factor --source baostock \
  --adjust point_in_time --force-full --start 2015-01-01 --skip-dump
python scripts/a_share_data_pipeline.py price-basis-audit
python scripts/a_share_data_pipeline.py materialize
```

如果审计只报告源端 `amount/volume` 算出的 VWAP 不在同日未复权 OHLC 内，先运行 `quarantine-vwap`，再重新审计。该命令保留异常 `raw_vwap` 与原成交额/成交量供追溯，仅将对应的研究 `vwap` 置空；绝不把均价夹到最高/最低价，也不修改 OHLC、收益或复权因子：

```bash
python scripts/a_share_data_pipeline.py quarantine-vwap
python scripts/a_share_data_pipeline.py price-basis-audit
```

通过报告允许非零 `source_vwap_quarantined_rows`，但要求 `source_vwap_unquarantined_rows=0` 和 `adjusted_vwap_outside_ohlc_rows=0`。隔离记录保存在 `data/metadata/repairs/`。

中断后改用 `--only-missing --source baostock --adjust point_in_time --skip-dump`：已有且已达到同一 source/basis、日期完整的文件会跳过；旧 qfq 文件虽然路径存在，仍会被视为“缺少新合同”并全量替换。

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

在它之前先运行全市场价格口径审计：

```bash
python scripts/a_share_data_pipeline.py price-basis-audit
```

审计不读取任何未来收益，必须得到 `status=passed`、单一 `daily_sources`、零缺失合同列、零 VWAP 越界、零 adjusted/raw 还原错误与零 `pct_chg` 链错误。物化成功后，`data/qlib/cn_a_share/price_basis.json` 才会写成 `passed`；所有研究命令都会先验证它。`validate_a_share_factor_readiness.py` 现在也把 VWAP 不在 OHLC 范围内或 `$factor` 覆盖不足视为硬失败，而不是警告。

2026-07-14 的尾部归因发现旧 qfq 数据存在系统性错误：5,449 个文件、11,130,132 行中，约 6,807,341 行的未复权 VWAP 不在前复权 OHLC 内，5,302 只股票受影响，且 `$factor` 完全缺失；高分红股票还出现主板三日 −50% 至 −77% 的不可能回报。旧数据的全部因子诊断、候选策略、模型收益、前瞻台账和选股分数因此都是**无效证据**，只能保留作审计记录。修复后必须从窗口语义审计、全因子基线和两道固定门槛重新开始，不能把新结果与旧收益直接拼接或比较。

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

在技术/质量候选库的滚动检验被淘汰后，不能再从同一批连续因子里微调权重。本项目额外预先固定了一条不同的**限价样强势收盘事件**：主板日收盘收益至少 9.5%、创业板（`SZ300`/`SZ301`）至少 19.5%，且收盘价距当日日高不超过 0.5%；只在这些事件中按同日换手异常度取完整 Top‑3，次日开盘买入、第 3 日收盘卖出。少于 3 个可成交事件不会以非事件股票补足。修复后它以点时收益链推断“限价样”现象，而非交易所官方涨停标签；旧 qfq 运行已经失效。不模拟次日封板、停牌或排队无法成交，因此只是一项开发期淘汰/分流审计：

```bash
python scripts/a_share_short_horizon_factor_research.py limit-like-event-audit \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062
```

通过也不能直接生成选股名单或登记策略；它仍需一条独立、未见日期开始的完整纸面观察。若不通过，固定门槛、Top‑3 和三日持有期不应再被放松或替换成更好看的变体。

另一条独立的公告后漂移假设只使用**新生效的季度报告**：公告严格在下一本地交易日才生效；在该日收盘时，若公司仍通过质量门槛且其同财季利润同比相对上一年同财季的加速度大于零，则按原始加速幅度取完整 Top‑3，次日开盘买入、第 3 日收盘卖出。报告发布当日、陈旧报告与非事件股票都不进入篮子。它检验公告后延续，而不是把日常 `profit_yoy_acceleration` 横截面因子再换一次权重：

```bash
python scripts/a_share_short_horizon_factor_research.py quarterly-profit-acceleration-event-audit \
  --fundamentals data/raw/a_share/fundamentals/quarterly_quality.parquet \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062
```

这是固定的开发期事件审计。若不通过，不得把负向加速、反转方向、不同报告窗口或不同 TopK 当作同一假设继续回测；若通过，仍须在新的、未见日期开始的前瞻观察中验证。

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

机构调研明细源带有公告日，但接口每页上限 50 条，旧同步器按整年查询时会在约第 52 页持续返回 `9701`（服务器繁忙），所以旧的年度同步尝试无效，任何短期片段都不得进入研究或评分。修复后的同步器从不重叠自然月开始；若某月超过 40 页，会在读取高页码前按日历日期递归二分。每个最终分片都要求服务端声明的总行数与实际逐页抓取行数完全一致，任一分片失败则不写最终 Parquet 或清单：

```bash
python scripts/a_share_short_horizon_factor_research.py sync-institutional-survey-events \
  --start-year 2019 --end-year 2025
```

2024 年 1 月的完整无写入验收已连续读取 32 页、精确核对 1,600/1,600 条源记录，过滤非 A 股与重复披露后形成 1,352 个股票公告日事件。正式 2019–2025 快照随后于 2026-07-15 完成：108 个连续且逐一核对的日期分片共读取 2,587 页、126,639 条源明细，归一为 107,939 个股票公告日事件；公告日覆盖 2019-01-01 至 2025-12-31，股票/公告日重复键为 0，Parquet SHA-256 为 `d55491709c9b6c89a759e0048593885d96b55848c5a3ea74617b4c84e61c3299`。请求和存储只包含股票代码、公告日、接待日期区间和披露机构数量，不包含参与者身份、当前价格或公告后收益。

完整快照通过验收只让来源进入**无收益容量门禁**，不代表因子有效。容量协议已在读取任何开盘、收盘或未来收益前冻结为 `docs/a_share_institutional_survey_capacity_preregistration.json`，固定检查机构数量、同日调研事件数和 0–3 日新鲜度三个原始高值方向；使用 2019–2025 非重叠三日网格、Top‑3、每截面至少 6 个有效名字和 2 个不同值、550 日季度质量、上市满 20 会话与至少 200 个潜在 cohort。命令不暴露这些语义参数，且只允许成功写出一次审计：

```bash
python scripts/a_share_short_horizon_factor_research.py institutional-survey-capacity-audit
```

唯一一次容量审计已完成为 `20260714T172717Z_institutional_survey_capacity_audit.json`，明确记录 `price_fields_loaded=[]`、`forward_return_fields_read=false` 和 `selection_or_promotion_allowed=false`。机构数量、同日事件数和新鲜度分别形成 **507、402、495** 个潜在完整 cohort，三项均跨 2019–2025 每年覆盖并超过 200，因此来源获准进入一次固定收益诊断；这仍不代表因子有效。

三因子共同诊断在读取行情前另行冻结为 `docs/a_share_institutional_survey_event_diagnostic_preregistration.json`，并绑定容量审计、两份输入快照与清单的 SHA-256。专用命令不暴露因子、方向、事件年龄、日期、成本、质量源或 TopK 覆盖，且只能成功完成一次：

```bash
python scripts/a_share_short_horizon_factor_research.py institutional-survey-event-diagnostic
```

正式诊断已完成为 `20260714T173339Z_factor_diagnostic.json`，默认稳定性与 Top‑3 可行性审计均为 `20260714T173402Z`，两门都通过 **0/3**。新鲜度是表面收益最强的一项：495 个 cohort 的 Top‑3 扣费累计收益为 +292.02%，但总体 Rank IC 为 −0.00431、正 IC 比例仅 49.49%、Top‑3 减 Bottom‑3 平均毛收益差为 −0.1523%，2019/2022/2023/2024/2025 年 IC 不为正，最大回撤 −24.54%，且 2022 年 Top‑3 净收益为负。机构数量的总体 Rank IC 为 −0.01649、正 IC 比例 46.15%，虽然 Top‑3 累计 +166.85%，最大回撤达到 −52.45%，2019/2020/2021/2023 年 IC 为负。事件数总体 Rank IC 为 −0.00680，Top‑3 累计 −30.59%、最大回撤 −55.00%。

因此三个原始“高机构数 / 高事件数 / 更新鲜”方向全部正式停止：不反向、不修改三日年龄、不筛年份或因子、不与日线或其他公告因子组合、不重跑诊断，也不生成当前选股。容量通过只证明样本足够完成一次有效检验；表面累计收益不能绕过关联稳定性和回撤门禁。

原始明细还包含接待起止日，但上述三因子没有使用这一时间结构。下一项独立机制在获取新的完整 timing 快照前冻结为 `docs/a_share_institutional_survey_timing_data_contract.json`：对同一股票和公告日取最晚接待结束日，计算 `公告日 − 最晚接待结束日` 的日历天数，并固定检验“披露越及时越好”的 `institutional_survey_prompt_disclosure`。它不是机构数、事件数或公告后新鲜度的反向版本；信号仍严格从公告后的下一本地交易日生效，事件年龄仍为 3 个日历日。

2019-01、2024-01、2025-01 的无收益字段验收确认历史两端都有接待日期，中位时滞均为 1 天且分别存在 46、37、55 个不同值。2019-01 有 2 条接待结束日晚于公告日的源异常；冻结协议要求将负时滞事件排除并在清单计数，不截断、不取绝对值、不改方向。独立命令写入新的 timing 文件，不覆盖已经绑定旧诊断指纹的机构调研计数快照：

```bash
python scripts/a_share_short_horizon_factor_research.py sync-institutional-survey-timing-events
```

完整 timing 快照随后成功：108 个连续分片、2,587 页和 126,639 条源明细与已验收的计数快照逐项一致；排除 26 个负时滞事件键后形成 107,913 行，股票/公告日重复键、缺失值和公式不一致均为 0。时滞共有 105 个不同值，中位数 1 天、95% 为 7 天以内、最大值 355 天且未截尾；Parquet SHA-256 为 `0b1544ac400f021ed632fbf5810967c5a1d6acd9d7fbb6334a743c19f824f5eb`。

无收益容量协议已绑定数据合同、timing 快照、季度质量、两份清单及旧计数清单的指纹，冻结为 `docs/a_share_institutional_survey_timing_capacity_preregistration.json`。命令只读取交易日历、上市活动区间、季度质量和时滞事件，不读取任何行情字段：

```bash
python scripts/a_share_short_horizon_factor_research.py institutional-survey-timing-capacity-audit
```

容量审计已完成为 `20260714T180635Z_institutional_survey_timing_capacity_audit.json`：质量与上市门禁后有 22,032 行有效事件值、539 个有值事件日和 **507/200** 个潜在完整 cohort，2019–2025 分别为 48、71、80、80、78、77、73；审计明确记录 `price_fields_loaded=[]` 与 `forward_return_fields_read=false`。

唯一一次收益诊断在读取行情前另行冻结为 `docs/a_share_institutional_survey_timing_diagnostic_preregistration.json`。它只运行 `institutional_survey_prompt_disclosure = 1 − rank(披露时滞)`，方向固定为低原始时滞、事件年龄 3 天，并绑定容量审计、timing 快照和季度质量指纹：

```bash
python scripts/a_share_short_horizon_factor_research.py institutional-survey-timing-diagnostic
```

唯一一次正式诊断已完成为 `20260714T181535Z_factor_diagnostic.json`，完整默认稳定性与 Top‑3 可行性审计均为 `20260714T181636Z`，两道门槛的通过数均为 **0/1**。507 个 cohort 的平均 Rank IC 为 **-0.00680**，正 IC 比例为 **46.55%**，TopK-minus-BottomK 毛收益差为 **-0.144%**；2021–2024 四个连续年份的平均 IC 均为负。Top‑3 净累计收益虽为 +113.93%，但来源高度不稳定：2019、2021、2023、2024 年分别亏损，最大回撤为 **-38.13%**，3 日净收益的 1%/5% 分位为 -7.64%/-4.86%，最差一期为 -10.73%。因此停止 `institutional_survey_prompt_disclosure`，不进入聚合、当前评分或选股。不能在同一历史上改为高时滞、修改聚合日期、截尾 355 天极值、挑年份、增加事后过滤器，或与已淘汰的机构数量因子组合。

下一项真正独立的细颗粒度来源是带发布日期的**分析师评级调整**。公开研报接口同时返回标题、作者、券商、EPS、PE、目标价和发行信息，但冻结合同 `docs/a_share_analyst_rating_data_contract.json` 只允许请求股票代码、发布日期、研报唯一键与评级调整码。源页面给出的调整字典为 `0=调高、1=调低、2=首次、3=维持、4=无`；同一股票/发布日期只在 `0–3` 的有效研报中计算“调高占比”，代码 4 与缺失值不进入分子或分母。无报告的股票保持缺失；只有当天确有有效报告但没有调高时，零才是合法值。标题、作者、券商身份、预测值、PE、目标价、当前价格和任何未来收益均不请求、不存储。

冻结前的无收益字段样本覆盖 2019-Q1、2024-Q1、2025-Q1，分别读取 2,302、3,089、2,227 条源记录；其中评级调整码有效 2,110、2,816、1,972 条，调高记录 62、23、28 条。三个季度分别有 38、16、20 个日期同时满足至少 6 只股票和 2 个调高占比值，说明值得构建完整快照，但不等于容量已通过。相反，同接口的 EPS 修订方案因历史字段断层在读取收益前即停止：较宽样本中，当年 EPS 可用数仅为 6/1,049/12,376，下一年 EPS 为 3/0/852，无法形成 2019–2025 同口径多期限序列。

同步命令固定下载 2019–2025，以不重叠自然月起步，超过 80 页时按日期二分；每个最终分片必须让接口 `hits` 与逐页实收行数完全一致，任一失败均不得写最终文件：

```bash
python scripts/a_share_short_horizon_factor_research.py sync-analyst-rating-events
```

每条事件在发布日期后的下一本地交易日才生效，年龄固定为 3 个日历日。完整快照完成后，仍必须先另行冻结并运行无开盘、收盘或未来收益的 200-cohort 容量门禁；容量未通过就停止，不能把静态买入评级、首次覆盖、报告数量、EPS/PE 或文本情绪临时加入来补容量。

完整快照已于 2026-07-15 完成：84 个连续自然月共 1,215 页、117,248 条源记录全部逐分片核对，排除非目标代码/缺失键 2,318 条和代码 4/缺失调整 6,198 条后，108,732 条有效评级记录聚合为 86,643 个股票/发布日期事件。调高记录 1,249 条，形成 1,233 个调高占比大于零的事件行和 16 个不同占比值；事件覆盖 2019-01-01 至 2025-12-31，重复键与缺失值均为 0，Parquet SHA-256 为 `30d51a93c98912d27b2f9d4236843766fab2b2c298c0e7acb1382d89d12a87ea`。清单明确记录 `price_fields_loaded=[]` 与 `forward_return_fields_read=false`。

无收益容量协议已绑定上述快照、清单、数据合同与季度质量指纹，冻结为 `docs/a_share_analyst_rating_capacity_preregistration.json`。它固定 2019–2025、非重叠三日、Top‑3、每截面至少 6 名且 2 个值、550 日季度质量和上市满 20 会话，且只允许成功写出一次：

```bash
python scripts/a_share_short_horizon_factor_research.py analyst-rating-capacity-audit
```

该命令通过交易日历和上市活动区间计算容量，不加载任何行情字段。只有达到 200 个潜在完整 cohort 才能另行冻结一次收益诊断；容量通过本身不代表评级调高有效。

唯一一次容量审计已完成为 `20260714T183854Z_analyst_rating_capacity_audit.json`（SHA-256 `1d0973d5560db6ba76c46e1925f0e5eddfb90bf3e7a08b55da917f1c7a77c105`）。三日事件展开后有 61,515 行候选值，季度质量与上市门槛后保留 24,413 行、542 个有值事件日，最终形成 **224/200** 个潜在完整 cohort；2019–2025 分别为 30、42、42、38、22、26、24。审计明确记录 `price_fields_loaded=[]`、`open_close_or_forward_return_fields_read=false` 和 `selection_or_promotion_allowed=false`。来源获准另行冻结一次固定收益诊断，但这 224 个 cohort 只是容量，不是收益、稳定性或可交易性证据。

唯一一次收益诊断已在读取行情前冻结为 `docs/a_share_analyst_rating_diagnostic_preregistration.json`。它只允许 `analyst_rating_upgrade_share` 高值方向，固定 2019–2025、事件年龄 3 天、Top‑3、开/平仓成本 0.012%/0.062%、550 日季度质量与上市满 20 会话，并绑定容量审计、事件快照和质量快照 SHA-256。专用命令不暴露日期、方向、因子、年龄、成本、质量或 Top‑3 等语义参数：

```bash
python scripts/a_share_short_horizon_factor_research.py analyst-rating-diagnostic
```

命令会先再次验证预注册、容量审计和两个输入快照的指纹，只把调高占比接入次日生效、3 个自然日过期的截面排名；报告数量只保留为事件审计上下文，不参与排名。完成后必须对产物运行完整默认稳定性与 Top‑3 可行性审计；不得使用通用多因子诊断顺带查看其他研报字段。

唯一一次正式诊断已完成为 `20260714T184904Z_factor_diagnostic.json`（SHA-256 `69a6e0c4646ca312caa5b2714a0d1c60a64d97c73ca67a29d0d93d6119d2040c`），完整默认稳定性与 Top‑3 可行性审计均为 `20260714T184914Z`，通过数均为 **0/1**。224 个 cohort 的平均/中位 Rank IC 为 +0.01364/+0.01734，正 IC 比例 53.13%，TopK-minus-BottomK 毛收益差 +0.156%；这些汇总值为正，但 2020、2023 年平均 IC 分别为 -0.01560、-0.04673，未通过逐年同向门禁。Top‑3 扣费累计收益为 +53.82%，但中位单期收益为 -0.141%、胜率仅 48.21%，2021、2023 年分别亏损 37.45%、16.04%，最大回撤 **-55.91%**，3 日净收益的 1%/5% 分位为 -7.05%/-4.59%，最差一期 -9.15%。稳定性审计 SHA-256 为 `07f5ee43f373fc6c218d795f519c50169cbbd3914f655a3a089021cddca610e8`，Top‑3 审计 SHA-256 为 `f104405b0780a6ea79a7b3037696f1b1e7630fdd948ad09c88760acdbfc50230`。因此停止 `analyst_rating_upgrade_share`，不进入聚合、当前评分或选股；不得在同一历史上反向、改变事件年龄、加入静态评级/首次覆盖/报告数/预测值/文本，挑选年份或增加事后过滤器。

下一项独立的细颗粒度来源是**限售股实际解禁压力**，完整快照前已冻结为 `docs/a_share_restricted_share_unlock_data_contract.json`。正式请求只允许股票代码、解禁日、实际解禁股数、实际解禁股数占总股本比例、批次股东数和限售类型；价格、实际解禁市值、占流通市值比例、最新收盘价、解禁前/后 20 日收益和股东姓名均禁止请求或存储。唯一因子为 `restricted_share_unlock_pressure = 1 − rank(实际解禁股数 / 总股本)`，低原始比例固定为更好；由于没有可验证的历史日程公告版本，最早只在解禁日收盘（非交易日则其后首个本地交易日收盘）形成信号，下一交易日开盘进入，事件年龄 3 个自然日。

冻结前的无收益样本覆盖 2019‑Q1、2024‑Q1、2025‑Q1，接口分别核对 430、622、400 条源记录，目标 A 股为 430、586、339 条，比例字段全部可用且股票/解禁日重复键均为 0；分别有 31、41、27 个日期满足至少 6 只股票与 2 个不同压力值，观察比例范围为 0 至 0.872149498753。三个相邻候选在收益读取前停止：回购终态金额完成率只有 153 个六名/两值日期且 2020、2023 为 0；上证 e 互动官方检索只支持最近 30 天，无法与深市形成可重放的 2019–2025 共同档案；重大合同的上年营收与收入占比字段在 2024‑Q1/2025‑Q1 几乎为空，当前“最新营收”又包含后续修订，不能用于历史点时归一化。

完整同步以 2019–2025 连续自然月分片，逐片核对接口公告行数，任一页失败都不写最终文件：

```bash
python scripts/a_share_short_horizon_factor_research.py sync-restricted-share-unlock-events
```

完整快照已于 2026-07-15 完成：84 个连续自然月、84 页和 16,286 条源记录均逐分片核对，保留 15,360 条目标 A 股解禁事件，排除 926 条非目标或合同字段缺失记录。事件覆盖 2019-01-02 至 2025-12-31，股票/解禁日重复键、合同字段缺失、负实际解禁股数和比例越界均为 0；比例为零 110 条，共 14,983 个不同值。各年保留 1,876、2,150、2,253、2,572、2,594、2,327、1,588 条，Parquet SHA-256 为 `da4e8ac847927dd13f79067e195025ba0933345e2352c24cddf3821e68d37a52`；清单明确记录 `price_fields_loaded=[]` 与 `forward_return_fields_read=false`。

同步完成仍不允许读收益。无收益容量协议已绑定快照、清单、数据合同与季度质量指纹，冻结为 `docs/a_share_restricted_share_unlock_capacity_preregistration.json`。它固定 2019–2025、非重叠三日、Top‑3、每截面至少 6 名且 2 个值、550 日季度质量、上市满 20 会话和至少 200 个 cohort；命令只读取日历、上市区间、季度质量和事件字段：

```bash
python scripts/a_share_short_horizon_factor_research.py restricted-share-unlock-capacity-audit
```

容量审计只能成功写出一次，并必须保持 `price_fields_loaded=[]`。容量不足即停止，不能改用解禁市值、前后收益、提前日程信号、股东身份、其他方向或更宽事件年龄补救；容量通过也只允许在读取价格前另行冻结一次精确的低原始解禁比例诊断，不代表因子有效。

唯一一次容量审计已完成为 `20260714T191131Z_restricted_share_unlock_capacity_audit.json`（SHA-256 `23b8dae5e8e8c354a9125e609274ca2fc4505b49a52e2d2b79ff605fcc0f26aa`）。三日事件展开后有 12,749 行候选值，季度质量与上市门槛后保留 3,153 行、495 个有值事件日，最终形成 **244/200** 个潜在完整 cohort；2019–2025 分别为 22、44、51、50、30、31、16。审计明确记录 `price_fields_loaded=[]`、`forward_return_fields_read=false` 和 `selection_or_promotion_allowed=false`。这只解锁一次预注册收益诊断，不是有效性或可交易性证据。

唯一一次收益诊断已在读取行情前冻结为 `docs/a_share_restricted_share_unlock_diagnostic_preregistration.json`。它只允许 `restricted_share_unlock_pressure = 1 − rank(实际解禁股数 / 总股本)` 的低原始比例方向，固定 2019–2025、事件年龄 3 天、Top‑3、开/平仓成本 0.012%/0.062%、550 日季度质量与上市满 20 会话，并绑定容量审计、解禁快照和季度质量快照指纹。专用命令不暴露日期、方向、因子、年龄、成本或 Top‑3 覆盖，只能运行一次，并随后执行完整默认稳定性与 Top‑3 可行性审计：

```bash
python scripts/a_share_short_horizon_factor_research.py restricted-share-unlock-diagnostic
```

唯一一次正式诊断已完成为 `20260714T191852Z_factor_diagnostic.json`（SHA-256 `7cff1cd500d046179d8568064288d68b63f500b9e4e47791c19b0abfe5d6a9a5`），完整默认稳定性与 Top‑3 可行性审计均为 `20260714T191908Z`，通过数均为 **0/1**。244 个 cohort 的平均/中位 Rank IC 为 **−0.03707/−0.03571**，正 IC 比例 43.85%，TopK-minus-BottomK 毛收益差 **−0.316%**；除 2022 外，其余六个年份平均 IC 全为负。Top‑3 扣费累计收益虽为 +62.65%、年化约 18.23%、胜率 54.10%，但它与截面关联方向相矛盾，2020、2025 年分别亏损 10.55%、9.89%，最大回撤 **−30.04%**，3 日净收益的 1%/5% 分位为 −7.54%/−5.80%，最差一期 −9.20%。稳定性审计 SHA-256 为 `a3cb59ce8d791b890a2c19072f3cce0ed14e7d78389a19bd3b689fcaa72eba93`，Top‑3 审计 SHA-256 为 `e1d706036e1330ff8a5c5e01772756a36f075757fe4abf81eec83456d3d06423`。因此停止 `restricted_share_unlock_pressure`，不进入聚合、当前评分或选股；不得在同一历史上反向为高解禁压力、改变事件年龄、提前使用日程、挑年份、增加事后过滤器，或与其他已淘汰事件因子组合。

下一项独立的细颗粒度来源是**董监高及相关人员二级市场实际买卖**，完整快照前已冻结为 `docs/a_share_insider_open_market_data_contract.json`。它与已有的“重要股东增减持公告”不同：这里只研究逐笔实际直接市场交易，不使用公告中的计划或累计比例。正式请求严格限于股票代码 `SCODE`、成交日 `TDATE`、变动股数 `CHANNUM`、方向 `BDFX` 和原因 `BDYY`；姓名、职务、关系、成交价、成交金额、变动后持股、总股本、证券简称和任何价格/收益字段均禁止请求或存储。只有契约白名单中的竞价、二级市场买卖、大宗、盘后定价和明确证券买卖行可进入；股权激励、送转、发行、继承、协议转让及其他机械变动全部排除并计数。

跨沪深公开历史字段没有统一可靠的填报/披露时间，故成交日不能直接作为信号时点。契约采用保守的合成可用日：`TDATE` 后**严格第 3 个本地交易日收盘**才形成信号，比两交易日报告窗口再多留一个完整会话，下一交易日开盘进入，事件年龄固定为 3 个自然日。迟报超过规定窗口时，合成日期仍可能早于真实公开时间，这一残余风险必须保留在所有清单和审计中，不能事后删除。唯一候选因子为 `insider_open_market_buy_share = 有效直接市场买入行数 / 有效直接市场买卖总行数`，高值固定为更好；事件数仅作上下文，不参与排名。

冻结前只做了无价格字段样本核验：2019‑Q1、2024‑Q1、2025‑Q1 分别逐页核对 2,690、3,078、2,108 条源记录，保留 2,493、2,000、1,316 条直接市场买卖行，源计数误差均为 0。三个样本分别有 1,980、1,438、998 个股票/成交日键；映射到保守可用日后，满足至少 6 只股票和 2 个买入占比值的日期为 58、56、57。下一步只能先同步 2019–2025 连续完整快照并做无收益容量门禁；容量不足必须停止，不能改用身份、股数大小、成交价、放宽原因或缩短披露延迟补救。

```bash
python scripts/a_share_short_horizon_factor_research.py sync-insider-open-market-events
```

同步按连续自然月开始，超过 80 页的区间递归二分；每个最终分片都必须满足接口广告条数等于实际收到条数。任何失败都不得留下最终快照或清单。同步只读取本地交易日历来生成合成可用日，不读取开盘、收盘或远期收益。

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

旧价格诊断中，户数增减比例和绝对值的总体 Rank IC 均为负，且 Top‑3 净收益无法稳定跨年；新鲜度也未通过年度方向与回撤要求。但该诊断没有点时价格和 20 日上市门禁，收益结论只保留为无效历史。修复后先通过统一的无收益容量门禁；容量不足则停止，容量足够才允许原方向的一次性重建，任何情况下都不能反向或扩窗。

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

这是当前公开源的历史快照，不是交易所级逐时点披露库；快照可能修订或漏收历史记录。旧价格诊断中，质押股数、总股本占比、事件笔数和新鲜度取得了 374–399 个 cohort，但其年度 IC 和 −51.3% 至 −61.8% 回撤都来自后来判定无效的行情口径，不能作为正式淘汰证据。其样本容量值得在 20 日上市门禁下重新确认；通过无收益容量门禁后，也只能按原四因子高值方向做一次点时价格重建。

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

旧价格诊断中，四项预案因子仅形成 4–124 个非重叠 cohort，提示其很可能达不到 200 个最低样本门槛；其中收益与回撤因行情口径无效而不可引用。修复后必须先用不读取开盘、收盘或未来收益的统一容量审计确认上限；若仍不足 200，直接停止，不得通过延长窗口、反向或合并其他因子绕过样本不足。

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

诊断还包含一个独立的流通规模结构假设 `free_float_cap_small`。它以当日成交额除以当日换手率构造流通市值代理（换手率的百分比单位只带来所有股票相同的常数），再偏好该代理值较小的质量合格股票；成交额和换手率均在收盘后、下一交易日开盘前可知。零换手或缺失换手的记录保持为空，绝不以无穷大或零流通市值补齐。该方向是事先声明的“小流通盘可能放大短期价格发现”假设，必须先经下方固定跨年度审计；不因诊断结果改为大流通盘或调整构造式。

该假设已在季度质量快照的 2019--2025 开发期记录为诊断 `20260714T002439Z`。它有 542 个非重叠 cohort，但总体平均 Rank IC 仅 +0.0010，2019、2020、2022 和 2024 的年度平均 IC 为负；单因子 Top‑3 最大回撤为 −41.52%。`20260714T002452Z` 的稳定性及 Top‑3 可行性审计均拒绝该因子。不得反向为“大流通盘”、扩大回看窗口或混入既有策略重新测试。

另一个独立的价格路径假设为 `up_day_consistency_5`：它统计截至信号收盘的五个本地交易日中收盘较前一交易日上涨的比例，并偏好上涨天数较多的质量合格股票。它与五日动量不同：一个大涨日不会自动等同于持续上涨路径。方向在诊断前固定为“持续上涨反映短期买方延续”；若不通过固定审计，不能把方向翻为连续下跌或改为其他回看日数。

该路径假设已在季度质量快照的 2019--2025 开发期记录为诊断 `20260714T002952Z`。542 个 cohort 的平均 Rank IC 为 −0.0113，正 IC 比例为 47.8%；单因子 Top‑3 净累计收益为 −24.55%，最大回撤为 −79.96%。`20260714T003006Z` 的稳定性审计与 `20260714T003007Z` 的可行性审计均拒绝该因子。不得将它反向为连续下跌、改变五日窗口或加入既有组合重新测试。

诊断还会纳入三个公告后基本面变化字段：本年年报相对上一年报的 ROE 变化、营收同比加速度和利润同比加速度。它们均在**新年报公告后的下一个本地交易日**才进入截面，第一份缺少前期年报的记录保持为空；因此它们适合检验“业绩改善是否有短期延续”，不把随后披露的财报反填到历史日期。

```bash
python scripts/a_share_short_horizon_factor_research.py factor-diagnostic \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062
```

每个单因子摘要除 IC、分组收益和累计 Top‑K 结果外，还固定保存 `topk_tail_risk`：Top‑K 单轮净收益的 1%/5% 分位、中位数、亏损比例、跌超 5%/10% 的比例、最差单轮，以及最差 5 个 cohort 的信号日、持仓代码、因子值、三日收益、次日开盘跳空和当时可知的流动性/市值/波动/振幅/动量/收盘位置横截面排名。该尾部归因只解释“为什么正 IC 未变成可承受的三只股票组合”，不参与因子排序、稳定性门槛或策略选择；不得根据最差 cohort 事后增加过滤器来恢复已淘汰因子。旧诊断没有这些字段时，报告显示 `—`，不能从累计净值反推持仓细节。

Qlib 的滚动算子可能在窗口未满时返回部分样本值。开始新的因子排列组合前，应先运行不读取任何未来收益的窗口语义审计；它从本地日历起点读取全部收盘已知字段，逐股票编号交易会话，并检查 5/10/20/60 日 `Mean`、`Std`、`Max`、`Sum`、`Corr` 与 `Ref` 字段是否在声明所需历史形成前意外非空：

```bash
python scripts/a_share_short_horizon_factor_research.py rolling-window-semantics-audit \
  --start 2015-01-01 --end 2026-07-13
```

结果必须记录 `forward_return_fields_read=false`。审计失败只说明输入语义与字段名称/预注册定义不一致，不能说明修复后的收益会更好；应保留旧 JSON、先修复完整窗口语义，再重新界定受影响的历史研究，禁止先看修复后收益再决定哪些字段加保护。

首次正式窗口审计 `20260714T094825Z_rolling_window_semantics_audit.json` 在 4,836 只股票上检查了 29 个字段，`forward_return_fields_read=false`。动量 `Ref`、单日缺口、10 日效率比和已修复的 20 日 MAX 等 10 个字段通过；其余 **19/29** 失败：5 日上涨比例，5/20/60 日均线，量能/换手/流动性均值，5/10/20 日波动率，5 日振幅，10/20 日接近高点，10 日收益/换手相关和 5 日量价压力。多数均值/极值字段从第 1 个会话即有值，波动率和相关性从第 3 个会话即有值。修复固定为一次性给全部 19 个字段加入各自完整窗口所需的零值 `Ref` 保护，不根据任何收益选择字段；修复后必须先重跑本审计达到 29/29，再允许重新计算受影响的历史诊断。

修复后的审计 `20260714T095117Z_rolling_window_semantics_audit.json` 已达到 **29/29 通过**、`failed_factor_count=0`、`forward_return_fields_read=false`。从该运行起生成的新诊断使用完整窗口语义；更早的诊断若包含上述 19 个原始字段或其 `volume_dry_up`、`volatility_target*`、`volatility_low_20`、`amplitude_low`、`drawdown_20`、`up_day_consistency_5`、`compression_consensus_min` 等派生方向，对应因子行自动标为无效，未受影响的因子行仍可保留。报告会显示“部分无效”及有效因子数；旧候选库/模型若使用任一受影响字段，也只能作为旧语义记录，不能晋级或与修复后的运行直接比较。

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

在分钟/资金流授权尚未完成时，下一项独立预注册假设为 `signed_volume_pressure_5`。它先计算每日收盘位置
`(2×close−high−low)/(high−low)`，再用当日成交量对最近 5 个交易日加权；高值表示成交量持续集中在收盘靠近日内高点的交易日。方向固定为“正压力代表短期买方积累，预期次日开盘至第 3 个交易日收盘收益更高”。这里只测试 5 日窗口、正方向和一个因子，不改成 3/10 日、不反向，也不与旧候选库组合。高低价相等导致的无定义值保持缺失。

该因子仍只是日线资金流代理，不冒充逐笔资金流或 Level‑2。先使用固定的 2019–2025 开发期、质量可用股票、非重叠三日 cohort 和既有交易成本，单独运行诊断及两道门槛；`--factor` 保证本轮不查看其他旧因子排名来形成新的组合：

```bash
python scripts/a_share_short_horizon_factor_research.py factor-diagnostic \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062 \
  --factor signed_volume_pressure_5
python scripts/a_share_short_horizon_factor_research.py factor-stability-audit \
  --diagnostic data/experiments/short_horizon/<本轮_factor_diagnostic.json> \
  --factor signed_volume_pressure_5
python scripts/a_share_short_horizon_factor_research.py factor-topk-viability-audit \
  --diagnostic data/experiments/short_horizon/<本轮_factor_diagnostic.json> \
  --factor signed_volume_pressure_5
```

只有跨年至少 5 年、至少 200 个 cohort、总体与逐年 Rank IC 均为正、正 IC 比例超过 50%、Top‑3 相对 Bottom‑3 毛差为正，并且 Top‑3 每年及总体扣费收益为正、最大回撤不差于 −20%，才允许提出下一项预注册组合。失败则原方向淘汰，不用反向或替代窗口重测。

该假设已按上述预注册版本完成。`20260714T081715Z_factor_diagnostic.json` 只包含这一项因子：560 个非重叠 cohort 的平均 Rank IC 为 **−0.0093**，正 IC 比例 **46.4%**；除 2023 年外，2019–2025 其余各年平均 IC 均为负。虽然平均 Top‑3 相对 Bottom‑3 毛差为 +0.63%，但 Top‑3 扣费累计收益为 **−32.90%**、最大回撤为 **−97.15%**，且 2019、2022、2023、2024 年净收益为负。固定稳定性与可行性审计 `20260714T081731Z` 均没有合格因子，因此 `signed_volume_pressure_5` 正方向被淘汰；不得改为负方向、替换窗口或混入旧候选库重测。该失败说明这一日线代理不能证明三日资金流延续，不代表真实分钟资金流或 Level‑2 盘口没有信息。

下一项独立预注册假设为 `close_above_vwap_1 = close/vwap−1`。本地 `vwap` 是当日成交额与成交量形成的日成交均价；因子偏好收盘价高于该均价的股票，方向固定为“尾盘相对全天成交成本更强，买方需求可能延续至之后三日”。它与只使用最高/最低价的 `close_to_high` 不同，但仍是日频摘要。只测试单日正方向，不反向、不平滑为多日窗口，也不与旧因子组合。

```bash
python scripts/a_share_short_horizon_factor_research.py factor-diagnostic \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062 \
  --factor close_above_vwap_1
python scripts/a_share_short_horizon_factor_research.py factor-stability-audit \
  --diagnostic data/experiments/short_horizon/<本轮_factor_diagnostic.json> \
  --factor close_above_vwap_1
python scripts/a_share_short_horizon_factor_research.py factor-topk-viability-audit \
  --diagnostic data/experiments/short_horizon/<本轮_factor_diagnostic.json> \
  --factor close_above_vwap_1
```

沿用与上一项相同的固定稳定性和 Top‑3 可行性门槛。失败时淘汰正方向，不能根据结果改为“收盘低于 VWAP 的反转”或选择别的 VWAP 窗口。

上述 `close_above_vwap_1` 诊断及其数值后来被价格口径审计判定为**无效证据**：当时的 qfq OHLC 与未复权 VWAP 不在同一基准，且没有 `$factor` 可还原。因此，由它事后推导出的 `close_below_vwap_1` 登记 `prospective_close_below_vwap_1_20260714` 也同步失效；不得运行 `prospective-monitor`，不得结算或引用其收益，也不能把旧诊断的正负方向当成新假设依据。

注册表和可能存在的台账不会删除，只作为审计记录保留。研究模块、报告与定时观察器均要求来源记录携带 `price_basis=close_known_raw_pct_chg_chain_v1`；旧登记缺少该字段，会被标记为“价格基准失效”并从收益汇总中剔除。完成全量重建和新因子基线后，若 VWAP 类定义仍有研究价值，必须从新数据提出一份新的、具有新 ID 和新首个未见日期的预注册，不能修补或复用这条旧登记。

下一项独立开发期假设预注册为 `signed_efficiency_ratio_10`：

```text
(close / Ref(close, 10) - 1) / Sum(Abs(close / Ref(close, 1) - 1), 10)
```

分子是 10 个交易日的净涨跌，分母是这 10 日逐日绝对收益之和，因此取值接近 +1 代表价格以较少来回波动完成上涨，接近 −1 代表平滑下跌。方向固定为高值：更有效率的上涨路径可能延续到下一交易日开盘至第 3 个交易日收盘。它不同于只看起终点的 `momentum_10` 和只统计上涨天数的 `up_day_consistency_5`。只测试 10 日、有符号、高值方向；不测试绝对值、负方向、5/20 日窗口或与旧因子的组合。分母为零或非有限值时保持缺失。

仍使用固定 2019–2025 开发期、非重叠三日 cohort、Top‑3、买入 0.012% / 卖出 0.062% 成本及既有两道门槛：

```bash
python scripts/a_share_short_horizon_factor_research.py factor-diagnostic \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062 \
  --factor signed_efficiency_ratio_10
python scripts/a_share_short_horizon_factor_research.py factor-stability-audit \
  --diagnostic data/experiments/short_horizon/<本轮_factor_diagnostic.json> \
  --factor signed_efficiency_ratio_10
python scripts/a_share_short_horizon_factor_research.py factor-topk-viability-audit \
  --diagnostic data/experiments/short_horizon/<本轮_factor_diagnostic.json> \
  --factor signed_efficiency_ratio_10
```

本轮仅回答该定义是否满足预设稳定性和可交易性门槛。失败即淘汰；即使通过，也只能作为设计下一份预注册候选库的开发期证据，不能直接晋级、提高仓位或与正在收集的纯前瞻 VWAP 观察混算。

该假设已按预注册版本完成。`20260714T084753Z_factor_diagnostic.json` 仅包含 `signed_efficiency_ratio_10`：560 个非重叠 cohort 的平均 Rank IC 为 **−0.0279**，正 IC 比例 **40.5%**，Top‑3 相对 Bottom‑3 的平均毛差为 **−0.17%**；2019–2025 每一年的平均 Rank IC 都为负。Top‑3 扣费累计收益为 **−86.93%**、最大回撤为 **−96.88%**；虽然 2019、2020 和 2025 年的 Top‑3 扣费收益为正，其余四年为负，且逐年横截面方向全部失败。`20260714T084806Z` 的稳定性与 Top‑3 可行性审计均没有合格因子，因此 10 日高效率上涨延续方向被淘汰；不得改测负方向、绝对效率、其他窗口或与旧因子组合来恢复它。

覆盖盘点确认已有 87 个唯一因子进入过历史诊断，单字段动量、振幅、波动、换手水平、换手变化和主要公告事件已多次覆盖。下一项机制独立的假设预注册为 `return_turnover_correlation_10`：

```text
Corr(close / Ref(close, 1) - 1, turnover, 10)
```

它在每只股票内部计算最近 10 个交易日“日收益与当日换手率”的相关系数。高值表示上涨日的成交参与通常高于下跌日，方向固定为“需求参与确认可能延续至下一交易日开盘到第 3 个交易日收盘”。这不是当前换手相对均值的 `turnover_surge`，也不是只看价格路径的动量或效率比率。只测试 10 日、高值方向和一个因子；不测试负方向、5/20 日窗口、收益与成交量的替代表达式，也不与已有低波动因子组合。相关系数不可计算或非有限时保持缺失。

检验继续锁定 2019–2025、560 个左右的非重叠三日 cohort、Top‑3 和买入 0.012% / 卖出 0.062% 成本：

```bash
python scripts/a_share_short_horizon_factor_research.py factor-diagnostic \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062 \
  --factor return_turnover_correlation_10
python scripts/a_share_short_horizon_factor_research.py factor-stability-audit \
  --diagnostic data/experiments/short_horizon/<本轮_factor_diagnostic.json> \
  --factor return_turnover_correlation_10
python scripts/a_share_short_horizon_factor_research.py factor-topk-viability-audit \
  --diagnostic data/experiments/short_horizon/<本轮_factor_diagnostic.json> \
  --factor return_turnover_correlation_10
```

沿用跨年至少 5 年、至少 200 cohort、总体与逐年 IC 为正、正 IC 比例超过 50%、Top‑3/Bottom‑3 毛差为正，以及 Top‑3 总体与逐年扣费收益为正、最大回撤不差于 −20% 的固定门槛。失败即淘汰；通过也只允许进入下一轮预注册组合设计，不直接生成选股或前瞻信号。

该假设已按预注册版本完成。`20260714T085351Z_factor_diagnostic.json` 仅包含 `return_turnover_correlation_10`：560 个非重叠 cohort 的平均 Rank IC 为 **−0.0174**，正 IC 比例 **43.9%**，Top‑3 相对 Bottom‑3 的平均毛差为 **−0.76%**；2019–2025 每一年的平均 Rank IC 都为负。Top‑3 扣费累计收益为 **−67.63%**、最大回撤为 **−88.07%**；2019–2021 年篮子收益为正，但 2022–2025 连续为负。`20260714T085414Z` 的稳定性与 Top‑3 可行性审计均没有合格因子，因此“上涨日高换手代表未来三日需求延续”的高值方向被淘汰；不得历史反向、改窗口、替换成交参与字段或与低波动因子组合重测。

### 五日盘中需求延续单因子

分钟数据尚未取得本地授权时，仍可用已验收日线 OHLC 把隔夜跳空与盘中买卖压力分开。`docs/a_share_intraday_demand_persistence_preregistration.json` 已在读取该因子的历史收益前冻结唯一新定义：

```text
intraday_return_sum_5 = Sum(close / open - 1, 5) + 0 * Ref(close, 4)
```

因子只累计最近 5 个完整交易日的开盘到收盘收益；零值引用不改变完整窗口，只保证不足 5 个会话时保持缺失。方向固定为高值，假设多日盘中持续买入比混入隔夜跳空的收盘动量更能延续到下一交易日开盘至第 3 个交易日收盘。它不同于只看信号日的 `intraday_strength`，也不冒充尚未取得的分钟尾盘或 Level‑2 数据。只测试这一窗口和方向，不测试 3/10/20 日、不反向、不增加成交量确认、不与旧失败因子组合。

新增滚动表达式后必须先运行不读取收益的完整窗口审计；审计中 `intraday_return_sum_5` 必须从第 5 个本地会话才首次非空，且 `forward_return_fields_read=false`：

```bash
python scripts/a_share_short_horizon_factor_research.py rolling-window-semantics-audit \
  --start 2015-01-01
```

只有该门禁通过，专用命令才允许按预注册一次性读取 2019–2025 的三日收益。命令不暴露日期、方向、窗口、成本、质量源、持有期、TopK 或因子子集：

```bash
python scripts/a_share_short_horizon_factor_research.py intraday-demand-persistence-diagnostic
python scripts/a_share_short_horizon_factor_research.py factor-stability-audit \
  --diagnostic data/experiments/short_horizon/<本轮_factor_diagnostic.json>
python scripts/a_share_short_horizon_factor_research.py factor-topk-viability-audit \
  --diagnostic data/experiments/short_horizon/<本轮_factor_diagnostic.json>
```

固定口径仍为 2019–2025、非重叠三日 cohort、Top‑3、买入 0.012% / 卖出 0.062%、财务最大年龄 550 天、上市满 20 会话和已验收点时价格。历史区间已被其他假设反复使用，因此不是纯净留出；即使同时通过两道门禁，也只能从新日期登记完全相同因子的纸面观察，不能直接聚合、选股或提高仓位。任一道门禁失败即停止，不允许事后换方向、窗口或组合。

新增字段的无收益窗口审计已完成为 `20260714T165311Z_rolling_window_semantics_audit.json`：当前 30/30 个声明字段全部通过，`intraday_return_sum_5` 的前 4 个本地会话没有任何提前非空值，第 5 个会话才首次有效，且 `forward_return_fields_read=false`。随后唯一一次正式诊断为 `20260714T165528Z_factor_diagnostic.json`，两道完整审计均为 `20260714T165538Z`，结论是 **0/1**。

该高值方向在 560 个 cohort 上的平均 Rank IC 为 **−0.0301**、正 IC 比例 **42.86%**、Top‑3 减 Bottom‑3 平均毛差 **−0.696%**，2019–2025 每一年平均 IC 都为负。最高分五分位的平均未来三日毛收益只有 +0.112%，低于其余四个五分位的约 +0.241% 至 +0.254%。Top‑3 扣费累计收益为 **−99.87%**、最大回撤 **−99.95%**，P5 单轮净收益 **−12.16%**、最差 **−26.64%**，28.93% 的 cohort 跌超 5%；只有 2025 年篮子累计收益为正，但该年平均 IC 仍为 −0.0357。

因此“五日盘中买盘延续”高值方向正式停止，不进入聚合或当前选股，也不反向测试低值、改变窗口或添加低波动/动量/成交量过滤器。最差 cohort 常同时具有极高 20 日动量、极低波动/振幅排名和高换手，只用于解释为什么极端 Top‑3 失效，不能转化为事后救援规则。该失败进一步支持下一阶段应取得真正的一分钟尾盘路径，而不是继续从日 OHLC 摘要中枚举相近公式。

在为稀疏季度公告事件写收益回测前，先运行**无收益样本容量审计**。它只读取季度报告字段、公告后下一交易日、买入股票池活动区间和交易日历；不会加载开盘、收盘或任何未来收益。事件仍固定在非重叠三日网格上，必须有完整 Top‑3，且最大可用 cohort 至少达到既有 200 门槛，才允许继续预注册收益审计：

```bash
python scripts/a_share_short_horizon_factor_research.py quarterly-event-capacity-audit \
  --metric revenue_yoy_acceleration \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --minimum-cohorts 200
```

审计结果必须记录 `forward_return_fields_read=false`。若 `capacity_gate_passed=false`，该事件定义立即停止，不能通过降低 cohort 门槛、改成重叠持仓或先看收益再决定。季度快照当前有 143,776 行、覆盖 2019Q1–2026Q1、5,207 只股票，公告日无缺失且关键键无重复；但公共接口可能包含日后更正，仍不是交易所级点时数据。

营收同比加速的正式容量审计已记录为 `20260714T090242Z_quarterly_event_capacity_audit.json`。在 1,699 个开发期交易日形成的 565 个非重叠三日网格中，质量合格、正营收同比加速且当时处于可交易活动区间的公司共形成 3,660 行候选，但只有 **122/200** 个日期能组成完整 Top‑3：2020–2025 分别为 13、25、24、21、20、19 个。`capacity_gate_passed=false` 且 `forward_return_fields_read=false`，因此营收加速事件在读取任何收益前被淘汰；不实现收益回测，也不降低样本门槛或改用重叠持仓。

在密集日线聚合方向，V9 的 `quiet_dual_compression` 已经测试 `amplitude_low`、`amplitude_low_1`、`volatility_low_20` 和 `volume_dry_up` 的加权和，但加权和允许一个弱项被其他强项补偿。下一项唯一预注册聚合为非补偿式 `compression_consensus_min`：

```text
min(amplitude_low, amplitude_low_1, volatility_low_20, volume_dry_up)
```

四项均为当日横截面 `[0,1]` 百分位，高值只有在五日振幅、单日振幅、20 日波动和五日相对量能都同时偏低时才成立；任一分量缺失则聚合缺失。公式固定为逐行最小值，不测试均值、几何平均、乘积、分位门槛或不同输入。方向固定为高值，假设“多维安静压缩”在未来三日具有正向释放。四个输入本身来自同一 2019–2025 单因子稳定性筛选，因此本轮明确属于**历史敏感性诊断**：即使通过，也不能晋级、登记前瞻信号或产生选股。

```bash
python scripts/a_share_short_horizon_factor_research.py factor-diagnostic \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062 \
  --factor compression_consensus_min
python scripts/a_share_short_horizon_factor_research.py factor-stability-audit \
  --diagnostic data/experiments/short_horizon/<本轮_factor_diagnostic.json> \
  --factor compression_consensus_min
python scripts/a_share_short_horizon_factor_research.py factor-topk-viability-audit \
  --diagnostic data/experiments/short_horizon/<本轮_factor_diagnostic.json> \
  --factor compression_consensus_min
```

仍沿用至少 5 年、200 个非重叠 cohort、总体与逐年 IC/Top‑3 收益为正、正 IC 比例超过 50%、Top‑3/Bottom‑3 毛差为正和最大回撤不差于 −20% 的门槛。失败即停止该聚合，不改聚合函数或阈值重测。

该聚合已按预注册版本完成。`20260714T091316Z_factor_diagnostic.json` 仅包含 `compression_consensus_min`：560 个非重叠 cohort 的平均 Rank IC 为 **+0.0457**，正 IC 比例 **64.3%**，且 2019–2025 每一年的平均 IC 都为正；但最高 3 只相对最低 3 只的平均毛收益差为 **−1.90%**，未通过极端篮子方向门槛。Top‑3 扣费累计收益虽为 **+55.60%**，最大回撤却达到 **−51.82%**，2021、2023 和 2024 年的扣费收益分别为负。`20260714T091342Z` 的稳定性和 Top‑3 可行性审计均没有合格因子，因此该非补偿式压缩共识被淘汰：它显示全横截面存在弱正单调关系，但最高分尾部不具备稳定可交易性；不得根据结果改成均值、几何平均、乘积、阈值组合、反向或替换输入重测。

在既有日线字段覆盖已接近饱和、分钟供应商尚无本地验收快照的条件下，下一项机制独立假设预注册为 `max_return_20_low`：

```text
raw_max_return_20 = Max(close / Ref(close, 1) - 1, 20) + 0 * Ref(close, 20)
max_return_20_low = 1 - cross_sectional_percentile_rank(raw_max_return_20)
```

20 个交易日包含信号日，修复后输入使用本地点时调整收盘价；额外的 `0 * Ref(close, 20)` 不改变完整窗口的 MAX 值，只强制不足 20 日的股票保持缺失，因为 Qlib 的滚动 `Max` 默认接受短窗口。高值方向固定，表示过去约一个月没有出现极端正收益日。该方向源自 Bali、Cakici 与 Whitelaw 的 [MAX 彩票偏好研究](https://doi.org/10.1016/j.jfineco.2010.08.014) 及 [中国市场 MAX 证据](https://doi.org/10.1016/j.najef.2021.101475)：高 MAX 股票后续回报较低。原研究主要使用月度形成/持有期，并不能证明三日预测，因此本轮只检验把该机制转移到“收盘信号、次日开盘进入、第 3 日收盘退出”后是否仍成立；不测试 5/10/60 日窗口、最大负收益、绝对收益、均值或与波动率组合。

```bash
python scripts/a_share_short_horizon_factor_research.py factor-diagnostic \
  --start 2019-01-01 --end 2025-12-31 --development-end 2025-12-31 \
  --hold-days 3 --topk 3 --open-cost 0.00012 --close-cost 0.00062 \
  --factor max_return_20_low
python scripts/a_share_short_horizon_factor_research.py factor-stability-audit \
  --diagnostic data/experiments/short_horizon/<本轮_factor_diagnostic.json> \
  --factor max_return_20_low
python scripts/a_share_short_horizon_factor_research.py factor-topk-viability-audit \
  --diagnostic data/experiments/short_horizon/<本轮_factor_diagnostic.json> \
  --factor max_return_20_low
```

沿用至少 5 年、200 个非重叠 cohort、总体与逐年 IC 为正、正 IC 比例超过 50%、Top‑3/Bottom‑3 毛差为正、Top‑3 总体及逐年扣费收益为正且最大回撤不差于 −20% 的固定门槛。失败即淘汰三日低 MAX 方向；不得根据结果反向、改窗口或把论文的月度结果当成本项目验证。

`20260714T092057Z_factor_diagnostic.json`、其 `20260714T092154Z` 两道审计以及补充尾部诊断 `20260714T093043Z` **不得作为该预注册假设的有效结论**。尾部持仓揭示 `SZ300879`、`SZ300880`、`SZ300881` 等刚上市股票在 `momentum_20` 为空时仍取得了低 MAX 分数；直接查询确认 Qlib 的 `Max(..., 20)` 会从第 2 个交易日开始返回部分窗口值，违反“不足 20 日必须缺失”的预注册语义。原 JSON 保留作为错误证据，不删除、不据此调方向或增加收益相关过滤器；实现只加入上述零值 20 日引用保护，然后按原方向、周期、成本和门槛重新运行。

修复后的唯一有效诊断为 `20260714T093606Z_factor_diagnostic.json`。560 个非重叠 cohort 的平均 Rank IC 为 **+0.0415**，正 IC 比例 **62.1%**，2019–2025 每一年平均 IC 均为正；但最高 3 只相对最低 3 只的平均毛收益差仍为 **−2.73%**。Top‑3 扣费累计收益为 **−34.50%**、最大回撤 **−62.81%**，2019、2021、2022、2023、2025 年为负；单轮净收益 P5 为 **−3.36%**、最差为 **−9.01%**，跌超 5% 的 cohort 占 **1.96%**。`20260714T093627Z` 的稳定性和 Top‑3 可行性审计均无合格因子，因此三日低 MAX 方向按有效实现正式淘汰。最差持仓显示该分数常把“过去 20 日几乎没有正向弹性”误当稳健，选入 20 日动量靠后的持续弱势股；这是描述性失效机制，不授权增加动量、流动性或波动过滤器重测。

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

当一次因子库同时比较很多候选时，开发期第一名还可能只是“多次尝试后恰好最高”的结果。在继续扩充字段前，先对已保存的研究运行一次候选选择多重尝试审计。它只读每个候选在**开发期**逐 cohort 的净收益：所有候选共用同一组 5‑cohort 循环区块自助法重采样，以保留真实的共同市场波动；零收益极值比较仅对实际持仓收益逐候选去均值，空仓 cohort 保持零。它输出胜者在重采样中仍然第一的频率，以及在“整库均无平均交易超额收益”假设下出现当前最高分的全局 p 值。它不读取原测试段，不调整权重、不生成选股名单，也不自动暂停或晋级策略：

```bash
python scripts/a_share_short_horizon_factor_research.py selection-multiplicity-audit \
  --study data/experiments/short_horizon/20260713T114832Z_study.json \
  --hold-days 3 --bootstrap-replicates 1000 --block-cohorts 5 --seed 17
```

该结果是开发期选择偏差的诊断，不是未来盈利概率。胜者频率低说明该名次对开发期具体路径敏感；全局 p 值较高说明在整库搜索后，最高开发分未明显超出零收益下的偶然极值。两者任一都需要通过新的、尚未见过的纸面样本验证，而不是回看 2026 年结果后重选候选。

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

当前注册表中的 18 个既有轮次全部来自旧价格基准，均已失效，所以下述命令此时会拒绝创建信号。只有全量点时价格重建后产生、并携带验收清单哈希的新轮次才能进入观察；不要为旧轮次手工补写 `price_basis`。

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

同日对该旧策略来源的 100 候选开发期扫描完成多重尝试审计（`20260714T004308Z_selection_multiplicity_audit.json`）：候选各有 158–162 个开发 cohort，5‑cohort 循环区块自助法 1,000 次中，原胜者仅有 **19.2%** 的重采样仍为第一；候选逐一中心化后的全局零收益极值 p 值为 **0.6983**。因此这次“开发期第一名”不足以构成强的独立选优证据；审计本身不增加仓位、不换成另一候选，也不使用结果反向挑新胜者。审计还验证出原始记录需使用已修复前的 `legacy_post_first_cohort_high_water` 回撤约定才能逐项复现；此兼容约定仅用于历史审计，新研究仍使用包含初始权益的已修正回撤计算。在决定是否暂停旧观察并以已修正规则重新预登记前，不应把旧胜者视为已获额外确认。

按已修正回撤规则，以相同 V1 候选、同样 Top‑10、广度状态和成本、但严格截断在 2025‑12‑31 的开发期重新登记（`20260714T004740Z_study.json`），胜者改为 `expanded_volatility_middle_q10_roe`（开发期净收益 +18.74%、年化 +9.37%、回撤 −16.69%）。它同样没有历史测试段；其候选选择多重尝试审计（`20260714T004911Z_selection_multiplicity_audit.json`）中胜者频率只有 **7.2%**、全局零收益极值 p 值 **0.7003**，因此不登记为前瞻纸面观察。

为避免在同一段开发样本内继续换权重，V1 整库随后做了 2019–2025 的扩展窗口年度检验（`20260714T005938Z_walk_forward_selection_audit.json`）：每一年只用此前完整持有周期选择下一年的候选，五年汇总样本外净收益 **−28.05%**、最大回撤 **−62.57%**。连同此前 V2 的 −43.23% / −46.80% 与 V3 的 −41.50% / −55.26%，当前技术/质量候选库均作为策略族淘汰证据保留；不得再从这三库挑选单一“胜者”进入观察。

作为独立方向，业绩预告公告事件的 `forecast_profit_yoy_precision`、`forecast_profit_yoy`、`forecast_turnaround` 和 `forecast_freshness` 曾完成五年/200 cohort 稳定性与 Top‑3 可行性审计（`20260714T010132Z_*_audit.json`），当时全部失败。但其输入诊断 `20260713T214654Z` 使用后来证明无效的混合价格口径，且没有 20 日上市门禁；这些数值只能作为旧流程的无效证据，不能继续用于淘汰、反向或组合。修复后的唯一一次原方向重建由后文的公告事件专用协议约束。

与连续技术因子不同的“限价样强势收盘 + 高换手延续”事件也按预先固定的主板 9.5% / 创业板 19.5% 收益门槛、收盘距日高不超过 0.5%、事件内完整 Top‑3、次日开盘至第 3 日收盘规则完成开发期审计（`20260714T012012Z_limit_like_event_audit.json`）。2019–2025 仅有 92 个可执行 cohort，净累计收益 **−86.04%**、最大回撤 **−89.05%**，且 2019、2020、2022、2023、2024 年为负，故延续方向停止。不能因这一失败在同一开发期事后改测“限价样反转”；若未来形成反转假设，必须先写死定义并只在新的未见区间验证。

季度公告后正利润加速漂移也完成了独立事件审计（`20260714T012826Z_quarterly_profit_acceleration_event_audit.json`）：只在公告后下一本地交易日的首个安全收盘、质量合格且同财季利润同比加速为正时按原始加速幅度取完整 Top‑3。2019–2025 的 124 个可执行 cohort 净累计收益 **−13.49%**、最大回撤 **−37.82%**，且 2020、2021、2023 年为负，故该延续方向停止。不可在同一开发期改测负加速、不同 TopK 或反转版本；这会是新的假设，只能在新的未见区间预注册。

### 点时价格重建后的上市资格与 V9 复核

全量日线改为 `close_known_raw_pct_chg_chain_v1` 并通过价格口径、因子就绪和 29/29 滚动窗口语义审计后，首个 54 因子基线 `20260714T125736Z_factor_diagnostic.json` 暴露了一个执行资格问题：`amplitude_low` 的极端 Top‑3 亏损主要来自上市初期连续一字涨停后开板的股票。原始 BaoStock 行情逐日复核证明这些不是坏数据，但一字涨停队列不能按“次日开盘必成交”处理。因此该诊断通过指纹登记为无效证据，不再用于组合或选股；旧 JSON 保留用于追溯。

修复是一条固定、与收益无关的股票池规则：股票从本地 Qlib provider 的首个上市会话起满 **20 个本地交易日**，才可进入质量合格池；上市日计为第 1 日，第 20 日收盘形成的信号可以参与下一交易日开盘。上市年龄使用 provider instrument span 和完整本地交易日历计算，不使用价格、收益或未来退市信息。该资格在**横截面排名之前**应用，所以因子百分位只在同日真正合格的成熟股票中计算；筛选 JSON 也保存 `listing_start_date` 和 `listing_age_sessions`。这条规则能移除上市初期队列机制，但仍不能模拟普通涨停队列、开盘撮合优先级、停牌或冲击成本。

固定替代诊断 `20260714T131044Z_factor_diagnostic.json` 只重跑此前通过关联稳定性审计的 8 个因子，保持 2019–2025、三日非重叠、Top‑3 和万一佣金成本不变。20 日门禁从 2,448,972 个财务合格行中排除 15,172 行，剩余 2,433,800 行。结果仍有 7 个因子通过 Rank IC 跨年度关联门禁，但 `20260714T131124Z_factor_topk_viability_audit.json` 显示 **0/8** 通过完整 Top‑3 门禁：

- `amplitude_low` 的平均 Rank IC 为 +0.0512，极端最差单轮由约 −33% 收敛到 −9.69%，但 Top‑3 最大回撤仍为 −34.55%，2021、2023 年净累计为负。
- `volatility_low_20` 的 Top‑3 最大回撤收敛到 −13.40%，但 2022、2023、2025 年为负，仍不满足每年为正的固定规则。
- 其余因子至少违反年度收益、整体收益、价差或 −20% 回撤中的一项；不能因为 pooled 累计收益为正而跳过年度门禁。

仓库中早已冻结的 12 个 V9 压缩/反转加权组合随后用相同新口径重跑，未添加公式或调权。第一次运行在写完 11 个候选后因宽表复制被系统以 137 终止，没有 study JSON，因此只算基础设施失败，零散候选文件不得引用。代码随后仅把评分输入裁剪为合格行、行情/市场状态和冻结因子，参数不变重跑；有效 study 为 `20260714T132413Z_study.json`，结论是 `no_eligible_candidate`。12/12 均未通过：表现最好的一个组合净累计收益 +16.15%，但最大回撤 −50.76%，只有 4/7 个自然年为正；其余多数累计净收益为负。因此本轮不登记未来观察、不生成当前选股，也不继续在同一日线因子上事后调权。

### 点时价格修复后的公告事件固定重建

业绩预告和大股东变动都有明确公告日，但原诊断 `20260713T214654Z` 与 `20260713T220522Z` 都来自旧价格口径且没有 20 日上市门禁。为只修复基础设施而不重新挑公式，`docs/a_share_announcement_event_rebuild_preregistration.json` 在读取修复后事件收益前固定绑定了业绩预告、大股东公告、原季度质量快照、各自清单和两份旧诊断的 SHA‑256。

专用命令一次运行原来的 4 个业绩预告因子和 5 个大股东公告因子，方向全部保持高值；预告保留 30 个日历日，大股东公告保留 3 个日历日，二者都严格从公告后的下一本地交易日生效。命令不暴露财务来源、因子子集、方向、日期、事件年龄、持有期、TopK 或成本覆盖：

```bash
python scripts/a_share_short_horizon_factor_research.py announcement-event-rebuild-diagnostic
```

协议固定 2019–2025、非重叠三日 cohort、Top‑3、买入 0.012% / 卖出 0.062% 成本、季度质量 550 天年龄、20 日上市门禁和 `close_known_raw_pct_chg_chain_v1`。完成后必须对整份 9 因子诊断运行默认的 `factor-stability-audit` 与 `factor-topk-viability-audit`，不得只审计表现较好的字段。只有同时通过两道门禁的因子，才允许另写全新的未来组合预注册；本次重建始终不能选股、晋级或登记策略，并且只允许完成一次。

固定重建已完成为 `20260714T162126Z_factor_diagnostic.json`，整目录稳定性与 Top‑3 审计分别为 `20260714T162139Z_factor_stability_audit.json` 和 `20260714T162140Z_factor_topk_viability_audit.json`，结论均为 **0/9**。平均 Rank IC 最高的 `forecast_profit_yoy_precision` 也只有 +0.00745；虽然正 IC cohort 占 53.77%、Top‑3 扣费累计收益为 +13.05%，但 2021、2022、2025 年平均 IC 和篮子收益都为负，最大回撤 −29.25%，最差单轮 −10.02%。`major_holder_decrease_free_ratio` 的累计收益看似达到 +53.96%，但正 IC 比例仅 49.71%，2019、2020、2022 年关联非正，2020、2022、2024 年篮子收益非正，最大回撤 −34.18%、最差单轮 −11.99%；这同样不能越过关联与回撤门槛。其余 7 项的 pooled IC、年度一致性、年度收益或回撤失败更多。

因此这 9 个原始“高值延续”方向在有效价格、季度质量和上市门禁下全部停止：不反向、不修改 30/3 日事件年龄、不筛年份、不挑子集、不与日线或交易事件因子组合，也不生成当前选股。专用命令会拒绝第二次消费同一协议；下一项研究必须来自事先冻结、具有新增信息的分钟成交路径或新公告字段。

### 稀疏公司公告的无收益容量门禁

回购计划、股东人数、股权质押和分红预案的旧诊断 `20260713T233314Z`、`20260713T234343Z`、`20260713T235418Z`、`20260714T000612Z` 同样缺少点时价格与 20 日上市门禁，收益只能保留为无效历史。其中回购、股东人数和分红的旧 cohort 数低于 200，不能直接重跑收益；质押虽然旧 cohort 数较多，也必须在修复后的上市资格下统一复核容量。

`docs/a_share_sparse_announcement_capacity_preregistration.json` 在读取任何新收益前固定绑定四类事件、季度质量、各自清单和旧诊断的 SHA‑256。专用命令不加载任何开盘、收盘或未来收益字段，也不允许覆盖日期、事件年龄、TopK、最低样本或因子子集：

```bash
python scripts/a_share_short_horizon_factor_research.py sparse-announcement-capacity-audit
```

容量口径与正式诊断一致：2019–2025 每 3 个本地交易日取一个信号截面，季度质量年龄不超过 550 天、上市满 20 个会话；Top‑3 与 Bottom‑3 的关联诊断要求同一因子至少有 6 个有效名字且至少 2 个不同值。每个因子必须达到 200 个潜在完整 cohort。一个来源只要有一项原始因子达到门槛，后续就必须把该来源全部原始因子一起纳入唯一一次点时价格重建；若一个来源没有任何因子达到门槛，则在 `forward_return_fields_read=false` 状态下停止整个来源，不能改窗口、降低样本或借其他来源补足。

固定容量审计已完成为 `20260714T163309Z_sparse_announcement_capacity_audit.json`，明确记录 `price_fields_loaded=[]` 和 `forward_return_fields_read=false`。回购三项只有 17、23、21 个潜在 cohort；股东人数三项为 194、194、178；分红四项为 123、49、4、110，三个来源全部在读取收益前停止。质押股数、质押占比、事件笔数和新鲜度分别达到 399、399、394、374，四项均超过 200，因此只有 `share_pledges` 获准进入下一阶段。

质押重建协议随后在读取点时价格收益前写入 `docs/a_share_pledge_event_rebuild_preregistration.json`，同时绑定容量审计、季度质量、质押快照、清单和无效旧诊断。专用命令不暴露因子、方向、年龄、日期、质量源、TopK 或成本覆盖，一次运行全部四项原始高值方向：

```bash
python scripts/a_share_short_horizon_factor_research.py pledge-event-rebuild-diagnostic
```

完成后必须对整份四因子诊断运行默认稳定性和 Top‑3 可行性审计。只有同时通过两道门禁的因子才允许另写未来组合预注册；本次重建本身不能选股、晋级或登记策略，也只允许完成一次。

固定重建已完成为 `20260714T163855Z_factor_diagnostic.json`，整目录稳定性与 Top‑3 审计均为 `20260714T163907Z`，结论是 **0/4**。`pledge_event_count` 的平均 Rank IC 最高（+0.01800），但 Top‑3 减 Bottom‑3 的平均净收益差为 −0.0143%，2020、2022 年平均 IC 非正，Top‑3 最大回撤 −61.22%、最差单轮 −12.68%。`pledge_freshness` 的平均 Rank IC 为 +0.01672，却有 5 个年度篮子收益为负且最大回撤 −54.90%；`pledge_share_count` 的平均 Rank IC 为 +0.01559、最大回撤 −53.51%，`pledge_total_share_ratio` 仅 +0.00627、最大回撤 −54.61%。四项都没有同时满足跨年度关联、年度篮子收益和风险门槛。

因此四个原始“高质押值延续”方向全部停止：不反向、不修改 3 日事件年龄、不筛年份或因子、不与其他公告或日线因子组合，也不生成当前选股。容量通过只证明样本足够做一次有效检验，不代表因子有效；本次 0/4 是该来源的正式点时价格淘汰证据。

### 点时价格修复后的交易事件固定重建

龙虎榜、块交易和融资流是当前公共数据中最接近成交行为的三类日度事件，但原诊断 `20260713T214915Z`、`20260713T222021Z`、`20260713T230129Z` 都形成于旧的混合价格口径，且没有 20 个本地交易日的上市门禁；这些收益结果只保留为无效历史，不能用于组合或淘汰。修复后重建协议在读取新口径事件收益前写入 `docs/a_share_transaction_event_rebuild_preregistration.json`，锁定原来的 5 个龙虎榜、4 个块交易和 4 个融资因子，方向全部保持高值，事件有效期分别为 3、3、0 个日历日。

专用命令不提供日期、因子子集、方向、持有期、TopK、成本或事件年龄参数，并通过快照、清单及旧诊断 SHA‑256 保证这只是基础设施修复，不是看结果后的换公式：

```bash
python scripts/a_share_short_horizon_factor_research.py transaction-event-rebuild-diagnostic
```

它固定使用 2019–2025、非重叠三日 cohort、Top‑3、买入 0.012% / 卖出 0.062% 成本、550 天财务年龄、20 日上市门禁和 `close_known_raw_pct_chg_chain_v1`。完成后必须对整份 13 因子诊断运行默认的 `factor-stability-audit` 与 `factor-topk-viability-audit`，不允许只审计看起来较好的字段。任何因子只有同时通过两道门禁，才可另写新的未来组合预注册；本次重建本身始终不能选股、晋级或登记策略。同一协议只允许产生一份完成的点时价格诊断。

固定重建已完成为 `20260714T161042Z_factor_diagnostic.json`，两道整目录审计为 `20260714T161053Z_factor_stability_audit.json` 和 `20260714T161053Z_factor_topk_viability_audit.json`，结论均为 **0/13**。最接近正向关联的块交易溢价率平均 Rank IC 仅 +0.0107，正 IC 比例恰为 50%、Top‑3/Bottom‑3 毛差为负，2020、2021 年方向为负；其 Top‑3 最大回撤达到 −61.10%。龙虎榜净流入/成交额平均 IC 仅 +0.0036，四个年份方向为负，Top‑3 扣费累计收益 −78.03%、最大回撤 −89.06%。融资余额增速虽然 Top‑3 累计数值达到 +313.90%，但总体平均 IC 为 −0.0330、七年中六年方向为负、最大回撤 −58.18%，属于极少数路径主导的误导性累计值，不能越过关联稳定性门禁。其余字段同样存在总体 IC 非正、年度反向或极端篮子回撤。

因此龙虎榜、块交易、融资流这 13 个原始“高值延续”方向在有效价格口径下全部停止：不反向、不修改事件年龄、不筛年份、不与日线压缩因子组合，也不生成当前选股。该结果已进入 `three_day_research_report.md`，专用重建入口会拒绝再次读取同一协议的收益。

此后更有信息增量的方向是分钟成交路径、尾盘量价和有明确发布时间的资金流/事件字段。`a_share_rich_data.py status` 在本检查点显示三个授权源均未就绪、SDK 未安装、快照清单为 0：Tushare 缺 `TUSHARE_TOKEN`，JQData 缺本地用户名/密码，RQData 缺本地用户名/密码。下一步必须由数据授权决定；不要把凭据粘贴到聊天或写进仓库。取得任一合法授权后，先按“受凭据保护的分钟与事件数据”章节做单日验收，未通过时间戳和量纲校验前不得形成分钟因子。

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

只有 `price_basis.json` 与因子就绪度测试都通过后，筛选和历史研究才可使用点时复权价与 `$factor` 还原实际价格；整手规划仍需用交易时券商可见价格复核。研究结果仅用于比较候选假设，不能作为收益承诺或直接实盘信号；涨跌停排队、停牌、冲击成本和完整退市历史仍未被精确模拟。

若正常 `sync` 因东财接口短暂不可用，但确认需要补入一个已收盘的交易日，可使用受审计的腾讯收盘行情恢复脚本。它只使用已有的本地股票池快照、只写入指定日期，并将源站、失败股票与 Qlib 重建结果记录在 `data/metadata/recoveries/`。东财恢复后，仍应执行一次正常 `sync` 覆盖并复核这一天。

```bash
python scripts/recover_a_share_close_from_tencent.py --date 2026-07-13
python scripts/a_share_data_pipeline.py status
```

`sanitize` 只保留给旧数据的非正数/错误 OHLC 清理，不能把旧 qfq 数据修复成合格的点时价格口径。旧数据必须全量重新下载；删除异常行会掩盖复权基准错误。

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

纸面观察任务会先检查 18:30 数据同步所持有的管线锁；若同步仍在进行，最多等待 45 分钟，避免用旧收盘数据漏记当日信号。随后只对注册表中带有已验收 `price_basis` 的记录运行 `monitor`、`shadow-monitor` 或 `prospective-monitor`，旧 qfq 登记会被跳过；无有效登记时只生成 `report`。它不会自动重跑因子搜索、修改策略权重、回填错过的前瞻信号或生成下单计划。日志在 `data/logs/`。需要移除定时任务时：

```bash
python scripts/install_a_share_launchd.py uninstall
```

定时任务不在休眠的电脑上补跑；若错过一次，手动执行 `sync` 即可恢复。若将来换成需要登录的专业数据服务，不要把令牌写进 YAML 或 Git；由系统钥匙串、环境变量或本地 `.env`（已忽略）提供即可。
## 受凭据保护的分钟与事件数据

日线管线继续是当前策略的唯一正式行情底座。三日持有期策略需要的尾盘、日内成交和资金流因子，使用独立且可审计的接入器；它不会覆盖日线数据或直接改动 Qlib 二进制。

| 来源 | 当前接入范围 | 适用阶段 |
| --- | --- | --- |
| RQData | 原始分钟 OHLCV/成交额 | 首选的全市场分钟研究数据 |
| JQData | 原始分钟 OHLCV/成交额 | RQData 的可替代分钟源 |
| Tushare | 原始分钟线、`moneyflow`、涨跌停、龙虎榜 | 资金流和盘后事件补充 |

供应商账户、分钟权限和历史深度必须由实际授权确认。不要购买、猜测权限或把凭据交给仓库。

对平均持有 3 个交易日的当前研究，接入优先级固定为：先选**已有合法授权**的 RQData 或 JQData 做 1 分钟 OHLCV/成交额单日验收；再用 Tushare 补充资金流、涨跌停和龙虎榜等有明确盘后时间的事件。分钟数据首先只构造尾盘收益、尾盘成交占比、日内 VWAP 路径、开盘跳空消化和日内实现波动等少量预声明字段。Level‑2 的十档盘口、逐笔委托/成交和队列字段暂不作为前置依赖：只有分钟/事件候选先通过时间对齐、跨年度与 Top‑3 门禁，且失败原因明确指向队列或成交优先级时，才评估合规的 Level‑2 历史授权。交易所 Level‑2 是增值行情，不应把客户端可见盘口抓取当作可回测历史数据库。

官方能力参考：[JQData 数据说明](https://www.joinquant.com/help/api/doc?id=10674&name=JQDatadoc)、[Tushare 股票数据目录](https://tushare.pro/document/2?doc_id=17)、[上证所 Level‑2 产品说明](https://www.sseinfo.com/services/assortment/level2/)。实际采购前仍须核对账户页显示的历史深度、频率、调用配额和再分发条款。

### 本机凭据和 SDK

先看安全状态；输出只显示“已配置/缺失”，不会显示令牌或密码：

```bash
python scripts/a_share_rich_data.py status
```

在已取得对应授权后，安装可选 SDK，并只在本机的 shell、钥匙串或被 Git 忽略的 `.env` 中提供凭据：

```bash
python -m pip install -r scripts/data_collector/a_share_rich/requirements.txt

export TUSHARE_TOKEN='...'
export JQDATA_USERNAME='...'
export JQDATA_PASSWORD='...'
export RQDATA_USERNAME='...'
export RQDATA_PASSWORD='...'
```

令牌和密码绝不能出现在 Git、命令历史、笔记本输出、研究清单或聊天中。未安装 SDK 或缺少变量时，程序会在发出网络请求前失败；不要用抓取公开网页的方式替代已授权数据源。

### 必经验收流程

只对一个已收盘交易日和四只代表性股票运行验收。`acceptance` 会保存原始快照，并自动检查字段、非负成交量/成交额、常规交易时段、同日 OHLC/收盘比值，以及与本地日线的成交额和成交量比值：

```bash
python scripts/a_share_rich_data.py acceptance --provider rqdata --date 2026-07-13
python scripts/a_share_rich_data.py acceptance --provider jqdata --date 2026-07-13
python scripts/a_share_rich_data.py acceptance --provider tushare --date 2026-07-13
python scripts/a_share_rich_data.py sync-tushare-events --start 2026-07-13 --end 2026-07-13
```

分钟线保存原始未复权价格；日线同时保留 raw OHLCV 与 `$factor`，所以验收应先用 `adjusted / factor` 还原日线原始价，再比较同日 OHLC、成交额和成交量。供应商的成交量单位可能是“股”或“手”，程序会记录比值；在确认并显式标准化之前，不得把不同供应商的量能字段混用。

分钟快照清单的状态必须是 `automatic_checks_passed_pending_time_alignment`，才可进入下一步人工检查：

1. 检查完整未停牌股票通常有约 240 根 1 分钟 bar；停牌/临停缺口必须保留，不能补零。
2. 确认时间戳是 bar 起点还是终点，并固定为一种约定后再构造尾盘因子。
3. 确认 Tushare 的盘后事件只从下一交易日开始可见；不能用当日收盘后才发布的字段解释当日买入。
4. 用点时上市/退市股票池和当时可得的复权信息重新进行历史研究，避免现有股票池造成幸存者偏差。

通过上述检查前，分钟和事件数据只属于“候选原始数据”，不得进入因子聚合、模型训练、纸面观察或选股评分。

完成首尾分钟人工复核后，不修改验收清单，而是追加一份独立确认记录。`--bar-label` 必须填供应商实际采用的 `start` 或 `end`，`--volume-unit` 必须与自动日线对账推断的 `shares` 或 `lots` 一致：

```bash
python scripts/a_share_rich_data.py confirm-minute-alignment \
  --manifest data/metadata/rich_data/runs/<acceptance-run>.json \
  --bar-label end --volume-unit shares --reviewed-boundaries
```

该命令要求验收快照至少有一个时间标签完全匹配的 240-bar 交易日，将确认写入 `data/metadata/rich_data/alignments/`，并绑定原验收清单的 SHA-256。它只确认同一供应商、同一频率的时间戳和成交量语义，不代表因子有效，也不授权选股。

第一版分钟因子已经在 [`a_share_minute_factor_preregistration.json`](a_share_minute_factor_preregistration.json) 中先于任何本地分钟收益冻结。五项原始定义及诊断方向固定为：

| 字段 | 固定含义 | 诊断方向 |
| --- | --- | --- |
| `late_return_30m` | 14:30 至 15:00 收益 | 高值 |
| `late_amount_share_30m` | 最后 30 分钟成交额占全天比例 | 高值 |
| `late_vwap_to_day_vwap_30m` | 尾盘 VWAP 相对全天 VWAP | 高值 |
| `opening_gap_digestion` | 跳空后向昨收可比价格回归的程度 | 高值 |
| `intraday_realized_volatility` | 完整交易时段分钟对数收益实现波动 | 低值 |

其中昨收可比价格使用 `昨日 raw_close × 昨日 factor ÷ 今日 factor`，避免除权日产生假跳空。特征生成器只接受原始未复权 1 分钟快照、已通过且哈希链完整的口径确认、单一供应商文件和日线 `close_known_raw_pct_chg_chain_v1`。每个股票日必须恰好匹配 240 个 bar-end 时间点；少一根、多一根、重复一根或关键值不可计算时，该日整体不合格，程序不会填补。

### 批量下载、存储与追溯

验收通过后，才对明确的股票列表下载分钟数据：

```bash
python scripts/a_share_rich_data.py sync-minutes \
  --provider rqdata --symbols 600519,000001,300750,688981 \
  --start 2026-07-10 --end 2026-07-13 --frequency 1m
```

批量快照的供应商和频率必须与口径确认一致，随后才能生成研究特征：

```bash
python scripts/a_share_rich_data.py build-minute-features \
  --manifest data/metadata/rich_data/runs/<bulk-run>.json \
  --alignment data/metadata/rich_data/alignments/<alignment-run>.json
```

输出 Parquet 位于 `data/derived/a_share/rich/minute_features/v1/`，运行清单位于 `data/metadata/rich_data/feature_runs/`。清单同时保存原始快照、口径确认和预注册文件的哈希，并明确记录 `forward_return_fields_read=false`、`selection_or_promotion_allowed=false`。此步骤仅生成当日收盘已知特征；后续关联诊断仍须使用固定 2019–2025 开发期、三日非重叠 cohort、Top‑3、万一佣金和卖出印花税门槛。任何方向失败，都不能在同一历史上反向或换窗口补测。

不能用四只验收股票或自选小名单直接计算 Rank IC。预注册的数据代表性门禁要求：在特征首尾日期之间，以当日质量合格且上市满 20 个本地交易日的可持有股票为分母，分钟源行覆盖率中位数至少 95%、P5 至少 90%，并且每个可诊断截面至少有 50 个完整合格名称。运行统一分钟诊断：

```bash
python scripts/a_share_short_horizon_factor_research.py minute-factor-diagnostic \
  --feature-run data/metadata/rich_data/feature_runs/<feature-run>.json
```

该命令不提供日期、方向、持有期、TopK、成本或财务新鲜度参数；全部从预注册文件读取（财务最大年龄固定 550 天），并一次运行全部五项，防止看过一部分结果后选择性修改。它会重新核验验收快照、口径确认、批量快照、特征文件和预注册文件的完整哈希链，使用轻量日线执行报价附加公告点时质量门禁，并在质量/上市门禁后才做分钟因子横截面方向排名。若覆盖不足，命令只写入 `*_minute_factor_coverage_audit.json`，记录 `forward_return_fields_read=false` 后停止；该拒绝记录会出现在三日研究报告中。

覆盖通过时，输出沿用标准 `*_factor_diagnostic.json`，随后必须运行既有两道固定审计：

```bash
python scripts/a_share_short_horizon_factor_research.py factor-stability-audit \
  --diagnostic data/experiments/short_horizon/<run>_factor_diagnostic.json
python scripts/a_share_short_horizon_factor_research.py factor-topk-viability-audit \
  --diagnostic data/experiments/short_horizon/<run>_factor_diagnostic.json
```

任一因子没有有效横截面时也会作为 `no_valid_cross_sectional_cohorts` 留在诊断中，而不是被静默删除。诊断本身始终 `selection_or_promotion_allowed=false`，不会生成选股或仓位。

组合规则也已在本机仍为 0 个分钟快照时冻结：取**同时**通过完整默认稳定性与 Top‑3 审计的因子交集；少于两个则停止，至少两个则把交集中全部方向分位数做唯一一次等权平均，任一分量缺失时该股票日不合格。不枚举子集，不搜索权重，也不根据开发期表现挑聚合函数。使用两个完整审计和一份包含 2026‑01‑01 以后数据的特征运行执行：

```bash
python scripts/a_share_short_horizon_factor_research.py minute-combination-holdout \
  --diagnostic data/experiments/short_horizon/<run>_factor_diagnostic.json \
  --stability-audit data/experiments/short_horizon/<run>_factor_stability_audit.json \
  --topk-audit data/experiments/short_horizon/<run>_factor_topk_viability_audit.json \
  --feature-run data/metadata/rich_data/feature_runs/<holdout-feature-run>.json
```

命令会拒绝只审计部分因子、放宽 5 年/200 cohort 门槛、输入诊断哈希不一致或供应商/预注册不一致的记录。2026 条件留出仍须通过相同覆盖门禁，并在读取未来价格前证明至少有 20 个潜在非重叠 Top‑3 cohort；覆盖或容量不足只写拒绝记录，允许以后用延长但仍未读取收益的特征快照重试。一旦形成过未来收益，同一诊断、稳定性审计与 Top‑3 审计的哈希组合即被视为已消费，不能换新快照重跑。

条件留出复用固定门槛：至少 20 个实际 cohort、扣费累计收益为正、最大回撤不差于 −20%。但此前其他日线研究已经观察过 2026 市场收益，因此这只是“分钟分数未见”的条件留出，不是纯净市场收益留出；即使通过也保持 `selection_or_promotion_allowed=false`，只能为这个完全相同的组合另行登记新日期开始的前瞻纸面观察，不能直接形成选股、仓位或实盘策略。所有通过、失败、无双门禁因子和未消费留出的覆盖/容量记录都会进入三日研究报告。

超过 100 个“股票 × 工作日”的付费请求必须显式加入 `--allow-large`，防止误触发多年全市场下载。每次下载按不可变快照写到 `data/raw/a_share/rich/`，并在 `data/metadata/rich_data/runs/` 写入供应商、原始价格口径、请求区间、SHA-256、日内汇总和验收结果。这些文件均由 `data/` 的 Git 忽略规则保护，不应提交或删除来掩盖失败。
