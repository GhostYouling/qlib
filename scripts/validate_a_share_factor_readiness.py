"""Validate that the local A-share data can produce Qlib Alpha158 features.

This is deliberately a small, deterministic acceptance test rather than a
full-market feature materialization.  It checks representative main-board,
ChiNext, and STAR stocks over a recent window, so it is safe to run on a
developer laptop before allocating memory and disk to model training.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROVIDER_URI = REPO_ROOT / "data" / "qlib" / "cn_a_share"
DEFAULT_REPORT_PATH = REPO_ROOT / "data" / "metadata" / "factor_readiness.json"
FACTOR_UNIVERSE = "factor_main_chinext_star"
BUYABLE_UNIVERSE = "buyable_main_chinext"
RAW_FIELDS = ("$open", "$high", "$low", "$close", "$volume", "$vwap")
REQUIRED_BOARDS = ("main", "chinext", "star")


def classify_board(instrument: str) -> str | None:
    """Return the supported A-share board for a Qlib-format instrument."""

    code = instrument.upper()[-6:]
    if code.startswith(("300", "301")):
        return "chinext"
    if code.startswith(("688", "689")):
        return "star"
    if code.startswith(("600", "601", "603", "605", "000", "001", "002", "003")):
        return "main"
    return None


def evenly_spaced(items: Iterable[str], count: int) -> list[str]:
    """Select a deterministic spread across a sorted universe."""

    values = list(items)
    if count <= 0 or not values:
        return []
    if len(values) <= count:
        return values
    if count == 1:
        return [values[len(values) // 2]]
    indexes = [round(position * (len(values) - 1) / (count - 1)) for position in range(count)]
    return [values[index] for index in indexes]


def select_full_window_sample(
    instrument_spans: dict[str, list[tuple[pd.Timestamp, pd.Timestamp]]],
    start: pd.Timestamp,
    end: pd.Timestamp,
    samples_per_board: int,
) -> tuple[list[str], dict[str, list[str]]]:
    """Pick board-balanced instruments whose listed range covers the test window."""

    by_board: dict[str, list[str]] = {board: [] for board in REQUIRED_BOARDS}
    for instrument, spans in instrument_spans.items():
        covers_window = any(pd.Timestamp(begin) <= start and pd.Timestamp(finish) >= end for begin, finish in spans)
        board = classify_board(instrument)
        if covers_window and board in by_board:
            by_board[board].append(instrument)
    selected = {board: evenly_spaced(sorted(values), samples_per_board) for board, values in by_board.items()}
    return sorted(instrument for values in selected.values() for instrument in values), selected


def _coverage(frame: pd.DataFrame) -> dict[str, float]:
    """Calculate finite-value coverage by column in a JSON-safe shape."""

    if frame.empty:
        return {column: 0.0 for column in frame.columns}
    values = np.isfinite(frame.to_numpy(dtype=float, copy=False))
    return {column: float(values[:, index].mean()) for index, column in enumerate(frame.columns)}


def _tail_excluded_label_coverage(frame: pd.DataFrame, label_name: str) -> float:
    """Exclude each instrument's final two rows, where the 2-day-ahead label is undefined."""

    evaluation_index = frame.groupby(level="instrument", sort=False).head(-2).index
    if len(evaluation_index) == 0:
        return 0.0
    label = frame.loc[evaluation_index, label_name]
    return float(np.isfinite(label.to_numpy(dtype=float, copy=False)).mean())


def _validate_raw_prices(raw: pd.DataFrame) -> dict[str, int]:
    """Count impossible OHLCV relationships while preserving missingness separately."""

    return {
        "non_positive_price_rows": int((raw[["$open", "$high", "$low", "$close"]] <= 0).any(axis=1).sum()),
        "high_below_low_rows": int((raw["$high"] < raw["$low"]).sum()),
        "negative_volume_rows": int((raw["$volume"] < 0).sum()),
        "non_positive_vwap_with_volume_rows": int(
            ((raw["$volume"] > 0) & (raw["$vwap"] <= 0)).sum()
        ),
    }


def run_readiness_check(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """Run the feature acceptance test and return its report and process status."""

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    import qlib
    from qlib.contrib.data.handler import Alpha158
    from qlib.data import D
    from qlib.data.dataset.handler import DataHandlerLP

    provider_uri = Path(args.provider_uri).expanduser().resolve()
    if not provider_uri.exists():
        raise FileNotFoundError(f"Qlib provider directory does not exist: {provider_uri}")

    qlib.init(provider_uri=str(provider_uri), region="cn", kernels=1)
    calendar = D.calendar(start_time=args.start, end_time=args.end, freq="day")
    if len(calendar) < 80:
        raise ValueError("the validation window must contain at least 80 trading days for Alpha158")
    start, end = pd.Timestamp(calendar[0]), pd.Timestamp(calendar[-1])

    factor_spans = D.list_instruments(
        instruments=D.instruments(FACTOR_UNIVERSE), start_time=start, end_time=end, as_list=False
    )
    samples, samples_by_board = select_full_window_sample(
        factor_spans, start, end, args.samples_per_board
    )
    missing_boards = [board for board, values in samples_by_board.items() if len(values) < args.samples_per_board]
    if missing_boards:
        raise ValueError(f"not enough full-window samples for boards: {', '.join(missing_boards)}")

    raw = D.features(samples, list(RAW_FIELDS), start_time=start, end_time=end, freq="day")
    raw_coverage = _coverage(raw)
    raw_invalid = _validate_raw_prices(raw)

    handler = Alpha158(
        instruments=samples,
        start_time=start,
        end_time=end,
        infer_processors=[],
        learn_processors=[],
    )
    alpha = handler.fetch(data_key=DataHandlerLP.DK_I)
    label_name = "LABEL0"
    if label_name not in alpha:
        raise ValueError("Alpha158 did not return its expected LABEL0 column")
    feature_frame = alpha.drop(columns=[label_name])
    feature_coverage = _coverage(feature_frame)
    label_coverage = _tail_excluded_label_coverage(alpha, label_name)

    buyable = D.list_instruments(
        instruments=D.instruments(BUYABLE_UNIVERSE), start_time=start, end_time=end, as_list=True
    )
    factor = D.list_instruments(
        instruments=D.instruments(FACTOR_UNIVERSE), start_time=start, end_time=end, as_list=True
    )
    buyable_star_count = sum(classify_board(instrument) == "star" for instrument in buyable)
    factor_star_count = sum(classify_board(instrument) == "star" for instrument in factor)

    restoration_factor = D.features(samples, ["$factor"], start_time=start, end_time=end, freq="day")
    restoration_factor_coverage = _coverage(restoration_factor).get("$factor", 0.0)
    warnings: list[str] = []
    if restoration_factor_coverage == 0.0:
        warnings.append(
            "Qlib restoration factor ($factor) is absent. Alpha158 is usable, but Qlib backtests use adjusted-price "
            "execution and cannot yet claim exact A-share 100-share-lot simulation."
        )

    failures: list[str] = []
    if len(feature_frame.columns) != 158:
        failures.append(f"expected 158 Alpha158 features, got {len(feature_frame.columns)}")
    minimum_raw_coverage = min(raw_coverage.values(), default=0.0)
    if minimum_raw_coverage < args.min_raw_coverage:
        failures.append(
            f"raw field coverage {minimum_raw_coverage:.4f} is below {args.min_raw_coverage:.4f}"
        )
    minimum_feature_coverage = min(feature_coverage.values(), default=0.0)
    if minimum_feature_coverage < args.min_feature_coverage:
        failures.append(
            f"Alpha158 feature coverage {minimum_feature_coverage:.4f} is below {args.min_feature_coverage:.4f}"
        )
    if label_coverage < args.min_label_coverage:
        failures.append(f"label coverage {label_coverage:.4f} is below {args.min_label_coverage:.4f}")
    if any(raw_invalid.values()):
        failures.append(f"invalid raw OHLCV relationships: {raw_invalid}")
    if buyable_star_count:
        failures.append(f"buyable universe unexpectedly contains {buyable_star_count} STAR instruments")
    if not factor_star_count:
        failures.append("factor universe contains no STAR instruments")

    report: dict[str, Any] = {
        "status": "passed" if not failures else "failed",
        "provider_uri": str(provider_uri),
        "window": {"start": start.date().isoformat(), "end": end.date().isoformat(), "trading_days": len(calendar)},
        "sample": {"total": len(samples), "by_board": samples_by_board},
        "raw": {"rows": len(raw), "coverage": raw_coverage, "invalid_rows": raw_invalid},
        "alpha158": {
            "rows": len(alpha),
            "feature_count": len(feature_frame.columns),
            "minimum_feature_coverage": minimum_feature_coverage,
            "label_coverage_excluding_final_two_days": label_coverage,
        },
        "universes": {
            "buyable_main_chinext": len(buyable),
            "buyable_star_count": buyable_star_count,
            "factor_main_chinext_star": len(factor),
            "factor_star_count": factor_star_count,
        },
        "restoration_factor_coverage": restoration_factor_coverage,
        "warnings": warnings,
        "failures": failures,
    }
    return report, 0 if not failures else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI), help="local Qlib provider directory")
    parser.add_argument("--start", default="2024-01-01", help="first test date (default: 2024-01-01)")
    parser.add_argument("--end", help="last test date; defaults to the local calendar's final date")
    parser.add_argument("--samples-per-board", type=int, default=8, help="deterministic samples from main, ChiNext, STAR")
    parser.add_argument("--min-raw-coverage", type=float, default=0.995, help="minimum finite coverage for raw fields")
    parser.add_argument("--min-feature-coverage", type=float, default=0.995, help="minimum finite coverage for every Alpha158 feature")
    parser.add_argument("--min-label-coverage", type=float, default=0.995, help="minimum finite coverage for 2-day-ahead labels")
    parser.add_argument("--output", default=str(DEFAULT_REPORT_PATH), help="JSON report path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report, status = run_readiness_check(args)
    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return status


if __name__ == "__main__":
    sys.exit(main())
