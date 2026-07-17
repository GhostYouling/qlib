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

完整快照已于 2026-07-15 完成：84 个连续自然月、242 页和 99,431 条源记录全部逐分片核对；保留 83,441 条有效直接市场买卖行，其中买入 21,218、卖出 62,223，聚合为 64,609 个股票/合成可用日事件。排除非目标或关键字段缺失 1,773 行、非白名单原因 14,206 行、方向与股数符号不一致或为零 11 行；事件覆盖 2019-01-07 至 2026-01-07，重复键、缺失、比例越界、事件数异常和第 3 会话映射错误均为 0，共 16 个买入占比值。Parquet SHA-256 为 `077dce86290c7a19dba65b76b3bae5cebe3c39ca36cbd5805dcaacf618c0afbf`；清单明确记录 `price_fields_loaded=[]` 与 `forward_return_fields_read=false`。

同步完成仍不得读取收益。一次性无收益容量协议已绑定数据契约、事件快照/清单和季度质量快照/清单，冻结为 `docs/a_share_insider_open_market_capacity_preregistration.json`。它固定 2019–2025、非重叠三日、Top‑3、每截面至少 6 名且 2 个值、550 日季度质量、上市满 20 会话和至少 200 个 cohort：

```bash
python scripts/a_share_short_horizon_factor_research.py insider-open-market-capacity-audit
```

容量命令只读取事件、日历、上市活动区间和季度质量，不加载价格或远期收益，并只能成功写出一次。容量不足即停止；容量通过也仅允许在读取价格前另行冻结一次精确的高买入占比收益诊断，不代表因子有效或可用于选股。

唯一一次容量审计已完成为 `20260714T194453Z_insider_open_market_capacity_audit.json`（SHA-256 `fa4792b836fe4769dc0cb10ccbe852bea2b8e487bfad55c0aff516bd3c399081`）。三日事件展开后有 37,876 行候选值，季度质量与上市门槛后保留 9,049 行、530 个有值事件日，最终形成 **380/200** 个潜在完整 cohort；2019–2025 分别为 41、59、69、67、52、45、47。审计明确记录 `price_fields_loaded=[]`、`forward_return_fields_read=false` 和 `selection_or_promotion_allowed=false`。这只解锁一次预注册收益诊断，不是有效性或可交易性证据。

唯一一次收益诊断已在读取行情前冻结为 `docs/a_share_insider_open_market_diagnostic_preregistration.json`。它只允许 `insider_open_market_buy_share` 高值方向，固定 2019–2025、事件年龄 3 天、Top‑3、开/平仓成本 0.012%/0.062%、550 日季度质量与上市满 20 会话，并绑定容量审计、事件快照和季度质量快照指纹。专用命令不暴露日期、方向、因子、年龄、成本、质量或 Top‑3 参数，只能运行一次，并必须随后执行完整默认稳定性与 Top‑3 可行性审计：

```bash
python scripts/a_share_short_horizon_factor_research.py insider-open-market-diagnostic
```

唯一一次正式诊断已完成为 `20260714T195205Z_factor_diagnostic.json`（SHA-256 `9d5410b7d2ce5b84fba631009de619daeec38b1c5ef8c53a30e8d0e34b48ec46`），完整默认稳定性与 Top‑3 可行性审计均为 `20260714T195221Z`，通过数均为 **0/1**。380 个 cohort 的平均/中位 Rank IC 为 +0.03243/+0.04978，正 IC 比例 54.74%，TopK-minus-BottomK 毛收益差 +0.0723%；但 2019、2020、2025 年平均 IC 分别为 −0.01224、−0.04652、−0.01538，未通过逐年同向门禁。Top‑3 扣费累计收益仅 +3.76%、年化约 0.82%，2020、2022 年分别亏损 8.73%、34.72%，最大回撤 **−43.43%**，3 日净收益的 1%/5% 分位为 −10.04%/−4.94%，最差一期 −14.60%。稳定性审计 SHA-256 为 `45c7b500a1578ae03cb12f57e1ffc5d31f5b451d2d8313229a3d492db7e3478a`，Top‑3 审计 SHA-256 为 `488fc8ba38b66059213b96b8ed32fcd05d66de85f348a1763e889b2af946f902`。因此停止 `insider_open_market_buy_share`，不进入聚合、当前评分或选股；不得在同一历史上改为卖出占比、缩短合成披露延迟、改变事件年龄、扩展原因、加入身份/股数/价格权重、挑年份、增加事后过滤器，或与其他已淘汰因子组合。

下一项独立的细颗粒度来源是**全市场融券卖出与偿还活动**，完整快照前已冻结为 `docs/a_share_securities_lending_data_contract.json`。它与已经淘汰的融资 Top‑100 因子不同：不读取融资净买入、融资买入、融资余额、余额增速、市值或任何价格/收益字段，只请求交易日、股票代码、融券余量、融券卖出量和融券偿还量。唯一因子为 `securities_lending_net_cover_ratio = (偿还量 − 卖出量) / (偿还量 + 卖出量)`，高值固定为更好；卖出与偿还同时为零时保持缺失，原始数量缺失或为负的行排除并计数，绝不裁剪、取绝对值或填充。

交易所规则要求在下一交易日开市前公布前一交易日的单券融资融券信息，因此 `DATE` 只作为当日收盘后形成、下一本地交易日开盘进入的信号，事件年龄固定为 0；公开日表没有可机器核验的历史发布时间，异常延迟导致次日开盘前尚未发布是残余风险。2024-01-29 限售股出借暂停、2024-03-18 转融券效率调整、2024-07-11 转融券暂停和 2024-07-22 保证金比例上调只作为制度背景记录，不能用于分段、过滤、重加权、换方向或事后调参。

冻结前只做了无价格字段的三个完整月样本审计。2019‑06、2024‑06、2025‑06 分别逐日核对 19、19、20 个本地交易日，38、152、180 页和 18,943、73,301、82,190 条源记录均完全对账；有效非负目标行 17,881、62,866、68,220 条，正活动行 15,227、47,668、38,789 条。三个样本每个交易日都满足至少 6 只股票和 2 个值，单日最少活动股票分别为 746、2,382、1,836，只数变化后的 2025 样本仍有容量。下一步只能先流式同步 2019–2025 全量日分片并做无收益容量门禁；容量不足即停止，不能恢复融资字段、加入价格/市值归一化、按监管日期挑区间或改用融券卖出方向补救。

```bash
python scripts/a_share_short_horizon_factor_research.py sync-securities-lending-events
```

同步以本地 Qlib 日历固定 2019–2025 的每个交易日，4 个线程各自复用一个 HTTP 会话；每个日分片最多 20 页，接口广告条数必须与实际收到条数完全一致。归一化后的日数据逐行组写入同目录临时 Parquet，不在内存中拼接全历史；只有所有交易日、年份、字段、重复键、缺失值、非负数量和 `[-1, 1]` 比例检查全部通过后，才替换正式快照并写 manifest。任一分页、日期或质量检查失败时删除临时文件，保留原正式文件不变。同步不读取价格、开收盘或远期收益；完成后也只能先冻结并执行一次无收益容量审计。

首次完整同步与随后独立的全日历存在性扫描均发现源覆盖缺口，结果冻结为 `docs/a_share_securities_lending_source_coverage_audit.json`（SHA‑256 `b81dcd3d1e5e24198343455ccec4928061ec8d7cafd5283460b65970a1eec8fc`）。1,699 个本地交易日中 1,695 个有正页数和正广告条数，但 2019‑12‑31、2020‑06‑30、2020‑12‑31、2021‑06‑30 均稳定返回 `9201 / 返回数据为空`；相邻日期和跨日期区间查询确认不是本地假日误判。同步在首个缺口前已逐页核验 243 个交易日，随后按契约中止并删除临时 Parquet，正式快照和 manifest 均未生成。

因此 `securities_lending_net_cover_ratio` 在读取任何价格或收益前淘汰，不执行容量或收益诊断，也不进入聚合、当前评分或选股。不得跳过四个日期、前后填充、把缺失当零、缩短开发期、混入另一提供商、恢复融资/价格/市值字段，或在不完整快照上继续研究；`sync-securities-lending-events` 只保留为可复现失败的管线入口，不应反复运行来寻找偶然通过。

随后发现交易所官网本身可以构成一条**新的、纯官方来源链**，而不是给上述东财快照补洞。新合同在读取任何官方样本行前冻结为 `docs/a_share_official_securities_lending_data_contract.json`（SHA‑256 `3a694f2a18e170623bd33ad405b55edd5fdf6c3806b08d6e0be83c8189c2306e`），并由 `docs/a_share_three_day_research_frontier_extension.json`（SHA‑256 `94a5ac622cb35724933ed451ab7e1beb7f37653f2c4a043961bb73798639d66e`）加入研究前沿。两市共同公开的最小字段固定为逐股融券余量与融券卖出量；只有同一股票在当前和上一**本地交易日**都有官方行时，才按 `偿还量 = 上日余量 + 当日卖出量 - 当日余量` 推导，再使用原先冻结的 `(偿还量 - 卖出量) / (偿还量 + 卖出量)` 高值方向。缺行不当作零，负推导值排除并计数，不使用价格、市值、融资字段或收益。

六日期、两交易所的预注册无收益接入门结果冻结为 `docs/a_share_official_securities_lending_source_acceptance_audit.json`（SHA‑256 `e118cb1330722b7d40f5e7de683f81a94d405d605907a1728dd930a634f56ec4`）。上交所 2018‑12‑28、2019‑12‑31、2020‑06‑30、2020‑12‑31、2021‑06‑30、2025‑12‑31 分别返回 556、919、965、1,090、1,194、1,957 行，广告数与接收数完全一致，必要字段逐行齐全；这也证明旧源缺失的四天是聚合提供商缺口，而非上交所缺少披露。深交所官网页面与 `ShowReport` 官方接口在当前运行环境对 2019/2025 样本均于连接层返回空响应，页面在命令行和应用内浏览器也同样不可达。该结论只说明**当前环境无法接入**，不声称深交所全球历史档案不存在。

因为合同要求两市同时通过，官方路线在启动全量同步、容量审计或收益诊断前停止。不得只保留沪市、用东财或其他提供商补深市、把连接失败当零、启动部分全量，或改变公式/方向/窗口/年份。只有网络环境发生可验证变化，或先独立找到深交所官方静态逐日档案时，才能在新的、仍未读取收益的合同下重新考虑接入。

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

### 方向性收益序列依赖单因子

继续设计日线机制前，先完成了不读取未来收益的同义性审计 `docs/a_share_directional_serial_dependence_uniqueness_audit.json`（SHA‑256 `1c41f2419713bcabda0b555d710dc5dac7718b364eb4244b596883c0e115c1d0`）。审计使用 2025 年 4,610 只历史可持有股票、243 个会话和 1,108,238 行 close-known 因子值；绝对日横截面 Spearman 相关中位数达到 0.80 即视为近同义。由此在收益访问前淘汰两个备选：低 `20 日绝对收益和/累计换手` 与 `liquidity_5` 的计分方向相关中位数为 **0.803605**；高 `20 日最差单日收益` 与 `volatility_low_20` 为 **0.805**。二者不得再做收益诊断或换公式救援。

唯一通过独立性门禁的定义冻结在 `docs/a_share_directional_serial_dependence_preregistration.json`（SHA‑256 `aa7a356ce196f2cc72d7a7d1c4085f0063467c7d34e41f2679652a910ad96696`）：

```text
directional_serial_dependence_20 =
  Sign(close / Ref(close, 1) - 1) *
  (Corr(close / Ref(close, 1) - 1,
        Ref(close / Ref(close, 1) - 1, 1), 20)
   + 0 * Ref(close, 21))
```

高值同时覆盖两种预注册情形：当日上涨且收益序列正相关，代表上涨延续；当日下跌且收益序列负相关，代表下跌后的均值回归。它不看累计涨幅、波动大小或换手水平；对 35 个既有日线技术字段的最大绝对相关中位数只有 **0.139096**（`momentum_1`），有限值覆盖率为 99.8294%，每日唯一值中位数为 4,409。低相关仅证明不是明显重写，不代表有效。

新表达式要求 20 对相邻收益和 21 个此前收盘。`20260714T204438Z_rolling_window_semantics_audit.json`（SHA‑256 `815911828c87f0288f45915feda26c8357261986efe982ee7160815981949f50`）在不读未来收益的情况下确认 31/31 个滚动字段通过：该因子前 21 个本地会话提前非空为 0，第 22 个会话才首次有效。收益前代码、公式和门槛随后以提交 `491d2116` 推送。专用命令不允许覆盖日期、方向、窗口、成本、质量源、持有期、TopK 或因子子集：

```bash
python scripts/a_share_short_horizon_factor_research.py rolling-window-semantics-audit
python scripts/a_share_short_horizon_factor_research.py directional-serial-dependence-diagnostic
python scripts/a_share_short_horizon_factor_research.py factor-stability-audit \
  --diagnostic data/experiments/short_horizon/<本轮_factor_diagnostic.json>
python scripts/a_share_short_horizon_factor_research.py factor-topk-viability-audit \
  --diagnostic data/experiments/short_horizon/<本轮_factor_diagnostic.json>
```

唯一正式诊断为 `20260714T205038Z_factor_diagnostic.json`（SHA‑256 `d726965cb83fe445c0888655d6a36f7a7e41a26e2b54a33d0e88f59b3d465285`）。560 个非重叠 cohort 的平均/中位 Rank IC 为 **+0.00034/−0.00269**，正 IC 比例 **48.21%**，Top‑3 相对 Bottom‑3 的平均毛差 **−0.249%**；2019、2020 年平均 IC 为负，其余年份虽略正但接近零。Top‑3 扣费累计收益 **−96.31%**、最大回撤 **−98.08%**、胜率 46.79%，仅 2019 年年度篮子收益为正。`20260714T205053Z_factor_stability_audit.json` 与 `20260714T205054Z_factor_topk_viability_audit.json`（SHA‑256 `90ad9db60fa240d4a8ecf892b01abc455f75949ac7c6415bc0ab4e32170c4cd4` / `e6ddab496128006d00e497ca3da3b4a1538bcb0e18aa9649a0933d06e5999fb8`）均为 **0/1**。

因此该高值方向正式淘汰，不进入聚合、当前评分或选股。不得在相同历史上反向、改窗口、把当日收益符号换成幅度、增加动量/低波动/换手/质量过滤，或只选表现较好的年份。日线摘要中暂不继续枚举相近路径公式。之后实际取得的 Tushare 日级大单分类已按独立合同完成全量、容量和一次收益诊断，也通过 0/1 双门禁而停止；JQData 是同机制供应商替代，不再作为下一独立因子。

### 当前三日研究前沿审计

在继续增加数据机制前，先用 `docs/a_share_three_day_research_frontier_contract.json`（SHA‑256 `36ac39c68fedebf2fdf999475e10452278bbeff4f42b1c41963539867539eeaf`）冻结当前所有权威、正确价格口径分支。合同列出 11 组诊断、各自完整的稳定性/TopK 审计和精确因子全集，防止遗漏失败分支、误用旧价格口径，或把只通过关联门的因子重新拼成组合。运行：

```bash
python scripts/a_share_short_horizon_factor_research.py research-frontier-audit
```

命令只读取已有诊断与两道审计 JSON，不重新加载原始开收盘或未来收益；它会逐项验证诊断哈希链、`close_known_raw_pct_chg_chain_v1`、2019–2025 开发期、20 会话上市门、完整因子全集、无 `--factor` 子集的默认门禁和失效登记。任一证据缺失或参数漂移都会失败。

正式结果 `docs/a_share_three_day_research_frontier_audit.json`（SHA‑256 `0ab41e940afff20cdd5ce46849820ffd56a3072aa859c30d4caa6dd71c10d846`）核对了基础前沿 **43** 个因子：稳定性门通过 **7** 个，TopK 可执行性门通过 **0** 个，双门禁交集为 **0**。因此这些历史证据没有可聚合因子；这 7 个关联通过项也不能用于评分、选股或仓位。其后新增的 Tushare 分类资金流是第 44 个独立历史机制实例，也通过 0/1 双门禁而淘汰；JQData 只是同机制供应商替代，不增加因子数。`docs/a_share_three_day_research_frontier_extension.json` 曾把纯交易所融券源列为新的第一优先路径，但其两市接入门已在读取收益前失败并停止。当前仍未读取收益的独立路径只剩未来可验证恢复的 BaoStock 5 分钟原子历史，或另行取得合法授权、先冻结合同的全市场分钟机制；Eastmoney/Sina 公开五分钟网页路线已通过无收益可用性审计排除为历史源。Level‑2 仍不提前采购或接入。

### 尾部样本成交真实性审计

现有日线诊断以信号后下一本地会话开盘买入、第三个本地会话收盘退出，但原实现只要求开盘/收盘价格为正，没有检查停牌日的零成交量，也不能从日线判断单价涨跌停队列优先级。为避免根据已见尾部样本临时挑规则，先冻结 `docs/a_share_three_day_execution_tail_realism_preregistration.json`（SHA‑256 `1bccc93a5018738f437fcee3456ad4ceda3bb07b9ed5bf64f80cdd5feef2b144`），再运行：

```bash
python scripts/a_share_short_horizon_factor_research.py execution-tail-realism-audit
```

命令覆盖研究前沿绑定的全部 11 条分支和 43 个因子，但只检查每个因子已经保存的最差 5 个 Top‑3 cohort；它从历史诊断只提取分支、运行号、因子、股票和信号/入场/退出日期，再读取这些日期及计划退出前一本地会话的 `$open/$high/$low/$close/$volume`。历史 JSON 虽含已有收益值，审计不使用这些值、不计算新的远期收益，也不落盘原始价格。零/缺成交量配合有效 OHLC 记为计划日明确不可成交；OHLC 单价且相对参考收盘绝对移动至少 4.5% 只记为队列不确定，不能据此声称绝对无成交。

冻结结果为 `docs/a_share_three_day_execution_tail_realism_audit.json`（SHA‑256 `9eb7ef62b099aece3b122d3fdabc44050bf0146dacc137b1575645277cb8d8f3`）：215 个尾部 cohort、645 条因子—股票记录、495 只股票。入场零/缺成交量 **7** 条，其中 **4** 条的计划退出日也为零/缺成交量；单价涨停样入场 **3** 条，单价跌停样退出 **3** 条；两类标记无重叠，共 **13** 条，另有 **632** 条在日线层面未标记。明确不可成交全部位于日线 OHLCV 摘要分支，队列不确定各有 3 条位于日线摘要与交易事件分支。

这些比例只描述刻意富集的最差尾部样本，不能表述为全历史发生率，也不改变任何既有因子收益、门禁或排名。它证明当前回测基础设施可能把正价格、零成交量的停牌日当作成交，但本轮不据此选择性重跑失败因子。任何历史修正都必须先另行冻结一份覆盖全部 43 因子、11 条分支的统一成交协议。未来新因子协议应在收益形成前显式验证入场/退出有效报价与正成交量；单价板的保守成交策略也必须预先定义。当前仍无双门禁因子，因此 Level‑2 继续延期，不能因为这 6 条队列不确定记录就提前采购。

### 未来新因子的统一成交账本

尾部审计以后、任何新因子的成交感知收益被观察以前，统一协议已冻结为 `docs/a_share_three_day_prospective_execution_policy.json`（SHA‑256 `72c3c3871e153372ed9e7691c9d89ba1aeb2f6d02cc839761fefa5fee085e1bc`）。它只适用于今后新运行的日线、事件、分钟线或分类资金流诊断；既有 43 因子不得选择性重跑，也不得为某一分支豁免或在看见结果后改规则。

每个信号仍在收盘后固定 Top‑3，下一本地会话开盘尝试买入，第三个本地会话收盘计划卖出。信号日先要求质量、因子、OHLC 和成交量有效；入场日若报价无效、成交量非正或为相对信号收盘至少上涨 4.5% 的单价板，该槽位保持现金，不能替换成第 4 名，也不能把预算加给其余两只。计划退出日若报价无效、成交量非正或为相对前收至少下跌 4.5% 的单价板，持仓和资金继续留在账本，每个后续本地收盘重试，最多延迟 20 个会话；到上限仍无法成交时，该因子的成交门禁直接失败。

后续 cohort 只能使用下一开盘前真实可用现金。账本每天以现金加全部未平仓持仓的最近有效收盘计值，完整记录入场阻断、准时/延期退出、延迟分布和终局未解决持仓，但不把逐只原始价格写进研究 JSON。研究收益使用归一化本金和小数股，因此只比较机制，不替代 20 万元、100 股整手的执行计划；实盘/模拟盘仍按“小资金实盘/模拟盘基础执行规范”单独测算。

新因子只有同时通过既有关联稳定性门和新的成交门才可进入后续登记：至少 200 个完整信号、扣费累计收益为正、最大回撤不差于 −20%、每个有信号年份收益为正、终局未解决持仓为 0。旧的固定三日 Top‑3 数值不再单独足够。实现审计 `docs/a_share_three_day_prospective_execution_policy_implementation_audit.json`（SHA‑256 `c09aa2f1862277b02f18443815a777a6ee1728cc0628f2aeeec1d8f6868ea97c`）记录了 209 项全量测试通过，包括空仓不替换、延期退出占资、20 日仍卖不出即失败，以及门禁必须使用成交账本而非矛盾的朴素收益；测试期间没有读取任何新因子收益。

在此基础上，`docs/a_share_three_day_pilot_execution_policy.json`（SHA‑256 `72235cd29fc14d43538238150bb2823dae1dd05b027b2c86a9872de89cc0d3f9`）又在任何整手敏感因子收益出现前冻结了未来诊断的 20 万元实盘可实现性门。它不替代上述满仓归一化研究门，而是附加验证：按单股 5%、入场总仓位 15%、100 股整手、万 1 双向佣金、0.002% 双向过户费和卖出 0.05% 印花税计算；实际股价必须用点时复权价除以同日 `$factor` 还原，不能拿复权价直接算股数。正式门禁在买入和卖出两侧各施加 10bp 不利滑点，同时记录 0/5/10/20bp 四档敏感性。买不起一手、现金不足或延期持仓占满仓位时，该槽位留现金，不替补、不借钱、不挪用其他槽位预算。

公司行为期间，买入整手数量先除以入场恢复因子转换为经济单位，持仓按点时复权收盘计值，退出时再按退出恢复因子出售整个余额，避免把除权错误记成亏损，也不遗留公司行为形成的零股。附加门要求至少 200 个完整信号、10bp 场景累计和逐信号年收益为正、整手可负担机会率至少 90%、没有终局未解决持仓或入场仓位违规、每笔已成交名义金额不超过当日成交额 1%，且成交额不可缺失。日成交额只用于成交后的容量审计，不能改变信号排名或证明开/收盘一定成交；Level‑2 队列、冲击成本和精确滑点仍未被宣称已建模。

实现审计 `docs/a_share_three_day_pilot_execution_policy_implementation_audit.json`（SHA‑256 `29cd7b7e3a65e20e2971cd57bd52e81644d354abeef9a26062052dbdd8fcc70b`）记录 213 项全量测试通过；其中代码级守卫证明旧前沿因子会在形成远期收益以前停止。本轮没有读取新因子收益、重算旧因子、评估组合或生成订单。

上交所 2026 年现行交易规则和深交所规则解读均要求普通 A 股竞价买入为 100 股或整数倍，并允许卖出时一次性处理不足 100 股余额。[上交所交易规则（2026 年修订）](https://www.sse.com.cn/lawandrules/sselawsrules2025/stocks/exchange/c/c_20260424_10816482.shtml) [深交所规则解读](https://www.szse.cn/www/investor/institute/rules/t20230706_601604.html) 印花税法规定只向出让方征收，2023 年第 39 号公告自 2023‑08‑28 起减半；中国结算当前公开标准为成交额 0.02‰ 双向过户费。[印花税法](https://fgk.chinatax.gov.cn/zcfgk/c100009/c5193058/content.html) [减半征收公告](https://fgk.chinatax.gov.cn/zcfgk/c102416/c5211343/content.html) [中国结算收费标准](https://www.chinaclear.cn/zdjs/editor_file/20220627143504384.pdf)

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

此后更有信息增量的方向是分钟成交路径、尾盘量价和有明确发布时间的资金流/事件字段。在这个历史检查点，`a_share_rich_data.py status` 曾显示三个授权源均未就绪、SDK 未安装、快照清单为 0；这只是当时状态，不是当前操作指引。2026‑07‑16 随后取得的 Tushare 授权已完成日级分类资金流的单日验收、全历史同步、无收益容量门和唯一一次正式诊断，最终因双门禁失败而停止。当前若已有合法分钟授权，仍须先按“受凭据保护的分钟与事件数据”章节冻结合同并做小样本验收；不要把凭据粘贴到聊天或写进仓库，未通过时间戳和量纲校验前不得形成分钟因子。

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

未来新因子的历史诊断还会自动运行上述 20 万元整手/滑点/成交额容量门；只有归一化研究门和该附加门同时通过，才可能进入后续组合登记。当前旧 43 因子不会为此回跑，因而这项门禁尚未授权任何现有因子、榜单或订单。

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
## 分钟与事件数据

日线管线继续是当前策略的唯一正式行情底座。三日持有期策略需要的尾盘、日内成交和资金流因子，使用独立且可审计的接入器；它不会覆盖日线数据或直接改动 Qlib 二进制。BaoStock 五分钟线可以匿名读取；其余专业分钟/资金流源仍要求合法本地授权。

| 来源 | 当前接入范围 | 适用阶段 |
| --- | --- | --- |
| BaoStock | 匿名原始 5 分钟 OHLCV/成交额；实测历史从 2020 年开始 | 低成本五分钟候选，独立于 1 分钟合同 |
| Eastmoney / Sina 网页行情 | 仅做固定小样本历史可用性审计；没有历史适配器 | 当前访问失败或仅有近期窗口，不作为 2020–2025 历史源 |
| RQData | 原始分钟 OHLCV/成交额 | 首选的全市场分钟研究数据 |
| JQData | 原始分钟 OHLCV/成交额；另购专业版日/分钟资金流 | 分钟替代源；同类日级大单分类已由 Tushare 实测，不再作为独立候选 |
| Tushare | 原始分钟线；默认盘后表为 `moneyflow`、`stk_limit`、`stock_st`、`top_list`；`limit_list_d` 为更高权限的可选表 | 资金流、交易约束和盘后事件补充 |

供应商账户、分钟权限和历史深度必须由实际授权确认。不要购买、猜测权限或把凭据交给仓库。

2026-07-16 的 2026-07-13 单日权限验收确认：3000 积分账户可以读取 `moneyflow`（5197 行）、`stk_limit`（7695 行）、`stock_st`（211 行）和 `top_list`（91 行），但不能读取要求 5000 积分的 `limit_list_d`。修正后四表原子验收清单为 `data/metadata/rich_data/runs/20260716T081652Z_tushare_events_6264ce79.json`（SHA-256 `83c141749256a01852cf2cb0534da653e947e264a1b5ba3eb0efa2fd4b87a849`），共 13,194 个原始行，四个 Parquet 内容指纹复核一致，未读取未来收益且不允许选股或推广。因此 `sync-tushare-events` 的默认集合固定为前四项；只有用户已经拥有 5000 积分且确实需要首次/末次封板、炸板次数或封单金额时，才显式传 `--datasets limit-list`。不要仅为了让默认命令成功而追加购买权限。

原始 `top_list` 样本包含 2 条完全重复记录。接入层保留供应商原始行，在清单中记录精确重复和事件键重复数量，并把状态停在 `pending_event_time_alignment_and_canonicalization`；后续必须先冻结规范化与去重规则，不能让重复行增加因子权重。首次按旧默认集合请求时，`limit_list_d` 权限失败并留下了一份无清单的单表目录；该目录只作为失败证据保留，任何下游都不得按文件存在推断验收通过。修正后的事件同步先写隐藏临时目录，只有全部表成功才原子发布；任一权限、字段、日期或写入失败都会删除本次临时快照。

对平均持有 3 个交易日的当前研究，Tushare 日级大单分类已完成并因双门禁失败而停止；JQData 同类产品不再计作独立候选。下一项凭证数据只有在已有合法授权时才选择 RQData/JQData 或券商导出的 1 分钟 OHLCV/成交额，且必须先冻结时间、字段与覆盖合同。分钟数据只构造尾盘收益、尾盘成交占比、日内 VWAP 路径、开盘跳空消化和日内实现波动等少量预声明字段。Level‑2 的十档盘口、逐笔委托/成交、撤单和队列字段暂不作为前置依赖：只有独立分钟候选先通过时间对齐、跨年度与 Top‑3 门禁，且剩余失败原因明确指向队列或成交优先级时，才评估合规的 Level‑2 历史授权。交易所 Level‑2 是增值行情，不应把客户端可见盘口抓取当作可回测历史数据库。

官方能力参考：[JQData 数据说明](https://www.joinquant.com/help/api/doc?id=10674&name=JQDatadoc)、[Tushare 股票数据目录](https://tushare.pro/document/2?doc_id=17)、[上证所 Level‑2 产品说明](https://www.sseinfo.com/services/assortment/level2/)。实际采购前仍须核对账户页显示的历史深度、频率、调用配额和再分发条款。

### 本机凭据和 SDK

完整的复制即用说明、继承范围、无回显验证、当前进程临时注入和清除步骤见 [`a_share_tushare_token_setup.md`](a_share_tushare_token_setup.md)。下面保留最短配置路径。

先看安全状态；输出只显示“已配置/缺失”，不会显示令牌或密码：

```bash
python scripts/a_share_rich_data.py status
```

BaoStock 全量使用外置根时，显式检查同一个目录；该命令只读本地状态，不登录供应商、不请求行情，也不删除锁：

```bash
python scripts/a_share_rich_data.py status --data-root /Volumes/DIsk/qlib-rich-data
```

`baostock_five_minute_storage.history_manifest_count` 是是否已有完整历史清单的权威计数，`raw_parquet_file_count` 只说明磁盘上有多少 Parquet，不能单独证明来源门禁通过。`latest_restoration_probe` 和 `latest_preflight` 只返回安全状态字段，不显示凭据或供应商错误正文。锁文件可能在进程退出后保留 PID 文本；只有 `process_lock.advisory_lock_currently_held=true` 才表示活动任务，不能因为文件存在就删除它。当前外置根检查为历史清单 **0**、历史 Parquet **0**、最新探针 `provider_rejected_stop_before_bulk_retry`，锁文件记录 PID 24906 但 advisory lock 未持有。

BaoStock SDK 无需凭据；其余来源只有在已取得对应授权后才配置环境变量。macOS 的 Tushare Token 使用隐藏输入，不能把真实值直接写在命令中：

```zsh
python -m pip install -r scripts/data_collector/a_share_rich/requirements.txt

read -s "token?请粘贴 Tushare Token，随后按回车："; echo
export TUSHARE_TOKEN="$token"
launchctl setenv TUSHARE_TOKEN "$token"
unset token
```

`export` 供当前终端使用，`launchctl setenv` 供之后启动的 macOS 图形程序继承。设置后必须彻底退出并重新打开 Codex。用下面的命令只检查“有/无”，不要直接运行会打印 Token 的 `launchctl getenv TUSHARE_TOKEN`：

```zsh
test -n "$(launchctl getenv TUSHARE_TOKEN)" && echo "已配置" || echo "未配置"
python scripts/a_share_rich_data.py status
```

`launchctl` 的该值不会跨注销或重启持久化，需要时重新执行隐藏输入。取消配置时，在当前终端运行 `unset TUSHARE_TOKEN`，并运行 `launchctl unsetenv TUSHARE_TOKEN` 清除后续程序的继承值。JQData/RQData 也只能在取得相应授权后采用同样的隐藏输入与本地环境变量方式，不能把凭据写进仓库文件。

令牌和密码绝不能出现在 Git、命令历史、笔记本输出、研究清单或聊天中。未安装 SDK 或缺少变量时，程序会在发出网络请求前失败；不要用抓取公开网页的方式替代已授权数据源。`status` 中 BaoStock 只检查固定 `baostock==0.9.3` 包，不要求环境变量。

### 公开五分钟历史备选源审计

在 BaoStock 恢复探针失败后，只用四只代表股票做了一次**无收益、非全市场**的公开路线探查，证据冻结在 `docs/a_share_public_five_minute_source_availability_audit.json`（SHA‑256 `743a7751f74c87dd11162f326b02c5d87f2e736456e160754fb6e45097078830`）。目标不是寻找当日信号，而是先证明某条路线能稳定覆盖 2020‑01‑01 至 2025‑12‑31；未构造任何因子，未加载本地日线开收盘或远期收益，也未落盘源行值。

Eastmoney 的公开 K 线网页显示支持 5 分钟图，但当前环境对 `push2his.eastmoney.com/api/qt/stock/kline/get` 的四股票、三个历史终点共 12 次小请求均被远端直接断开；一次仅请求 10 根的协议探针也得到 `curl` 退出码 52、空响应。这个结论只说明**当前网络无法接入**，不能推断其全球没有历史，也不能通过 Cookie、客户端登录态、代理或高频重试绕过。

Sina 的公开 JSONP 路线能返回 `day/open/high/low/close/volume/amount`。四只股票分别请求 1023/1024 根时均完整返回，但共同最早时间只有 2026‑06‑12；贵州茅台请求 1500 根时窗口为 2026‑05‑29 14:05 至 2026‑07‑14 15:00，请求 2000、2500、3000、4000、4999、5000 或 100000 根均返回空集，且没有观察到可验证的历史日期游标。因此它只是近期深度窗口，不能回填 2020–2025，也不能和 Eastmoney 混成一份历史源。

两条路线均在适配器、全量快照、因子和收益之前停止。Sina 若用于登记日之后的未来观察，仍须另行冻结一个 future-only 合同并验收时间标签、复权、成交量单位和持续可用性；本次近期窗口不能直接进入纸面监控。Tushare 日级分类资金流后来已完成正式研究并失败停止；当前历史研究只等待 BaoStock 在未来新的研究会话中出现可验证恢复，或用户本地已有合法授权的全市场分钟产品。不要为复制已失败的大单分类机制单独购买 JQData。Level‑2 继续延期。

### BaoStock 匿名五分钟候选

仓库原有 `scripts/data_collector/baostock_5min/collector.py` 和 [BaoStock 官方 Python API](https://www.baostock.com/mainContent?file=pythonAPI.md) 都支持 `frequency="5"` 的原始五分钟线。匿名可用性实测显示：浦发银行、平安银行和宁德时代在抽查的 2019 日期均返回 0 行，2020‑01‑02 起抽查完整交易日返回 48 行；因此它不能冒充既有 2019–2025、1 分钟、240 bar 合同。独立数据合同冻结为 `docs/a_share_baostock_5m_data_contract.json`（SHA‑256 `3352497aa911f69ced631fac57db1369eaa12acabad8ca7857f6254205354a8f`），只允许 2020‑01‑01 至 2025‑12‑31、`adjustflag=3`、`date,time,code,open,high,low,close,volume,amount,adjustflag` 十个字段，完整会话必须严格为 09:35–11:30 和 13:05–15:00 的 48 个 bar-end 标签。

该接入同时修正了分钟验收的成交量口径：未复权分钟量价必须与日线 `raw_open/raw_high/raw_low/raw_close/raw_volume` 比较，不能与反向因子调整后的 `volume` 比较。正式验收固定使用 2026‑07‑10 和四只代表股票，不开放日期、股票或频率覆盖：

```bash
python scripts/a_share_rich_data.py acceptance-baostock-5m
python scripts/a_share_rich_data.py confirm-minute-alignment \
  --manifest data/metadata/rich_data/runs/20260714T210140Z_baostock_5m_be9dfe63.json \
  --bar-label end --volume-unit shares --reviewed-boundaries
```

验收清单 `20260714T210140Z_baostock_5m_be9dfe63.json` 绑定数据合同并通过：四只股票各 48 行，全部在常规时段且时间网格精确；成交额/本地日线比值约为 1，成交量/`raw_volume` 比值约为 100，确认单位为股；四股票最大原始 OHLC 相对误差为 0.1758%，低于冻结的 0.2% 门槛。时间与单位确认是 `20260714T210154Z_baostock_5m_alignment_2b1ad30e.json`。两项都不读取未来收益，也不授权全量下载。

五分钟字段在看到任何字段值之前另行冻结为 `docs/a_share_baostock_5m_factor_preregistration.json`（SHA‑256 `a6b679c1476cacfc193aba5bf93988c92691025872150d3eaab723576c7164b8`）：`late_return_30m_5m`、`late_amount_share_30m_5m`、`late_vwap_to_day_vwap_30m_5m`、`opening_gap_digestion_5m` 方向为高，`intraday_realized_volatility_5m` 方向为低。四股票特征烟测 `20260714T210509Z_baostock_5m_features_v1_155027ba.json` 得到 4/4 合格行、0 个不完整会话，并明确 `forward_return_fields_read=false`；四股票单日值不能计算 Rank IC、形成选股或证明因子有效。

最初的全量下载在任何大请求前被磁盘门禁停止。`docs/a_share_baostock_5m_bulk_preflight_audit.json`（SHA‑256 `5cac308c82d6302e14ed076ea176a5fffb225261b3b15491aaeb8a13039a86ae`）对浦发银行 2020–2025 的单股票样本测得 69,840 行、1,455 个会话、Zstd Parquet 1,224,398 字节和 22.21 秒；按 4,800 只完整历史上界估计原始 Parquet 约 5.47 GiB，单进程约 29.6 小时、四进程理想约 7.4 小时，建议至少 10 GiB 可用空间。仓库所在数据卷仍只有约 3–4 GiB 可用，不能作为全量目的地，也不能靠自动删除缓存或已有研究数据腾挪。

全量接入现支持显式外置 `--data-root`，但先单独运行无网络预检：

```bash
python scripts/a_share_rich_data.py preflight-baostock-5m \
  --data-root /path/to/qlib-rich-data
```

预检重新验证数据合同、因子预声明、四股票验收、时间/单位确认、精确 SDK 0.9.3、本地历史股票区间和日历指纹，并在目标根目录的 `metadata/rich_data/preflights/` 写清单；它不请求网络、不读取分钟字段或收益。只有状态为 `passed_before_network` 且剩余空间不少于 10 GiB 才能继续。当前工作站选用 `/Volumes/DIsk/qlib-rich-data`，请求降频审计加入来源链后的最新预检是 `20260714T222229Z_baostock_5m_preflight_5dd2717c.json`（SHA‑256 `645f48175f1e95114977c2f1d59f3b0d9778ef88ff21107b59188d616ae9003d`）：记录 1,714.29 GiB 可用、5,451 个历史股票区间、5,386 个供应商区间请求、29,246 个本地年度存储分区和 1,455 个交易日，同时绑定目标文件系统设备号、股票区间/日历指纹、停牌占位审计及请求降频审计，已通过且 `network_request_issued=false`。

通过空间预检还不等于匿名服务已经恢复。服务端风控发生后，只允许在充分冷却或取得供应商指引后人工运行一次固定的小探针：

```bash
python scripts/a_share_rich_data.py probe-baostock-5m-restoration \
  --data-root /Volumes/DIsk/qlib-rich-data
```

它只请求已验收的 `600519`、2026‑07‑10、48 根五分钟 bar，并把成功或拒绝写到 `metadata/rich_data/availability/`。不要循环探测。只有最新记录为 `passed_for_bulk_retry`，且不超过 30 分钟，才运行固定的 2020–2025 全量命令；它没有日期、字段、频率或门槛覆盖：

```bash
python scripts/a_share_rich_data.py sync-baostock-5m \
  --data-root /Volumes/DIsk/qlib-rich-data \
  --workers 4 --allow-large
```

下载只请求冻结的十个原始字段，对每只股票裁剪后的历史有效区间发一次 2020–2025 请求，再在本地拆成年度 Parquet；因此供应商请求数是 5,386，而年度存储仍是 29,246 份。最多四个匿名会话进程，普通瞬时错误每个区间最多重试三次；`黑名单用户` 立即停止且不重试。原始重复时间戳直接失败；缺 bar 的股票日保留原始数据但整日不合格，不填充、不插值、不静默去重。所有 Parquet 先写同一文件系统的隐藏临时快照，任一请求、分区失败或遗漏即删除整份临时快照；全部成功后才原子改名并写清单。覆盖门禁要求历史有效股票覆盖率中位数至少 95%、P5 至少 90%，并至少有 200 个非重叠三交易日候选截面达到 50 只完整股票。门禁失败仍只保留可审计原始快照并停止；通过以前不读取日线开收盘或远期收益，不构造 IC、聚合评分或选股。不要在下载时拔出外置卷、让 Mac 睡眠或并行启动第二次同步；也不得跳过原始快照、只保留看起来有用的因子值来规避门禁。

全量清单只有在上述无收益覆盖门通过后，才能进入已经离线验收的五分钟特征与诊断路径。原始 Parquet 和派生特征继续放在同一个外置根；特征运行清单仍写入仓库的 Git 忽略元数据目录：

```bash
python scripts/a_share_rich_data.py build-minute-features \
  --manifest /Volumes/DIsk/qlib-rich-data/metadata/rich_data/runs/<history-run>.json \
  --alignment data/metadata/rich_data/alignments/20260714T210154Z_baostock_5m_alignment_2b1ad30e.json \
  --factor-spec docs/a_share_baostock_5m_factor_preregistration.json \
  --output /Volumes/DIsk/qlib-rich-data/derived/a_share/rich/minute_features/baostock_5m_v1/<feature-run>/features.parquet

python scripts/a_share_short_horizon_factor_research.py minute-factor-diagnostic \
  --feature-run data/metadata/rich_data/feature_runs/<feature-run>.json \
  --factor-spec docs/a_share_baostock_5m_factor_preregistration.json
```

加载器会重新核验全量快照的状态和哈希、四股票验收、时间/单位确认、因子预声明、48 根完整会话、供应商与频率、特征文件内容哈希。诊断仍固定使用 2020–2025、三日非重叠、Top‑3、0.012% 买入费和 0.062% 卖出费，并一次运行五个 `_5m` 因子。它不会沿用 1 分钟的 240 根或 2019 起始口径。进入远期收益前，还会用“完整且五分钟特征可计算的质量合格股票日”重新计算覆盖率中位数/P5 95%/90%，并验证至少 200 个三日非重叠截面有 50 个名称；失败只写覆盖审计且 `forward_return_fields_read=false`。

诊断完成后只运行两道完整默认审计，不得传 `--factor` 缩小清单：

```bash
python scripts/a_share_short_horizon_factor_research.py factor-stability-audit \
  --diagnostic data/experiments/short_horizon/<run>_factor_diagnostic.json
python scripts/a_share_short_horizon_factor_research.py factor-topk-viability-audit \
  --diagnostic data/experiments/short_horizon/<run>_factor_diagnostic.json
```

五分钟聚合规则已经在观察因子值与收益前冻结：取同时通过两道完整门禁的因子交集；少于两个就终止，达到两个才把全部合格方向分位数做一次等权聚合，不枚举子集、不搜索权重或聚合函数。2020–2025 不是新的纯净留出期，因此通过历史门禁也不能回头把聚合结果当成确认性回测或直接选股；只能在另行登记后，从登记日之后积累新的前瞻纸面观察。当前恢复探针未通过，以上命令是就绪后的固定顺序，不是现在启动因子或收益读取的授权。

两道审计完成后，用唯一登记命令固化交集决策；`--not-before` 必须晚于本地已见的全部收盘日，且只在至少两个因子同时通过时才是必需的：

```bash
python scripts/a_share_short_horizon_factor_research.py baostock-5m-combination-register \
  --diagnostic data/experiments/short_horizon/<run>_factor_diagnostic.json \
  --stability-audit data/experiments/short_horizon/<run>_factor_stability_audit.json \
  --topk-audit data/experiments/short_horizon/<run>_factor_topk_viability_audit.json \
  --not-before <first-genuinely-unseen-signal-date>
```

该命令只读取上述三个不可变 JSON 及五分钟预注册文件，不再次加载价格或远期收益。少于两个双门禁因子时写入一次终止记录；至少两个时写入全部合格因子、相等权重、缺任一分量即股票日不合格、三日持有成本与最早前瞻日期。相同四份输入指纹只能登记一次。记录会进入统一 `report` 的“BaoStock 五分钟双门禁聚合登记”章节。登记本身仍不生成分数或股票；全量历史只到 2025 年，必须另行实现并验收登记日之后的当前 5 分钟观察适配器，才能开始不可回填的纸面信号。

第一次全量尝试在完成至少 100 个分区后被 `600027` 的 2024 分区阻断，并按规则删除全部临时文件、未写最终快照或清单。隔离复核证明 11,616 个源 bar 中有 478 根来自 10 个股票日的停牌占位，精确定义为 `open=high=low=close=volume=amount=0`；其中 2024‑07‑22 和 2024‑07‑26 各另有一根 15:00 的零成交参考价 bar。这不是活动交易 bar。处置在 `docs/a_share_baostock_5m_suspension_placeholder_audit.json`（SHA‑256 `5c29bd194ef70ed0d30a1e72aa3adc7e287ec1f513e0d3ee29d7551cf1dff47d`）中冻结：零价零活动占位从可计算 bar 中排除，但其行数和股票日写入质量统计；正价零活动参考 bar 保留；这 10 个股票日整体不合格。修正后该分区写 11,138 行并识别 232 个完整且正活动会话。非占位的零/负价、负量额、OHLC 关系错误和重复时间戳仍是致命错误。该复核没有读取因子值、日线开收盘或远期收益。

第二次尝试使用四进程年度请求，在 40.95 分钟内完成 9,000/29,246 次请求、约 1.03 亿规范化行后，于 `603880/2025` 收到 `黑名单用户，请与管理员联系`；整份临时快照再次删除，没有最终数据或清单。随后的小探针连匿名登录都被拒绝。充分冷却后，2026‑07‑15 按冻结命令只执行了一次 `600519`、2026‑07‑10 的恢复探针；仍在登录阶段被服务端判为黑名单，历史查询未发出、返回 0 行，且日线开收盘、因子和未来收益均未读取。证据固化在 `docs/a_share_baostock_5m_restoration_probe_audit.json`（SHA‑256 `7d97216087a73c05bded07a05c0c3f5eecf936962d38bc7e48712f8d15220eba`），绑定外置卷原始清单 SHA‑256 `50ade9c89c476f55a0f3600c68609a92fca488be73836caa571ca9abea452d84`，结论为 `provider_rejected_stop_before_bulk_retry`。

在约 42 小时冷却且外置卷仍为历史清单 0、历史 Parquet 0、预检有效、无活动 advisory lock 后，2026‑07‑17 的当前研究会话又只执行了一次相同冻结探针。结果仍在匿名登录阶段返回黑名单，历史查询未成功、行数为 0；没有读取日线开收盘、分钟因子或未来收益。跟进记录为 `docs/a_share_baostock_5m_restoration_probe_followup_20260717.json`（SHA‑256 `932e493752916352db58fb38b0abf6e9940acd81f4aee8d8245d93b2f46a2b7b`），并绑定外置记录 `20260716T180144Z_baostock_5m_restoration_probe_ae7bd679.json`。本研究会话不再重复探针，也不启动全量、部分续传、分钟因子或收益诊断。

官方页面没有可验证的匿名数值频率上限，因此不使用代理、换 IP 或紧密登录规避。`docs/a_share_baostock_5m_request_throttle_audit.json`（SHA‑256 `4a881c707f41dc1a1043015ca004b65ff4607bc96bce21cd65c832cb20dc18aa`）在任何后续请求前把计划冻结为 5,386 次股票有效区间请求，本地仍写 29,246 个年度分区，请求数降低 81.5838% 且少于已观察的 9,000 次封禁点。恢复探针通过以前，继续做不依赖该源的研究，不得启动全量、构造五分钟因子或读取收益。[BaoStock 官方站点](https://www.baostock.com/)列有技术交流与联系渠道；是否需要联系由用户决定，代码不会自动发送消息。

### JQData 专业版日级资金流（先前冻结、现归档）

这条供应商路线曾在任何 JQData 权限或数据行被观察前冻结为 `docs/a_share_jqdata_moneyflow_data_contract.json`（SHA‑256 `1a3c451ecc2d1b4f8c2ef38a8de1acf4aa474bbce4f98b99dc0369bb8d9d6004`）。[JQData 官方文档](https://www.joinquant.com/help/api/doc?id=10674&name=JQDatadoc)说明 `get_money_flow_pro` 从 2015 年起提供日/分钟分类资金流，日级约 19:00 更新，且需单独购买；正式 JQData 账号本身不等于拥有该产品权限。无账号的东方财富个股资金流替代接口在 2026‑07‑15 对浦发银行、平安银行、宁德时代、中芯国际均只返回最近 120 个交易日，不能覆盖 2019–2025，故不作为历史源。其后 Tushare 已对等实现并完成同一“大单净流入占比”经济机制的全历史诊断，因此本节保留为可复现的历史合同和适配器说明，不再代表待执行的独立研究。

合同只请求 `inflow_xl/inflow_l/inflow_m/inflow_s/outflow_xl/outflow_l/outflow_m/outflow_s` 八个非负成交额字段，不请求供应商净额、涨跌幅、价格、市值或收益。本地唯一推导：

```text
jqdata_large_order_net_inflow_share =
  ((inflow_xl + inflow_l) - (outflow_xl + outflow_l)) /
  sum(全部八个流入/流出金额)
```

高值方向固定为更好；分母为零保持缺失，缺字段排除并计数，任何负原始金额直接中止分片，绝不裁剪、取绝对值或填充。日数据约 19:00 才可用，因此只形成当日收盘后、供下一本地交易日开盘使用的信号，事件年龄为 0。

以下命令是归档合同的原始验收入口；不要为了复制已经失败的 Tushare 机制而购买或执行。只有将来出于供应商数据一致性审计、且先另行冻结不读取收益的比较协议时，才可验收四只冻结股票和一个已收盘交易日：

```bash
python scripts/a_share_rich_data.py acceptance-jqdata-moneyflow --date 2026-07-13
```

验收必须返回四只股票、精确字段、唯一键、非负金额和 `[-1, 1]` 本地公式结果；清单不得含凭证、价格或收益。缺 SDK、缺环境变量、登录失败、产品未授权、缺股票或字段异常都会在发出大请求前停止。只有验收清单状态为 `accepted_entitlement_and_formula_pending_full_history` 后，才允许执行固定 2019–2025、历史股票区间和年度分片的全量命令：

```bash
python scripts/a_share_rich_data.py sync-jqdata-moneyflow --allow-large
```

每个年度调用必须低于供应商文档的 200 万行上限；分片依次写入同一临时目录，所有年度成功后才原子改名并写运行清单，失败删除整份临时快照。覆盖率以当日本地点时股票区间为分母，要求中位数至少 95%、P5 至少 90%，并保留至少 200 个有 50 只正活动因子值的日期。全量清单同时绑定来源验收清单、`factor_main_chinext_star` 点时区间文件和本地交易日历的 SHA‑256；任何一项随后变化，容量审计都会拒绝继续。

无收益容量规则已在任何 JQData 权限或数据行被观察前另行冻结为 `docs/a_share_jqdata_moneyflow_capacity_preregistration.json`（SHA‑256 `d379157a1fd21909f8edf33897efd7b77d1f45dc9f6e6e470da62c7f548fc159`）。它还预先绑定了 2019–2025 范围内规范化后的来源股票池、持仓股票池和交易日历指纹，日后只追加 2026+ 会话不会改变协议；历史区间被改写则会停止。全量清单状态只有达到 `full_source_coverage_passed_pending_no_return_capacity`，才可运行：

```bash
python scripts/a_share_short_horizon_factor_research.py \
  jqdata-moneyflow-capacity-audit \
  --manifest data/metadata/rich_data/runs/<full-run>.json
```

该命令逐年度核对 Parquet 内容指纹、精确列、非负八项金额、唯一股票日、供应商标识和本地推导公式，然后只在 `buyable_main_chinext`、季度质量年龄不超过 550 天、上市满 20 个会话的股票中计算 2019–2025 非重叠三日截面。每个截面至少 50 只股票、至少 2 个不同值，总计至少 200 个 cohort 且覆盖至少 5 个自然年才通过。命令不提供日期、方向、TopK、质量、上市年龄或样本门槛覆盖，并明确记录 `price_fields_loaded=[]`、`forward_return_fields_read=false`；同一全量清单只能完成一次容量审计。

容量通过本来也不代表因子有效，不能直接调用通用 `factor-diagnostic`、聚合、评分或选股。现在 Tushare 对等机制已经完成并失败，JQData 路线保持未验收、无数据、无因子结论的归档状态；不得继续进入容量或收益阶段，也不得把不同供应商包装成第二个因子。若未来仅做供应商一致性审计，必须另写不可变的无收益比较协议，并绑定双方合同与原始清单指纹。

### Tushare 日级分类资金流（当前授权实现）

2026‑07‑16 已用 3000 积分账户完成 2026‑07‑13 收盘日的原子事件验收。绑定清单为 `data/metadata/rich_data/runs/20260716T081652Z_tushare_events_6264ce79.json`（SHA‑256 `83c141749256a01852cf2cb0534da653e947e264a1b5ba3eb0efa2fd4b87a849`）；其中 `moneyflow` 有 5,197 行，缺键、越界日期和重复股票日均为 0。该单日样本已经被观察，所以新合同准确标记为“验收后、完整历史与因子收益观察前冻结”，不冒充事前未见数据。

[Tushare 官方 `moneyflow` 文档](https://tushare.pro/document/2?doc_id=170)说明数据始于 2010 年，单次最多 6,000 行，最低 2,000 积分，按主动买卖单和 L2 订单分成小/中/大/特大单；[官方更新表](https://tushare.pro/document/1?doc_id=108)标注交易日 19:00 更新。供应商特别说明 `net_mf_amount` 不能由大小单简单相减，因此合同 `docs/a_share_tushare_moneyflow_data_contract.json`（SHA‑256 `a38f8113d948a179e6cc38eb388f13fcd691fe793209703009762db6cfa81b12`）只请求股票/日期键和八个非负分档金额，不请求 `net_mf_amount`、成交量、价格、市值或收益。本地唯一因子为：

```text
tushare_large_order_net_inflow_share =
  ((buy_elg_amount + buy_lg_amount) - (sell_elg_amount + sell_lg_amount)) /
  sum(小/中/大/特大单的全部买入与卖出金额)
```

高值方向固定为更好；分母为零或字段缺失的股票日保持缺失，任何负金额中止分片，不裁剪、填充、取绝对值或改方向。该经济机制替代尚未取得数据的 JQData 合同，不是第二个独立因子；日后即使购买 JQData，也只能先冻结供应商一致性审计，不能把两家字段分别加入聚合或按收益选供应商。`top_list` 已属于失败并停止的龙虎榜机制，只保留原始对账用途；当日静态 `stock_st` 成员关系仍只用作点时股票池排除，不能直接排名；`stk_limit` 用作成交可实现性，不作为新因子。后文单独冻结的“确认退出 ST 后、按此前连续 ST 会话数排名”属于状态转换与恢复速度机制，不等同于静态 ST 二值。

完整历史下载固定为 2019–2025，只遍历本地真实交易日。每次请求一个完整交易日，字段白名单精确固定，连续调用间隔至少 0.32 秒，单日最多三次尝试；每个年度写入同一个隐藏临时快照，七年全部通过后才原子发布。达到 6,000 行上限会按可能截断处理并停止。运行：

```bash
TUSHARE_TOKEN="$(launchctl getenv TUSHARE_TOKEN)" \
  python scripts/a_share_rich_data.py sync-tushare-moneyflow --allow-large
```

命令中的 Token 只从本地 `launchctl` 注入，不能替换成明文。快照按当日 `factor_main_chinext_star` 点时区间过滤，要求来源覆盖率中位数至少 95%、P5 至少 90%，并至少有 200 个日期含 50 只正活动因子值；失败会删除临时快照或写 `full_source_coverage_failed_stop_before_prices`，不得进入价格研究。

无收益容量协议已经在完整历史、价格和因子收益观察前冻结为 `docs/a_share_tushare_moneyflow_capacity_preregistration.json`（SHA‑256 `2912fbc70d7b1b9168bddb353f6b5fd5070dc8dab15d2f78b47867c9e12ea2ab`）。只有全量清单状态为 `full_source_coverage_passed_pending_no_return_capacity` 时，才可运行一次：

```bash
python scripts/a_share_short_horizon_factor_research.py \
  tushare-moneyflow-capacity-audit \
  --manifest data/metadata/rich_data/runs/<full-run>.json
```

审计重新计算七个年度分片指纹、八项金额、因子公式、点时股票池成员和逐日覆盖率，然后只使用 `buyable_main_chinext`、550 日内季度质量、上市满 20 会话、非重叠三日网格、每截面至少 50 名且 2 个不同值。至少 200 个完整 cohort 并覆盖 5 个自然年才通过。命令不读取开盘、收盘或未来收益，同一全量清单只允许完成一次。通过只允许下一步先冻结一份绑定容量审计 SHA‑256 的单因子收益诊断；未冻结前不能调用通用诊断、聚合、当前评分、选股、仓位或订单。失败则停止这一版本，不反向、不降门槛、不改窗口、不加入 JQData 复制品或 Level‑2 补救。

完整历史已成功发布为 `20260716T085610Z_tushare_moneyflow_daily_6c78e93d.json`（SHA‑256 `eee76f4b3b3d3001f9c73e84fda6336a9732d648424828d7a000e045480e2fcb`）：七个年度共 **7,723,857** 条规范行，1,699 个本地交易日；来源覆盖率中位数 **99.684%**、P5 **99.178%**，全部 1,699 日都有至少 50 只正活动值。缺字段与零分母均为 0，点时来源股票池外排除 2,109 行。重新读取七份 Parquet 后，内容指纹、公式、点时成员和逐日覆盖率全部复算一致，过程中仍保持 `price_fields_loaded=[]` 与 `forward_return_fields_read=false`。

唯一容量审计 `20260716T091028Z_tushare_moneyflow_capacity_audit.json`（SHA‑256 `ee00d08e583f66efa7ad5ee53112c8bd0e8b112b8f922a4b7ce1fb853e8960e3`）形成 **540/200** 个完整 cohort，2019–2025 分别为 56、81、81、80、81、81、80，覆盖 7/5 年，因此只授权先冻结一次收益诊断。收益协议随后冻结为 `docs/a_share_tushare_moneyflow_diagnostic_preregistration.json`（SHA‑256 `978c86aaad0909cf327993f5ffb71a5cbc8351b01f88557c10434a8f7e84c5d8`），绑定全量清单、容量审计、季度质量、价格口径、股票池、日历、成本、20 万元整手/滑点/成交额政策，且没有语义参数覆盖。

诊断首次启动因精简行情入口缺少市场状态执行政策所需的五个收盘已知上下文字段，在形成收益摘要和写出诊断前中止。只把加载器换成既有验收的 `load_market_data`，其余参数完全不变，并按基础设施失败规则原参数重试一次。完成诊断为 `20260716T092511Z_factor_diagnostic.json`（SHA‑256 `499ac94ffb900dc4aa8776869698e8eb592e8320d754515ee7f3f0f44fc3db3a`）：542 个 cohort 的平均/中位 Rank IC 为 **−0.00763/−0.01042**，正 IC 比例 **44.65%**；只有 2019 年平均 IC 为正，2020–2025 全部为负。朴素固定三日 Top‑3 虽累计 +23.39%，但最大回撤已达 −86.41%，且它不能绕过关联与成交门禁。

成交感知 Top‑3 账本的 536 个完整信号最终为 **−89.23%**、最大回撤 **−96.99%**，2019、2022–2025 年均为负；20 万元、100 股整手、双边 10bp 滑点的试运行账本为 **−29.16%**、最大回撤 **−38.90%**，并有一笔成交额参与率 1.0619% 略超 1% 上限。正式稳定性审计 `20260716T092540Z_factor_stability_audit.json`（SHA‑256 `bb2b0eb4f17a4e2c4e6eebed60692d11a70a87deaaca32737c45fa35f82b2ed1`）与 TopK 审计 `20260716T092540Z_factor_topk_viability_audit.json`（SHA‑256 `361bec4f83d4cca224e1eb23447bbeb1da12b1ea9aa3820a5ea484aa9da44343`）均通过 **0/1**。

因此 `tushare_large_order_net_inflow_share` 高值方向正式淘汰。完整终止记录为 `docs/a_share_tushare_moneyflow_research_record.json`（SHA‑256 `3e9d4cb001dfef2589fa32f5b6a69ae69ca6e8e122007c3bc10cf7200202336a`）。不得反向、修改大小单阈值或分母、改变三日窗口/年份/TopK/成本、挑选 2019–2021、与旧因子或 JQData 同机制复制品组合、重新运行诊断、生成当前评分/选股/仓位或据此采购 Level‑2。完成诊断的最差 cohort 明细中 `close_known_feature_ranks` 名称下保存的是原始收盘已知上下文值；这些字段只用于尾部说明，不参与 Tushare 排名、Rank IC、TopK 选择、市场状态构造、两套成交账本或门禁，不能按“分位排名”解释，也不授权为修复展示标签而重跑结果。

### Tushare 北向 Top10 与日频 PB 验收

在大单资金流停止后，只按独立经济机制依次做了两个不读取价格或收益的单日来源验收。北向成交 Top10 合同 `docs/a_share_tushare_northbound_top10_data_contract.json`（SHA‑256 `9362211f3e35cbb24c779d49d138fb757d61f7a092b61f0304d0e147a739f63e`）先于接口行冻结，固定要求 2026‑07‑13 沪股通与深股通各含完整排名 1–10。第一个沪股通请求返回 0 行，程序立即停止，没有发出第二个市场请求。终止记录为 `docs/a_share_tushare_northbound_top10_source_acceptance_record.json`（SHA‑256 `29f1dd342f64b2a19efd0f5f9723db6d6b7b867940c12520395f41a8f5b6df81`）。这只证明当前日期路线不能形成合格信号，不声称供应商全球历史为空；不得改用旧日期、把空响应当零、降低完整性、同步历史或读取收益。

随后选择 `daily_basic.pb` 作为独立的点时估值机制，合同 `docs/a_share_tushare_daily_pb_data_contract.json`（SHA‑256 `cd5c95636d9efa8eb975190072dfe94c4ee6da954dd4d9d6826d2c0b391ebdd2`）在任何接口行前冻结。请求字段严格为 `ts_code,trade_date,pb`，唯一因子为正 PB 的倒数 `tushare_positive_book_to_market = 1 / pb`，高值方向固定为更好；不请求价格、PE、市值、换手率、股息、涨跌停或收益。2026‑07‑13 单日验收返回 5,524 条全市场源行，在 4,592 只点时可持有股票中保留 4,546 只正 PB，覆盖率 **98.9983%**，高于冻结的 90% 门槛；排除 42 条缺失 PB、0 条非正 PB 和 936 条股票池外记录，重复股票日为 0。可提交的验收记录为 `docs/a_share_tushare_daily_pb_source_acceptance_record.json`（SHA‑256 `0f4dcf910bfd7fca29a1ea97781ce8d65094fe54b53e98c54fd81f3817028574`）；本地原始清单 SHA‑256 为 `29951a3581e427f2ce0be875fadb50567dd4a8b1c55159601a3cb68040d2e4b7`。

PB 验收通过只说明账户权限、三字段口径、倒数公式和当前覆盖率成立，不说明因子有效。绑定该验收的全历史、唯一性和容量协议已经在完整历史与任何因子收益观察前冻结为 `docs/a_share_tushare_daily_pb_capacity_preregistration.json`（SHA‑256 `14668ad3f97cef68cd2fae882507280ef835c0f5e7b4ddecb763c1907590c0a0`）。它固定 2019–2025、三日非重叠网格、至少 200 个 50 名/2 值 cohort、至少 5 年、550 日季度质量、上市满 20 会话，以及 2025 年对 43 个既有收盘已知字段逐一做至少 100 日/50 名的日截面 Spearman 唯一性检查；PB 与任一字段的绝对中位相关达到 0.8 即停止。容量必须先于既有收盘字段加载，容量和唯一性都通过后才允许另行冻结收益诊断。

全历史命令只读取本地 `launchctl` 中的 Token，并按本地交易日逐日请求 `ts_code,trade_date,pb`：

```zsh
token="$(launchctl getenv TUSHARE_TOKEN)"
TUSHARE_TOKEN="$token" python scripts/a_share_rich_data.py \
  sync-tushare-daily-pb --allow-large
unset token
```

第一次尝试在历史 `.BJ` 源代码进入持有股票池排除门之前被误判为缺键，程序删除了完整临时目录且没有发布清单；修复仅让合法北交所源代码进入既有的“股票池外排除并计数”路径，没有把它们加入可持有股票池。原参数重试成功发布 `20260716T102519Z_tushare_daily_pb_2e5c38bf.json`（SHA‑256 `280bc68239cc70a5e7d6e44dbb0a15a0b331be8215ddfb8d9ebd27a408e1e366`）：7 个年度、1,699 个交易日、**7,042,084** 条正 PB 可持有行；覆盖率中位数 **98.847%**、P5 **98.354%**，全部 1,699 日都至少有 50 个值。共排除 57,287 条缺失 PB、0 条非正 PB 和 832,455 条点时持有股票池外记录。独立重读全部分片后，行数、内容指纹、`1 / pb` 公式、点时成员和逐日覆盖率均一致，且 `price_fields_loaded=[]`、`forward_return_fields_read=false`。

唯一联合无收益审计按预注册顺序运行：先完整重读七个分片并计算容量，容量通过后才加载 2025 年 43 个收盘已知字段。记录 `20260716T105955Z_tushare_daily_pb_no_return_audit.json`（SHA‑256 `a6a548539dd8017e57e226189678195e646795050244fe4914627f574e6d6e9c`）形成 **540/200** 个完整三日 cohort，2019–2025 分别为 56、81、81、80、81、81、80，覆盖 7/5 年。唯一性阶段保留 161,152 个质量、上市和 PB 均完整的 2025 行；43/43 个字段都有 243 个有效日且都低于 0.8，最近的是 `amplitude_5`，绝对中位日秩相关为 **0.4411**。审计仍为 `forward_return_fields_read=false`，因此只授权先冻结一次收益诊断。

收益协议随后冻结为 `docs/a_share_tushare_daily_pb_diagnostic_preregistration.json`（SHA‑256 `ad1e14fa8d2a858b7c35a0259ebe7ab087f2c08b2f27281edb7f3c08582b47da`），绑定上述审计、源清单、季度质量、价格口径、股票池、日历、三日/Top‑3/成本规则和两套执行政策。唯一诊断 `20260716T110957Z_factor_diagnostic.json`（SHA‑256 `c1afa5fa4a4551a14b202e0c84dbaf0fea3f1433410becbbbd5f75771b200763`）在 542 个 cohort 上得到平均/中位 Rank IC **+0.02164/+0.01788**、正 IC 比例 **53.87%**、TopK 减 BottomK 毛收益差 **+0.1965%**。但 2019、2020 年平均 Rank IC 分别为 −0.05068、−0.01719，跨年关联门失败。

朴素固定三日 Top‑3 累计 **+107.38%**、最大回撤 **−23.55%**，不能单独放行。成交感知账本累计 **+110.49%**，但最大回撤 **−24.12%** 超过 −20% 门槛且 2019 年为 −12.62%；20 万元、100 股整手、双边 10bp 滑点账本为 **−3.33%**，2019、2020、2022、2023、2025 均非正。稳定性审计 `20260716T111018Z_factor_stability_audit.json`（SHA‑256 `7b4aad95bb3c5c67cbfe9ef1d6007f7e0e2f88e745c43e15e5288dce39a9c201`）与 TopK 可行性审计 `20260716T111028Z_factor_topk_viability_audit.json`（SHA‑256 `d3055ab38cbd26508ae15cf07df892d6e58f3e24922c7d420059fe8eaedc751e`）均通过 **0/1**。

因此 `tushare_positive_book_to_market` 高值方向正式终止。完整记录为 `docs/a_share_tushare_daily_pb_research_record.json`（SHA‑256 `2bcf42171babc96043053c2669351d5ce2b84541f5da91ff1e568136cec9eae3`）。不得重复诊断、反向、改 PB 变换或阈值、挑选 2021–2025、改变持有期/TopK/成本/质量/上市门、与旧失败因子组合，或生成当前评分、选股、仓位和订单；这一失败也不构成采购 Level‑2 的理由。

### Tushare 申万一级行业广度（完整门禁已完成，历史方向终止）

独立行业机制使用 Tushare `index_classify(level="L1", src="SW2021")` 和 `index_member_all`，不把行业标签本身当作收益结论。合同 `docs/a_share_tushare_sw_industry_breadth_data_contract.json` 与无收益预注册 `docs/a_share_tushare_sw_industry_breadth_capacity_preregistration.json` 已在完整成员历史、行业广度值和因子收益出现前冻结。唯一候选为 `sw1_three_session_leave_one_out_breadth`：每天只用当日及过去收盘收益，按当日有效申万一级行业成员计算正收益占比，剔除股票自身，要求至少 10 个其他上市满 20 会话的有效同行，再对精确连续三个本地交易日取均值；高值方向固定为更好。持仓范围仍是 `buyable_main_chinext`，行业同伴来源使用 `factor_main_chinext_star`。

完整成员同步固定 31 个申万一级代码、`Y/N` 两种成员状态、共 62 次顺序请求，且不请求价格、因子值或收益。第一次全量尝试在供应商占位代码 `T00018.SH` 处按严格股票代码校验停止，临时快照已删除且没有发布最终清单。修复记录 `docs/a_share_tushare_sw_industry_breadth_symbol_repair.json` 只允许把六位 `.SH/.SZ/.BJ` 转为本地代码，并排除、计数无法进入冻结股票池的非六位占位代码；没有改变公式、方向、窗口、同行阈值或请求集合。按原参数从 62 次请求全部重启的一次重试成功发布 `20260716T114724Z_tushare_sw2021_l1_membership_92ef71fe.json`（清单 SHA‑256 `8582eb25f91ddcbe01130057ecb118431168545fa0a182cdb428c3a8d2a0228e`，成员帧 SHA‑256 `474bbfcd7da4bb4d1a7c1f6b30e7c26e19230782ddee2769af4539cc3eab5c88`）。快照共 7,803 行，其中当前成员 5,863 行、历史成员 1,940 行、唯一股票 5,863 只、31/31 个一级行业有记录、重复区间 0，并明确排除 1 条占位代码。

独立无价格复核把同一股票同一一级行业的重叠区间合并为 7,043 个点时区间，并拒绝任何同时属于两个一级行业的冲突。2019–2025 可持有股票的行业成员覆盖率中位数为 **99.651%**、P5 为 **98.145%**，通过冻结的 95%/90% 门槛。随后唯一联合无收益审计 `20260716T121912Z_tushare_sw_industry_breadth_no_return_audit.json`（SHA‑256 `083a6941aba00fd9caac954a404bf7e06bac4213b5e3668f161f3a47fc4680e3`）严格先做因子覆盖和容量，再加载 2025 年 45 个收盘已知比较字段：形成 7,048,922 个有效持有股票因子行、1,697 个至少 50 名的交易日和 **540/200** 个三日 cohort，覆盖 7/5 年；45/45 个字段都有 243 个有效比较日且绝对中位日秩相关均低于 0.8，最近的是 `momentum_3`，相关为 **0.26385**。该记录保持 `forward_return_fields_read=false`，因此只授权冻结一次收益协议。

收益协议 `docs/a_share_tushare_sw_industry_breadth_diagnostic_preregistration.json`（SHA‑256 `54940682e5325beafd086e80883fc2a02c2fc9f24eede08a11b53ce89c6628e1`）绑定上述全部证据、唯一高值方向、2019–2025、三日/Top‑3/成本、550 日季度质量、上市满 20 会话和两套执行政策。唯一诊断 `20260716T123832Z_factor_diagnostic.json`（SHA‑256 `01b3825a751a302f7ab041a04ff92ad32272364ee3cd939bb0e026e68e05f30d`）在 542 个 cohort 上得到平均/中位 Rank IC **+0.00049/−0.000004**、正 IC 比例正好 **50%**、TopK 减 BottomK 毛收益差 **−0.2107%**。2022–2025 的年度平均 Rank IC 都为负，关联稳定性门失败。

朴素固定三日 Top‑3 累计 **−68.29%**、最大回撤 **−76.03%**。成交感知账本累计 **−60.40%**、最大回撤 **−72.40%**，2019、2020、2021、2024 年为负；20 万元、100 股整手、双边 10bp 滑点账本累计 **−18.42%**、最大回撤 **−20.76%**，只有 2025 年微幅为正。完整默认稳定性审计 `20260716T123902Z_factor_stability_audit.json`（SHA‑256 `87680eb84e63d9bd4a5741aa783143c32a3c934b5bd1875df62d7d56550a63a4`）和 TopK 可行性审计 `20260716T123907Z_factor_topk_viability_audit.json`（SHA‑256 `196d7726793574468852481baf3c7ad1a07b8fc4edd14530cae4c5131d68ac49`）均通过 **0/1**。

因此这一申万一级行业广度历史方向正式终止。完整记录为 `docs/a_share_tushare_sw_industry_breadth_research_record.json`（SHA‑256 `14089c6854060f69d69eafb712ed4f29f1861ec993b5cff9a48b53fae325bfa3`）。不得重复同步或诊断、反向、改三日窗口/同行阈值/行业层级/是否剔除自身、挑选年份、改变持有期/TopK/成本/质量/上市/执行门、与旧失败因子组合，或生成当前评分、选股、仓位和订单；该失败也不构成采购 Level‑2 的理由。后续只能从新的、先验冻结且机制独立的数据假设开始。

### Tushare 龙虎榜机构席位（单日验收失败，历史方向终止）

这一独立候选是 `top_inst` 机构专用席位净买入机制。数据合同 `docs/a_share_tushare_top_inst_data_contract.json`（SHA‑256 `0520cd8bac454f14c2434cf7b8092aaaf3ff94cdc09b5404a6b55323bf0e7461`）在任何 `top_inst` 权限结果、数据行、全历史、因子值或因子收益被观察前冻结。唯一候选固定为同股票同日所有唯一机构席位的 `(sum(buy)-sum(sell))/(sum(buy)+sum(sell))`，高值方向固定为更好；供应商 `net_buy` 只允许用于逐行完整性对账，缺失事件不补零、不向前填充。

代码先通过 5 个机构席位聚焦测试和整套 **341** 个数据管线测试。无网络预检重新验证了同日原始 `top_list` 的 91 行内容摘要和 2 条原始重复，并在股票一致性集合中排除了 8 条北交所/非普通股证券行。随后唯一的 `2026-07-13` 请求按精确六字段进入本地校验，但有 **505** 条记录在日期、股票键、机构席位、`buy`、`sell`或 `net_buy` 中至少一项缺失或非有限。严格验收在席位唯一性、`net_buy` 对账、股票聚合和因子值之前拒绝，未发布原始或标准化快照。拒绝清单 `20260716T130843Z_tushare_top_inst_acceptance_85802249.json`（SHA‑256 `0d4c060e581b86823e853549192ff6fc3cfd6cb30401e872a2926bd270f4122f`）明确为 `forward_return_fields_read=false`。该清单没有保存被拒原始帧，因此响应总行数和分字段缺失明细未知，不得为补这一信息而第二次请求。

这一数据源方向现在正式终止。完整记录为 `docs/a_share_tushare_top_inst_source_acceptance_record.json`（SHA‑256 `1a69c5029154c9a81bfb4ee90d60742989eb6d7c86b8cce0c390dfa88899cb07`）。不得换日期或重试，不得删除 `net_buy` 对账、补零、静默剔除 505 条异常后接受余下数据，也不得换席位字段、运行全历史/容量/唯一性/收益、聚合、评分、选股、仓位、订单或据此采购 Level‑2。该分支不向任何因子组合贡献字段；后续只能从新的、机制独立且在数据行被观察前冻结的无收益合同开始。

### Tushare 前十大流通股东集中度（单次验收失败，历史方向终止）

在继续筛选 3000 积分可用的数据时，涨跌停榜单、热榜和筹码接口分别需要 5000 至 8000 积分，因此没有盲目探测或追加购买。`top10_floatholders` 官方要求 2000 积分，提供公告日、报告期和占流通股本比例。它与既有股东户数/大股东因子存在明显同义风险，所以数据合同 `docs/a_share_tushare_top10_float_concentration_data_contract.json`（SHA‑256 `cec766613b49292e724cfd78090bdbec9d7c52ae8b337bceaf0ebe208c729897`）在任何接口行或权限结果出现前，把唯一候选冻结为“首个完整十名披露的流通股集中度减去紧邻上一季度集中度”，高值固定为更好，并规定即使来源验收成功也必须先通过无收益容量和与所有股东户数/大股东字段的相关性门。明文股东名称只允许在内存做唯一性检查，若成功落盘只能保存 NFKC 规范化名称的 SHA‑256。

实现先通过 5 个聚焦测试和整套 **346** 个数据采集测试；11 个本地合同、宇宙、日历、价格基准和旧股东证据指纹也在无网络预检中通过。随后唯一允许的三个请求固定为 `600519.SH`、`000001.SZ`、`300750.SZ`，报告期固定为 2024‑12‑31 至 2025‑12‑31，分别返回 42、40、48 行，共 130 行。严格标准化在首个异常响应中发现 **2** 条 `ts_code`、`ann_date`、`end_date`、规范化股东名称或 `hold_float_ratio` 至少一项缺失或非有限的记录，因此在股东哈希发布、十名完整性、首版选择、季度差值、容量、近同义检查、价格和收益之前拒绝，且没有发布任何数据文件。拒绝清单 `20260716T133620Z_tushare_top10_float_concentration_acceptance_cc52e8ff.json` 的 SHA‑256 为 `88cd59c2ddd30af1a9531a7f1b9453a319763224ec229ff4e509539ed9f9600f`，明确记录 `price_fields_loaded=[]`、`forward_return_fields_read=false` 和明文身份未落盘。由于拒绝原始帧没有保存，分字段缺失与完整的分股票有效性明细未知，不得为补这一信息而重试。

这一方向现已正式终止。完整记录为 `docs/a_share_tushare_top10_float_concentration_source_acceptance_record.json`（SHA‑256 `9396a687aeae176097006395406ab79d74a015b1d9392f89023658b438bd2cdf`）。不得换股票或报告期、删除/填补两条异常、改用总股本比例/持股数/持股变化/股东类型、放松恰好十名和紧邻季度规则，也不得运行全历史、容量、唯一性、收益、聚合、当前评分、选股、仓位、订单或据此采购 Level‑2。该分支不向任何组合贡献字段。

### Tushare 经营现金流/归母净利润（全量来源二次原子失败，方向终止）

新的独立会计质量候选在任何 `income`、`cashflow` 行、权限结果、因子值或收益出现前冻结于 `docs/a_share_tushare_cash_conversion_data_contract.json`（SHA‑256 `54584d758fc0846d90281fecedc7b90113823bb56b55d4782e749a9a5212ee01`）。唯一因子是累计合并口径 `n_cashflow_act / n_income_attr_p`，高值固定为更好；只接受一般企业 `comp_type=1` 和 `report_type=1`。任一调整报表类型会剔除该接口整期，不同的一号报表版本会剔除该期，只有公告日、实际公告日和指标完全相同的语义重复行可以显式折叠。`update_flag` 只计数，不选值；归母净利润必须严格为正，经营现金流可为负。信号日期取两张表 `f_ann_date` 的较晚者，只能在下一本地交易日开盘使用，最长保留三个自然日。

实现先通过 8 个聚焦测试、完整 **354** 个数据采集测试、Python 编译、CLI 和 diff 检查。无网络预检重新验证了合同和 10 个本地上下文指纹，确认既有验收记录为零且未读取价格或收益。唯一允许的验收随后按 `600519.SH`、`000333.SZ`、`300750.SZ` 各调用一次 `income` 和 `cashflow`，正好 6 次；各接口分别返回 11/15、12/14、11/13 行，共 76 行，全部低于单次 100 行上限。版本规则为每只股票保留 10 个可连接报告期，共发布 30 行因子；16 条完全相同的语义重复行被显式折叠，没有调整期、版本歧义、缺失指标、非正利润分母、非有限现金流或重复因子键。因子范围为 0.2889472485 至 2.6982034084。原始财务报表帧没有落盘，价格字段为空且 `forward_return_fields_read=false`。

接受清单为 `data/metadata/rich_data/runs/20260716T135952Z_tushare_cash_conversion_acceptance_c829bf52.json`（SHA‑256 `8307b86d53a41a3fb2d5c827c9a2c1f356022ae8dd16d2f781b63ba2875af5b1`），已发布因子帧 SHA‑256 为 `0bd8b2b807ce4bbbd56285367267efa0b190ac31c93382a11c039fbda1093dcb`。跟踪记录为 `docs/a_share_tushare_cash_conversion_source_acceptance_record.json`（SHA‑256 `615f0b794c165569b3d89444c594ee16fc60c628b36f0f834c759e09167fe962`）。来源验收已永久消费，不得换股票、日期、字段或版本再次验收。在全量结果出现前，它当时只允许按冻结合同顺序运行 2019–2025 全量来源、无收益容量与 54 字段近同义门；验收通过本身从未证明历史收益，也从未允许聚合、评分、选股、定仓、下单或据此采购 Level‑2。

完整 Token 配置、无回显验证和旧进程的单次透传方式见 [`a_share_tushare_token_setup.md`](a_share_tushare_token_setup.md)。全量来源仍处于活动状态时，唯一命令曾是 `sync-tushare-cash-conversion --allow-large`；它固定为 2019–2025 点时范围并原子发布年度分区。现在终止记录已冻结，命令会在任何来源链或供应商调用前拒绝，不能再运行。

无收益门禁已经在全量结果出现前冻结为 `docs/a_share_tushare_cash_conversion_no_return_preregistration.json`（SHA‑256 `6966e50e734d6d7ff9e706c280f7c371b3eec626445677d07006a2e02c44ec8e`）。它原本要求先重验来源、七个年度分区、公式、点时股票集合和事件冲突，再在完全不读价格的情况下检查固定三交易日容量；只有容量通过才可临时计算预注册的 54 个收盘已知比较字段与两个质量复合字段。由于从未产生成功全量清单，这份门禁没有运行，比较价格字段也没有加载。

首次全量同步按 4,794 只股票和 9,588 次固定调用推进，在 `SZ002961 / income`、第 6,579 次调用发现完整整数 `comp_type=7`。临时快照被删除，最终快照未发布，价格与收益均未读取；失败记录 SHA‑256 为 `59693d4e34f63425670eaf6bf41adf9aacca888379c36ba315535c82b4ab3f3a`。官方文档仍只定义公司类型 1–4，因此没有推断 7 的业务含义。修复规则在重跑前冻结为 `docs/a_share_tushare_cash_conversion_company_type_repair.json`（SHA‑256 `0ac8c8caecafc92fd7af4626588b9f9830c1828ed40dd45b18bbc7522aa8bc80`）：候选仍严格为整数 1，其他完整整数只能排除并计数，缺失、非有限或非整数仍致命；只授权一次从头重跑，成功或失败都会消费授权。

唯一重跑通过了原失败边界，但在 `SZ301200 / income`、第 9,037/9,588 次调用发现非标准季度末并再次原子终止。它完成了 4,518 只股票，没有发布年度分区或最终清单，临时目录已删除；失败记录 SHA‑256 为 `0f4d6d40081eda418a7a94c999ec83f1a5be33a29f6af5af0470390de10c7344`，仍为 `price_fields_loaded=[]`、`forward_return_fields_read=false`。完整终止记录是 `docs/a_share_tushare_cash_conversion_research_record.json`（SHA‑256 `c1678755db519ae6645b7f1dd3ba61e768e36dc3976c8cef7d5b2e44ff45a819`）。不得第三次同步、重取异常股票来补明细、放宽季度末或报表键、映射未知公司类型、复用删除的半成品，亦不得运行容量、唯一性、收益、聚合、评分、选股、仓位、订单或据此采购 Level‑2。该分支不向任何组合贡献因子。

### Tushare 业绩预告同比中点（一次调用后终止，且与既有失败机制重叠）

在现金转换终止后，曾基于官方 `forecast` 文档冻结 `docs/a_share_tushare_earnings_forecast_data_contract.json`（SHA‑256 `4d2503381f3f7afcd02fcb80ed2a3a6ea06bddb0d1bb2831523ef0a7796c781b`）。合同只请求股票、公告日、报告期、预告类型、同比上下限和首次公告日七个字段，候选固定为预增/略增/续盈/预减/略减的 `(p_change_min + p_change_max) / 2`，扭亏/首亏/续亏保持缺失；不请求净利润金额、摘要、原因、报表字段、价格或收益。合同、4 个专项测试和当时完整 367 个数据采集测试均在任何接口行之前完成。

一次性验收的首个请求 `002466.SZ` 在标准化阶段被实现中额外加入的“报告期不得晚于公告日”检查拒绝。该检查不在冻结合同中，而且对可提前发布的业绩预告并不成立；但拒绝记录已经发布并消费一次性验收，不能修改实现后再请求。失败记录是 `data/metadata/rich_data/runs/20260716T173315Z_tushare_earnings_forecast_acceptance_2dd6da1a.json`（SHA‑256 `56125255b582c05c4e3889b75aefa4e29f77bb0b372fbc2c1456df5ff3883fe7`），仅发出 1/3 次调用，没有保存原始帧、构造或发布因子值，临时目录已删除，`price_fields_loaded=[]` 且 `forward_return_fields_read=false`。

随后重新核对研究账本发现，这也不是新的独立机制：既有 `performance_forecasts.parquet` 已在公告事件重建协议 `docs/a_share_announcement_event_rebuild_preregistration.json`（SHA‑256 `131c1b0cd44f6b2451991389375e57583b724df1567f5c82d0d8612e0966db7c`）下，用接受价格和 20 日上市门完成一次固定重建。`20260714T162126Z` 诊断及 `20260714T162139Z`/`20260714T162140Z` 两个完整审计对 9 个公告因子合格 **0/9**；表现最好的预告精度平均 Rank IC 也只有约 +0.00745，并在 2021、2022、2025 年和最大回撤门失败。换成 Tushare 百分比区间中点或缩窄类型，不会让同一个管理层业绩预告机制变成独立因子。

终止记录为 `docs/a_share_tushare_earnings_forecast_source_acceptance_record.json`（SHA‑256 `38b966eea1728769ca977c1e26733527fc908846188e4727f2d76b716e97878b`）。生产入口会在合同或供应商访问前拒绝。不得第二次验收、换股票/日期/字段/类型/公式/方向/事件年龄、为同一预告机制另写 v2 合同、运行全历史/容量/唯一性/收益，也不得聚合、评分、选股、定仓、下单或据此采购 Level‑2。下一机制必须先回到已记录研究前沿核重，确认经济独立后才能写合同或请求数据。

### Tushare 财报计划及时性（前沿核重后一次调用终止）

在继续寻找新机制前，`research-frontier-audit` 被重新运行到独立的本地记录 `20260716T174304Z`，仍复现 43 个历史因子、7 个关联稳定性通过、TopK 通过 0、双门交集 0，且没有重读原始价格或新增收益。机制级记录为 `docs/a_share_three_day_mechanism_overlap_reaudit_20260717.json`（SHA‑256 `f21194cf93b5ac126d6cb39d93cab529d77a2e28ab153b90e0cc2326c860370e`）。候选 `hk_hold` 虽然在经济上不同于分类大单和北向 Top‑10，但官方说明交易所从 2024‑08‑20 起停止日度北向持仓披露，因此它不能产生当前同口径信号，在任何行或适配器之前即被排除。

唯一推进的独立候选是财报披露计划及时性。合同 `docs/a_share_tushare_disclosure_promptness_data_contract.json`（SHA‑256 `dece34e99134b1ba0f55f7970833d7b0835e756f99a81f335a9c6af4795fa47c`）在接口行前固定只请求 `ts_code,ann_date,end_date,pre_date,modify_date`，原始值为 `pre_date - ann_date` 的日历日数，越短越好。`actual_date`、财务结果、文本、价格和收益全部禁止；`modify_date` 只允许计数是否存在，不解析、不保存到因子帧，也不参与公式。合法 `.BJ` 行只排除并计数，缺失、畸形或未知后缀仍致命。4 个专项测试、完整 372 个数据采集测试、Python 编译与 diff 检查均在请求前通过。

一次性验收只来得及请求首个固定年报期 `20191231`。接口返回 4,432 行，低于 6,000 行截断上限，但其中 25 行至少有一个股票代码、最新公告日、报告期或计划日缺失/不可解析，因此触发合同中的致命来源门。失败记录为 `data/metadata/rich_data/runs/20260716T175559Z_tushare_disclosure_promptness_acceptance_d4a47b11.json`（SHA‑256 `5929ce2a1520a9b93b170868be89e8dee7ef3842feb9a7de37625f2170ce9ef4`）。只发出 1/3 次调用，没有请求 2024/2025 年报期，没有保存原始帧或 `modify_date` 值，没有构造或发布因子值；临时目录已删除，价格字段为空且 `forward_return_fields_read=false`。

终止记录为 `docs/a_share_tushare_disclosure_promptness_source_acceptance_record.json`（SHA‑256 `2096e48a6126126e7fb4fd612e6f443a57e43df43bcfc45aa384d2574797e3ef`）。由于原始帧按合同未保留，25 行的具体字段分布未知；不得为了补这个细节再请求，也不得删除/填补/推断异常行、换报告期、增加 `actual_date`、删除 `modify_date`、改变日期锚点/方向/事件年龄或另写同机制 v2。生产入口会在合同、Token 或供应商访问前拒绝。不得运行全历史、容量、唯一性、收益、聚合、评分、选股、仓位、订单或据此采购 Level‑2；该拒绝只证明来源不符合冻结合同，不代表因子收益已经失败。

### Tushare 审计意见（全量来源通过、三日容量不足，方向终止）

在重新复现 43 个历史因子、7 个关联稳定性通过、TopK 通过 0、双门交集 0 后，机制核重记录 `docs/a_share_three_day_audit_opinion_mechanism_overlap_reaudit_20260717.json`（SHA‑256 `a13470c5dafa4c278035e7b17e56f896ae03932b4131b6d90830a2168282acdb`）排除了权限不足或机制重叠的集合竞价、异常波动和基金持仓路线。唯一推进的独立无收益候选是 [Tushare `fina_audit`](https://tushare.pro/document/2?doc_id=80) 审计意见；官方接口最低 2,000 积分。`stock_basic` 只保留为上市/退市与幸存者偏差基础设施，不作为因子。

合同 `docs/a_share_tushare_audit_opinion_data_contract.json`（SHA‑256 `701240585505558cf34a3e9bc51ba17fb2c50ed1617fc13b332973b331c76d97`）在任何接口行之前冻结。它只请求 `ts_code,ann_date,end_date,audit_result`，对完整非空文本只做 Unicode NFKC 和首尾空白清理；文本精确等于“标准无保留意见”时因子为 1，其他完整意见一律为 0，不允许同义词映射。信号只能从公告日后的首个本地交易日开盘使用，最长保留 3 个日历日；原始或标准化意见文本、审计费用、机构、签字人、价格与收益均不得保存或读取。

唯一一次三股票验收已成功：固定请求贵州茅台 `600519.SH`、平安银行 `000001.SZ`、康美药业 `600518.SH` 的 2019–2025 公告范围，共发出 3 次调用并取得 21 条来源记录，每只 7 条。四种意见类别只以摘要计数，严格公式产生 17 个值 1 和 4 个值 0；发布 21 个股票公告事件，重复键为 0。验收清单为 `data/metadata/rich_data/runs/20260716T182013Z_tushare_audit_opinion_acceptance_e6843d5a.json`（SHA‑256 `f23e7cc7571dc08f72d8ca1cbf465e2556934f22043a34aff50a87af8aab9b51`），跟踪记录为 `docs/a_share_tushare_audit_opinion_source_acceptance_record.json`（SHA‑256 `f5909c8114eb8505de1f86eab75ccf246938d9c537d7bbaf0f308d09e3dfce92`）。一次性验收已永久消费，不能再次运行 `acceptance-tushare-audit-opinion`；入口会在 Token 或供应商访问前拒绝。

固定的全量来源同步已完成且只执行一次：2019–2025 共顺序请求 5,451 只来源股票，取得 38,876 条审计报告并聚合为 34,228 个股票公告事件，按公告年写入 7 个不可变 Parquet 分区。严格二值公式得到 32,357 个值 1 和 1,871 个值 0；没有保存原始或标准化意见文本。2018–2024 七个固定年报期的来源覆盖中位数为 **99.9215%**、P05 为 **99.7799%**，来源完整性门通过。全量清单为 `data/metadata/rich_data/runs/20260716T183642Z_tushare_audit_opinion_full_7a9aa307.json`（SHA‑256 `251589504b721ac303b9b7f9c09b8771b58929c25bc2a5ed6eaf64b5209a977d`）。它仍使用当前上市快照加点时区间，不是历史退市全表，历史幸存者偏差限制保留。

在任何事件扩展、对照字段或收益读取之前，另行冻结无收益协议 `docs/a_share_tushare_audit_opinion_no_return_preregistration.json`（SHA‑256 `5fb77e7060cbd1a03824d015cc33b75ffcf23b3afb5817e60b783e8bcaea3d69`）。协议固定公告后的首个本地交易日才可用，且会话日期不得晚于公告日加 3 个自然日；容量使用 `buyable_main_chinext`、上市满 20 会话、550 天季度质量、固定非重叠三会话网格、Top‑3、每截面至少 6 个名称和两个二值、至少 200 个 cohort 与 5 个年份。只有容量通过，才允许临时构造历史 43 个字段和后来 11 个可同日比较的独立字段，并以至少 100 个日截面、绝对中位 Spearman 小于 0.8 做唯一性门。

唯一一次无收益容量审计 `data/experiments/short_horizon/20260716T192050Z_tushare_audit_opinion_no_return_audit.json`（SHA‑256 `be37f987fd8fd7a29326c1108cf9f311e14aef9d413716f99738e20075917f5f`）在 566 个固定非重叠候选日中，只找到 119 个有任一合格事件的日期、76 个至少有 6 个名称的日期，但只有 **9** 个日期同时包含 0 和 1；有效 cohort 为 **9 / 200**，分布在 2019、2020、2021、2022、2025 五年。容量门失败后程序没有加载 54 个对照字段，没有运行唯一性，也没有读取开盘、未来收盘或远期收益。

因此该候选作为独立三日横截面选股因子正式终止。完整跟踪记录为 `docs/a_share_tushare_audit_opinion_research_record.json`（SHA‑256 `48db650abbd108014eed55f0829f308d9ceb854e113b33d29aa489549fa91d65`）。不得重跑同一快照、反向、扩大事件年龄、选择报告期、映射额外意见文本、降低名称/二值/cohort 门槛、与其他因子组合或进入评分、当前选股、仓位和订单。审计意见仍可在另有治理的系统中作为财报可靠性风险标记，但不能把这种用途解释成已通过本管线的短线因子。下一步返回不读取收益的独立机制发现；新候选必须在来源行或因子值出现前另行冻结合同。

### 必经验收流程

只对一个已收盘交易日和四只代表性股票运行验收。`acceptance` 会保存原始快照，并自动检查字段、非负成交量/成交额、常规交易时段、同日 OHLC/收盘比值，以及与本地日线的成交额和成交量比值：

```bash
python scripts/a_share_rich_data.py acceptance --provider rqdata --date 2026-07-13
python scripts/a_share_rich_data.py acceptance --provider jqdata --date 2026-07-13
python scripts/a_share_rich_data.py acceptance --provider tushare --date 2026-07-13
python scripts/a_share_rich_data.py sync-tushare-events --start 2026-07-13 --end 2026-07-13
```

Tushare 单日事件命令默认请求 3000 积分可覆盖的 `moneyflow,limit-price,stock-st,top-list`，分别对应供应商的 `moneyflow,stk_limit,stock_st,top_list`。`limit-list` 对应 `limit_list_d`，要求 5000 积分，只能显式请求。事件快照保存原始行与逐文件 SHA-256，并记录缺键、越界日期、精确重复和事件键重复；它不会静默去重，也不读取未来收益。只有完整清单存在才表示本次原子下载完成，孤立 Parquet 或无清单目录不是可消费快照。

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

### Tushare 单季度毛利率同比改善验收

审计意见机制因事件横截面容量只有 9/200 而终止后，先做了新的无收益机制重叠审计：[`a_share_three_day_gross_margin_mechanism_overlap_reaudit_20260717.json`](a_share_three_day_gross_margin_mechanism_overlap_reaudit_20260717.json)（SHA‑256 `df2e40d788c91e66de278437379180a7082d7940da8ce46a37ba2b8791164427`）。日频股息率因与既有 PB/分红机制重叠而在请求前拒绝；`fina_mainbz` 主营构成因官方输出没有公告日期且分部文本身份会变化而暂缓。唯一进入验收的候选是 Tushare `fina_indicator.q_gsprofit_margin` 的单季度销售毛利率相对上年同季度变化。

[Tushare 官方财务指标文档](https://tushare.pro/document/2?doc_id=79)说明标准接口需要 2000 积分、每次最多 100 行且只能按单只股票取历史；当前 3000 积分账户可以使用。[官方常见问题](https://tushare.pro/document/1?doc_id=122)明确 `update_flag=0` 为初始数据、`update_flag=1` 为修订数据。因此数据合同 [`a_share_tushare_gross_margin_data_contract.json`](a_share_tushare_gross_margin_data_contract.json)（SHA‑256 `7d0bd69e72aa40a7426ea98444952caae35ce593647123684d376dd12a82d215`）在任何接口行前固定：

- 只请求 `ts_code,ann_date,end_date,q_gsprofit_margin,update_flag`；不请求 ROE、增长率、价格、市值、换手率或收益。
- 只有 `update_flag=0` 的初始行能进入公式；修订行只计数，不用于选值或补缺。
- 因子固定为“本期初始单季度毛利率 − 上年同季度初始单季度毛利率”，单位为百分点，高值方向固定为更好。
- 只在本期初始公告日后的第一个本地交易日可用，最多保持 3 个日历日；缺失不填零。
- 完整历史、容量和唯一性都通过前，不读取开盘、未来收盘或任何收益，也不允许聚合、评分或选股。

离线实现先通过 6 项专项测试；加入来源记录防重跑后，完整 `tests/data_collector_tests` 为 **394 passed, 9 warnings**。唯一一次真实验收使用本地 `launchctl` 中的 Token，对 `600519.SH`、`000333.SZ`、`300750.SZ` 的 2018–2025 报告期各发出一次请求。验收清单为 `20260716T194308Z_tushare_gross_margin_acceptance_270c845f.json`（SHA‑256 `21aafe677009f09ef78ba1fb6b1a5eed52c6c147dac29b2861cdbd05c8324c02`）：共返回 163 行，三只股票分别为 56、53、54 行，均低于 100 行上限；保留 67 条初始季度，观察但完全未使用 96 条修订行；得到 51 个同比事件和 51 个不同值，范围为 −12.795 至 +8.4164 个百分点，重复事件键为 0。发布的五列因子帧不含本期/上年原始毛利率、修订值、凭据、价格或收益。

跟踪验收记录为 [`a_share_tushare_gross_margin_source_acceptance_record.json`](a_share_tushare_gross_margin_source_acceptance_record.json)（SHA‑256 `86d90ecf0c47e97489c358762abf1d2f7a9eb07260fa1aae62d6587eea4e2637`）。同一验收已消费，CLI 会在合同、凭据和供应商访问前拒绝重跑。它只证明权限、五字段结构、初始版本政策和本地公式成立；不证明全市场覆盖、200 个三日 cohort、与 ROE/营收增长/利润增长及其加速度的独立性，更不证明收益。

随后实现了合同固定的 5,451 只来源股票 × 两个报告期切片的原子全量同步，并通过成功发布和触及 100 行上限时删除临时目录的离线测试。唯一全量尝试 `20260716T195414Z_tushare_gross_margin_full_fea987b0_source_failure.json`（SHA‑256 `0089f7e37e08ad802c89f3dffffa7595d689d6b742a0d3d2ed97252295081607`）在完成 528 只股票、1,058/10,902 次调用后，于 `SH600638` 的 `20220101–20251231` 切片发现一行股票代码、公告日、报告期或 `update_flag` 不完整/无效。此前只观察到 28,566 行源数据，分别来自两个切片 16,786 和 11,780 行。程序立即删除完整临时快照，正式分片数为 0、`files=[]`、`final_snapshot_published=false`，且仍为 `price_fields_loaded=[]`、`forward_return_fields_read=false`。

原始响应和源毛利率从未持久化，因此无法确定四个必填键/版本字段中究竟哪一个无效；一次性合同也不授权重新请求该股票来恢复字段级细节。终止记录为 [`a_share_tushare_gross_margin_research_record.json`](a_share_tushare_gross_margin_research_record.json)（SHA‑256 `83b9c930f1456ef748aa54765123d247dc330635f33c33ae8f675395c8cd3d18`）。验收和全量同步均已消费，CLI 会在来源链或供应商访问前拒绝再次全量运行；终止防护加入后，9 项专项测试以及完整数据测试 **397 passed, 9 warnings**。不得删除/填充/推断该行、改字段/日期/切片/公式/方向/修订政策/事件年龄、降低门槛、运行容量/唯一性/收益、聚合/评分/选股/仓位/下单或据此采购 Level‑2。这条机制不进入因子池；后续只能重新审计无收益机制前沿并为新的经济独立候选先冻结合同。

### Tushare 管理层连续性（来源点时门禁终止）

毛利率来源分支终止后，新的无收益机制审计 [`a_share_three_day_management_continuity_mechanism_overlap_reaudit_20260717.json`](a_share_three_day_management_continuity_mechanism_overlap_reaudit_20260717.json)（SHA‑256 `e6b64475b17839cac9e2c8f2177c60509d1d58950127eddb625b9bf128d11946`）先排除了两个近邻：`stk_rewards` 的薪酬偏年度披露、持股与既有所有权机制重叠；`stk_holdertrade` 则直接重叠已经完成的高管公开市场交易分支。唯一冻结的独立候选是管理层公告内的连续性比例。

[Tushare 官方 `stk_managers` 文档](https://tushare.pro/document/2?doc_id=193)给出代码、公告日、姓名、上任日和离任日等字段，并要求至少 2,000 积分；当前 3,000 积分满足权限门槛。[`stk_rewards` 官方文档](https://tushare.pro/document/2?doc_id=194)只作为拒绝候选的来源说明，没有发出请求。数据合同 [`a_share_tushare_management_continuity_data_contract.json`](a_share_tushare_management_continuity_data_contract.json)（SHA‑256 `86d7abc96da30c3e4825f1fcefa6722941b18f86ae3798ad6ad1db676c9323ec`）在账户行出现前固定：

- 只请求 `ts_code,ann_date,name,end_date`，不请求或存储职务、类别、性别、学历、国籍、生日、上任日、简历、薪酬或持股。
- 姓名只在内存中做 NFKC/空白规范化和 SHA‑256 去重；明文与哈希都不写入 Parquet、清单、日志或 Git。
- 同一股票/公告日的唯一身份进入一次分母；只有非空 `end_date == ann_date` 才算当次离任，缺失离任日算未离任。任何非空但不等于公告日的离任日使完整请求失败，不能删除、移动或重新解释。
- 因子固定为 `1 - 离任身份数 / 管理层身份数`，高值更好；只在公告日后的第一个本地交易日可用，最多 3 个日历日。
- 验收、全量来源、无收益容量和唯一性全部通过前，不读取任何价格或收益。

离线实现、隐私聚合、原子发布与一次性保护先通过 6 项专项测试。唯一真实验收原计划对 `000001.SZ`、`600000.SH`、`300750.SZ` 各请求一次 2019–2025 公告记录；第一个且唯一请求 `000001.SZ` 返回 184 行，其中 53 行的完整离任日不等于公告日，因此在身份聚合和因子值之前触发预先冻结的点时门禁。其余两只股票没有请求，临时快照已删除，`files=[]`、正式文件数为 0，姓名、身份哈希、原始响应、价格和收益均未持久化。

失败清单是 `20260716T202120Z_tushare_management_continuity_acceptance_3e1824f5.json`（SHA‑256 `1de603f276d14e77fafc993ed552f709d9c2d35456607c336875e3a70a06d45b`），跟踪终止记录是 [`a_share_tushare_management_continuity_source_acceptance_record.json`](a_share_tushare_management_continuity_source_acceptance_record.json)（SHA‑256 `e42380d3bbf4509c25533fc8f0b9eec7113bdf219b14ab78a86e50ea6aa703a8`）。CLI 现在会在合同、凭据和供应商访问前拒绝重跑。不得请求剩余股票或失败股票来恢复细节、丢弃/填充/移动 53 行、改变字段/身份/日期/公式/方向/事件年龄、创建同机制 v2、运行全量/容量/唯一性/收益、聚合/评分/选股/仓位/订单或据此采购 Level‑2。该结果只说明当前快照不满足冻结的历史点时合同，不说明管理层连续性的收益好坏。

### Tushare ST 确认退出恢复速度（来源连续性终止）

管理层连续性终止后，机制核重记录 [`a_share_three_day_st_recovery_mechanism_overlap_reaudit_20260717.json`](a_share_three_day_st_recovery_mechanism_overlap_reaudit_20260717.json)（SHA‑256 `a916021e4fa6fca094d03cdb6a3360b12c4c4fc09f7e7250dd6f2fde7dc5bc55`）保留静态 ST 成员作为不可排名的持仓资格过滤，并只推进不同的状态转换候选：股票在 `t-1` 属于 ST、在连续 `t` 和 `t+1` 两个本地会话都不属于 ST 后，才在 `t+1` 收盘确认退出；下一会话开盘最早可交易。候选固定为：

```text
tushare_st_recovery_speed = 1 / prior_consecutive_st_sessions
```

此前连续 ST 会话越短，值越高。因子最长保持 3 个日历日；触及 2019 年首个会话的左截断 ST 段必须排除。不得用名称中的 `ST`/`*ST` 字符串、当日静态成员二值、同日首次缺席或事后已知的完整持续时长代替。

[Tushare 官方 `stock_st` 文档](https://tushare.pro/document/2?doc_id=397)说明接口提供历史每日 ST 列表、最低 3,000 积分、单次最多 1,000 行。已有 2026‑07‑13 事件快照中的 211 行仅被零网络复核为权限、结构和字面 `type=ST` 证据；复核只读取 `ts_code,trade_date,type,provider,dataset`，没有读取姓名、`type_name`、转换、持续时长、因子、价格或收益。绑定记录为 [`a_share_tushare_stock_st_source_acceptance_record.json`](a_share_tushare_stock_st_source_acceptance_record.json)（SHA‑256 `e1798221e8758bd2d39ee0f7f611d9c3299b8fcbf824fa9df6e7627c61bd8d0f`），该证据不允许再发一次验收请求。

全量来源合同 [`a_share_tushare_st_recovery_data_contract.json`](a_share_tushare_st_recovery_data_contract.json)（SHA‑256 `cae22e7c7f8bf8c6e14587d5e7f260664c8080c579c52561ef0253d7c8a7ca9e`）固定遍历 2019–2025 的 1,699 个本地交易日，每日只请求 `ts_code,trade_date,type`，调用间隔至少 0.32 秒，每日最多三次尝试，空响应或达到 1,000 行都按来源不完整终止。合法 `.BJ` 行明确排除并计数；年度 Parquet 只保存 `trade_date,instrument,provider`。七年共享隐藏临时根，全部成功才原子发布；开始访问供应商后的任何失败也会删除半成品并留下终止清单。该全量合同只能消费一次。

Token 必须按 [`a_share_tushare_token_setup.md`](a_share_tushare_token_setup.md) 隐藏输入、只验证有无并向单个子进程透传。历史上唯一获准的全量命令曾为：

```bash
python scripts/a_share_rich_data.py \
  sync-tushare-stock-st-membership --allow-large
```

该命令已经永久消费，不能再次运行。唯一尝试按顺序完成 2019‑01‑02 至 2019‑03‑29 的 58 个会话；第 59 次调用对应 2019‑04‑01，Tushare 返回空表。空响应既可能表示完整的零成员列表，也可能表示来源不可用或分区不完整；冻结合同不能区分二者，因此程序没有当成零、没有重试、没有跳过、没有继续请求后续日期。此前共观察 5,066 行，但全部只存在于内存和隐藏临时目录，失败后临时快照被删除；没有年度 Parquet、正式全量清单或可用的 58 会话局部历史。

本地失败清单为 `20260716T205448Z_tushare_stock_st_membership_4fa3ee9c_source_failure.json`（SHA‑256 `58e12ab4b03dafd8f99725c03a8b8988d5df797f98163164cb3e221075640a75`）；跨克隆的终止记录是 [`a_share_tushare_st_recovery_research_record.json`](a_share_tushare_st_recovery_research_record.json)（SHA‑256 `bbed853556c603a154501d59196ab353299b1ce4199a6bbd978197b01d37e067`）。CLI 现在会先验证该记录，再在来源链、Token、供应商或本地运行清单扫描之前拒绝重跑。冻结的 [`a_share_tushare_st_recovery_no_return_preregistration.json`](a_share_tushare_st_recovery_no_return_preregistration.json)（SHA‑256 `50c885bebe89c3e5e8b674afc86b3320639619431c17cad27f9fc4d00474a795`）没有运行：转换、此前连续 ST 会话数、因子值、54 个比较字段、容量、唯一性、价格和收益均未构造或读取。

终止记录、跨克隆保护和原子失败路径通过 12 项 `stock_st` 专项测试；完整数据采集套件为 **414 passed, 9 warnings**。因此这条精确的 Tushare 历史路线正式终止且不向因子池贡献值。不得重请求 2019‑04‑01、把空表解释为无 ST、跳过/填充/插值该日、使用前 58 个会话、混入名称解析或其他供应商、修改日期/字段/确认规则/公式/方向/事件年龄、降低容量/唯一性门槛，或继续收益、聚合、评分、选股、仓位、订单和 Level‑2 采购。它证明的是历史来源连续性失败，不证明该经济机制的收益为正或为负；下一步只能回到不读收益的独立机制发现。

超过 100 个“股票 × 工作日”的付费请求必须显式加入 `--allow-large`，防止误触发多年全市场下载。每次下载按不可变快照写到 `data/raw/a_share/rich/`，并在 `data/metadata/rich_data/runs/` 写入供应商、原始价格口径、请求区间、SHA-256、日内汇总和验收结果。这些文件均由 `data/` 的 Git 忽略规则保护，不应提交或删除来掩盖失败。

### Tushare 自由流通股稀缺度（无收益唯一性门禁终止）

停复牌恢复候选在供应商请求前被容量上界淘汰。旧的“缺少日线行等于停牌”筛查无效，因为 BaoStock 可能保留 `raw_volume <= 0` 的停牌占位行，不能引用该结果。修正后的无收益乐观上界同时把缺少股票交易日和非有限/非正 `raw_volume` 都算作可能停牌，并保留左截断事件、跳过质量和上市门，仍只形成 **181/200** 个固定三交易日非重叠 cohort，虽覆盖 2019–2025 七年但容量失败。该上界没有读取 OHLC、价格、因子、评分或收益，因此无需为这一精确定义的全日停牌时长候选请求 `suspend_d`。完整记录为 [`a_share_three_day_free_float_scarcity_mechanism_overlap_reaudit_20260717.json`](a_share_three_day_free_float_scarcity_mechanism_overlap_reaudit_20260717.json)（SHA‑256 `62c6affbf4ea77a8d85a162f6a641a92bca17dc2d0a661744ed68b8e49b5c3d7`）。

下一项机制独立候选冻结为 `tushare_free_float_scarcity = 1 - free_share / total_share`，高值代表相对总股本可自由交易供给更稀缺。来源只允许 Tushare `daily_basic` 的 `ts_code,trade_date,total_share,free_share` 四个字段；缺失、非有限、非正或 `free_share > total_share` 的行只排除并计数，不得修复、裁剪或填充。[Tushare 官方 `daily_basic` 文档](https://tushare.pro/document/2?doc_id=32)说明该接口最低 2,000 积分、每日 15:00–17:00 更新、单次最多 6,000 行，并提供 `total_share` 与 `free_share` 字段。数据在更新后才视为已知，最早在下一本地交易日开盘使用。合同 [`a_share_tushare_free_float_scarcity_data_contract.json`](a_share_tushare_free_float_scarcity_data_contract.json)（SHA‑256 `a5897cf4bda28bb55e4a0f5c8db6fc328e916c68494e71931a313357d43bc1eb`）已在任何该接口行、因子值、价格或收益出现前冻结。

唯一的 `2026-07-13` 来源验收已经成功并冻结为 [`a_share_tushare_free_float_scarcity_source_acceptance_record.json`](a_share_tushare_free_float_scarcity_source_acceptance_record.json)（SHA‑256 `7f3a929b08ca4da2a95284bca557e3ff3783bbc747cf31e821c5f48a8e2c125d`）。全市场返回 5,524 行；点时可持有股票保留 4,586/4,592，只排除 938 个区间外名称，没有缺失、非正、`free_share > total_share`、重复键或公式误差。验收覆盖率为 99.8693%，因子有 4,568 个不同值。这个入口已永久消费，所有克隆都必须在合同、Token 和供应商访问前拒绝重跑。

验收后、全历史出现前冻结的联合无收益协议为 [`a_share_tushare_free_float_scarcity_no_return_preregistration.json`](a_share_tushare_free_float_scarcity_no_return_preregistration.json)（SHA‑256 `963e8c7d9f41da9c0ea7287399960ee5ecfdf02a1372cada25c6f7b7184f700f`）。唯一的 2019–2025 原子全量请求随后完成全部 1,699 个本地交易日，七个年度分区共 7,098,264 行；有效持有域覆盖率中位数/P5 为 99.6807%/99.1708%，所有 1,699 个交易日都有至少 50 个值。来源、分区字节与内容摘要、逐日点时成员、公式和覆盖率的独立复核记录为 [`a_share_tushare_free_float_scarcity_full_source_record.json`](a_share_tushare_free_float_scarcity_full_source_record.json)（SHA‑256 `2d9855e286e8fd8233e9bafe38301e2381fc4d2ca221a4a69626d580285adc13`）。验收与全量入口都已永久消费，不得再次调用 `daily_basic`、换日期/字段/供应商或删除记录重建。

唯一联合无收益审计 `20260716T221307Z`（SHA‑256 `062a6ef240caeeaac3a39ed811a22d8042e858c1a83485514af2818a1100b70e`）先在完全不加载比较字段或价格的情况下通过容量门：566 个固定三交易日网格中有 540 个质量、上市和因子完整 cohort，要求为 200；2019–2025 各年分别为 56/81/81/80/81/81/80。容量通过后才加载冻结的 2025 年 54 个收盘已知比较字段。结构稀缺度与命名近邻 `free_float_cap_proxy` 的中位日秩相关为 −0.1372，最大绝对中位相关来自 `liquidity_5`，也只有 0.2559，均远低于 0.8；但是协议要求全部 54 个字段各有至少 100 个可比交易日，只有 46 个满足。龙虎榜五项为 0 个合格交易日，股东户数三项只有 39/39/33 个，因此联合唯一性门按预注册规则失败。

终止记录为 [`a_share_tushare_free_float_scarcity_research_record.json`](a_share_tushare_free_float_scarcity_research_record.json)（SHA‑256 `9804ef63da08be5beec4a13460dc8ac0e36fdff3e203dd3f00dc9d148b88a24a`）。失败原因是八个预注册稀疏比较字段证据不足，不是观察到了近义重复；但不能在结果出现后删除稀疏字段、放宽 100 日门槛或把 46 个通过字段当作整体通过。不得重跑同一快照、修改公式/方向/日期/质量/上市/比较目录或阈值，也不得读取下一日开盘、未来收盘、因子收益、聚合、当前评分、选股、仓位或订单。任何针对稀疏比较字段的框架改进只能为未来独立假设事先冻结，不能重开这一已消费分支。

### Eastmoney 资产负债表韧性（收益稳定性与执行门禁终止）

自由流通股稀缺度因预注册的稀疏比较证据不足而停止后，下一条机制先冻结为 `eastmoney_balance_sheet_resilience = 1 - total_liabilities / total_assets`，高值代表总资产中由负债融资的比例更低。机制核重、来源合同分别为 [`a_share_three_day_balance_sheet_resilience_mechanism_overlap_reaudit_20260717.json`](a_share_three_day_balance_sheet_resilience_mechanism_overlap_reaudit_20260717.json)（SHA‑256 `ea3522891cee10446b01ba79ee875bdb9c16ac9ad63470b5894253a4ee0968ca`）和 [`a_share_eastmoney_balance_sheet_resilience_data_contract.json`](a_share_eastmoney_balance_sheet_resilience_data_contract.json)（SHA‑256 `44c3fa5498cbc644f7b7de07c3c53d6d8f7af6a9a367922929d458706133e5a4`）。来源固定为 AKShare 提交 `fcdbf25aa864a218c54864c3f6ab6a2ed19cce28` 中 `stock_zcfz_em` 使用的 Eastmoney `RPT_DMSK_FN_BALANCE` 公共接口，只取代码、公告日、总资产、总负债和供应商资产负债率位置来验式；规范帧只保存代码、报告期、公告日、总资产、总负债、派生因子和供应商。

该来源不需要账号、积分或 `TUSHARE_TOKEN`。唯一的 2025 年报验收清单为 `20260716T224734Z_eastmoney_balance_sheet_resilience_acceptance_a890a7c4.json`（SHA‑256 `08badce50927da1083d684c1614e88ba260d3c2d54acf8d74cf59cf58c65ca8c`），11 页广告数与接收数均为 5,218；在当时有效的 4,581 个主板/创业板名称中得到 4,543 个合法值，覆盖率 99.1705%，派生式与供应商比率的最大误差小于 `5e-13`。跟踪验收记录为 [`a_share_eastmoney_balance_sheet_resilience_source_acceptance_record.json`](a_share_eastmoney_balance_sheet_resilience_source_acceptance_record.json)（SHA‑256 `9a014c7bfa25cfe40f1a5deca0168fe28f5c98f10c1da2bc782366cb15c94baf`）。验收入口已经永久消费。

验收后、全量前冻结的无收益协议为 [`a_share_eastmoney_balance_sheet_resilience_no_return_preregistration.json`](a_share_eastmoney_balance_sheet_resilience_no_return_preregistration.json)（SHA‑256 `fac1c2aefb4c263704e7d93ff7affa6d7e1aa085e1f86dac04c18029ac632a6c`）。唯一的 2019Q1–2025Q4 原子全量快照复用验收分区并请求其余 27 个季度，共 28 个分区、113,916 行、277 次网络调用；季度有效持有域覆盖率最低 93.7483%、中位数 96.6102%。复核记录为 [`a_share_eastmoney_balance_sheet_resilience_full_source_record.json`](a_share_eastmoney_balance_sheet_resilience_full_source_record.json)（SHA‑256 `8c523f2e5b2b14cb46b98a9becf114ef5efab582af2b84482524f6676caf6cc6`）。全量入口也已永久消费。

公共接口提供的是当前可见历史快照，可能包含日后更正，不能声称是不可变的历史版本流。为避免更正日期制造过早信号，状态规则在读取容量、比较字段或收益前冻结为 [`a_share_eastmoney_balance_sheet_resilience_state_materialization_preregistration.json`](a_share_eastmoney_balance_sheet_resilience_state_materialization_preregistration.json)（SHA‑256 `80e00a7991ac52627956eb35a04a10755c88cf769c60298ae02c3332789c9d91`）：每个报告期以该分区最早展示公告日后的第一个本地会话统一激活，激活时清除所有股票的旧报告期值；单只股票仍必须等自己的展示公告日后的第一个会话才有新值；迟到的旧期更正不能覆盖已激活的新期，最大年龄 550 天。该规则偏保守，可能减少容量，但不会把值提前到展示公告日之前。

唯一联合无收益审计 `20260716T231333Z`（SHA‑256 `665399d5df3e2513f4b3095fd3a887d1c3f1e3a2aefdb1ad8490fad229c00967`）通过两道预注册门禁：潜在完整三日非重叠 cohort 为 460/200，覆盖 2019–2025 七年；46 个预先认定为稠密的比较字段全部具有至少 205 个合格日且绝对中位日秩相关均低于 0.8。最近的既有字段是 `free_float_cap_proxy`，绝对中位相关也只有 0.2586。龙虎榜和股东人数八个已知稀疏字段没有加载到这次统计中；这是在新候选及其收益出现前固定的框架规则，不能反过来重开已经终止的自由流通股分支。无收益通过记录为 [`a_share_eastmoney_balance_sheet_resilience_research_record.json`](a_share_eastmoney_balance_sheet_resilience_research_record.json)（SHA‑256 `4ae66604ed4c9a2ea2e8cf9cd9dc05883b8163f6848616dc55280609d1af450b`），它只授权一次单因子诊断，不授权选股。

收益诊断在读取该因子回报前冻结为 [`a_share_eastmoney_balance_sheet_resilience_diagnostic_preregistration.json`](a_share_eastmoney_balance_sheet_resilience_diagnostic_preregistration.json)（SHA‑256 `ffa41a5292aafa8aacbc32427442682c661efd30ca246d71cbb55b906cc52951`）。唯一诊断 `20260716T232128Z`（SHA‑256 `ac66873d1b26d43d12a7dc5609b9072db0e089ddf9473a5365e698c4ce13259b`）有 502 个 cohort，平均 Rank IC 仅 +0.00148、中位数 −0.00472、正 IC 比例 48.01%；2022、2024、2025 年平均 IC 为负。固定 Top‑3 的表面累计值为正，但最大回撤 −58.57%；更保守的执行账本最大回撤 −62.33%，2022–2024 年逐年收益均为负。

默认稳定性审计 `20260716T232453Z_factor_stability_audit.json`（SHA‑256 `e52833128d807e6ced1ec35a58e76d0f9b0f5904d38596ac9e14ebb304b0e779`）与同刻 Top‑3 可行性审计（SHA‑256 `4717d1d0b1df5ff10af7897ecf875cc2f06afb96f6e35327ecc95eafced4c188`）均为 **0/1**。20 万元、每个目标席位 5%、100 股整手、双边 0.1% 滑点和 1% 日成交额参与上限的方案只填到 1,180/1,530 个席位，整手可负担率 77.12%；七年累计仅 +6.40%，2021、2022、2024 年为负，因此附加执行门也失败。

跨克隆终止记录为 [`a_share_eastmoney_balance_sheet_resilience_diagnostic_record.json`](a_share_eastmoney_balance_sheet_resilience_diagnostic_record.json)（SHA‑256 `b7c2888e14fab0dfa4b3f65806ac8dac6e1c46e8390df144c631869ed6da2fcf`）。不得重跑验收、全量、无收益审计、收益诊断或两道通用审计；不得反转成高负债偏好、改变状态规则/公式/年份/阈值/持有期/TopK/成本、只选表现好的年份，或与已经拒绝的因子组合。该因子不进入聚合、当前评分、选股、仓位或订单，也不构成采购 Level‑2 的理由。下一步必须回到不读取收益的机制前沿，先冻结另一条经济独立候选。

### Eastmoney 核心利润一致性（收益与执行门禁终止）

资产负债表韧性在收益与执行门禁终止后，机制核重只推进 `eastmoney_core_profit_consistency = min(营业利润, 利润总额) / max(营业利润, 利润总额)`；营业利润和利润总额必须都为有限正数，高值代表主营经营结果与利润总额更一致、非经营性损益相对更小。Tushare 周转率候选因复用已经失败的 `fina_indicator` 来源路线而排除，现金流自给候选与已终止现金转换机制重叠，利润表费用率集合也不允许在同一响应上事后扫字段。核重记录为 [`a_share_three_day_core_profit_consistency_mechanism_overlap_reaudit_20260717.json`](a_share_three_day_core_profit_consistency_mechanism_overlap_reaudit_20260717.json)（SHA‑256 `ca5ac438068dbf8d1911658ec4fcd72e20196d748ba1cfda4d610a105e96ed82`）。

数据合同 [`a_share_eastmoney_core_profit_consistency_data_contract.json`](a_share_eastmoney_core_profit_consistency_data_contract.json)（SHA‑256 `2ae3be4b134e16681e702171157b48e8be5bc6c1f72aa9cecfc9a285518d7a45`）在来源行前固定 AKShare 提交 `fcdbf25aa864a218c54864c3f6ab6a2ed19cce28` 的 `stock_lrb_em` 适配器和 Eastmoney `RPT_DMSK_FN_INCOME` 公共接口。只从固定位置读取股票代码、公告日、营业利润和利润总额；不保存响应中的其他字段，不需要账号、积分、Cookie 或 `TUSHARE_TOKEN`，也不读取价格和收益。

唯一 2025 年报验收已完成：11 页广告数与接收数均为 5,218，固定的 46 列来源顺序哈希一致；当时 4,581 个点时可持有名称中，4,574 个具有完整身份，3,370 个具有合法因子值，覆盖率分别为 99.8472% 和 73.5647%，不同因子值 3,369 个，公式最大误差 `1.11e-16`。验收记录为 [`a_share_eastmoney_core_profit_consistency_source_acceptance_record.json`](a_share_eastmoney_core_profit_consistency_source_acceptance_record.json)（SHA‑256 `1372ee0af59cf45e4f46659ba05730d0cbaac99232f49464b014e578cd89bf34`）；验收入口已经永久消费。

验收后、全量来源前冻结的协议为 [`a_share_eastmoney_core_profit_consistency_no_return_preregistration.json`](a_share_eastmoney_core_profit_consistency_no_return_preregistration.json)（SHA‑256 `47884d88736a19715bb3a615f9941611309322f9d6f1f1f4a0456ce924fb3943`）。唯一全量同步复用 2025Q4 验收分区并请求另外 27 个季度，共发出 283 次供应商调用，原子发布 28 个分区、92,764 行。季度完整身份覆盖率最低 94.0817%、中位数 96.9569%，合法因子覆盖率最低 65.8051%、中位数 78.2767%；所有公式与文件指纹复核通过。全量记录为 [`a_share_eastmoney_core_profit_consistency_full_source_record.json`](a_share_eastmoney_core_profit_consistency_full_source_record.json)（SHA‑256 `be6d43b7fb1e707898b88180c5d5a180bb4e28620fb8d9c646ef1c58cb7604fb`）。验收和全量入口都已永久消费，生产入口会在任何网络请求前拒绝重跑。

随后唯一联合无收益审计 `20260717T001138Z`（SHA‑256 `26f9c4409b119b6ecc777ce09379c3383c8b17310488f4b7eb29ad719aa664a9`）先按冻结的全局报告期重置规则物化状态，再检查容量与唯一性。得到 304/200 个潜在完整三日非重叠 cohort，覆盖 2020–2025 六年；47 个稠密比较字段全部具备至少 118 个合格相关会话且绝对中位日秩相关低于 0.8。最近字段为已终止的 `eastmoney_balance_sheet_resilience`，绝对中位相关 0.1459；ROE、利润同比和正账面市值比分别为 0.1204、0.1031 和 0.0550。通过记录为 [`a_share_eastmoney_core_profit_consistency_research_record.json`](a_share_eastmoney_core_profit_consistency_research_record.json)（SHA‑256 `753b20b657c5e233dc9948d46f9a29f5cea56b40a7163e757b9018303a4f4c9d`）。该审计没有加载价格或远期收益，也不构成因子有效或可交易的证据；无收益入口已永久消费。

在任何收益读取前，唯一诊断冻结为 [`a_share_eastmoney_core_profit_consistency_diagnostic_preregistration.json`](a_share_eastmoney_core_profit_consistency_diagnostic_preregistration.json)（SHA‑256 `2ba3377fd1c91d470fb07e2ab815048f1331ee38392c4d148fd9c6eec758c289`）：2019–2025、三日非重叠、Top‑3、开/平成本 0.00012/0.00062、质量最大年龄 550 日、最少上市 20 个会话，并同时应用 20 万元、100 股整手、双边各 0.1% 滑点和 1% 日成交额参与上限。

唯一诊断 `20260717T002517Z`（SHA‑256 `fac023aefe695a24a6b86c7f6b605e20f832639828e0dc6020b354a673310ef0`）覆盖 360 个有效 cohort，平均/中位 Rank IC 为 −0.00274/−0.00099，正 IC 比例 48.89%，TopK-minus-BottomK 毛收益均值为 −0.2010%；2021、2022、2023、2025 年平均 IC 为负。固定 Top‑3 扣成本累计 −38.22%、最大回撤 −68.64%、胜率 48.61%，最差三日 cohort 为 −11.25%。执行账本有 370 个完整信号，累计 −43.76%、最大回撤 −68.67%，仅 2025 年为正。

20 万元、每个席位 5%、100 股整手、双边各 0.1% 滑点和 1% 日成交额参与上限的方案只填到 922/1,110 个席位，整手可负担率 83.24%；累计 −6.14%、最大回撤 −13.59%，2020–2024 每年均为负，最大成交额参与率 1.344% 也超过上限。零滑点的 +2.21% 不能推翻冻结的 10bp 主门槛，且 5bp 已转为 −2.44%。

默认稳定性审计 `20260717T002534Z`（SHA‑256 `541ba737149cc53b8905fab4fa40fbbbb5c840ba39bf1e34c5bde3fc2b02a9cd`）与 Top‑3 可行性审计 `20260717T002540Z`（SHA‑256 `1a65deb27529ba1034ab8a9b9aed1f46621ef8dd80338d4d970f0723cd2b7c6f`）均为 **0/1**。跨克隆终止记录为 [`a_share_eastmoney_core_profit_consistency_diagnostic_record.json`](a_share_eastmoney_core_profit_consistency_diagnostic_record.json)（SHA‑256 `970c76e87ee664df2085e305472fc49ea92c5652af8da246f359450ff641907f`）。不得重跑任何该分支入口或通用门禁，不得反向、挑年份、改公式/状态/阈值/持有期/TopK/成本，或与已拒绝因子组合；该因子不进入聚合、当前评分、选股、仓位、订单或 Level‑2 采购理由。下一步回到不读取收益的机制前沿。

### Tushare 业绩快报资产扩张约束（仅冻结验收合同）

核心利润一致性终止后，新的独立机制只选择 `tushare_express_asset_growth_restraint = -growth_assets`：较低的期初以来总资产增长率解释为更克制的资产负债表扩张。营业收入、利润、EPS、ROE、文本摘要及其增长字段全部禁止读取，避免在同一响应上事后筛选盈利类字段。无收益机制核重记录为 [`a_share_three_day_express_asset_growth_mechanism_overlap_reaudit_20260717.json`](a_share_three_day_express_asset_growth_mechanism_overlap_reaudit_20260717.json)（SHA‑256 `94c0c4655918976c3113055d94e573a1bbcaf9cff85ecfc409d3f74e5a593ba4`）。该记录没有观察供应商行、因子值、价格或收益。

数据合同 [`a_share_tushare_express_asset_growth_data_contract.json`](a_share_tushare_express_asset_growth_data_contract.json)（SHA‑256 `517a9e402ecd77f4f09090414ff4e68a45a0af215ff9b200703a4f8ea6d3e177`）固定使用标准 `express` 接口，只请求 `ts_code,ann_date,end_date,growth_assets`，要求账户至少 2,000 积分；当前 3,000 积分不需要 5,000 积分的 VIP 接口。唯一验收固定按 `600000.SH`、`000001.SZ`、`300750.SZ` 顺序各请求一次 2019–2025 历史，任一失败立即停止且不得重试。验收帧只允许保存公告日、报告期、股票、负资产增长率因子和供应商五列，不保存原始响应或原始 `growth_assets`。

目前只完成机制审计与合同冻结，尚未实现验收入口，也没有访问 `TUSHARE_TOKEN` 或供应商。下一步仅允许先实现并本地测试精确的三次请求、严格规范化、原子发布、失败也消费和访问 Token 前的一次性守卫；实现与测试通过后才能执行唯一一次真实验收。验收无论成功或失败都不能直接下载全历史、读取收益、聚合、评分、选股或下单；成功时仍需另行冻结全量来源与无收益协议。
