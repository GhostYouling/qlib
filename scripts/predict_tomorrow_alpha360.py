# -*- coding: utf-8 -*-
import os
import pandas as pd
import qlib
from qlib.data import D
from qlib.utils import init_instance_by_config
from qlib.workflow import R

# ======== 你可以改的参数 ========
PROVIDER_URI = os.path.expanduser("~/.qlib/qlib_data/cn_data")
REGION = "cn"
INSTRUMENTS = "csi300"   # 与训练时一致（常用 csi300 / csi500）
TOP_N = 50               # 多空利差的 N
EXP_ID = "110540802959754721"                 # 你的 Experiment ID（日志里有）
REC_ID = "a8ed4b0d665a425183e0c84dbf51b91b"   # 你的 Recorder ID（日志里有）

# ======== 初始化 Qlib ========
qlib.init(provider_uri=PROVIDER_URI, region=REGION)

# 拿到数据中最后一个交易日（在这个日的特征上出分，对应下一交易日的收益）
cal = D.calendar(freq="day")
last_trading_day = str(cal[-1])

# 用与训练一致的 Alpha360 配置（时间窗口放宽到包含 last_trading_day）
dataset_conf = {
    "class": "DatasetH",
    "module_path": "qlib.data.dataset",
    "kwargs": {
        "handler": {
            "class": "Alpha360",
            "module_path": "qlib.contrib.data.handler",
            "kwargs": {
                "start_time": "2005-01-01",
                "end_time": "2099-12-31",
                "fit_start_time": "2005-01-01",
                "fit_end_time": last_trading_day,
                "instruments": INSTRUMENTS,
            },
        },
        # 只在 last_trading_day 出一次分（这一次分数对应“下一交易日”的收益预测）
        "segments": {"test": (last_trading_day, last_trading_day)},
    },
}

with R.start(experiment_id=EXP_ID, recorder_id=REC_ID):
    rec = R.get_recorder()
    # 加载已训练好的模型（一般名为 model.pkl；若报错，可在 rec.artifacts 里查看实际文件名）
    model = rec.load_object("model.pkl")

    dataset = init_instance_by_config(dataset_conf)

    # 预测：得到 (datetime, instrument) MultiIndex 的 Series
    pred = model.predict(dataset).rename("score").to_frame()

# 取这天（last_trading_day）的横截面分数
dt = pred.index.get_level_values(0).max()
today_scores = pred.xs(dt)  # DataFrame: index=instrument, col=score
s = today_scores["score"]

# === 指数层级聚合（等权） ===
eq_ret = float(s.mean())

# === 多空利差（TopN - BottomN） ===
top_mean = float(s.nlargest(TOP_N).mean())
bot_mean = float(s.nsmallest(TOP_N).mean())
ls_spread = top_mean - bot_mean

# 简单方向判断
if eq_ret > 0 and ls_spread > 0:
    direction = "看多"
elif eq_ret < 0 and ls_spread < 0:
    direction = "看空"
else:
    direction = "中性"

# 保存明日交易用的股票列表（可选）
out_dir = "./pred_outputs"
os.makedirs(out_dir, exist_ok=True)
s.sort_values(ascending=False).to_csv(os.path.join(out_dir, f"pred_{dt}.csv"), header=["score"])

print(f"基于 {dt} 的特征（对应下一交易日）的聚合结果：")
print(f"- 指数等权预期收益（均值score）: {eq_ret:.6f}")
print(f"- 多空利差（Top{TOP_N}-Bottom{TOP_N}）: {ls_spread:.6f}")
print(f"- 明日市场方向（规则版）: {direction}")
print(f"- 明日候选（由高到低）已保存：{os.path.join(out_dir, f'pred_{dt}.csv')}")
