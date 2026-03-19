# infer_with_saved_model.py
import os
import argparse
import tempfile
import pandas as pd
import qlib
from qlib.workflow import R
from qlib.data import D
from qlib.data.dataset import DatasetH
from qlib.contrib.data.handler import Alpha360

try:
    import ruamel.yaml as ry
    _yaml = ry.YAML(typ="safe")
except Exception:
    import yaml as ry
    _yaml = None  # 会用 yaml.safe_load 兜底

# === 你的环境固定信息 ===
TRACKING_URI = "file:///Users/niyufei/Coding/qlib/examples/mlruns"
DEFAULT_RUN_ID = "88525ef2a49548f8bab96e1d6b51badb"
PROVIDER = os.path.expanduser("~/.qlib/qlib_data/cn_data")

def latest_trading_day():
    cal = D.calendar(start_time="2005-01-01", end_time="2100-01-01", freq="day")
    return str(pd.Timestamp(cal[-1]).date())

def _safe_yaml_load(text: str):
    if _yaml is not None:
        return _yaml.load(text)
    import yaml
    return yaml.safe_load(text)

def try_load_processors_from_run(rec):
    """
    从 run 的 artifacts 里尝试还原训练时的 processors。
    成功返回 (learn_processors, infer_processors)，失败返回 (None, None)。
    """
    # 常见文件名尝试（不同版本/脚本产物命名可能不同）
    candidate_names = [
        "config",                # 有时是完整 workflow yaml
        "task",                  # 也可能是 task 片段
        "task.yaml",
        "workflow_config.yaml",
        "workflow.yaml",
    ]
    for name in candidate_names:
        try:
            # 先把 artifact 下载到临时文件/目录
            local_path = rec.download_artifacts(name)
            if not local_path or not os.path.exists(local_path):
                continue

            # 如果是目录，尝试在里面找 *.yaml
            if os.path.isdir(local_path):
                yaml_files = [os.path.join(local_path, f) for f in os.listdir(local_path) if f.endswith((".yml", ".yaml"))]
                if not yaml_files:
                    # 目录里没 yml，就跳过
                    continue
                # 取最像样的一个
                local_path = yaml_files[0]

            with open(local_path, "r", encoding="utf-8") as f:
                cfg = _safe_yaml_load(f.read())

            # 兼容不同层级：找 dataset->kwargs->handler->kwargs 下的 processors
            ds = None
            try:
                ds = cfg["task"]["dataset"]["kwargs"]
            except Exception:
                pass
            if ds is None:
                # 有些导出的可能直接是 dataset 片段
                ds = cfg.get("dataset", {}).get("kwargs")

            if not ds:
                continue

            h_kwargs = ds.get("handler", {}).get("kwargs", {})
            learn_procs = h_kwargs.get("learn_processors")
            infer_procs = h_kwargs.get("infer_processors")

            if learn_procs:
                return learn_procs, (infer_procs or None)
        except Exception:
            # 读不到就继续尝试下一个
            continue
    return None, None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", type=str, default=DEFAULT_RUN_ID, help="含已保存模型对象的 run_id")
    parser.add_argument("--day", type=str, default=None, help="出分目标交易日（YYYY-MM-DD），缺省为数据中最后一日")
    parser.add_argument("--inst", type=str, default="csi300", help="标的集合（如 csi300, csi500, all）")
    args = parser.parse_args()

    # 1) init
    qlib.init(provider_uri=PROVIDER, region="cn")
    R.set_uri(TRACKING_URI)
    rec = R.get_recorder(recorder_id=args.run_id, experiment_name="workflow")

    # 2) 加载已落盘模型对象
    model = None
    for name in ("trained_model", "model"):
        try:
            model = rec.load_object(name)
            if model is not None:
                print(f"[ok] 已加载模型对象：{name}")
                break
        except Exception:
            pass
    if model is None:
        raise RuntimeError("该 run 没有可加载的模型对象（常见名：trained_model / model）。请换一个含模型的 run，或重训时确保模型落盘。")

    # 3) 目标交易日
    target_day = args.day or latest_trading_day()
    print("最后训练日为:", target_day)

    # 4) 复原训练时的 processors；兜底：推理阶段对 feature 做 CSRankNorm
    learn_processors, infer_processors = try_load_processors_from_run(rec)
    if learn_processors is None:
        # 兜底策略：训练阶段通常至少有 DropnaLabel；推理阶段务必对 feature 做 CSRankNorm
        learn_processors = [{"class": "DropnaLabel"}]
        infer_processors = [{"class": "CSRankNorm", "kwargs": {"fields_group": "feature"}}]
        print("[info] 未能从 artifacts 还原 processors，采用兜底：learn=DropnaLabel；infer=CSRankNorm(feature)")
    else:
        # 如果训练时没配 infer_processors，我们在推理阶段补上对 feature 的 CSRankNorm（多数范式如此）
        if not infer_processors:
            infer_processors = [{"class": "CSRankNorm", "kwargs": {"fields_group": "feature"}}]
            print("[info] 已复原训练 processors；推理阶段补充 CSRankNorm(feature) 以对齐训练尺度。")
        else:
            print("[info] 已从 run 复原 processors：learn/infer 将与训练一致。")

    # 5) handler 与训练尽量一致（时间上 end_time 要 >= 目标日）
    handler = Alpha360(
        start_time="2008-01-01",
        end_time=target_day,            # >= 目标日
        fit_start_time="2008-01-01",
        fit_end_time="2019-12-31",     # 你的训练截止
        instruments=args.inst,
        infer_processors=infer_processors,
        learn_processors=learn_processors,
        label=["Ref($close, -2) / Ref($close, -1) - 1"],
    )

    dataset = DatasetH(handler=handler, segments={"test": (target_day, target_day)})

    # 6) 预测
    pred_any = model.predict(dataset)  # 0.9.7 通常是 Series: MultiIndex=[datetime, instrument]
    if isinstance(pred_any, pd.DataFrame):
        pred = pred_any["score"] if "score" in pred_any.columns else pred_any.iloc[:, 0]
    else:
        pred = pred_any

    # 切片到该日
    day_idx = pd.Timestamp(target_day)
    available_days = pred.index.get_level_values("datetime").unique()
    if day_idx not in available_days:
        raise ValueError(f"预测结果中没有 {target_day} 这天的数据；可用日期：{str(available_days.min().date())}~{str(available_days.max().date())}")

    pred_day = pred.xs(day_idx, level="datetime").astype(float)  # index=instrument

    # 自检
    print("样本数（股票数）:", pred_day.shape[0])
    print("预测值唯一个数:", pred_day.nunique())
    print("预测值概览:", pred_day.describe().to_dict())
    if pred_day.nunique() == 1:
        print("[warn] 该日所有股票预测值相同。八成是训练/推理特征尺度不一致导致。已在推理端启用 CSRankNorm(feature)；若仍相同，请检查训练 YAML 是否也对 feature 做了 CSRankNorm。")

    # 7) 保存
    out_dir = os.path.join(os.path.dirname(__file__) or ".", "qlib_outputs", f"preds_{args.run_id}")
    os.makedirs(out_dir, exist_ok=True)
    out_pkl = os.path.join(out_dir, f"pred_{target_day}.pkl")
    out_csv = os.path.join(out_dir, f"pred_{target_day}.csv")

    pred_day.sort_values(ascending=False).to_frame("score").to_pickle(out_pkl)
    pred_day.sort_values(ascending=False).reset_index().rename(columns={"index": "instrument", 0: "score"}).to_csv(out_csv, index=False)

    print(f"[ok] {target_day} 共 {len(pred_day)} 条打分")
    print("[head]")
    print(pred_day.sort_values(ascending=False).head())
    print(f"[saved] {out_pkl}")
    print(f"[saved] {out_csv}")

if __name__ == "__main__":
    main()
