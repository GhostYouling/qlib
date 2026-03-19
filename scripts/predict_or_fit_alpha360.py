# -*- coding: utf-8 -*-
import os
import multiprocessing as mp

def main():
    import qlib
    from qlib.data import D
    from qlib.utils import init_instance_by_config
    from qlib.workflow import R
    # ↓↓↓ 尝试把 joblib 并行改成“线程”，并取消 maxtasksperchild，避免再次 spawn
    try:
        from qlib.config import C
        C.joblib_backend = "threading"   # 不用多进程
        C.maxtasksperchild = None
        # 有些版本有 num_workers；没有就忽略
        if hasattr(C, "num_workers"):
            C.num_workers = 0
    except Exception:
        pass

    # 也可再保险：限制底层线程数，避免 MKL/OMP 抢线程（不会影响功能）
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    # 对于 mac，一些科学库在 fork 下需要这个（可选）
    os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")

    # ========= 可改参数 =========
    PROVIDER_URI = os.path.expanduser("~/.qlib/qlib_data/cn_data")
    REGION = "cn"
    INSTRUMENTS = "csi300"
    TOP_N = 50
    NUM_BOOST_ROUND = 200
    EARLY_STOPPING = 50

    qlib.init(provider_uri=PROVIDER_URI, region=REGION)

    cal = D.calendar(freq="day")
    last_trading_day = str(cal[-1])

    train_start = "2008-01-01"
    valid_end_idx = -2
    valid_start_idx = max(-61, -int(len(cal) * 0.02) - 1)
    valid_start = str(cal[valid_start_idx])
    valid_end = str(cal[valid_end_idx])
    test_start = last_trading_day
    test_end = last_trading_day

    dataset_conf = {
        "class": "DatasetH",
        "module_path": "qlib.data.dataset",
        "kwargs": {
            "handler": {
                "class": "Alpha360",
                "module_path": "qlib.contrib.data.handler",
                "kwargs": {
                    "start_time": train_start,
                    "end_time": "2099-12-31",
                    "fit_start_time": train_start,
                    "fit_end_time": last_trading_day,
                    "instruments": INSTRUMENTS,
                },
            },
            "segments": {
                "train": (train_start, valid_start),
                "valid": (valid_start, valid_end),
                "test": (test_start, test_end),
            },
        },
    }

    model_conf = {
        "class": "LGBModel",
        "module_path": "qlib.contrib.model.gbdt",
        "kwargs": {
            "loss": "mse",
            "colsample_bytree": 0.8879,
            "learning_rate": 0.02,
            "subsample": 0.8789,
            "lambda_l1": 205.6999,
            "lambda_l2": 580.9768,
            "max_depth": 8,
            "num_leaves": 210,
            "min_data_in_leaf": 40,
            "num_boost_round": NUM_BOOST_ROUND,
            "early_stopping_rounds": EARLY_STOPPING,
            "verbose": -1,
        },
    }

    with R.start(experiment_name="alpha360_lgb_predict", recorder_name=None):
        recorder = R.get_recorder()
        dataset = init_instance_by_config(dataset_conf)
        model = init_instance_by_config(model_conf)

        model.fit(dataset)

        pred = model.predict(dataset).rename("score").to_frame()
        dt = pred.index.get_level_values(0).max()
        scores = pred.xs(dt)["score"]

        eq_ret = float(scores.mean())
        top_mean = float(scores.nlargest(TOP_N).mean())
        bot_mean = float(scores.nsmallest(TOP_N).mean())
        ls_spread = top_mean - bot_mean

        if eq_ret > 0 and ls_spread > 0:
            direction = "看多"
        elif eq_ret < 0 and ls_spread < 0:
            direction = "看空"
        else:
            direction = "中性"

        out_dir = "./pred_outputs"
        os.makedirs(out_dir, exist_ok=True)
        outfile = os.path.join(out_dir, f"pred_{dt}.csv")
        scores.sort_values(ascending=False).to_csv(outfile, header=["score"])

        recorder.save_object("model.pkl", model)

        print(f"基于 {dt} 的特征（对应下一交易日）的聚合结果：")
        print(f"- 指数等权预期收益（均值score）: {eq_ret:.6f}")
        print(f"- 多空利差（Top{TOP_N}-Bottom{TOP_N}) : {ls_spread:.6f}")
        print(f"- 明日市场方向（规则版）: {direction}")
        print(f"- 明日候选（由高到低）已保存：{outfile}")
        print(f"- 模型已保存为 recorder 的 'model.pkl'")

if __name__ == "__main__":
    # 对 macOS/Anaconda，优先用 fork，避免 spawn 回放主模块导致“死循环”
    try:
        mp.set_start_method("fork", force=True)
    except RuntimeError:
        # 已经设置过就忽略
        pass
    # 也给 joblib 一个暗示（可选）
    os.environ.setdefault("JOBLIB_START_METHOD", "fork")
    main()
