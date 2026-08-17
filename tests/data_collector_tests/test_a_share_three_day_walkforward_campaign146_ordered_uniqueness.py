from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import (
    a_share_three_day_walkforward_campaign146_ordered_uniqueness as audit,
)


def test_campaign146_uniqueness_protocol_and_all_141_order_are_bound() -> None:
    spec = audit.load_protocol()
    definitions = audit.comparison_definitions()
    assert spec["comparison_order"]["count"] == 141
    assert len(definitions) == 141
    assert definitions[:140] == audit.design.current_feature_order()
    assert definitions[-1] == {
        "name": audit.c136_formula.FACTOR_NAME,
        "score_direction": "higher",
    }


def test_campaign146_candidate_panel_accepts_negative_and_filters_missing() -> None:
    factor = audit.candidate.FACTOR_NAME
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2023-01-03", "2023-01-03", "2023-01-03"]),
            "symbol": ["SZ000001", "SH600000", "SZ000002"],
            factor: [-0.25, 0.5, np.nan],
            f"{factor}_eligible": [True, True, False],
        }
    )
    keys = frame[["trade_date", "symbol"]].copy()
    result = audit.eligible_candidate_panel(frame, keys)
    assert result[factor].tolist() == [-0.25, 0.5]


def test_campaign146_subset_alignment_requires_complete_superset() -> None:
    source = np.array([1, 2, 3, 4, 5], dtype=np.int64)
    target = np.array([2, 4], dtype=np.int64)
    assert audit.subset_positions(source_keys=source, target_keys=target).tolist() == [
        1,
        3,
    ]
    with pytest.raises(audit.Campaign146OrderedUniquenessError):
        audit.subset_positions(
            source_keys=source, target_keys=np.array([2, 6], dtype=np.int64)
        )


def test_campaign146_daily_rank_rows_use_average_ties_and_drop_constant() -> None:
    keys = np.array([8_000_001, 8_000_002, 8_000_003, 12_000_001, 12_000_002])
    candidate = np.array([1.0, 1.0, 2.0, 1.0, 2.0])
    comparator = np.array([1.0, 1.0, 2.0, 5.0, 5.0])
    rows = audit.base.daily_rank_rows(keys, candidate, comparator, minimum_names=2)
    assert len(rows) == 1
    assert rows[0][2] == pytest.approx(1.0)


def _result(name: str, value: float, passed: bool = True) -> dict[str, object]:
    return {
        "comparison_factor": name,
        "absolute_median_daily_rank_correlation": value,
        "gate_passed": passed,
    }


def test_campaign146_summary_rejects_strict_boundary_and_reorder() -> None:
    names = [item["name"] for item in audit.comparison_definitions()]
    results = [_result(name, 0.1) for name in names]
    assert audit.summarize_comparisons(results, names)[
        "all_required_numeric_comparisons_passed"
    ]
    results[-1] = _result(names[-1], 0.8, passed=False)
    assert not audit.summarize_comparisons(results, names)[
        "all_required_numeric_comparisons_passed"
    ]
    results[-1] = _result(names[-1], 0.1)
    assert not audit.summarize_comparisons(results[::-1], names)[
        "all_required_numeric_comparisons_passed"
    ]


def test_campaign146_comparator_source_metadata_are_immutable() -> None:
    design_manifest = audit.validate_design_manifest_metadata()
    c136_manifest = audit.validate_c136_manifest_metadata()
    assert design_manifest["feature_count"] == 140
    assert design_manifest["dataset_sha256"] == audit.DESIGN_DATASET_SHA256
    assert c136_manifest["dataset_sha256"] == audit.C136_DATASET_SHA256
