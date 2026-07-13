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

若策略目标是约 5 个交易日的快进快出、以量价关系为主，同时只在具备正向业绩基础的公司中选股，请使用可复现的研究脚本。它先下载带公告日期的年度 ROE、净利润、营收同比和净利润同比，再运行五个预先声明的候选因子组合：突破、量能加速、回撤反转、趋势内回撤与均衡组合。

```bash
python scripts/a_share_short_horizon_factor_research.py sync-fundamentals \
  --start-year 2022 --end-year 2025
python scripts/a_share_short_horizon_factor_research.py run
```

每个候选组合会在 `data/experiments/short_horizon/` 写入一个独立 JSON；同一批运行另有一个 `*_study.json` 汇总文件。记录包含因子权重、年报文件哈希、股票池、成本、发展期/测试期切分以及净收益、波动、回撤和胜率。候选组合只按 `2025-12-31` 以前的发展期结果选择，之后的测试期不会参与选优。

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

本机时区与中国大陆一致。下列命令会安装两个 `launchd` 用户任务：工作日 18:30 增量更新，以及周五 20:00 的全量复权校正。

```bash
python scripts/install_a_share_launchd.py install
python scripts/install_a_share_launchd.py status
```

日志在 `data/logs/`。需要移除定时任务时：

```bash
python scripts/install_a_share_launchd.py uninstall
```

定时任务不在休眠的电脑上补跑；若错过一次，手动执行 `sync` 即可恢复。若将来换成需要登录的专业数据服务，不要把令牌写进 YAML 或 Git；由系统钥匙串、环境变量或本地 `.env`（已忽略）提供即可。
