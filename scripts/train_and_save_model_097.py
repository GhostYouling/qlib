# scripts/train_and_save_model_097.py
import os
from pathlib import Path
import argparse
import ruamel.yaml as ry
import qlib
from qlib.workflow import R
from qlib.utils import init_instance_by_config

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--yaml",
        default="/Users/niyufei/Coding/qlib/examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha360.yaml",
        help="YAML 的绝对路径",
    )
    ap.add_argument(
        "--tracking_uri",
        default="file:///Users/niyufei/Coding/qlib/examples/mlruns",
        help="MLflow 跟踪目录（file:// 开头的绝对路径）",
    )
    args = ap.parse_args()

    qlib.init(provider_uri=os.path.expanduser("~/.qlib/qlib_data/cn_data"), region="cn")
    R.set_uri(args.tracking_uri)

    yaml_path = Path(args.yaml)
    cfg = ry.YAML(typ="safe").load(yaml_path.read_text())

    task = cfg["task"]
    model_cfg   = task["model"]
    dataset_cfg = task["dataset"]

    model   = init_instance_by_config(model_cfg)
    dataset = init_instance_by_config(dataset_cfg)

    with R.start(experiment_name="workflow"):
        model.fit(dataset)
        R.save_objects(trained_model=model)
        print("✅ run_id =", R.get_recorder().id)

if __name__ == "__main__":
    main()
