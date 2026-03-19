# export_from_run.py
import os, json, argparse, traceback
from pathlib import Path

def export_with_qlib(run_id, tracking_uri, out_dir):
    import qlib
    from qlib.workflow import R
    # 1) 先初始化 Qlib（用你本地的 CN 数据目录）
    qlib.init(provider_uri=os.path.expanduser("~/.qlib/qlib_data/cn_data"), region="cn")
    # 2) 绑定 MLflow 跟踪目录
    R.set_uri(tracking_uri)
    rec = R.get_recorder(rec_id=run_id, experiment_name="workflow")
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    print("Artifacts 列表：")
    for a in rec.list_artifacts():
        print(" -", a)

    # 常见的关键信息都拉一下（有啥拉啥，都用 try 包起来）
    for art in [
        "config",             # 当时渲染后的完整 YAML（若存在）
        "task",               # task_config.json 等（若存在）
        "params.pkl",         # 模型超参
        "code_cached.txt",    # 代码快照（若存在）
        "code_diff.txt",      # 代码 diff（若存在）
    ]:
        try:
            rec.download_artifacts(art, out_dir)
            print(f"[ok] {art} -> {out_dir}/{art if '/' not in art else ''}")
        except Exception as e:
            print(f"[skip] {art}: {e}")

    # 把 MLflow 的元信息也存一份，便于复现
    try:
        meta = {
            "run_id": rec.id,
            "experiment_name": rec.experiment_name,
            "params": rec.list_logged_params(),
            "metrics": rec.list_logged_metrics(),
            "tags": rec.list_tags(),
        }
        with open(os.path.join(out_dir, "mlflow_meta.json"), "w") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2, default=str)
        print(f"[ok] 写出 {out_dir}/mlflow_meta.json")
    except Exception as e:
        print(f"[skip] meta: {e}")

def export_with_mlflow(run_id, tracking_uri, out_dir):
    from mlflow.tracking import MlflowClient
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    client = MlflowClient(tracking_uri=tracking_uri)
    run = client.get_run(run_id)

    # 元信息
    with open(os.path.join(out_dir, "mlflow_meta.json"), "w") as f:
        json.dump({
            "run_id": run_id,
            "experiment_id": run.info.experiment_id,
            "status": run.info.status,
            "start_time": run.info.start_time,
            "end_time": run.info.end_time,
            "params": run.data.params,
            "tags": run.data.tags,
            "metrics": run.data.metrics,
        }, f, ensure_ascii=False, indent=2, default=str)
    print(f"[ok] 写出 {out_dir}/mlflow_meta.json")

    # 拉取常见 artifacts
    for art in ["config", "task", "params.pkl", "code_cached.txt", "code_diff.txt"]:
        try:
            local = client.download_artifacts(run_id, art, out_dir)
            print(f"[ok] {art} -> {local}")
        except Exception as e:
            print(f"[skip] {art}: {e}")

    # 如果没有 config，但 task 下有 JSON，顺手拼个可复现的 YAML 草稿
    try:
        import glob, yaml
        task_jsons = glob.glob(os.path.join(out_dir, "task", "**", "*.json"), recursive=True)
        for p in task_jsons:
            with open(p, "r") as f:
                j = json.load(f)
            if isinstance(j, dict) and ("dataset" in j and "model" in j):
                frozen = {"task": j}
                with open(os.path.join(out_dir, "frozen_from_task.yaml"), "w") as f:
                    yaml.safe_dump(frozen, f, allow_unicode=True, sort_keys=False)
                print(f"[ok] 写出 {out_dir}/frozen_from_task.yaml（从 {p} 还原）")
                break
    except Exception as e:
        print(f"[skip] 还原 YAML: {e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_id", required=True, help="要导出的 MLflow run_id（Recorder ID）")
    parser.add_argument("--tracking_uri", default="file:///Users/niyufei/Coding/qlib/examples/mlruns",
                        help="MLflow 跟踪目录（默认指向 examples/mlruns）")
    parser.add_argument("--out_root", default="/Users/niyufei/Coding/qlib/scripts/qlib_outputs",
                        help="输出根目录")
    args = parser.parse_args()

    out_dir = os.path.join(args.out_root, f"recovered_{args.run_id}")
    print(f"Tracking URI: {args.tracking_uri}")
    print(f"Run ID      : {args.run_id}")
    print(f"Out Dir     : {out_dir}")

    # 先尝试用 Qlib 的 R，失败再回退到 MLflow
    try:
        export_with_qlib(args.run_id, args.tracking_uri, out_dir)
        print(f"\n✅ 完成（Qlib 模式）。输出目录：{out_dir}")
    except Exception as e:
        print("\n[warn] Qlib 导出失败，回退到纯 MLflow：")
        traceback.print_exc()
        export_with_mlflow(args.run_id, args.tracking_uri, out_dir)
        print(f"\n✅ 完成（MLflow 模式）。输出目录：{out_dir}")

if __name__ == "__main__":
    main()
