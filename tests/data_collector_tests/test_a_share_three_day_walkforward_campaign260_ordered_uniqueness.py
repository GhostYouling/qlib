from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign260_ordered_uniqueness as audit


def test_protocol_and_all_142_order_are_exact() -> None:
    spec = audit.load_protocol()
    definitions = audit.comparison_definitions()
    assert spec["comparison_order"]["count"] == len(definitions) == 142
    assert definitions[-1]["name"] == audit.c146.FACTOR_NAME


def test_candidate_panel_accepts_closed_unit_interval() -> None:
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2023-01-03"] * 3),
            "symbol": ["SH600000", "SZ000001", "SZ000002"],
            audit.candidate.FACTOR_NAME: [0.0, 0.5, 1.0],
            f"{audit.candidate.FACTOR_NAME}_eligible": [True, True, True],
        }
    )
    result = audit.eligible_candidate_panel(frame, frame[["trade_date", "symbol"]])
    assert result[audit.candidate.FACTOR_NAME].tolist() == [0.0, 0.5, 1.0]


def test_candidate_panel_rejects_out_of_range_values() -> None:
    for value in (-0.01, 1.01):
        frame = pd.DataFrame(
            {
                "trade_date": pd.to_datetime(["2023-01-03"]),
                "symbol": ["SH600000"],
                audit.candidate.FACTOR_NAME: [value],
                f"{audit.candidate.FACTOR_NAME}_eligible": [True],
            }
        )
        with pytest.raises(audit.Campaign260OrderedUniquenessError):
            audit.eligible_candidate_panel(frame, frame[["trade_date", "symbol"]])


def test_source_snapshot_comparison_uses_intersection_without_fill() -> None:
    dates = pd.bdate_range("2022-01-03", periods=101)
    rows = []
    for date_index, date in enumerate(dates):
        for name_index in range(50):
            rows.append(
                {
                    "trade_date": date,
                    "symbol": f"SH{name_index:06d}",
                    "synthetic": float((name_index * 17 + date_index) % 50),
                    "synthetic_eligible": True,
                }
            )
    source = pd.DataFrame(rows)
    candidate_keys = audit.base.design.compact_stock_day_keys(
        source["trade_date"], source["symbol"]
    )
    candidate_values = np.arange(len(source), dtype=np.float64) % 47 / 47.0
    order = np.argsort(candidate_keys, kind="stable")
    result, receipt = audit.source_snapshot_comparison(
        frame=source,
        factor="synthetic",
        definition={"name": "synthetic", "score_direction": "higher"},
        candidate_keys=candidate_keys[order],
        candidate_values=candidate_values[order],
        valid_minimum=0.0,
        valid_maximum=None,
    )
    assert receipt["matched_candidate_rows"] == len(source)
    assert result["pairwise_sessions"] == 101


def test_summary_requires_exact_order_and_all_passes() -> None:
    names = [f"f{i}" for i in range(142)]
    results = [
        {
            "comparison_factor": name,
            "absolute_median_daily_rank_correlation": 0.2,
            "gate_passed": True,
        }
        for name in names
    ]
    assert audit.summarize_comparisons(results, names)[
        "all_required_numeric_comparisons_passed"
    ]
    results[-1]["gate_passed"] = False
    assert not audit.summarize_comparisons(results, names)[
        "all_required_numeric_comparisons_passed"
    ]


def test_output_path_is_campaign_scoped() -> None:
    assert "campaign_260/uniqueness" in str(audit.OUTPUT_PATH)


def test_pairwise_gate_is_strict() -> None:
    assert audit.MINIMUM_PAIRWISE_NAMES == 50
    assert audit.MINIMUM_PAIRWISE_SESSIONS == 100
    assert audit.MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION == 0.8
