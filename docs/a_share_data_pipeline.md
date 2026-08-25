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

空数据根首次运行时，默认清单和日线来自东财公开接口；已有日线数据时，`sync` 会先只读检查全部 Parquet 的 `daily_source`，并自动继续唯一已验收来源。当前本地数据因此会继续 BaoStock，而不会静默切回东财。当东财历史接口限流或断连时，可用免费、匿名登录的 BaoStock 日线作为独立恢复源。两者都不需要用户账号、令牌或 Cookie。
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

普通增量刷新不再把 `--source eastmoney` 当作固定默认值：空目录才默认东财；已有且全为 BaoStock 的目录会自动继续 BaoStock。若目录含混合来源、旧文件缺少 `daily_source`，或显式请求的来源与现有唯一来源不同，命令会在创建客户端和网络请求前硬停止。`--force-full` 只表示用**同一供应商**重下所选股票，不能授权在非空目录内换源；因为当前股票池无法证明历史遗留或已退市文件也被覆盖。确需换源时必须在独立干净的暂存根完成全量下载、审计和原子切换，不能原地混写。

### BaoStock 被拒绝时迁移到 Tushare 日线

仓库已有一份独立、不可变的 Tushare 2019–2025 未复权日线镜像，约 799 万行。它与 BaoStock 的 772 万条共同股票日记录中只有 68 条超过冻结阈值的实质差异，跨源分类为 `small`；证据保存在 [`a_share_tushare_baostock_daily_concordance_result.json`](a_share_tushare_baostock_daily_concordance_result.json)。这证明 Tushare 可以作为候选日线主源，但历史镜像本身不能直接覆盖当前 `data/`。

迁移协议 [`a_share_tushare_daily_provider_migration_protocol.json`](a_share_tushare_daily_provider_migration_protocol.json) 固定以下边界：

- 复用并逐文件验证已有 2019–2025 Tushare `daily` 快照，不重复请求这些日线；
- 从 Tushare 补齐 2015–2018、2026 至显式截止日的未复权 `daily`；
- 对所有 2015 至截止日交易日请求 Tushare `daily_basic.turnover_rate`。现有 BaoStock 换手率不得填入 Tushare 价格，否则仍然是混合供应商；
- 通过 `trade_cal` 固定完整交易日历，通过 `stock_basic` 的 L/D/P 三种状态构建现存及历史股票身份；
- 原始日线金额从千元乘 1000 转为元，成交量保持“手”，VWAP 用成交额除以成交股数；随后只用同日已知 `pct_chg` 构建 `close_known_raw_pct_chg_chain_v1`；
- 全过程只写显式外置 staging，不能改写当前 BaoStock 日线、Qlib 或 `latest_run.json`；
- 只有尚未发布 `source_manifest.json` 的同合同中断同步可以按已验证分区续传；源清单一旦完成就绑定截止日、交易日历、股票清单和全部分区哈希，成为不可变快照。要更新到新的截止日必须使用新的 staging 版本，不能向旧快照追加；
- `daily_source=["tushare"]`、价格基准、换手率覆盖、股票池规模和 Qlib 物化全部验收后，也只得到“待显式激活”的 staging；`build` 永远不会自动切换活动数据；
- 激活是单独的本地命令：先复制并逐文件验证冻结白名单内的非日线研究资料，再用仓库根目录的 `.qlib_a_share_data_root` 原子指针切换。它不复制旧日线、旧 Qlib、旧股票池或旧价格基准；新根的全新 `status` 不通过时会精确恢复原指针状态。

Tushare 官方当前说明：未复权 `daily` 每次最多 6000 行、基础积分每分钟可请求 500 次；`daily_basic` 至少需要 2000 积分、每次最多 6000 行；`trade_cal` 与 `stock_basic` 也从 2000 积分起。迁移器仍使用更保守的聚合 0.22 秒调用间隔，并把 6000 行视作可能截断而拒绝。接口文档分别见 [日线](https://tushare.pro/document/1?doc_id=27)、[每日指标](https://tushare.pro/document/2?doc_id=32)、[交易日历](https://tushare.pro/document/2?doc_id=26) 和 [股票列表](https://tushare.pro/document/1?doc_id=25)。

先执行零网络、零写入预检：

```zsh
python scripts/a_share_tushare_daily_migration.py preflight \
  --staging-root /Volumes/DIsk/qlib-a-share-tushare-daily-staging \
  --through-date <latest-completed-session>
```

预检只有在以下条件同时成立时才返回 0：参考快照及跨源证据指纹正确、当前活动日线仍是唯一来源、截止日不晚于安全收盘边界、外置磁盘至少有 5 GiB 空间，并且当前进程能读取 `TUSHARE_TOKEN`。未就绪仍输出诊断 JSON，但退出 2，不创建 staging 根、不请求供应商。

Token 可见后，显式批准源请求，再构建：

```zsh
python scripts/a_share_tushare_daily_migration.py sync-source \
  --staging-root /Volumes/DIsk/qlib-a-share-tushare-daily-staging \
  --through-date <latest-completed-session> \
  --allow-network

python scripts/a_share_tushare_daily_migration.py build \
  --staging-root /Volumes/DIsk/qlib-a-share-tushare-daily-staging

python scripts/a_share_tushare_daily_migration.py status \
  --staging-root /Volumes/DIsk/qlib-a-share-tushare-daily-staging
```

每个 `daily` / `daily_basic` 股票日分区都有独立字节和内容哈希；在源清单尚未完成时，同一协议、同一截止日的中断可从已验证分区继续，任何已完成分区变化都硬停止。`source_manifest.json` 发布后，再用同一截止日运行是只做本地深度复核的幂等操作，不请求供应商；换截止日则在任何供应商请求前拒绝，必须换一个全新的 staging 根。源同步失败会原子写入 staging 内的 `latest_failure.json`，保留已完成分区并明确 `active_root_mutated=false`。

`build` 按年份流式重分区、按股票重建完整收益链，再在 staging 内调用日线管线做价格基准审计和 Qlib 物化。若使用 `build --skip-materialize`，之后可以在同一 staging 继续普通 `build`，但迁移器会先重新核对源清单、构建清单、股票池哈希、至少 5,000 个 Tushare 单源文件和价格基准，任一变化都拒绝续跑。最终清单状态必须是 `accepted_staging_pending_explicit_crash_safe_activation`；未通过下面的独立激活预检和显式原子激活前，不得手工复制文件、删除当前 `data/`、改符号链接或把 staging 交给 Candidate49。

只有看到上述验收状态后，才运行零复制、零指针写入的激活预检。`QLIB_A_SHARE_DATA_ROOT` 环境覆盖必须为空，否则本地指针无法成为唯一活动根：

```zsh
env -u QLIB_A_SHARE_DATA_ROOT \
  python scripts/a_share_tushare_daily_migration.py activation-preflight \
  --staging-root /Volumes/DIsk/qlib-a-share-tushare-daily-staging
```

预检输出 `ready=true` 后，显式确认原子激活，再用一个全新进程读取活动状态：

```zsh
env -u QLIB_A_SHARE_DATA_ROOT \
  python scripts/a_share_tushare_daily_migration.py activate \
  --staging-root /Volumes/DIsk/qlib-a-share-tushare-daily-staging \
  --confirm-activation

env -u QLIB_A_SHARE_DATA_ROOT \
  python scripts/a_share_data_pipeline.py status
```

激活前会把 `derived`、`experiments`、`exports`、`handoffs`、事件、基本面、rich data 和 `metadata/rich_data` 中尚未存在的文件复制到 staging；同路径不同哈希会硬停止。激活意图在指针更新前落盘，切换后的新进程必须看到 Tushare 单一日线、通过的价格基准及正确日历截止日；否则自动恢复原先“存在或不存在”的指针状态，并留下失败记录。旧 BaoStock 根始终保留，不在同步、构建、验收或激活中改写。Candidate49 的活动日线、Qlib 和未来基本面默认路径会跟随该指针，但仍必须先通过对应目标会话的激活后预检，不能因为换源成功而回填历史候选收益、直接评分或下单。

一旦活动根已经正式切换为 Tushare，普通 `a_share_data_pipeline.py sync` 会在任何客户端或网络请求前拒绝原地更新。后续日更仍须构建一个新的隔离 Tushare staging 版本、验收后再执行可回滚切换；不能重新用 BaoStock 或 Eastmoney 填一部分股票/字段。

从第二个 Tushare 版本开始，不需要再向供应商请求从 2015 年开始的全部 `daily_basic`。先解析当前活动根，再把它已经验收的源会话检查点播种到一个带日期的新 staging：

```zsh
ACTIVE_ROOT="$(env -u QLIB_A_SHARE_DATA_ROOT \
  python scripts/a_share_data_pipeline.py data-root)"
NEW_ROOT="/Volumes/DIsk/qlib-a-share-tushare-daily-<YYYY-MM-DD>"

env -u QLIB_A_SHARE_DATA_ROOT \
  python scripts/a_share_tushare_daily_migration.py seed-refresh \
  --parent-root "$ACTIVE_ROOT" \
  --staging-root "$NEW_ROOT" \
  --through-date <latest-completed-session>

python scripts/a_share_tushare_daily_migration.py preflight \
  --staging-root "$NEW_ROOT" \
  --through-date <latest-completed-session>
```

`seed-refresh` 不读取 Token、不访问网络，也不复制父根的日线成品、Qlib 或股票池。它先完整验证活动父根的 Tushare 验收清单和源清单，再用独立文件复制父根已有的 `daily` / `daily_basic` 会话分区；硬链接被禁止，复制后逐文件核对字节哈希和表内容哈希。开始复制前会写入带父根、父截止日和目标截止日的 intent；中断后只能在这些绑定完全相同时继续，已完成副本变化会硬停止。完整 seed 清单发布后，`sync-source --allow-network` 仍会重新请求交易日历和 L/D/P 股票列表，但只请求父截止日之后缺少的 `daily` 与 `daily_basic`。父根和其源清单始终只读。

播种只减少重复的供应商请求，不放宽构建门禁。后续仍按上文运行 `sync-source → build → status → activation-preflight → activate`；`build` 会从完整源会话重新生成每只股票的价格链，并完整重建、审计 Qlib。第一份 Tushare 活动根无法从 BaoStock 播种，仍必须走前面的初始迁移流程。若 seed 尚未完成、父根已不再是活动根、目标截止日不晚于父截止日、父清单被改动或 staging 已存在构建/验收状态，命令都会在任何供应商请求前拒绝。

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
  --start-year 2019 --end-year 2026 --through-report-date 2026-06-30
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

季度财报的 `--through-report-date` 必须设为最新已经结束的自然季度；例如 2026 年 7 月可截止到 2026‑06‑30，但不能请求 2026‑09‑30。同步器会在创建供应商会话前计算最新已结束季度：显式截止日晚于该季度会硬停止；年份范围跨入未结束季度但省略 `--through-report-date` 也会硬停止。完成清单同时记录 `through_report_date` 和 `latest_completed_quarter_end_at_sync`。业绩预告使用同名参数时，可使用已出现预告公告的报告期，但不能把尚未公告的缺失值解释成负面信号。季度全历史请求较长时，可以按不重叠年份范围分别下载到临时 Parquet，再显式合并；合并前的分片不能单独作为研究数据。最终合并会按股票与报告期保留最早公告，并重新写入完整清单：

```bash
python scripts/a_share_short_horizon_factor_research.py sync-quarterly-fundamentals \
  --start-year 2019 --end-year 2020 --output data/raw/a_share/fundamentals/quarterly_2019_2020.parquet
python scripts/a_share_short_horizon_factor_research.py sync-quarterly-fundamentals \
  --start-year 2021 --end-year 2022 --output data/raw/a_share/fundamentals/quarterly_2021_2022.parquet
python scripts/a_share_short_horizon_factor_research.py sync-quarterly-fundamentals \
  --start-year 2023 --end-year 2024 --output data/raw/a_share/fundamentals/quarterly_2023_2024.parquet
python scripts/a_share_short_horizon_factor_research.py sync-quarterly-fundamentals \
  --start-year 2025 --end-year 2026 --through-report-date 2026-06-30 \
  --output data/raw/a_share/fundamentals/quarterly_2025_2026q2.parquet
python scripts/a_share_short_horizon_factor_research.py merge-quarterly-fundamentals \
  --input data/raw/a_share/fundamentals/quarterly_2019_2020.parquet \
  --input data/raw/a_share/fundamentals/quarterly_2021_2022.parquet \
  --input data/raw/a_share/fundamentals/quarterly_2023_2024.parquet \
  --input data/raw/a_share/fundamentals/quarterly_2025_2026q2.parquet
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

## Windows、macOS 与 Linux

日频管线、丰富数据接入和纸面监控现在共用跨平台进程锁，并按中国标准时间判断
已完成交易日。Windows 虚拟环境、凭据注入与任务计划程序配置见
[a_share_cross_platform_usage.md](a_share_cross_platform_usage.md)。各平台使用相同 CLI，
不维护独立的 Windows 脚本副本。

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

### Campaign113：正式交易所监管行动零行来源合同

2026-08-09 的 Campaign113 在任何程序化来源行、因子公式、比较值、价格或收益之前，冻结了沪深交易所正式监管措施/纪律处分的双交易所来源合同 `docs/a_share_official_exchange_enforcement_source_contract_20260809.json`。它只允许证券代码、监管类型/家族、处理日期和官方文档 href 身份；名称、涉及对象、事由、标题与正文不得进入标准化或因子逻辑。无日内发布时间时，事件只能在处理日期之后的首个本地交易日收盘可用，随后下一交易日开盘进入三日持有协议。

该合同不是因子注册，也不授权联网验收。下一阶段必须先用纯合成 fixture 实现有限标签 schema 角色解析、严格代码/日期/官方链接规范化、精确重复折叠与冲突硬失败，并冻结实现/测试哈希；然后在来源行之前另行冻结唯一公式、方向、事件窗口、缺失和值域。`top_list`、`suspend_d`、增减持/回购与 CNInfo 诉讼分支的旧终止记录保持不变，不能作为这一来源的字段或救援路线。

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

BaoStock SDK 无需凭据；其余来源只有在已取得对应授权后才配置环境变量。完整的配置、只检查“有/无”、单命令透传、清除和轮换步骤见 [`a_share_tushare_token_setup.md`](a_share_tushare_token_setup.md)。macOS 的 Tushare Token 使用隐藏输入，不能把真实值直接写在命令中：

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

### Tushare CCASS 参与者广度（账户权限验收终止）

在前沿仍为 43 个历史因子、7 个关联稳定性通过、TopK 通过 0、双门交集 0 后，机制核重记录 `docs/a_share_three_day_ccass_participant_breadth_mechanism_overlap_reaudit_20260721.json`（SHA‑256 `875939121554c84fb0020fe7e53e55118e401a7d24c46b09fc2df8d359c51d4c`）只推进一个尚未读取价格或收益的候选：`tushare_ccass_participant_breadth_change_3 = hold_nums_t / hold_nums_t_minus_3_local_sessions - 1`，高值方向固定为更好。这里的 `hold_nums` 只表示持有该证券的 CCASS 结算参与者数量；合同不允许读取参与者身份、名称、持股数量、`shareholding`、`hold_ratio`、价格、市值或收益。

数据合同 `docs/a_share_tushare_ccass_participant_breadth_data_contract.json`（SHA‑256 `97892a79c0ad650c2f4dfeceb993da9d3624105d79095e49bfa60453e3586402`）在任何权限结果、来源行或因子值出现前冻结。它只请求 `trade_date,ts_code,hold_nums`，按每页 5,000 行做未知总数分页；唯一验收固定为 2019、2024、2025 和最新本地 2026 四个四会话锚点，共 16 个会话，并要求逐日不少于 50 个点时来源股票、每锚点不少于 20 个连续四会话可持有股票、沪市主板/深市主板/创业板运输证据，以及最新锚点的科创板证据。验收快照最多只能有 `trade_date,instrument,ccass_participant_count,provider` 四列，公式只在内存复算。

在 222 项离线数据采集测试通过后，唯一命令 `acceptance-tushare-ccass-participant-breadth` 发出第一项冻结请求：2019‑01‑02、offset 0。当前 3,000 积分 Token 被 Tushare 明确拒绝为没有 `ccass_hold` 接口访问权限，因此程序没有取得任何来源行，完成会话数为 0，规范行和因子值均为 0，没有发布 Parquet，并删除了隐藏临时目录。失败清单 `data/metadata/rich_data/runs/20260721T085955Z_tushare_ccass_participant_breadth_acceptance_be044cb1.json` 的 SHA‑256 为 `a2a4bf44ce3a2129143be0554b575b12a5425f6960191f1f438ba43564c06f09`；跨克隆终止记录为 `docs/a_share_tushare_ccass_participant_breadth_source_acceptance_record.json`（SHA‑256 `54a4d18096b14797e351d9380bcf9e1e6a6bf943cacd984fe674f51353c1615f`）。Token 值没有被输出、哈希或持久化，价格和未来收益均未读取。

该一次性验收已永久消费。不得换日期、重试、购买权限后沿用同一合同、把权限失败解释为来源为空或因子无效，也不得继续全历史、容量、唯一性、收益、聚合、当前评分、选股、仓位、订单或 Level‑2。程序必须先校验上述终止记录并在合同、本地上下文、Token 和网络之前拒绝。这个结果只证明当前账户无接口权限，不证明 CCASS 的沪深覆盖、历史容量、独立性或预测能力；下一步只能重新冻结一个经济机制独立且当前已授权的无收益候选。

后续零网络前沿审计 `docs/a_share_three_day_post_ccass_authorized_source_frontier_audit_20260721.json`（SHA‑256 `61804bfb535954ae517aba1e67791dc8371ce68cf384219fe8a08c6ded6dc499`）没有推进新候选。券商月度金股和 TDX 板块成分均需 6,000 积分；同花顺概念资金流需 5,000 积分；深证互动易和全量公告需要单独权限。即使忽略权限，月度金股在 2019–2025 的硬上限只有 84 个独立月份，低于 200 个三日 cohort；互动易只有深圳路线；板块/概念资金流分别与已终止的行业广度和分类资金流机制重叠。当前 120 分可用的 `stock_company` 只是当前静态快照，不能无泄漏地重建 2019–2025；标准财务报表和限售解禁则分别是已终止来源字段扫描与已完成失败机制的供应商复制。审计没有请求任何接口行、因子值、价格或收益。本机同时未发现 `xtquant` Python 包或常见 QMT/XTQuant 本地路径；这只表示当前 macOS 工作区没有可直接接入的券商分钟运行时，不代表用户的其他 Windows/QMT 环境不存在。当前下一条可执行路径是由用户暴露已有合法的全市场 1 分钟 OHLCV/成交额导出后另冻合同，或等待 BaoStock 按既有规则出现可验证恢复；不为重试 CCASS 或复制淘汰机制追加购买。

### 官方交易所问询负担（来源元数据门禁终止）

独立机制审计 [`a_share_three_day_official_exchange_inquiry_burden_mechanism_overlap_reaudit_20260721.json`](a_share_three_day_official_exchange_inquiry_burden_mechanism_overlap_reaudit_20260721.json)（SHA‑256 `8b9ee95c5a19184053aa0646bbd4a700a03488da65a9c35e20bfc82325bf4de0`）只推进沪深交易所同时可复现的问询韧性；两所合同 [`a_share_official_exchange_inquiry_burden_data_contract.json`](a_share_official_exchange_inquiry_burden_data_contract.json)（SHA‑256 `6e9912ebd6a58291a91d6773c1ef4d241877dd33eea6a95180372f8c4bd47a51`）在任何来源行、文档身份、因子值、价格或收益前冻结。唯一候选为 `(1 + 距最近已生效问询的自然日数) / 最近三自然日内有效的唯一问询数`，高值固定为更好；必须同时通过 SSE 和 SZSE，且禁止读取或保存标题、公司名、问询类型、正文和回复文本。

唯一验收从冻结顺序的 SZSE `main_wxhj` 元数据探针开始，响应没有且仅有一个可见报表，因而在默认数据行规范化、SSE 请求、因子值、价格和收益之前终止。失败清单 `data/metadata/rich_data/runs/20260721T102937Z_official_exchange_inquiry_burden_acceptance_3c38881b.json` 的 SHA‑256 为 `e73fef90eda1467ec992be8e0d00c890422110542b4b74f84ff7958b5eaf656b`；跨克隆终止记录为 [`a_share_official_exchange_inquiry_burden_source_acceptance_record.json`](a_share_official_exchange_inquiry_burden_source_acceptance_record.json)（SHA‑256 `a2c5d1c6daa11cf73d29843eb36dffdacf3d27ff07802e5d222fe9e14f3f5cdf`）。不得重跑、任选一个报表、改标签、检查默认行来倒推结构、只用一个交易所、第三方补齐或继续全量/容量/收益/选股。这是来源元数据合同失败，不是因子收益结论。

### QMT / XtQuant Level‑1 一分钟导出桥（购买前已选路径，现保留为备用）

在交易所问询分支终止后，零行情前沿记录 [`a_share_three_day_post_inquiry_qmt_minute_source_frontier_audit_20260721.json`](a_share_three_day_post_inquiry_qmt_minute_source_frontier_audit_20260721.json)（SHA‑256 `7913899f53e6e87d597929573fe9788add0fa9604c6b79999e7ad7057ed340db`）曾选择已有合法 MiniQMT/XtQuant 环境的 Level‑1 一分钟导出作为下一条数据路径；没有新建或改写因子。冻结合同 [`a_share_qmt_xtquant_one_minute_export_data_contract.json`](a_share_qmt_xtquant_one_minute_export_data_contract.json)（SHA‑256 `a5ccb8bb4a7356a2c655d3cfd3ffc72365cc93c19198476110fb793c2fa71399`）固定 `2026-07-13` 与 `600519.SH/000001.SZ/300750.SZ/688981.SH`，只允许 `time,open,high,low,close,volume,amount,suspendFlag`、`1m`、不复权、禁止填充。账户、Token、Cookie、客户端路径、机器名、用户名、交易 API、Level‑2 与 QMT 原始缓存都不得进入导出包。用户随后单独购买并启用了 Tushare 历史分钟权限，且真实四股验收已经通过，因此 QMT 不再是当前首选，只作为不改合同的备用来源保留。

Tushare Token 配置完成后，购买前零行情权限复核 [`a_share_three_day_tushare_minute_permission_frontier_audit_20260721.json`](a_share_three_day_tushare_minute_permission_frontier_audit_20260721.json)（SHA‑256 `61e2325c0199b35d7e10ec97f4d71f973786b925b6e0f187a0e4de8bb4068959`）确认：3,000 积分本身只覆盖积分接口，不能授权 A 股历史分钟。该记录当时没有消耗试用调用、没有读取任何 Tushare 分钟行，并基于尚未购买的事实保留 QMT 优先。它现在只作为购买前审计保留；不能再用其中“未授权”的结论覆盖用户后来单独购买并通过真实验收的新证据。

候选 49 登记时的前序权威迭代状态写入 [`a_share_three_day_iteration_status_20260725_future_only.json`](a_share_three_day_iteration_status_20260725_future_only.json)（SHA‑256 `d44e1cb3707cce194eed37e99cc90f865396b1de8c35e02a393a2a243d973466`）。它不改写、只以前序指纹连接候选 48 状态 [`a_share_three_day_iteration_status_20260725.json`](a_share_three_day_iteration_status_20260725.json)（SHA‑256 `355b992452b73607034a182699d4fff337905e484229441e7ae138db1ffdefef`），后者再连接候选 47 状态和完整旧账本。48 条主机制均已终止，TopK 通过数、双门禁通过数和聚合候选数仍全部为 0；另有且仅有一个**非终止、纯前瞻**候选 49。聚合、评分、当前选股、定仓、下单和 Level‑2 采购仍全部为 `false`。

为控制已经反复查看 2019–2025 三日收益造成的选择偏差，后续分钟因子执行 [`a_share_three_day_future_only_minute_research_policy_20260725.json`](a_share_three_day_future_only_minute_research_policy_20260725.json)（SHA‑256 `52ca8bfa7201509fe891d0af3d1c87aeebd64e47e6ec6641e897849411df408c`）：历史区间只允许验证公式、覆盖/容量和机制唯一性，不得再读取历史日线价格或三日未来收益。候选 49 的最早有效信号日是注册之后首个已验收的本地交易日，且不得早于 **2026‑07‑27**；满 200 个已完成信号日才执行完整门禁，60 个已完成信号日仅允许按预登记条件提前否决，绝不允许提前晋级。在候选 49 形成终局记录前不得启动候选 50。

等待候选 49 前瞻样本时只允许维护未激活的机制储备。原队列 [`a_share_three_day_inactive_mechanism_scouting_queue_20260726.json`](a_share_three_day_inactive_mechanism_scouting_queue_20260726.json)（SHA‑256 `00565a87b5eb4241de3dfdd24f96ef78756fb286655969351ec966bbe32afad3`）保留前三个概念及顺序；追加记录 [`a_share_three_day_inactive_mechanism_scouting_queue_delta_20260726.json`](a_share_three_day_inactive_mechanism_scouting_queue_delta_20260726.json)（SHA‑256 `60f280cfecbd390a4fb6388eb3c5a63a507506b542aeba937f60d583cc717835`）只增加零收益成交吸收、午间重定价持续性、方向性价格冲击不对称三个经济问题。追加项的候选编号、公式和方向全部为空，没有读取外置分钟/日线分区、候选值、比较值、价格或收益；可用字段严格来自清洗协议的 `datetime,symbol,provider,close,volume,amount`，开高低继续禁止。Candidate49 终止或完成 200 个信号前，任何队列项都不得实现、计算或越过原队列顺序；满足条件后也只能先对最早仍独立的一项做新的无数值机制核重，再在任何数值前冻结一个公式和方向。

### 三日策略历史滚动研究主线（2026‑07‑27 方法更新）

2026‑07‑27 的用户研究指令明确纠正了“把逐日新增样本作为唯一迭代引擎”的做法。新的正式政策为 [`a_share_three_day_historical_walkforward_research_policy_20260727.json`](a_share_three_day_historical_walkforward_research_policy_20260727.json)（SHA‑256 `38426d6161b9bfed323c58caba18feca668b8c9d53e294951a8ba90c01a798bb`），新的权威状态为 [`a_share_three_day_iteration_status_20260727_walkforward.json`](a_share_three_day_iteration_status_20260727_walkforward.json)（SHA‑256 `75e639c4b8579983bfcda8da19c221d018b7b62cd68fac9e94822f6c3ed73267`）。新状态只以前序路径和 SHA‑256 推进 2026‑07‑25 的未来专用状态，不改写候选 49 的登记、账本或历史证据。

研究自此采用双轨制：

- **历史滚动研究是主要迭代引擎。** 2019‑01‑01 至 2023‑12‑31 是开发与内部走步区间，固定三组扩展折：2019–2020 训练/2021 验证、2019–2021 训练/2022 验证、2019–2022 训练/2023 验证。允许在这些开发折内研究经济上有动机的因子、方向、窗口、变换、阈值、过滤、特征子集、组合、模型与权重。
- **2024‑01‑01 至 2025‑12‑31 是一次性历史 campaign 回测区间。** 打开之前必须冻结有限候选库、父子版本、完整搜索空间、存活规则、组合/拟合方法、成本、门禁以及数据和代码指纹；整个 campaign 只打开一次，并记录所有候选结果。看到结果后产生的任何新公式、参数、子集、过滤或权重都是新探索版本，不得再把同一 2024–2025 区间称为未见或纯净测试。
- **2026 年以后只承担真正前瞻确认与衰减监测。** 逐日数据不再负责主要因子发现，也不再阻塞离线历史研究。离线研究不需要等待目标交易日 16:30；只有 Candidate49 当日来源到信号流程仍必须等待同日收盘缓冲并通过原有预检。

三日标签在每个训练、验证和回测边界都必须做泄漏清除：边界前清除最后三个本地信号会话，且只有 `t+1` 开盘和 `t+3` 收盘均完整落在同一分区的信号才能进入该分区。关联比较继续使用冻结的非重叠三日网格；可执行收益必须用同一共享、现金受限、允许持仓重叠的组合重放，不得把独立交易收益简单相加。

所有历史尝试必须进入追加式试验账本。每个公式、方向、参数、窗口、过滤、子集、组合、模型和基础设施失败都要记录唯一 ID、父版本、campaign、数据/代码/执行协议指纹以及训练、验证和锁定回测结果；不能只保留最佳版本。2019–2025 已被此前 48 条机制和大量变体反复观察，因此新切分只能称为“历史已暴露的准样本外证据”，不能追溯性包装成纯净留出。历史结果可以用于排序、否决和估计稳健性，但不能直接授权当前评分、选股、仓位或订单。

旧的 48 条终止记录保持终止且不得改写；其公式定义只有在一个新 campaign 事前冻结完整复用库和搜索空间时，才可作为历史研究特征参与组合。旧结果不会因此被重新标记为通过。Candidate49 仍是唯一活动的前瞻候选，禁止回填它的历史收益、信号、执行或里程碑；但 Candidate49 不再阻塞新的历史因子和组合研究。历史试验不等于 Candidate50 前瞻激活，也不会创建第二条未来账本；Candidate49 活跃期间仍不启动第二个前瞻候选。

首轮有限搜索已经按上述流程完成，结果记录为 [`a_share_three_day_walkforward_campaign_001r1_research_record.json`](a_share_three_day_walkforward_campaign_001r1_research_record.json)。原始预注册在任何试验或收益框架形成前暴露了一个字段级清洗覆盖层合并错误；失败被保留在原台账，且只允许把覆盖层有效补充键做确定性外并。修复版重新绑定执行器指纹和新输出根后，完整运行了 8 个冻结因子、8 个单因子加 84 个两因子权重组合，共 92 项 2019–2023 扩展走步试验；所有试验均入追加式哈希链，按冻结规则选出 8 个锁箱幸存者。

2024–2025 锁箱随后只打开一次，8 个幸存者全部记录，但最终门禁通过数为 0。日内收益方差熵单因子是最接近完整门禁的版本：2024–2025 合并 Rank IC 为正，20 万元、双边 10bp 试算收益为正且 2024/2025 分年均为正，但标准化最大回撤为 `-20.0363%`，低于冻结的 `-20%` 下限，不能事后放宽。低已实现波动与收益方差熵的等权组合在同一成本设定下合并收益 `+4.0030%`、两年分别为正，但标准化最大回撤 `-20.4841%`，同样拒绝。其余版本主要失败于 10bp 成本后的分年稳定性、回撤或关联门禁。该负结果不启动当前评分、选股、定仓或订单；2024–2025 自此已暴露，后续新探索必须建立新 campaign，且不能再把该区间称为未见锁箱。

只读完成审计器 `python scripts/a_share_three_day_walkforward_completion_audit.py` 会重新验证冻结输入指纹、92 项完整目录、三组扩展折、幸存者确定性重放、100 条哈希链、一次性锁箱顺序、全部结果留档、Candidate49 两本零条目账本、Candidate50 未启动以及无当前评分/订单产物。完成审计记录为 [`a_share_three_day_walkforward_campaign_001r1_completion_audit.json`](a_share_three_day_walkforward_campaign_001r1_completion_audit.json)，15 项要求全部通过；79 项聚焦回归和完整 `tests/data_collector_tests` 的 1,145 项测试均通过。原始预注册中的 `frozen_at` 存在一个保留的书写时间不一致；审计不使用该字段证明先后，而使用已被无收益基础设施失败记录绑定的原文件哈希，以及修复版 `11:51Z` 预注册早于 `11:52:37Z` 首条开发结果、幸存者记录早于锁箱意图的完整链路。

第二轮有限搜索已由 [`a_share_three_day_walkforward_campaign_002_preregistration.json`](a_share_three_day_walkforward_campaign_002_preregistration.json)（SHA‑256 `2f9977f020d4b8bd06b7968e0cfb29287d13e87cf1510881f3acbbe83050d511`）在任何该轮结果读取前冻结。它没有针对 Campaign001 的近失版本局部调参，而是完整复用全部 8 个旧研究特征，并对 28 个无序因子对统一应用几何均值、调和均值和较小分位数三种非线性一致性算子，共 84 项；旧终止结论保持不变，Candidate49 明确排除。2019–2023 仍使用原三组扩展折、每个边界清除 3 个信号会话、`t+1` 开盘/`t+3` 收盘完整落区以及相同共享组合和成本。验证质量由报告项升级为硬门槛：三折方向一致性、10bp 试跑、最差回撤不低于 `-25%`、整手/成交额/未决持仓可执行性，以及 2019–2023 合并 20bp 压力收益为正都必须同时通过。

该轮 84/84 项均完整写入追加式哈希链，基础设施失败为 0；43 项通过可执行性检查，但质量门槛通过数和最终幸存者均为 0。所有 84 项的五年 20bp 压力试跑都不为正，80 项还触发最差验证期回撤门槛；三种算子的平均 20bp 收益约为 `-20.42%/-20.39%/-20.06%`，平均最差验证期回撤约为 `-41.08%/-41.00%/-39.97%`。最接近的收益方差熵与尾盘 VWAP 比组合在调和/几何算子下都有 3/3 个验证年平均 IC 与标准化收益为正，但最差回撤约为 `-30.49%/-30.04%`，五年 20bp 试跑仍为 `-10.63%/-11.14%`，因此不能放宽门槛救援。

因为开发幸存者为 0，2024–2025 的“已暴露压力复验”没有打开、没有读取该区间收益，也没有生成压力试验条目。统一结果记录为 [`a_share_three_day_walkforward_campaign_002_research_record.json`](a_share_three_day_walkforward_campaign_002_research_record.json)（SHA‑256 `9abd467e8c110e3c30ffd78ed76e921d5119d4442ac9b09aa22de6ea4ee5521d`）。只读审计命令 `python scripts/a_share_three_day_walkforward_campaign002_completion_audit.py --compact` 会重放完整目录、84 条台账、幸存者规则、零压力读取、Campaign001 与 Candidate49 独立状态以及无评分/选股/仓位/订单边界；12 项要求全部通过。25 项聚焦回归与完整数据采集测试 1,155 项也全部通过，9 条提示仅为既有 pandas 性能/未来行为警告。

下一轮不能修改 Campaign002。其新假设必须作为 Campaign003 在数值前另行冻结：用原低已实现波动方向分位作为风险资格门，对其余 7 个完整信号库统一尝试保留 75%/60%/45% 名称的三个固定门槛，并在“门内主信号排名”与“75% 主信号 + 25% 低波动”两种固定评分方式下形成 42 项完整搜索。这个方向针对本轮普遍的回撤和成本失败，而不是只修改一个近失组合；Campaign003 仍必须记录所有尝试、保持 2019–2023 开发折，并把 2024–2025 明示为已暴露且在幸存者冻结前不得读取。

Campaign003 已按独立预注册 [`a_share_three_day_walkforward_campaign_003_preregistration.json`](a_share_three_day_walkforward_campaign_003_preregistration.json)（SHA‑256 `7c2f9339aabe093bd40acde3f352ac147f30f119aa5a341252df992788be05c0`）完成。精确定义不是先筛选再沿用原全截面分位：每个交易日先要求主信号与低波动方向分位均有限且为正，再按 `>=0.25/0.40/0.55` 保留约 75%/60%/45% 名称；随后在门内分别对主信号和低波动分位重新做平均百分位排名，最后使用纯主信号门内排名或 `75%` 主信号加 `25%` 低波动两种固定评分。7 个主信号、3 个门槛、2 个评分模式共 42 项，任何数值出现前已同时冻结。

2019–2023 的 42/42 项均完成并进入追加式哈希链，基础设施失败为 0；21 项通过可执行性检查，但验证质量门槛与最终幸存者仍均为 0。全部 42 项的五年 20bp 压力试跑都为负，37 项触发最差验证期回撤门槛。纯主信号门内排名与 75/25 混合的平均 20bp 收益分别为 `-18.66%/-21.31%`，平均最差验证回撤分别为 `-35.87%/-34.35%`：把低波动再加入评分略微改善平均回撤，却进一步削弱成本后收益。60% 保留门槛的平均 20bp 结果最不负（`-19.28%`）；45% 门槛平均回撤最好（`-34.23%`）但成本结果最差（`-21.08%`）。这些只是完整网格的描述，不能在看到结果后挑门槛或修改权重。

最接近的版本是收益方差熵主信号配 60% 低波动资格门、门内只按主信号排序。它在三个验证年均取得正平均 IC 与正标准化收益，最差验证回撤改善到 `-20.03%`，2019–2023 标准化累计收益为 `+83.23%`；但 20 万元试跑在零/5bp/10bp/20bp 滑点下依次为 `+9.92%/+4.27%/-1.04%/-10.51%`，因此仅失败的冻结质量项仍是“20bp 合并收益必须为正”。45% 门槛的同类版本最差验证回撤 `-22.76%`，20bp 收益 `-13.67%`，同样拒绝。不得把零或 5bp 的正敏感性用于事后降低 10/20bp 门槛、宣称通过或生成当前选股。

因为开发幸存者为 0，2024–2025 的已暴露压力区间再次没有打开或读取。统一记录为 [`a_share_three_day_walkforward_campaign_003_research_record.json`](a_share_three_day_walkforward_campaign_003_research_record.json)；只读命令 `python scripts/a_share_three_day_walkforward_campaign003_completion_audit.py --compact` 重放 42 项目录、台账、门内公式、硬门槛、零压力读取和 Candidate49 零条目账本，12 项要求全部通过。Campaign003 与前两轮聚焦回归 33 项、完整 `tests/data_collector_tests` 1,163 项均通过；9 条提示仍只是既有 pandas 性能/未来行为警告。

Campaign003 的结论不是“低波动毫无作用”，而是“它能降低部分回撤，却不能从这组复用因子中产生足以覆盖冻结成本的边际”。下一轮不能只救援收益方差熵近失版本，也不能放宽回撤或成本门槛。Campaign004 的待冻结方向改为扩展经济信息：把未激活队列前三项——市场中性尾盘残差漂移、负收益后的成交额加权吸收率、日内有符号路径效率——作为一个完整的新分钟机制库；先在任何值和收益前同时冻结三个精确公式、方向、缺失/分母/市场同伴语义、覆盖与全终止因子唯一性门槛，再对通过无收益门禁的分支执行有限单因子和配对滚动网格。它仍是历史研究 campaign，不是 Candidate50 前瞻激活；Candidate49 继续保持唯一前瞻候选。

Campaign004 已按 [`a_share_three_day_walkforward_campaign_004_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_004_no_return_preregistration.json)（SHA‑256 `39e2147b75bcc3a0fd3cb39dee3932f794331142654f0bfe63679b2c8ecc2a4e`）先完成无收益门禁。不可变分钟特征快照含 33,015 个分区和 7,724,498 行，manifest/data SHA‑256 为 `8eefc381d006997f1dcd95edcd9be4db8485e0c4954d6166d94f1981ae3b57fe` / `1359e755e669c7b949b26b2086d1c1328ec0cdf53b45ce7e67d117a274c7fc8a`。三个 higher 方向都通过覆盖、容量和全终止因子唯一性：中位覆盖为 `99.7926%–99.8318%`，P05 覆盖为 `99.2631%–99.3371%`，P05 合格名称均为 138，潜在非重叠三日 cohort 均为 540；观察到的最大绝对中位日秩相关为 `0.781471`，低于冻结的 `0.8`。无收益审计 SHA‑256 为 `d7cdce80d0ac2923695b866a7cf034f5049ec4da1a5a8dd5fc36d4f41f1cb755`，历史日线字段为空、forward return 读取为 false。

随后且仍在第一次 Campaign004 收益读取之前，精确开发目录冻结为 [`a_share_three_day_walkforward_campaign_004_preregistration.json`](a_share_three_day_walkforward_campaign_004_preregistration.json)（SHA‑256 `e67811f265b2b744073391fa65698951b132065109f95fa47991b8254a5756e6`）：3 个单因子加 3 个无序因子对各自的 `25/75、50/50、75/25` 三个方向秩权重，共 12 项；没有三阶组合、阈值、过滤器、年份子集或权重拟合。2019–2023 的 12/12 项全部写入追加式哈希链，基础设施失败为 0；仅 3 项通过可执行性检查，但冻结开发 survivor 为 0。全部 12 项都失败“20bp 合并收益为正”、最差验证回撤、验证期试跑中位收益、正标准化收益折数和正试跑折数门槛。

中位验证 Rank IC 最高的是单独的市场中性尾盘残差漂移：`+0.005288`，3 折中 2 折为正；但中位 Top3-minus-Bottom3 spread 为 `-0.8562%`，验证期标准化和 10bp 试跑正收益折数都是 0，最差回撤 `-58.58%`，2019–2023 合并 10bp/20bp 收益为 `-23.56%/-30.74%`。相对最不负的版本是 `75%` 市场中性尾盘残差漂移加 `25%` 负收益吸收率：中位 IC `+0.001107`、中位 spread `+0.3500%`，但 10bp/20bp 仍为 `-10.89%/-17.81%`，最差验证回撤 `-35.89%`，并在两个验证折失败整手可负担率。不得据此事后救援权重、放宽回撤/成本门槛或开启 2024–2025。

因为 survivor 为 0，2024–2025 已暴露压力区间没有打开、没有读取该区间收益，也没有压力试验条目。统一记录为 [`a_share_three_day_walkforward_campaign_004_research_record.json`](a_share_three_day_walkforward_campaign_004_research_record.json)（SHA‑256 `6e0dd1295a75c1f3eebe70a5cf327d98490bd76a43b307cf5fb416013d60c88e`），并由追加式权威状态 [`a_share_three_day_iteration_status_20260728_campaign004.json`](a_share_three_day_iteration_status_20260728_campaign004.json)（SHA‑256 `2037007da4fe750b70715b9f0cf7e8d361cb9d6d18128fdb6c18b05486954749`）推进而不改写 20260727 状态；四轮 campaign 共保留 230 个开发试验。无收益与开发命令均已幂等复验，Campaign004 与政策聚焦测试 17/17、Campaign001–004 交叉回归 46/46、完整 `tests/data_collector_tests` 1,176/1,176 通过；第一次全量尝试中的 `OSError 28` 仅来自本机 Data 卷无可用空间，迁移 pytest 临时目录到外接盘后无失败复现，验证证据单独冻结在 [`a_share_three_day_walkforward_campaign_004_verification_20260728.json`](a_share_three_day_walkforward_campaign_004_verification_20260728.json)，不改变既有研究记录哈希。Candidate49 信号/执行台账仍为 0 条且哈希不变，Candidate50、当前评分、选股、仓位和订单均未创建。下一轮只能作为独立 Campaign005，在任何值前先对未激活队列中的“零收益活动吸收、午间重定价持续性、方向性价格冲击不对称”做机制重叠审计并冻结完整公式/方向/有限搜索，不能继续改 Campaign004。

Campaign005 已完整执行。机制重叠审计 [`a_share_three_day_walkforward_campaign_005_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_005_mechanism_overlap_audit.json)（SHA‑256 `c378541156f8e68a2d73bafe44f99f7d1b3fc7ca06c1cf72c093d07a93f7907e`）先于任何候选值、比较值、日线或收益，把三项队列概念分别冻结为零收益成交额强度、午间重定价持续性和方向性价格冲击不对称，连同 higher 方向、241 行来源网格中的精确窗口、零值/缺失/分母语义、合法范围、28 项比较目录以及最多 12 项的有限单因子/配对搜索一起固定。随后无收益协议 [`a_share_three_day_walkforward_campaign_005_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_005_no_return_preregistration.json)（SHA‑256 `01b0c48e2a3e1b0741dee62d4e9d4858e202410ea266a00faa1b5d5ccc21ffa3`）绑定不可变分钟来源和实现。

外接盘特征快照仍为 33,015 个分区、7,724,498 行，manifest/data SHA‑256 为 `7f48bd252d381f85deb416ed282b6f62aacee0ca492c37c99fdb901d2e241675` / `5c7f9e7e534cc4e4678c7ea746c69f5809dcc6415d9a652b93ff63899413fd75`；公式只读取 `datetime,symbol,provider,close,amount`。首次无收益审计在加载第一个候选的覆盖帧时因复用加载器缺少已冻结合法范围映射而以 `KeyError` 失败关闭：没有审计文件、比较值、日线或收益。修复仅注入原先已冻结的三项范围并新增范围断言，公式、方向、门槛、比较顺序和有限目录均未改变；记录为 [`a_share_three_day_walkforward_campaign_005_no_return_audit_infrastructure_repair_20260728.json`](a_share_three_day_walkforward_campaign_005_no_return_audit_infrastructure_repair_20260728.json)（SHA‑256 `3ed6cec7aa5fecfcf97b7ffa08d1f3e8aee912db7d8fdc69e558820e843cbc7e`）。

成功且幂等的无收益审计 `20260728T094320Z_campaign005_no_return_audit.json` SHA‑256 为 `7a6ae6e1667aeb7a7060550c722431f0e8b88ff6e18bc00c2f3478dc2646b2b1`。午间持续性中位/P05 覆盖仅 `82.2666%/74.9629%`，在比较值前停止；方向性冲击不对称虽通过覆盖，却与已终止 `intraday_up_move_amount_share_238m` 的绝对中位日秩相关为 `0.916883`，超过冻结的 `0.8`，在唯一性门停止。只有 `intraday_zero_return_amount_intensity_238m` 通过：中位/P05 覆盖 `99.9193%/99.4935%`，P05 合格名称 138，最大绝对中位日秩相关 `0.640094`，最近比较为 `intraday_amount_volatility_coupling_238p`。审计的历史日线字段仍为空，forward return 为 false。

在第一次 2019–2023 收益读取前，开发预注册 [`a_share_three_day_walkforward_campaign_005_preregistration.json`](a_share_three_day_walkforward_campaign_005_preregistration.json)（SHA‑256 `ff0afcde4dab5c6783a0c31190b3c1daf6857957016fe7554bab9d69c5e7ea96`）把搜索压缩为恰好一个 higher 单因子试验，禁止配对、终止因子救援、阈值、过滤、年份子集和权重拟合；三组扩展折、边界 purge 3 个信号日、`t+1` 开盘/`t+3` 收盘、Top3、CNY 200,000 整手试跑、成本、回撤和幸存门槛均哈希继承 Campaign004。独立入口 [`a_share_three_day_walkforward_campaign005.py`](../scripts/a_share_three_day_walkforward_campaign005.py) 哈希绑定 Campaign004 执行内核但不修改其文件。

唯一试验三个验证年的平均 Rank IC 都为正，依次为 `0.002685/0.024016/0.022619`；但 spread 三折都为负，中位数 `-0.001881`。归一化收益为 `-55.27%/-28.09%/-24.97%`，10bp 的 CNY 200,000 试跑收益为 `-6.61%/-3.09%/-2.40%`，整手可负担率为 `69.55%/67.58%/82.88%`，全部低于冻结的 90% 门槛。全开发期 10bp/20bp 试跑分别为 `-13.64%/-20.75%`，最差验证归一化回撤 `-55.95%`；因此正 IC 没有转化为正 spread 或可执行收益，开发 survivor 为 0。继承的 `survivor_decision` 辅助器把决定记录中的展示字段 `complexity` 固定写成 2，但试验目录和台账明确是一个因子、权重 1.0；该字段在全部指标和门槛之后生成，不参与冻结排序或选择，原冻结产物不为修正文案而改写。

零幸存者关闭记录明确 `stress_interval_opened=false`、`stress_return_fields_read=false`，2024–2025 没有加载。统一研究记录为 [`a_share_three_day_walkforward_campaign_005_research_record.json`](a_share_three_day_walkforward_campaign_005_research_record.json)（SHA‑256 `add4984c7bcfc9cd2aa9bd0b7ed31d324577b24378ec9f931ac16effbd69a604`），新的追加式权威状态为 [`a_share_three_day_iteration_status_20260728_campaign005.json`](a_share_three_day_iteration_status_20260728_campaign005.json)（SHA‑256 `196873713efc1ab323b8511427a3e3613988b6013a5dcc2544a32901ca45ffc0`）：五轮 campaign 共保留 231 个开发试验，Candidate49 两本真实台账仍为 0 条且哈希不变，Candidate50、当前聚合、评分、选股、仓位和订单均未创建。Campaign001–005、无收益特征、完成审计、政策和 Candidate49 工作流的交叉回归 86/86 通过；开发与零幸存者关闭命令再次运行均幂等，四个核心结果哈希不变。验证记录为 [`a_share_three_day_walkforward_campaign_005_verification_20260728.json`](a_share_three_day_walkforward_campaign_005_verification_20260728.json)（SHA‑256 `55a452ae93d44ffa30f51d8f750fd5f6f9593de4e9519c9552bdaada604c2b65`）。Campaign005 的精确定义已终止，不得反向、改公式/窗口/零值规则、阈值、过滤、年份、成本或与任何终止因子组合后重测；下一轮只能从新的经济机制做 Campaign006 概念筛查和独立无收益冻结。

Campaign006 已按该顺序完整执行。概念记录 [`a_share_three_day_walkforward_campaign_006_concept_scouting.json`](a_share_three_day_walkforward_campaign_006_concept_scouting.json)（SHA‑256 `745bfd2e50b87b2a67f099ad31794b500dcd8e8ee204f9b697d278c2b0a4b767`）先在不读分钟分区、比较值、日线或收益的条件下排除了收益自相关、波动时点、市场响应滞后、零收益变体和成交量轮廓等终止机制近义项，只保留“成交均价路径是否确认分钟收盘路径”。随后机制审计 [`a_share_three_day_walkforward_campaign_006_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_006_mechanism_overlap_audit.json)（SHA‑256 `6178638773f4ababdcbd91e93c925a6c2c768fe692e02ed029f5f8174a0d9e7d`）冻结 `intraday_transaction_price_path_confirmation_238p`：在上午/下午各自的相邻活跃分钟对上计算收盘对数收益与 `amount/volume` 成交均价对数收益的 Pearson 相关，排除 09:30 和午间跨段，双零成交只移除相邻对、单边零成交判整日缺失，至少需要 120 个有效对，方向为 higher。水平差、符号命中、领先滞后、加权、改窗口、改阈值、反向和组合均在值前排除；有限目录只有一个权重 1.0 的单因子试验。

无收益协议 [`a_share_three_day_walkforward_campaign_006_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_006_no_return_preregistration.json)（SHA‑256 `fbe683e54705b458f7d13f56f3ccbd87235ff62a1cd67e1b5ced8b5538bda579`）绑定实现与来源后，生成 33,015 分区、7,724,498 行的不可变快照；清单 SHA‑256 为 `1f32cbe4c9d93ef2fbecf27b74cc4d15caddb5f62ca77e9818395c1c1743e0ab`，数据集 SHA‑256 为 `170381f7624e9b3d2e45170c9e363eea877ecec0f1f3945d03945ac2238f3c04`，有效因子行 7,541,702。唯一审计 `20260728T112534Z_campaign006_no_return_audit.json`（SHA‑256 `dbc6f63904e7a064f26f9fee12f979cb1702ecc2e61eec5422d341fe62b0db8a`）的覆盖中位/P05 为 `99.5430%/98.1986%`，P05 合格名称 138，540 个潜在非重叠三日 cohort；与 29 个冻结机制的最大绝对中位日秩相关仅 `0.390068`，最近项为 `intraday_amount_volatility_coupling_238p`，所以获得一次开发资格。该阶段的日线字段仍为空、forward return 为 false。

开发预注册 [`a_share_three_day_walkforward_campaign_006_preregistration.json`](a_share_three_day_walkforward_campaign_006_preregistration.json)（SHA‑256 `7da7117147ef2d1b929beefc033550b1336185550875086788fc2074b60c3f98`）在第一次 2019–2023 收益读取前固定唯一试验，并哈希继承三组扩展折、边界 purge 3 个信号会话、`t+1` 开盘/`t+3` 收盘、Top‑3、CNY 200,000 整手试跑、成本和幸存门槛。三个验证年 2021/2022/2023 的平均 Rank IC 分别为 `-0.021195/-0.029380/-0.047427`，归一化收益分别为 `-17.34%/-63.70%/-27.71%`，10bp 试点收益分别为 `-2.76%/-13.24%/-5.47%`；中位验证 spread 为 `-0.003741`，最差验证归一化回撤 `-64.20%`，2019–2023 汇总 20bp 试点收益 `-27.74%`。整手可负担率和成交额参与上限均通过，但关联与收益门全部失败，开发幸存者为 0。

因此 2024–2025 压力区间没有打开、没有读取压力收益。统一研究记录 [`a_share_three_day_walkforward_campaign_006_research_record.json`](a_share_three_day_walkforward_campaign_006_research_record.json)（SHA‑256 `c8124405072a6bbc61a135444765ec05bfdaade813fa325357dabef8e081812e`）和追加式权威状态 [`a_share_three_day_iteration_status_20260728_campaign006.json`](a_share_three_day_iteration_status_20260728_campaign006.json)（SHA‑256 `bb2aa86c67cf6d5ef50c7c898d1a4c8ad6ffc15e19dff59a707de6a76dde8657`）把累计开发试验数推进为 232；Candidate49 信号/执行台账仍为 0 条且哈希不变。快照、无收益审计、开发和零幸存者关闭均已幂等复验，Campaign001–006 与 Candidate49 工作流交叉测试 99/99 通过；统一报告的 Candidate49 语义重放也在临时输出上通过且未改权威报告。验证记录为 [`a_share_three_day_walkforward_campaign_006_verification_20260728.json`](a_share_three_day_walkforward_campaign_006_verification_20260728.json)（SHA‑256 `cfe790674b75e234eb60b5b1880fc8b5df08c6e2263a0ee1ac3413681ccb6bd6`）。该 higher 成交均价路径确认定义已经终止，不得反向、改 120 对门槛、活动语义、相关估计、窗口、过滤或与终止因子组合后重测；Campaign007 只能重新从概念级无值筛查开始。

Campaign007 已继续使用完整历史样本做独立研究，不等待当日 16:30 数据。概念筛查 [`a_share_three_day_walkforward_campaign_007_concept_scouting.json`](a_share_three_day_walkforward_campaign_007_concept_scouting.json)（SHA‑256 `324f03c09b4f28ebaeda2055772de35a1a89bd186919864f60db0ef9b1cc021d`）先拒绝把 09:30 到 09:31 的价格位移作为新机制，因为 09:30 可能是零活动参考占位且开盘缺口协议已经终止；机制审计 [`a_share_three_day_walkforward_campaign_007_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_007_mechanism_overlap_audit.json)（SHA‑256 `7e7ebe2232f379b9659222c878b49730a3a2ab331f6542890906d5880970da57`）随后冻结唯一 higher 因子 `intraday_share_volume_transaction_price_coupling_238p`。它只读取 `datetime,symbol,provider,volume,amount`，在上午和下午各自的相邻活跃分钟对上计算 `log(volume_t/volume_t-1)` 与 `log((amount_t/volume_t)/(amount_t-1/volume_t-1))` 的 Pearson 相关，排除 09:30 和午间跨段；双零活动对被移除、单边零值判整日缺失，至少需要 120 对。公式、方向、活动语义、阈值、窗口、反向、领先滞后、过滤、组合和年份子集均在任何值或收益前固定，有限目录只有一个权重 1.0 的单因子试验。

无收益协议 [`a_share_three_day_walkforward_campaign_007_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_007_no_return_preregistration.json)（SHA‑256 `308d5898c4a6d04b127c21876039ef7886d28b317951240fc29ba9ab2568a8ef`）绑定实现和来源。首次特征构建在第 801 个已完成分区后遇到一个合法空基集，却在空集返回前误执行单例 symbol 校验而退出；当时没有最终快照、比较值、日线或收益。修复只把空集返回移到校验前，不改公式、字段、门槛或任何研究选择，并记录在 [`a_share_three_day_walkforward_campaign_007_feature_build_infrastructure_repair_20260728.json`](a_share_three_day_walkforward_campaign_007_feature_build_infrastructure_repair_20260728.json)（SHA‑256 `c708e0114ee0c272965086102e1b0c4e9399f3d952a6618890f786b07ef30c98`）。恢复时复用 801 个逐分区哈希检查点，最终不可变快照含 33,015 分区、7,724,498 行和 7,551,741 个合格因子行，manifest/data SHA‑256 为 `d76fee2c03a38673eb4ce3a20ad0dba35f509c67a86201e50a410cadbdde6033` / `3eeee40583146024e7b9b8e867daa2e17043c6dc5a72ce3d3e8d525602bb8931`。

唯一无收益审计 `20260728T123537Z_campaign007_no_return_audit.json` SHA‑256 为 `69de8e7cf7cfd16c2563d259f4cdc786d20c2b73e153e73ed7a16f3c73544bf8`。覆盖中位/P05 为 `99.6243%/98.3153%`，P05 合格名称 138，2019–2025 共 540 个潜在非重叠三日 cohort；30 个冻结比较全部通过，最大绝对中位日秩相关为 `0.547339`，最近项是已终止的 `intraday_signed_path_efficiency_239m`，低于 `0.8` 唯一性上限。无收益阶段没有读取分钟收盘、日线价格或 forward return。

第一次 2019–2023 收益读取前，开发预注册 [`a_share_three_day_walkforward_campaign_007_preregistration.json`](a_share_three_day_walkforward_campaign_007_preregistration.json)（SHA‑256 `38e70809366f44455c05020079e0b069fff056b8a134417f163501d404a902e9`）冻结原有三组扩展式训练/验证折、折边界 purge 3 个信号日、`t+1` 开盘/`t+3` 收盘、Top‑3、CNY 200,000 整手试跑、成本与幸存门槛。2021/2022/2023 验证期平均 Rank IC 为 `-0.028128/-0.019124/-0.018013`，spread 为 `+0.004541/+0.001741/-0.001566`，归一化收益为 `+74.04%/-15.84%/-31.29%`，10bp 试跑为 `+6.45%/-3.65%/-5.28%`；第三折整手可负担率 `89.64%`，也低于冻结的 90% 门槛。2019–2023 合并归一化、10bp 和 20bp 收益分别为 `-43.35%/-10.02%/-17.20%`，开发幸存者为 0。

因此 2024–2025 最终压力集没有打开且没有读取收益；这正是“利用历史样本持续研究，同时把最终压力集保留给预先冻结且通过开发门槛的幸存者”的工作方式，不需要等待每天新增一根日线。研究记录 [`a_share_three_day_walkforward_campaign_007_research_record.json`](a_share_three_day_walkforward_campaign_007_research_record.json)（SHA‑256 `796300c1eace69b207202c698ee96b91f1e75bb723291692902f892a5d53587b`）和追加式状态 [`a_share_three_day_iteration_status_20260728_campaign007.json`](a_share_three_day_iteration_status_20260728_campaign007.json)（SHA‑256 `11ca8ddbc5b523db5075b2a08a204f4f9c8f12804770affa1b0ae1778cea4d1e`）把累计开发试验数推进为 233。快照、无收益审计、开发和关闭压力集均已幂等复验，Campaign001–007 与 Candidate49 工作流交叉测试 111/111 通过；统一报告语义重放通过且未改权威报告。验证记录为 [`a_share_three_day_walkforward_campaign_007_verification_20260728.json`](a_share_three_day_walkforward_campaign_007_verification_20260728.json)（SHA‑256 `ece65c2429fbd4a2af39e52d04ce182fcc17a5ebd89dc3b6ef580425dfac7b99`）。Candidate49 信号/执行台账仍为 0 条且哈希不变；Candidate50、当前聚合、评分、选股、仓位、订单和 Level‑2 工作均未创建。Campaign007 定义已经终止，不得反向、改公式/窗口/120 对门槛/活动语义、筛选、年份或与任何终止因子组合重测；下一轮只能作为独立 Campaign008 从新的经济机制与无值重叠审计开始。

Campaign008 继续按“先机制、后值、再收益”的历史分段流程执行，不等待当日 16:30 数据。概念筛查 [`a_share_three_day_walkforward_campaign_008_concept_scouting.json`](a_share_three_day_walkforward_campaign_008_concept_scouting.json)（SHA‑256 `0268be76964f272ba32618c2823b530e860dd507fae656ae389d89f637b79667`）和无值机制审计 [`a_share_three_day_walkforward_campaign_008_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_008_mechanism_overlap_audit.json)（SHA‑256 `259d3055898961287bea478946fa1653deade16b9b9927da9fc8b7a5d3d87246`）冻结唯一 higher 因子 `intraday_post_shock_share_volume_replenishment_236p`。它把每个半日内截至 `t` 的绝对一分钟收盘冲击与 `t` 到 `t+1` 的股数成交量对数增长相关，最多 236 对；09:30、午间跨段和末端越界响应均排除，双零响应端点只移除该对，任一单边零端点判整个股票日缺失，至少需要 120 对。公式、方向、滞后、零值语义、门槛、窗口、反向、过滤和组合在任何分钟值或收益前固定。

无收益协议 [`a_share_three_day_walkforward_campaign_008_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_008_no_return_preregistration.json)（SHA‑256 `1c209a1611d822531efe178793c80e5a8f68f5752ae5a0dfa890585e62dfcf56`）绑定后，全量快照仍覆盖 33,015 分区和 7,724,498 个源股票日，manifest/data SHA‑256 为 `09d4f82ec350ff8c16106c7ebc007d791f626589d33cd3e09cd4d0725893aaab` / `825b9a68890a6975b0866a99ce5b798968b82d80f226c8fdadbffba3472b40dc`。结果不是收益失败，而是可用性失败：每个源股票日都至少有一组单边零成交量响应端点，严格冻结规则使有效因子行数为 0。无收益审计 `20260728T132806Z_campaign008_no_return_audit.json`（SHA‑256 `af4013e0d439174ab6bb0c08d26bdf4bed71b6bd668eea25c834ec5ff0f5e937`）因此记录覆盖中位/P05、P05 名称和潜在三日 cohort 全为 0，并在加载任何比较因子值、日线价格或 forward return 前终止。

Campaign008 没有创建开发预注册、训练或回测试验，累计开发试验数保持 233，2024–2025 也没有打开。研究记录 [`a_share_three_day_walkforward_campaign_008_research_record.json`](a_share_three_day_walkforward_campaign_008_research_record.json)（SHA‑256 `7057ed2031a16c4e6bc5bdc643aae11b321883e548c553bb82c499225e2f2a67`）、追加式状态 [`a_share_three_day_iteration_status_20260728_campaign008.json`](a_share_three_day_iteration_status_20260728_campaign008.json)（SHA‑256 `8d2c00e25e847166bbdb8454bdf3f2c79d0b7a6668bf73923bdc2d9d175f7bbb`）和验证记录 [`a_share_three_day_walkforward_campaign_008_verification_20260728.json`](a_share_three_day_walkforward_campaign_008_verification_20260728.json)（SHA‑256 `20336c17a7182f5fec645668af546299a6d32bf44274e11fa1dc39d7c0d5a979`）冻结该结论。快照和审计幂等复验通过，Campaign001–008 与 Candidate49 交叉测试 120/120 通过，统一报告语义重放通过且未改权威报告；Candidate49 两本真实台账仍为 0 条且哈希不变。

不得把 Campaign008 的单边零端点改成“仅移除该对”，也不得改 120 对门槛、滞后、冲击/成交量变换、窗口、方向、年份、过滤或与任何终止因子组合后重测。不得读取它的历史或压力收益、回填 Candidate49、启动 Candidate50、生成当前评分/选股/仓位/订单或购买 Level‑2。下一轮 Campaign009 只能从新的经济机制和独立无值审计开始；统计唯一性应覆盖所有拥有可用冻结值的既有因子，并把 Campaign008 作为不可数值比较但必须通过语义核重的终止机制。

Campaign009 选择了与成交量响应和跨分钟收盘路径不同的 OHLC 微观价格发现机制。概念筛查 [`a_share_three_day_walkforward_campaign_009_concept_scouting.json`](a_share_three_day_walkforward_campaign_009_concept_scouting.json)（SHA‑256 `718a81b78fb156fb5162a794d5f70de72af8683ed9dfaca5963570f23ad9e905`）及无值机制审计 [`a_share_three_day_walkforward_campaign_009_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_009_mechanism_overlap_audit.json)（SHA‑256 `abfbc1d94b6a6272eaedb65a8c9ea8673398da3cb220b30c34997c2fcd45df21`）在任何分钟值或收益前冻结 higher 因子 `intraday_intrabar_body_range_efficiency_240m = sum(abs(log(close/open))) / sum(log(high/low))`。它只使用 09:31–11:30 与 13:01–15:00 的 240 个 contemporaneous OHLC bar，排除 09:30，不用相邻 bar、成交量或成交额；所有 OHLC 必须正数、有限并精确满足排序，零区间 bar 合法贡献 0，至少需要 120 个正区间 bar。

无收益协议 [`a_share_three_day_walkforward_campaign_009_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_009_no_return_preregistration.json)（SHA‑256 `7080dae932fa3b35869ea39de1b4e3759ff968629ee20f422e368eb2e0799e19`）绑定实现后，首次 33,015 分区计算在最终发布前因复用执行器的阶段标志适配错误而 fail closed：内存中的 Campaign006 原生 `source_open_high_low_read=false/source_volume_read=true` 标志被发布后 Campaign009 标志校验提前拒绝，当时没有最终快照、比较值、日线或收益。修复记录 [`a_share_three_day_walkforward_campaign_009_feature_build_infrastructure_repair_20260728.json`](a_share_three_day_walkforward_campaign_009_feature_build_infrastructure_repair_20260728.json)（SHA‑256 `a5263a15e4d4b1af5c2cf9d755627302ea94d8cf05989ba67f33c638f5b6a28b`）只让校验区分发布前/发布后阶段，未改公式、字段、OHLC 规则、120-bar 门槛或任何研究选择；唯一重试复用全部 33,015 个逐分区哈希检查点。日志沿用的 “Campaign006” 进度标签也只是显示文本。

最终不可变快照仍有 7,724,498 行，其中 6,924,627 行有效；799,871 行因正区间 bar 少于 120 个而缺失，OHLC 非法值、排序违例、非有限聚合和越界值均为 0。manifest/data SHA‑256 为 `1857176ced53c5515688b4c4b8e0e6e1b5b8332212841e529608169f77496aa7` / `14fac16f960b84be9ec89c01eea286267bed079c1c17600e94ae2156deac357d`。无收益审计 `20260728T142948Z_campaign009_no_return_audit.json`（SHA‑256 `b170574e70cabe2700d90716e852c4c6c0a85714619261cecb5d2d1ef4f70c5e`）的覆盖中位/P05 为 `97.494964%/90.957541%`，P05 合格名称 136，潜在非重叠三日 cohort 540；31 个有可用冻结值的统计比较全部通过，最大绝对中位日秩相关 `0.472734`，最近项为 `intraday_zero_return_amount_intensity_238m`。Campaign008 另以语义而非数值方式完成核重。此时仍未读取日线或 forward return。

开发预注册 [`a_share_three_day_walkforward_campaign_009_preregistration.json`](a_share_three_day_walkforward_campaign_009_preregistration.json)（SHA‑256 `04fc26d329fe16d00e939adaf77d3a5c80659205775aa610d01d87bb6da41ae2`）随后冻结唯一一次 2019–2023 higher 单因子试验。2021/2022/2023 验证平均 Rank IC 为 `-0.021132/-0.047906/-0.040967`，spread 为 `-0.004317/-0.006383/-0.000731`，归一化收益为 `-19.62%/-43.22%/-24.53%`，10bp 整手试跑为 `-4.03%/-7.89%/-3.45%`；第二折整手可负担率 `87.21%` 低于冻结的 90% 门槛。2019–2023 汇总归一化、10bp 和 20bp 收益分别为 `-84.96%/-17.95%/-22.51%`，开发幸存者为 0，因此 2024–2025 没有打开或读取。

研究记录 [`a_share_three_day_walkforward_campaign_009_research_record.json`](a_share_three_day_walkforward_campaign_009_research_record.json)（SHA‑256 `4590efb674e78a82eca080cf042db76e6f73ded22ec56cad8714da4cc8c08769`）和追加式状态 [`a_share_three_day_iteration_status_20260728_campaign009.json`](a_share_three_day_iteration_status_20260728_campaign009.json)（SHA‑256 `ab9072891b5b903cd02cf05830213f8909287dccdb833a182843f7cb030ecf76`）把累计开发试验数推进到 234。快照、无收益审计、开发与零幸存者关闭均已幂等复验，Campaign001–009 和 Candidate49 交叉测试 134/134 通过，统一报告语义重放通过且未改权威报告；验证记录为 [`a_share_three_day_walkforward_campaign_009_verification_20260728.json`](a_share_three_day_walkforward_campaign_009_verification_20260728.json)（SHA‑256 `fa31ffe17d7a44d0a2d210e76b5f99d26f6ad3b4defc5a2f53685188d0746885`）。Candidate49 两本真实台账仍为 0 条且哈希不变。不得反向、改 log body/range、改成逐 bar 比率均值、拆分 K 线方向/影线、改 120-bar 门槛、窗口、过滤、年份或组合后重测；Campaign010 只能重新从独立概念和无值审计开始。

Campaign010 从概念级无值筛查重新开始，选择相邻一分钟高低价区间的价格接受连续性，而不是 Campaign009 的单根 K 线实体/振幅效率。概念记录 [`a_share_three_day_walkforward_campaign_010_concept_scouting.json`](a_share_three_day_walkforward_campaign_010_concept_scouting.json)（SHA‑256 `c21f5487bbbfcf608557a004d76d8f7032f7488dff76e23c44c9756593b504e3`）、机制审计 [`a_share_three_day_walkforward_campaign_010_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_010_mechanism_overlap_audit.json)（SHA‑256 `41f4d88ff785ef594c1aec9337a4498de53f08edac532c4237340810f2f57680`）和无收益协议 [`a_share_three_day_walkforward_campaign_010_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_010_no_return_preregistration.json)（SHA‑256 `0981e5915f0ba5eff8f779b7ad594324bccfd75b0fb76f22916ed734d6443a53`）均在候选值前冻结。唯一 higher 因子 `intraday_adjacent_range_overlap_continuity_238p` 只读取 `datetime,symbol,provider,high,low`，在上午和下午各形成 119 个相邻区间对，以 log 价格空间的总交集长度除以总并集跨度；排除 09:30 和午间跨段，精确要求正数有限且 `low<=high`，零并集对贡献 0 且不计入门槛，至少需要 120 个正并集对。

不可变 Campaign010 快照 manifest/data SHA‑256 为 `e700c23b8c86e412153dd7ebd3bcb4a322f12b8a506cbbf5e4659490da50d69b` / `55303f4934044fa2543d459aa378e28ff440b03b8a0a69d6866e14736d6bdcc0`。33,015 个分区、7,724,498 行中 7,509,368 行有效；215,130 行因正并集对不足 120 个缺失，high/low 非法值、排序违例、非有限聚合和越界均为 0。首次无收益调用在候选或比较值前被继承校验器错误要求 `source_close_read=true` 挡住；[`a_share_three_day_walkforward_campaign_010_no_return_infrastructure_repair_20260728.json`](a_share_three_day_walkforward_campaign_010_no_return_infrastructure_repair_20260728.json)（SHA‑256 `f2cb1b0cfe222bab987abd329048a56418e3a6450bdc92ca2c1b0a8486d736d2`）只把已发布 Campaign010 manifest 改为必须 `source_close_read=false`，未改公式、方向、120 对门槛、快照或比较目录。

唯一成功的无收益审计 `20260728T153818Z_campaign010_no_return_audit.json`（SHA‑256 `e86bd79edc830d68bcf72ab5148e42e030dae5df28087d6b68f0147a581fb262`）先通过覆盖/容量：中位/P05 覆盖 `99.024390%/97.236239%`，P05 合格名称 `137.55`，潜在非重叠三日 cohort 540。随后 32 个统计比较中 31 个通过，但与 terminal Campaign009 `intraday_intrabar_body_range_efficiency_240m` 的中位日秩相关为 `-0.877524`，绝对值超过冻结的 0.8 门槛，所以唯一性失败。负号不授权反向；按预注册绝对相关判重。Campaign010 因而在任何日线、forward return、2019–2023 开发折或 2024–2025 压力收益前终止，开发试验为 0、累计仍为 234。保存研究记录 [`a_share_three_day_walkforward_campaign_010_research_record.json`](a_share_three_day_walkforward_campaign_010_research_record.json)（SHA‑256 `f8beb653f3f0215b4483e773360637c0713cf43b62d57e488a6006b326ab927d`）和追加状态 [`a_share_three_day_iteration_status_20260728_campaign010.json`](a_share_three_day_iteration_status_20260728_campaign010.json)（SHA‑256 `fa03536f5fdaf8a7732057ea9bd798be966321337fc9628ff190ad0cfe26ce98`）。不得反向、改 containment/Jaccard/逐对均值或并集分母、改 120 对门槛、时间窗、零宽规则、年份、过滤或组合后重测；Campaign011 只能再次从全新概念和独立无值审计开始。

Campaign010 的快照与无收益审计均已幂等复验，Campaign001–010 与 Candidate49 交叉测试 146/146 通过。统一报告首次因走前研究记录误用会被旧 48 机制扫描捕获的 `terminal_*` 状态前缀而在写文件前拒绝；按 Campaign008/009 既有 `completed_*` 语义修正记录状态后，报告只读重放恢复，输出哈希仍为 `eee6a662721fe9c511dfa57830ded2d84ae071f26b2beda890cea82d8f51cead`、622 行、0 信号/0 结算，权威报告未重写。该兼容修正未改任何因子、指标、门槛、快照、审计、台账或结论。验证记录为 [`a_share_three_day_walkforward_campaign_010_verification_20260728.json`](a_share_three_day_walkforward_campaign_010_verification_20260728.json)（SHA‑256 `7a982880898a3400c06b32298a3c1803f6f81fde47ed32b20c36d04dd20e0cec`）。

Campaign011 继续使用“概念先行、值前冻结、2019–2023 扩展走前开发、仅对冻结开发幸存者一次性打开 2024–2025”的研究流程，不需要等待当天日线。概念记录 [`a_share_three_day_walkforward_campaign_011_concept_scouting.json`](a_share_three_day_walkforward_campaign_011_concept_scouting.json)（SHA‑256 `f3bb2a4f2641f4617de8fddbbb4fb933ae17531c17c4b88b5366ad5b4d31a6e5`）、机制核重 [`a_share_three_day_walkforward_campaign_011_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_011_mechanism_overlap_audit.json)（SHA‑256 `fe50e938523f49fe8038e72036b2d3d7c8a08ef3c5870747d5f967b910679eed`）和无收益协议 [`a_share_three_day_walkforward_campaign_011_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_011_no_return_preregistration.json)（SHA‑256 `3e530c7a2f76e6a1eecdb18c6058a1d20fb1e3e54aaffb5ae4b3a857d5112e56`）都在候选或比较值前冻结。唯一 higher 因子 `intraday_intrabar_range_participation_entropy_240m` 只读取连续交易时段 240 根一分钟 K 线的 high/low，以每根 `log(high/low)` 在全天总区间中的份额计算固定 240 支撑的归一化 Shannon entropy；09:30 排除，零区间 bar 保留在固定支撑并贡献 0，至少要求 120 根正区间 bar，且不得修复非正、非有限或 `low>high`。

不可变快照 manifest/data SHA‑256 为 `36efe15038681d3a2fc154dfd3ce6d918c54ab56d1a5e803ee7aa86c295f4084` / `078dcb053e641813978ed96542fb9c69fbf3108ac490d3463e870b640feeee11`。33,015 个分区、7,724,498 行中 6,924,627 行有效；无收益审计 `20260728T164310Z_campaign011_no_return_audit.json`（SHA‑256 `1c07ddba4d3447016aa9460e6a9018b33eb380246cd672fbbb533d397066e995`）的覆盖中位/P05 为 `97.494964%/90.957541%`，P05 合格名称 136，潜在非重叠三日 cohort 540。33/33 个可用统计比较全部通过，最大绝对中位日秩相关为 `0.764617`，最近项是已终止的 Campaign010 相邻区间连续性。Campaign008 另以语义方式核重。首次审计调用因生成命名空间遗漏已冻结的 Campaign009 快照常量，在加载比较值、日线或收益前失败；只补齐该常量的无语义修复记录为 [`a_share_three_day_walkforward_campaign_011_no_return_infrastructure_repair_20260728.json`](a_share_three_day_walkforward_campaign_011_no_return_infrastructure_repair_20260728.json)（SHA‑256 `f4471448ccf786c7ffe2b167f4b877e279b8ffee4cddc92ca2c1b0a8486d736d2`）。

开发协议 [`a_share_three_day_walkforward_campaign_011_preregistration.json`](a_share_three_day_walkforward_campaign_011_preregistration.json)（SHA‑256 `3baa4343f1fb37d29a4aa9bfb568d1525a6d54155febfa5740c47590f97bc158`）冻结唯一一次 higher 单因子试验。2021/2022/2023 验证平均 Rank IC 为 `-0.007021/+0.022980/+0.003065`，spread 为 `-0.000903/+0.006522/-0.002570`，归一化收益为 `+11.38%/+6.06%/-6.08%`，10bp 整手收益为 `-0.42%/-1.07%/-2.95%`。整手可负担率三折均为 100%，但成本后收益三折全负、中位 spread 为负，2019–2023 汇总 20bp 整手收益为 `-15.19%`，因此开发幸存者为 0，2024–2025 没有打开或读取。不得以未扣成本的汇总归一化收益 `+37.99%` 推翻冻结的成本后门槛。

研究记录 [`a_share_three_day_walkforward_campaign_011_research_record.json`](a_share_three_day_walkforward_campaign_011_research_record.json)（SHA‑256 `e2b06cd44de18a179beddecac5f869a09c0cdbb6417595671a1e9510ff5a88c3`）和追加式状态 [`a_share_three_day_iteration_status_20260728_campaign011.json`](a_share_three_day_iteration_status_20260728_campaign011.json)（SHA‑256 `b474f33b9700713c03f4271a5da8335bf550f75df79eafa39d5e12e073798bd6`）把累计开发试验数推进到 235。继承的幸存者文件显示字段 `complexity=2`，但冻结目录和台账都证明本试验实际只有一个因子、语义复杂度为 1；这是无门槛影响的展示字段，不得重写冻结文件。当前上市快照导致的幸存者偏差仍是明确限制。不得反向、改 entropy 支撑/归一化/120 根门槛、删除零区间 bar、增加时间或活跃度权重、挑年份、改方向或与任何终止因子组合后重测；Campaign012 只能从真正不同的概念和独立无值审计开始。

Campaign012 继续在不等待新日线的情况下按同一历史样本分层流程推进。概念记录 [`a_share_three_day_walkforward_campaign_012_concept_scouting.json`](a_share_three_day_walkforward_campaign_012_concept_scouting.json)（SHA‑256 `8174841542272fb8d6f563032dda98d739f153999e6dbc9cbbdbf4589d100db0`）、机制核重 [`a_share_three_day_walkforward_campaign_012_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_012_mechanism_overlap_audit.json)（SHA‑256 `2311e40efb3d97a913c91fced47eff041490112b72285c60f0e3ff3a9bc25918`）和无收益协议 [`a_share_three_day_walkforward_campaign_012_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_012_no_return_preregistration.json)（SHA‑256 `23ffe9f165cf03bdbe3a0fc1ab0119e687c8388040674f5256ccbd1c1a5ffe86`）均在候选或比较值前冻结。唯一 higher 因子 `intraday_intrabar_range_reversal_238p` 只读取 high/low，在上午和下午各形成 119 个相邻 `log(high/low)` 区间幅度对，以固定 238 对的负 Pearson 相关刻画区间冲击的即时消退；09:30、午间跨段、隔夜和跨股票对均排除，零—零对保留，至少要求 120 个任一端为正区间的相邻对，退化方差不得填 0。

不可变快照 manifest/data SHA‑256 为 `58fca32b58be53523daa0fe7a971a1394a35d4f1251c484214d06f5deff6677a` / `aaa33541d55f68699e99a4a9d5abc697feafe215dd70ab1ba1c807b7cab3c18f`。33,015 个分区、7,724,498 行中 7,375,921 行有效，348,577 行因有效相邻对不足 120 个而缺失；非法 high/low、排序错、退化方差、非有限和越界均为 0。唯一无收益审计 `20260728T174604Z_campaign012_no_return_audit.json`（SHA‑256 `ddce865c259d712fefac213c2db923a292f49aa78f5e8cac8ad16dba3fc570fe`）的覆盖中位/P05 为 `98.777933%/96.213656%`，P05 合格名称 137，潜在 cohort 540。34/34 个统计比较全部通过，最大绝对中位日秩相关 `0.521641`，最近项为 `intraday_volatility_resolution_238m`；与 Campaign011 区间熵和 Campaign010 区间重叠的相关仅 `+0.275484/+0.216760`。审计没有读取日线或 forward return。

开发协议 [`a_share_three_day_walkforward_campaign_012_preregistration.json`](a_share_three_day_walkforward_campaign_012_preregistration.json)（SHA‑256 `8c7aac81dd2d3ffeb053d26c19ec140576bc6add00a1bb970f818d99f9e4f4aa`）冻结唯一一次 higher 单因子试验。2021/2022/2023 验证平均 Rank IC 为 `+0.034737/+0.036308/+0.049930`，spread 为 `-0.000315/+0.001137/+0.008665`，归一化收益为 `+25.71%/-6.75%/+4.77%`，10bp 整手收益为 `+0.79%/-3.37%/-1.15%`。三折关联均为正、操作门均通过，但成本后只有一折为正，中位 10bp 为 `-1.15%`，2019–2023 汇总 10bp/20bp 为 `-4.51%/-13.91%`，所以开发幸存者为 0，2024–2025 没有打开或读取。零滑点汇总 `+6.55%` 和 5bp `+0.77%` 不能推翻冻结的 10bp/20bp 稳健性门槛。

研究记录 [`a_share_three_day_walkforward_campaign_012_research_record.json`](a_share_three_day_walkforward_campaign_012_research_record.json)（SHA‑256 `340acecacf12ef5755dacbc57e792124ff0cb25113f82bc078e06db1585af986`）和追加式状态 [`a_share_three_day_iteration_status_20260728_campaign012.json`](a_share_three_day_iteration_status_20260728_campaign012.json)（SHA‑256 `e883ebde9d9b2c50368181d4a8aec15dde1c10625460abda060c1f601c284ffd`）把累计开发试验数推进到 236。继承的幸存者文件仍有无门槛影响的展示字段 `complexity=2`，实际是单因子、语义复杂度 1，不得重写冻结文件。不得反向、改 lag/相关估计器/午间语义/120 对门槛、去掉零—零对、使用 favorable 年份或成本、与终止因子组合后重测；Campaign013 只能从新的独立概念和无值审计开始。

Campaign013 同样直接使用既有历史分钟样本，不等待当天日线。概念记录 [`a_share_three_day_walkforward_campaign_013_concept_scouting.json`](a_share_three_day_walkforward_campaign_013_concept_scouting.json)（SHA‑256 `e4ed47f439cf3dd024ef2dde8669c72f422259c95c8c3df0728d6421db741e6f`）、机制核重 [`a_share_three_day_walkforward_campaign_013_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_013_mechanism_overlap_audit.json)（SHA‑256 `78262a1e90af0de4561329a21217ab5304925d7694877b9f84d61771fe77a715`）和无收益协议 [`a_share_three_day_walkforward_campaign_013_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_013_no_return_preregistration.json)（SHA‑256 `0a5c0225cba49ab11056e232b6ba9875f65c2734d318ef7644031472a9d76764`）均在候选值、比较值和收益前冻结。唯一 higher 因子 `intraday_transaction_vwap_envelope_asymmetry_240m` 在 09:31–11:30、13:01–15:00 的 active bar 上计算 `vwap=amount/volume`，以 `sum(log(high/vwap))-sum(log(vwap/low))` 除以上下两侧之和；零成交量且零成交额的 bar 不活跃，单边零使 stock-day 缺失，每根 active bar 必须精确满足 `low<=vwap<=high`，至少 120 根正区间 active bar，禁止换单位、取整、夹断或容差修复。

不可变快照 manifest/data SHA‑256 为 `706e71aacb802a2b34cf7b52236823bb3e63cd30d3f0e8340456344c7ef184d7` / `45ee0352936be01714efba01fef80118bb9fe97ee3cdfcdba65f429bf01b528b`。33,015 个分区、7,724,498 行中只有 78,351 行生成有限特征；7,616,444 行未通过 active bar 的 VWAP 包含关系，29,656 行正区间 active bar 不足 120 根，另有 47 行单边零活动。首次完整构建已算完所有分区，但继承的发布前校验错误要求尚未写入的 `source_amount_read`；[`a_share_three_day_walkforward_campaign_013_feature_build_infrastructure_repair_20260729.json`](a_share_three_day_walkforward_campaign_013_feature_build_infrastructure_repair_20260729.json)（SHA‑256 `c12fd002ce93ca472c6f8e68555f56fb96424bc3845f52036856e123325ea842`）仅把该字段改为发布前允许缺失、发布后必须为 true，公式、门槛和已计算分区均未改变。

无收益审计 `20260728T182958Z_campaign013_no_return_audit.json`（SHA‑256 `105ac63bc01828cf512be282377f835c87359a2356f29b7ff998734dcf4467b6`）在第一道覆盖/容量门终止：中位/P05 覆盖仅 `2.380952%/0.853085%`，P05 合格名称 3，潜在非重叠三日 cohort 11。审计没有加载任何比较因子值、日线、forward return、开发折或压力收益；唯一性没有求值，开发试验新增 0，累计仍为 236。这证明冻结字段组合在当前已接受分钟源中的联合兼容覆盖不足，不是方向或预测能力证据，也不得靠改单位、夹断、放宽 VWAP 包含关系、降低 120 根门槛、选年份或组合终止因子来救援。

研究记录 [`a_share_three_day_walkforward_campaign_013_research_record.json`](a_share_three_day_walkforward_campaign_013_research_record.json)（SHA‑256 `26f92825d28930500977cc4c78c661494841df18449759d13d8a601c31bf6d0f`）和追加式状态 [`a_share_three_day_iteration_status_20260729_campaign013.json`](a_share_three_day_iteration_status_20260729_campaign013.json)（SHA‑256 `7032456e2b73303d13d3502fc0e577c58b6e7ba27bcdf93453895fe24e798b03`）将 Campaign013 终止在收益读取前，当前候选仍为 0，Candidate49 仍仅保留其既有前瞻台账。Campaign014 可以立即从新的独立概念、值前机制核重和有限精确预注册开始；继续使用 2019–2023 扩展走前开发，只有冻结开发幸存者才可一次性打开 2024–2025。

Campaign014 继续直接使用既有历史样本。概念记录 [`a_share_three_day_walkforward_campaign_014_concept_scouting.json`](a_share_three_day_walkforward_campaign_014_concept_scouting.json)（SHA‑256 `0ccf17baa24347e2ad8fb83298bf7fd37a30c7fc916d407dc78c492e1c700f55`）、机制核重 [`a_share_three_day_walkforward_campaign_014_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_014_mechanism_overlap_audit.json)（SHA‑256 `2c5db4acd886d57649e7ac7cc0ce2232ae8efe957412d1fdc4804fcb7bb96890`）和无收益协议 [`a_share_three_day_walkforward_campaign_014_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_014_no_return_preregistration.json)（SHA‑256 `82e5cf3e26b6f2edc34e37651bf49026bb90d0409b97fd19bc853d71778cd16c`）均在任何候选值、比较值或收益前冻结。唯一 higher 因子 `intraday_global_price_range_revisit_240m` 只读取 09:31–11:30、13:01–15:00 的 high/low，把 240 个 `[log(low),log(high)]` 闭区间排序合并；若总区间长度为 `S`、精确并集长度为 `U`，因子为 `(S-U)/S`。它衡量全天任意时点对既有价格区域的全局重访，时间顺序置换不改变结果，区别于 Campaign010 的相邻区间重叠。零宽区间保留但不计入至少 120 根正区间 bar 的门槛。

不可变快照 manifest/data SHA‑256 为 `62469bb340ea9be6ee93321f4f81707c6753c30f4395ebcdd1db967efb360a67` / `7bea5c1047c4c5fdde5043d5b102a337a0f28deb26bb17c94eff82b65cb317bf`。33,015 个分区、7,724,498 行中 6,924,627 行有效，799,871 行仅因正区间 bar 少于 120 根而缺失，其余 high/low、并集、数值和边界错误均为 0。首次错误使用仓库日线根在分区读取前被 10 GiB 空间门拒绝；改用权威外接分钟根后全部分区完成，但发布前继承的 `source_volume_read` 阶段校验与原子发布后证据不一致。修复记录 [`a_share_three_day_walkforward_campaign_014_feature_build_infrastructure_repair_20260729.json`](a_share_three_day_walkforward_campaign_014_feature_build_infrastructure_repair_20260729.json)（SHA‑256 `74300718a6fe820f0264fe1e6551b758736f61bb5a919b2e186bce05df1b3412`）只令该标记在发布前接受继承 true、发布后必须为实际 false；重试时 33,015 个检查点全部按哈希恢复，公式和值未改。

无收益审计 `20260728T193433Z_campaign014_no_return_audit.json`（SHA‑256 `827fa9d5079ad86e9c25545fcbe680b2e26bc17edc1506dd1d3a7c883f44819f`）的中位/P05 覆盖为 `97.494964%/90.957541%`，P05 合格名称 136，潜在 cohort 540；35/35 个可用统计比较全部通过，最高绝对中位日秩相关 `0.667243`，最近项为 Campaign010 相邻区间重叠。Campaign008 和低覆盖的 Campaign013 仅做语义核重。开发协议 [`a_share_three_day_walkforward_campaign_014_preregistration.json`](a_share_three_day_walkforward_campaign_014_preregistration.json)（SHA‑256 `4a9e6deaf18889f0a500b908e45ca9f98fea39db5e119829de240bc35e7da190`）冻结唯一一次 higher 单因子试验。

2021/2022/2023 验证平均 Rank IC 为 `+0.020960/+0.028949/+0.029063`，spread 为 `+0.003757/+0.008447/-0.000336`，归一化收益为 `+6.70%/+14.80%/+0.57%`，10bp 整手收益为 `-1.12%/+0.05%/-1.98%`。三折 IC 和归一化收益均为正，整手可负担率均为 100%，但成本后只有一折为正、中位 10bp 为 `-1.12%`，2019–2023 汇总 10bp/20bp 为 `-2.77%/-12.86%`；零滑点 `+8.83%` 和 5bp `+2.95%` 不得推翻冻结的 10bp/20bp 稳健性门槛。因此开发幸存者为 0，2024–2025 没有打开或读取。

研究记录 [`a_share_three_day_walkforward_campaign_014_research_record.json`](a_share_three_day_walkforward_campaign_014_research_record.json)（SHA‑256 `33ba947dcb2abbdfebe896eccd365eb54f51afb1b073c9a61b3de2fec68fb260`）和追加式状态 [`a_share_three_day_iteration_status_20260729_campaign014.json`](a_share_three_day_iteration_status_20260729_campaign014.json)（SHA‑256 `c4d1ecf43024588ccd159e6f67141a381d058458d3d97db9d362d819dfea2975`）把累计开发试验推进到 237，当前候选仍为 0。继承的展示字段 `complexity=2` 对实际单因子、语义复杂度 1 无门槛影响，不得重写冻结文件。不得反向、用日高低凸包替代精确并集、改分母/120 根门槛/区间合并/时间窗、挑 2022 或低成本、与终止因子组合后重测；Campaign015 只能再次从真正不同的概念、值前核重和精确有限预注册开始。

Campaign015 继续直接使用 2019–2023 历史样本，不等待当天日线或 16:30。概念记录 [`a_share_three_day_walkforward_campaign_015_concept_scouting.json`](a_share_three_day_walkforward_campaign_015_concept_scouting.json)（SHA‑256 `6993ef826ba01f5abd80632d20fc0c521229e938f18c0ab12686e9ff337e85c7`）、机制核重 [`a_share_three_day_walkforward_campaign_015_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_015_mechanism_overlap_audit.json)（SHA‑256 `64af6fd2b9381f11495737fabd568b9c1685e0ca7793a79dc9b73d2f1dc7160e`）和无收益协议 [`a_share_three_day_walkforward_campaign_015_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_015_no_return_preregistration.json)（SHA‑256 `ef8cfbf9d7cb1dcc50f65c2d050d9e1931c97d86f74770d4270a5b94da21609e`）均在任何 Campaign015 值或收益前冻结。唯一 higher 因子 `intraday_prior_range_breakout_pressure_238p` 只读取 09:31–11:30、13:01–15:00 的 high/low/close；在各半场内形成 238 个“前一 bar 区间—当前 close”对，令 `U=sum(max(log(close_t/high_(t-1)),0))`、`D=sum(max(log(low_(t-1)/close_t),0))`，因子为 `(U-D)/(U+D)`。当前 close 位于或接触前一区间时贡献 0；每根输入必须正、有限且满足自身 `low<=close<=high`，并且至少有一个非零突破。

不可变快照 manifest/data SHA‑256 为 `450cefd5b268658997841038fd45156f436b7f3645a8ba5980681370abf42811` / `681c048babc594bf0b215fada4ff868d70d0a6bf450cf59cb610e22c6002747f`。33,015 个分区、7,724,498 行中 7,693,412 行有效；无收益审计 `20260728T203847Z_campaign015_no_return_audit.json`（SHA‑256 `1f09cca7bc62445558b1e8e2cee1d42f87e7bd784fdb1e8212c897d6fb503608`）的中位/P05 覆盖为 `99.824715%/99.301537%`，P05 合格名称 138，潜在 cohort 540，36/36 个统计比较通过。最近项是 `intraday_signed_path_efficiency_239m`，中位日秩相关 `+0.769704`，低于冻结的绝对值 0.8 门槛但较接近；与 Campaign014 的相关只有约 `-0.04082`。审计未读取日线、forward return 或 Candidate49 收益。

开发协议 [`a_share_three_day_walkforward_campaign_015_preregistration.json`](a_share_three_day_walkforward_campaign_015_preregistration.json)（SHA‑256 `26dc73a5d67c888d2d87fc24114d2163966b5ad4c3f3f3edee86383d79304636`）只允许一个 higher 单因子试验。2021/2022/2023 验证平均 Rank IC 为 `-0.009037/-0.003982/-0.006538`，归一化收益为 `+20.28%/-54.52%/-31.80%`，10bp 整手收益为 `+2.50%/-11.45%/-6.91%`；三个 IC 折全部为负，成本后只有一折为正。2019–2023 汇总归一化收益 `-68.75%`，0/5/10/20bp 整手收益为 `-11.34%/-15.62%/-20.93%/-26.84%`。开发幸存者为 0，因此 2024–2025 没有打开或读取。

研究记录 [`a_share_three_day_walkforward_campaign_015_research_record.json`](a_share_three_day_walkforward_campaign_015_research_record.json)（SHA‑256 `ddaf96c66cb86abb2f7d07950adade7f2a4e5a788004f7b4c6525f0d4ac8449c`）和追加式状态 [`a_share_three_day_iteration_status_20260729_campaign015.json`](a_share_three_day_iteration_status_20260729_campaign015.json)（SHA‑256 `c6092e60fa3934388e5fded6e1669ba173185dacf5fb5ecd39753d50cd27397f`）把累计开发试验推进到 238，当前聚合候选仍为 0。不得反向、修补、改成突破次数或阈值、改窗口/方向/年份/过滤器、与终止因子组合后重测，也不得打开 Campaign015 压力期、回填 Candidate49、启动 Candidate50 或形成当前评分、选股、仓位、订单。Campaign016 可以立即从全新的独立机制、值前核重和有限精确预注册开始，继续使用既有历史训练/验证划分；只有冻结开发幸存者才可一次性打开 2024–2025。

Campaign016 同样直接使用既有历史样本，不需要等待新日线或 16:30。概念记录 [`a_share_three_day_walkforward_campaign_016_concept_scouting.json`](a_share_three_day_walkforward_campaign_016_concept_scouting.json)（SHA‑256 `9cf788aaaa7f69ee020c9bf8716166a26c5553e780722a38bd58fe4c72921083`）、机制核重 [`a_share_three_day_walkforward_campaign_016_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_016_mechanism_overlap_audit.json)（SHA‑256 `ef932893c2e6afb5f5601846cdd7ac3e84c0eee375cec5930b817776bb6429d1`）和无收益协议 [`a_share_three_day_walkforward_campaign_016_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_016_no_return_preregistration.json)（SHA‑256 `8cb26965a4a4802e8e5c68730e7aae57b8fb3883aacd8f2d38c8b9d6daec5f89`）均在候选值和收益前冻结。唯一 higher 因子 `intraday_interbar_gap_body_confirmation_238p` 在上午、下午各自内部形成 119 个边界：`g_t=log(open_t/close_(t-1))`、`b_t=log(close_t/open_t)`，因子为 238 对的总体 Pearson 相关。09:30、午休边界、隔夜和跨日全部排除；零值、异号值全部保留。240 根 open/high/low/close 必须正、有限且满足 `low<=open<=high`、`low<=close<=high`，两个向量方差都必须为正。high/low 只做自身 bar 校验，公式不读取成交量或金额。

不可变快照 manifest/data SHA‑256 为 `052ff2096a18951f884825453a730fbf0175b693ec497a2faca23c5150e8830c` / `3279806f522c347bdcd0beeef8249a89656de4204fcc22276ac53afb136c8242`。33,015 个分区、7,724,498 行中 7,693,417 行有效；无收益审计 `20260728T220647Z_campaign016_no_return_audit.json`（SHA‑256 `36e19377f5406e8beb992627b1b456fcd4d5cbe0bcb54b0e814055ef80643224`）的中位/P05 覆盖为 `99.826990%/99.313892%`，P05 合格名称 138，潜在 cohort 540，37/37 个统计比较通过。最近项是 `intraday_adjacent_range_overlap_continuity_238p`，中位日秩相关 `-0.561793`；与 Campaign015 只有 `+0.058295`。审计未读取日线、forward return 或 Candidate49 收益。

开发预注册 [`a_share_three_day_walkforward_campaign_016_preregistration.json`](a_share_three_day_walkforward_campaign_016_preregistration.json)（SHA‑256 `b9eefe47df24afdc92cf433d80cf7d18f014fc0414c25baa33fcf74b6f02b4f9`）只允许一个权重 1.0 的单因子试验。2021/2022/2023 三折验证 mean Rank IC 为 `-0.038608/-0.050233/-0.057482`，normalized return 为 `+0.038583/-0.334710/-0.208937`，10bp、20 万元整手收益为 `+0.001176/-0.064173/-0.024332`；三折整手可负担率 `0.824324/0.894009/0.876147`，全部低于冻结的 0.90 门槛。2019–2023 聚合 normalized 与 0/5/10/20bp 收益为 `-0.696315` 和 `-0.112884/-0.142054/-0.179858/-0.241630`。开发幸存者为 0，所以 2024–2025 压力期未打开或读取。

研究记录 [`a_share_three_day_walkforward_campaign_016_research_record.json`](a_share_three_day_walkforward_campaign_016_research_record.json)（SHA‑256 `c483597cfca52a0fa6285d92bff1835992c23b2f6799ee32ddb67a5fc1a80948`）和追加式状态 [`a_share_three_day_iteration_status_20260729_campaign016.json`](a_share_three_day_iteration_status_20260729_campaign016.json)（SHA‑256 `8f1ae9b5934f8006cb016a8211d253a7c897d62182149ed797a7ab0e062b1ae2`）把累计开发试验推进到 239，当前聚合候选仍为 0。不得反向、改成符号一致/计数/beta/余弦/其他相关估计、删除零值或异号对、加入幅度或活跃阈值、纳入开盘/午休/隔夜、挑年份/成本、过滤或与终止因子组合后重测；也不得打开 Campaign016 压力期、回填 Candidate49、启动 Candidate50 或形成当前评分、选股、仓位、订单。Campaign017 可以立即从真正不同的独立机制和值前精确预注册开始。

Campaign017 继续直接使用冻结的 2019–2025 历史分钟样本，不等待当天日线或 16:30。概念记录 [`a_share_three_day_walkforward_campaign_017_concept_scouting.json`](a_share_three_day_walkforward_campaign_017_concept_scouting.json)（SHA‑256 `881f2e7bd0f30906a2c0a5cef7e32208dc7d6c87e3ac7e917dbd3f63cb4f7083`）、机制核重 [`a_share_three_day_walkforward_campaign_017_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_017_mechanism_overlap_audit.json)（SHA‑256 `bd0c6487d55baad23e41713b07e94206cafb9681f54e88cf609d161ebda68f48`）和无收益协议 [`a_share_three_day_walkforward_campaign_017_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_017_no_return_preregistration.json)（SHA‑256 `4676afee54b66b558dfd96dc238cbc4d8545aa728fbcf27ec09a8681001929ba`）均在候选值和收益前冻结。唯一 higher 因子 `intraday_midrange_width_change_coupling_238p` 对 240 根 high/low 计算对数几何区间中心 `m_i=(log(high_i)+log(low_i))/2` 与对数宽度 `w_i=log(high_i/low_i)`，再对上午、下午内部合计 238 个 `delta_m`、`delta_w` 求总体 Pearson 相关。09:30、午休边界、隔夜和跨日全部排除；零宽度、零变化和所有符号组合均保留；全部 high/low 必须正、有限且满足 `low<=high`，两个变化向量方差都必须为正。构建不读取 open、close、volume、amount、日线或 forward return。

不可变快照 manifest/data SHA‑256 为 `04b588681f64a61525407f7de5501e38244256e100d9895dbbee8635127e358a` / `e91a17f29edbd59f82801469187ac16c8bc460e08a1c2d6110cc4b2e99e17276`。33,015 个分区、7,724,498 行中 7,699,914 行有效。首次构建后的顶层清单继承了错误的 `source_close_read=true`，但实际 `source_fields_read` 始终只有 `datetime,symbol,provider,high,low`，分区与数据集均未包含 close；审计前仅将该顶层布尔值纠正为 false，并修复执行器的发布校验。语义修复记录 [`a_share_three_day_walkforward_campaign_017_feature_manifest_semantic_repair_20260729.json`](a_share_three_day_walkforward_campaign_017_feature_manifest_semantic_repair_20260729.json)（SHA‑256 `fbe8f7b9f19182c4fd214196db7376b2d0e498e6c9bf17d9d2448173961f0b0f`）证明旧/新清单哈希分别为 `cf98767e...` / `04b58868...`，数据集哈希、所有分区、因子值和 eligibility 均未改变。无收益审计 `20260728T232431Z_campaign017_no_return_audit.json`（SHA‑256 `be1c69e7184209f74d7d86ca9be0dff4281da7984461c1d35b7de0dbc7d5da92`）的中位/P05 覆盖为 `99.853694%/99.354839%`，P05 合格名称 138，潜在 cohort 540，38/38 个统计比较通过；最近项为 `intraday_share_volume_transaction_price_coupling_238p`，中位日秩相关 `+0.320704`，与 Campaign016 只有 `+0.073270`。

开发预注册 [`a_share_three_day_walkforward_campaign_017_preregistration.json`](a_share_three_day_walkforward_campaign_017_preregistration.json)（SHA‑256 `f4fa96727e42f7eafdd959a3f26979096b4c1dbc18dae2915f3abd77615796be`）只允许一个权重 1.0 的单因子试验。2021/2022/2023 三折验证 mean Rank IC 为 `-0.010556/-0.004556/-0.019069`，spread 为 `+0.007950/+0.000684/+0.007074`，normalized return 为 `+0.564543/-0.265114/-0.143264`，10bp、20 万元整手收益为 `+0.045355/-0.054377/-0.029811`。三折整手可负担率和成交额参与率均通过操作门，但三折 IC 全负，归一化和 10bp 仅一折为正；2019–2023 聚合 normalized 与 0/5/10/20bp 收益为 `-0.180526` 和 `+0.002589/-0.040263/-0.084667/-0.173094`。开发幸存者为 0，所以 2024–2025 压力期未打开或读取。

研究记录 [`a_share_three_day_walkforward_campaign_017_research_record.json`](a_share_three_day_walkforward_campaign_017_research_record.json)（SHA‑256 `c8c0241b6d49ab52af11feee80f630223f7c1dbb33c6ddad5f5ea4a6cd9c47e0`）和追加式状态 [`a_share_three_day_iteration_status_20260729_campaign017.json`](a_share_three_day_iteration_status_20260729_campaign017.json)（SHA‑256 `a6d4e30219178ee70b34fbb8441e52313da53a3cbaaca4f543d11ccaa14dd857`）把累计开发试验推进到 240，当前聚合候选仍为 0。不得反向、改为算术中点/宽度水平或比值/符号一致/beta/秩相关/其他估计，删除零宽或零变化，加入幅度/波动/活跃阈值，纳入 09:30/午休/隔夜，挑年份/成本、过滤或与波动率、区间、Campaign016 或其他终止因子组合后重测；也不得打开 Campaign017 压力期、回填 Candidate49、启动 Candidate50 或形成当前评分、选股、仓位、订单。Campaign018 可以立即从真正不同的独立机制和值前精确预注册开始。

Campaign018 同样直接使用冻结的 2019–2025 历史分钟样本，不等待当天日线或 16:30。概念记录 [`a_share_three_day_walkforward_campaign_018_concept_scouting.json`](a_share_three_day_walkforward_campaign_018_concept_scouting.json)（SHA‑256 `7c56399081205965859efbfe8c52ff4296984f68ddb2d3219354530994253890`）、机制核重 [`a_share_three_day_walkforward_campaign_018_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_018_mechanism_overlap_audit.json)（SHA‑256 `20cab7f44607e53c9af0a3bf95eee96a13711c3e72b051038d1b0bcccbf044e5`）和无收益协议 [`a_share_three_day_walkforward_campaign_018_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_018_no_return_preregistration.json)（SHA‑256 `5cc74329648ce47787291d2f4b5c960084ca1a0fc148284170e1a23d429c1fe6`）均在候选值和收益前冻结。唯一 higher 因子 `intraday_range_share_volume_confirmation_240m` 对 09:31–11:30、13:01–15:00 的 240 根连续分钟计算 `Corr(log(high/low), log1p(volume))`。09:30 排除；零振幅和零成交量保留在固定支持中；全部 high/low/volume 必须有限，high/low 为正、`low<=high`、volume 非负，两个转换向量方差均须为正。构建只读 `datetime,symbol,provider,high,low,volume`，不读 open、close、amount、日线或 forward return。

不可变快照 manifest/data SHA‑256 为 `9fe343dc34d57e59c3a5d12fb3d159b10e9d98cdd02cf1ce8c82b77fbbdb37a0` / `7762728e0a7d94dcddb1bcfb21531d4b66f98620a0282ffe501767c7e4f607be`。33,015 个分区、7,724,498 行中 7,699,914 行有效；24,584 行因 240 根分钟振幅方差为 0 而缺失，没有负成交量、字段排序或非有限转换错误。无收益审计 `20260729T004232Z_campaign018_no_return_audit.json`（SHA‑256 `16e8c23e8a4cac9d7e0e70649cf9f1b01e809b61459c7dbbc71b55870a4f58ff`）中位/P05 覆盖为 `99.853694%/99.354839%`，P05 合格名称 138，潜在 cohort 540，39/39 个统计比较通过。最近项为 `intraday_amount_volatility_coupling_238p`，中位日秩相关 `+0.672082`，仍低于冻结的 0.8；与 Campaign017 为 `-0.012856`。

通过无收益门后，[`a_share_three_day_walkforward_campaign_018_preregistration.json`](a_share_three_day_walkforward_campaign_018_preregistration.json)（SHA‑256 `3b59e6ad5d359a4b12a12280518ec978cf74ed08a4b79c2df3699a4a3a749812`）只冻结一个权重 1.0 的 higher 方向试验。2021/2022/2023 验证 mean Rank IC 为 `-0.004568/-0.024506/-0.016779`，normalized return 为 `-47.71%/-30.16%/+0.14%`，10bp 板手试点为 `-7.54%/-5.69%/-0.49%`；三折 IC 与 10bp 收益均没有正值，2022 可买率 `89.9543%` 低于冻结的 90%。2019–2023 aggregate normalized return 为 `-51.45%`，0/5/10/20bp 板手结果为 `-2.49%/-6.06%/-10.71%/-19.92%`。开发幸存者为 0，2024–2025 压力期没有打开或读取。

研究记录 [`a_share_three_day_walkforward_campaign_018_research_record.json`](a_share_three_day_walkforward_campaign_018_research_record.json)（SHA‑256 `b1d1af08a157adb1057dc12299bcb8e47bcb84369c7d45fe1d6c60b8b9ed6551`）和追加式状态 [`a_share_three_day_iteration_status_20260729_campaign018.json`](a_share_three_day_iteration_status_20260729_campaign018.json)（SHA‑256 `7d054e627d925267f7ee731251154df8a73afeba6d490e3f68aa42494f91e74b`）把累计开发试验推进到 241，当前聚合候选仍为 0。不得反向、替换 share volume 为 amount、替换振幅为 close return 或 true range、改成相邻变化/lead-lag/子窗口/市场归一化、删除零振幅或零成交量、加入活跃或幅度阈值、挑年份/成本、过滤或与终止因子组合后重测；也不得打开 Campaign018 压力期、回填 Candidate49、启动 Candidate50 或形成当前评分、选股、仓位、订单。Campaign019 只能从真正独立的概念、值前机制核重和精确有限预注册开始。

`python scripts/a_share_rich_data.py status` 现在还会输出 `qmt_xtquant_one_minute_acceptance`。该只读段落核对合同指纹、Windows 导出器与交接打包器是否存在、已消费验收/拒绝记录数、真实包是否出现、自动导入与显式对齐是否通过、QMT 验收锁是否正被占用，并给出唯一下一动作；它不会扫描仓库外目录、读取 K 线、访问网络或创建锁文件。没有真实包时，`next_action` 必须为 `run_frozen_windows_qmt_four_symbol_export_and_transfer_untouched_bundle`；拒绝记录出现后会要求停止并复核，成功导入后才会转为边界检查和显式对齐。

为了避免在 Windows 端复制整个研究仓库，可先在研究机生成一个确定性、无凭据的最小交接 ZIP。目标文件必须不存在；输出放在 Git 已忽略的 `data/` 下，不能提交 ZIP：

```bash
python scripts/package_qmt_acceptance_handoff.py \
  --output data/handoffs/qmt-1m-acceptance-handoff-v1.zip
```

ZIP 只含冻结导出器、冻结合同、逐文件 SHA‑256 清单和一个 PowerShell 启动器，共四个普通文件；不含 Token、账户、客户端路径、QMT 缓存、行情行、价格或收益。打包器使用固定 ZIP 时间戳、文件顺序、权限与不压缩存储，因此相同仓库输入会产生相同字节；现有目标绝不覆盖。它只读取这两个已跟踪文件，不导入 XtQuant、不访问网络。

把 ZIP 解压到 Windows 后，在用户已经依法可用的 MiniQMT/XtQuant Python 环境中进入 `qmt_acceptance_handoff`，运行一条命令；启动器会先复核导出器和合同哈希，再调用冻结导出命令，默认输出到同目录下全新的 `qmt-1m-acceptance-20260713`：

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_QMT_ACCEPTANCE_EXPORT.ps1
```

如果激活环境中的解释器命令不是 `python`，仅可通过 `-Python <命令>` 指定同一个合法 QMT Python；不得改启动器、导出器或合同。也可以继续从完整仓库副本直接运行下列等价命令；无论哪种方式，输出目录都必须不存在：

```powershell
python scripts/export_qmt_one_minute.py export-acceptance --output C:\qmt_exports\qlib_20260713_acceptance
```

脚本只调用 `download_history_data2` 与 `get_market_data_ex`，每个股票写一份确定性 gzip CSV，并生成 `qmt_1m_acceptance_export.json`。它不登录账户、不读取持仓或订单、不调用交易/Level‑2 接口，也不会输出 K 线内容。导出失败会删除隐藏临时目录，现有目标目录绝不覆盖。

把完整目录原样移到研究机后，从仓库根目录运行；不能手工改 CSV 或清单，也不能在目录里加入 `.DS_Store` 或其他文件：

```bash
python scripts/a_share_rich_data.py acceptance-qmt-1m-export \
  --manifest /绝对路径/qlib_20260713_acceptance/qmt_1m_acceptance_export.json
```

离线验收不联网，先绑定冻结合同与本地日线基座指纹，再逐字节校验清单和四份 gzip CSV；每股必须恰好有 240 个唯一、递增、同一种起始或结束标签的规则时间戳，并通过不复权 OHLC、成交额和成交量单位的本地日线对账。四股只能一起原子发布。任何失败都会写一份不含行情值的拒绝记录、删除临时快照，并永久消费该导出包，不能编辑后重试。

成功清单仍是 `automatic_checks_passed_pending_time_alignment`。人工核对清单中的四组首尾时间后，按验收器报告的 `observed_label` 与 `automatic_volume_unit` 单独确认；下面只是结束标签、股数单位的示例，不能不看清单直接照抄：

```bash
python scripts/a_share_rich_data.py confirm-minute-alignment \
  --manifest data/metadata/rich_data/runs/<QMT-acceptance-run>.json \
  --bar-label end \
  --volume-unit shares \
  --reviewed-boundaries
```

QMT 的对齐记录只会得到 `passed_pending_separate_full_source_no_return_protocol`，不会得到通用的 `passed_for_feature_research`；因此验收样本不能进入 `build-minute-features`。验收入口持有单一进程锁，意外发布错误也只能形成不含来源值的拒绝记录。当前仓库只有冻结合同、确定性交接包、导出器、严格离线验收器与伪 XtData 离线回归；本机仍没有观察任何真实 QMT 运行时或导出行。除非 Tushare 全量路线以后因来源或覆盖失败而明确切回备用，否则不再要求 Windows/QMT 验收。聚合、评分、选股、仓位、订单与 Level‑2 继续禁止。

### Tushare `stk_mins` 一分钟历史（当前首选，单日验收与对齐已通过）

用户确认单独购买并启用了 A 股历史分钟产品后，只运行了一次冻结的四股、单会话验收，没有直接启动多年全市场下载。官方主合同使用 [`stk_mins`](https://tushare.pro/document/2?doc_id=370)，仓库频率 `1m` 显式映射为接口频率 `1min`，只请求 `ts_code,trade_time,open,high,low,close,vol,amount`。接口文档说明单次最多 8,000 行，`vol` 单位为股、`amount` 单位为元；Token 仍只从 `TUSHARE_TOKEN` 环境变量读取，不能写入代码、命令、日志或清单。

真实验收固定为 2026‑07‑13 的 `600519/000001/300750/688981`。本地清单 `20260721T140021Z_tushare_1m_d57ea9d3.json` 的 SHA‑256 为 `a404aea025aec0335273d83d26cc39fe70e41e229da7aa1a8dd9e7752db9f2d0`；四份不可变 Parquet 均为 241 行，四股日 OHLC 相对误差全部为 0，成交额比率在 `0.9999999932–1.0000000031`，成交量相对本地“手”口径均为 100 倍，和官方“股”口径一致。跨克隆验收记录为 [`a_share_tushare_one_minute_source_acceptance_record.json`](a_share_tushare_one_minute_source_acceptance_record.json)（SHA‑256 `643f2177c80bfb77ba7bdbc84bd8cda3ad5feb222f1fc7309256f66436f75411`）。验收成功行由已安装 SDK 的 `pro_bar(freq=1min)` 内部委托 `stk_mins` 取得；随后适配器改为直接调用官方 `pro.stk_mins`，没有为了改调用方式重复下载已接受样本。

四股验收样本与官方样例都呈现独立的 09:30 行，随后是 09:31–15:00 的结束标签分钟行，因此验收时冻结了 241 行来源网格。显式对齐清单 `20260721T140521Z_tushare_1m_alignment_89ec2deb.json` 的 SHA‑256 为 `2c8c85ba1155289d03c3ebc1175a4a2504bf8022b849087840777ee41586e2a0`：保留原始 241 行，并预注册把 09:30 合并进 09:31。全市场下载后的无收益来源诊断发现，这一语义不能稳定外推到所有股票‑会话：部分 09:30 行价格为正但成交量和成交额均为零，更像参考价占位；部分剩余分钟最高/最低价或首分钟开盘价也与独立本地原始日线超出冻结的 0.2% 容差。原始 241 行仍完整保留，但既不能在观察后改价或改开盘规则，也不能放宽阈值让失败会话进入覆盖率。

全量无收益协议已经冻结为 [`a_share_tushare_one_minute_full_source_no_return_preregistration.json`](a_share_tushare_one_minute_full_source_no_return_preregistration.json)（SHA‑256 `ea0cbb8f2adc8f64a41627c4be1d62a6cc21dae3da755ffdf4d512996d974948`）。固定范围仍是 2019‑01‑01 至 2025‑12‑31，按 `factor_main_chinext_star` 点时区间估算共 1,699 个会话、5,396 只曾有效股票、7,751,950 个股票‑会话、最多 1,868,219,950 条来源行。每次只取一只股票、最多 33 个本地会话（最多 7,953 行）。冻结时的 237,628 次调用是允许跨日历年度连续分片的估算；可执行下载器为了让每个“股票 × 年度”分区能够独立验哈希和恢复，会在年度边界重新开始 33 日窗口，因此预检得到 255,955 次计划调用，多 18,327 次。安全限速固定为不超过 400 次/分钟，对应纯限速理论下限约 10.665 小时。按验收样本保守估计，单份压缩原始数据约 95.7–139.19 GiB，尚未计临时副本、规范特征、元数据和文件系统开销，因此全量开始前至少要求目标卷空闲 250 GiB。

用户已经明确授权使用 `/Volumes/DIsk`，当前固定根目录是 `/Volumes/DIsk/qlib-a-share-tushare-1m`。真实无网络预检通过：Tushare SDK 与 Token 环境就绪，目标卷约有 1,719.3 GiB 空闲，计划 33,015 个年度分区；记录明确为 `network_request_issued=false`、`minute_rows_read=false` 和 `forward_return_fields_read=false`。先运行预检，再用同一个绝对路径启动或恢复：

```bash
python scripts/a_share_rich_data.py preflight-tushare-1m \
  --data-root /Volumes/DIsk/qlib-a-share-tushare-1m
python scripts/a_share_rich_data.py sync-tushare-1m \
  --data-root /Volumes/DIsk/qlib-a-share-tushare-1m \
  --allow-large
```

全量命令持有 `/Volumes/DIsk/qlib-a-share-tushare-1m/.a_share_tushare_1m.lock`，先验哈希并跳过已完成分区，再以四个工作线程共享 400 次/分钟限速。数据先写入固定隐藏目录 `.tushare_stk_mins_1m_2019_2025_ea0cbb8f.partial`；每个 Parquet 和侧车完成原子写入后才计入检查点，全部来源与覆盖门通过后才把整个目录原子改名发布。中断时不要删除隐藏目录或仅凭锁文件存在判断任务仍活跃；使用只读状态检查锁是否真实持有、已完成分区、调用数和行数：

```bash
python scripts/a_share_rich_data.py status \
  --data-root /Volumes/DIsk/qlib-a-share-tushare-1m \
  | jq '.selected_minute_source.full_history'
```

首次运行曾因 `600000` 在 2019‑01‑04 的分钟最低价 9.72 与本地日线 9.70 相差 0.02 元而在质量门安全停止；开/高/收、成交额与成交量单位均一致。修正后的处理不改变 0.2% 对账阈值：完整 241 行原始会话仍保存，但未通过日线对账的会话不进入可用覆盖率；若成交量不再是已验收的“股”口径仍立即硬失败。重启已经验哈希跳过首次并发完成的分区，证明恢复路径有效。首个 `SH600000/2019` 分区为 58,804 行，即 244 个来源完整会话，无缺日、重复或越界时间；其中 237 个会话通过日线对账，7 个价差会话被明确列出并排除。

全量下载最终完成 33,015/33,015 个股票年度分区、255,955 次调用和 1,866,461,373 行来源数据；最终清单 SHA‑256 为 `9b3d959563c9d182f38981c6a36bdb3bc9b415de08487a9e1f9e850825c0839f`。7,751,950 个预期股票‑会话中有 7,724,581 个精确 241 行网格（99.6469%），但只有 7,320,317 个同时通过冻结的日线对账；404,506 个完整网格因日线对账失败被排除。日覆盖率中位数为 97.0892%，通过 95% 门槛；P05 仅 82.5709%，未达到 90%，最差的 2020‑03‑13 为 67.1402%。566 个非重叠三日 cohort 和七个年份满足数量门槛，但不能覆盖 P05 失败。

跨克隆终止审计是 [`a_share_tushare_one_minute_full_source_coverage_audit.json`](a_share_tushare_one_minute_full_source_coverage_audit.json)（SHA‑256 `5626c0f6523eeadd7739266f29a133b4e66852b1af0aebf84ef00ad88dadbfec`）。它明确记录原始快照保留、未改价、未放宽阈值、未读取分钟因子值或未来收益。不得重跑或续传同一 Tushare 全量协议，不得把原五因子协议改判为通过，也不得聚合、评分、选股、定仓、下单或据此采购 Level‑2。该审计形成时的下一路径是单独验收 QMT、RQData 或 JQData；后续用户另行授权的清洗分支只能作为新派生协议存在，不能反向修改这项终止结论。

用户随后明确授权把来源质量诊断转成一条独立、非破坏性的清洗研究支线。原始快照、原五因子协议和上面的失败审计均保持不变；清洗不是把分钟价格改成日线价格，也不是放宽原门槛。第一层协议 [`a_share_tushare_one_minute_sentiment_cleaning_protocol.json`](a_share_tushare_one_minute_sentiment_cleaning_protocol.json)（SHA‑256 `f70c7da688ecb6d2e88cd86f4ec086a42b620e0c12025ee9263fe603abe3a2fe`）只保留 `late_return_30m`、`late_amount_share_30m`、`late_vwap_to_day_vwap_30m` 和 `intraday_realized_volatility`：09:30 零量零额行的价格不进入 240 根规范路径，开盘和高低价不参与这四个因子，`opening_gap_digestion` 明确排除。

共同有效清洗快照包含 33,015 个派生分区、7,724,498 个股票‑会话，清单 SHA‑256 为 `453c6719cb3c7da42fed8807b28a2bfe988700283e9625a6db97912534f368de`。覆盖率中位数为 99.6865%、P05 为 99.1717%，最差会话仍有 98.1116%，566 个非重叠三日 cohort 覆盖七年，全部在读取收益之前通过。跨克隆结果是 [`a_share_tushare_one_minute_sentiment_cleaning_result.json`](a_share_tushare_one_minute_sentiment_cleaning_result.json)（SHA‑256 `2bd511045a1c9bc8a2b8d3bc566d4c0219c5764e8f1ae02c559125c99c6a4275`）。

为了避免“四个因子必须同时有效”的保守掩码，第二层协议 [`a_share_tushare_one_minute_fieldwise_cleaning_protocol.json`](a_share_tushare_one_minute_fieldwise_cleaning_protocol.json)（SHA‑256 `51e4fbf399411f62d35cbdb81d78651b4ceab17934264db0146cef61554d2fd6`）在冻结后只回读由第一层质量计数预先选出的 190 个异常分区，未重扫其余原始数据，并且读取列严格限于时间、身份、收盘、成交量和成交额。它生成 325 行、与共同有效基表键完全不重合的异常覆盖层；没有加载来源开盘/最高/最低，也没有改写或插补任何值：

| 因子 | 总可用股票‑会话 | 字段级新增 | 覆盖中位数 | 覆盖 P05 |
| --- | ---: | ---: | ---: | ---: |
| `late_return_30m` | 7,724,823 | 325 | 99.6884% | 99.1978% |
| `late_amount_share_30m` | 7,724,758 | 260 | 99.6883% | 99.1941% |
| `late_vwap_to_day_vwap_30m` | 7,724,498 | 0 | 99.6865% | 99.1717% |
| `intraday_realized_volatility` | 7,724,823 | 325 | 99.6884% | 99.1978% |

四个字段级覆盖门全部通过。异常层清单 SHA‑256 为 `06b5ffc2dac16f608d92e9eb7d93729800a2fa99e5727817caead3d698e19bd3`，Parquet SHA‑256 为 `046a5902c5fe3d6040df3a57185d445268cd025f6c922275363318123bc210c6`；跨克隆结果是 [`a_share_tushare_one_minute_fieldwise_cleaning_result.json`](a_share_tushare_one_minute_fieldwise_cleaning_result.json)（SHA‑256 `f0170519bb0ac8b49c7d48be9a65abd281e2b624e0360acdb63e1914dc429130`）。重建命令只复核固定哈希并返回已有清单；不会访问 Tushare 或读取收益：

```bash
python scripts/a_share_tushare_one_minute_sentiment_clean.py \
  build-fieldwise-overlay \
  --data-root /Volumes/DIsk/qlib-a-share-tushare-1m \
  --workers 4
```

这一步证明的是“清洗后的四个因子有足够样本可以研究”，不是“因子有效”。随后已经先冻结 [`a_share_tushare_cleaned_four_factor_exploratory_preregistration.json`](a_share_tushare_cleaned_four_factor_exploratory_preregistration.json)（SHA‑256 `88e08350aff470e8c7b92fe5f5971f770297d2ca513593971e24d59f07105ca7`），固定四个原方向、2019–2025、三日非重叠持有、Top‑3、0.012%/0.062% 成本、550 日财务新鲜度、上市满 20 日、逐因子覆盖、跨年稳定性、可成交 TopK 和 20 万元整手压力门槛。聚合只能取同时通过两道完整门槛的全部因子等权；少于两个停止，不允许枚举子集、反向、改窗口、调阈值、调权或切换聚合函数。

单次研究由 `scripts/a_share_tushare_cleaned_minute_factor_research.py` 执行。它先逐字节核验 33,015 个清洗分区，再合并 7,724,498 条共同有效基表和 325 条字段级补丁。质量与上市门禁后，四因子的覆盖门全部通过：最低 P05 覆盖 99.5689%，P05 截面 138 只股票，覆盖七个年份和 540 个潜在非重叠三日 cohort；这时才写入不可重复消费标记并读取收益。正式命令已经消费，不得再次运行；下面只保留复现入口，现有消费标记会在任何行情或收益访问前拒绝：

```bash
python scripts/a_share_tushare_cleaned_minute_factor_research.py diagnose \
  --minute-data-root /Volumes/DIsk/qlib-a-share-tushare-1m \
  --provider-uri data/qlib/cn_a_share \
  --fundamentals data/raw/a_share/fundamentals/quarterly_quality.parquet \
  --experiment-root data/experiments/short_horizon
```

539 个完整 cohort 的结果固化在 [`a_share_tushare_cleaned_four_factor_research_record.json`](a_share_tushare_cleaned_four_factor_research_record.json)（SHA‑256 `f3f2e7436667e746cfe20a9f594981a6f53d10efec2c498d8b08b115d46726c2`）。只有低 `intraday_realized_volatility` 通过相关性稳定门：平均 Rank IC 0.03028、正 IC 比例 59.74%、Top3−Bottom3 平均毛收益差 +0.4404%，且 2019–2025 每年平均 IC 均为正。但它没有通过可交易 Top3 门：执行感知累计收益 −94.74%、最大回撤 −95.36%、七年全部为负；20 万元、100 股整手、双边 10bp 滑点的试运行累计收益 −36.44%、回撤 −37.02%，整手可负担率只有 82.22%，并出现超过日成交额 1% 的交易。其余三因子连相关性门也未通过。双门禁交集为空，因此没有聚合模型、当前评分或选股结果；这个结果也不构成采购 Level‑2 的理由。下一步只能是先冻结一个经济机制真正不同的新候选，或积累注册后真正未见的分钟样本。

### 午后资金加权方向效率（收益与执行门终止）

四个清洗方向终止后，新候选在任何候选值或未来收益之前冻结为 [`a_share_tushare_afternoon_signed_amount_efficiency_no_return_preregistration.json`](a_share_tushare_afternoon_signed_amount_efficiency_no_return_preregistration.json)（SHA‑256 `072693166e96e228d734b3789db3613ea16d4fc87abfd35eb81edf1710f6d9b6`）。定义固定为 13:01–15:00 每分钟对数收益的成交额加权有符号和，除以成交额加权绝对收益和；13:01 的前一价格固定为 11:30 收盘，高值方向固定为更好。来源只读取 `datetime,symbol,provider,close,amount`，候选股票日严格等于联合清洗基表；开盘、最高、最低、成交量和日线价格都不进入因子。

可恢复构建器 [`a_share_tushare_afternoon_signed_amount_efficiency.py`](../scripts/a_share_tushare_afternoon_signed_amount_efficiency.py) 完成 33,015 个股票年度分区、7,724,498 行，其中 7,633,609 行有效，90,889 行因分母为零保持缺失，必需值异常为 0。外置候选清单 SHA‑256 为 `e1184b04385d1b0d1eb4a56ad6c21609c4387cf53324cbbb41c420cdb8ed5`，数据集内容 SHA‑256 为 `e580ce8bbcd7779256d344153def5d0587e1fd1ee8d59af63ef9e3d6a9254dd2`；原始分钟快照没有修改，也没有向分钟行补日线值。

首次无收益审计暴露了一个基础设施口径差异：自定义助手把最新已生效财报当成不可拆分的一行，而仓库标准 `attach_quality_asof` 会对 `roe/net_profit/revenue_yoy/profit_yoy` 四个已经披露的状态字段分别前向填充。两次诊断尝试都在写消费标记和构造未来收益之前停止。旧审计与旧收益协议被保留但废弃；修复边界先冻结在 [`a_share_tushare_afternoon_signed_amount_efficiency_quality_semantics_repair.json`](a_share_tushare_afternoon_signed_amount_efficiency_quality_semantics_repair.json)（SHA‑256 `2a22cd253249ec7e5574c77ae9e1ea9c9a0dadc717203d64c7198114fe5f87af`），只允许复现逐字段点时前向填充，不改变因子、方向、样本或门槛，并有离线回归覆盖“后续披露缺字段时保留此前已知值”。

校正后的唯一无收益审计 `20260722T131733Z`（SHA‑256 `a0203b564ba093d09cebe17ebcb36595e63b97f972a8c04bd29098198325ed7d`）得到 1,331,759 个质量/上市合格行和 1,321,007 个候选有效行；覆盖中位数 99.3716%、P05 98.2172%，P05 名称数 138，潜在三日非重叠 cohort 为 540，覆盖 2019–2025 七年。与四个终止分钟因子的最大绝对中位日秩相关为 0.58175，低于冻结的 0.8 门槛，因此覆盖、容量和独立性均通过；该审计没有读取未来收益。

新版收益协议 [`a_share_tushare_afternoon_signed_amount_efficiency_diagnostic_preregistration_v2.json`](a_share_tushare_afternoon_signed_amount_efficiency_diagnostic_preregistration_v2.json)（SHA‑256 `3d050a7c303ffae8dd09e31a4010d9128611accc76aac7a6399a21192c7f9eda`）随后才冻结并被唯一消费。539 个 cohort 的平均 Rank IC 为 +0.001963、正 IC 比例 51.39%，但 Top3−Bottom3 平均毛收益差为 −0.10215%；2019、2020、2021、2024、2025 年平均 IC 不为正，完整稳定性门失败。执行感知 Top‑3 累计 −70.97%、最大回撤 −88.51%；按 20 万元、100 股整手、双边 10bp 滑点和日成交额 1% 上限，试运行累计 −19.77%、最大回撤 −27.47%，可负担率 94.29%，最大成交额参与率 0.6584%，仍未通过执行门。

完整终止记录为 [`a_share_tushare_afternoon_signed_amount_efficiency_research_record.json`](a_share_tushare_afternoon_signed_amount_efficiency_research_record.json)（SHA‑256 `bd872c494f8dbfa7eed82e79a67d145a08e561dbdc5f36548f172fc79641cd1d`）。该精确高值方向永久退出 2019–2025 研究池；不得反向、改午后窗口、阈值化、加过滤、选年份、调权或重测，也不加入聚合候选，不生成当前评分或选股，不构成采购 Level‑2 的理由。后续只能提出经济机制真正不同且预先冻结的新候选，或积累注册后真正未见的数据。

### 午后最大回撤恢复韧性（收益与执行门终止）

资金加权方向效率终止后，没有把它倒过来或改窗口；新的 close-only 路径机制先冻结在 [`a_share_tushare_afternoon_drawdown_recovery_resilience_no_return_preregistration.json`](a_share_tushare_afternoon_drawdown_recovery_resilience_no_return_preregistration.json)（SHA‑256 `b4b1a15e5f8dc6073093bcd5ed52825c545e8f8cf228bee9ea9aa28e83eda6b8`）。路径从 11:30 收盘开始，连接 13:01–15:00 共 120 个分钟收盘；先找运行峰值到当前价格的最大对数回撤 `D` 及其最早谷底，再计算谷底到 15:00 的对数恢复 `R`，唯一因子为 `R / (D + R)`，高值固定为更好。它只读取 `datetime,symbol,provider,close`；开高低、成交量、成交额、日线价格和未来收益全部禁止进入候选构建。没有严格回撤的股票日保持缺失，不填充、裁剪或设人为阈值。

可恢复构建器 [`a_share_tushare_afternoon_drawdown_recovery_resilience.py`](../scripts/a_share_tushare_afternoon_drawdown_recovery_resilience.py) 完成 33,015 个股票年度分区和 7,724,498 行；7,631,291 行有效，93,207 行因最大回撤为零保持缺失，必需收盘异常与恢复恒等式违规均为 0。外置候选清单 SHA‑256 为 `a94413ba437dce44ef17215cce42c2d62e5aefab376f345df525dec3fd7a9c45`，数据集内容 SHA‑256 为 `07f1d0e83de44a1d533acf6e269bf34fc02d0c6ef582affdd96eac5c7af769c8`；原始分钟数据、联合清洗层和上一轮因子快照均未修改。

唯一无收益审计 `20260722T141606Z`（SHA‑256 `57227ee97c70155a69db5275514ad418c6a72ed467f1920a79eb2b578e4d8a36`）先复现逐字段点时质量语义，再得到 1,331,759 个质量/上市合格行和 1,320,685 个候选有效行；覆盖率中位数 99.3631%、P05 98.1340%，P05 名称数 138，潜在三日非重叠 cohort 为 540，覆盖 2019–2025 七年。覆盖门通过之后才加载五个终止分钟因子。最大绝对中位日秩相关为 0.60748（对尾盘 30 分钟收益），与上一轮午后资金效率为 0.34523，均低于冻结的 0.8 门槛；该审计没有读取任何未来收益。

一次性收益协议随后冻结为 [`a_share_tushare_afternoon_drawdown_recovery_resilience_diagnostic_preregistration.json`](a_share_tushare_afternoon_drawdown_recovery_resilience_diagnostic_preregistration.json)（SHA‑256 `9a4eb0da319e8acddd9cf8c22716d5bc408b46f4acb9408901651ea71b632515`）。唯一诊断 `20260722T142403Z` 在 539 个 cohort 上得到平均/中位 Rank IC −0.008087/−0.005694、正 IC 比例 46.20%、Top3−Bottom3 平均毛收益差 −0.4705%；2019、2020、2021、2024、2025 年平均 IC 不为正，关联稳定性门失败。执行感知 533 个完整信号累计 −82.70%、最大回撤 −88.90%；20 万元、100 股整手、双边 10bp 滑点账本累计 −26.02%、最大回撤 −30.13%，整手可负担率 92.22%，最大日成交额参与率 0.4122%，终端未平仓为 0。稳定性和 TopK 审计均为 0/1 通过。

完整终止记录为 [`a_share_tushare_afternoon_drawdown_recovery_resilience_research_record.json`](a_share_tushare_afternoon_drawdown_recovery_resilience_research_record.json)（SHA‑256 `b608fd9c8bbe3ba40aa433c39b2c31ff7a0bbff9abb31aa1905acf26ee9f48d5`）。这证明“较高恢复韧性”在冻结方向上无效，不授权在同一 2019–2025 历史上改成低方向、改谷底定义、换路径窗口、加过滤、挑年份、调权或重测。它不加入聚合候选，不生成当前评分/选股/仓位/订单，也不构成采购 Level‑2 的理由。

### 全日成交额参与熵（收益与执行门终止）

午后恢复韧性终止后，新机制在候选值、旧因子比较值和未来收益之前冻结为 [`a_share_tushare_intraday_amount_participation_entropy_no_return_preregistration.json`](a_share_tushare_intraday_amount_participation_entropy_no_return_preregistration.json)（SHA‑256 `66f5925b2883151fc051d20388d927646cd6a058744f07ae26253bf848454f5b`）。它只使用 09:31–11:30 与 13:01–15:00 的 240 个连续交易分钟成交额；09:30 独立来源行只参与 241 行网格身份校验，不进入公式。令每分钟成交额占全天连续交易段总额的比例为 `p_t`，唯一因子为归一化 Shannon 熵 `-sum(p_t log(p_t))/log(240)`，高值固定为更好。来源只读取 `datetime,symbol,provider,amount`；开高低收、成交量、日线价格和未来收益均不进入候选构建，不允许填充、裁剪、缩尾或删除零成交分钟。

可恢复构建器 [`a_share_tushare_intraday_amount_participation_entropy.py`](../scripts/a_share_tushare_intraday_amount_participation_entropy.py) 完成 33,015 个股票年度分区和 7,724,498 行，全部 7,724,498 行有效；连续段总成交额为零、必需成交额异常和熵越界均为 0。外置候选清单 SHA‑256 为 `58c9a9c8f3991fa94a3e5289ed0a72333dfc037dae1e7f318de29eca4f207631`，数据集内容 SHA‑256 为 `8d34ac56836fe1cc22157ac07f29e6a3ef94429008376e22e851730992b3891d`；同命令重跑只识别已发布清单，原始分钟数据和此前派生快照均未修改。

唯一无收益审计 `20260722T151427Z`（SHA‑256 `6cf5d5d16681c542dc915ebbdfa0c5a5ace62e370f2cf71c44f10840fd9ab6cd`）先得到 1,331,759 个质量/上市合格行和 1,330,171 个候选有效行；覆盖率中位数 99.9452%、P05 99.5689%，P05 名称数 138，潜在三日非重叠 cohort 为 540，覆盖 2019–2025 七年。覆盖门通过后才加载六个终止分钟因子；最大绝对中位日秩相关仅 0.108449（对低日内实现波动率方向分数），与上一轮午后恢复韧性为 −0.021331，六项均通过冻结的 0.8 独立性门。该阶段没有读取未来收益。

一次性收益协议随后冻结为 [`a_share_tushare_intraday_amount_participation_entropy_diagnostic_preregistration.json`](a_share_tushare_intraday_amount_participation_entropy_diagnostic_preregistration.json)（SHA‑256 `ec59d180c4d8c76dfe0183b45ec37eeb350e43756b9aefde473d0dbd17a20055`）。唯一诊断 `20260722T152154Z` 在 539 个 cohort 上得到平均/中位 Rank IC −0.012842/−0.011988、正 IC 比例 45.64%、Top3−Bottom3 平均毛收益差 +0.5098%；2020–2024 五年平均 IC 不为正，关联稳定性门失败。执行感知 533 个完整信号虽然累计 +124.70%，但最大回撤 −49.55%，2019、2022、2023 年为负，不能越过执行门。按 20 万元、100 股整手和双边 10bp 滑点，期末权益 199,790.98 元、累计 −0.1045%、最大回撤 −9.54%；整手可负担率仅 79.86%，最大日成交额参与率 0.0541%，试运行门同样失败。稳定性与 TopK 审计均为 0/1 通过。

完整终止记录为 [`a_share_tushare_intraday_amount_participation_entropy_research_record.json`](a_share_tushare_intraday_amount_participation_entropy_research_record.json)（SHA‑256 `6268a51a5210624e3b75283fc0a21e79f7572b9e82a31d670afa50dcf6a8f036`）。完整覆盖和低相关只证明数据可算且机制不同，不证明可预测性；标准化执行累计为正也不能覆盖负关联、年度不稳定、深回撤和 20 万元整手失败。该精确高值方向永久退出 2019–2025 研究池，不得改成低熵、换窗口、包含 09:30、删零成交分钟、阈值化、挑年份、加过滤、调权、组合后重测或采购 Level‑2 挽救；它不加入聚合候选，也不生成当前评分、选股、仓位或订单。

### 全日成交额序列持续性（收益与执行门终止）

参与熵终止后，新的有序路径机制在候选值、七个旧因子比较值和未来收益之前冻结为 [`a_share_tushare_intraday_amount_profile_serial_persistence_no_return_preregistration.json`](a_share_tushare_intraday_amount_profile_serial_persistence_no_return_preregistration.json)（SHA‑256 `f0eddc1fd2fe9586618d1375c53a0725d14f5a906157573e75ec59e4537b406d`）。它同样只使用 09:31–11:30 与 13:01–15:00 的 240 个连续交易分钟成交额，并排除 09:30；令 `x_t = log1p(amount_t)`，唯一因子为相邻 239 对的 Pearson 相关 `corr(x_1..x_239, x_2..x_240)`，高值固定为更好。常量序列保持缺失，除 IEEE 端点 `1e-12` 规范化外不裁剪。该因子依赖分钟顺序，而参与熵在分钟置换下不变，因此两者不是同一公式的重命名。

可恢复构建器 [`a_share_tushare_intraday_amount_profile_serial_persistence.py`](../scripts/a_share_tushare_intraday_amount_profile_serial_persistence.py) 完成 33,015 个股票年度分区和 7,724,498 行，其中 7,724,497 行有效，只有 1 条常量成交额序列；必需成交额异常、端点规范化和相关系数越界均为 0。外置候选清单 SHA‑256 为 `8c362725187c9e6021e64a07feadc6958e4334c65642dca0e0dc1eb4fccf7186`，数据集内容 SHA‑256 为 `a79d964f8d8a4d91f1f1bb29897753175c446b4ec649d92ddd4e6dbcc7b895e4`，原始分钟和已有派生快照未修改。

唯一无收益审计 `20260722T160810Z`（SHA‑256 `a95d03c6aef98f49dcd31f1ba3f3e6c7223f706b65e1283deba8a6689907345c`）得到 1,331,759 个质量/上市合格行和 1,330,171 个候选有效行；覆盖率中位数 99.9452%、P05 99.5689%，P05 名称数 138，潜在三日非重叠 cohort 540，覆盖 2019–2025 七年。覆盖门通过后才加载七个终止分钟因子；最大绝对中位日秩相关为 0.307500（对低日内实现波动率方向分数），与参与熵为 +0.282734，七项均通过冻结的 0.8 独立性门。该阶段没有读取未来收益。

一次性收益协议随后冻结为 [`a_share_tushare_intraday_amount_profile_serial_persistence_diagnostic_preregistration.json`](a_share_tushare_intraday_amount_profile_serial_persistence_diagnostic_preregistration.json)（SHA‑256 `a86f51d939da2b0221f16783d470fd528c595c54eccd9079f83064b41cc062c6`）。唯一诊断 `20260722T161536Z` 在 539 个 cohort 上得到平均/中位 Rank IC −0.024843/−0.022811、正 IC 比例 41.93%、Top3−Bottom3 平均毛收益差 +0.0441%；2019–2025 七年平均 IC 全部为负，关联稳定性门失败。执行感知 533 个完整信号累计 −41.21%、最大回撤 −88.67%，2020–2024 五年为负；20 万元、100 股整手和双边 10bp 滑点试运行累计 −14.85%、最大回撤 −29.21%，整手可负担率 92.07%、最大日成交额参与率 0.0824%，同样未通过 TopK 门。稳定性与 TopK 审计 SHA‑256 分别为 `22b0f97d7a86b39ac1dcee3b44770ad19d9e14b038fd39fffa38e08a8e2085dc` 和 `df7afa30d18fcc5383992e3a57e2288173f1ec2830f8b56342c0385607cb6b12`。

完整终止记录为 [`a_share_tushare_intraday_amount_profile_serial_persistence_research_record.json`](a_share_tushare_intraday_amount_profile_serial_persistence_research_record.json)（SHA‑256 `197899381a59f7a528c575e11a21310c15a41ac8b06232b1c8174648f2117b04`）。近乎完整的覆盖和低于 0.8 的相关只证明候选可算且统计上不重复，不能覆盖七年负 IC、执行亏损和深回撤。该精确高值方向永久退出 2019–2025 研究池，不得反向、换滞后、换窗口、阈值化、挑年份、加过滤、调权、组合后重测或采购 Level‑2 挽救；它不加入聚合候选，也不生成当前评分、选股、仓位或订单。

### 全日上行半方差占比（收益与执行门终止）

成交额序列持续性终止后，新的价格符号构成机制在候选值、八个旧因子比较值和未来收益之前冻结为 [`a_share_tushare_intraday_upside_semivariance_share_no_return_preregistration.json`](a_share_tushare_intraday_upside_semivariance_share_no_return_preregistration.json)（SHA‑256 `9fc26c9625e8223e9091042d6e07745780be4d4b570dbd51d742d556c295de14`）。它只读取 `datetime,symbol,provider,close`，排除独立的 09:30 记录，在 09:31–11:30 与 13:01–15:00 的 240 个连续收盘价上形成 239 个相邻对数收益，并计算正收益平方和占全部收益平方和的比例；11:30→13:01 对保留，高值方向预先固定为更好。零实现方差保持缺失，不填充、不统计裁剪，也不读取开高低、成交量、成交额或日线价格。

可恢复构建器 [`a_share_tushare_intraday_upside_semivariance_share.py`](../scripts/a_share_tushare_intraday_upside_semivariance_share.py) 完成 33,015 个股票年度分区和 7,724,498 行，其中 7,695,092 行有效，29,406 行因整日相邻收盘收益方差为零保持缺失；必需值异常、IEEE 端点规范化和比例越界均为 0。外置候选清单 SHA‑256 为 `81d121431a4ec79a839b592322ea1da22faf60191197ca1020f691d401bdab61`，数据集内容 SHA‑256 为 `4745113ff183f44f9dfab2114a5ff161471d2a8fba9f3aa529a45e25e4638c0b`，原始分钟和已有派生快照未修改。

唯一无收益审计 `20260722T170150Z`（SHA‑256 `974774bca4dce314cba205dab222a560e76a301275ae92148d0d74790d509e4a`）得到 1,331,759 个质量/上市合格行和 1,328,066 个候选有效行；覆盖率中位数 99.8318%、P05 99.3371%，P05 名称数 138，潜在三日非重叠 cohort 540，覆盖 2019–2025 七年。覆盖门通过后才加载八个终止分钟因子；最大绝对中位日秩相关为 0.420318（对尾盘 VWAP 相对全日 VWAP），与此前成交额序列持续性为 +0.092599，八项均通过冻结的 0.8 独立性门。该阶段没有读取未来收益。

一次性收益协议随后冻结为 [`a_share_tushare_intraday_upside_semivariance_share_diagnostic_preregistration.json`](a_share_tushare_intraday_upside_semivariance_share_diagnostic_preregistration.json)（SHA‑256 `ecb5217ac8cc2983fb3f69ce28e56a83c1741a3b58053628802c9db04cbac9d6`）。唯一诊断 `20260722T171145Z` 在 539 个 cohort 上得到平均/中位 Rank IC −0.017634/−0.015569、正 IC 比例 43.97%、Top3−Bottom3 平均毛收益差 −0.3853%；2019–2025 七年平均 IC 全部为负，关联稳定性门失败。执行感知 533 个完整信号累计 −96.89%、最大回撤 −97.63%，除 2020 外六年为负；20 万元、100 股整手和双边 10bp 滑点试运行累计 −40.05%、最大回撤 −41.96%，整手可负担率 94.11%、最大日成交额参与率 1.1150%，同样未通过 TopK 门。稳定性与 TopK 审计 SHA‑256 分别为 `2f3278201dd711c8b646c01906dca761bf9c3a29503448dfb099e8e8ce30b9b4` 和 `53b229dd4cf4000079e0ea571648b12173931a68c8a70813b86a6526cf206e76`。

完整终止记录为 [`a_share_tushare_intraday_upside_semivariance_share_research_record.json`](a_share_tushare_intraday_upside_semivariance_share_research_record.json)（SHA‑256 `a878729da102b9c4216f08a5c89707f58093541d8512dce522371d43d0d505b2`）。高覆盖和低于 0.8 的相关只证明候选可算且不与旧因子近似重复，不能覆盖七年负 IC、执行亏损和深回撤。该精确高值方向永久退出 2019–2025 研究池，不得在同一历史上反向为低占比、改成下行比率/差值、改窗口、阈值化、挑年份、加过滤、调权、组合后重测或采购 Level‑2 挽救；它不加入聚合候选，也不生成当前评分、选股、仓位或订单。

### 全日终点收盘位置（无收益近同义门终止）

上行半方差占比终止后，新的终点位置机制在候选值、九个旧因子比较值和未来收益之前冻结为 [`a_share_tushare_intraday_terminal_close_location_no_return_preregistration.json`](a_share_tushare_intraday_terminal_close_location_no_return_preregistration.json)（SHA‑256 `f15e3743458cdc7d52b68be50210fb35a76d8c3f5a62ed6415785a16ed4f1ef4`）。它只读取 `datetime,symbol,provider,close`，排除独立的 09:30 行，在 09:31–11:30 与 13:01–15:00 的 240 个连续收盘价上计算 `(15:00 收盘 − 分钟收盘最低值) / (分钟收盘最高值 − 分钟收盘最低值)`，高值预先固定为更好。零收盘区间保持缺失；不读取来源开高低、成交量、成交额、日线价格或未来收益，也不允许统计裁剪或填充。

可恢复构建器 [`a_share_tushare_intraday_terminal_close_location.py`](../scripts/a_share_tushare_intraday_terminal_close_location.py) 完成 33,015 个股票年度分区和 7,724,498 行，其中 7,695,092 行有效，29,406 行因全天 240 个分钟收盘价完全不变而缺失；必需值异常、IEEE 端点规范化和位置越界均为 0。外置候选清单 SHA‑256 为 `69a66d063cb470702db5e8b256f0b4be0f54c847c3188578fe85fba6ba63441c`，数据集内容 SHA‑256 为 `da90792615fa120d07417c8d9d5a2d8660a16f7c5ea5cd2bb09b5cb724eeba00`。第二次构建直接返回同一清单，原始分钟和已有派生快照均未修改。

唯一无收益审计 `20260722T175938Z`（SHA‑256 `1ff6a7b0b73192664145f97e2e9d66351b80fad20d4b8add19478d484ab559af`）先得到 1,331,759 个质量/上市合格行和 1,328,066 个候选有效行；覆盖率中位数 99.8318%、P05 99.3371%，P05 名称数 138，潜在三日非重叠 cohort 540，覆盖 2019–2025 七年，因此覆盖与容量门通过。此后才加载九个终止分钟因子。与较高 `late_vwap_to_day_vwap_30m` 的方向化中位日秩相关为 **+0.840148**，超过冻结的绝对值上限 **0.8**；其余八项通过也不能覆盖“所有九项必须通过”的规则。该审计没有读取日线价格或未来收益，且没有创建收益消费标记。

完整终止记录为 [`a_share_tushare_intraday_terminal_close_location_research_record.json`](a_share_tushare_intraday_terminal_close_location_research_record.json)（SHA‑256 `b5c0f740353e35df27d7f0390dbee7e500990fb4d7986550faadd632ab0ef0c9`）。高覆盖只说明公式可计算；超过近同义阈值说明它不能作为独立聚合候选再消耗同一段历史收益。该精确高值方向永久退出 2019–2025 研究池，不得反向、改用来源日高低、改终点、改窗口、做 signed/logit/量价加权变换、阈值化、挑年份、加过滤、调权或组合后重测；不创建收益诊断，不加入聚合候选，也不生成当前评分、选股、仓位或订单。

### 全日收益符号连跑不平衡（稳定性与执行门终止）

终点收盘位置在无收益近同义门停止后，新的顺序敏感机制在候选值、十个旧因子比较值和未来收益之前冻结为 [`a_share_tushare_intraday_return_sign_run_imbalance_no_return_preregistration.json`](a_share_tushare_intraday_return_sign_run_imbalance_no_return_preregistration.json)（SHA‑256 `180e59227db73815aa0af68a0cd6781fab801e1b35b544bffbbf2be0ca5a4609`）。它排除独立 09:30 行，从 240 个连续收盘价形成 239 个相邻对数收益和 238 个相邻符号对；`N_pp`/`N_nn` 分别计数 `++`/`--`，零收益和异号对不计入，因子固定为 `(N_pp-N_nn)/(N_pp+N_nn)`，高值为更好，零分母保持缺失。原预注册漏带点时点日历/持仓池/季度质量指纹，但在任何历史候选值、比较值或收益出现前以不可变补充记录 [`a_share_tushare_intraday_return_sign_run_imbalance_context_repair.json`](a_share_tushare_intraday_return_sign_run_imbalance_context_repair.json)（SHA‑256 `7d71fddba20e9753e93423ffa8bd9004dcd40e7698cdd29b78ca3a071b17a89c`）逐字继承上一轮相同上下文；因子、方向、公式、字段、日期和门槛均未改变。

构建器 [`a_share_tushare_intraday_return_sign_run_imbalance.py`](../scripts/a_share_tushare_intraday_return_sign_run_imbalance.py) 完成 33,015 个股票年度分区和 7,724,498 行，其中 7,605,471 行有效，119,027 行因没有任何 `++/--` 相邻对而缺失；必需值异常、非有限对数收益和范围越界均为 0。外置候选清单 SHA‑256 为 `e7e37808ed92c789c259296b57e3205c038dcc17f04b04d2ba32395d2cf52920`，数据集内容 SHA‑256 为 `265bb3da24be81ca1127028aecd5ffed79a7f9b35d094514bc7cc7b0cc01b20a`；确定性复跑返回同一清单。构建只读取 `datetime,symbol,provider,close`，未读取来源开高低、量额、日线价格、比较因子或未来收益。

有序无收益审计 `20260722T185243Z_intraday_return_sign_run_imbalance_no_return_audit.json`（SHA‑256 `ea9fe485af2693473a14649a20b242e51e1e0f95d64b8c1d9b3f47847598bfee`）先通过覆盖/容量：质量与上市资格行 1,331,759，候选有效行 1,322,098，中位/P05 覆盖 99.4565%/98.3852%，P05 有效股票 137，只形成 540 个不重叠三日 cohort，覆盖 2019–2025 七年。随后十项唯一性全部通过；最大绝对中位日秩相关为 0.439397，对全日终点收盘位置，低于冻结上限 0.8。至此仍未读取日线价格或未来收益。

唯一一次收益协议在读收益前冻结为 [`a_share_tushare_intraday_return_sign_run_imbalance_diagnostic_preregistration.json`](a_share_tushare_intraday_return_sign_run_imbalance_diagnostic_preregistration.json)（SHA‑256 `bd56f1dfc9c1d5e1c901e2e20c4cc31ca5499dc72f5142bbda20a65a745d9b13`）。正式诊断 `20260722T185949Z_factor_diagnostic.json`（SHA‑256 `9666f95f7234da2d79e7bd8c3e0c38f119767263fa184939a10e097c63197128`）包含 539 个 cohort：平均/中位 Rank IC 为 **−0.004743/−0.005093**，正 IC 比例 **48.05%**，2019、2020、2022–2025 年平均 IC 非正；虽然 Top‑3 减 Bottom‑3 平均毛差为 +0.03615%，但关联稳定性门失败。执行感知 Top‑3 累计 +18.51%，最大回撤 **−46.91%**，2019、2024、2025 年亏损。20 万元、100 股整手、双边 10bp 滑点账本累计 **−7.79%**，98.93% 的机会可以买到整手，最大成交额参与率 0.8722%，但 2019、2020、2022、2024、2025 年为负；零滑点为 +6.43%，5bp 已转为 −0.91%，说明结果不能覆盖现实摩擦。

完整稳定性审计 `20260722T190013Z_factor_stability_audit.json`（SHA‑256 `9a2cf88630a51b1eb740e10ecc22f23ce20289900544e84678c261a4771686d7`）和 Top‑3 可行性审计（SHA‑256 `b87e203ea6e9a6b3605060ca66db1128ef9d11a3d4e5840bf5cdc08112b5ac21`）均为 0/1 通过。终止记录为 [`a_share_tushare_intraday_return_sign_run_imbalance_research_record.json`](a_share_tushare_intraday_return_sign_run_imbalance_research_record.json)（SHA‑256 `ef325c59c061109248c360bcd836eea70ac4531dd29c1028bf74d5e599108139`）。该精确高值方向永久退出 2019–2025 研究池；不得反向、改为最长连跑/转移概率/收益自相关、改窗口、加入量价或波动权重、阈值化、挑年份、加过滤、调权、组合后重测或购买 Level‑2 挽救，也不生成当前评分、选股、仓位或订单。

### 全日波动率早晚分配（稳定性与执行门终止）

符号连跑分支终止后，新候选在任何候选值、十一项比较值或收益出现前冻结为 [`a_share_tushare_intraday_volatility_resolution_no_return_preregistration.json`](a_share_tushare_intraday_volatility_resolution_no_return_preregistration.json)（SHA‑256 `b17349eef3f17fc3b4a86c06ddde0b08c6b46f1fc6f3b90c0d3e5eb24230f1f2`）。它保留精确 241 行来源网格但排除独立 09:30 行，分别用 09:31–11:30 和 13:01–15:00 各 120 个收盘价形成 119 个相邻对数收益，明确排除 11:30→13:01 午休收益；因子固定为 `RV_am/(RV_am+RV_pm)`，高值为更好，总方差为零时保持缺失。构建器 [`a_share_tushare_intraday_volatility_resolution.py`](../scripts/a_share_tushare_intraday_volatility_resolution.py) 只读取 `datetime,symbol,provider,close`，不读取来源开高低、量额、日线替代值或收益。

外置快照含 33,015 个股票年度分区、7,724,498 行，其中 7,695,088 行有效，29,410 行因早晚段内总方差为零而缺失；必需值异常、非有限收益、端点规范化和范围越界均为 0。清单 SHA‑256 为 `da7d0a455697833a188e9cade9c1393ba16e7fef019e5a07b6f209c6db5cbc41`，数据集内容 SHA‑256 为 `2e2131445a6f41ffd96c666e41d5faaa528291ea0b8419833e2b6a69dce8a468`。有序无收益审计 `20260722T195227Z_intraday_volatility_resolution_no_return_audit.json`（SHA‑256 `d625bc29ebe66a9287465024e6ace9a2493097d8a17fd09734df4efdf85bffbf`）先通过覆盖/容量：1,331,759 个质量/上市行、1,328,065 个候选行，中位/P05 覆盖 99.8318%/99.3371%，P05 名称数 138，540 个潜在三日 cohort，覆盖七年。十一项唯一性全部通过，最大绝对中位日秩相关仅 0.247917，对尾盘成交额占比；至此没有读取日线价格或未来收益。

唯一收益协议 [`a_share_tushare_intraday_volatility_resolution_diagnostic_preregistration.json`](a_share_tushare_intraday_volatility_resolution_diagnostic_preregistration.json)（SHA‑256 `6d4a0c21e0a63a86457e69f8e905d83861dffffe5bb17f6c06737c34c161d519`）在审计通过后、首次收益读取前冻结。正式诊断 `20260722T195855Z_factor_diagnostic.json`（SHA‑256 `13b1d2431ab7e69f038823c17389ccfbaed8f86d4ecd37956b53d9320fb63ae2`）含 539 个 cohort：平均/中位 Rank IC 为 **−0.017821/−0.021111**，正 IC 比例 **43.04%**，Top‑3 减 Bottom‑3 平均毛差 **−0.05172%**；2021–2025 年平均 IC 均为负。执行感知 Top‑3 累计 **−92.29%**、最大回撤 **−95.93%**。20 万元、100 股整手、双边 10bp 滑点账本累计 **−34.81%**、最大回撤 **−36.40%**，整手机会可负担率 89.76%，最大成交额参与率 0.7107%；即使零滑点也累计亏损 26.62%。

稳定性审计 `20260722T195911Z_factor_stability_audit.json`（SHA‑256 `c50c438cf1d0db9fd345e83100a148a344db805431c3f4c73c8b6b0f5470d4f0`）和 Top‑3 审计 `20260722T195916Z_factor_topk_viability_audit.json`（SHA‑256 `c3b89cd7e552e26140db08f00c00cbeb907b56f11331e43ced94542f0a06b31f`）均为 0/1 通过。终止记录是 [`a_share_tushare_intraday_volatility_resolution_research_record.json`](a_share_tushare_intraday_volatility_resolution_research_record.json)（SHA‑256 `b40e639937359ff5f25a783e2834e7488463f152314870642daa6d572d172dc5`）。该精确高值方向永久退出 2019–2025：不得因负相关而改成低值优先，也不得改午休/09:30、分段、比例/差值、窗口、阈值、子集、过滤、年份、权重或组合后重测；不加入聚合池，不生成当前评分、选股、仓位或订单，也不采购 Level‑2 挽救。

### 分钟成交额领先下一分钟收益相关性（稳定性与执行门终止）

波动率早晚分配终止后，新候选在任何候选值、十二项比较值或收益出现前冻结为 [`a_share_tushare_intraday_amount_lead_return_correlation_no_return_preregistration.json`](a_share_tushare_intraday_amount_lead_return_correlation_no_return_preregistration.json)（SHA‑256 `702046343e2e1e38c73095a125a6023b20d926fce47a3234c32264d4340fb730`）。因子 `intraday_amount_lead_return_correlation_238p` 固定为高值更好：排除独立 09:30 和午休跨段对，只在上午、下午各 120 根连续分钟内，把较早一分钟的 `log1p(amount)` 与下一分钟 `log(close_next/close_prev)` 配成 119 对，共 238 对后计算 Pearson 相关；任一向量常数时保持缺失。构建器 [`a_share_tushare_intraday_amount_lead_return_correlation.py`](../scripts/a_share_tushare_intraday_amount_lead_return_correlation.py) 只读取 `datetime,symbol,provider,close,amount`，不读取来源开高低、成交量、日线替代值或未来收益。

外置不可变快照含 33,015 个股票年度分区、7,724,498 行，其中 7,695,088 行有效；常数成交额向量 1 行，常数下一分钟收益 29,410 行，必需值异常、非有限值、端点规范化和范围越界均为 0。清单 SHA‑256 为 `505e15e5015973fb3d32fc881b8b2845c419da8f327ec8abe3a681949621e55f`，数据集内容 SHA‑256 为 `65f1d3c70da7f1f90154129d5ce4af7b3ddde7dae5b387ec5a38e8ea612f18ce`。有序无收益审计 `20260722T205610Z_intraday_amount_lead_return_correlation_no_return_audit.json`（SHA‑256 `d47db6b57b48dba58d83e9656eda8801f9d347f78babc3593d485063fd3d72de`）先通过覆盖/容量：1,331,759 个质量/上市行、1,328,065 个候选行，中位/P05 覆盖 99.8318%/99.3371%，P05 有效名称 138，540 个潜在三日 cohort，覆盖七年。十二项唯一性全部通过，最大绝对中位日秩相关为 0.264759，对全日上行半方差占比；至此未读取日线价格或未来收益。

唯一收益协议 [`a_share_tushare_intraday_amount_lead_return_correlation_diagnostic_preregistration.json`](a_share_tushare_intraday_amount_lead_return_correlation_diagnostic_preregistration.json)（SHA‑256 `64113fbd408a6770f0c7e3dd927f6f7b0e0f0fd56af7679fac341c29dea58f2c`）在首次收益读取前冻结。正式诊断 `20260722T210127Z_factor_diagnostic.json`（SHA‑256 `f459dba216b12a9ef0e8654f034ac8aaa9ac2188c30706ae819263cdee0d1d38`）含 539 个 cohort：平均/中位 Rank IC 为 **−0.000567/−0.000524**，正 IC 比例 **49.54%**，Top‑3 减 Bottom‑3 平均毛差 **+0.06397%**，但 2020、2022、2024 年平均 IC 非正，关联稳定性门失败。执行感知 Top‑3 累计 **−61.28%**、最大回撤 **−80.76%**。20 万元、100 股整手、双边 10bp 滑点账本累计 **−25.09%**、最大回撤 **−28.07%**，整手机会可负担率 89.87%，也低于冻结的 90% 门槛；最大成交额参与率 0.6049%，终态未解决持仓为 0。

稳定性审计 `20260722T210147Z_factor_stability_audit.json`（SHA‑256 `70e213531b0216fb38a54b32557307a9080af238ec5c71de3036ba4bcec85a90`）和 Top‑3 审计 `20260722T210147Z_factor_topk_viability_audit.json`（SHA‑256 `fcba802b687cccfd57ffdeba51b7a891d3f934fb5e16e75f2efac69399ee1f68`）均为 0/1 通过。单次诊断消费标记 SHA‑256 为 `eb7117f72e6fab1a4c618b0f8f54c37a101b2e08b10b469373fb7301eeff7a41`；终止记录是 [`a_share_tushare_intraday_amount_lead_return_correlation_research_record.json`](a_share_tushare_intraday_amount_lead_return_correlation_research_record.json)（SHA‑256 `6d19191b7c4d48b96decba444cc815d052f3f5ae4c1414ea290cf186a3384a01`）。该精确高值方向永久退出 2019–2025：不得因结果接近零而反向、改配对/午休/09:30、窗口、变换、阈值、子集、过滤、年份、权重或组合后重测；不加入聚合池，不训练模型，不生成当前评分、选股、仓位或订单，也不采购 Level‑2 挽救。

### 全日成交额重心（稳定性与执行门终止）

成交额领先收益路线终止后，新候选在任何候选值、十三项比较值或未来收益出现前冻结为 [`a_share_tushare_intraday_amount_center_of_mass_no_return_preregistration.json`](a_share_tushare_intraday_amount_center_of_mass_no_return_preregistration.json)（SHA‑256 `c9a22da2f2fffeb54c7500de24b1c5cfb866520fef276fa9a533ea44f7d66f7a`）。`intraday_amount_center_of_mass_240m` 固定为高值更好：保留来源的 241 行完整网格但从公式排除独立 09:30 行，在 09:31–11:30 与 13:01–15:00 的 240 根连续成交额上使用归一化序号 `i/239`，计算 `sum(A_i * (i/239)) / sum(A_i)`；午休时钟间隔被折叠为相邻观测序号，不获得额外权重。构建器 [`a_share_tushare_intraday_amount_center_of_mass.py`](../scripts/a_share_tushare_intraday_amount_center_of_mass.py) 只读取 `datetime,symbol,provider,amount`，不读取来源开高低收、成交量、日线替代值或未来收益。

第一次构建在原始股票年度分区含有联合清洗基准区间之外的日期时停止，没有发布最终快照、加载比较值或读取收益。修复只把原始日期过滤到预登记的联合基准日期集合，并增加离线回归；公式、方向、字段和门禁均未改变，随后复用 45 个哈希绑定的可恢复分区。最终外置快照含 33,015 个股票年度分区和 7,724,498 行，全部因子有效；总成交额为零、必需值异常、加权和非有限、端点规范化和范围越界均为 0。清单 SHA‑256 为 `f96f40d25f65b65914e40f1ca71f604961266d05540d90c04e0d3e80c9e0df03`，数据集内容 SHA‑256 为 `ecce1174ec94f8ba91372da0edfc00007ef1acdfc20ee09c63b38ea6daf7adfd`。

有序无收益审计 `20260722T215242Z_intraday_amount_center_of_mass_no_return_audit.json`（SHA‑256 `4281e8ecd51afe81a6f9af205511440140c63233df48669c0f2c6f46178375a6`）先通过覆盖和容量：质量/上市资格行 1,331,759，候选有效行 1,330,171，中位/P05 覆盖 99.9452%/99.5689%，P05 有效名称 138，形成 540 个潜在不重叠三日 cohort，覆盖 2019–2025 七年。随后十三项唯一性全部通过；最大绝对中位日秩相关为 0.636094，对尾盘 30 分钟成交额占比，低于冻结的 0.8 上限。审计阶段没有加载日线价格或未来收益。

唯一收益协议在首次收益读取前冻结为 [`a_share_tushare_intraday_amount_center_of_mass_diagnostic_preregistration.json`](a_share_tushare_intraday_amount_center_of_mass_diagnostic_preregistration.json)（SHA‑256 `5f9c7563939d4dbd6afc3fdb61f7f98307774c6b6a160820f546fee6252d4795`）。正式诊断 `20260722T215740Z_factor_diagnostic.json`（SHA‑256 `1f0419141b6649556b0bb934856d7d43ef465fa78994576144b5857665a03262`）含 539 个 cohort：平均/中位 Rank IC 为 **+0.006335/+0.003540**，正 IC 比例 **51.39%**，但 Top‑3 减 Bottom‑3 平均毛差为 **−0.04788%**，2019、2020、2024 年平均 IC 为负，关联稳定性门失败。执行感知 533 个完整信号累计 **−59.04%**、最大回撤 **−82.52%**，2020–2024 年均非正。20 万元、100 股整手、双边 10bp 滑点账本累计 **−20.62%**、最大回撤 **−25.11%**，整手机会可负担率 95.62%，但最大成交额参与率 **1.0619%**，超过冻结的 1% 上限；零滑点仍累计亏损 8.01%。

完整稳定性审计 `20260722T215817Z_factor_stability_audit.json`（SHA‑256 `b53c875a7d8a4dcdd0228280bb536d0d2e53ddcbe35451a4764562abd88c9507`）和 Top‑3 可行性审计 `20260722T215818Z_factor_topk_viability_audit.json`（SHA‑256 `b51a6aaba302c7d89a59481330ca06c7ae0a6d7c9f223fc9706ab6e5f8616e24`）均为 0/1 通过。单次诊断消费标记 SHA‑256 为 `7b529da37886fbeeaf287bfb75578823e3690fc880a57cf8bcfa0637bd14c341`；终止记录是 [`a_share_tushare_intraday_amount_center_of_mass_research_record.json`](a_share_tushare_intraday_amount_center_of_mass_research_record.json)（SHA‑256 `79a36ae4f3b3c74078ec0680d4e3e4b31c9b90f08ccb73e81089aff483d14dd0`）。该精确高值成交额到达时序方向永久退出 2019–2025：不得反向、改归一化时钟或午休处理、改窗口、变换、阈值、子集、过滤、年份、权重或组合后重测；不加入聚合池，不训练模型，不生成当前评分、选股、仓位或订单，也不采购 Level‑2 挽救。

### 全日上涨分钟成交额占比（稳定性与执行门终止）

成交额重心终止后，第 39 个候选在任何候选值、十四项比较值或未来收益出现前冻结为 [`a_share_tushare_intraday_up_move_amount_share_no_return_preregistration.json`](a_share_tushare_intraday_up_move_amount_share_no_return_preregistration.json)（SHA‑256 `0f7861e8be777f6de2df9576e334bfdf03a98da8b6248fbf27e3e78387597eed`）。`intraday_up_move_amount_share_238m` 固定为高值更好：保留 241 行来源网格但排除独立 09:30，在上午和下午各 120 根连续收盘价内分别形成 119 个相邻对，不计算 11:30→13:01 午休跨段收益；把每个非零对数收益与目标分钟成交额配对，计算上涨目标分钟成交额除以全部非零涨跌目标分钟成交额。零涨跌分钟成交额不进入任一求和，分母为零时保持缺失。构建器 [`a_share_tushare_intraday_up_move_amount_share.py`](../scripts/a_share_tushare_intraday_up_move_amount_share.py) 只读取 `datetime,symbol,provider,close,amount`，不读取来源开高低、成交量、日线替代值或未来收益。

外置不可变快照含 33,015 个股票年度分区和 7,724,498 行，其中 7,695,088 行有效；29,410 行因所有非零涨跌目标分钟成交额之和为零而保持缺失，必需收盘价、必需成交额、非有限收益/求和、端点规范化和范围越界均为 0。清单 SHA‑256 为 `d7d839c70c2289c9f05182de5ade655f31a0006c3871fcf9273cf17e2404d634`，数据集内容 SHA‑256 为 `f549ce8dc479dbe48a8bba13c5b013e3ea0d2218a8cfd0d8eaabf268fbb1de76`。有序无收益审计 `20260722T225834Z_intraday_up_move_amount_share_no_return_audit.json`（SHA‑256 `f87566c8256f6a95a0e3e67f58bd520396972bc82b7c20457dd5ec5ef833aabb`）先通过覆盖/容量：1,331,759 个质量/上市行、1,328,065 个候选行，中位/P05 覆盖 **99.8318%/99.3371%**，P05 有效名称 138，540 个潜在不重叠三日 cohort，覆盖七年。十四项唯一性全部通过，最大绝对中位日秩相关为 **0.577328**，对全日终点收盘位置；与成交额重心仅为 **0.0177515**。此阶段日线价格和未来收益均未读取。

唯一收益协议在首次未来收益读取前冻结为 [`a_share_tushare_intraday_up_move_amount_share_diagnostic_preregistration.json`](a_share_tushare_intraday_up_move_amount_share_diagnostic_preregistration.json)（SHA‑256 `0866b66b8c4bf1e4f12bf61b0a3e1546ff5103b4e44f4737e769f2d3d41fc271`）。正式诊断 `20260722T230420Z_factor_diagnostic.json`（SHA‑256 `6c1090ba0e04dba117d6c6d56f0d42a1339cd14c1261cd457e96d4e59183f40e`）含 539 个 cohort：平均/中位 Rank IC 为 **−0.004682/−0.004847**，正 IC 比例 **47.31%**，Top‑3 减 Bottom‑3 平均毛差 **−0.11893%**；只有 2023 年平均 IC 为正，关联稳定性门失败。执行感知 533 个完整信号累计 **−81.28%**、最大回撤 **−91.79%**。20 万元、100 股整手、双边 10bp 滑点账本累计 **−25.77%**、最大回撤 **−31.31%**，整手机会可负担率 **94.75%**，最大成交额参与率 **1.0204%** 超过冻结的 1% 上限；即使零滑点仍累计亏损 **17.10%**。

完整稳定性审计 `20260722T230510Z_factor_stability_audit.json`（SHA‑256 `aab2de1f07ee0ded7913a868b02588464ba1ed52f2bf627a68d5933f7ba00f6f`）和 Top‑3 可行性审计 `20260722T230511Z_factor_topk_viability_audit.json`（SHA‑256 `b2c31fd4e124f5926494a95451c7d378fc3ee45be89f6a422c05834165c2dceb`）均为 0/1 通过。单次消费标记 SHA‑256 为 `0c6a181f955c0b709085ca8b30e044b45f815584eb2cfb7012b6a9aca0bd0f37`；终止记录是 [`a_share_tushare_intraday_up_move_amount_share_research_record.json`](a_share_tushare_intraday_up_move_amount_share_research_record.json)（SHA‑256 `ae6af77dcb554cba1adffac56462b49a69afad01269d2c7198722052707b5de2`）。该精确高值成交额方向分配机制永久退出 2019–2025：不得反向为“下跌分钟成交额占比”、改收益阈值/幅度权重/午休/09:30/窗口、变换、子集、过滤、年份、权重或组合后重测；不加入聚合池，不训练模型，不生成当前评分、选股、仓位或订单，也不采购 Level‑2 挽救。

### 全日扩散变差比（稳定性与执行门终止）

第 40 个候选在任何候选值、十五项比较值或未来收益出现前冻结为 [`a_share_tushare_intraday_diffusive_variation_ratio_no_return_preregistration.json`](a_share_tushare_intraday_diffusive_variation_ratio_no_return_preregistration.json)（SHA‑256 `db16eac2ed99dba863a94be9d9debd52c9bc62dbe291cb1faf7b9bfe7c2cf05f`）。`intraday_diffusive_variation_ratio_238m` 固定为高值更好：只用 09:31–11:30 和 13:01–15:00 的 240 个收盘价，分别形成上午、下午各 119 个相邻对数收益；分子为两段内相邻绝对收益乘积之和乘 `pi/2`，分母为 238 个收益平方和。09:30、跨午休收益和跨午休 bipower 对都不参与；实现方差为零保持缺失。构建器 [`a_share_tushare_intraday_diffusive_variation_ratio.py`](../scripts/a_share_tushare_intraday_diffusive_variation_ratio.py) 只读取 `datetime,symbol,provider,close`。

外置不可变快照含 33,015 个股票年度分区、7,724,498 行和 7,695,088 个有效值；29,410 行因实现方差为零而缺失，其余必需值、非有限收益/分量/比率、端点规范化和范围越界均为 0。清单 SHA‑256 为 `ead71a5fc82e25b2b90467ea7e3a66070440c2eedb53b1beb78e14723a25074b`，数据集内容 SHA‑256 为 `28ae11c5f51e667dca1216851bb9e364d23af31d9f79f21686a4f14e78432372`。有序无收益审计 `20260723T001116Z_intraday_diffusive_variation_ratio_no_return_audit.json`（SHA‑256 `e25ecaee8617825284b4134a718fc3a048870c8235abbd184fc58286bb4ab4f4`）先通过覆盖/容量：1,331,759 个质量/上市行、1,328,065 个候选行，中位/P05 覆盖 **99.8318%/99.3371%**，P05 有效名称 138，540 个潜在不重叠三日 cohort，覆盖七年。十五项唯一性全部通过，最大绝对中位日秩相关为 **0.342908**，对全日成交额参与熵；此阶段未读取日线价格或未来收益。

唯一收益协议 [`a_share_tushare_intraday_diffusive_variation_ratio_diagnostic_preregistration.json`](a_share_tushare_intraday_diffusive_variation_ratio_diagnostic_preregistration.json)（SHA‑256 `ca16edb3a78bb47aa6f8795458eea33b82f58a0ddafb7236cf3c0426eb79cb12`）在首次未来收益读取前冻结。正式诊断 `20260723T001737Z_factor_diagnostic.json`（SHA‑256 `38b857b21df1ae001ddf73734f74d0fb884bbf822701c516aab593049c1271ce`）含 539 个 cohort：平均/中位 Rank IC 为 **−0.022508/−0.017018**，正 IC 比例 **44.16%**，Top‑3 减 Bottom‑3 平均毛差 **−0.14042%**；2021–2025 年平均 IC 均为负。执行感知 533 个完整信号累计 **−85.59%**、最大回撤 **−91.58%**。20 万元、100 股整手、双边 10bp 滑点账本累计 **−23.24%**、最大回撤 **−26.59%**，整手机会可负担率 **87.78%**，最大成交额参与率 **0.07277%**；零滑点仍累计亏损 **14.35%**。

稳定性审计 `20260723T001811Z_factor_stability_audit.json`（SHA‑256 `7c30f02442c698b522d35c131364a78f360c3d5f349b2ca57de40c4d65b14bd3`）和 Top‑3 可行性审计 `20260723T001811Z_factor_topk_viability_audit.json`（SHA‑256 `6f7ecae484237edf6ae04430013d9faa2775a79063ab54ff50bf00fd6f9b987f`）均为 0/1 通过。单次消费标记 SHA‑256 为 `d4f4720ee108c3553df8b6d44fc8524e0e23c0aad41962fe33d8deba53fa89fb`；终止记录是 [`a_share_tushare_intraday_diffusive_variation_ratio_research_record.json`](a_share_tushare_intraday_diffusive_variation_ratio_research_record.json)（SHA‑256 `c09e46bba9fe60dc611f6718dacf0b14928a8bd9f6d6b74835ac369e7c0ed086`）。该精确高值扩散变差机制永久退出 2019–2025：不得因整体负相关而反向、改变 bipower/实现方差定义、加入 09:30 或午休对、改窗口/阈值/子集/年份/权重或组合后重测；不加入聚合池，不训练模型，不生成当前评分、选股、仓位或订单，也不采购 Level‑2 挽救。

### 全日成交额—绝对收益同步耦合（稳定性与执行门终止）

第 41 个候选在任何候选值、十六项比较值或未来收益出现前冻结为 [`a_share_tushare_intraday_amount_volatility_coupling_no_return_preregistration.json`](a_share_tushare_intraday_amount_volatility_coupling_no_return_preregistration.json)（SHA‑256 `71de0d8214daaed1025149747c16b7dd94e682a8881318fef98899eff89a5142`）。`intraday_amount_volatility_coupling_238p` 固定为高值更好：排除 09:30 和午休边界，在上午、下午各 119 个相邻对数收益上，将每个收益与终点分钟的 `log1p(amount)` 配对，计算 238 对成交额与绝对收益的 Pearson 相关；任一向量为常数则保持缺失。构建器 [`a_share_tushare_intraday_amount_volatility_coupling.py`](../scripts/a_share_tushare_intraday_amount_volatility_coupling.py) 只读取 `datetime,symbol,provider,close,amount`。

外置不可变快照含 33,015 个股票年度分区、7,724,498 行和 7,695,088 个有效值；29,410 行因绝对收益向量为常数而缺失，成交额常数、必需值异常、非有限配对/相关、端点规范化和范围越界均为 0。清单 SHA‑256 为 `ffe853163c8acfe7cb7accd8dde69ad15768160d8346386a849978f845215600`，数据集内容 SHA‑256 为 `b74f30139ae9529700e91e2e019e769ae8b38086dc27866798e2b41dbec22f06`。有序无收益审计 `20260723T011732Z_intraday_amount_volatility_coupling_no_return_audit.json`（SHA‑256 `88627b1cc3c5debcc61651d273d2dccefee56affdb849746389cdede79abbb50`）先通过覆盖/容量：1,331,759 个质量/上市行、1,328,065 个候选行，中位/P05 覆盖 **99.8318%/99.3371%**，P05 有效名称 138，540 个潜在不重叠三日 cohort，覆盖七年。十六项唯一性全部通过，最大绝对中位日秩相关为 **0.341766**，对全日成交额参与熵；此阶段未读取日线价格或未来收益。

唯一收益协议 [`a_share_tushare_intraday_amount_volatility_coupling_diagnostic_preregistration.json`](a_share_tushare_intraday_amount_volatility_coupling_diagnostic_preregistration.json)（SHA‑256 `4afd6fc54f42609a71a235831569ade0423ce883b59dc595780ecc9cd6c614db`）在首次未来收益读取前冻结。正式诊断 `20260723T012430Z_factor_diagnostic.json`（SHA‑256 `0240fe6d362e550446edd78eb43e70b14df630c6b93d2c31d459738c5c0d761a`）含 539 个 cohort：平均/中位 Rank IC 为 **−0.017633/−0.018947**，正 IC 比例 **42.67%**，Top‑3 减 Bottom‑3 平均毛差 **+0.01604%**；2019–2025 每一年平均 IC 都不为正，关联稳定性门失败。执行感知 533 个完整信号累计 **+7.59%**，但最大回撤达到 **−64.97%**，且 2021、2022、2024、2025 年亏损。20 万元、100 股整手、双边 10bp 滑点账本累计 **−6.22%**、最大回撤 **−16.95%**，整手机会可负担率 **96.49%**，最大成交额参与率 **1.4784%** 超过冻结的 1% 上限；零滑点累计 **+6.17%**，不足以通过成本和容量门。

稳定性审计 `20260723T012523Z_factor_stability_audit.json`（SHA‑256 `db34499cb198dc797a67e1c4e38dac751adeddfb02208ecafadbcd6107f9f977`）和 Top‑3 可行性审计 `20260723T012524Z_factor_topk_viability_audit.json`（SHA‑256 `6be765ab763d8f500c27620a79022c477e9325cc8322a95b93f1962de678c634`）均为 0/1 通过。单次消费标记 SHA‑256 为 `8dbe497566f923c0e5c6fb30f18ce4b7f32bded900d237b534fc4e85fe3485c6`；终止记录是 [`a_share_tushare_intraday_amount_volatility_coupling_research_record.json`](a_share_tushare_intraday_amount_volatility_coupling_research_record.json)（SHA‑256 `3c6803bd073f6afa35501e4ee766b235d588a496311f610a9e58e794bfef647f`）。该精确高值同步耦合机制永久退出 2019–2025：不得因整体负相关而反向、改变成交额/绝对收益变换或配对方向、加入 09:30 或午休对、改窗口/阈值/子集/年份/过滤/权重或组合后重测；不加入聚合池，不训练模型，不生成当前评分、选股、仓位或订单，也不采购 Level‑2 挽救。

### 日内收益方差熵（关联稳定通过、执行门终止）

第 42 个候选在任何候选值、十七项比较值或未来收益出现前，以机制核重记录 [`a_share_tushare_intraday_return_variance_entropy_mechanism_overlap_reaudit_20260723.json`](a_share_tushare_intraday_return_variance_entropy_mechanism_overlap_reaudit_20260723.json)（SHA‑256 `ab7a398f56fb3930d2794231b900c7e859f8a601d299129a4e798ff29cbffa2d`）和无收益预登记 [`a_share_tushare_intraday_return_variance_entropy_no_return_preregistration.json`](a_share_tushare_intraday_return_variance_entropy_no_return_preregistration.json)（SHA‑256 `0493b2855e9e9c8d01e3a233cf5e7198fbb8b8ae303cf4f3d1d02be488cce5d3`）冻结。`intraday_return_variance_entropy_238m` 固定为高值更好：排除 09:30 和午休边界，上午、下午各取 119 个相邻对数收益，将 238 个平方收益按两半日位置归一化为概率后计算以 `log(238)` 标准化的 Shannon 熵；全日实现方差为零时保持缺失。构建器 [`a_share_tushare_intraday_return_variance_entropy.py`](../scripts/a_share_tushare_intraday_return_variance_entropy.py) 只读取 `datetime,symbol,provider,close`。

外置不可变快照含 33,015 个股票年度分区、7,724,498 行和 7,695,088 个有效值；29,410 行因全日实现方差为零而缺失，必需值、非有限收益/分量、端点规范化和范围越界均为 0。清单 SHA‑256 为 `f1905de2c51540d55369b8c84117f63bfd509db31dad79c933c90559d880556c`，数据集内容 SHA‑256 为 `e49b7856b59dd5c24eaeb4a6748066dd0e42c2636495325d7b961d1844eb6775`。有序无收益审计 `20260723T023219Z_intraday_return_variance_entropy_no_return_audit.json`（SHA‑256 `8c1c7a1f32de94125ee524a6185e5297bdd423fcaf6034eebbab7b5a227e3d14`）先通过覆盖/容量：1,331,759 个质量/上市资格行、1,328,065 个候选行，中位/P05 覆盖 **99.8318%/99.3371%**，P05 有效名称 138，540 个潜在不重叠三日 cohort，覆盖七年。十七项唯一性全部通过，最大绝对中位日秩相关为 **0.494584**，对全日波动率早晚分配；此阶段未读取日线价格或未来收益。

唯一收益协议 [`a_share_tushare_intraday_return_variance_entropy_diagnostic_preregistration.json`](a_share_tushare_intraday_return_variance_entropy_diagnostic_preregistration.json)（SHA‑256 `1dc70c8b1b4075dcecbf9a03440da5e7054e582ec6c8abab3587a4539aec67b4`）在首次未来收益读取前冻结。正式诊断 `20260723T024057Z_factor_diagnostic.json`（SHA‑256 `2b4a51c3f540258c7712ce637bef52d3a002104ca915f20e09c5a25a7d6f5b7a`）含 539 个 cohort：平均/中位 Rank IC 为 **+0.020849/+0.022411**，正 IC 比例 **58.998%**，Top‑3 减 Bottom‑3 平均毛差 **+0.37420%**；2019–2025 每年平均 IC 都为正，关联稳定性门通过。但执行感知 533 个完整信号累计 **+13.66%**、最大回撤 **−45.27%**，且 2019、2020、2023 年为负。20 万元、100 股整手、双边 10bp 滑点账本累计 **−8.50%**、最大回撤 **−12.33%**，整手机会可负担率 **97.94%**，最大成交额参与率 **0.0680%**；0/5/10/20bp 滑点累计分别为 **+6.14%/−1.70%/−8.50%/−21.33%**。

稳定性审计 `20260723T024129Z_factor_stability_audit.json`（SHA‑256 `42b9fec6621443b7716d1690cb1f94f08443b2963e6c21024d7de251b83a0e1d`）为 1/1 关联通过，Top‑3 可行性审计 `20260723T024130Z_factor_topk_viability_audit.json`（SHA‑256 `5c8be84690d5cc4d03c575706e9a7036f0a51de40149ef5102d91d6b62171551`）为 0/1 通过。单次消费标记 SHA‑256 为 `186f65abe7d60d03a6a69f59461cedca02306341023f157dc41032b6507e8745`；终止记录是 [`a_share_tushare_intraday_return_variance_entropy_research_record.json`](a_share_tushare_intraday_return_variance_entropy_research_record.json)（SHA‑256 `7f79ff0b09a132bcd6af0e1a4c6401de58105cf0c778c6625dada71ba11b07f1`）。该精确高值收益方差熵机制因可执行 Top‑3 门失败而永久退出 2019–2025：不得反向、改熵或平方收益定义、改方向/窗口/阈值/子集/年份/过滤/权重或组合后重测；不加入聚合池，不训练模型，不生成当前评分、选股、仓位或订单，也不采购 Level‑2 挽救。

### 日内收益偏度（无收益近同义门终止）

第 43 个候选在任何候选值、十八项比较值或未来收益出现前，以机制核重记录 [`a_share_tushare_intraday_return_skewness_mechanism_overlap_reaudit_20260723.json`](a_share_tushare_intraday_return_skewness_mechanism_overlap_reaudit_20260723.json)（SHA‑256 `e87d343ff41a32ee19497767420a4a01dd4a00e902f12842d3da8824dfc416c0`）和无收益预登记 [`a_share_tushare_intraday_return_skewness_no_return_preregistration.json`](a_share_tushare_intraday_return_skewness_no_return_preregistration.json)（SHA‑256 `b7d20fade0436e706cbefc9abdf909f8b9ec7e2e565516af722ebda9864a3936`）冻结。`intraday_return_skewness_238m` 固定为高值更好：排除 09:30 和午休边界，上午、下午各取 119 个相邻对数收益，在 238 个收益上计算总体二、三阶中心矩及标准化偏度 `m3 / m2^(3/2)`；二阶中心矩为零时保持缺失，不做 Fisher 修正、裁剪、缩尾、符号拆分、成交额加权或秩变换。构建器 [`a_share_tushare_intraday_return_skewness.py`](../scripts/a_share_tushare_intraday_return_skewness.py) 只读取 `datetime,symbol,provider,close`。

外置不可变快照含 33,015 个股票年度分区、7,724,498 行和 7,695,088 个有效值；29,410 行因二阶中心矩为零而缺失，必需收盘、必需值、非有限收益、二阶/三阶矩和标准化偏度异常均为 0。清单 SHA‑256 为 `f4ff8ec91db7e86a56113ca3dab507f19537392c26de4912095aeed9b4f8c392`，数据集内容 SHA‑256 为 `f9bcf84e41e7607a4a7891ef3de822ff8fa602e952b0a22d73ed51fedfacd13a`。有序无收益审计 `20260723T035200Z_intraday_return_skewness_no_return_audit.json`（SHA‑256 `812f3c95d953218ad0e93c8eca6847127b53ca9b041e06b083f02418443dc59b`）先通过覆盖/容量：1,331,759 个质量/上市资格行、1,328,065 个候选行，中位/P05 覆盖 **99.8318%/99.3371%**，P05 有效名称 138，540 个潜在不重叠三日 cohort，覆盖七年。

覆盖通过后才加载十八项比较。十七项通过，但对既有较高 `intraday_upside_semivariance_share_239m` 的中位日秩相关为 **+0.862555**，高于冻结的绝对上限 0.8；对最近的收益方差熵则为 −0.293871。因而偏度在本股票横截面上与上涨半方差占比构成近同义重叠，审计状态为 `terminal_rejected_at_no_return_uniqueness_gate`。终止记录是 [`a_share_tushare_intraday_return_skewness_research_record.json`](a_share_tushare_intraday_return_skewness_research_record.json)（SHA‑256 `2a58052992102b08e9310e9521b946ddc0382c3d07b2fa06f9a21eef546b879b`）。全程未读取日线价格或未来收益，未创建收益诊断、消费标记、模型、评分或选股。不得在 2019–2025 上反向、改为峰度/尾部/分位数、改窗口、符号拆分、裁剪、筛选或组合后重测，也不采购 Level‑2 挽救。

### 同分钟 VWAP 收盘压力（稳定性与可执行 Top‑3 双门终止）

第 44 个候选在读取候选值、十九项比较值或未来收益前，先用机制核重记录 [`a_share_tushare_intraday_bar_vwap_close_pressure_mechanism_overlap_reaudit_20260723.json`](a_share_tushare_intraday_bar_vwap_close_pressure_mechanism_overlap_reaudit_20260723.json)（SHA‑256 `eee5229ecc19748e16e911810f8a60e5eb0a96939718f449d67c3f3bf7164079`）排除已被旧协议禁止的分钟收益自相关、成交额—波动耦合与全日方向效率变体，再以无收益协议 [`a_share_tushare_intraday_bar_vwap_close_pressure_no_return_preregistration.json`](a_share_tushare_intraday_bar_vwap_close_pressure_no_return_preregistration.json)（SHA‑256 `e27ac45b7193bacfcab3941f84fbeabd789e3d853640a599e9245f8a853d4554`）冻结 `intraday_bar_vwap_close_pressure_240m` 的高值方向。公式是在 09:31–11:30 与 13:01–15:00 的活动分钟上，按 CNY 成交额加权 `log(close / (amount / volume))`；09:30 排除，成交量/额同为零的分钟权重为零，只有一侧为零则整日缺失，不设最少活动分钟数。构建器 [`a_share_tushare_intraday_bar_vwap_close_pressure.py`](../scripts/a_share_tushare_intraday_bar_vwap_close_pressure.py) 只读取 `datetime,symbol,provider,close,volume,amount`，不读取分钟开高低、日线价格或未来收益。

不可变外置快照清单 SHA‑256 为 `dd5d541fb0ab99a5663ba00431eb0bac45f2975480bd681719fbb0d3eb799259`，数据集内容 SHA‑256 为 `6d153b1e1b1951afa196ae8ff1983d6166fcf61b8dbfa5d843f643ca9095c5dc`；33,015 个股票年度分区共 7,724,498 行，其中 7,724,451 行有效。77,334,747 个零成交量/零成交额分钟按预登记保留为非活动权重，47 个单边为零股票日保持缺失；必需值、同分钟 VWAP、对数差、加权分子和最终压力的非有限计数均为 0。

有序无收益审计 `20260723T045637Z_intraday_bar_vwap_close_pressure_no_return_audit.json`（SHA‑256 `f8bc19d70dca1753b764b70230bf63a3e0a7d5be0fa48c6aa3b2ec5e623b2a76`）先通过覆盖与容量：1,331,759 个质量/上市资格行、1,330,171 个候选行，中位/P05 覆盖 **99.9452%/99.5689%**，P05 有效名称 138，可形成 540 个三日非重叠 cohort，覆盖 2019–2025。随后十九项比较全部通过；最大绝对中位日秩相关为 0.488407，对应 `intraday_up_move_amount_share_238m`，低于冻结的 0.8 上限。此时日线字段仍为空且 `forward_return_fields_read=false`。

收益读取前另行冻结唯一诊断协议 [`a_share_tushare_intraday_bar_vwap_close_pressure_diagnostic_preregistration.json`](a_share_tushare_intraday_bar_vwap_close_pressure_diagnostic_preregistration.json)（SHA‑256 `b6522a451c7a2307d93f41620c31cde34300fec12f578b79001d7e5308de16c5`）。唯一诊断 `20260723T050530Z`（SHA‑256 `67e22e44ed761b0f1256f97f8d70e7288407d0e250c34fd6138f432db5b02bbe`）含 539 个 cohort：平均/中位 Rank IC 为 **−0.002436/+0.000014**，正 IC 比例 50.09%，Top‑3 减 Bottom‑3 平均毛收益差 +0.0272%；2019、2022、2024、2025 年平均 IC 非正。执行感知 Top‑3 完整信号 533 个，累计 **−81.37%**、最大回撤 **−91.88%**，2021、2022、2024 年为负。

20 万元、100 股整手、单槽 5%、总入场仓位 15%、买卖各 10bp 不利滑点与 1% 日成交额参与约束下，填充 1,486 个席位，整手机会可负担率 94.59%，累计 **−26.16%**、最大回撤 **−31.98%**；即使零滑点也为 −15.11%，最大成交额参与率 0.8746%，终局未解决持仓为 0。稳定性审计 `20260723T050602Z`（SHA‑256 `d774ec2e80dd331c4d81db606c7a80afa10c5000cda882aa43a58a6f437ff52e`）和 Top‑3 可行性审计同运行号（SHA‑256 `adf7162777f5af55246f5d880e6e1cec984d35f6cd21f18461b1f1636e81ee7c`）均为 0/1。

终止记录为 [`a_share_tushare_intraday_bar_vwap_close_pressure_research_record.json`](a_share_tushare_intraday_bar_vwap_close_pressure_research_record.json)（SHA‑256 `135e56d0b2389f17f262bdbe39ef125de98eb3feffba69ea1e7aadc9bc8bbe26`）。该精确高值方向不得在 2019–2025 上反向、改成绝对差/简单平均、改变成交额权重、窗口、09:30 或零活动处理、加阈值/过滤、挑子集/年份、重权或组合重测；不得用于聚合、当前评分、选股、仓位、订单或 Level‑2 采购理由。

### 午别相邻分钟价格更新占比（稳定性与可执行 Top‑3 双门终止）

第 45 个候选在读取候选值、二十项比较值或未来收益前，以机制核重记录 [`a_share_tushare_intraday_price_update_share_mechanism_overlap_reaudit_20260723.json`](a_share_tushare_intraday_price_update_share_mechanism_overlap_reaudit_20260723.json)（SHA‑256 `1977bf2c182d4f7568dc5ecb7ae2340fe5651984d39112fc8465dded989e8ff6`）和无收益协议 [`a_share_tushare_intraday_price_update_share_no_return_preregistration.json`](a_share_tushare_intraday_price_update_share_no_return_preregistration.json)（SHA‑256 `9a84bb0d0d86d61ba64b8dffbf6854cea708936c43aa9ae6f494e73b56db13fc`）冻结。`intraday_price_update_share_238m` 固定为高值更好：只使用 09:31–11:30 与 13:01–15:00 的 240 个收盘价，在上午、下午内部各比较 119 对相邻分钟，统计精确不相等的对数并除以固定 238。09:30 与跨午休对排除，不做舍入、epsilon 或容差；全天价格不变是有效零值。构建器 [`a_share_tushare_intraday_price_update_share.py`](../scripts/a_share_tushare_intraday_price_update_share.py) 只读取 `datetime,symbol,provider,close`，不读取开高低、成交量、成交额、日线价格或未来收益。

不可变外置快照清单 SHA‑256 为 `3081777797bae9983da3c7d943eb4bb886dbf3ff383c7da06e859d57fb7cf7b3`，数据集内容 SHA‑256 为 `7b3b471caf30e7162074f7882e8ae1b2b9e56ab87748dfcfb49b5e66b986d10b`；33,015 个股票年度分区共 7,724,498 行且全部有效。238 对中累计 1,177,277,526 对价格更新、661,152,998 对价格不变；必需收盘异常、非有限结果和范围越界均为 0。

有序无收益审计 `20260723T061227Z_intraday_price_update_share_no_return_audit.json`（SHA‑256 `fd07ea6c811c0158f90f4c8e258146242e2f9c1efff99b1977a8e30cad356969`）先通过覆盖与容量：1,331,759 个质量/上市资格行、1,330,171 个候选行，中位/P05 覆盖 **99.9452%/99.5689%**，P05 有效名称 138，可形成 540 个三日非重叠 cohort，覆盖 2019–2025。随后二十项唯一性比较全部通过；最大绝对中位日秩相关为 **0.562439**，对应 `intraday_diffusive_variation_ratio_238m`，低于冻结的 0.8 上限。此阶段没有加载日线字段或未来收益。

收益读取前另行冻结唯一诊断协议 [`a_share_tushare_intraday_price_update_share_diagnostic_preregistration.json`](a_share_tushare_intraday_price_update_share_diagnostic_preregistration.json)（SHA‑256 `7f32f0ebbd027a86de5f94aceced9ab94a39dd775073c437181a090940bb2177`）。唯一诊断 `20260723T062019Z`（SHA‑256 `d47068033c17c575a841ae3de7e4a6cd274d163460cb7b7e8f46ffdb8c338a8d`）含 539 个 cohort：平均/中位 Rank IC 为 **−0.027741/−0.037697**，正 IC 比例 **44.34%**，Top‑3 减 Bottom‑3 平均毛收益差 **+0.5016%**；2021–2025 年平均 IC 均非正，关联稳定性门失败。标准化执行感知 Top‑3 的 533 个完整信号累计 **+415.13%**，但最大回撤 **−48.24%** 且 2022 年为负，不能只凭累计收益通过门禁。

20 万元、100 股整手、单槽 5%、总入场仓位 15%、买卖各 10bp 不利滑点与 1% 日成交额参与约束下，只填充 315/1,599 个登记席位，整手机会可负担率仅 **19.70%**，累计 **−1.38%**、最大回撤 **−5.00%**；0/5/10/20bp 描述性累计分别为 **+1.16%/−0.18%/−1.38%/−2.85%**，最大成交额参与率仅 0.007895%，终局未解决持仓为 0。稳定性审计 `20260723T062100Z`（SHA‑256 `d6631f223370258edc83f0eebca4d846ddcd45a9bd34ca3059647c5c7b9b4755`）和 Top‑3 可行性审计 `20260723T062101Z`（SHA‑256 `601f18ed56d5d0959eb95a80115b497cbaf1b7fff248d15b576fedd4a1c658d1`）均为 0/1。

单次消费标记 SHA‑256 为 `a2a6838314fd1543dfa4e0fc7fc704a808bf7ba7e79e839d64efa4c20387dab3`；终止记录为 [`a_share_tushare_intraday_price_update_share_research_record.json`](a_share_tushare_intraday_price_update_share_research_record.json)（SHA‑256 `ae24ac70ae3365776b68414f5fc615786bee67e4329d28c04ad621be894447f0`）。该精确高值价格更新占比永久退出 2019–2025：不得因平均 IC 为负而反向、改成价格不变占比、加入 09:30 或午休对、加 epsilon/舍入/阈值、改窗口/子集/年份/权重或与旧因子组合重测；不加入聚合池，不训练模型，不生成当前评分、选股、仓位或订单，也不采购 Level‑2 挽救。

### 分钟收益留一法市场特异份额（稳定性与可执行 Top‑3 双门终止）

第 46 个候选在读取候选值、二十一项比较值或未来收益前，以机制核重记录 [`a_share_tushare_intraday_market_idiosyncratic_share_mechanism_overlap_reaudit_20260723.json`](a_share_tushare_intraday_market_idiosyncratic_share_mechanism_overlap_reaudit_20260723.json)（SHA‑256 `ae446992ad28bc867e33e8210bf5129fae9ba5a0d55de184ae68b72aa5fbd10b`）和无收益协议 [`a_share_tushare_intraday_market_idiosyncratic_share_no_return_preregistration.json`](a_share_tushare_intraday_market_idiosyncratic_share_no_return_preregistration.json)（SHA‑256 `6f1f4108cd54357e94e44cee8793e917a2bc627af9da885af6d2b50b76c4078a`）冻结。`intraday_market_idiosyncratic_share_238m` 固定为高值更好：从 09:31–11:30 与 13:01–15:00 的 240 个收盘价形成午别内部 238 个一分钟对数收益；对每个股票—日期—分钟位置，以同日所有有效股票的收益和、数量减去该股票，构造至少 50 个同业样本的等权留一法市场收益，再计算 `1 - Corr(stock, market_without_stock)^2`。09:30 和午休边界排除；股票或市场向量为常数时缺失。构建器 [`a_share_tushare_intraday_market_idiosyncratic_share.py`](../scripts/a_share_tushare_intraday_market_idiosyncratic_share.py) 只读取 `datetime,symbol,provider,close`，不读取开高低、成交量、成交额、指数、行业、市值、日线价格或未来收益。

不可变外置快照清单 SHA‑256 为 `954b71d571bcd89cbf4eae4eedad014091a9b40e6b2b083e0071cbf870634ef0`，数据集内容 SHA‑256 为 `e30578d063c16bafc77873e8d061d8b3985c4d3b9beb8a5994514db292f8c430`；33,015 个股票年度分区共 7,724,498 行，其中 7,695,088 行有效。29,410 行因股票收益向量为常数而缺失；必需收盘异常、同行不足、市场向量常数、非有限相关、端点规范化和范围越界均为 0。独立市场基准含 404,362 行（1,699 日 × 238 位置），每个位置最少 3,549 只有效股票，字节/帧 SHA‑256 分别为 `5437805f84c5c637904a62664cc3ec677e0155f5a215b0df7c38ed0cc35b88bf` / `5412520f379a3d7584f18a0fd5a0b55fd8b68ed3a49d76ff6430a330eee9d4a1`。

有序无收益审计 `20260723T081939Z_intraday_market_idiosyncratic_share_no_return_audit.json`（SHA‑256 `44e9a2279aebc55d265378aa8bf4dad4a562cc4c2438973925c638b89ec0b34b`）先通过覆盖与容量：1,331,759 个质量/上市资格行、1,328,065 个候选行，中位/P05 覆盖 **99.8318%/99.3371%**，P05 有效名称 138，可形成 540 个三日非重叠 cohort，覆盖 2019–2025。随后二十一项唯一性比较全部通过；最大绝对中位日秩相关为 **0.265628**，对应 `intraday_amount_participation_entropy_240m`，低于冻结的 0.8 上限。前两次执行分别因递归比较链内存退出和重复 `np.isin` 过慢而未写出审计，且均未读取收益；唯一允许的修复只是串行加载单个比较、紧凑排序键和 `searchsorted`，详见 [`a_share_tushare_intraday_market_idiosyncratic_share_no_return_audit_infrastructure_repair.json`](a_share_tushare_intraday_market_idiosyncratic_share_no_return_audit_infrastructure_repair.json)（SHA‑256 `d4c31cff26b1fc44eabac83480101388d2414a4c8022343e4578e949239a2c93`），未改变公式、方向、比较顺序或门禁。

收益读取前另行冻结唯一诊断协议 [`a_share_tushare_intraday_market_idiosyncratic_share_diagnostic_preregistration.json`](a_share_tushare_intraday_market_idiosyncratic_share_diagnostic_preregistration.json)（SHA‑256 `06101c155c81b9fb6128327db25da9b078bfcd045f160fce2e56f2ece0020b75`）。唯一诊断 `20260723T090824Z`（SHA‑256 `78659065220f61db5119c0091383be0f4ff984f8ece2c6f7687f3e1e2b228a5b`）含 539 个 cohort：平均/中位 Rank IC 为 **−0.011523/−0.006791**，正 IC 比例 **47.50%**，Top‑3 减 Bottom‑3 平均毛收益差 **−0.2648%**；只有 2021 年平均 IC 为正。五分位收益从第 1 组约 +0.2683% 下降到第 5 组约 +0.1751%，与冻结的高值方向相反。标准化执行感知 Top‑3 的 533 个完整信号累计 **−58.55%**，最大回撤 **−78.94%**，2019、2021、2023、2024 和 2025 年为负。

20 万元、每槽 5%、总入场 15%、100 股整手、用户 0.01% 佣金、双边 0.002% 过户费、卖出 0.05% 印花税和双边 10bp 不利滑点下，累计收益 **−18.38%**、最大回撤 **−22.39%**、整手机会可负担率 **93.11%**，最大成交额参与率 **1.0161%**，超过冻结的 1% 上限；即使零滑点仍累计 **−6.20%**。稳定性审计 SHA‑256 `748f5f14e5b4f0c4ca8c1b5d0de263c6bbc0c7ce043106ad8f52d5cc1adcecff` 与 TopK 审计 SHA‑256 `7e3726a2a6890327dca3fc1bab68f6f2c4552492d266c2a81ed4ce3fc6cdc701` 均通过 0/1，双门禁仍为空。

单次消费标记 SHA‑256 为 `5ea43c65a6200608413a33792d7a54fd1f20d9b61018ba73225d8d3fa285bafd`；终止记录为 [`a_share_tushare_intraday_market_idiosyncratic_share_research_record.json`](a_share_tushare_intraday_market_idiosyncratic_share_research_record.json)（SHA‑256 `cb6829903b5cc4254bb1965e9308fdff5902ce420467a3a552a5484091a22b61`）。该精确高值市场特异份额永久退出 2019–2025：不得因为方向相反而反向成市场同步度或 R²，替换为指数/行业/板块/市值加权基准，改 beta/有符号相关、窗口、阈值、子集、年份或权重，或与旧因子组合重测；不加入聚合池，不训练模型，不生成当前评分、选股、仓位或订单，也不采购 Level‑2 挽救。

### 09:30 集合竞价成交额占比（稳定性与可执行 Top‑3 双门终止）

第 47 个候选在读取候选值、二十二项比较值或未来收益前，以机制核重记录 [`a_share_tushare_intraday_opening_auction_amount_share_mechanism_overlap_reaudit_20260723.json`](a_share_tushare_intraday_opening_auction_amount_share_mechanism_overlap_reaudit_20260723.json)（SHA‑256 `f3ada152a88df413e45826ea4a72ced7cd63f043f45fbcd90c0e431b8aa636a7`）和无收益协议 [`a_share_tushare_intraday_opening_auction_amount_share_no_return_preregistration.json`](a_share_tushare_intraday_opening_auction_amount_share_no_return_preregistration.json)（SHA‑256 `3aca85681061bedf7dc049f21e6bfcfaa520f9478938bd007b3d6666814db84b`）冻结。`intraday_opening_auction_amount_share_241m` 固定为高值更好，公式为 `09:30 成交额 / 241 根完整来源分钟的成交额总和`。构建器 [`a_share_tushare_intraday_opening_auction_amount_share.py`](../scripts/a_share_tushare_intraday_opening_auction_amount_share.py) 只读取 `datetime,symbol,provider,amount`；09:30 成交额为零是有效零，不读取存在口径争议的 09:30 价格，也不读取开高低收、成交量、日线价格或未来收益。

外置不可变快照清单 SHA‑256 为 `cb6acb3dcbad2ca459ac2f11ea80364593543adc852bf82ea3f177ae58154580`，数据集内容 SHA‑256 为 `9e7cd5b724347bc5193970ed2f23fa8ff1ce1e58f0c460ba46891a86538f8e65`；33,015 个股票年度分区共 7,724,498 行，全部有效，必需成交额异常、全天总额非正、端点规范化和范围越界均为 0。有序无收益审计 `20260723T115821Z_intraday_opening_auction_amount_share_no_return_audit.json`（SHA‑256 `fb904d0cac194491eff119ad409a63b30603bd8225206284dad391136e34c979`）先通过覆盖：1,331,759 个质量/上市资格行中有 1,330,171 个候选值，中位/P05 覆盖 **99.9452%/99.5689%**，P05 有效名称 138，可形成 540 个三日非重叠 cohort。随后二十二项唯一性比较全部通过；最大绝对中位日秩相关为 **0.303467**，对应成交额重心，低于 0.8 上限。高覆盖和独立性只允许进入一次收益诊断，不代表因子有效。

收益读取前另行冻结唯一诊断协议 [`a_share_tushare_intraday_opening_auction_amount_share_diagnostic_preregistration.json`](a_share_tushare_intraday_opening_auction_amount_share_diagnostic_preregistration.json)（SHA‑256 `69c18050be829c73c09c988a5d4f37795a310b678b691113a989a94b78b2c1c9`）。唯一诊断 `20260723T120824Z`（SHA‑256 `3c801cf4e67d4e6c523d3ea63cc19852243a6183e4a4cc733a2b2584b20a559e`）含 539 个 cohort：平均/中位 Rank IC 为 **−0.003394/−0.003633**，正 IC 比例 **48.98%**，Top‑3 减 Bottom‑3 平均毛收益差 **−0.1337%**；除 2020 外六个年份的平均 IC 均不为正。标准化执行感知 Top‑3 的 533 个完整信号累计 **−95.38%**，最大回撤 **−98.06%**。

20 万元、每槽 5%、总入场 15%、100 股整手、既定 A 股费用和双边 10bp 不利滑点下，累计 **−35.45%**、最大回撤 **−39.32%**、整手机会可负担率 **94.07%**，最大成交额参与率 **0.3587%**，容量本身没有触发 1% 上限；即使零滑点仍累计 **−28.63%**。稳定性审计 `20260723T120854Z`（SHA‑256 `cebcc7bb447c14690d951e659fb0a2857b5c2d263a95fe13eee3613e4a9bf855`）和 Top‑3 可行性审计 `20260723T120855Z`（SHA‑256 `4c64faab230221687e8a93a31c5559f8fa4df432b63275d47e5b0cf274ce85f3`）均为 0/1。单次消费标记 SHA‑256 为 `c99e094132adf754c4066414ce782e2e56d52d2f4d4fb70c003fde6d5399c09e`；终止记录为 [`a_share_tushare_intraday_opening_auction_amount_share_research_record.json`](a_share_tushare_intraday_opening_auction_amount_share_research_record.json)（SHA‑256 `b70a8ec547bdc36db408adc86b809456caac9a774d074de913369b3349899abd`）。

该精确高值集合竞价成交额占比永久退出 2019–2025：不得反向为低集合竞价占比、排除 09:30 零成交记录、改全天分母、改窗、阈值、子集、年份或权重，或与旧因子组合重测；不加入聚合池，不训练模型，不生成当前评分、选股、仓位或订单，也不采购 Level‑2 挽救。

### 全市场成交额轮廓同步性（稳定性与可执行 Top‑3 双门终止）

第 48 个候选在读取候选值、二十三项比较值或未来收益前，以机制核重记录 [`a_share_tushare_intraday_market_amount_profile_synchronization_mechanism_overlap_reaudit_20260725.json`](a_share_tushare_intraday_market_amount_profile_synchronization_mechanism_overlap_reaudit_20260725.json)（SHA‑256 `24127b8326f29175a88a74ecb5c21cb508b3fc9bb5a68ee5f7e003f29b84d17f`）和无收益协议 [`a_share_tushare_intraday_market_amount_profile_synchronization_no_return_preregistration.json`](a_share_tushare_intraday_market_amount_profile_synchronization_no_return_preregistration.json)（SHA‑256 `f560442de1a344ddcfee4ec42e14bfaa8e1abf9f1015506f011fee27121e6845`）冻结。`intraday_market_amount_profile_synchronization_240m` 固定为高值更好：先把每只股票 09:31–11:30、13:01–15:00 的 240 根成交额除以当日连续交易总额，再与同日全部其他有效股票的等权留一平均轮廓计算普通 Pearson 相关。每个位置至少需要 50 个留一同业；09:30 明确排除。构建器 [`a_share_tushare_intraday_market_amount_profile_synchronization.py`](../scripts/a_share_tushare_intraday_market_amount_profile_synchronization.py) 只读取 `datetime,symbol,provider,amount`，不读取价格、收益、成交量、日线、行业或市值。

外置不可变快照清单 SHA‑256 为 `40f9700a919cc22f30bd928133fb20bc6af3476a7952020d180f712d97f063f5`，数据集内容 SHA‑256 为 `26d82a495393cee45293d0ca00c444f88b2e25900d2ccc92fc0be5329fdf63a8`；33,015 个股票年度分区共 7,724,498 行，全部有效。必需成交额异常、连续交易总额非正、同业不足、个股/市场常量轮廓、非有限相关和范围越界均为 0。两遍流式构建没有保存约 18 亿个展开轮廓中间值；最终市场基准只有 1,699 日 × 240 位置。每日有效股票数最少 3,549、中位数 4,713、最大 5,170，远高于最低同业要求。

有序无收益审计 `20260725T010933Z_intraday_market_amount_profile_synchronization_no_return_audit.json`（SHA‑256 `516dd4e88b31790a30c5477a7a6a4a05591a2fdb48f4a43fa4f31044245c3ca3`）先通过覆盖：1,331,759 个质量/上市资格行中有 1,330,171 个候选值，中位/P05 覆盖 **99.9452%/99.5689%**，P05 有效名称 138，可形成 540 个三日非重叠 cohort。随后二十三项唯一性比较全部通过；最大绝对中位日秩相关为 **0.566705**，对应成交额重心；与集合竞价成交额占比为 **0.482061**，均低于 0.8 上限。高覆盖和独立性只允许进入一次收益诊断，不代表因子有效。

收益读取前另行冻结唯一诊断协议 [`a_share_tushare_intraday_market_amount_profile_synchronization_diagnostic_preregistration.json`](a_share_tushare_intraday_market_amount_profile_synchronization_diagnostic_preregistration.json)（SHA‑256 `279c6c248aaa517d36db00ac39a5336742bf2404b99888c311f398bca8ebefb5`）。唯一诊断 `20260725T051451Z`（SHA‑256 `154fae15db6775fc1f9ae6cc853eee11fb54559e032f4c29a5e89f7057d439a1`）含 539 个 cohort：平均/中位 Rank IC 为 **−0.011745/−0.015435**，正 IC 比例 **45.08%**，Top‑3 减 Bottom‑3 平均毛收益差 **−0.2946%**；2019–2023 年平均 IC 均非正。标准化执行感知 Top‑3 的 533 个完整信号累计 **−53.64%**，最大回撤 **−80.01%**；只有 2024 年年度执行收益为正。

20 万元、每槽 5%、总入场 15%、100 股整手、既定 A 股费用和双边 10bp 不利滑点下，累计 **−13.18%**、最大回撤 **−18.85%**、整手机会可负担率 **87.99%**，最大成交额参与率仅 **0.0407%**，容量不是失败原因；即使零滑点仍累计 **−2.90%**。稳定性审计 `20260725T051520Z`（SHA‑256 `a58ac6bcd186d65dbb810ad892bf4ce0048dda719356834e2fe8f25725f8abfe`）和 Top‑3 可行性审计 `20260725T051521Z`（SHA‑256 `f3a46baf5302fb6cb4c1d03e45f3a609f5a6e8290893779e26941f376e4a5d71`）均为 0/1。单次消费标记 SHA‑256 为 `a67862b618171518c5d835e6e9fde38af3a3393becc094c32cd094d0cf3adfad`；终止记录为 [`a_share_tushare_intraday_market_amount_profile_synchronization_research_record.json`](a_share_tushare_intraday_market_amount_profile_synchronization_research_record.json)（SHA‑256 `75a41875b5133258d483c470d44f1fdd1cdd030573e03ce66c33c22d926874ed`）。

该精确高值市场成交额轮廓同步性永久退出 2019–2025：不得因为总体结果为负而反向为特异轮廓、改成平方/绝对值/余弦/秩相关/回归残差，替换指数、行业、板块、加权或非留一基准，加入 09:30，改窗口、阈值、子集、年份或权重，或与旧因子组合重测；不加入聚合池，不训练模型，不生成当前评分、选股、仓位或订单，也不采购 Level‑2 挽救。

### 累计 VWAP 穿越率（候选 49，纯前瞻观察已登记）

在 2026‑07‑25 候选 49 登记时，48 条历史机制全部终止且双门禁交集仍为空，因此当时的未来专用政策不再允许从 2019–2025 三日收益中为候选 49 挑选公式。候选 49 先由机制核重记录 [`a_share_tushare_intraday_cumulative_vwap_crossing_rate_mechanism_overlap_reaudit_20260725.json`](a_share_tushare_intraday_cumulative_vwap_crossing_rate_mechanism_overlap_reaudit_20260725.json)（SHA‑256 `f86ba3cdfd7ead04963519e1c86e0d022467896a68ac3422fb5d742f716dcdcd`）和无收益协议 [`a_share_tushare_intraday_cumulative_vwap_crossing_rate_no_return_preregistration.json`](a_share_tushare_intraday_cumulative_vwap_crossing_rate_no_return_preregistration.json)（SHA‑256 `cefa5f23b5214e123d0bdea1511a398cb4a70c0ee4cc8da7d1f69f52bdbe4aeb`）冻结为高值更好 `intraday_cumulative_vwap_crossing_rate_240m`。2026‑07‑27 新增的历史滚动研究政策不回溯改变这一候选的身份：Candidate49 仍不得历史收益回填，但它不再阻塞单独的历史训练/验证/回测主线。

公式只使用 09:31–11:30、13:01–15:00 的 240 个连续交易位置。每个位置按截至当时的累计成交额除以累计成交量得到因果累计 VWAP，再取 `log(close / cumulative_vwap)` 的符号；删除精确为零的符号后，以相邻非零符号发生改变的次数除以相邻非零符号对数。至少需要两个非零符号；共同为零的成交量/成交额作为无活动位置保留，单边为零使整个股票日缺失，只有 `1e-12` 的端点归一化。构建器 [`a_share_tushare_intraday_cumulative_vwap_crossing_rate.py`](../scripts/a_share_tushare_intraday_cumulative_vwap_crossing_rate.py) 只读取 `datetime,symbol,provider,close,volume,amount`，明确禁止 09:30、原始开高低、日线价格和未来收益。

外置不可变快照清单 SHA‑256 为 `f3dd3417bd6adcaa06d8927865ea3f464ebc02df302b8f488e43450f7c620196`，数据集内容 SHA‑256 为 `67bda6df74747a0f39fe6eb252aada84ea7850fff2c05bdae4951aa41fcc7037`。33,015 个股票年度分区共有 7,724,498 行，其中 7,714,026 行可计算；单边零成交量/额 47 行，非零偏离符号不足两项 10,425 行，范围越界和端点修正均为 0。中断后的构建从 2,025 个指纹绑定检查点安全恢复，完整重跑保持字节级幂等。

有序无收益审计 `20260725T062547Z_intraday_cumulative_vwap_crossing_rate_no_return_audit.json`（SHA‑256 `51bb248b1071983cf9a05fca94c6cc08770a2d10fbef1d6d087f2d5a875fdf7d`）在 1,331,759 个质量/上市资格行中保留 1,329,458 个候选值，中位/P05 覆盖率为 **99.9161%/99.4461%**，P05 有效名称 138，历史区间可形成 540 个三日非重叠 cohort。二十四项唯一性比较全部低于 0.8；最大绝对中位日秩相关为 **0.197644**，对应成交额轮廓序列持续性。审计的 `historical_daily_price_fields_loaded=[]` 且 `forward_return_fields_read=false`；这些结果只证明可构建、覆盖充分且不是已登记近重复，完全不证明预测收益。

未来观察登记 [`a_share_tushare_intraday_cumulative_vwap_crossing_rate_future_observation_registration.json`](a_share_tushare_intraday_cumulative_vwap_crossing_rate_future_observation_registration.json)（SHA‑256 `431cb0b3b078823f08b888bf4c499bcc5088309a2e58e9de5cb9a9aaa849ffa9`）已在 2026‑07‑25 完成，登记 ID 为 `candidate49_intraday_cumulative_vwap_crossing_rate_240m_v1`。首个信号只能来自 **2026‑07‑27 或之后**首个完成并验收的本地交易日。当前没有信号、评分、选股、仓位或订单。

构建器还提供两个只读/本地准备命令。第一条幂等创建两个空的哈希链账本；已有任一账本缺失、表头改变、旧条目改变、链断裂、重复 ID 或早于 2026‑07‑27 的条目都会硬停止，绝不重置。第二条只做本地预检，不访问 Tushare、不读取分钟行、不写信号或执行条目：

```bash
python scripts/a_share_tushare_intraday_cumulative_vwap_crossing_rate.py \
  initialize-future-ledgers

python scripts/a_share_tushare_intraday_cumulative_vwap_crossing_rate.py \
  future-preflight \
  --data-root /Volumes/DIsk/qlib-a-share-tushare-1m \
  --session 2026-07-27
```

2026‑07‑25 的真实预检按预期返回 `not_ready_no_provider_request`：目标会话尚未收盘，本地已验收日线日历仍止于 2026‑07‑13，当前 Codex 进程也没有继承 `TUSHARE_TOKEN`；两个空账本已初始化且条目数都是 0。低层 `future-preflight` 和最终 `--preflight-only` 在未就绪时都会先打印完整 JSON，再以退出码 `2` 结束；就绪时退出码为 `0`，JSON 同时给出 `recommended_cli_exit_code`。因此 shell 串联必须使用成功退出码和 `ready=true` 双重确认，不能用 `;`、`|| true` 或忽略退出码继续 `--allow-large`。不得因为预检尚未就绪而提前请求、回填或使用历史收益。新原始会话只能在目标交易日的**同一当地日期**、收盘缓冲结束后开始；到了下一日期再请求旧会话会以 `past_session_delayed_source_to_signal_backfill_forbidden` 在任何供应商检查、分钟请求或新文件写入前停止。

2026‑07‑26 的最后一次周末只读复核绑定在 [`a_share_candidate49_first_future_session_operational_readiness_20260726.json`](a_share_candidate49_first_future_session_operational_readiness_20260726.json)（SHA‑256 `4287168ef3b9f60d1fa6487ca2be05ae3dbef643c39cde0a20fde73fdb70ffa6`）。它再次确认两个账本为 0、外置历史分钟根完整且未持锁、预检零网络零写入，并记录了迁移后未来质量文件必须跟随活动数据根的修正；它不授权提前请求、历史回填、选股或订单。

随后对 2026‑07‑27 统一工作流执行的真实 `plan` 记录在 [`a_share_candidate49_20260727_readonly_plan_20260726.json`](a_share_candidate49_20260727_readonly_plan_20260726.json)（SHA‑256 `cef6c64e1182ed27084fab6fcf49cacd49bcc1f62d6b5976c9596be931478d6f`）。它以退出码 2 和 `not_ready_no_write` 正常结束，失败项只有 `signal_session_has_not_arrived` 与 `TUSHARE_TOKEN_not_available_to_workflow`；历史 Tushare 日线参考仍为 7 个分区、1,699 个会话、7,989,350 行且不会重下，目标 staging、两把锁和 2026‑07‑27 完整/partial 分钟目录都不存在，外置盘空闲约 1,656.9 GiB。当前进程与 `launchctl` 都看不到 Token；这不会由仓库自动修复，也不能把凭据发到聊天。请重新执行凭据指南中的 `read -s "token?…"` 三行，并只检查“已配置/未配置”。`launchctl` 值可能在注销或重启后消失；若曾把 `read -s "xxxxxx"` 当提示使用，后续 `$token` 实际可能为空。

未来单会话采集器 [`a_share_tushare_candidate49_future_observation.py`](../scripts/a_share_tushare_candidate49_future_observation.py) 已实现并完成离线全链路演练。它只在本地预检全部通过且显式给出 `--allow-large` 后，按 400 次/分钟、4 个 worker、最多 3 次瞬时错误尝试请求当日完整可买股票池。每只股票的供应商响应单独原子落盘并附带帧/文件双指纹；隐藏的 `.YYYY-MM-DD.partial` 目录只允许在目标信号日当天中断续传，并只跳过指纹仍一致的已完成股票。若运行跨过当地午夜仍未完成，partial 必须原样保留为中断证据，下一日期不得继续请求或发布为信号；若只完成 raw 而尚未发布 factor，跨日也不得补完。交易日历、可买区间、价格基准和当日季度质量文件及清单必须在第一个分钟请求前一起冻结；上下文、全部股票分区和清单完成后才把目录原子改名为公开日期目录。只有 raw 和 factor 都已经在信号日完整原子发布的会话，才允许以后跨日零请求幂等复核及确定性账本核对。

未来数据不复用历史 OHLC 严格对账的错误口径。每个供应商返回行都原样保留为规范列；只有精确的 241 时间戳网格以及 `close`、以股计的 `volume`、`amount` 与同日未复权日线对账通过，才允许进入 candidate49 公式。`open/high/low` 只保留取证，既不参与这个因子的对账，也不影响可用性。缺行、停牌、重复时间戳、网格外行或对账失败都保持缺失，绝不补行、前向填充或用日线替换分钟值。价格基准清单还必须声明且仅声明一个受支持的 `daily_source`，并随交易日历、可买区间和质量文件一起冻结、按哈希复核。日线同步阶段负责扫描完整原始日线根并拒绝混源；candidate49 的 Parquet 读取直接投影 `date,raw_close,raw_volume,amount,price_basis` 并下推 `date == 信号日`，不把未注册的 `daily_source` 或其他日期行载入内存。

未来观察的季度质量必须单独写入 `data/raw/a_share/fundamentals/quarterly_quality_future.parquet` 和 `data/metadata/quarterly_quality_future_manifest.json`。严禁覆盖或传入历史研究已按指纹冻结的 `quarterly_quality.parquet` 或 `quarterly_quality_manifest.json`。未来文件必须在目标信号日当地时间 16:00 后重新下载；清单状态、季度频率、数据路径、行数、逐报告期计数、最新已结束季度、时区化抓取时间和数据 SHA‑256 全部通过后才能发出任何分钟请求。校验调用本身只投影 `instrument,report_date,announcement_date,roe,net_profit,revenue_yoy,profit_yoy` 七列。原始会话上下文冻结后，因子阶段只从该上下文复制质量文件，不再读取后来变化的外部版本；因子读取仍只投影这七列，并在 Parquet 调用层下推 `announcement_date < 信号日`，因此同日公告、之后公告和其他源列都不会载入信号构建内存。

质量信息严格在公告后的下一本地交易日生效，逐字段前向填充，最长 550 日，并要求上市满 20 个会话、ROE 不低于 5%、净利润/营收同比/利润同比均为正。分钟因子阶段的 Parquet 调用只投影 `datetime,symbol,provider,close,volume,amount`，并下推 09:31—11:30 与 13:01—15:00 两段；原始 09:30 以及 `open/high/low` 仍保留在不可变取证分区，但不会载入因子构建。只有至少 50 只股票同时通过来源、公式、质量和上市门槛，才按因子降序、股票代码升序打破并列并把 Top‑3 追加到信号哈希链；因子快照不足 50 只仍永久留证，但不产生信号。该命令不读取未来收益、不结算持仓、不生成真实订单。

离线演练覆盖了 50 只 × 241 行的确定性 Top‑3、已发布会话同日及跨日重复执行均零请求且零重复条目、单只缺一根时原样保留 240 行并因 49 只有效名停止出信号、信号日内进程中断后的分区级续传、跨日新采集与跨日 partial 续传在零请求和零新写入下停止、分区字节改变后硬停止，以及历史质量路径或非信号日 16:00 后快照在任何供应商检查/请求前硬停止。这些只是实现验收，不是一个真实未来信号或收益结果。

等待 Candidate49 的 60/200 个未来样本不等于停止机制研究，但同时活动的新机制上限仍是 1。零数值侦察队列已记录在 [`a_share_three_day_inactive_mechanism_scouting_queue_20260726.json`](a_share_three_day_inactive_mechanism_scouting_queue_20260726.json)（SHA‑256 `00565a87b5eb4241de3dfdd24f96ef78756fb286655969351ec966bbe32afad3`）：优先考察市场中性尾盘残差漂移、负收益后的成交额加权吸收率和有符号路径效率。它只比较既有机制的文字定义，没有读取历史因子值、日线价格或收益，也没有分配 Candidate50 序号、冻结第二套公式、生成代码或派生快照。Candidate49 终止或完成 200 个样本前只能维护概念；满足条件后也只能从队首取一个，先做新的机制重叠审计，再在任何数值出现前单独预注册。Tushare 日线在当前阶段继续承担口径、对账、股票池和未来结算，不因此自动变成第二条日线因子赛道。

首个允许会话收盘后，必须先更新日线并让价格基准、日历和 `buyable_main_chinext` 覆盖该日，再执行只读预检。当前 BaoStock 根已经被匿名黑名单拒绝，因此 2026‑07‑27 的首次运行不能再照抄普通 `sync`：应先按前文“Tushare 日线迁移”章节，用带日期的新 staging 根完成 `preflight → sync-source → build → activation-preflight → activate`，并在新进程中确认活动日历覆盖 2026‑07‑27。源清单发布后不能把截止日从 7 月 24 日改到 7 月 27 日，所以周末不应提前完成一个较早的源快照。

推荐使用单一的失败即停入口 [`a_share_tushare_candidate49_future_session_workflow.py`](../scripts/a_share_tushare_candidate49_future_session_workflow.py)，其冻结协议是 [`a_share_tushare_candidate49_future_session_workflow_protocol.json`](a_share_tushare_candidate49_future_session_workflow_protocol.json)（SHA‑256 `6ff5636a3f7ef65e93452098186b3aecf9231d68873ab8a1070afb91d699ef7c`）。先运行只读计划：

```zsh
python scripts/a_share_tushare_candidate49_future_session_workflow.py plan \
  --session 2026-07-27 \
  --staging-root /Volumes/DIsk/qlib-a-share-tushare-daily-2026-07-27 \
  --minute-data-root /Volumes/DIsk/qlib-a-share-tushare-1m
```

`plan` 只核对冻结指纹、活动日线状态、staging 状态、目标日期、Token 是否存在，以及现有 Tushare 历史日线参考；它不创建 staging、不写锁、不请求供应商，也不读取分钟行或收益。当前参考已按哈希验证为 2019‑01‑01 至 2025‑12‑31、7 个年度分区、1,699 个交易日和 7,989,350 行。计划输出会明确标记这些覆盖日不会再次请求 `daily`；这不代表 `daily_basic` 已存在，也不免除 2015–2018 与 2026 目标日前缺失日线的补齐。目标日尚未到、16:30 收盘缓冲尚未结束或 Token 对当前进程与 `launchctl` 都不可见时，它输出诊断 JSON 并退出 2。这个退出码不能被当成成功串联到运行命令。

目标会话当地日期 16:30 以后，只有 `plan` 的阻塞项已经解决才运行：

```zsh
python scripts/a_share_tushare_candidate49_future_session_workflow.py run \
  --session 2026-07-27 \
  --staging-root /Volumes/DIsk/qlib-a-share-tushare-daily-2026-07-27 \
  --minute-data-root /Volumes/DIsk/qlib-a-share-tushare-1m \
  --confirm-run
```

该命令按“当前进程环境 → 仓库根目录 `.env` → `launchctl getenv TUSHARE_TOKEN`”读取 Token；`.env` 只解析唯一的 `TUSHARE_TOKEN=...`，不执行 shell、不展开变量，且必须被 Git 忽略。Token 从不进入参数、输出、清单或日志。它先识别活动日线来源：BaoStock 首次迁移直接复用已验收的 2019–2025 Tushare 日线参考，不使用 seed；已验收 Tushare 父根的后续日期则先运行无 Token、无网络的 `seed-refresh`。随后严格按 `日线预检 → 源同步 → 完整构建/验收 → 激活预检 → 原子激活 → 新进程价格基准复核 → 活动根解析 → 当日未来季度质量 → Candidate49 组合预检 → --allow-large` 执行。Token 只注入日线 Tushare 预检/同步以及 Candidate49 预检/采集子进程；本地构建、激活、状态、价格基准和公开季度质量子进程会显式移除 Token 与 `QLIB_A_SHARE_DATA_ROOT` 覆盖。

每一步必须同时满足退出码和冻结 JSON 状态；任一步非零、输出不可解析、指纹/截止日/活动根不一致或 Candidate49 存在质量以外的阻塞项，都会停止所有后续步骤。日线源清单必须额外证明：参考快照路径/哈希/行数不变，参考覆盖交易日的本次重复请求数为 0，并记录复用交易日数、本次新请求的 `daily`/`daily_basic` 会话数及日线供应商调用总数；任何一项缺失或变为非零重复请求都会在季度质量与分钟采集前停止。若同一信号日已有通过组合预检的未来季度质量快照，它会直接复用；否则只有 `future_quarterly_quality_not_accepted` 是唯一失败时才刷新，避免因重跑改变已经接受的同日质量上下文。完成后在外置分钟根的 `metadata/rich_data/candidate49_future_workflows/<session>.json` 写入一次不可变的哈希证据链，包含上述历史复用统计；以后可在零 Token、零子命令、零供应商请求下复核该记录。该工作流只完成当日 source-to-signal，不读取历史/未来收益、不结算 `t+1/t+3`、不下单，也不启动 Candidate 50。

最终工作流记录本身也必须可从子产物重建，不能只遍历记录自己给出的 `evidence` 路径和 SHA。零请求复核会要求顶层字段集合、冻结协议/状态、请求的 staging/minute 根以及全部研究边界精确不变；从目标会话的确定性 raw/factor 目录和信号语义账本重建活动根、合格股票数及信号条目 SHA，再从该活动根重新验证 Tushare 激活、验收、源清单、历史参考复用统计和季度质量路径。永久记录不再保存只能说明某次进程经过、却无法事后从产物证明的 `steps`；它固定重建四项 `phase_receipts`：静态研究边界、精确截止日的 Tushare 活动日线根、同日未来季度质量、Candidate49 source-to-signal。类似地，当次命令仍可返回 `future_signal_appended` 或 `future_signal_already_present_idempotent`，但永久记录只保存事后可证明的稳定结果 `future_signal_present`；低于 50 名时则保存精确的无信号结果。最终记录也不保存无法在事后区分“首次采集”和“零调用续跑”的某次 observation 进程调用数，而只保存可重建的 `candidate49_raw_provider_calls_total`；每个原始分区必须仍证明一个逻辑供应商调用，原始清单的行数、精确时间网格、日线对账、源资格与调用数聚合也会重新计算。信号与执行账本不再绑定会随以后追加而失效的“当前整文件 SHA”，而是记录完成当时的条目数、链尖、前缀内容 SHA 和按原子 JSON 规则重建的前缀文件 SHA；因此后续会话追加信号或纸面执行后，旧会话记录仍能验证其原始前缀。改写阶段收据、稳定结果、合格数、信号 SHA、活动根、日线复用数、分钟采集总调用数或安全标志，即使重新计算工作流 JSON 的外部哈希也会硬停止，且不会加载 Token 或运行子命令。

少于 50 名是合法但终止当日信号的结果，不是可以补录或降低门槛的基础设施失败。必须保留每只不完整股票的原始行及不合格原因，仍原子发布 raw/factor 快照，保持信号账本零新增，并在永久记录和 source-to-signal 阶段收据中同时写入 `future_session_frozen_without_signal_fewer_than_50_names`、实际合格数和空信号 SHA。以后的任何日期只能零请求重放这个结果；不得补分钟、换股票、降至 49 名、重排 Top‑3 或把无信号日从前瞻样本计数中伪装为一个信号。

永久工作流记录的 JSON 语义正确还不够，文件身份也必须不可变。记录目录的既有父级链必须是解析后路径不变的真实目录，不能包含符号链接；已经存在的 `<session>.json` 必须是链接数恰好为 1 的普通文件，不能是符号链接、硬链接别名或其他文件类型。验证器会在读取 Token、获取工作流锁或启动子进程之前检查这些条件；因此即使链接指向一份语义完全正确的 JSON，也不能通过“零请求已验证”。首次写入和测试中的受控原子改写会先验证或创建真实目录链，记录目标初始设备号和 inode，在替换前复核目标没有并发出现或换 inode，先 `fsync` 临时文件，再原子替换、`fsync` 父目录，最后复核新目标仍为唯一普通文件；异常留下的临时文件会清理，已发布记录不会通过共享 inode 被另一条路径静默改写。

身份检查和内容读取之间也不能重新信任路径。最终记录现在先取得唯一普通文件的设备号/inode，再用 `O_NOFOLLOW` 打开一个文件描述符；JSON 字节和返回给调用方的 SHA‑256 必须从该同一描述符一次读取。打开后及读取完成后都用 `fstat` 复核普通文件、链接数、设备号、inode、大小、修改时间与状态变更时间，解析完成后再把确定性路径的当前身份与已打开描述符比较。即使攻击或并发进程在最初身份检查后换入一份字节完全相同但 inode 不同的 JSON，也必须报 `workflow record file identity changed during read`，不能返回“零请求已验证”；新发布记录的持久化内容和摘要也走同一绑定读取，不再另按路径计算摘要。

同一信号日的中断按已经验收的最近边界继续，而不是从头重跑：完整日线 source 直接进入本地 build，完整 acceptance 直接进入激活，已经活动且截止日准确的 Tushare 根完全跳过迁移，已经通过组合预检的同日季度质量不会重刷；若日线、质量都完成后分钟采集失败，同日重跑只重新校验活动根和质量，再恢复分钟采集。增量日线 source 只有在其 `seed-refresh` 证据仍完整时才能这样复用。15 项专项离线测试和完整 1,092 项采集测试已经覆盖这些路径；跨越当地午夜的分钟 partial 仍然禁止恢复或补录。

下面的分步命令保留为协议级排错参考。不要与上述单一入口并行运行，也不要绕过其中任何一个退出码或 JSON 门禁。

活动根可能已经从仓库 `data/` 切到外置 Tushare staging。必须在激活之后用轻量、零网络的 `data-root` 命令解析它；未来季度质量文件和清单必须写到这个活动根，不能写死为旧 BaoStock `data/`。季度质量刷新和 Candidate49 采集仍都要在目标信号日完成，其中质量刷新必须等到当地 16:00 后。预检通过后，Token 仅注入 Candidate49 子进程：

```zsh
active_data_root="$(python scripts/a_share_data_pipeline.py data-root)"
python scripts/a_share_data_pipeline.py price-basis-audit
python scripts/a_share_data_pipeline.py status

python scripts/a_share_short_horizon_factor_research.py \
  sync-quarterly-fundamentals \
  --start-year 2019 \
  --end-year 2026 \
  --through-report-date 2026-06-30 \
  --output "$active_data_root/raw/a_share/fundamentals/quarterly_quality_future.parquet" \
  --manifest "$active_data_root/metadata/quarterly_quality_future_manifest.json"

run_candidate49_session() {
  local token result
  token="$(launchctl getenv TUSHARE_TOKEN)"
  if [[ -z "$token" ]]; then
    print -u2 "TUSHARE_TOKEN is not available through launchctl"
    unset token
    return 1
  fi

  TUSHARE_TOKEN="$token" python \
    scripts/a_share_tushare_candidate49_future_observation.py \
    --data-root /Volumes/DIsk/qlib-a-share-tushare-1m \
    --session 2026-07-27 \
    --preflight-only || {
      result=$?
      unset token
      return "$result"
    }

  TUSHARE_TOKEN="$token" python \
    scripts/a_share_tushare_candidate49_future_observation.py \
    --data-root /Volumes/DIsk/qlib-a-share-tushare-1m \
    --session 2026-07-27 \
    --allow-large
  result=$?
  unset token
  return "$result"
}
run_candidate49_session
unfunction run_candidate49_session
unset active_data_root
```

上面的日线迁移/激活、季度质量刷新、组合预检和首次 `--allow-large` 采集必须都在目标会话的同一当地日期完成；季度质量仍须等到信号日 16:00 后执行。`data-root` 只打印当前解析结果，不扫描 5,000 多个日线文件、不写文件也不访问网络。若活动根仍为 BaoStock且同源刷新可用，普通 `sync` 可以继续它；本机 BaoStock 已被匿名黑名单拒绝，不得重试或原地切源。Candidate49 接受价格基准清单中唯一的 `eastmoney`、`baostock` 或 `tushare`，但 Tushare 名称本身不能替代迁移验收。`--through-report-date` 随已结束的最新季度推进，不能提前请求未结束报告期。若刷新/迁移失败、质量文件落在非活动根、清单时间不是该信号日 16:00 后、误用了历史质量路径，或已经跨到下一当地日期，采集器会在 Tushare 分钟供应商检查和请求之前停止。

`--preflight-only` 是最终的组合式零网络门禁：除原有收盘时间、日线价格基准、恰好一个受支持的日线来源、日历、可买池、账本、Token 是否注入和目标目录检查外，还验证隔离季度质量的报告频率、行数、信号日 16:00 后抓取时间以及数据/清单指纹。它还要求 `provider_uri=<活动根>/qlib/cn_a_share` 与 `daily_raw_root=<同一活动根>/raw/a_share/daily`，防止把 Tushare 名义下的 Qlib 价格基准与 BaoStock、旧版本或任意外部日线目录拼接。失败时返回 `daily_raw_root_not_bound_to_accepted_provider_root`。它不创建外置数据根、不读取分钟行、不访问供应商，也不写信号、执行或评估记录。未通过时仍会输出可诊断 JSON，但退出码固定为 `2`；只有状态为 `ready_for_explicit_future_source_to_signal_collection`、`ready=true` 且退出码为 `0` 后，才运行紧随其后的 `--allow-large` 命令。后者在账本初始化、外置会话目录创建、供应商权限检查和首个请求之前重复验证这一根绑定，并把活动根、Qlib 根、日线根及确定性小写股票代码文件布局冻结进 raw context；每个股票分区仍另外记录实际日线源文件的路径和 SHA。完整发布后的幂等复核继续验证当时冻结的根，不要求它等于后来新激活的版本化根，也不扩大冻结注册允许的日线字段集合。

同根路径还不等于同根文件。组合预检会只读扫描信号日活动可买池对应的日线文件身份，拒绝日线根本身的符号链接、任何股票 Parquet 符号链接、非普通文件或链接数不为 1 的硬链接；返回值会记录活动股票数、普通私有文件数和缺失文件数。正式采集在账本初始化前执行同一检查，并在每只股票实际读取前后复核解析路径、设备、inode、链接数、大小和修改时间，再连同完整文件 SHA 写入其不可变分区。这样即使根目录名称正确，也不能借由根外文件或共享 inode 冒充已验收的 Tushare 日线。

raw 发布完成后，factor 清单必须同时绑定 raw 清单的绝对路径、文件 SHA 和 `dataset_sha256`，不能只验证其中一个指纹。每次原子发布后或幂等复核时，验证器都会重新计算因子 Parquet 的文件/帧哈希，并从帧本身复算公式合格数、质量/上市合格数、最终合格数和应有状态；公式文字、方向、最少 50 只门槛、未来策略指纹及禁止读取/执行字段也必须与冻结合同完全一致。factor 中的季度质量文件和清单必须恰好各一份，既绑定 raw 冻结上下文中的来源路径与 SHA，也互相验证数据 SHA。删除质量上下文、伪造 raw dataset 指纹、改写公式或只改合格计数都会在信号排序前硬停止。

信号账本的哈希链只能证明“条目彼此一致”，不能单独证明 Top‑3 正确。组合预检、正式采集和纸面执行现在都会按会话顺序重放账本语义：重新验证条目引用的 raw 清单路径/文件 SHA/dataset SHA，按上述完整合同验证 factor 清单与因子帧，再用冻结的降序因子、股票代码升序并列规则重新生成整个 signal payload。除 `ordinal`、前项哈希和本项哈希外，重算 payload 必须与账本逐字段完全相同。即使篡改 Top‑3 后重新计算全部账本哈希，也会在外置新会话目录、供应商检查和分钟请求之前被 `candidate49_signal_ledger_semantics_not_accepted` 拒绝；纸面执行也使用同一重放门禁，不会在错误排名上结算。

全市场约需一次“活跃股票数”规模的 `stk_mins` 调用；4,800 只股票在 400 次/分钟上限下仅请求阶段约 12 分钟，网络重试和落盘会使实际时间更长。不要同时运行日线刷新或第二个 candidate49 采集进程。运行中断且仍在同一当地日期时才可原命令重跑；一旦跨日就保留 partial 并停止，不得删除、改写分区、绕过指纹或补采旧会话。

纸面执行细则已在任何真实未来信号、入场开盘价或结果出现前冻结为 [`a_share_tushare_candidate49_future_execution_protocol.json`](a_share_tushare_candidate49_future_execution_protocol.json)（SHA‑256 `b9b4ea8906924c8303cb7a434db5f21ed6383ce7d794e50936b675acfa869486`），实现为 [`a_share_tushare_candidate49_future_execution.py`](../scripts/a_share_tushare_candidate49_future_execution.py)。这里的三日仍沿用历史研究口径：信号日为 `t`，`t+1` 未复权开盘买入，`t+3` 未复权收盘卖出；也就是把入场日算作第一个持有会话。

执行器只做纸面账本，不访问 Tushare、不发订单。它使用一个共享的 20 万元现金账户；每个排名槽以此前一已处理收盘权益的 5% 为目标，三个槽总目标不超过 15%，按注册排名顺序以 100 股整手向下取整，并把买入费用纳入现金约束。费用固定为双边万分之一佣金、双边万分之零点二过户费、卖出万分之五印花税和双边 10bp 不利滑点，没有最低佣金。卖出所得发生在收盘，不能反过来资助同日更早的开盘买入。

只有日线原始开高低收、成交量、成交额、前收和价格基准齐全且有正成交时才可纸面成交。一字上涨日不买、空槽不替补；一字下跌、停牌或缺报价阻塞退出，随后逐个已验收收盘重试，含计划退出日在内最多 20 次，仍未成交就保留为 `terminal_unresolved` 并使完整门禁失败。同日成交额参与率只做事后容量审计，不被当成成交保证，也不反过来决定是否填单。

每个处理日都会先把可买股票、未平仓持仓、当日入场选择和到期 Rank IC 全截面的未复权日线行原子冻结到外置数据根目录；缺行显式写成缺失，不填充。这里可以复用已经通过迁移验收的 Tushare 日线：它承担日线质量/股票池基础、`t+1` 入场开盘、`t+3` 退出收盘和未来 Rank IC 结算，不需要继续绑定 BaoStock；但日线不能替代 Candidate49 在信号日所需的 241 根 Tushare 分钟线，也不能把 2019–2025 历史数据回填成事前未来信号。

执行器要求价格基准仍只绑定一个受支持的日线来源，而且 `provider_uri=<活动根>/qlib/cn_a_share` 与 `daily_raw_root=<同一活动根>/raw/a_share/daily` 必须解析到同一个活动数据根；不能把声明为 Tushare 的 Qlib 价格基准与另一个目录中的 BaoStock、旧版或任意日线文件拼接。门禁在初始化账本和发布每日快照前检查这条路径关系。

每个不可变快照会写入日历、可买股票池、价格基准三个上下文文件的路径/哈希，同时写入原始日线根的绝对路径、确定性的 `小写股票代码.parquet` 布局，以及每只股票源 Parquet 的完整文件 SHA。每次幂等复核或继续追加前都会重新验证旧快照实际绑定的三个上下文文件；逐股票源 SHA 与根路径则让抽取报价可以回溯到唯一原文件。活动 Tushare 根可以按交易日滚动到新的版本化目录，新处理日绑定新根，旧处理日仍绑定并验证原根；不得原地改写或删除旧根。实际 Parquet 读取严格投影冻结执行协议 `tradeability.required_daily_fields` 的 8 个字段，并下推 `date <= 当前处理会话`。因此处理 `t+1` 时不会把 `daily_source`、其他未注册列或 `t+2/t+3` 行载入内存；当日抽取后的 Parquet 与内容哈希就是具体报价证据。执行账本每个交易日追加一个哈希条目，记录入场机会、成交、退出/重试、现金、逐笔持仓、权益、费用、滑点、回撤和容量。固定未来 Rank IC 使用信号快照中全部合格股票的 `raw_close(t+3) / raw_open(t+1) - 1`，不套交易性过滤，至少 50 个有效结果才计为一个完成信号。

执行账本的哈希链也只能证明条目内部自洽，不能证明成交和状态是从冻结行情正确算出的。每次幂等返回或继续追加前，执行器会从 20 万元空状态开始逐日语义重放：要求账本引用的每日快照路径恰好位于该外置数据根的冻结会话目录，重新验证清单、帧与来源上下文，再用已验证信号、上一日重算状态和冻结执行协议重建入场/退出事件、费用与滑点、持仓与现金、权益与回撤、未来 Rank IC、容量及评估标志。除账本序号、前项哈希、本项哈希和非确定性的 `settled_at` 外，重算载荷必须逐字段等于原条目；`settled_at` 仍单独要求可解析、带时区且不早于处理会话。语义重放后还会把全部当前信号与已处理身份、入场链接和到期结果逐项对照，从而拒绝迟到插入或被删除的信号。即使修改成交价以及所有相关状态后重新计算整条哈希链，也不能通过这一门禁。

评估不能使用“运行命令时最新的累计值”代替预登记观察时点。执行器会在完成未来 Rank IC 数首次精确达到 60 和 200 时，把对应执行条目、结束状态和协议指纹写入 `data/experiments/short_horizon/candidate49_future_evaluations/` 下的不可变里程碑记录。第 60 个样本只有平均未来 Rank IC 与共享 20 万元组合净收益同时不为正时才提前终止；否则只记录“继续到 200、不得提前晋级”。第 200 个样本一次性检查平均 Rank IC、正 IC 比例、组合净收益、最大回撤、整手可负担率、成交额参与率和终局未解决持仓七项门禁。通过也只允许继续纸面观察，不允许聚合、当前评分或下单；失败则终止。终止里程碑后的执行条目、被改写的记录或跳过精确样本数都会硬停止，后续更好的累计结果不能事后挽救第 60/200 个样本的既定结论。

里程碑 JSON 也不能只核对 `decision`。同步器会先要求调用者提供的执行条目与磁盘上的完整通用哈希账本逐项一致，然后从里程碑条目所在位置截取当时的账本前缀；使用未变的账本头、该前缀和当时链尖，按原子 JSON 序列化规则重建“评估时账本文件 SHA”，同时重算前缀内容 SHA、条目数和链尖。记录的 `created_at` 固定复用里程碑执行条目的 `settled_at`，其余注册、协议、决策摘要、无历史回填、无网络、无下单及非投资建议字段全部确定性重建，已有记录必须与重建对象完整相等。这样账本从 60 个已完成信号继续增长到 200 个后，仍能复核第 60 个样本的原始字节状态；篡改记录中的链尖、文件 SHA、路径、计数、结论或安全标志，即使重新计算该 JSON 的外部文件哈希也会被拒绝。

source→signal 预检也以只读方式验证同一里程碑状态。第 60 个样本早停或第 200 个样本终止后，新的分钟采集会在创建外置会话目录、供应商权限检查和任何分钟请求之前拒绝，因此不会出现“执行器已终止、信号采集仍继续”的分叉；已完整发布的旧会话仍只允许零请求幂等复核。

统一研究报告以只读方式验证这些里程碑，绝不补写缺失记录。账本已经达到 60 或 200 而对应记录缺失时，报告会硬停止，必须先幂等重跑执行器恢复原时点记录。验证通过后，报告分别给出“继续到 200”“60 样本早停”“200 样本终止”或“200 样本通过但只继续纸面观察”的下一动作，不会在候选 49 已终止后仍提示继续采集。

统一报告不能用比执行器更弱的“通用哈希链有效”来展示真实信号数、累计收益或下一动作。`overlay_candidate49_live_ledger_state` 现在调用执行模块的只读报告验证器：先从 raw/factor 不可变证据重建每条信号；存在执行条目时，再读取当前已验收本地日历，从最新执行快照的固定目录后缀反推出唯一外置数据根，并从空 20 万元状态重放所有每日快照、成交、费用、持仓、Rank IC 与评估状态；随后核对完整信号—执行链接，并以只读模式验证 60/200 记录。信号日还没有足够后续日历来确定 `t+1` 或 `t+3` 时，该信号明确保留为待处理，不会被误判为缺失执行，也不会预构造未来会话。整个报告验证不写文件、不补里程碑、不访问供应商；一个只有合法哈希链但没有 raw/factor 证据的伪信号会在计数和渲染前被拒绝。

为了在写入入场 lot 时就确定其 `t+3`，被处理会话之后必须已经有两个**已验收且已经越过收盘缓冲**的本地会话；执行账本因此故意滞后两个会话，并不会从未来价格取值。门禁同时检查日历位置和第二个后续会话的实际收盘时间，不能把日历文件中预先列出的未来日期当成已完成会话。例如 2026‑07‑27 信号的 2026‑07‑28 入场，最早在日历和日线已验收到 2026‑07‑30 收盘后才能物化；要把 2026‑07‑30 的退出也写入，则需再等 2026‑07‑31、2026‑08‑03 成为已验收会话。命令不需要 Token：

```zsh
python scripts/a_share_tushare_candidate49_future_execution.py \
  --data-root /Volumes/DIsk/qlib-a-share-tushare-1m \
  --through-session 2026-07-28
```

离线测试已覆盖：共享现金与三项费用/滑点、同日收盘卖出款不能资助更早的开盘买入、整手 Top‑3、`t+3` 退出、50 名全截面 Rank IC、幂等重跑、一字涨停空仓不替补、20 次阻塞退出转终端未解决、收盘前零写入、日历不足两个后续会话零写入、日历虽预列未来会话但尚未收盘时零写入、幂等返回前拒绝后来插入的迟到信号、终止里程碑在供应商检查前阻止新信号、日线错源在快照/账本前停止、已发布日线快照改变后在新条目前硬停止、旧快照绑定的来源上下文被改写后在新条目前硬停止、Tushare 单一日线源完整走通 `t+1` 至 `t+3`、版本化 Tushare 根滚动时保留旧根取证、不同活动根的 Qlib provider 与原始日线目录在任何快照或账本写入前拒绝、精确 60 样本联合早停、60 样本禁止提前晋级、精确 200 样本通过/失败以及里程碑篡改或终止后续写拒绝。这些结果仍只是实现验收；当前真实信号数、成交数、未来 Rank IC 数和组合收益全部是 0，不能据此下单。

### CNInfo 补充更正披露负担（全历史分页稳定性终止）

在上述 Tushare/本地券商审计之后，只补查了此前未覆盖的 CNInfo 官方分类元数据。官方检索脚本 `history-notice.js?v=20260710082532` 的观测 SHA‑256 为 `ef36c3fb82af6b4176c2b4fcf92c1c7eb58ff03beba7931fa48bc1b2b417213a`，其中明确把 `category_bcgz_szsh` 标为“补充更正”。机制复核 `docs/a_share_three_day_cninfo_supplement_correction_disclosure_burden_mechanism_overlap_reaudit_20260721.json`（SHA‑256 `95e8e93d5ace85e44fbe6d682cdea1c1873cfba9152b06fcb37c0c4e626c3853`）在公告行前只推进这一项：`cninfo_supplement_correction_disclosure_resilience = (1 + 距最近已生效公告的自然日数) / 最近三自然日内有效的唯一补充更正公告数`，高值固定为更好；无有效事件的股票保持缺失，不得当成零负担或满分。

数据合同 `docs/a_share_cninfo_supplement_correction_disclosure_burden_data_contract.json`（SHA‑256 `d27dd754890d5c8d7743630164e68ea9f7169c466b3babaa26c74f6697d6f53b`）只从公共 `hisAnnouncement/query` 的该分类读取 `secCode,announcementTime,announcementId`。它明确不读取标题，因此即使响应含 HTML 标记也不能影响本机制；公告 ID 只在内存去重，允许来源把同一 ID 显式映射到多个支持股票，只折叠代码/ID/日期完全相同的重复，冲突日期则终止。事件严格在公告日后的第一本地交易日收盘生效，输出只允许 `announcement_date,instrument,supplement_correction_notice_count,provider` 四列。

唯一验收清单 `20260721T093018Z_cninfo_supplement_correction_disclosure_burden_acceptance_0c42fcbd.json`（SHA‑256 `74c47eb4a091b102353b6e2d7ae1c4210226aca40977e92849e398fcf506fa14`）完成九个月、41 次请求并逐页对账 1,076/1,076 行。排除 62 条不支持板块记录后得到 1,014 个唯一代码/公告身份和 974 个股票/日期事件；2019Q1、2024Q1、2025Q1 分别产生 53、33、11 个至少六只股票且至少两个取值的候选截面，总计 97，物化值共有 10 种。独立本地复核重现四列表、文件/内容哈希、1,014 个计数和所有截面；事件键重复为 0、点时持有范围外记录为 0，标题、ID/哈希、原始响应、价格和收益均未落盘。跨克隆验收记录是 `docs/a_share_cninfo_supplement_correction_disclosure_burden_source_acceptance_record.json`（SHA‑256 `9ea84b1155f77dff651f8e0484523441606e83edf4b23cd7ec5efc5ec13d666b`），验收已永久消费。

验收后、未验收月份之前冻结了全历史无收益协议 `docs/a_share_cninfo_supplement_correction_disclosure_burden_no_return_preregistration.json`（SHA‑256 `e9a7d740470788dfaaddc318393e63c2bac92681f0fcff0dcfa23318de64a84b`）。唯一全量复用已经验收的月份且没有再次请求它们，随后顺序完成 28 个新月份、234 次完整分页调用和 6,682/6,682 行对账；最后完整月份为 2021‑07。固定顺序的下一月 2021‑08 在同一叶分区后续页返回了不同的 `totalAnnouncement`，违反预注册的稳定分页计数，因此立即终止。共享传输助手在错误文本中保留了旧的 “equity-incentive” 标签，但清单中的运行 ID、分类和字段明确属于本分支；这个显示标签不授权修复或重试。

失败清单 `20260721T093902Z_cninfo_supplement_correction_disclosure_burden_full_75258ef6.json` 的 SHA‑256 为 `eccf58bd19b3449975eb8357c5e35b0fdac3ee6663e459040b8e5b486142dc2f`；跨克隆终止记录 `docs/a_share_cninfo_supplement_correction_disclosure_burden_full_source_record.json` 的 SHA‑256 为 `c331ef49010cc3481b0449326855cc8e0d879e0fd9607e9c27139af29449535a`。完整临时快照已删除，年度文件和成功全量清单均为 0，非活动锁标记保留；比较字段、价格和未来收益均未读取。不得重跑或续传全量、重取 2021‑08、把动态计数当瞬时网络错误、改变分页/分类/字段/身份/公式/方向/三日年龄、使用已完成的部分月份、从验收样本运行容量或收益，也不得聚合、当前评分、选股、定仓、下单或据此采购 Level‑2。该结果只是来源一致性终止，不是因子收益失败。

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

### Tushare 业绩快报资产扩张约束（来源验收终止）

核心利润一致性终止后，新的独立机制只选择 `tushare_express_asset_growth_restraint = -growth_assets`：较低的期初以来总资产增长率解释为更克制的资产负债表扩张。营业收入、利润、EPS、ROE、文本摘要及其增长字段全部禁止读取，避免在同一响应上事后筛选盈利类字段。无收益机制核重记录为 [`a_share_three_day_express_asset_growth_mechanism_overlap_reaudit_20260717.json`](a_share_three_day_express_asset_growth_mechanism_overlap_reaudit_20260717.json)（SHA‑256 `94c0c4655918976c3113055d94e573a1bbcaf9cff85ecfc409d3f74e5a593ba4`）。该记录没有观察供应商行、因子值、价格或收益。

数据合同 [`a_share_tushare_express_asset_growth_data_contract.json`](a_share_tushare_express_asset_growth_data_contract.json)（SHA‑256 `517a9e402ecd77f4f09090414ff4e68a45a0af215ff9b200703a4f8ea6d3e177`）固定使用标准 `express` 接口，只请求 `ts_code,ann_date,end_date,growth_assets`，要求账户至少 2,000 积分；当前 3,000 积分不需要 5,000 积分的 VIP 接口。唯一验收固定按 `600000.SH`、`000001.SZ`、`300750.SZ` 顺序各请求一次 2019–2025 历史，任一失败立即停止且不得重试。验收帧只允许保存公告日、报告期、股票、负资产增长率因子和供应商五列，不保存原始响应或原始 `growth_assets`。

唯一真实验收在 463 项数据采集测试通过后执行了全部三次固定请求，`600000.SH`、`000001.SZ`、`300750.SZ` 分别返回 11、4、2 行，共 17 行；每一行的 `growth_assets` 都缺失或非有限，因此三个股票均为 0 个有效事件，未达到至少 2 个股票、6 个事件的冻结门槛。失败清单是 `20260717T005128Z_tushare_express_asset_growth_acceptance_6719f415.json`（SHA‑256 `4c8b8fee687d42fc246532b4037657f754955248dd26f1e1bd7e531a30c29902`）。它没有保存原始响应或 `growth_assets`，没有发布 Parquet，没有读取价格或收益，也没有形成有限因子值。

跨克隆终止记录为 [`a_share_tushare_express_asset_growth_source_acceptance_record.json`](a_share_tushare_express_asset_growth_source_acceptance_record.json)（SHA‑256 `71a61cdfb33359e07f74e101b7958258fce08a70974aee2be0aab16179e48b1e`）。验收入口会在合同、Token 和供应商访问前拒绝重跑。不得换股票或日期、重请求明细、删除/填充缺失值、改用同一响应的盈利/资产/权益字段、反向或改变公式，也不得继续全量、容量、唯一性、收益、聚合、评分、选股、仓位、订单或 Level‑2。该结果只说明冻结样本的字段覆盖失败，不是因子收益证据，也不证明所有 `express` 记录都缺少该字段。

### Tushare 合同负债需求积压（全量来源覆盖终止）

下一轮不读取收益的机制前沿审计冻结在 [`a_share_three_day_contract_liability_backlog_mechanism_overlap_reaudit_20260717.json`](a_share_three_day_contract_liability_backlog_mechanism_overlap_reaudit_20260717.json)（SHA‑256 `2d8cc98378f7e2ffac7182f80a9fbb8c0288c769ca4de9f1c5d68abd1ded0729`）。唯一候选 `tushare_contract_liability_backlog_delta = (当期合同负债 - 上年同季度合同负债) / 当期总资产` 用于刻画由客户预付款支持的需求积压；它与已经研究的利润、资产扩张、总杠杆、现金转换、持有人、订单流和价格机制分离，高值方向固定为更好。

数据合同 [`a_share_tushare_contract_liability_backlog_data_contract.json`](a_share_tushare_contract_liability_backlog_data_contract.json)（SHA‑256 `4c6105188ce7246fd9069fdf3e547e612813998b6316ec332e42acdb0aecf611`）固定使用至少 2,000 积分可调用的标准 `balancesheet` 单股历史接口；当前 3,000 积分不使用 5,000 积分 VIP。请求只能包含 `ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,contract_liab,total_assets,update_flag`。只有一般工商业 `comp_type=1`、合并报表 `report_type=1` 可进入公式；任何调整报表类型排除整个报告期，`update_flag` 只计数、不选版本，跨切片冲突也不得修复。实际公告日 `f_ann_date` 是信号日，只允许下一本地会话开盘使用，最长三自然日。

唯一真实验收在 469 项数据采集测试通过后，按 `600519.SH`、`000333.SZ`、`300750.SZ` 和四个固定两年公告切片完成 12/12 次单次尝试。共返回 146 行，预先规则观察 98 个目标公司报告期；29 个报告期因合同负债或总资产缺失/非有限而排除，28 条精确语义重复折叠，最终保留 69 个报告期并形成 55 个有限因子事件。三只股票分别有 19、17、19 个事件，55 个值全部不同，范围为 −0.015350 至 +0.031225，公式最大误差、完整事件键重复和信号键重复均为 0。成功清单 `20260717T011835Z_tushare_contract_liability_backlog_acceptance_3d78a4ab.json` 的 SHA‑256 为 `d407969b0f508b388f94711051b6509527c05dfdf4451226bf1cf4a5ac6f5680`；五列派生帧内容 SHA‑256 为 `0eccb77f5e9d32323e8b5c71ca92eea330873e62c0ee903d6346b4de11ca3cda`。原始响应、合同负债和总资产金额均未保存，也没有读取价格或收益。

跨克隆验收记录为 [`a_share_tushare_contract_liability_backlog_source_acceptance_record.json`](a_share_tushare_contract_liability_backlog_source_acceptance_record.json)（SHA‑256 `5a06db91c904c38bf0415cbff7cec6987e72212d8349a3805ca4a7749911295b`）。验收入口会在合同、Token 和供应商访问前拒绝重跑；不得换股票、切片、字段、版本规则、公式或方向。该结果只证明固定样本的来源、版本和公式可用，不是收益、执行或当前选股证据。

后续全市场来源与无收益协议冻结在 [`a_share_tushare_contract_liability_backlog_no_return_preregistration.json`](a_share_tushare_contract_liability_backlog_no_return_preregistration.json)（SHA‑256 `7528d5ab17c24b4c0904f6d213311a0a5132ab7a0c897fa572223e9de1455dc8`）。唯一全量于 2026‑07‑20 完成协议规定的全部请求：固定来源宇宙 5,451 个区间，直接复用验收三股，对其余 5,448 股四个固定切片完成 21,792 / 21,792 次调用，取得 217,539 条来源行和 76,511 个开发期完整派生事件。完整事件数、七个信号年份和报告期覆盖中位数 78.10% 均通过；27 个报告期的 P05 覆盖只有 2.12%，低于冻结的 30% 门槛，因此全量来源被拒绝。主要缺口集中在本次冻结快照的 2019Q1–2020Q4，单期覆盖仅 0.19%–4.03%，不能通过删除早期历史或降低门槛修复。

来源 P05 门失败后，隐藏临时快照已删除，没有发布年度 Parquet 分区或成功全量清单。本机失败清单为 `data/metadata/rich_data/runs/20260720T095129Z_tushare_contract_liability_backlog_full_ba447c5b_source_failure.json`（SHA‑256 `ab980476d67f3501c8686775425907158f544659028f5e5b8b013d35ac40a4f0`）。原始响应、合同负债/总资产金额、Token、价格和收益均未保存或读取。

跨克隆终止记录为 [`a_share_tushare_contract_liability_backlog_research_record.json`](a_share_tushare_contract_liability_backlog_research_record.json)（SHA‑256 `982d3014b82b13ef85017e68ed8e4a2fa2e23336b752d3d488169b1a2daf2519`）。`sync-tushare-contract-liability-backlog --allow-large` 现在会在无收益协议、合同、Token 和供应商访问之前拒绝重跑。不得局部续传、单股修补、缩短到 2021 年以后、改切片/字段/版本规则/公式/方向或降低覆盖门槛。

因为没有成功全量清单，`tushare-contract-liability-backlog-no-return-audit` 从未真实运行；入口现在也会在读取清单、本地价格基座、质量数据或 48 个比较字段前按终止记录拒绝。因此容量门、唯一性门和毛利率语义门均未运行，更没有收益诊断、聚合、评分、选股、仓位或订单结果。此机制不进入当前因子库；下一步只能重新审计机制前沿并在读取新供应商行或因子值前冻结一个经济上独立的新候选。

### Eastmoney 关联交易披露稀疏度（收益、稳定性与执行门终止）

合同负债在全量来源 P05 覆盖门终止后，新一轮机制核重只选择 `eastmoney_related_party_transaction_sparsity = 1 / related_party_transaction_count`。其中计数仅为同一股票、同一 `NOTICE_DATE` 下完整且唯一的 `EID` 数；高值固定解释为同日关联交易披露聚集较少。交易金额、币种、交易方、关联关系、交易文本、控制标志以及网页展示的最新营收和净利润全部禁止请求或保存，避免币种混合、当期不可知财务分母和文本/身份字段泄漏。无收益机制记录为 [`a_share_three_day_related_party_transaction_sparsity_mechanism_overlap_reaudit_20260720.json`](a_share_three_day_related_party_transaction_sparsity_mechanism_overlap_reaudit_20260720.json)（SHA‑256 `697def3023b93b639363b05c262293dda75cb515fa58d8124ea5e96384d61190`）。

数据合同 [`a_share_eastmoney_related_party_transaction_sparsity_data_contract.json`](a_share_eastmoney_related_party_transaction_sparsity_data_contract.json)（SHA‑256 `242baad268f11c56b0c3ccb14b9726f653b908e553d0b1d39faed36e6069c277`）固定 Eastmoney 公共 `RPT_RELATED_TRADE` 报告，只请求 `SECURITY_CODE,NOTICE_DATE,EID`。任何缺键、畸形键、分区外日期、重复股票/日期/EID、分页广告数变化或接收行数不符都会终止；完整但不属于主板/创业板的代码只排除并计数。EID 只在内存中用于唯一性与计数，随后丢弃；规范帧只有公告日、股票、正整数计数、倒数因子和 `provider` 五列。公告最早在严格下一本地交易日使用，最长三自然日；没有事件保持缺失，不能填成零或有利值。

唯一来源验收固定为 2019Q1、2024Q1、2025Q1 三段。102 次公共请求完整接收 50,597/50,597 条广告记录，点时持有池最终形成 4,040 个股票公告日事件；三个样本窗分别有 54/58/57 个至少 6 只股票且至少 2 个因子值的横截面，合计 169 个，因子有 130 个不同值。重复键、缺键、下一会话映射缺失和公式误差均为 0，EID 与禁止字段均未落盘。验收清单为 `20260720T125250Z_eastmoney_related_party_transaction_sparsity_acceptance_db9e2dde.json`（SHA‑256 `c61e47b05354e11119b4bf80f335dc334cc1042c6fc30c4d9bdd16d58e31fd70`）；跨克隆记录为 [`a_share_eastmoney_related_party_transaction_sparsity_source_acceptance_record.json`](a_share_eastmoney_related_party_transaction_sparsity_source_acceptance_record.json)（SHA‑256 `054728119ccfd39858e4eb391a16097a3b63f9f2ef8cfebf9f928f9dfa29c582`）。验收入口已永久消费。

验收后、全量前冻结的协议为 [`a_share_eastmoney_related_party_transaction_sparsity_no_return_preregistration.json`](a_share_eastmoney_related_party_transaction_sparsity_no_return_preregistration.json)（SHA‑256 `51447a3647ad461480b98a01c7d55f094c0dbd139c81fa8abfb378f4167e20d8`）。唯一全量复用验收覆盖的 9 个月，不重复访问供应商，并请求其余 75 个月。2024‑04 整月第一页显示 84 页，超过冻结的 80 页上限；程序没有继续请求该父分区后页，而是先拆成 2024‑04‑01 至 04‑15 的 13 页和 04‑16 至 04‑30 的 72 页，两段分别完整对账。全量共 933 次新调用（含一次父分区探测）、447,536 条新来源记录，加上验收的 50,597 条来源证据，最终一次性发布 2019‑01 至 2025‑12 共 84 个月分区、51,401 个点时持有池事件。

七年事件数为 7,011/7,365/7,104/7,446/7,673/7,738/7,064；因子有 223 个不同值，无质量/上市门的来源上界横截面为 1,598，远高于 500 的来源门。所有 84 个分区的内容摘要、51,401 行、公式、全局事件唯一性和年份覆盖均已独立重算；最大公式误差为 0，EID、禁止字段、价格和收益字段均不存在。全量清单为 `20260720T130538Z_eastmoney_related_party_transaction_sparsity_full_53f2347e.json`（SHA‑256 `e8a668ffda6668040f1129c60d402aa9731560801475fe2644f7fb7146b089e9`）；跨克隆全量记录为 [`a_share_eastmoney_related_party_transaction_sparsity_full_source_record.json`](a_share_eastmoney_related_party_transaction_sparsity_full_source_record.json)（SHA‑256 `45f39cfd550728c2b5d2260930cf1758a4aee924ca4d35d43cf457b2531c2aac`）。全量入口也已永久消费。

唯一完成的无收益审计为 `20260720T132935Z_eastmoney_related_party_transaction_sparsity_no_return_audit.json`（SHA‑256 `277d6c4ca1f25b275cc1cf94f8a4a1b761f084808472fb9d2c83d25389cd40b2`）。固定 566 个三日非重叠再平衡位中，质量、上市 20 会话、至少 6 名且 2 个值的完整 cohort 有 **352 / 200** 个，2019–2025 七年分别为 38/53/62/57/52/47/43，容量门通过。六个稀疏近邻都完成语义复核；只有 `analyst_valid_rating_report_count` 达到 100 个统计会话，其 358 个有效会话的日秩相关中位数为 −0.0350，通过绝对值低于 0.8 的门槛。其余五项按预注册规则只作重叠描述，不以样本不足判失败。三个稠密混淆项各有 166 个至少 50 名的有效会话，`free_float_cap_proxy`、`liquidity_5`、`turnover_surge_1` 的相关中位数分别为 −0.2212、+0.1586、−0.0388，全部通过。

第一次入口调用曾因候选公告日与季度质量公告日同名而在容量计算前中止；没有审计文件、比较字段、价格或收益产生。候选公告列改名并加入专项回归测试后才执行上面的唯一完整审计，规则、阈值、方向、时点和目录均未改变。跨克隆无收益记录为 [`a_share_eastmoney_related_party_transaction_sparsity_no_return_record.json`](a_share_eastmoney_related_party_transaction_sparsity_no_return_record.json)（SHA‑256 `827aacdfc661c280cd22dbc3f97b3e6fc3ad7b91489861bd45c1d6a65c581cc8`）。`eastmoney-related-party-transaction-sparsity-no-return-audit`、来源验收和全量入口现在都必须拒绝重跑。

价格读取前冻结的唯一诊断协议为 [`a_share_eastmoney_related_party_transaction_sparsity_diagnostic_preregistration.json`](a_share_eastmoney_related_party_transaction_sparsity_diagnostic_preregistration.json)（SHA‑256 `fcb1686eaed04764b545c80318fa6fcb74b922c4c5722e81a566c96bc7790848`）。它绑定完整来源、无收益审计和记录、接受价格基准、2019–2025 开发窗、严格公告后首个交易日生效、三自然日事件时效、三交易日非重叠持有、Top‑3、0.012%/0.062% 成本、550 日质量、20 会话上市门，以及前瞻成交与 20 万元/100 股/10bp/成交额 1% 执行规则。专用入口不暴露日期、方向、公式、时效、TopK、成本或门槛参数。

唯一诊断 `20260720T134932Z`（SHA‑256 `9f208c7d7b0781dd2221a57ec3b651416cd83149a208359f070a3e47981192ed`）包含 351 个有效横截面。平均/中位 Rank IC 为 **−0.02105 / +0.00426**，正 IC 比例 50.71%，Top‑3 减 Bottom‑3 的平均毛收益差为 **−0.1351%**；2020、2021、2022、2024 年平均 IC 为负。普通固定持有 Top‑3 虽累计 +26.17%，但最大回撤 −45.36%、中位单期 −0.1481%、胜率 48.43%、P05 −5.02%、最差单期 −13.53%，不能绕过关联稳定性与执行门。

前瞻保守成交台账有 420 个完整信号、1,260 个登记槽位和 1,253 个成交槽位，累计 +21.47%，但最大回撤 **−44.04%**，且 2019–2022 四年为负，执行门失败。按用户固定的 20 万元、每槽 5%、最高 15% 暴露、100 股整手、万一佣金无最低、双边 0.002% 过户费、卖出 0.05% 印花税、双边 10bp 主门槛重算后，整手可负担率 96.17%，最大成交额参与率 0.5007%，但期末仅 191,461.91 元，累计 **−4.27%**，2019–2022 四年仍为负。0/5/10/20bp 描述性累计收益分别为 +6.12%/+1.26%/−4.27%/−13.48%；10bp 才是冻结的主门，不能改用零滑点结果。

完整稳定性审计 `20260720T134945Z`（SHA‑256 `684c2f5154c431dbe5861d23b1159f28a8cdbde1802828117bbcb5f4ec5b5dba`）和 Top‑3 可行性审计（SHA‑256 `a9e63484602dd9a73188ad793304bcce338a3550a0d0e8b426bd163c4fab27d3`）均为 0/1 通过。跨克隆终止记录为 [`a_share_eastmoney_related_party_transaction_sparsity_diagnostic_record.json`](a_share_eastmoney_related_party_transaction_sparsity_diagnostic_record.json)（SHA‑256 `b8bda6862349a0ff9082109a3e176b4ecc195dc9be5bfb07043e91c6e7460dba`）。此分支永久终止：不得重跑、反向、改变计数/时效/年份/持有期/TopK/成本/质量/上市/执行规则、选有利年份或事后加过滤器；不得聚合、当前评分、选股、仓位、订单，也不能据此采购 Level‑2。下一步只能回到新的、经济机制独立且先无收益预注册的候选。

### CNInfo 近期对外担保披露稀疏度（来源传输结构终止）

关联交易因子在收益与执行门终止后，新一轮机制核重只选择 `cninfo_recent_guarantee_disclosure_sparsity = 1 / guarantee_count`：每个信号只统计此前三个完整本地交易日内、至少披露一次担保的股票，记录越少分数越高；没有披露保持缺失。担保金额、归母权益、供应商比率、证券名称、价格和收益均不进入因子。机制记录为 [`a_share_three_day_cninfo_guarantee_sparsity_mechanism_overlap_reaudit_20260720.json`](a_share_three_day_cninfo_guarantee_sparsity_mechanism_overlap_reaudit_20260720.json)（SHA‑256 `295dd5e8461fac0b3d203830499ce6550c2450d708c4ee3b9afa87ec7ff20a94`）。

数据合同 [`a_share_cninfo_guarantee_sparsity_data_contract.json`](a_share_cninfo_guarantee_sparsity_data_contract.json)（SHA‑256 `1c59a4fdabbb7ae82d3279e83f81e55b3518f9634201379a96d59e25a7e12e68`）在任何 CNInfo 公司记录或因子值出现前冻结。来源固定为公共 `p_sysapi1054`，依次请求深市主板 `012002`、沪市 `012001`、创业板 `012015`；固定 AES‑128‑CBC 时间签名只在请求内存中生成，不是凭据且不得落盘。样本是冻结 2019–2025 信号网格中的 2019Q1、2024Q1、2025Q1，共 57 个信号、171 个计划市场窗口。每条来源记录必须恰为七位位置数组，且只允许区间、担保次数和代码进入规范化；30 秒超时、最多三次尝试、调用间至少 0.1 秒均在真实访问前固定。

467 项离线回归通过后执行唯一真实验收。首个信号 `2019-01-07` 的深市主板窗口 `2019-01-02` 至 `2019-01-04` 连续三次都得到顶层 `records` 列表，但至少一条记录不是合同要求的七位 list/tuple，而是对象形态；因此程序在任何规范化、股票池过滤或因子计算之前终止。完成市场窗口和信号窗口均为 0，规范行与因子值均为 0；没有发布 Parquet，隐藏临时目录已删除，原始响应、名称、金额、权益、比率和签名头均未保存，也没有读取价格或收益。

本机失败清单是 `data/metadata/rich_data/runs/20260720T141256Z_cninfo_guarantee_sparsity_acceptance_9f29ed74.json`（SHA‑256 `8a2c04d590972c14012e49112a8738aeeace6c24517635826f947ffb2a977ac7`）；跨克隆终止记录为 [`a_share_cninfo_guarantee_sparsity_source_acceptance_record.json`](a_share_cninfo_guarantee_sparsity_source_acceptance_record.json)（SHA‑256 `0719385358e9cbed298eb34c32f864093d7298253dab770e0297673a8ae6688d`）。`acceptance-cninfo-guarantee-sparsity` 现在会先验证该记录，再在合同、本地上下文、签名和网络之前拒绝重跑。

这是来源传输结构失败，不是收益证据。观察不匹配后不得把对象字段改写成七位数组、重请求同一窗口、换板块/日期/接口/字段、调整三日窗口/公式/方向/阈值，或改用担保金额、权益比率、诉讼数据救援；也不得继续全量、无收益审计、收益诊断、聚合、评分、选股、仓位、订单或 Level‑2。此分支不向因子池贡献值；下一步只能重新审计一个经济上独立、先无收益冻结的新候选。

### Eastmoney 货币资金资产占比（无收益容量门终止）

CNInfo 担保披露分支在传输结构门禁终止后，新的机制审计冻结为 [`a_share_three_day_monetary_funds_asset_intensity_mechanism_overlap_reaudit_20260721.json`](a_share_three_day_monetary_funds_asset_intensity_mechanism_overlap_reaudit_20260721.json)（SHA‑256 `6f195390c950e08f10cd5c0725497c769434f6848ce8eeee22a4b77a6088a419`）。唯一候选是：

```text
eastmoney_monetary_funds_asset_intensity = monetary_funds / total_assets
```

高值方向固定为更好，只表示报告口径下货币资金占总资产比例更高，不能宣称为已核实的无限制现金。应收账款/总资产因重叠现金转化和会计质量机制、存货/总资产因行业与周期依赖、货币资金/总负债因直接复用已终止的杠杆分母，均在读取新来源行前拒绝。

数据合同 [`a_share_eastmoney_monetary_funds_asset_intensity_data_contract.json`](a_share_eastmoney_monetary_funds_asset_intensity_data_contract.json)（SHA‑256 `f879f2095936e6a1f084432bbce2c5d5f2f74951d4a12d1742064b1e365b8d82`）绑定 AKShare 提交 `fcdbf25aa864a218c54864c3f6ab6a2ed19cce28` 的 `stock_zcfz_em` 适配器和 Eastmoney 公共 `RPT_DMSK_FN_BALANCE` 报告。传输必须维持 57 列和顺序哈希 `08dbc752c0ec71e56d9aea88c0a1ecfa0929dbe006c6b71bd6c7422d6b2515e3`；只允许代码、公告日、总资产、货币资金四个预声明位置进入规范化。总资产须有限且严格为正；货币资金须有限、非负且不大于总资产；明确报告的零值有效，其他无效值只排除并计数，不填充、裁剪、取绝对值或换用响应中的其他字段。公告当日不可交易，因子在公告日后的第一个本地交易日收盘才可用，若后续获准诊断则下一交易日开盘入场，最长保持 3 个自然日。

在 473 项完整离线回归通过后，唯一一次 2025‑12‑31 来源验收完成 11/11 页、5,218/5,218 行。规范化前有 4,605 个完整主板/创业板身份；点时可持有股票共 4,581 个，最终发布 4,574 个有效名称，覆盖率 **99.8472%**，4,574 个取值全部不同，范围为 0.00218176–0.88652427，公式最大绝对误差为 0，重复键和无效资产/货币资金行均为 0。只发布七列规范 Parquet；未保存其余 53 个传输字段，也未读取 `TUSHARE_TOKEN`、价格或收益。

接受清单为 `data/metadata/rich_data/runs/20260721T060142Z_eastmoney_monetary_funds_asset_intensity_acceptance_5196e914.json`（SHA‑256 `77172da63f5e94eebc04fb3a5493f907c22fc59c734ab84b85e33eb96e2e9907`）；跨克隆记录为 [`a_share_eastmoney_monetary_funds_asset_intensity_source_acceptance_record.json`](a_share_eastmoney_monetary_funds_asset_intensity_source_acceptance_record.json)（SHA‑256 `bcea6af54b32eb80c4118345a72be01b332c626217bba87ec95217d1811c5171`）。不得再次运行 `acceptance-eastmoney-monetary-funds-asset-intensity`；守卫会在合同或供应商访问前核验记录并拒绝。

全量与无收益协议 [`a_share_eastmoney_monetary_funds_asset_intensity_no_return_preregistration.json`](a_share_eastmoney_monetary_funds_asset_intensity_no_return_preregistration.json)（SHA‑256 `b8cf79b968ee9ca609748508e82d4a30d8fc9762c9e4794f5648c4b18c7f5f14`）已经在任何其他季度来源行前冻结。唯一全量命令已经消费：它复用已接受的 2025Q4 分区而未重复请求，用 27 个网络分区和 277 次供应商调用原子发布 2019Q1–2025Q4 共 28 个季度、114,418 行。年度行数依次为 13,739、14,473、15,735、16,772、17,550、17,936、18,213；完整身份和有效因子覆盖率的季度最小值/中位数/最大值为 94.0817%/96.9802%/99.8906%。全部分区的公式、键、七列规范结构、文件与内容哈希独立复核通过，公式最大误差为 0。

本机全量清单为 `data/metadata/rich_data/runs/20260721T061812Z_eastmoney_monetary_funds_asset_intensity_full_ef43d4e5.json`（SHA‑256 `ee9d7cacd2097b840b2f0cfafd177fd5bb8203fea5df95b292ca14e962eba885`）；跨克隆来源记录为 [`a_share_eastmoney_monetary_funds_asset_intensity_full_source_record.json`](a_share_eastmoney_monetary_funds_asset_intensity_full_source_record.json)（SHA‑256 `0b399ab472a425702e8fe40387849e2b258032081e5bac44d984b0272cce557e`）。不得再次运行：

```bash
python scripts/a_share_rich_data.py \
  sync-eastmoney-monetary-funds-asset-intensity --allow-large
```

唯一无收益审计 `20260721T064408Z`（SHA‑256 `f2a5051a0b673c7b22a245b1898d0f8723eedd9ab815a25e0c7ac5a6a7f227d6`）在固定 566 个非重叠三交易日网格上，先把公告严格映射到下一本地交易日，并只保留公告日起不超过 3 个自然日的值。57,973 个展开行中，10,985 个晚披露旧报告行因不得覆盖更新报告而剔除；46,988 个点时持有行经过 20 会话上市与 550 日财务质量门后只剩 9,839 个候选值。最终只有 **114/200** 个完整 cohort，年度为 17/17/19/16/16/13/16，虽覆盖七年但容量不足，因此在第一道无收益门终止。

首次入口调用曾因候选报告期与季度质量报告期同名而在容量计算前中止；没有审计文件、比较字段、价格或收益产生。基础设施修复只把候选审计列改名为 `monetary_funds_report_date`，新增同时保留两个报告期的回归测试后，用完全相同参数完成上述唯一审计；公式、方向、时效、样本、网格、质量、上市、阈值和比较目录均未改变。独立重算复现了 9,839 个合格行、114 个 cohort 和全部年度计数。

容量失败意味着固定七项比较从未加载，唯一性门未运行，也没有读取价格或未来收益。跨克隆终止记录为 [`a_share_eastmoney_monetary_funds_asset_intensity_research_record.json`](a_share_eastmoney_monetary_funds_asset_intensity_research_record.json)（SHA‑256 `d2a21996cb3e622a307c80e7218036f082ff320b7b79367631595ea6956b588a`）。不得再次运行验收、全量或无收益审计，不得反向、延长三自然日、降低质量/上市/名称/取值/容量门、改变比较项，亦不得继续收益诊断、聚合、当前评分、选股、仓位、订单或 Level‑2。下一步只能回到一个经济机制独立、在读取新来源行或因子值前冻结的新候选。

### Eastmoney 政府补助公告强度（来源身份门终止）

货币资金资产占比分支终止后，新一轮无收益机制核重冻结为 [`a_share_three_day_government_subsidy_disclosure_intensity_mechanism_overlap_reaudit_20260721.json`](a_share_three_day_government_subsidy_disclosure_intensity_mechanism_overlap_reaudit_20260721.json)（SHA‑256 `8e518365a05fc98056502a43c492dd4f44ec9195046588af2e2987c76030e368`）。研发投入候选被判定为复用已终止的 Tushare 财务报表/指标路线；筹码分布需要当前账户未具备的 5,000 积分权限；开盘和收盘集合竞价需要独立权限。当前只推进经济上不同的外部支持催化候选：

```text
eastmoney_government_subsidy_disclosure_intensity
  = latest already-effective government_subsidy_announcement_count
    / (1 + calendar days since notice)
```

数据合同 [`a_share_eastmoney_government_subsidy_disclosure_intensity_data_contract.json`](a_share_eastmoney_government_subsidy_disclosure_intensity_data_contract.json)（SHA‑256 `b7b351e8c31e65391c208b5133ed0d740bea7b8cdeb7686e0c26866b89b360af`）在任何新公告行、标题、因子值、价格或收益出现前固定。来源是 Eastmoney 公共重大事项公告接口，只允许传输 `art_code,notice_date,title,codes,columns`；标题经 NFKC 和空白规范化后，仅匹配“获得/收到政府补助或补贴”的四个固定字面量，并排除更正、补充、修订、进展、取消和撤回。`art_code` 和标题只在内存中用于唯一性与分类，最终规范帧只保存公告日、股票、同日合格公告数和供应商，不保存文本、公告编号、名称、URL、金额或响应体。

公告在严格下一本地交易日才生效，最长保持三自然日；同一股票有新公告时只使用最新已生效事件，没有事件保持缺失。分页必须逐页对账广告数与接收数；单分区超过 80 页时先按日期递归二分，单日仍超限则终止。任一缺键、畸形日期、同一公告映射多个支持股票、重复股票/日期/公告编号、分页元数据变化或计数不一致均为致命错误。这个公共来源不读取 `TUSHARE_TOKEN`、账号、积分、Cookie、代理、零售客户端会话、价格或收益。

6 项专项离线测试通过后，唯一真实验收按冻结顺序从 `2019Q1` 开始。`2019-01-01` 至 `2019-01-31` 的首个叶分区完整请求 57/57 页并对账 5,632/5,632 行；规范化阶段随后发现至少一则公告同时映射到两个或以上受支持的主板/创业板代码，违反“每条公告恰好一个支持发行人”的预注册身份规则。程序没有任选其中一个代码、没有把同一公告复制给多个代码，也没有继续请求 `2019Q1` 后续月份或 2024/2025 样本。

本机失败清单为 `data/metadata/rich_data/runs/20260721T072630Z_eastmoney_government_subsidy_disclosure_intensity_acceptance_0ab4f00d.json`（SHA‑256 `609307dae1c633402c187d931d53c540b62e687882c8d9d33eec3ce9098f8c92`）；跨克隆终止记录为 [`a_share_eastmoney_government_subsidy_disclosure_intensity_source_acceptance_record.json`](a_share_eastmoney_government_subsidy_disclosure_intensity_source_acceptance_record.json)（SHA‑256 `431f02f0e9c4609ee12b764e593fa40904daf2ebe9262cd90461ad4c39f98cfd`）。规范行和因子值均为 0，`files=[]`，隐藏临时快照已删除；标题、公告编号、代码数组、栏目、响应体、公告正文、金额、价格和收益均未持久化，价格与未来收益也未读取。

`acceptance-eastmoney-government-subsidy-disclosure-intensity` 已永久消费，入口现在必须先验证跟踪记录并在合同、本地上下文、清单扫描或供应商访问前拒绝。不得重请求失败分区或公告来查明细、选择一个代码、把公告复制到多个代码、改变身份/标题/排除词/公式/方向/时点/三日年龄/样本/阈值、创建同机制 v2 或更换供应商救援；也不得继续全历史、容量、唯一性、收益、聚合、当前评分、选股、仓位、订单或 Level‑2。该结果是来源身份合同失败，不是因子收益为正或为负的证据；下一步只能回到新的经济独立机制并在任何新来源行或因子值前重新冻结。

### Eastmoney 重大合同公告强度（来源签订日结构门终止）

政府补助公告分支在来源身份门终止后，新一轮无收益机制核重冻结为 [`a_share_three_day_major_contract_disclosure_intensity_mechanism_overlap_reaudit_20260721.json`](a_share_three_day_major_contract_disclosure_intensity_mechanism_overlap_reaudit_20260721.json)（SHA‑256 `5299adf4f15d70ff0f3cc82eb153c67fd90afea0d766e40b6da6e7d57298efe5`）。金额/上年营收版本因历史分母稀疏、当前营收可能包含后续修订且会引入币种与尺度风险而在读取来源行前拒绝；当前唯一候选只刻画商业需求或订单确认事件：

```text
eastmoney_major_contract_disclosure_intensity
  = latest already-effective major_contract_disclosure_count
    / (1 + calendar days since announcement date)
```

数据合同 [`a_share_eastmoney_major_contract_disclosure_intensity_data_contract.json`](a_share_eastmoney_major_contract_disclosure_intensity_data_contract.json)（SHA‑256 `12d2f985f87bbdd47ff9c113b53a47d5325a4ca6a0cc70d7897e05757bd23f6b`）在任何重大合同来源行、合同身份、因子值、价格或收益出现前冻结。公共 Eastmoney `RPTA_WEB_ZDHT_LIST` 请求仅允许传输 `SECURITYCODE,DIM_RDATE,CONTRACTNAME,SIGNDATE`；合同名称和签订日只在内存中组成唯一身份，发布前必须丢弃。规范帧只能保存公告日、股票、同日唯一合同数和供应商四列，禁止金额、营收、占比、对手方、关系、合同文本、名称、身份哈希、价格和收益落盘。

公告在严格下一本地交易日才生效，最长保持三自然日；新公告生效后替代旧公告，没有事件保持缺失。分页固定每页 500 行并完整对账 `pages/count/data`；一个叶分区超过 40 页时必须在请求后续页前按日期递归二分，单日仍超限即终止。任何缺键、畸形代码/日期、签订日晚于公告日、重复完整身份、分页元数据变化或计数不一致都是致命错误。本来源使用公共静态查询参数，不读取 `TUSHARE_TOKEN`、账号、积分、Cookie、代理或零售客户端会话。

6 项重大合同专项离线测试通过后，唯一真实验收按冻结顺序从 `2019Q1` 开始。`2019-01-01` 至 `2019-01-31` 的首个叶分区用 1 次公共请求完整对账 1/1 页、86/86 行；规范化随后发现至少一条来源记录的 `SIGNDATE` 不是字符串，违反“每条签订日必须是完整严格 ISO 类标量字符串且不得晚于公告日”的预注册身份规则。程序没有删除、填充、强制转换、推断或替换该值，也没有继续请求 `2019Q1` 后续月份或 2024/2025 样本。

本机失败清单为 `data/metadata/rich_data/runs/20260721T075033Z_eastmoney_major_contract_disclosure_intensity_acceptance_d92dbd6a.json`（SHA‑256 `b94979620fb1b2af2d534b6313d39535f4126bd509e7054721836bcc576be52d`）；跨克隆终止记录为 [`a_share_eastmoney_major_contract_disclosure_intensity_source_acceptance_record.json`](a_share_eastmoney_major_contract_disclosure_intensity_source_acceptance_record.json)（SHA‑256 `4c89537c713fc1ad0c0769edb73e227669d99c92461d77de9c374f14973e8316`）。规范行和因子值均为 0，`files=[]`，隐藏临时快照已删除；没有重大合同 Parquet 或原始响应目录。合同名称、签订日及其哈希、金额、营收、比率、对手方、关系、文本、价格和收益均未持久化，价格与未来收益也未读取。运行结束后保留的锁文件只是未被进程持有的 PID 标记，不得为“清理”而删除。

`acceptance-eastmoney-major-contract-disclosure-intensity` 已永久消费；7 项专项测试确认入口现在先验证跟踪记录并在本地清单扫描、合同、本地上下文或供应商访问前拒绝。不得重请求失败分区或记录来查看值、删除/填补/转换非字符串签订日、改变字段/身份/公式/方向/时点/三日年龄/样本/阈值、创建同机制 v2 或更换供应商救援；也不得继续全历史、容量、唯一性、收益、聚合、当前评分、选股、仓位、订单或 Level‑2。该结果是来源签订日结构合同失败，不是因子收益为正或为负的证据；下一步只能回到新的经济独立机制并在任何新来源行或因子值前重新冻结。

### CNInfo 股权激励计划草案披露强度（来源验收通过、全历史标题结构门终止）

重大合同分支终止后，新机制核重记录冻结为 [`a_share_three_day_cninfo_equity_incentive_plan_disclosure_intensity_mechanism_overlap_reaudit_20260721.json`](a_share_three_day_cninfo_equity_incentive_plan_disclosure_intensity_mechanism_overlap_reaudit_20260721.json)（SHA‑256 `69450addda402d3a5bef80de41f94a4d817e41de7f89c61719cfa99f90a950bf`）。该候选刻画新披露的管理层/员工薪酬对齐方案，经济机制不同于高管二级市场交易、管理层离任、股东持仓/质押、财务报表、商业合同、价格、资金流和分析师关注度：

```text
cninfo_equity_incentive_plan_disclosure_intensity
  = latest already-effective initial_equity_incentive_plan_disclosure_count
    / (1 + calendar days since announcement date)
```

数据合同 [`a_share_cninfo_equity_incentive_plan_disclosure_intensity_data_contract.json`](a_share_cninfo_equity_incentive_plan_disclosure_intensity_data_contract.json)（SHA‑256 `2c63471a7bc76c24d5fef8171bbac9d28d1e4bcc50c11059eb648b902aaad110`）在任何 CNInfo 来源记录、标题、身份、因子值、价格或收益出现前冻结。来源固定为 CNInfo 公告检索公共 `hisAnnouncement/query` 的 `category_gqjl_szsh` 分类，POST 表单分页每页 30 条；只允许传输 `secCode,announcementTime,announcementId,announcementTitle`。公告 ID 与标题只在内存中用于严格身份和分类，发布帧只能保留公告日、股票、同日初始计划草案数和 `cninfo` 来源四列。

标题规则在来源访问前经过一次显式纠正：初始假设错误地要求所有标题都包含“股权激励计划”；常见标准名称还包括“限制性股票激励计划”和“股票期权激励计划”。最终冻结规则为标题必须包含“草案”，并至少包含“限制性股票激励计划 / 股票期权激励计划 / 股权激励计划”之一，同时排除摘要、修订、修正、更正、补充、调整、终止、取消和撤回。该纠正没有读取任何供应商标题、行、因子值、价格或收益；真实来源访问后不得再增删字面量。

每条记录的代码、Unix 毫秒公告时间、公告 ID 和标题都必须完整且类型正确；时间先按 UTC 解释再转 Asia/Shanghai 公告日。支持的主板/创业板之外完整代码只计数并排除；同一股票/公告日/公告 ID 重复、日期越界、标题含角括号标记或分页广告数变化都会终止。公告严格在下一本地交易日生效，最多保留三自然日，新事件覆盖旧事件，缺失永不填零。一个叶分区超过 80 页时只能在读取第一页后先按日期二分；任一失败都原子删除临时快照并冻结该精确机制。

6 项专项离线测试覆盖合同指纹、三类标题、严格身份/隐私、31 行两页 POST 表单、超限二分、下一交易日物化和原子发布；完整采集测试为 212/212。唯一真实验收随后完整请求 2019Q1、2024Q1、2025Q1 九个月：270 个广告页面全部按顺序完成，7,904/7,904 条来源记录对账；其中一次页面请求触发冻结合同允许的瞬时重试，因此供应商调用合计 271 次，没有递归二分。

标题和身份规范后，2019Q1、2024Q1、2025Q1 分别保留 78、108、80 个点时持有事件，共 266 行；满足至少 6 名且至少 2 个值的候选横截面分别为 7、12、5，共 24 个，严格下一交易日/三自然日物化得到 9 个不同因子值。独立复核再次重算了每个窗口事件数、候选横截面、公式、唯一键、四列模式和文件哈希。标题、公告 ID/哈希、响应体、正文、人员身份、授予数量/价格、业绩目标、Token、价格和收益均未持久化或读取。

本机验收清单为 `data/metadata/rich_data/runs/20260721T081359Z_cninfo_equity_incentive_plan_disclosure_intensity_acceptance_c83698b8.json`（SHA‑256 `021c37e542565b075b2440f575b4dd0cc9f7758abb017ee6712da2e0c42c134f`）；跨克隆跟踪记录为 [`a_share_cninfo_equity_incentive_plan_disclosure_intensity_source_acceptance_record.json`](a_share_cninfo_equity_incentive_plan_disclosure_intensity_source_acceptance_record.json)（SHA‑256 `4332cc7b10dc90c061d4a997180e5d38192785ed9a453c842742f56c392f07d6`）。剩余锁文件是非活动进程标记，按审计规范保留。

`acceptance-cninfo-equity-incentive-plan-disclosure-intensity` 已永久消费；入口必须先验证跟踪记录，并在本地清单扫描、合同、本地上下文或网络访问前拒绝重跑。验收通过只证明冻结的公共传输、标题分类、身份、公式和三个历史样本的横截面变化成立，不证明 2019–2025 全历史容量、与既有因子的独立性或收益。

验收后且在任何未验收月份来源行前，新的全历史无收益协议冻结为 [`a_share_cninfo_equity_incentive_plan_disclosure_intensity_no_return_preregistration.json`](a_share_cninfo_equity_incentive_plan_disclosure_intensity_no_return_preregistration.json)（SHA‑256 `8f49a2febee16e14dc0a142c6678dffbea264f4dff89df3e893d88558a0e35c4`）。它绑定机制、合同、验收记录、验收清单、266 行验收快照及全部本地上下文，固定 2019‑01 至 2025‑12 共 84 个月：九个验收月直接复用且禁止再请求，其余 75 个月按时间顺序请求；所有月份成功后才原子发布 2019–2025 七个年度四列 Parquet。任何失败都会删除完整临时根并永久终止，不能续传或重跑。

全历史离线实现新增协议指纹、复用月和七年原子发布测试，完整采集测试达到 215/215；预检确认全量记录/本地清单/并发进程均不存在后，唯一全量命令被执行一次。程序先在内存复用 2019‑01 至 2019‑03 的 78 行验收事件，三个验收月供应商调用为 0；随后请求首个未验收月 2019‑04，22/22 页、654/654 条来源记录完整对账。严格必需字段规范化发现至少一条公告标题含角括号标记，违反冻结合同“标题不得含角括号 markup”的规则，因此立即终止。

程序没有去除标签、转义、删除记录、重解释标题或重请求失败月；2019‑05 及以后月份均未请求。失败清单为 `data/metadata/rich_data/runs/20260721T082754Z_cninfo_equity_incentive_plan_disclosure_intensity_full_29dcdd5e.json`（SHA‑256 `4ed7a714fd1b890293331402caf0fe95d310498416ae5873ca2aaaffc8244233`）；跨克隆终止记录为 [`a_share_cninfo_equity_incentive_plan_disclosure_intensity_full_source_record.json`](a_share_cninfo_equity_incentive_plan_disclosure_intensity_full_source_record.json)（SHA‑256 `6ec4d753c4646a7f0fc7aa4a888645df429adb20fc07c14016ee2575f9bbe375`）。`files=[]`、年度分区为 0、隐藏临时快照已删除；标题/ID 明文或哈希、响应体、正文、人员身份、计划经济字段、比较字段、价格和收益均未持久化或读取。剩余全量锁文件是非活动 PID 标记，必须保留。

`sync-cninfo-equity-incentive-plan-disclosure-intensity --allow-large` 已永久消费；跟踪记录守卫必须在本地清单扫描、协议、合同、本地上下文或供应商访问前拒绝重跑。不得去标签后再试、重请求 2019‑04 或具体记录、跳过/删除/修复该行、改变标题/身份/字段/日期/公式/方向/三日年龄、续传剩余 74 个月、创建同机制 v2 或更换供应商。全历史未通过，所以容量和唯一性不得运行；也不得访问收益、聚合、当前评分、选股、仓位、订单或 Level‑2。该结果只证明冻结标题结构合同与当前公共历史快照不兼容，不说明因子收益好坏；后续回到新的无收益经济独立机制。

## Campaign019：分钟实体方向连续性（覆盖门终止）

Campaign019 继续直接使用冻结的 2019–2025 历史分钟样本，不等待当天日线或 16:30。概念记录 [`a_share_three_day_walkforward_campaign_019_concept_scouting.json`](a_share_three_day_walkforward_campaign_019_concept_scouting.json)（SHA‑256 `749f63c0acb05622ac8e547933d06d3311a37d9a237f166d9b9b4d2f3e0dd010`）、机制核重 [`a_share_three_day_walkforward_campaign_019_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_019_mechanism_overlap_audit.json)（SHA‑256 `29e7dc24776e458cd471414a076029dfb232fb5299f10fd333b6f9c4e7522606`）和无收益协议 [`a_share_three_day_walkforward_campaign_019_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_019_no_return_preregistration.json)（SHA‑256 `de68ec246a0b0944ef75edc2594e8909c89b9118de3cd01bdad7cc1b902f011f`）均在候选值、比较值和收益前冻结。

唯一 higher 因子 `intraday_bar_direction_continuity_238p` 先对 09:31–11:30、13:01–15:00 的 240 根分钟计算 `s_i=sign(log(close_i/open_i))`，再取两个半日内固定 238 个相邻对中同号非零对占全部非零对的比例。09:30 和午间连接排除；精确零实体保留在固定支持中，只令直接相邻对失去信息，禁止删除后跨越；全部 open/close 必须有限且为正，并预先要求至少 120 个信息对。构建只读 `datetime,symbol,provider,open,close`，不读 high、low、volume、amount、日线或 forward return。

不可变快照 manifest/data SHA‑256 为 `7c4f7268f33af3274a9057241b9bd45df3c2565729a684a07f48105cdf9474cb` / `66efe683268dbcc681591ee9918ba2948f3c4420232c4e1f4c57371d0ac24ecc`。33,015 个分区、7,724,498 行中 2,623,556 行有效；每一行都至少有一个零实体，零实体观测共 746,337,349 个，5,100,942 行不足 120 个信息对，34,816 行分母为零。无收益审计 `20260729T014807Z_campaign019_no_return_audit.json`（SHA‑256 `ccb7c4582a4944fe6c26423d07d25cefc488f3200fb70e45ec738ea8c716f10e`）在质量/上市联合基座上的中位/P05 覆盖仅 `56.290492%/39.160894%`，低于冻结的 `95%/90%`；P05 合格名称 85，潜在三日 cohort 539。

覆盖门失败后按冻结顺序停止：40 项统计比较值未读取，2019–2023 日线和未来收益未读取，开发试验为 0，2024–2025 未打开。研究记录 [`a_share_three_day_walkforward_campaign_019_research_record.json`](a_share_three_day_walkforward_campaign_019_research_record.json)（SHA‑256 `92d99a2a9d11165050686a8ec054e8e42e1e7b49ed5ef27ecab83bdbbe562d93`）和追加式状态 [`a_share_three_day_iteration_status_20260729_campaign019.json`](a_share_three_day_iteration_status_20260729_campaign019.json)（SHA‑256 `77c11172bd6952b7a0b9b2be4e6ee4bd3782152c73516816567a26ed0297d47f`）保持累计开发试验 241、当前聚合候选 0，Candidate49 两本台账不变且为空。不得降低 120 对门槛、删除零实体、桥接零值、改方向/窗口、过滤或与终止因子组合后重试；也不得为 Campaign019 读取比较值或收益。Campaign020 可以立即从新的独立概念和值前精确有限预注册开始，不需要等待新日线。

## Campaign020：季度公告新鲜度（开发门终止）

Campaign020 继续把历史样本作为主要迭代引擎，不等待当天新日线或 16:30。概念记录 [`a_share_three_day_walkforward_campaign_020_concept_scouting.json`](a_share_three_day_walkforward_campaign_020_concept_scouting.json)（SHA‑256 `e1f6db2ef25d05bd4a2503091004ee812f1783d7c2618940b2f640ce95a1b94f`）、机制核重 [`a_share_three_day_walkforward_campaign_020_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_020_mechanism_overlap_audit.json)（SHA‑256 `e61185b024e9d2a1a0f7d34769819c1c7a274d30f8f8ce235727daa626e606ad`）和无收益协议 [`a_share_three_day_walkforward_campaign_020_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_020_no_return_preregistration.json)（SHA‑256 `cbd04a23d73c1535886a063cdf26bacc4d86b2ebec16bc0e8724efc82b4bc1e6`）在因子值、比较值和收益前冻结。唯一 higher 因子 `quarterly_announcement_freshness_60s = 2 ** (-age_sessions / 60)`；`age_sessions` 是最新季度公告严格在公告日之后第一个已接受交易会话生效后，到信号会话的非负交易会话距离。60 会话衰减尺度没有搜索。

特征构建只从股票日网格读取 `datetime,symbol,provider`，从季度源读取 `instrument,report_date,announcement_date`；季度数值、分钟 OHLCV/amount、日线价格和 forward return 均未用于构建。不可变快照 manifest/data SHA‑256 为 `a776c1bcfb3d573ea7583be843ee42b1b6a368ccc8d80dbd382bf56fa2115fdd` / `39cda0c04c87c94886ac9f0f99453a2db627fa5cd64096ba33ef92df91223faa`。33,015 个分区、7,724,498 行中 7,233,196 行有效；491,302 行在当时没有更早的有效公告，负年龄和范围/非有限错误均为 0。

无收益审计 `20260729T032544Z_campaign020_no_return_audit.json`（SHA‑256 `08752d1a28411d52fe59d574951065ba14b0eb729620c6c8a75b63efceb72794`）先通过覆盖/容量：中位/P05 覆盖 `99.945175%/99.568865%`，P05 合格名称 138，可形成 540 个非重叠三日 cohort。随后 41 项统计比较全部通过；最大绝对中位日秩相关仅 `0.084882`，对象为已终止的 `intraday_adjacent_range_overlap_continuity_238p`，与 Campaign019 的相关为 `-0.001047`。因此精确冻结单因子、权重 1.0 的唯一一个开发试验，并只打开 2019–2023 三个扩展走前验证折；2024–2025 保持关闭。

开发中三折平均 Rank IC 有 2 折为正，但归一化执行收益只有 1 折为正，10bp 纸面试点收益 0 折为正。2019–2023 聚合平均 Rank IC 为 `-0.000836`，10bp/20bp 纸面试点累计收益分别为 `-9.143608%/-19.074213%`；三折 10bp 收益分别为 `-1.689219%/-2.076404%/-2.963635%`。该试验操作门通过，但未通过冻结的跨折质量、试点收益、回撤和 20bp 总体收益门，survivor 为 0；`2024–2025` 压力收益未读取。

研究记录 [`a_share_three_day_walkforward_campaign_020_research_record.json`](a_share_three_day_walkforward_campaign_020_research_record.json)（SHA‑256 `08fed585bff19fe7850ba24cd953a8fe61720d45d2980b68695a1c8a2ced30d9`）和追加式状态 [`a_share_three_day_iteration_status_20260729_campaign020.json`](a_share_three_day_iteration_status_20260729_campaign020.json)（SHA‑256 `0efac48bd62d5cc54ae1c88164224ceb2099bb4754e8073415df44e2593c9c2a`）把累计开发试验推进到 242，当前聚合候选仍为 0。Candidate49 仍是唯一前瞻候选，两本真实台账保持为空；不得回填 Candidate49 或启动 Candidate50。不得反向、改变 60 会话尺度、重定时、挑年份/成本、增加阈值或过滤、使用季度数值、与终止因子组合或以其他方式修补 Campaign020。Campaign021 可以立即从真正独立的新机制和值前精确有限预注册开始，仍只用 2019–2023 开发；只有冻结开发 survivor 才能一次性打开 2024–2025。

## Campaign021：分钟市场响应延迟非对称（开发门终止）

Campaign021 继续直接使用冻结历史样本，不等待当天新日线或 16:30。概念记录 [`a_share_three_day_walkforward_campaign_021_concept_scouting.json`](a_share_three_day_walkforward_campaign_021_concept_scouting.json)（SHA‑256 `d5f7ea17f6f9ff6e0a4ce7e682d9e048dcb32c7ae7c9e25df3bf0dc2eeb82f54`）、机制核重 [`a_share_three_day_walkforward_campaign_021_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_021_mechanism_overlap_audit.json)（SHA‑256 `056988a36deb220a221fe46bde5e9554628cd078f258684869ca9dc30c262ad7`）和无收益协议 [`a_share_three_day_walkforward_campaign_021_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_021_no_return_preregistration.json)（SHA‑256 `6daee3570af9fa29ca29bb0e3b642b525d9822c8f94b99e3b1e36e20e37e43b7`）均在分钟分区、市场基准值、候选值、比较值和收益前冻结。

唯一 higher 因子 `intraday_market_response_delay_asymmetry_236p` 等于 `Corr(r_i,t, m_-i,t-1) - Corr(r_i,t-1, m_-i,t)`。股票和剔除自身后的等权市场序列都使用 09:31–11:30、13:01–15:00 的 238 个半日内相邻分钟对数收益；每半日形成 118 个相邻收益对，合计固定 236 对，午间连接严格排除。两项都用等权 population Pearson correlation；任一 close 无效、任一收益非有限、任一位置不足 50 个 leave-one-out peers、任一相关向量方差为零或结果越出 `[-2,2]` 都令该 stock-day 缺失。禁止改 lag、选择子窗口、加入市场净收益、beta/residual、多个 lag 或其他终止因子。

特征快照 manifest/data SHA‑256 为 `05b1d511d9c53c1167ee97015c762b0882ab21469258fd9562eab7b28e8a24f2` / `1557eb872713ee5456fdfd0caef1d6aae6b2e9d43951afd5ca7f7b93766429a2`。33,015 个分区、7,724,498 行中 7,692,709 行有效；31,789 行因相关向量退化而缺失，peer 不足、无效 stock/market return、范围或非有限错误均为 0。构建只读分钟 `datetime,symbol,provider,close` 和已经冻结的市场 `trade_date,return_position,return_sum,valid_stock_count`，不读 open/high/low/volume/amount、日线或 forward return。

无收益审计 `20260729T050900Z_campaign021_no_return_audit.json`（SHA‑256 `b198a2deec6d31634adb4ac00b10f8c22a18cd70739f8ce10c2dd2cd70068623`）先通过覆盖/容量：中位/P05 覆盖 `99.819413%/99.287391%`，P05 合格名称 138，可形成 540 个非重叠三日 cohort。随后 42 项统计比较全部通过；最大绝对中位日秩相关 `0.198815`，对象为 Campaign019 的 `intraday_bar_direction_continuity_238p`；与 contemporaneous market-idiosyncratic-share、late market-neutral residual drift、Campaign020 公告新鲜度的中位日秩相关分别为 `0.129121/-0.002673/0.002958`。因此只冻结权重 1.0 的唯一开发试验，并打开 2019–2023 三个 expanding validation 折；2024–2025 保持关闭。

三折 validation Rank IC 为 `+0.008200/-0.001245/-0.006203`，只有 1/3 为正；归一化执行收益为 `-2.109579%/-4.990826%/-17.245224%`，10bp 纸面试点收益为 `-1.291059%/-2.185715%/-3.443258%`，两类均为 0/3 正。2019–2023 聚合平均 Rank IC 为 `-0.008946`；虽然零滑点试点为 `+7.467336%`，5bp 降到 `+3.561997%`，但冻结的 10bp/20bp 分别为 `-1.494883%/-9.743846%`，最差 validation normalized drawdown 为 `-32.969502%`。操作门通过，但跨折 IC、一致收益、回撤和 20bp 总体门均失败，survivor 为 0；2024–2025 压力收益未读取。

研究记录 [`a_share_three_day_walkforward_campaign_021_research_record.json`](a_share_three_day_walkforward_campaign_021_research_record.json)（SHA‑256 `09f1ae1a331e346196a6cfb4ad91f2ee9627d8c4fc00f979106d45ed13c2f937`）和追加式状态 [`a_share_three_day_iteration_status_20260729_campaign021.json`](a_share_three_day_iteration_status_20260729_campaign021.json)（SHA‑256 `794688a8081252665ce8be06948a380cf477052c1721259525b0b1e10b8ce2a3`）把累计开发试验推进到 243，当前聚合候选仍为 0。Candidate49 仍是唯一前瞻候选，两本真实台账保持为空。不得反向、改变 lag/peer 门槛/相关估计器、重定时、挑年份/成本、增加阈值或过滤、与终止因子组合或以其他方式修补 Campaign021。Campaign022 可以立即从真正独立的新机制和值前精确有限预注册开始；仍只用 2019–2023 开发，只有冻结开发 survivor 才能一次性打开 2024–2025。

## Campaign022：分钟线内收盘位置压力（开发门终止）

Campaign022 继续把已有历史样本和冻结的训练/验证划分作为主要迭代引擎，不需要等待当天新日线或 16:30。概念记录 [`a_share_three_day_walkforward_campaign_022_concept_scouting.json`](a_share_three_day_walkforward_campaign_022_concept_scouting.json)（SHA‑256 `e8708e06040c97691e93b9ad795229abb7a43f0d818932a650ac9b1f80dd2061`）、机制核重 [`a_share_three_day_walkforward_campaign_022_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_022_mechanism_overlap_audit.json)（SHA‑256 `6db5024304c4142cdbb3f04529af5c21719fd16684d9c99c7befa0e5152dadd5`）和无收益协议 [`a_share_three_day_walkforward_campaign_022_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_022_no_return_preregistration.json)（SHA‑256 `82a8a7038155c0ac40dcad5275b0a987ca7f938cf51cbbc28c050a737d468d8b`）均在 Campaign022 分区、候选值、比较值和收益前冻结。

唯一 higher 因子 `intraday_intrabar_close_location_pressure_240m` 在 09:31–11:30、13:01–15:00 的 240 根完整分钟线上计算：

```text
(sum(log(close/low)) - sum(log(high/close))) / sum(log(high/low))
```

它只读 `datetime,symbol,provider,high,low,close`；open、volume、amount、市场基准、日线和 forward return 在构建时均禁止。每根 high/low/close 必须有限、为正且满足 `low<=close<=high`。零振幅分钟保留在固定支持中并贡献零；预先冻结至少 120 根正振幅分钟和正的全日总对数振幅，聚合是全日距离之和的比率而不是逐分钟比率的平均。不得修改正振幅门槛、删除零振幅分钟、改成 open/VWAP/成交量权重或选择子窗口。

特征快照 manifest/data SHA‑256 为 `987fae851b1b003ba5c171746a964f99d969bf660e99b6038feebb7deda3883c` / `d3dd2cba290b662116c466d67543393c7cec4ef398bc0a6f010acbef05934e61`。33,015 个分区、7,724,498 行中 6,924,627 行有效；799,871 行不足 120 根正振幅分钟，24,584 行全日总振幅非正，非正价格、high/low/close 错序、非有限分量和范围越界均为 0。无收益审计 `20260729T065914Z_campaign022_no_return_audit.json`（SHA‑256 `cc84e8e22bae5393889853503f61f61ba5d2735ccb4c752613601490629e097b`）先通过覆盖/容量：中位/P05 覆盖 `97.494964%/90.957541%`，P05 合格名称 136，可形成 540 个非重叠三日 cohort；P05 仅略高于冻结的 90% 门，异常市场日的缺失风险必须保留为限制。

覆盖通过后才加载 43 项统计比较，全部通过。最大绝对中位日秩相关为 `0.617621`，对象是 Campaign015 的 `intraday_prior_range_breakout_pressure_238p`；与交易 VWAP 收盘压力为 `0.569143`，与 Candidate49 为 `-0.000872`，与 Campaign021 为 `-0.004040`，均低于冻结的 `0.8`。随后 [`a_share_three_day_walkforward_campaign_022_preregistration.json`](a_share_three_day_walkforward_campaign_022_preregistration.json)（SHA‑256 `a9782c89573d655cfd5872cec88cc2a28ff5706750e82f84ccca2d44ea2daf5f`）在日线和三日收益前只冻结单因子、权重 1.0 的唯一一个开发试验；2019–2023 使用三组 expanding train/next-year validation 和 3 会话 purge，2024–2025 保持关闭。

三折 validation Rank IC 为 `-0.003803/-0.008713/+0.011015`，只有 1/3 为正；归一化执行收益为 `+11.519698%/-8.574983%/-5.183193%`，同样只有 1/3 为正；10bp 纸面试点收益为 `-1.359323%/-1.722055%/-2.290215%`，0/3 为正。2019–2023 聚合平均 Rank IC 为 `-0.001601`；零成本/5bp 纸面试点为 `+6.371071%/+0.292537%`，但冻结的 10bp/20bp 降到 `-4.063015%/-12.833459%`。操作门通过，但跨折 IC、一致收益、10bp 和 20bp 成本门失败，survivor 为 0；2024–2025 压力收益没有读取。

研究记录 [`a_share_three_day_walkforward_campaign_022_research_record.json`](a_share_three_day_walkforward_campaign_022_research_record.json)（SHA‑256 `8f5cc7f0cde494a824d100debd55504222fa70d882c01ecc411df89053a4ff78`）和追加式状态 [`a_share_three_day_iteration_status_20260729_campaign022.json`](a_share_three_day_iteration_status_20260729_campaign022.json)（SHA‑256 `fb41c096c16a4c6f50a81fc4daa2b0a73bc3ecf18b80fbddd2ed1f21ffa366f8`）把累计开发试验推进到 244，当前聚合候选仍为 0。Candidate49 仍是唯一前瞻候选，两本真实台账保持为空。不得反向、降低正振幅门槛、重定时、挑年份/成本、增加阈值或过滤、与终止因子组合或以其他方式修补 Campaign022。Campaign023 可以立即从新的独立机制和值前精确有限预注册开始；仍只用 2019–2023 开发，只有冻结开发 survivor 才能一次性打开 2024–2025。

## Campaign023：分钟高低价边界平移一致性（开发门终止）

Campaign023 同样直接使用冻结历史样本和固定训练/验证划分，不等待当天新日线或 16:30。概念记录 [`a_share_three_day_walkforward_campaign_023_concept_scouting.json`](a_share_three_day_walkforward_campaign_023_concept_scouting.json)（SHA‑256 `4b56205deddacf2121a4a5591c9ff0369d40422d097f491cab43a1b520e268c5`）、机制核重 [`a_share_three_day_walkforward_campaign_023_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_023_mechanism_overlap_audit.json)（SHA‑256 `0a686cacdcce6e281e1b3c7100a5230f61308f09a9acb692859c44d24fad30c7`）和无收益协议 [`a_share_three_day_walkforward_campaign_023_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_023_no_return_preregistration.json)（SHA‑256 `bf796a2b251fcd8ff717180c59d74da4e664dca85fbdb96d9d565fc801bcf61b`）均在 Campaign023 分区、候选值、比较值和收益前冻结。

唯一 higher 因子 `intraday_range_boundary_translation_coherence_238p` 是 238 个半日内相邻转换上的 population Pearson correlation：

```text
Corr(delta(log(high)), delta(log(low)))
```

它只读 09:31–11:30、13:01–15:00 的 `datetime,symbol,provider,high,low`。09:30、午间连接、overnight、open、close、volume、amount、市场基准、日线和 forward return 均不进入构建。全部 240 根 high/low 必须有限、为正且 `low<=high`；零振幅、零边界变化、同向和反向变化均保留在固定支持中。两个 238 元变化向量都必须有正的总体方差；禁止改成回归、秩相关、符号一致率、阈值、额外 lag 或子窗口。

特征快照 manifest/data SHA‑256 为 `64732b36c84cf95024e615569bd5626f5951282e24a2ea534ea3f09c03fc41c8` / `443aa07644a31721eda4a3791ea24f3726049319aaabd917cb0ad00e5551d0b7`。33,015 个分区、7,724,498 行中 7,692,348 行有效；高价/低价变化方差非正分别为 30,608/25,889 行，价格错序、非正、变化非有限和范围越界均为 0。无收益审计 `20260729T084202Z_campaign023_no_return_audit.json`（SHA‑256 `d44a4a1d0147515655e11cc5456d87ff5067d2f6e15b0a78b7b4313d0a87ac08`）先通过覆盖/容量：中位/P05 覆盖 `99.823399%/99.275362%`，P05 合格名称 138，可形成 540 个非重叠三日 cohort。2020‑02‑03 单日覆盖只有 46.44%，但没有改变冻结门槛或挑掉该日。

覆盖通过后才加载 44 项统计比较，全部通过。最大绝对中位日秩相关为 `0.613569`，对象是 `intraday_intrabar_range_reversal_238p`；与 Campaign017 的 midpoint-width coupling 为 `+0.033633`，与 Campaign022 为 `+0.011763`，与 Candidate49 为 `-0.225561`，均低于冻结的 `0.8`。随后 [`a_share_three_day_walkforward_campaign_023_preregistration.json`](a_share_three_day_walkforward_campaign_023_preregistration.json)（SHA‑256 `0f78cea5e2e0814bf0e3214dbcb85078e149f2a30177bcb2e824e268635d0c6d`）只冻结单因子、权重 1.0 的唯一开发试验；2019–2023 使用三组 expanding train/next-year validation 和 3 会话 purge，2024–2025 保持关闭。

三折 validation Rank IC 为 `-0.045793/-0.035589/-0.056474`，0/3 为正；归一化执行收益为 `+46.083666%/-62.612418%/-23.512490%`，只有 1/3 为正；10bp 纸面试点收益为 `+4.707688%/-13.794912%/-5.741194%`，也只有 1/3 为正。前两折的 100 股整手可负担率为 `88.18%/87.21%`，低于冻结的 90%。2019–2023 聚合平均 Rank IC 为 `-0.031782`，归一化执行收益/最大回撤为 `-54.440454%/-77.160969%`；零成本、5bp、10bp、20bp 纸面试点分别为 `-6.138312%/-10.496352%/-15.711001%/-23.070014%`。操作门、IC、一致收益、回撤和成本门均失败，survivor 为 0；2024–2025 压力收益没有读取。

研究记录 [`a_share_three_day_walkforward_campaign_023_research_record.json`](a_share_three_day_walkforward_campaign_023_research_record.json)（SHA‑256 `37bff754329fe93f17b0458093029404fc26afcb851030b1776b832faf805b6f`）和追加式状态 [`a_share_three_day_iteration_status_20260729_campaign023.json`](a_share_three_day_iteration_status_20260729_campaign023.json)（SHA‑256 `e48028360965e0cd22e9dab736bae7beb4d1a9d94a9c8f9ba7870ff9b92830cc`）把累计开发试验推进到 245，当前聚合候选仍为 0。Candidate49 仍是唯一前瞻候选，两本真实台账保持为空。不得反向、改变边界变化/相关估计器/午间规则、挑年份或成本、增加阈值或过滤、与终止因子组合或以其他方式修补 Campaign023。Campaign024 可以立即从新的独立机制和值前精确有限预注册开始；仍只用 2019–2023 开发，只有冻结开发 survivor 才能一次性打开 2024–2025。

## Campaign024：有符号分钟实体到下一分钟振幅响应（开发门终止）

Campaign024 继续以冻结历史数据和固定训练/验证切分为主要迭代引擎，不等待新增日线或 16:30。概念记录 [`a_share_three_day_walkforward_campaign_024_concept_scouting.json`](a_share_three_day_walkforward_campaign_024_concept_scouting.json)（SHA‑256 `1cbc8436aa6036d12af9f785f4ca76177d50929c3744f250d14c3c25f50129c4`）、机制核重 [`a_share_three_day_walkforward_campaign_024_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_024_mechanism_overlap_audit.json)（SHA‑256 `ffe4485ebfe0387076f33e2a631d7a14e93ae6d8559e13a67b0b74f3b32d72b6`）和无收益协议 [`a_share_three_day_walkforward_campaign_024_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_024_no_return_preregistration.json)（SHA‑256 `70d8e8f1fc6b0b74f3f19e41bc6a148e999eb57239ed5a156d75a3315edecb02`）均在 Campaign024 分区、候选值、比较值和收益前冻结。

唯一 higher 因子 `intraday_directional_range_response_coupling_238p` 是：

```text
Corr(log(close_t/open_t), log(high_{t+1}/low_{t+1}))
```

它在 09:31–11:30 和 13:01–15:00 两个半日内分别形成 119 个一步 lead-response 对，再拼成固定 238 对并计算 population Pearson correlation。09:30、午间、overnight 和跨股票连接都排除；精确零实体与零后继振幅保留。全部 240 根 open/high/low/close 必须有限、为正且满足 `low<=open<=high`、`low<=close<=high`；两个 238 元向量都必须有正的总体方差。构建只读分钟 `datetime,symbol,provider,open,high,low,close`，不读 volume、amount、日线、forward return 或 Level‑2。

特征快照 manifest/data SHA‑256 为 `855d4f64b6c06d294ba971472e0a6a0b13a82b5cfd708be0535a04255151282b` / `b204fd6048454308fda9fc9724dfe7d0379847230c29822b71d18948a3ce2f20`。33,015 个分区、7,724,498 行中 7,695,318 行有效；实体方差和后继振幅方差非正分别为 26,088/28,375 行，无效、非正、错序、非有限和范围越界均为 0。无收益审计 `20260729T104150Z_campaign024_no_return_audit.json`（SHA‑256 `90587a0029069e1e6a339b9d406cbbd25bb689e748cb6a0d48c4cacffe043d7e`）先通过覆盖/容量：中位/P05 覆盖 `99.834231%/99.332435%`，P05 合格名称 138，可形成 540 个非重叠三日 cohort。最差的 2020‑02‑03 覆盖为 50%，2019‑04‑15 的点时合格横截面只有 4 个名称；这些尾部事实均被保留。

覆盖通过后才加载 45 项统计比较，全部通过。最大绝对中位日秩相关为 `0.450104`，对象是 `intraday_upside_semivariance_share_239m`；与 Campaign009/012/019/022/023 分别为 `+0.113630/-0.154721/+0.048638/+0.277189/+0.145544`，与 Candidate49 为 `-0.064611`，均低于冻结的 `0.8`。随后 [`a_share_three_day_walkforward_campaign_024_preregistration.json`](a_share_three_day_walkforward_campaign_024_preregistration.json)（SHA‑256 `07494e3490166325bd2cf48291eff557a4034c6ba0b32a0d27732d7d3fee13e1`）只冻结单因子、权重 1.0 的唯一开发试验；2019–2023 使用三组 expanding train/next-year validation 和 3 会话 purge，2024–2025 保持关闭。

三折 validation Rank IC 为 `-0.023223/-0.008864/-0.005427`，0/3 为正；归一化执行收益为 `+18.364593%/-28.312644%/+21.135686%`，2/3 为正；10bp 纸面试点收益为 `-0.498771%/-5.581699%/+0.746600%`，只有 1/3 为正。2019–2023 聚合平均 Rank IC 为 `-0.015261`，归一化执行收益/最大回撤为 `-10.786457%/-48.719072%`；零成本、5bp、10bp、20bp 试点分别为 `+2.577638%/-2.380478%/-6.431197%/-14.932448%`。操作门通过，但跨折 IC、spread、10bp、回撤和 20bp 总体门失败，survivor 为 0；2024–2025 压力收益没有读取。

研究记录 [`a_share_three_day_walkforward_campaign_024_research_record.json`](a_share_three_day_walkforward_campaign_024_research_record.json)（SHA‑256 `9ad0e7e37414162bce30273b145dae3956e62c7e31a971791239d3fd8c67b05f`）和追加式状态 [`a_share_three_day_iteration_status_20260729_campaign024.json`](a_share_three_day_iteration_status_20260729_campaign024.json)（SHA‑256 `c3d6a40a99f84d9de299b844b5425701ba8f00e0a16b37617fe9003d76bc2725`）把累计开发试验推进到 246，当前聚合候选仍为 0。Candidate49 仍是唯一前瞻候选，两本真实台账保持为空。不得反向、反转 lead、改成 contemporaneous body-range、协方差/回归/秩相关/符号计数、改变午间或零值规则、挑年份/成本、增加阈值或过滤、与终止因子组合或以其他方式修补 Campaign024。Campaign025 可以立即从新的独立机制和值前精确有限预注册开始；仍只用 2019–2023 开发，只有冻结开发 survivor 才能一次性打开 2024–2025。

完成后终检发现无收益协议 `/source_chain/campaign023_statistical_snapshot/sha256` 存在一处转录错误：协议声明 `64732b281052df83606604db50ce8e6c69bd07a26e2b6501cad1326b6997694f`，实际 Campaign023 manifest 为 `64732b36c84cf95024e615569bd5626f5951282e24a2ea534ea3f09c03fc41c8`。冻结协议不得事后改写；差异记录 [`a_share_three_day_walkforward_campaign_024_preregistration_binding_discrepancy_20260729.json`](a_share_three_day_walkforward_campaign_024_preregistration_binding_discrepancy_20260729.json)（SHA‑256 `e7058df6c8eb17c173284f12be1a429a594db79314a773d1750999f6a851ff28`）证明实际运行器和无收益审计使用正确 manifest/data 哈希，并逐字节/逐 frame 验证 33,015 分区、7,724,498 行，没有替换比较值或改公式；但协议自洽性仍判失败。最新追加状态 [`a_share_three_day_iteration_status_20260729_campaign024_binding_discrepancy.json`](a_share_three_day_iteration_status_20260729_campaign024_binding_discrepancy.json)（SHA‑256 `748cee197bf7bb199ab8d253c44414258ac6a320aeb7c7acce9bb65bf06708c6`）因此把 Campaign024 保守降为“含披露绑定缺陷的终止诊断”，不得用于策略晋级，也不得重跑或修补。Campaign025 仍不需新日线或 16:30，但选概念前必须先安装并通过所有已存在 path/SHA‑256 的完整验证器；任何失败都应在读候选值前停止并新开版本，绝不修改冻结协议。

该防复发门已实现为 [`a_share_three_day_preregistration_binding_validator.py`](../scripts/a_share_three_day_preregistration_binding_validator.py)（SHA‑256 `a6ab81a645fb25be2594937356e873c62737167dc88569d9b4b46bba6b7dcc4f`），递归覆盖 `path+sha256`、`path_below_data_root+sha256` 和 `manifest_path+manifest_sha256`。激活记录 [`a_share_three_day_preregistration_binding_validator_activation_20260729.json`](a_share_three_day_preregistration_binding_validator_activation_20260729.json)（SHA‑256 `ca07f930cb6e617e9f917b2afba3ebd43a0e12e86eddda7ad05006205be50913`）以 Campaign024 无收益协议作负控，稳定得到 14 项中 13 通过、1 失败和退出码 2；以其开发预注册作正控，15/15 通过。最新权威状态 [`a_share_three_day_iteration_status_20260729_campaign024_binding_validator_ready.json`](a_share_three_day_iteration_status_20260729_campaign024_binding_validator_ready.json)（SHA‑256 `626e1a9264d1b544143c1d5361ed68f103b524cb7f1f48706cbb6f06a870fd34`）允许 Campaign025 只从概念侦察开始；每个冻结边界的验证器退出码必须为 0，才能继续读取受保护值。

## Campaign025：日内极值到达顺序（开发门终止）

Campaign025 在离线历史滚动主线上完成，不等待新增日线或 16:30。冻结因子 `intraday_extreme_arrival_order_240m = (first_index(global_max(high)) - first_index(global_min(low))) / 239`，方向为高值更好；只使用 09:31–11:30 与 13:01–15:00 的 240 根有序分钟 high/low，精确并列取首次出现，全日极差为零时记缺失。概念、机制核重、无收益协议、快照/审计和开发预注册的所有 1/3/19/18 项 path/SHA‑256 绑定均先经完整验证器以退出码 0 通过，才读取下一阶段受保护值。

快照 manifest/data SHA‑256 为 `4f7b9b335f6df9c8a69ebc7d137abb92e88d5be579fd98231b80c5403bb69def` / `57871e9955670b3e8610fa249a14accf53830a41b88d0d66e05b80dc212c1056`。33,015 个分区、7,724,498 行中 7,700,153 行有效；24,345 行全日极差为零。无收益审计 `20260729T122303Z_campaign025_no_return_audit.json`（SHA‑256 `e67df10a429b902246450823ea7cb9645e88a8b027ab97965afca6029989b238`）先通过覆盖/容量：中位/P05 覆盖 `99.853694%/99.354839%`，P05 合格名称 138，可形成 540 个非重叠三日 cohort；随后 46 项唯一性比较全部通过，最大绝对中位日秩相关为 `0.760219`（对 `intraday_signed_path_efficiency_239m`），对 Campaign024/Candidate49 分别为 `0.244080/0.021373`。

开发预注册 SHA‑256 为 `5920146afef4a726fcd5e843e41e577bbd9cb0533d4386dbe8f0464d15f3b8cb`，只冻结一条高方向单因子试验。2021/2022/2023 三个验证折的平均 Rank IC 为 `-0.012502/-0.001164/+0.004046`，归一化收益为 `-0.003322/-0.457685/-0.158553`，10bp 纸面收益为 `-0.017008/-0.104219/-0.034491`。中位验证 Rank IC、spread、归一化收益和 10bp 收益分别为 `-0.001164/-0.003331/-0.158553/-0.034491`；开发期 20bp 累计收益为 `-0.279762`，最差验证归一化回撤为 `-0.463315`。前两折整手可负担率亦低于冻结 90% 门槛，因此无开发 survivor，2024–2025 压力区间没有打开或读取。

Campaign025 已终止，不得反向、改并列规则或分钟窗口、挑年份/成本、增加阈值/过滤、修补或与终止因子组合。累计历史开发试验为 247，当前聚合候选仍为 0。Candidate49 仍是唯一前瞻候选，禁止历史收益/信号/执行回填，两本前瞻台账保持为空；2026‑07‑29 同日计划使用新 staging root `/Volumes/DIsk/qlib-a-share-tushare-daily-2026-07-29`，因 workflow credential 不存在而 `ready=false`、退出码 2，未执行 run、未发 provider 请求、未写入 staging。Campaign026 只可从新的独立概念和完整值前冻结开始，不需要等待新日线或 16:30。

## Campaign028：分钟绝对收益强度相邻持续性（开发门终止）

Campaign028 继续以历史滚动研究作为主要引擎，不等待新增日线或 16:30。唯一 higher 因子 `intraday_absolute_return_serial_persistence_236p` 对上午和下午各 119 个半日内相邻 log-close return 取绝对值，再将每个半日内部的 118 组 lag-one 对合并为 236 对，计算 equal-pair-weight population Pearson correlation。它只读 09:31–11:30、13:01–15:00 的 `datetime,symbol,provider,close`；精确零收益留在固定位置，09:30、午间、overnight、跨日、open/high/low/volume/amount、市场基准和 daily forward return 均排除。

概念、机制核重、无收益协议和开发预注册分别为 [`a_share_three_day_walkforward_campaign_028_concept_scouting.json`](a_share_three_day_walkforward_campaign_028_concept_scouting.json)、[`a_share_three_day_walkforward_campaign_028_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_028_mechanism_overlap_audit.json)、[`a_share_three_day_walkforward_campaign_028_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_028_no_return_preregistration.json) 和 [`a_share_three_day_walkforward_campaign_028_preregistration.json`](a_share_three_day_walkforward_campaign_028_preregistration.json)。各冻结阶段在保护值前经绑定验证器通过。特征快照 manifest/data SHA‑256 为 `b08065c1cb7dbdbf06e4285a0c686338e121d27546fce97bb92dc9251f8366d0` / `8d3a3368ed85c0215751bf86b7d491bf9ad049762a810cce2e50b1a3b4badadf`，33,015 个分区、7,724,498 行中 7,692,709 行有效。

无收益审计 `20260730T072927Z_campaign028_no_return_audit.json`（SHA‑256 `9f077d989d0456cbfaf23fbcce4d3737ac3da25380c50435cfddbc7f31fe0963`）的中位/P05 覆盖为 `99.819413%/99.287391%`，P05 合格名称 138，可形成 540 个非重叠三日 cohort。49 项唯一性比较全部通过；最大绝对中位日秩相关为 `0.684913`，对象是 `intraday_diffusive_variation_ratio_238m`，仍低于冻结的 0.8 门。

唯一 2019–2023 试验的 2021/2022/2023 validation Rank IC 为 `-0.026870/-0.038192/-0.047461`，0/3 为正；normalized return 为 `+126.247478%/-27.549380%/-51.693671%`，10bp、20 万元整手收益为 `+9.917843%/-3.410372%/-9.643662%`。2021 年表面收益不能绕过负 Rank IC 和 `89.0909%` 的整手可负担率。开发聚合平均 Rank IC 为 `-0.025077`，normalized return/maximum drawdown 为 `-43.680967%/-72.368017%`；零成本、5bp、10bp、20bp 整手收益为 `+2.362376%/-1.517330%/-5.819079%/-14.007480%`。开发 survivor 为 0，2024–2025 未打开或读取。

研究记录 [`a_share_three_day_walkforward_campaign_028_research_record.json`](a_share_three_day_walkforward_campaign_028_research_record.json)（SHA‑256 `55788cf6acd10ac1c4ee9772438d14faf8c30b1e3e28a7fc4c744730a6c75423`）将该 exact higher construction 终止。不得反向、改 absolute transform、改 lag、跨午间、换相关估计器、改方向/窗口/年份/成本、加阈值或过滤、与终止因子组合、打开其压力期、回填 Candidate49、启动 Candidate50 或形成当前评分、选股、仓位、订单。累计历史开发试验推进到 250；Candidate49 仍是唯一前瞻候选，两本台账保持为空。Campaign029 只能从新的独立概念和值前冻结开始。

## Campaign029：个股分钟波动与市场冲击幅度脱钩（20bp 成本门终止）

Campaign029 继续使用冻结历史滚动主线，不等待新增日线或 16:30。唯一 higher 因子 `intraday_market_shock_magnitude_decoupling_238m` 为 238 个同步半日内位置上的：

```text
-Corr(abs(stock_return), abs(leave_one_out_market_return))
```

个股与市场收益都只由 09:31–11:30、13:01–15:00 的 close 在各自半日内形成；每个位置从冻结市场 `return_sum/valid_stock_count` 中减去个股自身，要求至少 50 个其余有限收益。精确零幅度保留，两个完整 238 元幅度向量都必须有正的总体方差。09:30、午间、overnight、lead/lag、市场涨跌符号、open/high/low/volume/amount、日线和 forward return 均不进入构建。

概念、机制核重和无收益协议分别为 [`a_share_three_day_walkforward_campaign_029_concept_scouting.json`](a_share_three_day_walkforward_campaign_029_concept_scouting.json)、[`a_share_three_day_walkforward_campaign_029_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_029_mechanism_overlap_audit.json) 和 [`a_share_three_day_walkforward_campaign_029_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_029_no_return_preregistration.json)，SHA‑256 依次为 `92a16be11087c243f8ce613c52cf0a9d1a2cd759e035eb2e94f84b03231d66c5`、`a1085b91b0d0fb697d36befbc913cd2066900b7e94434e86c63548e329573dfa`、`6bf84e6a6b9b40338447e3ff08784a09df2a76f780cbdfb09980e93f0268baf3`。各边界均在保护值前以绑定验证器退出码 0 通过。快照 manifest/data SHA‑256 为 `6dbf652eab4b787773d235cdcb4342ee82bbfb34c42d1a161c5d071c1c9df6a9` / `e37d17aa9f915425d2cd49e869d899045a0b385ffd04d74bb1bec543772de201`；33,015 个分区、7,724,498 行中 7,695,088 行有效。

无收益审计 `20260730T091416Z_campaign029_no_return_audit.json`（SHA‑256 `6188912d099f969c1b8c6a2e5436161a9e51496b4634fa2b80ebe0e7c97260f0`）的中位/P05 覆盖为 `99.831839%/99.337089%`，P05 合格名称 138，可形成 540 个非重叠三日 cohort。50 项唯一性比较全部通过；最大绝对中位日秩相关为 `0.607057`，对象是 `intraday_market_idiosyncratic_share_238m`，低于冻结的 0.8 门。比较前仍没有读取日线或未来收益。

开发预注册 [`a_share_three_day_walkforward_campaign_029_preregistration.json`](a_share_three_day_walkforward_campaign_029_preregistration.json)（SHA‑256 `b2e3d5312d2c77fa91e004751a11cc6b4934ac4ae2d34adf0ec25fc60f7c9101`）只允许 higher、权重 1.0 的单因子试验。2021/2022/2023 validation Rank IC 为 `+0.018695/+0.007229/+0.015981`，normalized return 为 `+26.988029%/+43.481007%/+39.496349%`，10bp、20 万元整手收益为 `+1.827652%/+5.164042%/+1.789554%`；三折的 IC、归一化收益、10bp 收益、整手可负担率和回撤门都通过。

2019–2023 聚合平均 Rank IC 为 `+0.004846`，normalized return/maximum drawdown 为 `+194.456802%/-23.133637%`；零成本、5bp、10bp、20bp 整手收益为 `+21.018953%/+14.095075%/+8.675010%/-2.443479%`。冻结的 20bp 聚合收益必须严格为正，因此该唯一门失败，survivor 为 0；2024–2025 没有打开或读取。

研究记录 [`a_share_three_day_walkforward_campaign_029_research_record.json`](a_share_three_day_walkforward_campaign_029_research_record.json)（SHA‑256 `71b17b0c67cff407a36f4fb1294de9a2f0ded2b55bc10448853a97acb07a2ee2`）终止该 exact construction。不得把成本门槛事后降为 10bp，不得反转方向、改成正相关或 `1-corr`、改变市场基准/同业阈值、使用 signed return/市场符号/lead/lag/子窗口、挑年份或成本、增加过滤或阈值、修补或与终止因子组合。累计历史开发试验推进到 251；Candidate49 仍是唯一前瞻候选，禁止历史收益/信号/执行回填，两本台账保持为空。Campaign030 只能从新的独立概念和值前冻结开始。

## Campaign030：早晚市场相关性消退差（开发门终止）

Campaign030 继续使用冻结历史滚动主线，不等待新增日线或 16:30。唯一 higher 因子 `intraday_market_correlation_resolution_119p` 为：

```text
Corr(stock_return, leave_one_out_market_return)[morning 119 positions]
- Corr(stock_return, leave_one_out_market_return)[afternoon 119 positions]
```

个股收益只由 09:31–11:30、13:01–15:00 的 close 在各自半日内形成；冻结市场基准只提供 `trade_date,return_position,return_sum,valid_stock_count`，每个位置减去个股自身后要求至少 50 个其他有限收益。精确零收益留在固定支持内，个股与市场的上午/下午四个完整向量均要求正的总体方差。09:30、午间、overnight、lead/lag、open/high/low/volume/amount、日线和 forward return 均不进入特征构建。

概念、机制核重和无收益协议分别为 [`a_share_three_day_walkforward_campaign_030_concept_scouting.json`](a_share_three_day_walkforward_campaign_030_concept_scouting.json)、[`a_share_three_day_walkforward_campaign_030_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_030_mechanism_overlap_audit.json) 和 [`a_share_three_day_walkforward_campaign_030_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_030_no_return_preregistration.json)，SHA‑256 依次为 `041bde8e66800f8e76fac6578ae1f2dddfda5d084c1c5216d31bf3ac3868e424`、`e32bd7824c8bf752d632d852b617ba5fca1b8be4059beccf79d82ebf7f33d6fb`、`15a7a9c3d255d1cae56d5b8ee3e3b0b69bb78a1a85a741a3c0b364ac0ee340f0`。各边界均在保护值前以绑定验证器退出码 0 通过。快照 manifest/data SHA‑256 为 `bc34e382f427d02380b6bf7858ad364064540cf1ec9be3b91e878bfefc84ab42` / `10953d752e924d0be3692c5bd0a392cb27d7009c3e7c3358c8602215d70dc549`；33,015 个分区、7,724,498 行中 7,630,332 行有效。

无收益审计 `20260730T112347Z_campaign030_no_return_audit.json`（SHA‑256 `3cec65d23b1d7952813e67db2e9b1d7486be797925e470703c3a9b4a5cf97a3b`）的中位/P05 覆盖为 `99.358885%/98.156168%`，P05 合格名称 138，可形成 540 个非重叠三日 cohort。51 项唯一性比较全部通过；最大绝对中位日秩相关为 `0.340229`，对象是 `intraday_market_idiosyncratic_share_238m`，低于冻结的 0.8 门。比较前没有读取日线或未来收益。

开发预注册 [`a_share_three_day_walkforward_campaign_030_preregistration.json`](a_share_three_day_walkforward_campaign_030_preregistration.json)（SHA‑256 `b3e73ab138e21bed849479f10babe4de4ab5e3795cb8b2b2a6ee1af7de23bb48`）只允许 higher、权重 1.0 的单因子试验。2021/2022/2023 validation Rank IC 为 `+0.010202/-0.008997/+0.013925`，gross spread 为 `-0.156049%/-0.434394%/-0.061372%`，normalized return 为 `-12.369431%/-30.604469%/-7.894037%`，10bp、20 万元整手收益为 `-4.155055%/-6.335204%/-2.172210%`。三折的 spread、归一化收益和 10bp 收益全部为负。

2019–2023 聚合平均 Rank IC 为 `+0.004805`，normalized return/maximum drawdown 为 `-50.993208%/-68.482799%`；零成本、5bp、10bp、20bp 整手收益为 `-8.851180%/-12.617061%/-17.787345%/-24.528441%`。操作门通过，但中位 spread、正收益折数、正 10bp 折数、中位 10bp 收益、最差回撤和 20bp 聚合收益门失败，survivor 为 0；2024–2025 没有打开或读取。

研究记录 [`a_share_three_day_walkforward_campaign_030_research_record.json`](a_share_three_day_walkforward_campaign_030_research_record.json)（SHA‑256 `6bb3142809c2034445ad4f5a11cdd8326dbc890dcec4f61321c6560af6af8e0b`）终止该 exact construction。不得反转方向、交换早晚差值、改变相关估计器、市场基准、同业门槛、窗口/年份/成本，增加 signed/magnitude 条件、lead/lag、过滤或阈值，重跑、修补、救援或与终止因子组合。累计历史开发试验推进到 252；Candidate49 仍是唯一前瞻候选，禁止历史收益/信号/执行回填，两本台账保持为空。Campaign031 只能从新的独立概念和值前冻结开始，但不需要等待新日线或 16:30。

## Campaign031：个股波动与横截面离散度脱钩（成本与回撤门终止）

Campaign031 继续使用冻结历史滚动主线，不等待新增日线或 16:30。唯一 higher 因子 `intraday_market_dispersion_decoupling_238m` 为：

```text
-Corr(abs(stock_return), leave_one_out_cross_sectional_population_std)
```

个股收益只由 09:31–11:30、13:01–15:00 的 close 在各自半日内形成。横截面基准按 `trade_date,return_position` 冻结 `return_sum,return_sum_squares,valid_stock_count`；每个位置减去个股自身后用总体分母 `n` 计算方差，并要求至少 50 个其他有限收益。精确零个股收益和零横截面离散度留在固定支持内，两个完整 238 元向量都要求正总体方差。09:30、午间、overnight、open/high/low/volume/amount、lead/lag、日线和 forward return 均不进入特征构建。

概念、机制核重、无收益协议和开发预注册分别为 [`a_share_three_day_walkforward_campaign_031_concept_scouting.json`](a_share_three_day_walkforward_campaign_031_concept_scouting.json)、[`a_share_three_day_walkforward_campaign_031_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_031_mechanism_overlap_audit.json)、[`a_share_three_day_walkforward_campaign_031_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_031_no_return_preregistration.json) 和 [`a_share_three_day_walkforward_campaign_031_preregistration.json`](a_share_three_day_walkforward_campaign_031_preregistration.json)。各保护值边界均在绑定验证器退出码 0 后打开。横截面基准有 404,362 行；特征快照 manifest/data SHA‑256 为 `4df07ce452454d742521e835f2b7954fe53c597ba47ec31438cb47fd2abbd086` / `9858378a035142b36f19bf00b0b8c7847802e428f6798dc1900b2ae003bcd6b1`，33,015 个分区、7,724,498 行中 7,695,088 行有效。

无收益审计 `20260730T140740Z_campaign031_no_return_audit.json`（SHA‑256 `659c3282bd02d85f5b3da99e555ba25ec227bf6c8546e50f12bc5e8ad97e30d9`）的中位/P05 覆盖为 `99.831839%/99.337089%`，P05 合格名称 138，可形成 540 个非重叠三日 cohort。52 项唯一性比较全部通过；最大绝对中位日秩相关为 `0.690903`，对象是 `intraday_volatility_resolution_238m`，低于冻结的 0.8 门。比较前没有读取日线或未来收益。

唯一 2019–2023 试验的 2021/2022/2023 validation Rank IC 为 `+0.024805/+0.033512/+0.044496`，gross spread 为 `-1.020905%/+1.123479%/+0.917309%`，normalized return 为 `-15.461557%/+35.038548%/+13.108708%`，10bp、20 万元整手收益为 `-3.141680%/+3.027903%/-0.673251%`。三折 IC 均为正，但只有 1/3 折的 10bp 收益为正。

2019–2023 聚合平均 Rank IC 为 `+0.020420`，normalized return/maximum drawdown 为 `+36.257407%/-37.428723%`；零成本、5bp、10bp、20bp 整手收益为 `+6.513813%/-0.223049%/-4.284055%/-12.827843%`。正 10bp 折数、中位 10bp 收益、最差验证回撤和 20bp 聚合收益门失败，survivor 为 0；2024–2025 没有打开或读取。

研究记录 [`a_share_three_day_walkforward_campaign_031_research_record.json`](a_share_three_day_walkforward_campaign_031_research_record.json)（SHA‑256 `e0db3cdad2508672189d5f2599fef26b8a9fff385d13bd8ba669645f640a0aa5`）终止该 exact construction。不得反向、改总体/样本方差、改变横截面离散度、leave-one-out、同业门槛、窗口/年份/成本、增加符号条件、lead/lag、过滤或阈值、重跑、修补、救援或与终止因子组合。survivor 文件的 `complexity=2` 是继承的非决策报告字段错误；冻结 catalog 与 ledger 证明单因子实际复杂度为 1，门禁和结论不受影响，原文件不改写。累计历史开发试验推进到 253；Candidate49 仍是唯一前瞻候选，两本台账保持为空。Campaign032 只能从新的独立概念和值前冻结开始，且必须在任何保护值前修正未来 campaign 的 complexity 报告字段。

## Campaign032：季度公告及时性（无收益唯一性门终止）

Campaign032 继续使用冻结历史滚动主线，不等待新增日线或 16:30。先新增独立的报告语义帮助器：试验 `complexity` 必须由去重后的非空 `feature_set` 个数推导，`single_factor` 必须恰有一个特征。该修复在任何 Campaign032 候选值、比较值或收益前冻结；Campaign031 的不可变结果没有改写。

唯一 higher 因子 `quarterly_announcement_timeliness_days` 是信号时点最新已生效季度报告的 `-(announcement_date - report_date)` 整数自然日。公告只在公告日之后第一个已接受交易会话生效；同一股票按有效会话、报告期、公告日稳定排序保留最后一项。没有更早有效披露，或延迟为正、非整数、非有限时缺失；禁止缩放、裁剪、阈值、过滤或填充。构建只读股票日身份列与季度源的 `instrument,report_date,announcement_date`，不读季度数值、分钟价格/成交、日线或 forward return。

快照 manifest/data SHA‑256 为 `8e64ad897fe725ab4ed800b0203ddd88a6c1431e2386744e1d2b13867d848c65` / `c72008162f6655e7ce34da114641f451aa04d32df61ac4c77222f7f8ad1d787f`；33,015 个分区、7,724,498 行中 7,233,196 行有效，491,302 行没有更早的有效披露，正值/非整数延迟为 0。无收益审计 `20260730T154237Z_campaign032_no_return_audit.json`（SHA‑256 `6096b9d725f5fc1e7f98467bb334a211350bcc86edda28132439fc98f28f8af9`）先通过覆盖/容量门：中位/P05 覆盖 `99.945175%/99.568865%`，P05 合格名称 138，可形成 540 个非重叠三日 cohort。

固定的 53 项唯一性比较有 52 项通过；与既有 `quarterly_announcement_freshness_60s` 的中位日秩相关为 `-0.979325`，绝对值超过冻结上限 0.8，因此唯一性门失败，admissible factor 为 0。负相关符号不允许事后反转方向。Campaign032 没有创建开发预注册，没有读取 2019–2023 日线/收益，没有增加开发试验，也没有打开 2024–2025。

研究记录 [`a_share_three_day_walkforward_campaign_032_research_record.json`](a_share_three_day_walkforward_campaign_032_research_record.json)（SHA‑256 `eaf9691aee28ccbc5130989835a224b5071780d4b931578948e01d7a5ba385d7`）终止该 exact construction。不得把自然日改成交易会话、反向、缩放、分桶、裁剪、挑报告/年份/股票/板块/状态、增加阈值或缺失修复，也不得与 Campaign020 或其他终止因子组合。累计历史开发试验保持 253；Candidate49 仍是唯一前瞻候选，两本台账不变且为空。Campaign033 可以立即从真正独立的新机制和值前冻结开始，不需要新日线或 16:30。

## Campaign033：半日内收益频谱熵（开发质量门终止）

Campaign033 继续使用冻结历史滚动主线，不等待新增日线或 16:30。唯一 higher 因子 `intraday_return_spectral_entropy_59f` 在上午与下午各取 120 个 close、各形成 119 个半日内有符号对数收益、各自去均值并做长度 119 的非归一化 DFT。对正频率 `k=1..59`，上午和下午同频平方复模功率相加后归一化为 `p_k`，因子为 `-sum(p_k*log(p_k))/log(59)`。固定范围是 `[0,1]`；非正/非有限 close、非有限收益或功率、非正总功率均缺失。禁止 09:30、午间、隔夜、open/high/low/volume/amount、taper、padding、选频、phase、wavelet、lead/lag、子窗口、年份、阈值或过滤搜索。

特征快照 manifest/data SHA‑256 为 `bbd2b064885e90576712610a5b11426c3f3048fd10ff1d0590ea02861e423bd6` / `ef76f920ab1b88dcbec40b640de240db308e60fc9711f42bb9cffbfe002e27cf`；33,015 个分区、7,724,498 行中 7,695,088 行有效。无收益审计 `20260730T171610Z_campaign033_no_return_audit.json`（SHA‑256 `f92d564c0a8f8bd32ae0a29f3879cb7c4bee85e61f9030f6ee8b635f4f5c1b35`）先通过覆盖/容量门：中位/P05 覆盖 `99.831839%/99.337089%`，P05 合格名称 138，可形成 540 个非重叠三日 cohort。54 项唯一性比较全部通过；最大绝对中位日秩相关为 `0.245542`，对象是 `intraday_global_price_range_revisit_240m`。

开发预注册 [`a_share_three_day_walkforward_campaign_033_preregistration.json`](a_share_three_day_walkforward_campaign_033_preregistration.json)（SHA‑256 `1c15aec7e148e4d9e039654fe090e85629c85d57e8e8ca9d5844a9e067eb49b3`）只允许 higher、权重 1.0 的单因子试验，使用三组冻结扩展折、边界清除三个信号会话、t/t+1/t+3 分区内完整包含、固定 Top-3、20 万元和整手成本模拟。2021/2022/2023 validation Rank IC 为 `-0.012842/-0.010158/-0.029073`，gross spread 为 `-0.280969%/+0.157654%/-0.656946%`，normalized return 为 `-16.856120%/-27.484849%/-40.688676%`，10bp 整手收益为 `-1.291245%/-5.256160%/-7.376166%`。

2019–2023 聚合平均 Rank IC 为 `-0.010941`，normalized return/maximum drawdown 为 `-30.154727%/-73.363250%`；零成本、5bp、10bp、20bp 整手收益为 `-2.950138%/-7.269095%/-9.331777%/-17.806730%`。操作门通过，但八项冻结质量门失败，survivor 为 0；2024–2025 没有打开或读取。

研究记录 [`a_share_three_day_walkforward_campaign_033_research_record.json`](a_share_three_day_walkforward_campaign_033_research_record.json)（SHA‑256 `cf4f7d3ea7ef074cf13288001047675e60a237eeae66cb628f79a6c48e849a28`）终止该 exact construction。完整测试发现初版非决策状态前缀会被旧 48 条机制扫描器误收，追加语义修复只把它对齐为既有 campaign 的 `completed_zero_development_survivors_stress_interval_not_opened`；结果、账本和终止结论未改。不得因负 IC 反向、改变去均值/DFT/功率池化/熵归一化、窗口/年份/成本、增加频带/phase/taper/padding/lead/lag/过滤/阈值，重跑、修补、救援或与终止因子组合。预收益调度、覆盖上下文、复杂度注入、单试验压力语义和 CLI 导入修复均保留为追加记录，未改变研究参数或结果。累计历史开发试验推进到 254；Candidate49 仍是唯一前瞻候选，两本台账不变且为空。Campaign034 只能从新的独立机制和值前冻结开始，但不需要新日线或 16:30。

## Campaign035：三收益弱序熵（无收益唯一性门终止）

Campaign035 继续使用离线历史滚动主线，不等待新增日线或 16:30。唯一 higher 因子 `intraday_return_weak_order_entropy_234t` 在上午和下午各用 120 个 close 形成 119 个半日内对数收益，再各取 117 个重叠三收益元组。全部 234 个元组按精确比较三元组 `(cmp(a,b),cmp(a,c),cmp(b,c))` 分入 13 种传递弱序，因子为 `-sum(p_k*ln(p_k))/ln(13)`。精确并列保留、比较容差为 0；禁止抖动、舍弃并列、跨午间收益、去重、改元组长度、子窗口、阈值和过滤。

概念、机制核重、无收益协议和终止记录分别为 [`a_share_three_day_walkforward_campaign_035_concept_scouting.json`](a_share_three_day_walkforward_campaign_035_concept_scouting.json)、[`a_share_three_day_walkforward_campaign_035_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_035_mechanism_overlap_audit.json)、[`a_share_three_day_walkforward_campaign_035_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_035_no_return_preregistration.json) 和 [`a_share_three_day_walkforward_campaign_035_research_record.json`](a_share_three_day_walkforward_campaign_035_research_record.json)。所有保护值边界均先通过指纹绑定验证器。快照 manifest/data SHA‑256 为 `33de221a37e0a19d3c1fffba3c8f0e64c20571581a7c72296b1a593c0acc91f4` / `b557148b91a16dad9f028190723b2485f9eadd231c0aaded6b499d9dc1c68606`；33,015 个分区、7,724,498 行全部有效，精确并列三元组共 630,100,770 个。

无收益审计 `20260730T205353Z_campaign035_no_return_audit.json`（SHA‑256 `ca40ca05991c8ea3c56fe3b3d85dc782c4e2d22f69b51bd12f192c3b9f289b0a`）先通过覆盖/容量门：中位/P05 覆盖为 `99.945175%/99.568865%`，P05 合格名称 138，可形成 540 个三日 cohort。固定 56 项唯一性比较有 55 项通过；与 `intraday_price_update_share_238m` 的中位日秩相关为 `-0.883137`，绝对值超过 0.8，因此收益前终止。

Campaign035 未创建开发预注册、未读取日线或 forward return、未增加开发试验，2024–2025 未打开。不得因负相关而反向、删除比较、改状态字母表/并列规则/窗口/方向/归一化、增加阈值或过滤、修补、重跑或组合。累计历史开发试验仍为 255；Candidate49 仍是唯一前瞻候选，禁止历史回填、Candidate50 和当前交易输出。Campaign036 必须从不再重表达价格更新频率的独立机制和值前冻结开始。

## Campaign038：半日端点弦贴合度（开发质量门终止）

Campaign038 使用离线历史滚动主线，不等待新增日线或 16:30。唯一 higher 因子 `intraday_half_session_chord_adherence_240m` 在上午和下午各用 120 个 close 的首尾端点确定一条对数价格弦；分数为 `1-D/(120*V)`，其中 `D` 是两段共 240 个位置到各自弦的绝对偏离和，`V` 是两段共 238 个半日内相邻绝对对数收益和。午间跳变排除，总行程为零时缺失；禁止全日弦、拟合趋势、平方或有符号偏离、平滑、回归、子窗口、阈值、过滤和组合。

特征快照 manifest/data SHA‑256 为 `d8042490037077c68c42bbf24f5b354b2a808894ac0bad79ad0c63c43404519a` / `0791779f97992d3c9cd9ee6501a2eacb6df45d534f5c6b0359088221de951904`；33,015 个分区、7,724,498 行中 7,695,088 行有效。无收益审计 `20260731T014516Z_campaign038_no_return_audit.json`（SHA‑256 `efc9b96c4754f86f32bcb54d3ae31228bb930972aefcf11560c3b9c781bdc0de`）先通过覆盖/容量门：中位/P05 覆盖为 `99.831839%/99.337089%`，P05 合格名称 138，可形成 540 个三日 cohort。固定 59 项唯一性比较全部通过；最大绝对中位日秩相关为 `0.506321`，对象是 `intraday_global_price_range_revisit_240m`。

开发预注册只允许 higher、权重 1.0 的一个试验，三组验证折 Rank IC 为 `+0.013989/+0.029755/+0.020184`，但归一化收益为 `-6.254077%/-33.266306%/-25.046695%`，10bp 整手收益为 `-2.639380%/-6.622402%/-5.809039%`。2019–2023 聚合 0/5/10/20bp 整手收益为 `-9.462748%/-13.966825%/-17.888889%/-25.726446%`；最差验证归一化回撤为 `-35.132852%`。操作门通过，收益一致性、回撤和 20bp 压力成本质量门失败，survivor 为 0；2024–2025 未打开或读取。

Campaign038 exact construction 终止。不得降低收益/回撤门、反向、改弦或归一化、跨午间、重跑、修补、救援、组合或生成当前评分/选股/仓位/订单。累计历史开发试验为 258；Candidate49 仍是唯一前瞻候选且禁止历史回填。Campaign039 只能从独立机制和值前冻结开始，不需要新日线或 16:30。

## Campaign039：日内收益时间反演非对称（开发质量门终止）

Campaign039 继续使用离线历史滚动主线，不等待新增日线或 16:30。唯一 higher 因子 `intraday_return_time_reversal_asymmetry_236p` 在上午和下午各由 120 个 close 形成 119 个相邻对数收益和 118 个有序相邻收益对；两段共 236 对先汇总 `T=sum(a^2*b-a*b^2)` 与 `Q=sum(abs(a*b)*(abs(a)+abs(b)))`，再返回 `abs(T)/Q`。精确零收益保留，`Q=0` 时缺失，绝对值只在两段合并后取一次；禁止跨午间配对、去均值、标准化、逐对或分半日取绝对值、裁剪、缩放、阈值、过滤和组合。

特征快照 manifest/data SHA‑256 为 `cda070af6d700a32f5dba1c003a3a38c9921b1c75b29ac9b8a9aa4d39d169d17` / `4d61fc2b98d2a1fc3f884668b23fcc763857926ba34abb08fab4f8ae6a3a4948`；33,015 个分区、7,724,498 行中 7,692,009 行有效。无收益审计 `20260731T033003Z_campaign039_no_return_audit.json`（SHA‑256 `9afe7310fbcf3bd8f062ddbeb5dac7f65708d60a3e376b96ffa3b1d265226db2`）先通过覆盖/容量门：中位/P05 覆盖为 `99.818840%/99.287391%`，P05 合格名称 138，可形成 540 个三日 cohort。固定 60 项唯一性比较全部通过；最大绝对中位日秩相关为 `0.308938`，对象是 `intraday_return_variance_entropy_238m`，与 Campaign038 为 `-0.015115`。

开发预注册只允许 higher、权重 1.0 的一个试验。三组验证折 Rank IC 为 `+0.011945/-0.007920/-0.011286`，归一化收益为 `-1.800701%/-5.462095%/-34.421761%`，10bp 整手收益为 `-1.817215%/-1.648212%/-6.071025%`。2019–2023 聚合 0/5/10/20bp 整手收益为 `+1.311107%/-3.852654%/-7.934397%/-16.734396%`；最差验证归一化回撤为 `-44.021941%`。操作门通过，IC、spread、收益一致性、回撤和 20bp 压力成本质量门失败，survivor 为 0；2024–2025 未打开或读取。

Campaign039 exact construction 终止。不得用零成本正收益绕过成本门、反向、改三次项/归一量/绝对值位置、跨午间、改窗口/方向/成本、重跑、修补、救援、组合或生成当前评分/选股/仓位/订单。累计历史开发试验为 259；Candidate49 仍是唯一前瞻候选且禁止历史回填。Campaign040 只能从独立机制和值前冻结开始，不需要新日线或 16:30。

## Campaign040：早晚盘分钟振幅分布相似度（无收益唯一性门终止）

Campaign040 继续使用离线历史滚动主线，不等待新增日线或 16:30。唯一 higher 因子 `intraday_morning_afternoon_range_profile_similarity_120b` 在上午和下午各读取 120 个 high/low，以每分钟 `log(high/low)` 构造两条钟点振幅轮廓。两段分别归一化为概率分布 `p/q`，再返回等权 Jensen–Shannon 相似度 `1-JSD(p,q)/log(2)`。精确零振幅分钟留在固定支持中，任一半日总振幅为零时缺失；禁止 09:30、午间、open/close/volume/amount、范围熵、Pearson、总振幅比、子窗口、反向、阈值、过滤和组合。

概念筛选、机制核重、无收益协议、快照冻结和终止记录分别为 [`a_share_three_day_walkforward_campaign_040_concept_scouting.json`](a_share_three_day_walkforward_campaign_040_concept_scouting.json)、[`a_share_three_day_walkforward_campaign_040_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_040_mechanism_overlap_audit.json)、[`a_share_three_day_walkforward_campaign_040_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_040_no_return_preregistration.json)、[`a_share_three_day_walkforward_campaign_040_feature_snapshot_freeze_20260731.json`](a_share_three_day_walkforward_campaign_040_feature_snapshot_freeze_20260731.json) 和 [`a_share_three_day_walkforward_campaign_040_research_record.json`](a_share_three_day_walkforward_campaign_040_research_record.json)。所有保护值边界均先通过指纹绑定验证器。

快照 manifest/data SHA‑256 为 `9830dc3dc4f5ceb86f6983c1353bd52c3b6c87eeb206f433b10c19adc7d82f40` / `9b7443611ce0da082aa31fb88d4b001c0d7231639112e15fd9645d7ede46dee8`；33,015 个分区、7,724,498 行中 7,633,953 行有效。快照冻结前只纠正两个继承兼容布尔标签为 `high/low=true, close=false`；显式投影本来就是 high/low，分区文件、候选值和 dataset SHA‑256 均未改变，随后重新通过 33,015 个分区的字节/frame 哈希及幂等验证。

无收益审计 `20260731T051832Z_campaign040_no_return_audit.json`（SHA‑256 `4a17a68aec878c216e70aaabef3500534fcf4f9924cc92f19b61a33849311f5c`）先通过覆盖/容量门：中位/P05 覆盖为 `99.377358%/98.227732%`，P05 合格名称 138，可形成 540 个三日 cohort。覆盖通过后才加载固定的 61 项唯一性比较；顺序匹配，60 项通过。与 `intraday_intrabar_range_participation_entropy_240m` 的中位日秩相关为 `+0.884338`，绝对值超过 0.8，因此收益前终止。

Campaign040 未创建开发预注册、未读取日线或 forward return、未增加开发试验，2024–2025 未打开。不得把 similarity 改成 divergence、反向、删除失败比较、改距离/归一化/半日切分/零值语义/方向、增加阈值或过滤、修补、重跑或组合。累计历史开发试验仍为 259；Candidate49 仍是唯一前瞻候选，禁止历史回填、Candidate50 和当前交易输出。Campaign041 必须从不再重表达分钟 high-low 振幅质量分布或参与熵的独立机制和值前冻结开始。

## Campaign041：日内微 gap 吸收占比（无收益唯一性门终止）

Campaign041 继续使用离线历史滚动主线，不等待新增日线或 16:30。唯一 higher 因子 `intraday_microgap_absorption_share_238p` 在上午和下午各读取 120 个 OHLC，各形成 119 个半日内转换。`g_t=log(open_t/close_(t-1))` 精确非零时才是 informative gap；若 `low_t <= close_(t-1) <= high_t` 则计为已吸收，因子为已吸收 informative gap 数除以 informative gap 总数。至少需要 30 个 informative gap；禁止 09:30、午间转换、volume/amount、gap 权重、符号分组、阈值、过滤、反向和组合。

概念筛选、机制核重、无收益协议、最终快照冻结、无收益审计冻结和终止记录分别为 [`a_share_three_day_walkforward_campaign_041_concept_scouting.json`](a_share_three_day_walkforward_campaign_041_concept_scouting.json)、[`a_share_three_day_walkforward_campaign_041_mechanism_overlap_audit.json`](a_share_three_day_walkforward_campaign_041_mechanism_overlap_audit.json)、[`a_share_three_day_walkforward_campaign_041_no_return_preregistration.json`](a_share_three_day_walkforward_campaign_041_no_return_preregistration.json)、[`a_share_three_day_walkforward_campaign_041_feature_snapshot_freeze.json`](a_share_three_day_walkforward_campaign_041_feature_snapshot_freeze.json)、[`a_share_three_day_walkforward_campaign_041_no_return_audit_freeze_20260731.json`](a_share_three_day_walkforward_campaign_041_no_return_audit_freeze_20260731.json) 和 [`a_share_three_day_walkforward_campaign_041_research_record.json`](a_share_three_day_walkforward_campaign_041_research_record.json)。所有保护值边界均先通过指纹绑定验证器。

快照 manifest/data SHA‑256 为 `838f71169e90d33e9ebbfd34d62dd2c4969432454eeaa69ae6601bb6fdc95391` / `d330e806262d5e3187649273aea14bb20e53d13cc18edfbc8d8dd0616aa0ac0b`；33,015 个分区、7,724,498 行中 7,461,292 行有效。共检查 1,838,430,524 个固定转换，其中 783,613,890 个是 informative gap，495,091,836 个满足吸收条件；263,206 行因不足 30 个 informative gap 而缺失。非正、非有限或错序 OHLC 行均为 0。三次发布失败均作为追加式基础设施证据保留；修复只纠正继承发布器的 OHLC/volume 元数据，没有改变公式、分区字节或 dataset SHA‑256，最终 33,015 个分区的字节/frame 哈希和幂等验证全部通过。

无收益审计 `20260731T072630Z_campaign041_no_return_audit.json`（SHA‑256 `fe00c12d6cb1ebfbb0c7eb31e7f43e188f845ae41a4efff5ebbc9d7230fcf52b`）先通过覆盖/容量门：中位/P05 覆盖为 `99.403996%/92.885907%`，合格名称中位/P05 为 937/138，可形成 540 个三日 cohort。覆盖通过后才加载固定的 62 项唯一性比较；顺序匹配，60 项通过。与 `intraday_adjacent_range_overlap_continuity_238p` 和 `intraday_intrabar_range_participation_entropy_240m` 的中位日秩相关分别为 `+0.836224` 和 `+0.801723`，两项绝对值均超过 0.8，因此收益前终止。

Campaign041 未创建开发预注册、未读取日线或 forward return、未增加开发试验，2024–2025 未打开。不得把吸收改成未吸收、反向、修改 gap/最小计数/闭区间/半日重置/窗口/方向、删除失败比较、增加阈值或过滤、修补、重跑或组合。累计历史开发试验仍为 259；Candidate49 仍是唯一前瞻候选，禁止历史回填、Candidate50 和当前交易输出。Campaign042 必须从不再重表达相邻区间重叠、区间包含、吸收或范围质量集中度的独立机制和值前冻结开始。

## Campaign042：午间重定价—下午延续一致性（开发质量门终止）

Campaign042 继续使用无需等待新增日线或 16:30 的离线历史滚动主线。唯一 higher 因子 `intraday_lunch_repricing_persistence_2r` 定义 `g=log(close_13:01/close_11:30)`、`a=log(close_15:00/close_13:01)`，返回 `2*g*a/(g^2+a^2)`；单个零分量保留，二者同时为零时缺失。只读完整 240 根 close 网格；禁止改锚点、绝对值、open/high/low/volume/amount、阈值、过滤、反向和组合。

快照 manifest/data SHA‑256 为 `c56a81a461aae4ea9d1f44c238dd381541e18425837872a17f3d34f8dc796acd` / `9fe1a6095a70702ef3ce7ba6cbca8e1386749513b00e8494b37813a1639826c8`；33,015 个分区、7,724,498 行中 7,449,531 行有效。初次发布因继承 manifest 缺少 `source_amount_read=false` 在发布前失败；追加修复只补源字段元数据，恢复全部 checkpoint 且零重算，候选值和 dataset SHA‑256 未变。无收益审计通过覆盖门和全部 63 项比较；中位/P05 覆盖为 `98.039216%/96.197134%`，最大绝对中位日秩相关为 `0.041753`。

唯一冻结开发试验的 2021/2022/2023 验证 Rank IC 为 `-0.008747/-0.001419/-0.002932`，归一化收益为 `-4.183944%/-29.863464%/-13.939693%`，10bp 整手收益为 `-2.488201%/-5.341144%/-3.712165%`。2019–2023 聚合 0/5/10/20bp 整手收益为 `-2.146893%/-7.421575%/-11.867364%/-18.965983%`，最差验证归一化回撤为 `-32.235952%`。操作门通过，但八项冻结质量门全部失败，survivor 为 0；2024–2025 未打开或读取。

研究记录 [`a_share_three_day_walkforward_campaign_042_research_record.json`](a_share_three_day_walkforward_campaign_042_research_record.json)（SHA‑256 `95ed818100ce2529e6eea442702a09d0bf0ae2ffd35a0604927826f3431328fd`）终止该 exact construction。不得反向、改锚点/归一化/零值规则/窗口/成本、重跑、修补、救援或组合。累计历史开发试验推进到 260；Candidate49 仍是唯一前瞻候选，禁止历史回填和当前交易输出。下一轮必须作为独立 Campaign043 从新的经济机制和值前冻结开始。

2026‑07‑31 的 Candidate49 同日前瞻流程在 16:30 Asia/Singapore 后先以零请求 `plan` 得到 `ready=true`，随后确认运行在 `stock_basic` 源门因无效 `ts_code` 失败关闭。失败记录为 [`a_share_candidate49_20260731_daily_source_failure_record.json`](a_share_candidate49_20260731_daily_source_failure_record.json)（SHA‑256 `67effbc1bc364c8a312d5cb2003303b3cd7a48b7f805dac5a9b57b0f1185fd7f`）。不得同日重试或重请求失败响应；Candidate49 信号/执行台账均未改变。

## Campaign043：成交价 VWAP 一致度（开发质量门终止）

Campaign043 继续采用离线历史滚动主线，不等待新增日线或 16:30。唯一 higher 因子 `intraday_transaction_vwap_consensus_240m` 只读 09:31–11:30、13:01–15:00 的 `datetime,symbol,provider,volume,amount`。对 `volume>0 && amount>0` 的 active bar 定义 `p_i=amount_i/volume_i`、`w_i=volume_i/sum(volume)`，返回 `exp(sum(w_i*log(p_i)))/sum(w_i*p_i)`；联合零量零额 bar 排除，单边零使股票日缺失，至少要求 120 个 active bar，常成交价日为有效分数 1。禁止 open/high/low/close、09:30、子窗口、替代中心/权重/离散度、反向、缩放、阈值、过滤或组合。

快照 manifest/data SHA‑256 为 `7652e88cbaf7f3f21751b3c944dc21c2746580f6a4d48aebffeea410b9c89590` / `59410bf94f8c013f0be2bea166c6fa128ff2b173c0ba85e688683675270d3885`；33,015 个分区、7,724,498 行中 7,682,604 行有效。首次构建因继承发布 hook 查找失败，第二次在全部 checkpoint 完成后因继承 manifest 的 kind、协议键前缀和两个源字段布尔值不兼容而在原子发布前失败；两项追加修复只处理发布基础设施/元数据。最终恢复 33,015 个 checkpoint、零分区重算，候选值和 dataset SHA‑256 未变。

无收益审计的首次交互执行在聚合阶段因会话生命周期消失且未产生文件；失败被单独记录，完全相同冻结参数的持久重试生成唯一审计 `20260731T115937Z_campaign043_no_return_audit.json`（SHA‑256 `d7cfb302d31e8ae740497d58e460b92cef9460fb4260d7cb4cba641db31d9b06`）。覆盖中位/P05 为 `99.876847%/99.339742%`，P05 合格名称 138，可形成 540 个三日 cohort。覆盖通过后才读取固定 64 项比较；全部通过，最大绝对中位日秩相关为 `0.667503`（`intraday_realized_volatility`），低于 0.8；与 Candidate49 为 `+0.542991`，与 Campaign042 为 `-0.051883`。

唯一冻结开发试验的 2021/2022/2023 验证 Rank IC 为 `+0.038580/+0.037693/+0.048980`，归一化收益为 `-16.789567%/-52.500067%/-16.758099%`，10bp 整手收益为 `-4.104895%/-10.579855%/-3.380239%`。2019–2023 聚合 0/5/10/20bp 整手收益为 `-14.495900%/-18.027923%/-21.034206%/-29.142929%`，最差验证归一化回撤为 `-55.074679%`。操作门通过，但 spread、收益一致性、pilot、回撤和 20bp 质量门失败，survivor 为 0；2024–2025 未打开或读取。

研究记录 [`a_share_three_day_walkforward_campaign_043_research_record.json`](a_share_three_day_walkforward_campaign_043_research_record.json)（SHA‑256 `44bd70909c20106ed920f5a77b5f9d54b28d3317b19c7392314a235cdd8939ba`）终止该 exact construction。正 Rank IC 不得绕过执行收益/成本/回撤门；不得反向、改 active-bar/零值/最小支持/权重/均值定义、重跑、修补、救援或组合。累计历史开发试验推进到 261；当前聚合候选仍为 0。Candidate49 仍是唯一前瞻候选，两本台账为空，禁止历史回填、Candidate50 和当前交易输出。Campaign044 只能从真正独立的新机制和值前冻结开始，但无需等待新日线或 16:30。

## Campaign044：完整终止特征库方向百分位共识（无收益覆盖门终止）

Campaign044 继续以离线历史样本作为主要迭代引擎，不等待新增日线或 16:30。它先后记录三个组合设计：包含 Candidate49 的 65 项版本因违反历史回填边界而在值前拒绝；从后期比较列表删除 Candidate49 得到的 64 项版本因遗漏两个冻结旧定义而在值前拒绝；最终版本才冻结为 `full_terminal_library_directional_percentile_consensus_66f`。最终版本复用全部 66 个终止定义，明确不读取 Candidate49；每个信号会话要求所有成分均为有限且合格值，按各自冻结方向计算平均并列经验百分位后以 `1/66` 等权平均，至少要求 50 个共同支持名称。不得使用部分平均、插补、删减、筛选、阈值、拟合权重或模型。

首次快照构建在第一个对齐来源值返回前发现质量/上市主键超出绑定的分钟身份键，按基础设施失败记录终止。唯一修复只把主键与 Campaign043 分钟身份键求交，未改变公式、成分库、方向或门槛。最终不可变快照 manifest/data SHA‑256 为 `ab5d08bf5c9ca8737c32b13e8a6fcc68d9cfb26fc8cdb43377d34bde5d724964` / `295c023b3f6a76605ab0413f6ab9410e2dabcb4cb2d262de7a62618818a55487`；33,015 个分区、7,724,498 行均通过字节与帧哈希验证。66 项共同支持在会话最小名称门之前为 646,683 行，最终有效 646,568 行；Candidate49 因子值、日线和 forward return 均未读取。

唯一无收益审计 `20260731T191808Z_campaign044_no_return_audit.json`（SHA‑256 `5bf91fae0ab73f04680e840d8a5280250e0e3091f80fe47684d1656fbde10776`）严格先运行覆盖门。中位/P05 覆盖为 `51.717636%/34.992895%`，低于冻结的 `95%/90%`；P05 合格名称 78、潜在三日 cohort 539、覆盖 2019–2025 七年虽分别通过对应门槛，仍不能抵消横截面覆盖失败。审计因此没有重载 66 项成分相关性，没有读取 2019–2023 日线或未来收益，也没有打开 2024–2025。

终止记录为 [`a_share_three_day_walkforward_campaign_044_research_record.json`](a_share_three_day_walkforward_campaign_044_research_record.json)（SHA‑256 `3e343e8387fd16db75f7e8a5c87025e712082ea50aa9e360083af7f0d3f2b615`）。追加式台账计入两个值前设计拒绝、一次基础设施失败和一次无收益候选，共 4 次；累计历史研究尝试从 261 推进到 265，而实际读取开发收益的累计试验仍为 261。不得放宽覆盖、改成部分支持、插补、删除稀疏成分、调权、拟合、反向、重跑或组合救援。旧终止记录保持不改写；Candidate49 仍是唯一活动前瞻候选且两本台账为空。下一轮 Campaign045 可以随时从独立值前概念开始，但历史结果不得直接生成当前评分、选股、仓位、订单或投资建议。

## Campaign045：波动—活动领先滞后非对称（开发质量门终止）

Campaign045 的冻结 higher 因子 `intraday_volatility_activity_lead_lag_asymmetry_236p` 只使用两个独立 120 分钟半场的 close/amount，比较“波动先发生、活动后到达”和“活动先到达、波动后发生”的总体 Pearson 相关。无收益覆盖中位/P05 为 `99.819413%/99.287391%`，68 项比较全部通过，最大绝对中位日秩相关为 `0.111220`，因此只运行一个冻结开发试验。三个验证折 mean Rank IC 全负，只有一折 normalized return 和一折 10bp 收益为正，三折整手可负担率均低于 90%，开发期 20bp 收益为 `-11.557080%`；survivor 为 0，2024–2025 未打开。累计历史研究尝试为 267，读取开发收益的试验为 262。该 exact construction 禁止反向、修改字段/半场/滞后、过滤、调参、组合或救援。

## Campaign046：相邻收益反转能量占比（无收益唯一性门终止）

Campaign046 继续使用随时可运行的离线历史滚动主线，不等待新日线或 16:30。唯一 higher 因子 `intraday_return_reversal_energy_share_236p` 在上午和下午各用 120 个 close 形成 119 个相邻对数收益和 118 个相邻收益对；两段共 236 对，返回反向对 `abs(a*b)` 能量占全部对 `abs(a*b)` 能量的比例。精确零收益保留并贡献零权重，分母必须有限且为正；禁止 09:30、跨午间、OHLC/volume/amount、替代 lag/window/sign tolerance、反向、阈值、过滤、模型或组合。

快照 manifest/data SHA‑256 为 `4103aeee6e45cd54ffcb304283808abb67e6ea6107605f67441df70653e31ccd` / `ee089ffd7dc7111ec6a7b620830595805ce998db6ef076f9d3cd516a7784d06f`；33,015 个分区、7,724,498 行中 7,692,009 行有效并全部通过字节/frame 哈希。两次基础设施失败均追加保留：首次构建在读取外部分区前因继承查找失败；首次无收益审计在覆盖通过并完成前 68 项比较后因 Campaign045 快照误用 Campaign044 列模式而失败。两次修复仅处理继承映射和校验器分派，没有改变公式、候选值、比较顺序或门槛。

最终无收益审计 `20260801T003958Z_campaign046_no_return_audit.json`（SHA‑256 `4d7db211439f4e2c019acf8fbc0e6029450f4a31b0dc78e2c20e4edae8673425`）先通过覆盖/容量门：中位/P05 覆盖为 `99.818840%/99.287391%`，P05 合格名称 138，可形成 540 个三日 cohort。覆盖通过后固定 69 项比较顺序完全匹配；与 `intraday_five_minute_variance_ratio_230w` 的中位日秩相关为 `-0.817758`，绝对值超过冻结上限 0.8，故零准入并在日线/forward return 前终止。

终止记录为 [`a_share_three_day_walkforward_campaign_046_research_record.json`](a_share_three_day_walkforward_campaign_046_research_record.json)。Campaign046 共记录两次基础设施失败和一次无收益候选，累计历史研究尝试从 267 增至 270，累计读取开发收益的试验仍为 262。不得反向、删除失败比较、改能量权重/符号/窗口/方向、重跑、救援或组合；2024–2025 未打开，Candidate49 历史未回填且前瞻台账未改变。下一轮只能作为独立 Campaign047 从值前冻结开始，历史结果仍不得生成当前评分、选股、仓位、订单或投资建议。

## Campaign049：早晚盘成交额轮廓相似度（无收益唯一性门终止）

历史 Campaign049 与前瞻 Candidate49 严格分离。冻结 higher 因子 `intraday_morning_afternoon_amount_profile_similarity_120b` 在两个连续半场各使用 120 个 amount，独立归一化后计算等权 Jensen–Shannon 相似度；每半场至少 60 个正成交额分钟，精确零值保留，禁止价格、volume、替代距离、方向、阈值、过滤、模型和组合。

快照 manifest/data SHA‑256 为 `6c27933f232926f33d750f624fc6ad32c394c2e97922043502e997275c1ace1d` / `c60c1f245e2bbfdd12acdcfdd8417799684fcda09caf4472270d870ba911164c`，33,015 个分区和 7,724,498 行均通过字节/frame 哈希。无收益覆盖中位/P05 为 `99.811143%/99.065421%`；覆盖通过后才加载 72 项冻结比较。与 `intraday_amount_participation_entropy_240m` 的绝对中位日秩相关为 `0.871597`，超过 0.8，故不创建开发预注册、不读取日线或 forward return、不打开 2024–2025。

本轮累计历史研究尝试增至 280，累计读取开发收益的试验保持 264。Candidate49 的历史收益、信号、执行和里程碑均未回填，两本前瞻台账不变；周六没有运行供应商工作流。后续离线 Campaign050 可随时独立预注册，不必等待新日线或 16:30，但不得救援、重跑、组合 Campaign049 或生成当前评分、选股、仓位、订单和投资建议。

## Campaign050：半场极端冲击反转完成度（开发质量门终止）

Campaign050 延续离线历史滚动主线，不依赖当天日线或 16:30。唯一 higher 因子 `intraday_half_session_extreme_shock_reversal_completion_2h` 在上午、下午两个独立 120-close 半场内分别选择绝对值最大的最早一分钟冲击 `s`，以冲击结束后到同半场末的收益 `R` 计算 `-2*s*R/(s²+R²)`，再等权平均。固定禁止跨午间、替代 tie rule、字段、窗口、方向、阈值、过滤、拟合、模型和组合。

快照 manifest/data SHA‑256 为 `8e95728fd9e1ba3d3ab820dbf5d92812bd18f9076ee901ee80cd76cf989300ef` / `d758c059ff6fb602106c240c369d5d3db60eb245ec7cccf23d5a32b9f69dec8a`；33,015 个分区、7,724,498 行中 7,630,332 行有效并全部通过字节/frame 哈希。无收益覆盖中位/P05 为 `99.358885%/98.156168%`，固定 73 项比较全部通过，最大绝对中位日秩相关为 `0.149511`。

唯一冻结开发试验的 2021/2022/2023 验证 mean Rank IC 为 `+0.009970/+0.000564/-0.003655`，归一化收益为 `+23.210460%/-16.237229%/-23.423742%`，10bp 整手收益为 `+0.774438%/-4.699991%/-5.836597%`。2019–2023 聚合 0/5/10/20bp 整手收益为 `-1.577495%/-5.908229%/-10.111490%/-18.403172%`。操作门通过，但收益折一致性、spread、pilot、回撤和 20bp 质量门失败，survivor 为 0；2024–2025 未打开或读取。

追加式台账保留一次快照空联合分区失败、一次无收益校验器命名空间污染、两次开发预注册语义失败、一个完整因子尝试，以及收口阶段一次绑定校验器 CLI 参数误用，最终共 6 次独立尝试、7 条阶段记录。后者未读取价格或收益，位置参数重试后 38/38 项绑定通过。累计历史研究尝试由 280 推进到 286，累计读取开发收益的试验由 264 推进到 265。Candidate49 仍是唯一前瞻候选，两本台账为空；周六未运行供应商流程。历史研究可继续从独立 Campaign051 值前机制开始，无需等待新增日线或 16:30，但不得救援 Campaign050、打开其 2024–2025、生成当前评分/选股/仓位/订单或构成投资建议。

## Campaign051：收盘价区间占用熵（开发质量门终止）

Campaign051 继续以离线历史滚动为主要迭代引擎，不等待新增日线或 16:30。唯一 higher 因子 `intraday_close_range_occupancy_entropy_10b` 读取固定 240 根 close，将 `log(close)` 按当日完整对数价格区间归一到 `[0,1]`，落入 10 个固定等宽 bin，再用 `-sum(p*log(p))/log(10)` 计算区间占用熵。精确最大值进入第 10 桶，重复 close 保留；完整区间必须严格为正。该量是顺序不变的价格区间占用广度，禁止 open/high/low/volume/amount、改 bin、替代边界、窗口、方向、阈值、过滤、拟合、模型或组合。

不可变快照 manifest/data SHA‑256 为 `13a2b7862cb2118dd8e42bcd94653973de603d840bd09f0762be219b840f032e` / `2930b47c228f3e033f8130d9960e55668e688e02ba020a02d02ffa60987cabbd`；33,015 个分区、7,724,498 行中 7,695,092 行有效，全部通过字节/frame 哈希验证。完整无收益审计为 `20260803T073502Z_campaign051_no_return_audit.json`（SHA‑256 `e5effeea374db0e18256be69caac92e68a5a42e8b3b095db90c42fa4e65240cf`）：1,632 个会话的覆盖中位/P05 为 `99.831839%/99.337089%`，P05 合格名称为 138，可形成 540 个不重叠三会话 cohort；覆盖通过后固定 74 项比较按预注册顺序全部通过。最大绝对中位日秩相关为 `0.282850`，最近因子是 `intraday_amount_center_of_mass_240m`；与最后加入的 Campaign050 因子绝对相关仅 `0.005963`。

唯一冻结开发试验的 2021/2022/2023 验证 mean Rank IC 为 `+0.010069/+0.003607/-0.021171`，归一化收益为 `-1.748712%/-8.586244%/-12.948299%`，10bp 整手收益为 `+0.011174%/-3.683443%/-3.096231%`。2019–2023 聚合 0/5/10/20bp 整手收益为 `+2.587285%/-1.295268%/-5.713620%/-14.030842%`，最差验证归一化回撤为 `-30.626166%`。fold 1 整手可负担率仅 `88.288288%`，低于冻结 90% 门槛；三折 normalized return 全负、仅一折 10bp 收益为正，median pilot、回撤和聚合 20bp 门也失败。survivor 为 0，2024–2025 未打开或读取。

当前终止记录为 [`a_share_three_day_walkforward_campaign_051_research_record_v3.json`](a_share_three_day_walkforward_campaign_051_research_record_v3.json)（SHA‑256 `3c772a960ffb005f4227391c79a37223187c1bd51bbfec6be43e6a7ed28426d0`），权威状态为 [`a_share_three_day_iteration_status_20260803_campaign051_verified.json`](a_share_three_day_iteration_status_20260803_campaign051_verified.json)（SHA‑256 `71d63fa1f47a659e74c0b5a472762ca4be6ee07ea982626b80aad924b883612e`）；v1/v2 均保留为历史证据。追加式台账保留 7 次审计前后的基础设施失败、收口阶段 1 次 stress-intent 语义断言失败、完整测试集 1 次跨克隆绝对路径/旧模块状态失败、1 个完整因子尝试及其 1 条开发延续记录，共 10 次独立尝试、11 条记录。当前仅存 `/Volumes/DIsk/Disk-Coding/qlib` 工作树，旧台账和预注册中保存的 `/Users/niyufei/Coding/qlib` 绝对路径无法相等；完整测试集因此为 1,709 通过、69 个旧 Campaign 失败、13 warnings，而 Campaign051 专项 27/27 与当前指纹绑定全部通过。两次收口失败均未读取价格或收益。累计历史研究尝试由 286 推进到 296，累计读取开发收益的试验由 265 推进到 266。Candidate49 仍是唯一前瞻候选，历史收益、信号、执行和里程碑均未回填，两本台账不变。不得反向、改 bin/边界/窗口/方向、调参、过滤、重跑、救援、组合或打开该因子的 2024–2025；下一轮 Campaign052 只能从新的经济独立机制和值前冻结开始，但离线工作可随时运行。

## Campaign052：四季度公告延迟一致性（覆盖门终止）

Campaign052 继续执行“历史滚动为主、Candidate49 前瞻观察为独立确认层”的双轨制，不等待新增日线或 16:30。唯一 higher 因子 `quarterly_announcement_delay_consistency_4q` 只读取股票日身份字段和季度 `instrument/report_date/announcement_date`；每个股票日仅使用公告日严格早于该日的最新四个连续 Q-DEC 季末报告，令四个非负整数公告延迟的总体标准差为 `sigma`，返回 `1/(1+sigma)`。季度财务数值、分钟 OHLCV/amount、日线价格和 forward return 均禁止。

不可变快照 manifest/data SHA-256 为 `04547981bed8a78438d7988296f1b3887a7d67b6604df555b207fac0b85a26c4` / `f9a6f08060c60c2183c587d6008ffa20f76735bdef46a989f02dff6ecba1a30e`；33,015 个分区、7,724,498 行中 6,259,298 行有效，全部通过字节/frame 哈希。无收益审计 `20260803T084328Z_campaign052_no_return_audit.json`（SHA-256 `47559113a6ea3e9cf52525d5d1440f242d41d764c478ced9d7d51feedc48114c`）的中位覆盖为 `96.039422%`，但 P05 覆盖与 P05 合格名称均为 0；尽管有 469 个三会话 cohort、覆盖 2020–2025 六年，仍未达到冻结的 P05 `90%/50` 门槛。

门禁按预注册顺序在加载 75 项比较值之前停止；没有读取日线或 forward return、没有开发试验、没有打开 2024–2025。追加台账记录缺失兼容工作树、绑定验证器 CLI 误用、pytest 导入路径三次基础设施失败，以及一个完整因子尝试；累计历史尝试从 296 增至 300，累计收益试验保持 266。禁止缩短为三季度、推迟研究起点、删除早期折、放宽覆盖、插补、过滤、改方向、重跑、救援、组合或生成交易动作。Candidate49 仍是唯一前瞻候选且两本台账不变；Campaign053 可随时从独立值前机制开始。

## Candidate49：2026-08-03 日源失败关闭

2026-08-03 16:30 Asia/Singapore 后，使用全新 staging root `/Volumes/DIsk/qlib-a-share-tushare-daily-2026-08-03` 运行零请求 `plan`；结果为 `ready=true`、退出码 0、未写文件且未发供应商请求。随后完全相同参数的 `run --confirm-run` 在 `stock_basic` source gate 退出 1，供应商响应包含非法 `ts_code`，`provider_continuation_allowed=false`。

本次调用共 4 次供应商请求；活跃数据根未变，完成的会话 checkpoint 保留，凭据值未落盘，Candidate49 信号/执行台账 SHA-256 仍为 `5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79` / `d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f`。不得在 2026-08-03 同日重试、重请求失败响应补细节或推进后续信号阶段；离线 Campaign053 不受影响，可继续运行。

## Campaign053：金额/价格发现分布对齐（无收益唯一性门终止）

Campaign053 唯一 higher 因子为 `intraday_amount_price_discovery_alignment_js_238p`。在固定 09:31–11:30、13:01–15:00 网格内，分别形成两个半场各 119 个相邻 log-close return，排除 09:30 和午休跃迁；用 238 个 return 终点的非负 `amount` 归一化为 `p`，绝对收益归一化为 `q`，返回 `1-JSD(p,q)/log(2)`。只允许 `datetime,symbol,provider,close,amount`；禁止 open/high/low/volume、替代端点、跨午休、改窗、改方向、缩放、阈值、过滤、拟合或组合。

快照 manifest/data SHA-256 为 `e0f0e9176580e9e6216049d026ab360aea0904e5d1db57d61311fe6da7d3c402` / `d56d8628608faf32c97fb374cb05d06bfa0182d87f2d0467f5a08bca8c3f0f87`；33,015 个分区、7,724,498 行、7,695,088 个有效值全部通过字节/frame 哈希。唯一完成审计 SHA-256 为 `8228e32422686d020bdf7c6b00e54469d025884c23c234b48088428280bfd3ba`。覆盖中位/P05 为 `0.998318/0.993371`，P05 合格名称 138，可形成 540 个 cohort；覆盖门通过。

76 项冻结比较按预注册顺序全部读取后，唯一失败项为 `intraday_price_update_share_238m`，中位日度秩相关 `+0.852858` 超过绝对值 0.8 上限，因此在历史收益前终止。第一次审计因共享模块的 `OUTPUT_COLUMNS` 污染 Campaign051 verifier 而退出；隔离的精确五列 verifier 复核 33,015/33,015 分区后，唯一授权同参数续跑以退出码 0 完成。修复只影响验证器，不改变公式、方向、快照、比较、阈值或研究选择。

追加台账记录审计 verifier 失败、收口报告字面量断言失败两次基础设施尝试和 1 个完整因子尝试；累计历史尝试为 303，累计收益开发试验保持 266。首次收口测试 15/16 通过，唯一失败是测试漏写报告相关系数的正号；保留该失败后，当前 16/16 聚焦测试通过。该测试失败未读取因子值、比较值、价格或收益，也未改变任何结果或门禁。

没有读取日线或 forward return，没有开发或压力试验。不得反向、改窗、缩放、加阈值/过滤/模型、重跑、救援、组合或产生交易输出。Candidate49 仍是唯一前瞻候选且两本账本未变；2026-08-03 的失败闭锁仍禁止同日重试。Campaign054 离线研究无需等待新日线或 16:30，但必须从独立值前机制开始。

### Campaign054 历史滚动研究终止记录

Campaign054 的唯一值前冻结因子为高方向 `intraday_volume_weighted_transaction_price_bowley_skew_240m`：固定 240 个连续竞价分钟，活跃分钟 `x=log(amount/volume)`、权重为 `volume`，用成交量加权左连续经验 Q25/Q50/Q75 计算 Bowley 偏度；联合零量额不活跃，单边零量额无效，至少 120 个活跃分钟且 Q75>Q25。不得修改窗口、分位数、方向、变换、过滤、模型或组合。

权威 v2 快照 manifest/data SHA-256 为 `e61ec157d2119575bc53444d0c8e3c808a4c1113ace8ffa7ed2866bb5e431904` / `dbabb7ae1321f172b0ce3c3c4e6713f606245b8e2cc07387e5bacc77d58cfd7e`，含 33,015 个分区、7,724,498 行、7,675,743 个有效因子值。唯一无收益审计 SHA-256 为 `866006cbe319afeca3b055bef2a1754b954e4511b953a3e8a2337d3aa575ee87`；覆盖中位/P05 为 `0.998386/0.992613`，77/77 比较通过，最大绝对中位日度秩相关 `0.267355`。

唯一开发试验的 2021/2022/2023 Rank IC 为 `-0.000951/-0.010531/+0.003419`，10bp pilot 为 `-0.008040/-0.006610/-0.058345`；汇总 20bp pilot 为 `-0.229408`，最差归一化回撤 `-0.384016`。零开发幸存者，2024–2025 压力区间未打开、未读收益。累计历史尝试为 312，累计收益开发试验为 267。保留全部 8 次基础设施失败和 1 次完整因子尝试，不得以反向、改分位、重权重、改窗、过滤、重跑、救援或组合复活该因子。

Candidate49 仍是唯一前瞻候选，空信号/执行账本未变，且禁止历史回填。2026-08-03 已在 `stock_basic` 源门禁失败，虽然仓库 `.env` 中 `TUSHARE_TOKEN` 已确认存在且非空，仍不得同日重试；该凭据只供后续合格交易日的子进程读取，任何状态、报告、日志或清单不得写入其值或哈希。历史研究无需等待 16:30，但不得生成当前评分、选股、仓位、订单或投资建议，并须持续标注当前上市快照的幸存者偏差。

## Campaign055：价格更新时钟熵（无收益唯一性门终止）

Campaign055 继续以离线历史滚动为主要迭代引擎，不等待新增日线或 16:30。唯一 higher 因子 `intraday_price_update_clock_entropy_10b_238m` 只读取固定 09:31–11:30、13:01–15:00 的 240 个正有限 close；分别在两个半场形成 119 个相邻转移，排除 09:30 与午休转移，并以精确 `close_t != close_t-1` 定义更新事件，丢弃符号和幅度。每个半场的转移 `k=0..118` 映射到 `floor(5*k/119)`，合并为固定 10 桶；至少需要 20 次更新，因子为十桶更新占比的 Shannon 熵除以 `ln(10)`。不得改桶、阈值、方向、窗口、变换、过滤、模型或组合。

权威 v2 快照 manifest/data SHA-256 为 `f78d62adf2772d64e718e7fdc4138c40325f6c02d17073dd5db0d1271216009e` / `cfcdcd23267207f1a2190086b034105c447d5570549864d5468949ea05543882`；33,015 个分区、7,724,498 行、7,664,125 个有效因子值全部通过字节/frame 哈希。v1 快照保持不变但因保留陈旧的 Campaign006 协议证据而禁止进入下游；v2 重新完整计算，数值数据集哈希相同，协议证据仅保留 Candidate49 与 Campaign055。

唯一完成的无收益审计 SHA-256 为 `c931097cb92f6138c34bef7ad45e204cb17a25ae384d9fc1ad1b2622c0d66f7e`。质量与上市门后候选有效行 1,325,182；1,632 个会话的覆盖中位/P05 为 `99.633023%/98.850117%`，P05 合格名称 138，可形成 540 个不重叠三会话 cohort，覆盖门通过。随后 78 项冻结比较按预注册顺序读取；唯一失败项是 `intraday_price_update_share_238m`，中位日秩相关 `+0.878059` 超过绝对 0.8 上限，故 admissible factor 为 0。

Campaign055 在日线价格、forward return、2019–2023 开发折和 2024–2025 压力区间之前终止，不建立预测收益证据。追加台账记录 8 次基础设施失败与 1 个完整因子尝试，累计历史研究尝试由 312 推进到 321，累计读取开发收益的试验保持 267。第 6 次基础设施失败发生在终局后的组合测试：系统临时盘不足“复制字节 + 1 GiB”余量，5 个日线迁移测试在供应商请求前失败；完全相同的迁移测试移至 `/Volumes/DIsk` 独立 `basetemp` 后 21/21 通过。第 7 次基础设施失败来自把 3 条已被后续状态取代的不可变历史断言纳入当前专项集；第 8 次是 `--deselect` 使用了 `tests/data_collector_tests/...`，没有匹配 pytest 实际收集的 `data_collector_tests/...` 节点前缀。旧测试保持不变，当前套件使用 pytest 输出的精确节点 ID 排除历史断言，并使用独立版本的当前状态测试。这些收口失败均未改变因子或门禁。禁止反向、改桶、改阈值、重采样、缩放、过滤、重跑、救援或与终止因子组合；Campaign056 只能从经济上独立、值前冻结的新机制开始。

Candidate49 仍是唯一前瞻候选，信号/执行账本 SHA-256 仍为 `5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79` / `d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f` 且条目为 0；不得历史回填或启动第二个前瞻候选。本轮没有供应商请求；`.env` 中的 Token 只验证存在性，不输出、哈希或落盘。历史结果不生成当前评分、选股、仓位、订单或投资建议，并继续标注当前上市快照的幸存者偏差。

## Campaign056：跨日金额轮廓相似度（开发质量门终止）

Campaign056 继续执行双轨制，离线历史研究不等待新增日线或 16:30。唯一 higher 因子 `intraday_day_over_day_amount_profile_similarity_240b` 对信号日 t 与紧邻的已接受交易日 t-1 分别将固定 240 个同钟点非负 `amount` 归一化为分布 p/q，并计算 `1-JSD(p,q)/ln(2)`。只允许 `datetime,symbol,provider,amount`；股票缺失前一交易日时不跨停牌桥接，两个会话都必须有完整 240 格且金额和严格为正。不得改滞后、距离、方向、窗口、归一化、缩放、阈值、过滤、拟合、模型或组合。

不可变快照 manifest/data SHA-256 为 `cec4ce7db7a5a0a1715a8a117a09b74afe75bd94e3042df52493678ca6d6031b` / `b29accb9698fd6d62238540f49b85a32c6a3e7fd882bc64cb7fabd7ef1ec1d02`；33,015 个分区、7,724,498 行中 7,715,898 行有效，所有分区字节/frame 哈希与分数范围均通过。首次构建因 manifest 声明的空原始分区被拒绝；授权修复只接受精确列的零行 frame，所有非空 frame 原样委托，未改变非空候选值。

唯一无收益审计 SHA-256 为 `2a0c05800af7343e22d20c84c7380407df48616cfe86585b8cc52fb6513fcf8a`。覆盖中位/P05 为 `99.917184%/99.451102%`，P05 合格名称 138，可形成 540 个不重叠三会话 cohort；79 项比较按冻结顺序全部通过，最大绝对中位日秩相关 `0.747165`，最近因子为 `intraday_amount_participation_entropy_240m`。该阶段未读取日线价格或 forward return。

随后只运行预注册的一条 2019–2023 扩展滚动开发试验。2021/2022/2023 验证 Rank IC 为 `-0.046879/-0.028355/-0.050668`，normalized return 为 `-25.281001%/-41.429928%/-60.285918%`，10bp 整手收益为 `-3.054932%/-6.020877%/-9.581920%`，整手可负担率为 `68.918919%/79.452055%/66.216216%`。聚合 0/5/10/20bp 整手收益为 `-6.025908%/-9.967347%/-12.124552%/-19.371125%`，最差验证 normalized drawdown 为 `-60.287986%`。三折 IC、normalized return、10bp 收益全负且三折整手可负担率均低于 90%，故 survivor 为 0；2024–2025 压力区间未打开、未读取。

追加台账保留两次研究执行基础设施失败、一个完整因子尝试及同一尝试的一条开发延续记录。首次组合收口测试又误选了不可变的审计前断言：旧断言要求 `audit_count=0`，而当前已完成的审计数量正确为 1；该轮 23/24 通过，失败未读取分区值、价格或收益，旧测试保持不变，当前套件只排除这一精确历史节点。最终共 4 次独立尝试、5 条记录，累计历史研究尝试由 321 推进到 325，累计读取开发收益的试验由 267 推进到 268。Candidate49 仍是唯一前瞻候选，信号/执行台账不变且禁止历史回填；本 Campaign 未发供应商请求。不得反向、修补、改锚、重归一、重采样、缩放、过滤、调参、重跑、救援或与终止因子组合。历史结果不生成当前评分、选股、仓位、订单或投资建议，并继续标注当前上市快照的幸存者偏差；下一轮只能从新的经济独立、值前冻结机制开始。

## Campaign057：跨日绝对收益轮廓相似度（无收益唯一性门终止）

Campaign057 继续以离线历史滚动为主要迭代引擎，不等待新增日线或 16:30。唯一 higher 因子 `intraday_day_over_day_absolute_return_profile_similarity_238b` 对信号日 t 与紧邻的已接受交易日 t-1，分别在 09:31–11:30 和 13:01–15:00 两个半场内形成 119 个相邻 log-close return，取绝对值后合并为固定 238 格，独立归一化为 p/q，再计算 `1-JSD(p,q)/ln(2)`。精确零收益保留，09:30 与午休转移排除，股票缺失前一交易日时不得跨停牌桥接；只允许 `datetime,symbol,provider,close`，不得改滞后、格点、距离、方向、归一化、阈值、过滤、拟合、模型或组合。

不可变快照 manifest/data SHA-256 为 `7aba63621b2c6bd2b9d511d11ab56fc5331ae1dcf7a3c6055dbe6455d437d0ed` / `b24d183b15feb98015d7353160740273ffb5acc14dcf0031a984d9eb3003f19d`；33,015 个分区、7,724,498 行中 7,671,540 行有效，全部通过字节/frame 哈希。首次构建因 manifest 声明的六个零行源分区被拒绝；冻结修复只接受精确列的零行 frame，所有非空 frame 原样委托。

唯一完成的无收益审计为 `20260804T073457Z_campaign057_no_return_audit.json`（SHA-256 `1a0452a5ca821589d10131ec095f36a08046289f796770070bf750bfc1aa5a8b`）。第一次 16-worker 审计在系统交换空间耗尽后消失且未发布产物；冻结的同语义 4-worker 重试未复用任何部分状态，以退出码 0 完成。质量与上市门后有 1,326,131 个候选有效行；1,632 个会话的覆盖中位/P05 为 `99.728752%/99.056604%`，P05 合格名称 138，可形成 540 个不重叠三会话 cohort，覆盖门通过。

随后 80 项冻结比较按预注册顺序读取。`intraday_price_update_share_238m` 与 `intraday_amount_price_discovery_alignment_js_238p` 的中位日秩相关分别为 `+0.872247/+0.832056`，均超过绝对 0.8 上限，admissible factor 为 0。Campaign057 在日线价格、forward return、2019–2023 开发折和 2024–2025 压力区间之前终止，不建立预测收益证据。追加台账记录两次基础设施失败和一个完整因子尝试，累计历史研究尝试由 325 推进到 328，累计读取开发收益的试验保持 268。

Candidate49 仍是唯一前瞻候选，信号/执行台账为空且禁止历史回填；本 Campaign 未发供应商请求。禁止反向、修补、改锚、重归一、重采样、缩放、过滤、调参、重跑、救援、建模或与终止因子组合。历史结果不生成当前评分、选股、仓位、订单或投资建议，并继续标注当前上市快照的幸存者偏差；Campaign058 只能从新的经济独立、值前冻结机制开始。

## Campaign058：季度利润—营收同比增速差（无收益唯一性门终止）

Campaign058 继续以离线历史滚动为主要迭代引擎，不等待新增日线或 16:30。唯一 higher 因子 `quarterly_profit_revenue_growth_spread_pp` 固定为 `profit_yoy_state_t - revenue_yoy_state_t`。季度公告只在公告日之后的第一个已接受交易日可用；两个字段独立按股票前向填充，不回填、不跨股票填充。分钟网格只读取 `datetime,symbol,provider` 以确定股票—交易日身份，不读取分钟价格、成交量、成交额或活跃度。不得改方向、公告时点、填充、缩放、过滤、阈值、拟合、模型或组合。

不可变快照 manifest/data SHA-256 为 `c5bf57a70a2af71f30be87eec254710db65550f5dd7e041f219e862b4d97c00f` / `59fb5ed46c76a4737bbc60de9707f7f3b10223b692de4f4a88fec4143891cd4c`；33,015 个分区、7,724,498 行中 7,231,483 行有效，全部通过字节/frame 哈希。首次构建因 manifest 声明的零行源分区被拒绝；冻结修复只接受精确列的零行 frame，所有非空 frame 原样委托。

唯一完成的无收益审计为 `20260804T105439Z_campaign058_no_return_audit.json`（SHA-256 `df9c2ec09d6162ffa2ba4190f5c1141258a9769203cd7b4e297f8977f779b5b8`）。首次审计在读取候选快照后因兼容包装器未导出旧模块范围常量而失败，未产出覆盖或比较结果；冻结修复只补充候选值的有限浮点范围语义，不改公式、方向、门禁或比较顺序。质量与上市门后有 1,330,171 个候选有效行；覆盖中位/P05 为 `99.945175%/99.568865%`，P05 合格名称 138，可形成 540 个不重叠三会话 cohort，覆盖门通过。

随后 89 项冻结比较按预注册顺序读取；唯一失败项是 `quality_profit`，中位日秩相关 `+0.817009` 超过绝对 0.8 上限，admissible factor 为 0。Campaign058 在日线价格、forward return、2019–2023 开发折和 2024–2025 压力区间之前终止，不建立预测收益证据。追加台账记录四次基础设施失败和一个完整因子尝试，累计历史研究尝试由 328 推进到 333，累计读取开发收益的试验保持 268。后两次失败发生在终局验证：一次误用了绑定验证器不支持的 `--record` 参数，另一次测试进程未设置仓库 `PYTHONPATH` 而在五个模块的导入阶段失败；两者均未读取候选值、比较值、价格或收益，随后只用正确的 positional records 和 `PYTHONPATH=.` 重放相同验证。

Candidate49 仍是唯一前瞻候选，信号/执行台账为空且禁止历史回填。2026-08-04 的独立前瞻工作流在 16:30 后先通过只读 plan，随后 run 因 `stock_basic` 返回无效 `ts_code` 在源门禁失败；凭据存在且不是失败原因，同日未重试，活跃数据根和两本 Candidate49 台账未改变。该供应商失败不属于 Campaign058。禁止反向、修补、改锚、重归一、重采样、缩放、过滤、调参、重跑、救援、建模或与终止因子组合。历史结果不生成当前评分、选股、仓位、订单或投资建议，并继续标注当前上市快照的幸存者偏差；Campaign059 只能从新的经济独立、值前冻结机制开始。

## Campaign059：市场方向符号一致率（开发质量门终止）

Campaign059 继续执行双轨制，离线历史研究不等待新增日线或 16:30。唯一 higher 因子 `intraday_market_directional_sign_agreement_238m` 只读取固定 09:31–11:30、13:01–15:00 的 240 个 close，并分别在两个半场形成 119 个相邻 log-close return；09:30 与午休转移排除。每个位置使用冻结的全市场 return sum/count 扣除本股票后形成 leave-one-out 市场收益，要求至少 50 个其他股票；股票和市场收益均精确非零的同位置才有信息，至少需要 60 个信息位置，分数为其中符号相同的比例。不得加入 open/high/low/volume/amount，不得改市场定义、零值语义、方向、窗口、阈值、过滤、拟合、模型或组合。

不可变快照 manifest/data SHA-256 为 `478597c0b06fe6d777dac906b6b70dc95f9b6e0a498c5f0e5eabf271dc2de9e6` / `53f0c782633885f150ff1625e2b75ebb3b27e9f6e53e58c2e133718ebebf5293`；33,015 个分区、7,724,498 行中 7,583,771 行有效，全部通过字节/frame 哈希。保留三次基础设施失败及其窄修复：六个 manifest 声明的零行原始分区、分区全部完成后的 manifest 动态命名空间错误，以及无收益审计候选模块缺少旧范围别名；修复均未改变公式、方向、门禁、比较顺序或数值范围。

唯一完成的无收益审计为 `20260804T141411Z_campaign059_no_return_audit.json`（SHA-256 `633a85a1fe808947bb2a1ef3837f53ecfb85716fcc6ef91a4a06cff9e059ae0e`）。质量与上市门后有 1,319,978 个候选有效行；覆盖中位/P05 为 `99.300205%/98.067939%`，P05 合格名称 137，可形成 540 个不重叠三会话 cohort。覆盖门通过后才按冻结顺序读取 90 项比较，全部通过；最大绝对中位日秩相关为 `0.714890`，对应 `intraday_market_idiosyncratic_share_238m`，低于绝对 0.8 上限。该阶段未读取日线或 forward return。

随后只运行预注册的一条 2019–2023 扩展滚动开发试验。2021/2022/2023 验证 Rank IC 为 `-0.010331/+0.013326/+0.010566`，normalized return 为 `+21.973682%/-37.502954%/+1.263147%`，10bp 整手收益为 `+2.098032%/-7.662734%/-1.170692%`。聚合 normalized return 为 `+6.951373%`，但 0/5/10/20bp 整手收益为 `+4.107619%/-0.924121%/-4.556525%/-13.017742%`；最差验证 normalized drawdown 为 `-43.623938%`，仅一折 10bp 收益为正。它因此同时失败于中位 spread、中位 10bp 收益、正 10bp 折数、最差回撤和聚合 20bp 收益门，survivor 为 0；2024–2025 压力区未打开、未读取。

追加台账记录 7 次基础设施失败、1 个完整因子尝试及同一尝试的 1 条收益读取开发延续；Campaign059 有 8 次独立尝试、9 条记录，累计历史研究尝试由 333 推进到 341，累计读取开发收益的试验由 268 推进到 269。第 4 次基础设施失败发生在终端当前套件：`--deselect` 错带 `tests/` 前缀，未匹配 pytest 实际的 `data_collector_tests/` 节点，因此开发前零台账断言仍被执行，33/34 通过。第 5 次来自原地更新了第 4 次失败记录已字节绑定的终端测试文件，导致活绑定检查失败，32 通过、1 失败、1 排除；旧测试已恢复原字节，当前断言改用新版本路径。第 6 次是从 `tests/` 工作目录启动且没有显式仓库模块路径，7 个模块以 `ModuleNotFoundError: scripts` 收集失败；第 7 次虽从仓库根启动，但测试子进程仍未获得仓库模块路径，32 通过、1 失败、1 排除。固定绝对 `PYTHONPATH=/Volumes/DIsk/Disk-Coding/qlib` 后，同一当前套件为 33 通过、0 失败、1 排除。四次终端失败均未重算价格/收益或改变研究结论。Candidate49 仍是唯一前瞻候选，信号/执行台账为空且禁止历史回填；本 Campaign 未发供应商请求。2026-08-04 的独立 Candidate49 `stock_basic` 失败保持同日关闭。禁止反向、修补、改锚、重归一、重采样、缩放、过滤、调参、重跑、救援、建模或与终止因子组合。历史结果不生成当前评分、选股、仓位、订单或投资建议，并继续标注当前上市快照的幸存者偏差；Campaign060 只能从新的经济独立、值前冻结机制开始。

## Campaign060：跨日方向收益一致率（无收益覆盖门终止）

Campaign060 继续执行双轨制，离线历史研究不等待新增日线或 16:30。唯一 higher 因子 `intraday_day_over_day_directional_return_agreement_238b` 对信号日 `t` 与接受日历中紧邻的 `t-1`，分别在 09:31–11:30 和 13:01–15:00 两个半场形成 119 个相邻 log-close return，并按固定 238 个同钟点位置配对；任一日收益精确为零的配对无信息，至少需要 60 个共同非零位置，因子值为其中同方向配对的比例。股票缺失前一接受交易日时不得跨停牌桥接；只允许 `datetime,symbol,provider,close`，不得改滞后、窗口、零值语义、方向、阈值、过滤、拟合、模型或组合。

不可变快照 manifest/data SHA-256 为 `3f328039fb7806c66a260a7fd723a3297e2e0ce5ba23e9bb11f39d963e7250cd` / `052e5c8e5090c173c1e9486b545eafaa3b1301e038c1acc72434222e683d5735`；33,015 个分区、7,724,498 行中有 5,878,602 个因子有效行，所有分区字节/frame 哈希与分数范围均通过。首次构建因 manifest 声明的六个零行源分区被拒绝；冻结修复只接受精确列的零行 frame，所有非空 frame 原样委托。另保留快照验证命令误用 `--data-root`、审计兼容命名空间、manifest 适配器和候选范围别名等基础设施失败及其窄修复；它们没有改变公式、方向、数值、门禁或比较顺序。

唯一完成的无收益审计为 `20260804T160410Z_campaign060_no_return_audit.json`（SHA-256 `880dfc060005f49aa9df6d3c3f479d6408dc3c1667cc45c1b274a5ebf9fdd748`）。质量与上市门后候选有效 1,171,969 行，基准可用 1,331,759 行；覆盖中位/P05 为 `90.332413%/79.901731%`，分别低于冻结的 `95%/90%` 门槛。P05 合格名称数 128.55、540 个三会话 cohort 和 7 个观察年份通过容量项，但不能抵消覆盖失败。

覆盖门失败后，冻结的 91 项比较值均未读取，日线价格、forward return、2019–2023 开发折与 2024–2025 压力区间也均未打开。追加台账记录 9 次基础设施失败和 1 个完整因子尝试；累计历史研究尝试由 341 推进到 351，累计读取开发收益的试验保持 269。第 9 次基础设施失败来自终态组合测试误选了两条不可变的审计前断言：它们要求审计计数为 0，而唯一审计完成后的当前正确值为 1；该轮 24 项通过、2 项失败，未读取候选/比较分区值、价格或收益，历史测试保持不变，当前套件只排除这两个精确节点。不得降低覆盖阈值、减少共同非零支持数、把零收益计作一致、桥接停牌、筛选年份/股票/板块、反向、改窗、重跑、救援或与终止因子组合。

Candidate49 仍是唯一前瞻候选，信号/执行台账 SHA-256 仍为 `5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79` / `d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f`，条目均为 0；Campaign060 未发供应商请求、未历史回填、未生成当前评分、选股、仓位、订单或投资建议。继续标注当前上市快照的幸存者偏差；Campaign061 只能从新的经济独立、值前冻结机制开始，且离线研究不等待新日线或 16:30。

## Campaign061：跨日实现方差稳定度（开发质量门终止）

Campaign061 继续执行双轨制，离线历史研究不等待新增日线或 16:30。唯一 higher 因子 `intraday_day_over_day_realized_variance_stability_238b` 对信号日 `t` 与接受日历中紧邻的 `t-1`，分别在固定 09:31–11:30 和 13:01–15:00 的两个半场形成 119 个相邻 log-close return；每个会话的实现方差是 238 个收益平方和，分数固定为 `2*min(RV_t,RV_t-1)/(RV_t+RV_t-1)`。两日 RV 都必须严格为正且有限，不加 epsilon，不跨越缺失股票交易日，只允许 `datetime,symbol,provider,close`。

不可变快照 manifest/data SHA-256 为 `15ed4b46192402f301218e20b1fe37233dd7547256fb9786692ce544fae20b3c` / `a8a6261eaa92cd8eca7c25513236abf73f84f500da368a7b325634808fbb576a`；33,015 个分区、7,724,498 行中 7,671,540 行有效，全部通过字节/frame 哈希。保留三次基础设施失败：状态探针缺少数据根参数、六个 manifest 声明的零行原始分区，以及候选模块缺少旧审计器公开范围别名；冻结修复只处理精确零行 frame 或补充已经冻结的 `[0,1]` 范围属性，没有改变非空候选值、公式、方向、门禁或比较顺序。

唯一完成的无收益审计为 `20260804T183906Z_campaign061_no_return_audit.json`（SHA-256 `0d095077d10dd75668d4ce43f88f3b358aea0f815cbe9b7742a104eb913d16cb`）。质量与当前上市过滤后候选/基准有效行是 1,326,131/1,331,759；覆盖中位/P05 为 `99.728752%/99.056604%`，P05 合格名称 138，可形成 540 个不重叠三会话 cohort。覆盖通过后 92 项冻结比较全部通过；最大绝对中位日秩相关为 `0.212609`，对应 `intraday_return_variance_entropy_238m`。该阶段未读取日线价格或 forward return。

随后只运行预注册的一条 2019–2023 扩展滚动开发试验。2021/2022/2023 验证 Rank IC 为 `+0.009063/+0.009686/+0.023551`，normalized return 为 `-17.240067%/-2.293530%/-24.769728%`，10bp 整手收益为 `-2.780860%/-2.120424%/-4.798731%`，normalized 最大回撤为 `-38.990106%/-25.467597%/-32.254386%`。聚合 20bp 整手收益为 `-17.788650%`。虽然三折 IC 均为正，但两折价差为负、三折 normalized/10bp 收益全负且回撤门失败，因此 survivor 为 0；2024–2025 压力区间未打开、未读取。

追加台账记录 3 次基础设施失败、1 个完整因子尝试及同一尝试的 1 条收益读取开发延续；累计历史研究尝试由 351 推进到 355，累计读取开发收益的试验由 269 推进到 270。Candidate49 仍是唯一前瞻候选，信号/执行台账为空且禁止历史回填；本 Campaign 未发供应商请求。Campaign061 永久终止，不得反向、改 RV 定义、加入 epsilon、改滞后/网格/方向/成本/TopK/过滤/年份/门槛、重跑、救援、建模或与终止因子组合。历史结果不生成当前评分、选股、仓位、订单或投资建议，并继续标注当前上市快照的幸存者偏差；Campaign062 只能从新的经济独立、值前冻结机制开始，且离线研究不等待新日线或 16:30。

## Campaign062：季度公告同行拥挤稀疏度（开发质量门终止）

Campaign062 继续执行双轨制，离线历史研究不等待新增日线或 16:30。唯一 higher 因子 `quarterly_announcement_peer_crowding_sparsity` 对每个股票—交易日使用已经严格跨过公告日、在接受日历下一交易日生效的最新季度事件；按精确 `(report_date, announcement_date)` 统计不同发行人数量 `peer_count`，分数固定为 `1/peer_count`。同日同时生效时先取更晚 `report_date`，再取更晚 `announcement_date`。只读取 `datetime,symbol,provider` 和 `instrument,report_date,announcement_date`，不读取季度财务值或分钟价格、成交量、成交额。

不可变快照 manifest/data SHA-256 为 `518131c1ecac2820a426d2d7de46552daf9009b476ed7efbf3d69ba555f1ac45` / `5012eebb056fff75b6931390acaa5272629e70267ee5a32f46377c60994571a0`；33,015 个分区、7,724,498 行中 7,233,196 行有效，491,302 行位于首个有效披露之前，全部通过字节/frame 哈希。保留前三次值前基础设施失败：两个合成测试 fixture 错误，以及首份实现冻结中错误的 Campaign052 基础 runner SHA；它们都没有读取来源值、候选值、比较值、价格或收益。

唯一完成的无收益审计为 `20260804T210409Z_campaign062_no_return_audit.json`（SHA-256 `c783f58c5432068b1c5ca724be01d83bb234f17df21fcda64f9e7818b12bd4ea`）。质量与当前上市过滤后候选/基准有效行是 1,330,171/1,331,759；覆盖中位/P05 为 `99.945175%/99.568865%`，P05 合格名称 138，可形成 540 个不重叠三会话 cohort。覆盖通过后 93 项冻结比较全部通过；最大绝对中位日秩相关为 `0.769144`，对应 `quarterly_announcement_freshness_60s`，有符号相关为 `-0.769144`。该阶段未读取日线价格或 forward return。

随后只运行预注册的一条 2019–2023 扩展滚动开发试验。2021/2022/2023 验证 Rank IC 为 `-0.004674/-0.015270/-0.006314`，spread 为 `-0.350360%/-0.055596%/-0.644386%`，normalized return 为 `-18.683720%/+12.604669%/-30.421294%`，10bp 整手收益为 `-5.016157%/+0.985748%/-6.362546%`，normalized 最大回撤为 `-28.562210%/-22.784061%/-35.586048%`。全开发期 normalized/10bp/20bp 收益为 `-6.139055%/-10.407666%/-17.680546%`。操作门通过，但三折 IC 和价差全负，normalized 和 10bp 仅一折为正，回撤与聚合 20bp 门也失败，因此 survivor 为 0；2024–2025 压力区间未打开、未读取。

追加台账记录 5 次基础设施失败、1 个完整因子尝试及同一尝试的 1 条收益读取开发延续。第 4 次失败是终局文档补丁上下文不匹配，补丁在写入前被拒绝；第 5 次失败是通用完成审计遇到 Campaign001 不可变 `/Users/...` 路径与当前 `/Volumes/...` 克隆不一致，15 项通过、1 项失败。两者都未重算 Campaign062 研究值或收益。累计历史研究尝试由 355 推进到 361，累计读取开发收益的试验由 270 推进到 271。Candidate49 仍是唯一前瞻候选，信号/执行台账为空且禁止历史回填；本 Campaign 未发供应商请求。Campaign062 永久终止，不得反向为披露拥挤度、改变同行键/生效时点/冲突处理、加入财务值、改方向/成本/TopK/过滤/年份/门槛、重跑、救援、建模或与终止因子组合。历史结果不生成当前评分、选股、仓位、订单或投资建议，并继续标注当前上市快照的幸存者偏差；下一轮历史研究只能从新的经济独立、值前冻结机制开始，且离线工作不等待新日线或 16:30。

## Campaign063：横截面标准化收益状态稳定度（结构性零覆盖终止）

Campaign063 继续执行双轨制，离线历史研究不等待新增日线或 16:30。唯一 higher 因子 `intraday_cross_sectional_standardized_return_state_stability_236p` 在固定两个半场内形成 238 个相邻有符号 log-close return；每个位置使用冻结横截面 `sum/sum_squares/count` 计算 leave-one-out 同行总体 z 状态，要求至少 50 个其他同行且每个位置总体方差严格为正，再对精确 236 个半场内相邻 z 状态位移取平均绝对值并返回 `1/(1+mean_abs_displacement)`。禁止跨午间、删除位置、方差地板、零方差替代、改网格/同行下限/方向/变换/过滤、拟合、模型或组合。

不可变快照 manifest/data SHA-256 为 `12fc8d8bf7df432608f4cb63b7c5337f2cd46d2a029c34d8b3e60c0f8906a098` / `fd040477f3af2948976fda9a71f6d04a0bd9b9713a1b9b5a6dedf2f06f0c76df`；33,015 个分区、7,724,498 行均通过字节/frame 哈希。全部行都有完整股票收益且同行数量充足，但全部因至少一个位置的同行方差非正而无效。冻结矩基准的独立重放证明第 236 个位置在全部 1,699 个日期上横截面总体方差精确为零，第 29/30 位各另有 1 个零方差日期；这是收盘集合竞价网格的结构性同值，不是快照损坏或实现偏差。

唯一完成无收益审计为 `20260804T224823Z_campaign063_no_return_audit.json`（SHA-256 `06a8b4aace41d9567c8afb26755b6c5f932845a31dc842459ac3d148ab73c7c0`）。质量和当前上市过滤后基准可用 1,331,759 行，候选有效 0 行；1,632 个会话的覆盖中位/P05、P05 可用名称和三会话 cohort 都为 0。覆盖门失败，因此 94 项冻结比较值、日线价格、forward return、2019–2023 开发折及 2024–2025 压力区间均未打开。

追加台账保留状态导入路径、六个 manifest 零行分区、manifest 常量命名空间、通用审计因子范围、终局文档补丁上下文、终态组合测试历史断言和 deselect 节点前缀七次基础设施失败，以及一个完整因子尝试；累计历史研究尝试由 361 推进到 369，累计读取开发收益的试验保持 271。前四个窄修复未改变公式、候选值、严格正方差语义、方向、门槛、比较顺序或收益边界；第五个补丁在写入前原子拒绝；第六轮测试为 27 通过、2 失败；第七轮因 `tests/data_collector_tests` 未匹配实际 `data_collector_tests` 节点而为 33 通过、2 失败，新版当前测试本身全部通过。两轮都未读取研究值或收益。Candidate49 仍是唯一前瞻候选，空信号/执行账本未变；未发供应商请求、未历史回填、未产生当前评分、选股、仓位、订单或投资建议。Campaign063 永久终止，不得删除第 236 位、加入 epsilon、改网格/方差语义、重跑、救援、反向、建模或组合。继续标注当前上市快照的幸存者偏差；后续离线 Campaign 必须从新的经济独立、值前冻结机制开始。

## Campaign074：尾盘标准分钟成交额集中度（开发质量门终止）

Campaign074 继续执行双轨制；历史研究不等待新日线或 16:30，Candidate49 前瞻层保持独立。唯一 higher 因子 `intraday_terminal_bar_amount_share_240m` 要求原始 09:30 行存在，并验证精确 09:31–11:30、13:01–15:00 的 240 根标准一分钟 bar；分子是 15:00 的非负有限 `amount`，分母是 240 根标准 bar 的非负有限 `amount` 正和。09:30 不进入分母。该定义只衡量标准终端分钟成交额集中度，不声称使用专用收盘集合竞价委托、逐笔或不平衡数据。

不可变特征快照 manifest/data SHA-256 为 `5a993ce8b71c541a0b2d2402627d5f2b7f562cf1266bebcafe0606945086a3cd` / `d4fbb9eb8135674df16a50c96b5817f63e6461e99ee48df96537cd8ed930a4b5`；33,015 个分区、7,724,498 个接受行均通过独立字节、帧及聚合校验并具有有限值。冻结质量/上市资格口径下，候选/基准有效行是 1,330,171/1,331,759；覆盖中位/P05 为 `99.945175%/99.568865%`，P05 合格名称 138，可形成 540 个不重叠三会话 cohort。104 项冻结数值比较全部通过；最大绝对中位日秩相关为 `0.425556`，对应 `late_amount_share_30m`。

唯一预注册的 2019–2023 开发试验在 2021/2022/2023 得到 Rank IC `-0.015200/-0.011330/-0.010665`、normalized return `-5.338159%/-9.266436%/-7.552818%`、10bp 整手收益 `-0.314571%/-4.716421%/-2.208770%`。三个验证折的 IC、归一化收益与 10bp 收益全部为负；聚合 20bp 整手收益为 `-22.994450%`。运营门禁单独通过但质量门禁失败，survivor 为 0；2024–2025 压力区间未打开、未读取。

最终追加口径为 9 次基础设施失败、1 个完整因子尝试和该尝试的 1 条收益读取延续；累计历史研究尝试为 452，累计读取开发收益的试验为 276。第 5 次失败是终局多文件补丁引用陈旧上下文后被原子拒绝；第 6、7 次是两个 `pytest` 运行时探针在收集前失败；第 8 次是一条套件命令因隔离运行时缺少 `requests` 而产生 4 个收集错误，按命令只计一次；第 9 次是绑定校验器命令行参数解析失败。它们都未读取研究值或收益。Candidate49 仍为唯一前瞻候选，信号/执行台账各 0 条且禁止历史回填；Campaign074 未发 provider 请求。Campaign074 永久终止，不得反向、调权、重标、残差化、过滤、重跑、救援或组合；历史结果不得生成当前评分、选股、仓位、订单或投资建议。Campaign075 只能在 Campaign074 追加至完整定义顺序并事前冻结其数值比较资格后，从新的经济独立机制开始。

## Campaign075：接受覆盖会话年轻度（开发质量门终止）

Campaign075 继续执行双轨制；历史研究不等待新日线或 16:30，Candidate49 前瞻层保持独立。唯一 higher 因子 `accepted_instrument_session_youth_20s` 使用接受的本地交易日历，包含首尾地计算接受 instrument 覆盖起点至信号日的会话数，至少 20 个会话才有效，并返回负会话数。接受起点不是核验后的法定 IPO 日期；早于本地历史边界的股票被左截断并并列。不得改变符号、会话时钟、年龄规则、缺失语义、阈值、过滤、子集、模型、反向、重标、残差化、救援或组合。

不可变快照 manifest/data SHA-256 为 `d621c73d8f32fa0187c0b8f834a170548eeb8deb04e1fade7a12da08f160aef4` / `63b3bd548fa3f2d7f88e19542eb6be5e4ee7cc6f9d83f5dc874868efade98936`；33,015 个分区、7,724,498 行中有 7,689,881 个有效值。冻结质量/上市资格口径下，候选/基准有效行是 1,330,171/1,331,759；覆盖中位/P05 为 `99.945175%/99.568865%`。105 项数值比较全部通过，最大绝对中位日秩相关为 `0.543980`，对应 `intraday_microgap_absorption_share_238p`，有符号值为 `-0.543980`。

唯一预注册的 2019–2023 开发试验在 2021/2022/2023 得到 Rank IC `-0.002682/-0.023929/-0.013780`、normalized return `+38.128374%/+20.854240%/-44.381191%`、10bp 整手收益 `+3.587779%/+0.863344%/-5.960894%`。聚合 20bp 收益为 `-7.074176%`，最差验证归一化回撤为 `-46.658540%`。三折 IC 全负，质量门失败，survivor 为 0；2024–2025 压力区间未打开、未读取。

最终追加口径为 8 次基础设施失败、1 个完整因子尝试和该尝试的 1 条收益读取延续；累计历史研究尝试为 456，累计读取开发收益的试验为 277。开发时缺少 `setuptools_scm` 的失败发生在市场值读取前，保留于 trial ledger；解释器修复没有改变研究参数。随后一条终态套件命令因两个不可变事前状态断言失效而失败，首次 deselect 又使用了与 collection root 不匹配的节点前缀；两条命令各计一次，没有重算研究值或收益。Candidate49 仍为唯一前瞻候选，信号/执行台账各 0 条；本 Campaign 未发 provider 请求。v11 已冻结 107 个完整定义与 106 个数值比较器供下一轮离线研究使用；不得历史回填、创建 Candidate50、生成当前评分、选股、仓位、订单或投资建议。

## Campaign076：最大成交额分钟出现时点（开发门终止）

Campaign076 的唯一 higher 因子 `intraday_peak_amount_bar_recency_240m` 在精确 09:31–11:30、13:01–15:00 的 240 根标准一分钟 `amount` 中，固定取最大值最后一次出现的零基位置并除以 239。不可变快照 manifest/data SHA-256 为 `dc23177c4125142fb2287fb3e19a4be8a3cd53b70abd3be91718979aaf200f32` / `aef7cfb7cbc3ccaabe5552a4ed4f81ea8582d5f739153dd405b70e2a73b3a952`；33,015 个分区、7,724,498 行全部有限。

冻结质量/上市资格口径的中位/P05 覆盖为 `99.945175%/99.568865%`；106 项数值比较全部通过，最大绝对中位日秩相关为 `0.617854`。唯一 2019–2023 开发试验在三个验证折的 normalized return 与 10bp 整手收益均为负，聚合 20bp 收益为 `-24.195927%`，最差验证回撤为 `-36.458720%`，2023 折整手可负担率还低于 90%。因此 survivor 为 0，2024–2025 压力区间未打开。

本轮保留 11 次基础设施失败、1 个完整因子尝试及 1 条收益读取延续；累计历史尝试为 468，累计开发收益试验为 278。第 9 次失败来自终态套件中两条不可变事前状态断言在唯一审计完成后失效；第 10 次是首次 deselect 使用了与 pytest collection root 不匹配的节点前缀；第 11 次发生在 52/52 绑定已通过后，附加摘要读取了错误的 v12 计数字段。三条命令均没有重算研究值或收益。不得修改并列规则、反向、重标、过滤、调参、重跑、救援或组合。Candidate49 仍是唯一前瞻候选，账本为空且禁止历史回填；Campaign076 未发 provider 请求，历史结果不得生成当前评分、选股、仓位、订单或投资建议。

## Campaign077：成交额时钟离散度（开发质量门终止）

Campaign077 继续双轨制；离线历史研究不等待新日线或 16:30，Candidate49 前瞻层保持独立。唯一 higher 因子 `intraday_amount_clock_dispersion_240m` 要求精确 09:31–11:30、13:01–15:00 的 240 根标准分钟 `amount`，定义 `x_i=i/239`、`w_i=amount_i/sum(amount)`、`mu=sum(w_i*x_i)`，返回 `4*sum(w_i*(x_i-mu)^2)`。所有金额必须非负有限且总和严格为正；禁止改变公式、方向、网格、矩、变换、阈值、过滤、子集、年份、制度、拟合、模型或组合。

不可变快照 manifest/data SHA-256 为 `2449976e3bc95b66668496cee513277da21eff301677969f17053baf36fa18c8` / `2b40ea3cb07a75b8dbddae124da86d32578120b74e616ff4ada5446d77010fc9`；33,015 个分区、7,724,498 行全部有限并通过完整校验。冻结质量/当前上市资格口径下，候选/基准有效行是 1,330,171/1,331,759；覆盖中位/P05 为 `0.999452/0.995689`，P05 可用名称 138，可形成 540 个三会话 cohort。107 项数值比较全部通过，最大绝对中位日秩相关为 `0.661230`，对应 `late_amount_share_30m`。比较之前未读取日线价格或 forward return。

唯一 2019–2023 开发试验的 2021/2022/2023 Rank IC 为 `-0.003649/-0.008056/-0.002974`，normalized return 为 `+0.095682/-0.394839/-0.365443`，10bp 整手收益为 `+0.004794/-0.075211/-0.066501`。聚合 20bp 收益为 `-0.364508`，最差验证归一化回撤为 `-0.491742`。运营门禁通过、质量门禁失败，survivor 为 0；2024–2025 暴露压力区间保持关闭且未读取。

最终保留 9 次基础设施失败、1 个完整因子尝试和同一尝试的 1 条收益读取延续，trial ledger 共 11 条；累计历史尝试为 478，累计开发收益试验为 279。第 8 次失败是一次终局三文件原子补丁因陈旧上下文在任何写入前拒绝；第 9 次是终态测试错误地要求三份报告用同一百分比字符串表达同一个冻结收益，得到 20 通过、1 失败、3 条历史生命周期断言按计划跳过。两次失败均未重算因子、比较或收益。v13 已冻结 109 个完整逻辑定义与 108 个数值比较器，供 Campaign078 事前使用。Campaign077 不得反向、改窗、重标、过滤、调参、重跑、救援或与终止因子组合。Candidate49 仍是唯一前瞻候选，账本为空且禁止历史回填；本轮无 provider 请求，也未生成当前评分、选股、仓位、订单或投资建议。继续明确当前上市快照的幸存者偏差。

## Campaign078：成交额局部峰密度（开发质量门终止）

Campaign078 继续双轨制；离线历史研究不等待新增日线或 16:30，Candidate49 前瞻层保持独立。唯一 higher 因子 `intraday_amount_local_peak_density_238p` 要求精确 09:31–11:30、13:01–15:00 的 240 根标准分钟 `amount`。只检查内部索引 1–238；若 `amount_i` 严格大于左右相邻值则计峰，最后除以精确组合上限 119。与任一邻居相等都不计峰；禁止 epsilon、首末 tie-break、prominence、转折点、阈值、子窗口、变换、过滤、模型、组合或同轮救援。

不可变快照 manifest/data SHA-256 为 `a8d2f2a68dba3f7f3a3f34ac8d203f1381e429612ded6daf6c6447e0ed983071` / `225c539824978df0cc3e4b34a9520aa919ffa77ba73246c21e1bdb6122a0227d`；33,015 个分区、7,724,498 行全部有限并通过字节、frame 与聚合校验。冻结质量/当前上市口径下，候选/基准有效行是 1,330,171/1,331,759；覆盖中位/P05 为 `0.999452/0.995689`，P05 可用名称 138，可形成 540 个三会话 cohort。108 项冻结数值比较全部通过；最大绝对中位日秩相关为 `0.189505`，对应 `intraday_amount_profile_serial_persistence_240m`，有符号值为 `-0.189505`。

唯一 2019–2023 开发试验的 2021/2022/2023 Rank IC 为 `+0.012717/+0.004521/+0.017942`，normalized return 为 `+0.126334/-0.061971/+0.124821`，10bp 整手收益为 `-0.015190/-0.015291/-0.005095`。聚合 normalized/10bp/20bp 收益为 `+0.579110/-0.024496/-0.114468`，最差验证归一化回撤为 `-0.271268`。运营门通过、三个 IC 均为正且两个 normalized 折为正，但三个 10bp 折全负，中位 spread、成本收益、回撤及聚合 20bp 门失败；survivor 为 0，2024–2025 暴露压力区间保持关闭且未读取。

最终追加口径为 4 次基础设施失败、1 个完整因子尝试和同一尝试的 1 条收益读取延续，共 6 条；累计历史尝试为 483，累计开发收益试验为 280。第一次失败是 no-return v1 在覆盖及 107 个旧比较值已读后找不到追加 Campaign077 比较器的 helper 属性路径，发生在审计发布和价格/收益读取前；v2 只修复 helper 路径并从头重跑。第二次是终局 Markdown 报告补丁缺少合法结尾，在任何目标写入前原子拒绝。第三次是终态套件 deselect 前缀未匹配 collection root，得到 21 通过、3 条不可变前态断言失败并按命令计一次。第四次是 BSD `date` 不支持 `%:z` 造成无效记录时间后缀；旧文件保留，控制策略与台账用合法 UTC 版本追加修正，按共同根因计一次。后三次均未重算研究值或收益。时间戳修正版 v14 已冻结 110 个完整逻辑定义与 109 个数值比较器。Candidate49 仍是唯一前瞻候选，账本为空且禁止历史回填；本轮无 provider 请求，也未生成当前评分、选股、仓位、订单或投资建议。继续明确当前上市快照的幸存者偏差；后续离线 Campaign 只能从新的经济独立、值前冻结机制开始。

## Campaign079：信号日换手率（值前机制重叠终止）

Campaign079 最初选择接受供应商原始信号日换手率 `signal_day_turnover_rate_pct`、方向 higher。后续只读元数据核查发现，权威历史库存已经多次覆盖单字段换手水平、换手变化、`turnover_surge` 系列与 `return_turnover_correlation_10`；因此原机制独立性审查无效，测试原始水平会成为删除旧窗口或归一化后的救援。

本轮在任何日线数据行、候选值、比较值、价格或 forward return 之前终止；未创建特征快照、开发预注册或 stress。1 个完整因子尝试使累计历史尝试为 484，累计开发收益试验保持 280。v15 保留该失败定义，完整语义库为 111 个；因没有候选数值，数值比较器保持 109 个。Candidate49 仍是唯一前瞻候选，空账本未变；无 provider 请求、历史回填、当前评分、选股、仓位、订单或投资建议。

## Campaign080–083：历史滚动续跑与 2026-08-06 前瞻来源状态

Campaign080–083 继续执行双轨制：2019–2023 三组冻结扩展训练/验证折是主要迭代引擎，三个信号会话边界清除且 t+1/t+3 必须留在同一分区；2024–2025 只有在完整有限候选库、搜索空间、门禁、成本、代码与数据指纹全部冻结且开发 survivor 非零后才可整体打开一次。四轮均只有一个事前冻结的 higher 因子、一个方向和一个试验，不允许反向、改窗、过滤、同轮救援、模型搜索或组合旧终止因子。

- Campaign080 `intraday_above_median_amount_longest_run_240m`：109 项无收益比较全部通过，最大绝对中位日秩相关 `0.512057`；三折 Rank IC 全负，聚合 20bp 整手收益 `-17.584418%`，三折可负担率均低于 90%，survivor 为 0。
- Campaign081 `intraday_amount_path_efficiency_238p`：110 项比较全部通过，最大绝对中位日秩相关 `0.484395`；三折 Rank IC 全负，聚合 20bp 收益 `-23.074433%`，后两折可负担率低于 90%，survivor 为 0。
- Campaign082 `intraday_range_amount_peak_timing_alignment_240m`：111 项比较全部通过，最大绝对中位日秩相关 `0.750677`；只有一折 Rank IC 与一折 10bp 收益为正，聚合 20bp 收益 `-11.395294%`，survivor 为 0。
- Campaign083 `intraday_close_frontier_innovation_share_238p`：33,015 个分区、7,724,498 行全部技术有效；112 项比较全部通过，最大绝对中位日秩相关 `0.691932`。2021/2022/2023 Rank IC 为 `-0.038984/-0.029657/-0.048226`，10bp 整手收益为 `-2.562653%/-5.616098%/-0.519265%`，三折可负担率为 `61.711712%/62.100457%/67.117117%`；聚合 20bp 收益 `-15.274999%`，运营门与质量门均失败，survivor 为 0。

四轮的 2024–2025 压力区间均未打开、未读取。Campaign083 收口后的累计历史研究尝试为 533，累计收益读取开发试验为 284；v19 固定保留 115 个完整定义和 113 个数值比较器。Campaign084 可以在任何时间从新的值前冻结独立机制开始，但历史结果仍不得生成当前评分、选股、仓位、订单或投资建议，并继续受当前上市快照幸存者偏差限制。

Candidate49 统一工作流现已验证可从仓库根目录 `.env` 安全读取唯一非空 `TUSHARE_TOKEN`：文件必须是被 Git 忽略的 0600 普通非符号链接，解析器不执行 shell、不展开变量、不加载其他键，Token 不进入参数、输出、清单或研究记录。2026-08-06 同日 16:30 后的零请求 `plan` 以退出码 0、`ready=true` 通过；唯一确认运行在 `stock_basic` 非法 `ts_code` 源门禁以退出码 1 失败，四次 provider 调用后禁止同日重试和重请求失败响应。新 staging root 为 `/Volumes/DIsk/qlib-a-share-tushare-daily-2026-08-06`，只保留交易日历检查点和失败记录；活动日线根未改变，Candidate49 信号/执行台账仍各 0 条，未读 forward return、未历史回填、未启动 Candidate50，也未产生纸面或实盘订单。下一接受交易日必须使用新的绝对日期 staging root 并重新从 16:30 后的只读 plan 开始。

## Campaign084：利润增长水平与加速度下限（覆盖门终止）

Campaign084 继续以历史滚动为主要迭代引擎，不等待 16:30 或新增日线。唯一 higher 因子 `quarterly_profit_growth_level_acceleration_floor_2r` 在严格点时可用且共同有限的股票日横截面上，分别对 `profit_yoy` 水平和同股票同财报季度的 `profit_yoy` 同比一阶变化计算 average-tie 百分位排名，再固定取两项排名的较小值。完整 115 定义、113 数值比较器、方向、公式与所有门禁均在候选源值前冻结；禁止变更方向、算子、阈值、过滤、子集、年份、模型或组合。

不可变快照 manifest/data SHA-256 为 `68a547c9d85f6437382a16704f601074264c8206dd5fe4d23adaff20079f5994` / `eaae6e206284f605e6d673a89166ab996e4f246d59955f4d8f427ff7d8aecc5a`，包含 33,015 个分区、7,724,498 行和 6,321,289 个技术有限值。冻结质量/当前上市资格口径下，候选/基准有效行为 1,112,914/1,331,759；中位覆盖 `0.994594`，但 P05 覆盖与 P05 可用股票数均为 0。加速度定义因缺少上一年同财报季度基准而在 2019 形成结构性冷启动，违反冻结的 P05 `0.90` 与 50 名门槛。

因此无收益审计在读取任何 113 个比较器值、日线价格或 forward return 前终止；2019–2023 开发折和 2024–2025 压力区间均未打开。不得删除 2019、放宽门槛、改成单独同比水平、改变加速度定义、反向、重标、过滤、残差化或同轮救援。只读复核确认 2020-04-29 至 2025-12-31 有 1,378 个交易日至少 50 只候选股票，超过后续重复检测的 100 日资格线，所以本定义仍会进入下一轮数值比较库；覆盖门失败结论保持不变。

最终台账保留 11 次基础设施失败和 1 个完整因子尝试，累计历史研究尝试为 545，累计开发收益试验仍为 284。终态失败命令包括 Black、Ruff、两个冻结生命周期前态断言，以及测试绑定路径更新后的一次 Black 换行要求；未修改冻结特征脚本或旧测试。精确排除前态断言后的组合套件为 `13 passed, 2 deselected`，最终终态测试为 `4 passed` 且 Black/Ruff 通过。所有验证失败均未重算研究值或读取收益。Candidate49 仍是唯一前瞻候选，信号/执行台账各 0 条；Campaign084 未发 provider 请求、未历史回填，也未生成当前评分、选股、仓位、订单或投资建议。当前上市快照幸存者偏差和季度快照修订偏差继续作为硬限制披露。

## Campaign085 离线历史状态

Campaign085 继续使用双轨制：离线历史滚动无需等待 16:30，Candidate49 前瞻确认层保持独立。唯一事前冻结的 higher 因子是季报公告新鲜度排名与市场中性尾盘残差漂移排名的乘积；候选快照 manifest / dataset SHA256 为 `fb8ea4bdb2b2f783a8c1d4e020f1dcdfca1697c779c732e50233fe7b040b4d28` / `368f7cb96c15186cd511ccd4120e89b577141aa9687df8b39f9dd17320db8fb9`。

无收益覆盖门和 114 项比较门全部通过后，只运行一次冻结的 2019–2023 三折开发试验。三个 10bp 整手收益全负，聚合 20bp 收益 `-26.190957%`，survivor 为 0，所以 2024–2025 压力区间没有打开。开发首次二进制导入失败保留于追加台账；唯一修复是使用 Campaign083 已冻结、哈希绑定且不设置 DYLD 覆盖的 Conda 兼容解释器。

当前完整库为 117 个定义、115 个数值比较器；最终追加口径为 26 次基础设施失败、累计历史尝试 572、累计开发收益试验 285。三条不可变前态断言未被首次 deselect 排除的组合套件按一次失败保留，明确当前节点白名单为 19 passed，Black/Ruff 通过。Campaign085 的公式、方向和失败历史不可改写，也不得同轮反向、改窗、过滤、重跑、救援或组合；它只可作为以后事前冻结的重复检测比较器。历史输出不得生成当前评分、选股、仓位、订单或投资建议，Candidate49 仍禁止历史回填并保持唯一活动前瞻账本。

## Campaign086 离线历史状态

Campaign086 不等待 16:30 或新增日线。唯一 higher 因子 `intraday_intrabar_close_location_serial_persistence_238p` 对 240 根固定分钟 K 线计算 bar 内对数收盘位置，并只在两个半场内部汇总相邻位置的总体 Pearson 持续性；零振幅 bar 不桥接，至少要求 120 个信息对。快照 manifest / dataset SHA-256 为 `848ce713344f1ce805e3180344107d1d4bee5f8350bbcf52f8089e391fae3803` / `49cf11b5d69fa38a72f1a977975e290d4ed0bfd2205be6c50ba08dc64844b8e3`，1,331,759 行中 1,193,690 行有效。

冻结质量/当前上市口径的覆盖中位/P05 为 `92.318613%/80.755044%`，未达到 `95%/90%`；名称容量、538 个三会话 cohort 和 7 个年份虽通过，审计仍在读取 115 个比较器值之前终止。日线价格、forward return、开发折和 2024–2025 压力收益均未读取。

追加台账保留 9 次基础设施失败和 1 个完整因子尝试，累计历史尝试为 582，累计开发收益试验保持 285。当前完整库更新为 118 个定义、116 个数值比较器。不得降低覆盖门、删低覆盖年份/会话、放宽 120 对支持、桥接零振幅或午休、反向、过滤、重跑、救援或组合。Candidate49 仍是唯一前瞻候选，禁止历史回填；本 Campaign 未生成当前评分、选股、仓位、订单或投资建议。

## Campaign087 离线历史状态

Campaign087 继续以离线历史 walk-forward 为主要引擎，不等待 16:30 或新增日线。唯一 higher 因子 `intraday_range_amount_profile_alignment_js_240m` 在精确 240 根标准分钟上把对数振幅与成交额分别归一化为时钟概率轮廓，返回 `1-JS(p,q)/ln(2)`；零质量保留为零，不使用伪计数、平滑、阈值、过滤、模型或组合。

v5 紧凑快照共 1,331,759 行、1,328,449 个有效值；中位/P05 覆盖为 `99.853694%/99.354839%`。116 项冻结数值比较全部通过，最大绝对中位日秩相关为 `0.787143`，严格低于 `0.8` 但接近拒绝线。

唯一 2019–2023 三折开发试验的 Rank IC 为 `-0.035740/-0.025508/-0.052188`；normalized return 为 `+16.660467%/+47.546682%/-5.195431%`，10bp 整手收益为 `+0.961899%/+4.541692%/-2.178972%`。全开发期 20bp 收益为 `+2.528237%`，但三折 IC 全负、中位 spread 为负，最差验证回撤 `-25.217549%` 未通过 `-25%` 门。survivor 为 0，2024–2025 压力区间保持关闭且未读取。

最终保留 19 个历史研究尝试和 1 条收益读取延续，累计历史尝试为 601，累计开发收益试验为 286。终态组合套件的 5 条不可变前态断言、首次错误 deselect 前缀和手填声明时间超前均追加记录；文件系统出生时间确认值前冻结顺序成立，正确当前套件为 `36 passed, 5 deselected`。下一轮库为 119 个完整定义、117 个数值比较器。Campaign087 结果不可反向、改窗、平滑、过滤、重跑、救援或组合；Candidate49 仍是唯一前瞻候选，禁止历史回填，本轮没有 provider 请求、当前评分、选股、仓位、订单或投资建议。


## Campaign088 离线历史状态

Campaign088 继续以离线历史 walk-forward 为主要引擎，不等待 16:30 或新增日线。唯一 higher 因子 `intraday_bipower_jump_variation_share_238m` 在上午、下午两个 120-close 半场内分别形成 119 个相邻自然对数收益，共 238 个收益和 236 个半场内相邻对；定义 `RV=sum(r²)`、`BV=(pi/2)*(238/236)*sum(|r_i||r_{i+1}|)`，返回 `max(RV-BV,0)/RV`。午休不成对，零收益保留，不允许 epsilon、阈值、平滑、改窗、过滤、模型或组合。

不可变快照 1,331,759 行中 1,328,065 行有限；覆盖中位/P05 为 `99.831839%/99.337089%`，P05 可用名称 138，可形成 539 个不重叠三会话 cohort，覆盖门通过。随后按冻结顺序读取 117 个比较器；116 项通过，但与 `intraday_diffusive_variation_ratio_238m` 的绝对中位日秩相关为 `0.998285`，超过严格 `0.8` 上限，数值去重门失败。

审计在日线价格和 forward return 之前终止；未打开 2019–2023 开发试验或 2024–2025 压力区间，开发 survivor 为 0。最终记录 11 次历史研究尝试、12 条台账和 1 个完整因子尝试；累计历史尝试 612、累计开发收益试验保持 286。v27 库为 120 个完整定义、118 个数值比较器；C88 快照只用于以后阻止重复机制，不改变其终止结论。不得反向、重标、改正部、改窗、过滤、残差化、重跑、救援或组合。Candidate49 仍是唯一前瞻候选且空账本未变；本轮无 provider 请求、历史回填、当前评分、选股、仓位、订单或投资建议。

## Campaign089 离线历史状态

Campaign089 继续执行双轨制：历史 walk-forward 是主要迭代引擎，可在任意时间离线推进，不等待 16:30 或新增日线；Candidate49 前瞻确认层保持独立。唯一 higher 因子 `intraday_directional_amount_timing_spread_238m` 在上午和下午内部形成 238 个相邻一分钟收益，按连续交易顺序对严格正收益、严格负收益各自的目的分钟成交额计算标准化时间重心，返回 `T_up-T_down`。零收益不进入任一方向质量，零成交额保留；禁止 epsilon、阈值、改窗、过滤、模型和组合。

不可变特征快照 manifest/data SHA-256 为 `3ab55cc6f61bebb6713aeacb9e54125c20183295b862717617be0b13c9d0a204` / `c4f8794f42f1fffe2847ade875232827c8ca532a7fd75dd1123686c41456655a`；1,331,759 行中 1,327,577 行有效。覆盖中位/P05 为 `99.789916%/99.214860%`，P05 可用名称 138，可形成 539 个三会话 cohort。118 项数值比较全部通过，最大绝对中位日秩相关为 `0.409231`，对应 `afternoon_signed_amount_efficiency_120m`。

唯一冻结的 2019–2023 开发试验在 2021/2022/2023 的 mean Rank IC 为 `-0.013709/+0.010598/+0.013964`，normalized return 为 `-6.456899%/-17.768407%/+1.929896%`，10bp 整手收益为 `-1.876524%/-2.777596%/-1.138621%`。聚合 0/5/10/20bp 整手收益为 `+1.197600%/-4.231820%/-8.655588%/-16.711836%`，最差验证 normalized 回撤为 `-34.876863%`。运营门通过但冻结质量门失败，survivor 为 0；2024–2025 压力区间未打开、未读取。

最终保留 10 次历史研究尝试、12 条台账、1 个完整因子尝试和 1 条收益读取延续；累计历史研究尝试为 622，累计开发收益试验为 287。报告同步的一次组合补丁因上下文不匹配在任何写入前被拒绝，逐文件锚定更新随后成功且没有重算研究值。未来政策 v30 固定 121 个完整定义和 119 个数值比较器。Campaign089 结论不得反向、改窗、阈值化、过滤、重跑、救援或组合，历史结果不得生成当前评分、选股、仓位、订单或投资建议。Candidate49 仍是唯一活动前瞻候选，`.env` token 读取已安全验证但本轮未发 provider 请求、未运行同日 plan/run、未历史回填，两本前瞻台账仍各 0 条。

## Campaign090 离线历史状态

Campaign090 在任意本地时间使用离线历史主引擎，不等待 16:30 或新增日线。唯一 higher 因子 `intraday_range_clock_center_240m` 对完整 240 根标准一分钟 bar 的 `ln(high/low)` 振幅质量计算固定交易时钟第一矩；要求全部 high/low 有效有序、总质量严格为正，精确零振幅保留。该因子不读 close、amount 或 volume，不允许 epsilon、改窗、阈值、过滤、模型和组合。

不可变 7 分区快照 manifest/data SHA-256 为 `c065e81f4eec91b214a3e1f69d8e15e567fac5bd879e173c5b985777ab4ba2ed` / `d1da6b2c1d059038e473c55a15c76ba2efaf1a282d5a6bec1f302cd37a76ca31`；1,331,759 行中 1,328,449 行有效。覆盖中位/P05 `99.853694%/99.354839%`，119 项数值比较全部通过，最高绝对中位日秩相关 `0.789773`，对象为 `intraday_volatility_resolution_238m`。

唯一冻结开发试验的三折 Rank IC 均为正，但 normalized return 和 10bp 整手收益三折全负；聚合 20bp 收益 `-17.691709%`，最差验证 normalized 回撤 `-41.038853%`。因此 survivor 为 0，2024–2025 压力区间未打开、未读取。最终记录 10 次历史研究尝试、12 条记录和 1 条收益读取延续；累计历史尝试 632、累计开发收益试验 288。终态验证的两条冻结值前断言、首次错误 deselect 前缀和过宽 Black 范围按三次失败追加，正确当前节点套件为 `16 passed, 2 deselected`，Ruff 通过且冻结字节未改写。未来库为 122 个完整定义和 120 个数值比较器。Candidate49 仍是唯一活动前瞻候选；`.env` 凭据存在性已用兼容运行时安全验证，但当前早于 16:30，本轮未运行同日 plan/run、未发 provider 请求、未历史回填，两本前瞻台账仍各 0 条。历史结果不得生成当前评分、选股、仓位、订单或投资建议。

## Campaign091 离线历史状态

Campaign091 继续以离线历史 walk-forward 为主要引擎，不等待 16:30 或新增日线。唯一 higher 因子 `intraday_directional_range_mass_imbalance_240m` 在完整 240 根标准一分钟 bar 上，将 `ln(high/low)` 振幅质量按 `ln(close/open)` 的严格正负实体方向分组，返回 `(U-D)/(U+D)`；零实体不分组，零振幅保留，OHLC 必须有限、严格为正且有序。禁止 epsilon、改窗、阈值、过滤、模型、组合或同轮救援。

不可变 7 分区快照 manifest/data SHA-256 为 `1caf67c6b65947e4407f3064f732bf33a7595b9df977c8d62236c321c91e4541` / `e179abf89f0ef956e22508c00ca198a6cf612b25700c5b8612f1d3d6d383e6fa`；1,331,759 行中 1,328,350 行有效。覆盖中位/P05 `99.847561%/99.354839%`，120 项数值比较全部通过，最高绝对中位日秩相关 `0.623136`，对象为 `intraday_intrabar_close_location_pressure_240m`。

唯一冻结开发试验只有一折 Rank IC、normalized return 和 10bp 整手收益为正；聚合 20bp 收益 `-29.240505%`，最差验证 normalized 回撤 `-57.508261%`。因此 survivor 为 0，2024–2025 压力区间未打开、未读取。最终记录 4 次历史研究尝试、7 条记录和 1 条收益读取延续；累计历史尝试 636、累计开发收益试验 289。未来库为 123 个完整定义和 121 个数值比较器。Candidate49 仍是唯一活动前瞻候选；`.env` 凭据仅做存在性与权限验证，本轮早于 16:30，未运行同日 plan/run、未发 provider 请求、未历史回填，两本前瞻台账仍各 0 条。历史结果不得生成当前评分、选股、仓位、订单或投资建议。

终态验证把两条冻结值前生命周期断言误纳入授权产物已存在的当前节点套件，得到 `13 passed, 2 failed`；新终态测试首次 Black 检查也失败。两次命令均按基础设施失败追加，未修改旧断言或重算数据。显式当前节点白名单最终 `14 passed`，Black/Ruff 通过；最终口径为 6 次历史尝试、9 条记录、5 次基础设施失败，累计历史尝试 638、累计开发收益试验 289。科学结果、压力关闭状态及 Candidate49 空账本不变。

第一次当前节点白名单实际得到 `13 passed, 1 failed`，因为追加报告说明后研究记录 v1 的报告哈希绑定已过期。该失败追加后发布 v2 绑定链，不改写旧文件或科学值。最终 Campaign091 口径为 7 次历史尝试、10 条记录、6 次基础设施失败，累计历史尝试 639、累计开发收益试验 289。

逻辑时间审计再发现 4 个终态文件手填了比当时系统时钟稍晚的计划完成时间；通过追加 UTC 修正记录处理，原文件与研究值不改写，按一次共同根因失败计数。最终 Campaign091 口径为 8 次历史尝试、11 条记录、7 次基础设施失败，累计历史尝试 640、累计开发收益试验 289。

## Campaign092 离线历史状态

Campaign092 继续按双轨制在任意本地时间运行离线历史主引擎，不等待 16:30 或新增日线。唯一 higher 因子 `intraday_interbar_gap_discovery_share_238p` 在上午、下午两个 120-bar 半场内部各形成 119 个相邻分钟对，计算目的分钟开盘相对上一分钟收盘的绝对对数跳空质量 `G` 与目的分钟对数振幅质量 `R`，返回 `G/(G+R)`。午休、隔夜和跨日不桥接，完整 240 根 OHLC 必须有限、严格为正且有序，精确零跳空和零振幅有效，分母必须严格为正。禁止 epsilon、改窗、阈值、过滤、模型、组合或同轮救援。

不可变 7 分区快照 manifest/data SHA-256 为 `06fbfcae04af4ce2a917601876b5047e5ac09f75cf19d17bebc0bca8d9ff019e` / `7df85a0b3a75b203661de4d1695d8f75890fdc649efbee7739b4f2241ab93321`；1,331,759 行中 1,328,155 行有效。覆盖中位/P05 为 `99.835841%/99.337748%`，121 项数值比较全部通过，最高绝对中位日秩相关 `0.765191`，对象为 `intraday_amount_price_discovery_alignment_js_238p`。

唯一冻结开发试验的三折 Rank IC 全为正，但 normalized return 只有两折为正、10bp 整手收益只有一折为正；聚合 20bp 收益 `-13.979600%`，最差验证 normalized 回撤 `-24.668093%`。因此 survivor 为 0，2024–2025 压力区间未打开、未读取。最终记录 6 次历史研究尝试、9 条记录和 1 条收益读取延续；其中 5 次基础设施失败均在额外收益读取前发生。累计历史尝试 646、累计开发收益试验 290；未来库为 124 个完整定义和 122 个数值比较器。Candidate49 仍是唯一活动前瞻候选；`.env` 凭据读取、权限和 Git 忽略均安全通过，但本轮早于 16:30，未运行同日 plan/run、未发 provider 请求、未历史回填，两本前瞻台账仍各 0 条。历史结果不得生成当前评分、选股、仓位、订单或投资建议。

## Campaign093 离线历史状态

Campaign093 继续执行双轨制：离线历史研究可在任意时间推进，不等待 16:30 或新增日线，Candidate49 前瞻确认层保持独立。唯一 higher 因子 `intraday_close_transition_range_quadratic_efficiency_238p` 在上午、下午各 120 根标准分钟内部形成 238 个相邻收盘对，令 `Q=sum(ln(close_j/close_{j-1})²)`，并对各目的分钟令 `H=sum(ln(high_j/low_j)²)`，返回 `Q/(Q+H)`。午休不桥接，要求完整、有限、严格为正且有序的 HLC；零迁移和零振幅保留，分母必须严格为正。禁止 epsilon、改窗、阈值、过滤、模型、组合或同轮救援。

不可变 7 分区快照 manifest/data SHA-256 为 `69428173fd9a84f7272b56e253b589cb712355ce0b59a05e2a0b0b9576b82e92` / `bba3e4e71626b0ff2fa3860649da5187ef5c5412879b009f6890e9599ba3cf0b`；1,331,759 行中 1,328,155 行有效。覆盖中位/P05 为 `99.835841%/99.337748%`，122 项数值比较中 121 项通过；最高绝对中位日秩相关 `0.846190`，对象为 `intraday_intrabar_body_range_efficiency_240m`，超过严格 `0.8` 上限。

因此审计在日线价格和 forward return 之前终止，未打开开发折或 2024–2025 压力收益。最终记录 4 次历史研究尝试、6 条记录、3 次基础设施/实现失败和 1 个完整因子尝试；累计历史尝试 650、累计开发收益试验保持 290。未来库更新为 125 个完整定义和 123 个数值比较器。Campaign093 不得反向、改窗、重定义二次质量、过滤、残差化、重跑、救援或组合；Candidate49 仍是唯一活动前瞻候选。`.env` 为 0600 普通文件且凭据存在，当前早于 16:30，未运行同日 plan/run、未发 provider 请求、未历史回填，两本前瞻台账仍各 0 条。历史结果不得生成当前评分、选股、仓位、订单或投资建议。

## Campaign094 离线历史状态

Campaign094 继续执行双轨制：离线历史研究可在任意时间推进，不等待 16:30 或新增日线，Candidate49 前瞻确认层保持独立。唯一 higher 因子 `intraday_range_local_peak_clock_dispersion_236p` 在上午、下午各 120 根标准分钟内，对 `ln(high/low)` 的严格内部局部峰位置分别计算归一化交易时钟总体方差并取均值；每半场至少两个峰，午休不桥接，平峰和零振幅保留为有效非峰。禁止 epsilon、改峰定义、改窗、阈值、过滤、模型、组合或同轮救援。

不可变 7 分区快照 manifest/data SHA-256 为 `1f1441e59bcef1cb3d18b0030c640453e2ee762668d05157dec9ca1c0f01c340` / `37865a7d4c5556ee9a79ba9550f0f05229e3c52bb511d8bd1ac3b1f2525a6b63`；1,331,759 行中 1,314,834 行有效。覆盖中位/P05 为 `98.956975%/97.625760%`，123 项数值比较全部通过，最高绝对中位日秩相关 `0.077440`，对象为 `intraday_price_update_clock_entropy_10b_238m`。

唯一冻结开发试验只有一折 Rank IC 和一折 10bp 整手收益为正；三折 normalized return 为 `+14.596746%/+14.585687%/-3.875689%`，聚合 20bp 收益 `-16.037181%`，最差验证 normalized 回撤 `-18.552905%`。因此 survivor 为 0，2024–2025 压力区间未打开、未读取。最终记录 5 次历史研究尝试、8 条记录和 1 条收益读取延续；累计历史尝试 655、累计开发收益试验 291。未来库更新为 126 个完整定义和 124 个数值比较器。Campaign094 不得反向、改峰值定义、改窗、阈值化、过滤、重跑、救援或组合；Candidate49 仍是唯一活动前瞻候选，当前早于 16:30，本轮未运行同日 plan/run、未发 provider 请求、未历史回填，两本前瞻台账仍各 0 条。历史结果不得生成当前评分、选股、仓位、订单或投资建议。

终态验证首次 Black 检查仅要求格式化新建的终态测试，按一次不读额外收益的基础设施失败追加；格式化后 Ruff 通过、终态 `5 passed`。最终口径为 6 次历史研究尝试、9 条记录和 5 次基础设施/实现失败，累计历史尝试 656、累计开发收益试验 291；Campaign094 科学结果、126/124 库顺序、压力关闭状态和 Candidate49 空账本不变。

首次全量 JSON 扫描误把无文件指纹的纯叙事记录交给绑定验证器，按一次不读额外收益的终态工具范围失败追加。最终有效链扫描区分当前绑定与被授权激活/追加所取代的阶段记录；最终 Campaign094 口径为 7 次尝试、10 条记录、6 次基础设施/实现失败，累计历史尝试 657、累计开发收益试验 291，科学结论和边界不变。

第二次有效链扫描把快照 manifest 中按 manifest 所在目录解释的 7 个相对分区路径交给按仓库根解释相对路径的通用绑定验证器，造成 7 条根目录误判。该命令按一次不读额外收益的基础设施失败追加；manifest 和分区字节不改写，转由冻结的 Campaign094 快照专用校验器验证。最终口径为 8 次尝试、11 条记录、7 次基础设施/实现失败，累计历史尝试 658、累计开发收益试验 291，科学结果、126/124 库、压力关闭状态和 Candidate49 空账本不变。

## Campaign095–096 离线历史追加

Campaign095 的十桶自身收盘位置熵在值前合成测试中因半开桶边界不满足冻结的无条件反射不变性声明而终止，没有读取源数据或创建数值快照。Campaign096 的 `intraday_intrabar_close_location_total_variation_238p` 使用同一 HLC 状态但改为半场内相邻绝对迁移；不可变快照 manifest / dataset SHA-256 为 `1b205f1b6d3b28248b765860b8cf0e4aecee07f960fa535402e316ba13c39a3a` / `67106bd4f5d4382b770cb79355c27ea4d8ca179296841b7bd9fa2963a46e09f3`，1,331,759 行中 1,193,690 行有限。

Campaign096 覆盖中位/P05 为 `92.318613%/80.755044%`，未达到 `95%/90%`；124 个比较器、日线价格和 forward return 均未读取，开发与 2024–2025 压力区间保持关闭。其支持谓词与 Campaign086 的旧覆盖失败相同，后续历史 campaign 必须在值前做支持谓词去重：同一研究口径下，相同或更窄于已知失败支持的候选不得重复物化。Candidate49 前瞻账本与历史层继续严格隔离。

Campaign096 终态测试初版同时需要 Black 格式化，并把终态冻结 SHA-256 的最后一个字符漏写；该单一未冻结测试修订按一次不读研究值或收益的实现失败追加。修复后 Black、Ruff 与终态 `5 passed`。最终有效口径为 7 次历史尝试、7 条台账、6 次实现/基础设施失败，累计历史尝试 666、累计收益读取开发试验 291；科学结果、128/125 库顺序、2024–2025 关闭状态和 Candidate49 空账本不变。

## Campaign097 离线历史状态

Campaign097 按双轨制在任意时间运行离线历史主引擎，不等待新增日线。唯一 higher 因子 `intraday_market_range_profile_synchronization_240m` 把每只股票日的 240 个对数振幅归一化为时钟轮廓，再与同日 leave-one-out 市场轮廓做等时钟总体 Pearson 相关；每个时钟至少 50 个同行，零振幅分钟保留。紧凑快照 1,331,759 行中 1,328,449 行有限，覆盖中位/P05 为 `99.853694%/99.354839%`；125 项冻结数值比较全部通过，最大绝对中位日秩相关为 `0.684108`。

唯一 2019–2023 开发试验三折 Rank IC 全负，10bp 整手收益只有一折为正；聚合 10bp 收益 `+3.110050%`，但 20bp 收益 `-8.585555%`、最差验证 normalized 回撤 `-32.814553%`。质量门失败，survivor 为 0，2024–2025 未打开、未读取。最终保留 13 次历史尝试、16 条记录、12 次实现/基础设施失败和 1 条收益读取开发试验；累计历史尝试 679、累计开发收益试验 292。v43 固定下一轮 129 个完整定义和 126 个数值比较器；本因子只作为重复检测证据，不得反向、改定义、过滤、重跑、救援或组合。

Candidate49 仍是唯一活动前瞻候选，两本台账各 0 条且历史层不得回填。仓库 `.env` 已安全确认为 0600 普通文件、token 非空且不打印秘密；本轮在 16:30 前没有运行同日 plan/run 或请求供应商，也没有生成当前评分、选股、仓位、订单或投资建议。

## Campaign098 离线历史状态

Campaign098 在任意本地时间运行离线历史主引擎，不依赖新增日线。`intraday_range_clock_variance_240m` 的 7 分区不可变快照 manifest/data SHA-256 为 `371429a81292a91ef2bfa1292f467c81bf73e176fbfbc9888084f74eaaac1dc5` / `921f06fad98aed942550d86b1475c888aea6d2025c37d53ec55917401bd34b33`；1,331,759 行中 1,328,449 行有限。覆盖中位/P05 为 `99.853694%/99.354839%`，126 项数值比较全部通过，最高绝对中位日秩相关 `0.492023`。

唯一冻结开发试验的三折 Rank IC 全正，但 10bp 整手收益只有一折为正；聚合 20bp 收益 `-13.581324%`，最差验证 normalized 回撤 `-26.126720%`。因此 survivor 为 0，2024–2025 压力收益没有打开或读取。终态同步与验证共保留四次上下文/结果字段失败；最终记录 13 次历史研究尝试、16 条记录和 1 条收益读取延续，累计历史尝试 692、累计开发收益试验 293。未来库为 130 个完整定义和 127 个数值比较器。Candidate49 空账本不变，本轮未发 provider 请求、未历史回填，也未生成当前评分、选股、仓位、订单或投资建议。

### Campaign099 历史滚动终局（2026-08-07）

离线主引擎完成 `intraday_market_close_location_profile_synchronization_240m` 的事前冻结、紧凑快照、无收益覆盖/127 比较器去重和唯一一次 2019–2023 三折开发试验。紧凑快照为 1,331,759 行、1,328,449 个有限值；覆盖中位/P05 为 99.853694%/99.354839%，最大绝对中位日秩相关 0.712051。

开发三折 Rank IC、normalized return 和 10bp 整手收益均无正折；聚合 20bp 收益 -11.034078%，最差验证 normalized 回撤 -43.623594%。运营门和质量门均失败，survivor 为 0；2024–2025 压力区间保持关闭且未读取。首次执行的嵌套紧凑路径绑定失败已保留，修复仅绑定正确 manifest/数据哈希，没有改变因子、数据、折、成本或门槛。

当前有效台账为 18 次 Campaign099 历史尝试、23 条记录、15 次实现/基础设施失败和 1 条收益读取开发试验；累计历史尝试 710、累计开发收益试验 294。后续数值资格政策保持 131 个完整定义和 128 个数值比较器。Candidate49 两本前瞻账本仍各 0 条；没有 provider 请求、历史回填、当前评分、选股、仓位、订单或投资建议。

## Campaign105 离线历史终局（2026-08-08）

历史研究不依赖新增日线，也不等待 16:30。Campaign105 的唯一 higher 因子 `intraday_active_trading_bar_share_240m` 对 09:31–11:30、13:01–15:00 的精确 240 根 bar 统计量额同时严格为正的分钟占比；量额共同为零是有效不活跃，单边为零使股票日缺失。禁止改窗、阈值、方向、过滤、子集、模型、组合或同轮救援。

不可变快照 7,724,498 行中 7,724,451 行有效；质量上市口径覆盖中位/P05 为 `99.945175%/99.568865%`。131 项数值比较全部通过，最大绝对中位日秩相关 `0.635426`。唯一 2019–2023 三折开发试验在 2021/2022/2023 的 mean Rank IC 为 `-0.030565/-0.016617/-0.043634`，10bp 整手收益为 `-4.864958%/-0.951569%/-2.659420%`；聚合 20bp 收益 `-17.951247%`，最差验证 normalized 回撤 `-32.349363%`。

运营门通过但质量门失败，survivor 为 0，2024–2025 未打开、未读取。最终口径为 11 次历史尝试、12 条追加记录、10 次实现/基础设施失败、1 个完整因子尝试与 1 条收益读取延续；累计历史尝试 786、累计开发收益试验 300。未来政策 v63 为 135 个完整定义和 132 个数值比较器。Candidate49 仍是唯一前瞻候选且空账本未回填；`.env` 已按普通文件、`0600`、Git 忽略、唯一非空 token 安全验证，但周六没有 provider 请求或 Candidate49 workflow，也没有 Candidate50、当前评分、选股、仓位、订单或投资建议。

### Campaign113：监管行动适配器与公式冻结追加

纯离线阶段冻结了 `scripts/a_share_official_exchange_enforcement.py` 及合成测试。适配器不实现 transport，不含来源请求 CLI，只接受有限精确标签、严格 `YYYY-MM-DD`、沪主板/深主板与创业板代码以及同一官方域名 href；完整可分类的非持仓板块代码只排除计数，跨交易所代码、未知/歧义标签、非官方 href、日期或文档状态冲突均硬失败。归一化结果只保留处理日期、instrument、exchange、action family/type token、href SHA-256 和 provider。

同一值前记录冻结唯一 higher 因子 `official_exchange_enforcement_recovery_session_age_60sessions`。事件在处理日期之后第一个接受会话收盘生效；信号会话只看年龄 0–59 的活跃事件，并返回距离最新生效事件的会话数。没有活跃事件保持缺失，不允许零填充、措施家族权重、事件数量权重、剪裁或中性化。完整定义库更新为 141；在数值快照、容量与去重证据出现前，数值比较器保持 134。

旧 `research_attempt_ledger_v1.json` 保持六条记录阶段快照不变，后续完整记录进入 `research_attempt_ledger_v2.json`，最新增量进入 `research_attempt_ledger_v3.json`。在任何交易所列表/API 请求前，仍必须从官方静态元数据单独冻结精确 endpoint、schema 与分页映射，并冻结一次性原子 source-acceptance workflow；禁止猜测参数或提前检查、统计、持久化来源行。

### Campaign113 元数据终止

官方静态元数据已确认上交所 `commonSoaQuery.do`/JSONP 与深交所 `ShowReport/data`/JSON 的固定 catalog 和分页结构。上交所四个必需角色精确匹配；深交所监管措施目录的日期/文档标签、纪律处分目录的措施/日期/文档标签不在冻结白名单。由于双交易所是强制验收范围，Campaign113 在来源行前 fail-closed；不得曝光后扩充标签、模糊或位置映射、删除深交所、改来源或修补公式。深交所两次 catalog 请求只解析 `metadata`，响应 `data` 成员未访问、持久化、哈希或计数。

v77 保留 141 个完整定义和 134 个数值比较器；`official_exchange_enforcement_recovery_session_age_60sessions` 仅作为未来语义重复控制，不生成快照或比较器。最终台账为 15 次尝试、12 次基础设施失败、3 次值前科学尝试、1 个完整定义；累计历史尝试 842、累计收益读取开发试验 302。日线、forward return、2019–2023 开发和 2024–2025 压力均未打开。Candidate49 仍是唯一前瞻候选且两本账为空；周日没有 plan/run、历史回填、当前评分、选股、仓位、订单或投资建议。

首次终态 Black 命令把两个已有冻结测试纳入新版格式范围，命令在 pytest 前停止且没有改写文件或读取研究值。该范围失败由 v5 台账追加，v78 只更新有效会计为 16 次尝试、13 次基础设施失败和累计历史尝试 843；完整定义/数值比较器仍为 141/134，累计收益读取开发试验仍为 302。

终态测试绑定补丁随后因引用格式化前上下文而未命中，没有修改文件或读取研究值。v6 台账与 v79 最终更新会计为 17 次尝试、14 次基础设施失败、累计历史尝试 844；141/134 顺序和累计收益读取开发试验 302 保持不变。

组合完整性命令因包含临时目录删除而被安全策略在执行前整体拒绝；仓库与研究值无变化，临时目录保留。v7 台账与 v80 的最终会计为 18 次尝试、15 次基础设施失败、累计历史尝试 845；141/134 顺序和累计收益读取开发试验 302 不变。

### Campaign114 值前来源发现

有限概念审查从 6 个构想中只选择 `official_exchange_information_disclosure_evaluation_grade` 进入来源元数据发现。该状态拟使用沪深交易所年度发行人信息披露工作评价，但当前只通过相对 141 个完整定义的语义独立性预检；双交易所 2019–2025 档案、共同有限等级词表、发布日期和稳定文档身份尚未证明，因而没有完整因子定义。

冻结协议只允许三个精确检索词和官方公开静态搜索/导航/索引元数据；不得打开或下载评价附件，不得读取、统计或推断发行人等级行，也不得使用第三方镜像、OCR、手工名称匹配、单交易所路径或曝光后扩词。元数据若成功，仍须先冻结等级映射、纯合成适配器、公式、点时规则和原子 source contract；任一交易所、年份或角色失败即终止。

两次预协议搜索未取得结构化官方档案链接，一次本地 `python` 别名失败，均追加记账。Campaign114 当前 4 次尝试中有 3 次基础设施失败、1 次值前科学尝试，没有完整因子或收益试验；累计历史尝试 849、累计收益读取开发试验 302。v81 保持 141/134；无来源行、候选/比较值、日线、forward return 或压力读取。Candidate49 仍是唯一前瞻候选且两本账为空；周日没有 plan/run、历史回填、当前评分、选股、仓位、订单或投资建议。

首次定向测试的链式等式把预期哈希比较成布尔值，得到 `23 passed, 1 failed`；政策字节与库顺序没有不一致。修复只改未冻结测试断言，并把失败追加进 v2 台账。v82 最终口径为 Campaign114 5 次尝试、4 次基础设施失败、累计历史尝试 850；141/134、收益读取开发试验 302、来源边界和 Candidate49 空账本均不变。

#### Campaign114 官方元数据终止

协议绑定的三个固定检索词确认沪深两所规则均发布 A/B/C/D 评价词表，并定位若干年度结果页、发布日期和附件标签。完整双交易所 2019–2025 档案与全部点时角色尚未证明时，深交所静态文档域的检索响应直接嵌入了评价附件的公司代码、简称和等级行。未点击、打开、下载、截图或哈希附件字节，也未持久化或计数具体公司等级；但搜索响应已违反“映射、公式、纯适配器和 source contract 先于来源行”的冻结边界。

Campaign114 因此在完整定义前 fail-closed，禁止切换搜索工具、补标签、单交易所救援、改来源或事后冻结映射。最终 7 次尝试中有 5 次基础设施失败、2 次值前科学尝试，完整定义、数值快照和收益试验均为 0；累计历史尝试 852、累计收益读取开发试验 302。v83 保持 141/134。Candidate49 仍是唯一前瞻候选且两本账为空；周日没有 plan/run、历史回填、当前评分、选股、仓位、订单或投资建议。

首次跨 Campaign112–114 终态套件得到 `31 passed, 1 failed`；唯一失败是 Campaign114 专属报告标题缺少统一编号前缀。补全标题并追加失败会计后，v84 的最终口径为 Campaign114 8 次尝试、6 次基础设施失败、2 次值前科学尝试、累计历史尝试 853；141/134 和收益读取开发试验 302 不变，未新增任何读值或 Candidate49 行为。

## Campaign116 本地覆盖率终止（2026-08-12）

Campaign115 已按用户范围选择在供应商值前结束；Campaign116 改用既有本地 2019–2025 分钟快照，不依赖 `limit_list_d`、5,000 积分、新增日线或 16:30 等待。唯一 higher 因子 `intraday_amount_conditioned_directional_persistence_spread_236p` 的 33,015 分区、7,724,498 行快照已通过全部字节/帧哈希和聚合摘要验证，其中 5,177,430 行满足公式支持。

单独冻结的覆盖率 runner 必须先执行 metadata-only `plan`；本次 plan 为 `ready=true` 且退出码 0 后才执行一次确认审计。PIT 质量/当前上市资格基准为 1,331,759 个股票日与 1,632 个会话。中位/P05 覆盖率为 `85.013381%/71.417946%`，未达到 `95%/90%`；P05 名称数 `121`、`539` 个非重叠三会话 cohort、七年和 `1,632` 个非恒定横截面会话则通过。由于覆盖门是合取门，Campaign116 在所有比较因子前终止。

审计读取 0 个数值比较器，没有读取日线、forward return、开发折或 2024–2025 压力收益，也没有加载凭据或请求 provider。不得降低 30+30 信息对支持、改变严格金额中位规则、反向、过滤、拟合、组合或救援。v102 保持完整定义/数值比较器 `142/134`；Campaign116 有效会计仍为 5 次尝试、4 次基础设施失败、累计历史尝试 883、累计收益读取开发试验 302。Candidate49 仍为唯一前瞻候选且两本账各 0 条；无历史回填、第二前瞻候选、当前评分、选股、仓位、订单或投资建议。Campaign117 可以在任意时间从真正不同、值前冻结的机制开始。

终态后的技能文档追加首次因补丁上下文不匹配在写入前失败，未改变代码、快照、研究值或科学结果。v103 只追加该基础设施失败：Campaign116 有效会计为 6 次尝试、5 次基础设施失败，累计历史尝试 884；完整定义/数值比较器 `142/134`、累计收益读取开发试验 302、Candidate49 空账本和全部禁止边界不变。

终态测试指针补丁随后因 Black 格式化后的实际上下文不同而在写入前失败，也未改动文件。v104 再追加一次基础设施失败：Campaign116 有效会计为 7 次尝试、6 次基础设施失败，累计历史尝试 885；覆盖终止科学结果、`142/134`、收益读取试验 302 和 Candidate49 空账本不变。

## Campaign264 本地原始通道独立机制值前终止（2026-08-24）

Campaign264 继续执行双轨制，但只做零网络值前研究。它从权威 Campaign263 状态和 v414 政策重建 162 个完整定义、143 个数值比较器，并只读取 Tushare 一分钟与日线 Parquet footer 的 schema/row-count 元数据。分钟源仅含身份、OHLC、share volume 和 CNY amount；日线源仅含标准 OHLC、pre-close、change、pct-change、volume 和 amount。本轮没有加载任何候选、比较、日线价格序列或 forward return 值。

有限目录的七条路线全部在值前拒绝：收益超额峰度、range 轮廓频谱熵、volume 轮廓频谱熵、amount 方向字典、跨日 range 轮廓相似度、零成交/零 range 最长连续段，以及 143 项完整数值库的 pair/调权/模型。对应的冻结历史已明确关闭高阶尾部替代、range 复杂度 estimator 搜索、amount/volume 字段替换、activity 字典、跨日 range 相似度、二元支持状态路径细化和终止库重组。强行物化其中任一路线会成为曝光后救援。

因此 Campaign264 选中因子、定义追加、数值比较器追加、开发试验和 2024–2025 压力试验均为 0；库保持 `162/143`。7 条值前科学尝试进入追加式链，累计历史尝试为 2,604，累计收益读取开发试验保持 315。Candidate49 仍是唯一前瞻候选，两本账各 0 条；记录时早于 2026-08-24 16:30，本轮无 provider/Web 请求、无 plan/run、无历史回填、无当前评分、选股、仓位、订单或投资建议。Campaign265 只能从真正新的被接受点时信息通道或值前可证明独立的新机制开始。


## Campaign265 可转债平价溢价压缩值前合同（2026-08-24）

Campaign265 只重访 Campaign157 明确保留的 `c157_01` 跨资产来源延期项。6 条有限路线中，`convertible_bond_equity_parity_premium_compression_3s` 通过完整 162 定义的值前机制独立性审查；溢价水平/方向网格、转债价格动量、流动性交互、债券子类型扩展和多窗口/模型/旧因子组合均在任何值前拒绝。

来源合同冻结使用 Tushare `cb_basic` 的 `ts_code,cb_type,stk_code,list_date,delist_date,exchange` 与 `cb_daily` 的 `ts_code,trade_date,amount,cb_over_rate`。官方文档显示两接口最低均为 2,000 积分；5,000 积分只提高相对调用频次，因此本路线不要求追加购买。信号只允许在提供商 17:00 更新后的下一接受会话使用。每只 exact `CB` 的分数固定为前三个接受 A 股会话的转股溢价率减当前溢价率；两端都必须有有限溢价率和严格正成交额，同一正股多债券取算术中位数，无活动或合格债券为缺失。

合同同时固定 2019-01-02 至 2025-12-31 范围、当前因子宇宙与日历指纹、映射/摘牌/多债/缺失/陈旧值语义、活动转债发行人分母、中位/P05 覆盖 95%/90%、P05 至少 50 名、至少 200 个非重叠三会话 cohort、五年跨度以及全部 143 个比较器的有序严格唯一性门。任何来源或门禁失败都终止该精确定义，不得重试、换字段、改滞后、反向、筛选、模型化或组合救援。

本轮仅查阅官方公开文档，没有加载 Token 或请求 Tushare 行，也没有读取候选、比较、日线价格或 forward return。Campaign265 还没有完整因子定义或数值比较器追加；库保持 `162/143`。6 条科学尝试和 1 次写入前补丁失败均已入账，累计历史尝试为 2,611，收益读取开发试验保持 315。下一步仅允许实现并验证零网络 adapter，再单独冻结一次性来源验收计划；当前合同不授权请求。Candidate49 仍为唯一前瞻候选且账本为 0/0，禁止回填、第二候选、当前评分、选股、仓位、订单或投资建议。

## Campaign265 零网络适配器完成（2026-08-24）

冻结的 `convertible_bond_equity_parity_premium_compression_3s` 合同已经实现为纯 Python/pandas 确定性 adapter；它没有 CLI、网络、凭据、provider client 或真实数据文件加载器。16 项纯合成测试覆盖 exact `CB`、严格 schema/身份/日期、A 股映射、活动区间、两端有限溢价与严格正成交、精确三接受会话滞后、单债溢价压缩、发行人奇偶算术中位数、活动转债发行人分母、缺失不置零以及失败关闭。首次 Black 检查的格式问题已作为基础设施失败保留；格式化后 Black、Ruff 与全部 16 项测试通过。

适配器阶段没有加载 Token、请求 provider 或读取任何来源、候选、比较、价格、forward return 值；一次性来源验收 planner 也尚未创建。Campaign265 当前为 10 次尝试（7 科学、3 基础设施失败），累计历史尝试 2,614、收益读取开发试验 315，完整定义/数值比较库仍为 `162/143`。下一步只允许另行冻结并实现零网络一次性来源验收 planner；它必须绑定当前合同和 adapter 字节，固定接受日清单、字段、请求上限、原子路径、截断检查及失败不重试证据，然后才可讨论显式确认。Candidate49 继续保持唯一前瞻候选与 0/0 空账本，禁止回填、第二候选、当前评分、选股、仓位、订单或投资建议。

## Campaign265 零网络来源验收计划就绪（2026-08-24）

一次性 source-acceptance planner 已在 v418 的 plan-only 授权下完成冻结和执行。它绑定来源合同、adapter/测试字节、日历、因子宇宙和 Candidate49 空账本，完整列出 2019-01-02 至 2025-12-31 的 1,699 个接受日。未来请求序列严格为 1 次 `cb_basic` 加 1,699 次按日历顺序的 `cb_daily`，共 1,700 次；字段不扩展，每次至少一行且严格少于 2,000 行，provider entry 最小间隔 1.05 秒。

`plan` 实际退出码 0、`ready=true`、无 blocker，且目标路径执行前后均不存在。planner 不含 `.env`/环境凭据读取、provider client、传输、写盘、`run` 或确认接口；本轮没有加载/哈希 Token、请求来源或读取任何来源/候选/比较/价格/收益值。私有 intent/journal、逐请求授权、原子 checkpoint、精确已提交前缀恢复、终止不重试和失败去敏语义已冻结，但尚未实现或启动执行 workflow。`ready=true` 不等于来源授权，后续必须另冻 workflow 和新政策。

Campaign265 当前 13 次尝试（8 次值前科学、5 次基础设施失败），累计历史尝试 2,617、收益读取开发试验 315；完整定义/数值比较器仍为 `162/143`。Candidate49 继续是唯一前瞻候选且两本账为 0/0，禁止历史回填、第二候选、当前评分、选股、仓位、订单或投资建议。

来源计划发布后的第一次终态套件因旧 adapter 生命周期测试仍绑定统一报告的早期发布哈希而得到 41 通过、1 失败；第二次命令又因 `tests/data_collector_tests/` 与实际 `data_collector_tests/` collection root 前缀不同，得到 46 通过、同一项失败。两次都只属于测试编排，不读取或重算任何研究值。保留旧测试和两份失败证据后，版本化当前状态测试与精确 node deselect 的最终结果为 47 通过、1 个历史节点 deselected；Black、Ruff 和 v4–v6 台账链均通过。有效会计修正为 Campaign265 15 次尝试（8 科学、7 基础设施）、累计历史尝试 2,619；来源计划、`162/143`、收益试验 315、Candidate49 空账本和全部禁止边界不变。

## Campaign265 凭据安全执行工作流计划就绪（2026-08-24）

事前冻结的执行协议已经实现为一次性、可恢复但终止不重试的工作流。安全复核在任何 run 权限前发现 v1 未显式拒绝目标父目录符号链接；v1 证据原样保留，v2 增加仓库根和每个既有目标父级必须是真实目录的预检，并在 plan 和任何执行写入/凭据前重复检查。当前公开 CLI 仅包含 `plan`；v419 revision 2 只授权零网络计划。未来有效 v420 精确绑定工作流、测试、协议、实现冻结 v2 和 plan-result v2 字节前，`run` 子命令不会暴露。真实执行还必须显式给出 `--confirm-run`。

状态机要求 0600 intent 与空 journal 在凭据加载前独占创建并 fsync；每个请求的 `request_authorized` 事件必须先于 provider entry 持久化，checkpoint 与 sidecar 经过原子写、字节/帧哈希和 schema 验证后才允许提交。只可从完整验证的已提交前缀恢复；任何 authorized-without-checkpoint、凭据、传输、schema、空响应、截断、身份、日期或持久化失败均终止且不得重发。失败证据不得包含 token/摘要、原始值、行数或 provider 明文异常。

v419 revision 2 下的 standalone `plan` v2 实际退出码 0、`ready=true`，34/34 检查通过，目标目录树安全检查通过。它绑定 1,699 个接受日和精确 1,700 个未来调用，但没有构造 intent、检查 `.env`/环境/token、导入或创建 provider、发出请求、读取任何来源/候选/比较/价格/收益值或写来源文件；`future_run_authorized=false`，`run_interface_exposed=false`。

workflow 测试为 13 passed，Campaign265 跨阶段套件为 60 passed、1 个历史可变报告节点 deselected，v7–v12 追加链通过。最终 Campaign265 为 31 次尝试（14 科学、17 基础设施），累计历史尝试 2,635、累计收益读取开发试验 315；完整定义/数值比较器仍为 `162/143`，完整因子和本轮收益试验仍为 0。Candidate49 继续是唯一前瞻候选且账本 0/0；不得回填、启动第二候选、修改冻结门槛、生成当前评分/选股/仓位/订单或作投资建议。

## Campaign299 离线历史终局（2026-08-25）

Campaign299 不等待新增日线或 16:30，只使用冻结的 2019–2023 Alpha158 设计。唯一高方向因子 `alpha158_close_distribution_upper_tail_asymmetry_20d = (2*MA20-QTLU20-QTLD20)/(QTLU20-QTLD20)` 衡量二十日收盘均值相对 Q20/Q80 中点的上移，并按相同中心分位带宽归一化。公式、方向、窗口、缺失规则、151 项比较顺序、三折、成本与合取门禁均在候选/比较/收益值前冻结。

1,001,507 / 1,001,781 个质量/上市范围股票日可用；覆盖中位/P05 为 `100%/99.742122%`。151 项比较全部通过，最大绝对中位日秩相关 `0.083724`。2021/2022/2023 Rank IC 为 `-0.000995/-0.004262/-0.012414`，normalized return 为 `-24.303166%/-34.444851%/-28.452064%`，10bp 整手收益为 `-5.295866%/-6.000077%/-4.345104%`。复合 normalized/10bp/20bp 收益为 `-64.495644%/-14.846278%/-19.361571%`，最差 normalized 回撤 `-46.599829%`，survivor 为 0，2024–2025 未打开。

10 条值前概念、5 次基础设施失败和 1 个完整因子尝试使 Campaign299 有效尝试数为 16；累计历史尝试 3,084、累计收益读取开发试验 330。因覆盖和全部唯一性通过，重复控制库追加为 `171/152`；追加不表示幸存或投资价值。不得反向、改窗口/公式、阈值化或组合救援。Candidate49 仍是唯一前瞻候选且账本 0/0；本轮无 provider 请求、历史回填、当前评分、选股、仓位、订单或投资建议。

## Campaign300 离线历史终局（2026-08-25）

Campaign300 不等待新增日线或 16:30，只使用冻结的 2019–2023 Alpha158 设计。唯一高方向因子 `alpha158_conditional_return_magnitude_asymmetry_20d = (SUMP20/CNTP20)/((SUMP20/CNTP20)+(SUMN20/CNTN20))` 先用上涨/下跌会话频率归一化对应收益质量，再比较典型上涨日与典型下跌日的幅度。公式、方向、20 日窗口、缺失规则、152 项比较顺序、三折、成本与合取门禁均在候选/比较/收益值前冻结。

1,001,480 / 1,001,781 个质量/上市范围股票日可用；覆盖中位/P05 为 `100%/99.736974%`。152 项比较全部通过，最大绝对中位日秩相关 `0.602999`；与 Campaign299 的相关性为 `0.006729`。2021/2022/2023 Rank IC 为 `-0.004920/-0.016446/-0.011280`，normalized return 为 `-25.227026%/+20.647636%/-23.648362%`，10bp 整手收益为 `-2.024313%/+1.348565%/-3.687437%`。复合 normalized/10bp/20bp 收益为 `-31.121794%/-4.364560%/-8.757700%`，最差 normalized 回撤 `-39.412626%`；2021 整手可负担率 `87.330317%` 也未达 90%。survivor 为 0，2024–2025 未打开。

10 条值前概念、1 次发布基础设施失败和 1 个完整因子尝试使 Campaign300 有效尝试数为 12；累计历史尝试 3,096、累计收益读取开发试验 331。因覆盖和全部唯一性通过，重复控制库追加为 `172/153`；追加不表示幸存或投资价值。不得反向、改窗口/公式、阈值化或组合救援。Candidate49 仍是唯一前瞻候选且账本 0/0；本轮无 provider 请求、历史回填、当前评分、选股、仓位、订单或投资建议。
