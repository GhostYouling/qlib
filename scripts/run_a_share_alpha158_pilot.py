"""Run a low-resource Alpha158 + LightGBM aggregation pilot for A-share data.

The pilot consumes the deterministic main-board and ChiNext samples from the
factor-readiness report.  It establishes that Qlib can train, predict, and
calculate out-of-sample IC on this repository's data without materializing a
full-market factor matrix.  It is a mechanism check, not an investable model.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROVIDER_URI = REPO_ROOT / "data" / "qlib" / "cn_a_share"
DEFAULT_READINESS_REPORT = REPO_ROOT / "data" / "metadata" / "factor_readiness.json"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "metadata" / "alpha158_pilot.json"


def _safe_correlation(frame: pd.DataFrame, method: str) -> float:
    """Return a daily cross-sectional correlation, excluding degenerate days."""

    clean = frame[["score", "label"]].dropna()
    if len(clean) < 3 or clean["score"].nunique() < 2 or clean["label"].nunique() < 2:
        return float("nan")
    return float(clean["score"].corr(clean["label"], method=method))


def calendar_splits(calendar: pd.DatetimeIndex, holdout_days: int) -> dict[str, tuple[pd.Timestamp, pd.Timestamp]]:
    """Build contiguous train/validation/test intervals from one local calendar."""

    if holdout_days < 20:
        raise ValueError("--holdout-days must be at least 20")
    required_days = holdout_days * 2 + 120
    if len(calendar) < required_days:
        raise ValueError(f"need at least {required_days} trading days, found {len(calendar)}")
    train_end_index = len(calendar) - holdout_days * 2 - 1
    valid_end_index = len(calendar) - holdout_days - 1
    return {
        "train": (pd.Timestamp(calendar[0]), pd.Timestamp(calendar[train_end_index])),
        "valid": (pd.Timestamp(calendar[train_end_index + 1]), pd.Timestamp(calendar[valid_end_index])),
        "test": (pd.Timestamp(calendar[valid_end_index + 1]), pd.Timestamp(calendar[-1])),
    }


def load_buyable_samples(readiness_report: Path) -> list[str]:
    """Read the accepted main-board and ChiNext sample set from a readiness report."""

    report = json.loads(readiness_report.read_text(encoding="utf-8"))
    if report.get("status") != "passed":
        raise ValueError(f"factor readiness report is not passed: {readiness_report}")
    by_board = report.get("sample", {}).get("by_board", {})
    samples = sorted(set(by_board.get("main", [])) | set(by_board.get("chinext", [])))
    if len(samples) < 6:
        raise ValueError("factor readiness report contains too few main-board/ChiNext samples")
    return samples


def run_pilot(args: argparse.Namespace) -> dict[str, Any]:
    """Train the small baseline and calculate held-out cross-sectional IC."""

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    # Qlib's LGBModel records validation metrics through MLflow.  The pilot
    # intentionally uses Qlib's local file tracker and opts in to the current
    # MLflow compatibility switch rather than creating an external service.
    os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")
    import qlib
    from qlib.contrib.data.handler import Alpha158
    from qlib.contrib.model.gbdt import LGBModel
    from qlib.data import D
    from qlib.data.dataset import DatasetH
    from qlib.data.dataset.handler import DataHandlerLP

    provider_uri = Path(args.provider_uri).expanduser().resolve()
    readiness_report = Path(args.readiness_report).expanduser().resolve()
    if not provider_uri.exists():
        raise FileNotFoundError(f"Qlib provider directory does not exist: {provider_uri}")
    if not readiness_report.exists():
        raise FileNotFoundError(f"factor readiness report does not exist: {readiness_report}")
    samples = load_buyable_samples(readiness_report)

    qlib.init(provider_uri=str(provider_uri), region="cn", kernels=1)
    calendar = pd.DatetimeIndex(D.calendar(start_time=args.start, end_time=args.end, freq="day"))
    if len(calendar) == 0:
        raise ValueError("no local trading days match the requested pilot window")
    splits = calendar_splits(calendar, args.holdout_days)
    train_start, train_end = splits["train"]
    valid_start, valid_end = splits["valid"]
    test_start, test_end = splits["test"]

    handler = Alpha158(
        instruments=samples,
        start_time=train_start,
        end_time=test_end,
        fit_start_time=train_start,
        fit_end_time=train_end,
        infer_processors=[{"class": "Fillna", "kwargs": {"fields_group": "feature"}}],
        learn_processors=[{"class": "DropnaLabel"}],
    )
    dataset = DatasetH(
        handler=handler,
        segments={
            "train": (train_start, train_end),
            "valid": (valid_start, valid_end),
            "test": (test_start, test_end),
        },
    )
    model = LGBModel(
        loss="mse",
        learning_rate=0.05,
        num_leaves=31,
        max_depth=6,
        min_data_in_leaf=20,
        feature_fraction=0.8,
        bagging_fraction=0.8,
        bagging_freq=1,
        num_boost_round=args.num_boost_round,
        early_stopping_rounds=args.early_stopping_rounds,
        num_threads=1,
        verbose=-1,
    )
    model.fit(dataset)

    prediction = model.predict(dataset, segment="test").rename("score")
    labels = dataset.prepare("test", col_set="label", data_key=DataHandlerLP.DK_L)
    if isinstance(labels, pd.DataFrame):
        label = labels.iloc[:, 0].rename("label")
    else:
        label = labels.rename("label")
    evaluation = pd.concat([prediction, label], axis=1).dropna()
    by_day = evaluation.groupby(level="datetime", sort=True)
    ic = by_day.apply(_safe_correlation, method="pearson").dropna()
    rank_ic = by_day.apply(_safe_correlation, method="spearman").dropna()
    if ic.empty or rank_ic.empty:
        raise ValueError("pilot generated no valid cross-sectional IC observations")

    return {
        "status": "completed",
        "purpose": "mechanism_validation_only",
        "provider_uri": str(provider_uri),
        "readiness_report": str(readiness_report),
        "samples": samples,
        "segments": {
            name: {"start": start.date().isoformat(), "end": end.date().isoformat()}
            for name, (start, end) in splits.items()
        },
        "model": {
            "class": "LGBModel",
            "features": 158,
            "num_boost_round": args.num_boost_round,
            "early_stopping_rounds": args.early_stopping_rounds,
            "num_threads": 1,
        },
        "test": {
            "rows": len(evaluation),
            "trading_days_with_ic": len(ic),
            "ic_mean": float(ic.mean()),
            "ic_std": float(ic.std(ddof=0)),
            "icir": float(ic.mean() / ic.std(ddof=0)) if ic.std(ddof=0) else None,
            "rank_ic_mean": float(rank_ic.mean()),
            "rank_ic_std": float(rank_ic.std(ddof=0)),
            "rank_icir": float(rank_ic.mean() / rank_ic.std(ddof=0)) if rank_ic.std(ddof=0) else None,
        },
        "limitations": [
            "This pilot uses 16 readiness-test samples, so its IC is not evidence of an investable strategy.",
            "A passed readiness report now requires restoration factors, but this small pilot still does not simulate exact limit queues, suspensions, or fills.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI), help="local Qlib provider directory")
    parser.add_argument("--readiness-report", default=str(DEFAULT_READINESS_REPORT), help="passed readiness JSON report")
    parser.add_argument("--start", default="2024-01-01", help="first pilot date")
    parser.add_argument("--end", help="last pilot date; defaults to the local calendar's final date")
    parser.add_argument("--holdout-days", type=int, default=120, help="trading days in each validation/test segment")
    parser.add_argument("--num-boost-round", type=int, default=200, help="maximum LightGBM boosting rounds")
    parser.add_argument("--early-stopping-rounds", type=int, default=30, help="LightGBM validation patience")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="JSON result path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_pilot(args)
    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
