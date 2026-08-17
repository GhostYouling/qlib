from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign136_formula as formula
from scripts import (
    a_share_three_day_walkforward_campaign136_ordered_uniqueness as audit,
)


def _compact_keys(days: int, names: int) -> np.ndarray:
    return np.concatenate(
        [
            np.int64(day * 4_000_000) + np.arange(1_600_000, 1_600_000 + names)
            for day in range(19000, 19000 + days)
        ]
    )


def test_protocol_and_design_metadata_bind_exact_140_order() -> None:
    spec = audit.load_protocol()
    manifest = audit.validate_design_manifest_metadata()
    definitions = audit.comparison_definitions()
    assert len(definitions) == 140
    assert spec["comparison_order"]["order_sha256"] == (
        audit.EXPECTED_COMPARISON_ORDER_SHA256
    )
    assert manifest["feature_names"] == [item["name"] for item in definitions]


def test_daily_average_tie_rank_correlation_and_constant_skip() -> None:
    keys = _compact_keys(1, 60)
    candidate = np.arange(60, dtype=float)
    comparison = candidate.copy()
    comparison[:2] = 0.0
    rows = audit.daily_rank_rows(keys, candidate, comparison)
    assert len(rows) == 1
    assert rows[0][1] == 60
    assert rows[0][2] > 0.999
    reverse = audit.daily_rank_rows(keys, candidate, -candidate)
    assert reverse[0][2] < -0.999
    assert audit.daily_rank_rows(keys, candidate, np.ones(60)) == []


def test_insufficient_pairwise_names_are_excluded_without_fill() -> None:
    keys = _compact_keys(1, 60)
    candidate = np.arange(60, dtype=float)
    comparison = np.arange(60, dtype=float)
    comparison[:11] = np.nan
    assert audit.daily_rank_rows(keys, candidate, comparison) == []
    comparison[10] = 10.0
    assert len(audit.daily_rank_rows(keys, candidate, comparison)) == 1


def test_strict_point_eight_boundary_is_rejected() -> None:
    definition = {"name": "synthetic", "score_direction": "higher"}
    at_boundary = audit.comparison_result(
        definition=definition,
        daily_rows=[[19000 + index, 50, 0.8] for index in range(100)],
    )
    below_boundary = audit.comparison_result(
        definition=definition,
        daily_rows=[[19000 + index, 50, 0.799] for index in range(100)],
    )
    assert at_boundary["gate_passed"] is False
    assert below_boundary["gate_passed"] is True


def test_summary_rejects_missing_reordered_or_failed_comparator() -> None:
    order = [f"factor_{index:03d}" for index in range(140)]
    results = [
        {
            "comparison_factor": name,
            "absolute_median_daily_rank_correlation": 0.1,
            "gate_passed": True,
        }
        for name in order
    ]
    assert audit.summarize_comparisons(results, order)[
        "all_required_numeric_comparisons_passed"
    ]
    assert not audit.summarize_comparisons(results[:-1], order)[
        "all_required_numeric_comparisons_passed"
    ]
    reordered = list(results)
    reordered[0], reordered[1] = reordered[1], reordered[0]
    assert not audit.summarize_comparisons(reordered, order)[
        "all_required_numeric_comparisons_passed"
    ]
    failed = [dict(item) for item in results]
    failed[-1]["gate_passed"] = False
    assert not audit.summarize_comparisons(failed, order)[
        "all_required_numeric_comparisons_passed"
    ]


def test_candidate_panel_uses_only_declared_finite_quality_rows() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2019-01-02", "2019-01-02"]),
            "symbol": ["SH600000", "SH600001"],
            formula.FACTOR_NAME: [0.0, np.nan],
            f"{formula.FACTOR_NAME}_eligible": [True, False],
        }
    )
    keys = frame[["trade_date", "symbol"]].copy()
    panel = audit.eligible_candidate_panel(frame, keys)
    assert panel["symbol"].tolist() == ["SH600000"]
    assert panel[formula.FACTOR_NAME].tolist() == [0.0]


def test_ordered_uniqueness_freeze_is_live() -> None:
    freeze = audit.validate_implementation_freeze()
    assert freeze["frozen_implementation"]["runner_sha256"] == (
        audit.file_sha256(Path(audit.__file__).resolve())
    )
