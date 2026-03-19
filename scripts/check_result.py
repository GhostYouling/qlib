# check_result.py
# 批量为“未生成图表”的 run 生成 charts/data/artifacts；按 日期/Experiment_RunID 分类
import os, re, json, pickle, sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use("Agg")  # 无界面环境也能画图
import matplotlib.pyplot as plt
import pandas as pd

from mlflow.tracking import MlflowClient
from mlflow.entities import ViewType

# === 1) 配置 ===
TRACKING_CANDIDATES = [
    "file:///Users/niyufei/Coding/qlib/examples/mlruns",
    "file:///Users/niyufei/.qlib/exp",
]
OUTROOT = Path.cwd() / "qlib_outputs"
TZ = ZoneInfo("America/Los_Angeles")
MAX_RESULTS = 50000  # 关键修正：MLflow 的最大允许值

# === 2) 小工具 ===
def safe_name(s: str) -> str:
    import re as _re
    return _re.sub(r"[^A-Za-z0-9_.-]+", "_", s or "unknown")

def list_all_artifacts(client: MlflowClient, run_id: str, root=""):
    out, stack = [], [root]
    while stack:
        p = stack.pop()
        for it in client.list_artifacts(run_id, p or None):
            if it.is_dir:
                stack.append(it.path)
            else:
                out.append(it.path)
    return sorted(out)

def find_first(paths, *names):
    for name in names:
        for p in paths:
            if p.endswith("/" + name) or p == name:
                return p
    return None

def download_pkl(client: MlflowClient, run_id: str, rel_path: str, to_dir: Path):
    local_path = client.download_artifacts(run_id, rel_path, str(to_dir))
    with open(local_path, "rb") as f:
        return pickle.load(f), Path(local_path)

def save_fig(fig, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"[saved] {path}")

def plot_cum_dd_roll(ret_s: pd.Series, charts_dir: Path, prefix: str):
    s = pd.to_numeric(ret_s, errors="coerce").fillna(0)
    cum = (1 + s).cumprod()
    dd = cum / cum.cummax() - 1
    roll_ir = s.rolling(60).mean() / s.rolling(60).std()

    fig = plt.figure(); plt.plot(cum.index, cum.values); plt.title(f"{prefix} Cumulative Return")
    save_fig(fig, charts_dir / f"{prefix.lower()}_cum_return.png")

    fig = plt.figure(); plt.plot(dd.index, dd.values); plt.title(f"{prefix} Drawdown")
    save_fig(fig, charts_dir / f"{prefix.lower()}_drawdown.png")

    fig = plt.figure(); plt.plot(roll_ir.index, roll_ir.values); plt.title(f"{prefix} Rolling IR (60D)")
    save_fig(fig, charts_dir / f"{prefix.lower()}_rolling_ir_60d.png")

def df_from_report_like(obj):
    if isinstance(obj, pd.DataFrame):
        return obj
    if isinstance(obj, dict):
        for v in obj.items():
            vv = v[1] if isinstance(v, tuple) else v
            if isinstance(vv, pd.DataFrame):
                return vv
    return None

def has_charts(charts_dir: Path):
    return charts_dir.exists() and any(charts_dir.glob("*.png"))

def export_positions_sample(pos_obj, data_dir: Path):
    """尽力导出某日Top50持仓；结构不合预期时跳过不报错"""
    try:
        if isinstance(pos_obj, dict) and pos_obj:
            dates = sorted(pos_obj.keys())
            d0 = dates[0]
            val = pos_obj[d0]
            if isinstance(val, pd.DataFrame):
                df = val
            else:
                try:
                    df = pd.DataFrame(val)
                except Exception:
                    try:
                        df = pd.DataFrame([vars(val)])
                    except Exception:
                        print("positions 结构未知，跳过导出。")
                        return
            last_col = df.columns[-1]
            df_top = df.sort_values(last_col, ascending=False).head(50)
            out_csv = data_dir / f"positions_{str(d0).replace('-', '').replace(':','')}_top50.csv"
            df_top.to_csv(out_csv, index=False)
            print(f"[saved] {out_csv}")
    except Exception as e:
        print("导出持仓失败（已忽略）：", e)

# === 3) 主流程 ===
def process_tracking_uri(uri: str, force: bool = False):
    os.environ["MLFLOW_TRACKING_URI"] = uri
    client = MlflowClient(tracking_uri=uri)

    exps = client.search_experiments()
    print(f"\n== URI: {uri} | experiments: {len(exps)}")

    for exp in exps:
        # 修正：把 max_results 控制到 50000（或更小）
        runs = client.search_runs(
            [exp.experiment_id],
            run_view_type=ViewType.ACTIVE_ONLY,
            order_by=["attributes.start_time ASC"],
            max_results=MAX_RESULTS,
        )
        if not runs:
            continue

        for run in runs:
            status = str(run.info.status).upper()
            if status not in ("FINISHED", "SUCCEEDED"):
                continue

            run_id = run.info.run_id
            start_dt = datetime.fromtimestamp(run.info.start_time / 1000, TZ) if run.info.start_time else datetime.now(TZ)
            date_str = start_dt.strftime("%Y-%m-%d")

            run_dir = OUTROOT / date_str / f"{safe_name(exp.name)}_{run_id}"
            arts_dir = run_dir / "artifacts"
            charts_dir = run_dir / "charts"
            data_dir = run_dir / "data"
            for d in (arts_dir, charts_dir, data_dir):
                d.mkdir(parents=True, exist_ok=True)

            if has_charts(charts_dir) and not force:
                print(f"skip run {run_id} (charts already exist)")
                continue

            print(f"\n-- processing run: {run_id} | exp: {exp.name} | date: {date_str}")

            # 1) 工件清单
            paths = list_all_artifacts(client, run_id)
            if not paths:
                print("  (no artifacts)")
                continue

            # 2) pred.pkl -> pred_head.csv
            pred_rel = find_first(paths, "pred.pkl")
            if pred_rel:
                pred_obj, pred_local = download_pkl(client, run_id, pred_rel, arts_dir)
                try:
                    pred_obj.reset_index().head(100).to_csv(data_dir / "pred_head.csv", index=False)
                    print(f"[saved] {data_dir / 'pred_head.csv'}")
                except Exception as e:
                    print("pred 预览失败：", e)

            # 3) 报表（Strategy & Excess）
            report_rel = (find_first(paths, "report_normal_1day.pkl")
                          or find_first(paths, "report_1day.pkl")
                          or find_first(paths, "report.pkl"))

            got_any_curve = False
            if report_rel:
                report_obj, report_local = download_pkl(client, run_id, report_rel, arts_dir)
                df = df_from_report_like(report_obj)
                if df is not None:
                    # strategy 优先列
                    strategy_cols = ["strategy_return", "ret", "return", "port_ret"]
                    excess_cols   = ["excess_return", "excess", "excess_ret", "alpha", "exret"]

                    sc = next((c for c in strategy_cols if c in df.columns), None)
                    if sc:
                        plot_cum_dd_roll(df[sc], charts_dir, "strategy"); got_any_curve = True
                    ec = next((c for c in excess_cols if c in df.columns), None)
                    if ec:
                        plot_cum_dd_roll(df[ec], charts_dir, "excess"); got_any_curve = True
                else:
                    print("report_* 不是 DataFrame，跳过画图。")

            # 4) 若还没拿到曲线，尝试 port_analysis_1day.pkl
            if not got_any_curve:
                pa_rel = find_first(paths, "port_analysis_1day.pkl")
                if pa_rel:
                    pa_obj, pa_local = download_pkl(client, run_id, pa_rel, arts_dir)
                    if isinstance(pa_obj, dict):
                        strategy_cols = ["strategy_return", "ret", "return", "port_ret"]
                        excess_cols   = ["excess_return", "excess", "excess_ret", "alpha", "exret"]
                        for v in pa_obj.values():
                            if isinstance(v, pd.DataFrame):
                                sc = next((c for c in strategy_cols if c in v.columns), None)
                                ec = next((c for c in excess_cols if c in v.columns), None)
                                if sc:
                                    plot_cum_dd_roll(v[sc], charts_dir, "strategy"); got_any_curve = True
                                if ec:
                                    plot_cum_dd_roll(v[ec], charts_dir, "excess"); got_any_curve = True
                                if got_any_curve: break

            # 5) IC / RIC
            for name, out_png in [("ic.pkl", "ic.png"), ("ric.pkl", "ric.png")]:
                rel = find_first(paths, name)
                if rel:
                    obj, local = download_pkl(client, run_id, rel, arts_dir)
                    s = obj.squeeze() if isinstance(obj, (pd.Series, pd.DataFrame)) else None
                    if isinstance(s, pd.Series):
                        fig = plt.figure(); plt.plot(s.index, s.values); plt.title(name.replace(".pkl","").upper())
                        save_fig(fig, charts_dir / out_png)

            # 6) 示例持仓导出（尽力而为）
            pos_rel = (find_first(paths, "positions_normal_1day.pkl")
                       or find_first(paths, "positions_1day.pkl"))
            if pos_rel:
                pos_obj, pos_local = download_pkl(client, run_id, pos_rel, arts_dir)
                export_positions_sample(pos_obj, data_dir)

            # 7) manifest
            manifest = {
                "tracking_uri": uri,
                "experiment": {"id": exp.experiment_id, "name": exp.name},
                "run": {
                    "id": run_id,
                    "start_time": run.info.start_time,
                    "end_time": run.info.end_time,
                    "status": run.info.status,
                },
                "dirs": {"root": str(run_dir), "artifacts": str(arts_dir), "charts": str(charts_dir), "data": str(data_dir)},
                "sources": {
                    "pred": pred_rel,
                    "report_like": report_rel,
                    "port_analysis": 'pa_rel' in locals() and pa_rel or None,
                    "ic": find_first(paths, "ic.pkl"),
                    "ric": find_first(paths, "ric.pkl"),
                    "positions": pos_rel,
                },
            }
            (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            print(f"done: {run_dir}")

def main():
    force = "--force" in sys.argv
    OUTROOT.mkdir(parents=True, exist_ok=True)
    any_found = False
    for uri in TRACKING_CANDIDATES:
        try:
            process_tracking_uri(uri, force=force)
            any_found = True
        except Exception as e:
            print(f"[warn] failed on {uri}: {e}")
    if not any_found:
        print("未在候选 tracking 目录发现可用 run。请检查 TRACKING_CANDIDATES 是否包含你的 mlruns 路径。")

if __name__ == "__main__":
    main()
