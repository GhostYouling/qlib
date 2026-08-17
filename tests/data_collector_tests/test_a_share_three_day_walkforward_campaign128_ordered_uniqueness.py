from __future__ import annotations

import numpy as np
import pandas as pd

from scripts import (
    a_share_three_day_walkforward_campaign128_ordered_uniqueness as audit,
)


def _results() -> tuple[list[dict], list[str]]:
    order = [item["name"] for item in audit.candidate.reconstruct_comparisons()]
    results = [
        {
            "comparison_factor": name,
            "absolute_median_daily_rank_correlation": 0.1,
            "gate_passed": True,
        }
        for name in order
    ]
    return results, order


def test_campaign128_uniqueness_protocol_and_order_are_frozen() -> None:
    spec = audit.load_protocol()
    definitions = audit.candidate.reconstruct_comparisons()
    assert len(definitions) == 139
    assert definitions[-1] == {
        "name": audit.c121_candidate.FACTOR_NAME,
        "score_direction": "higher",
    }
    assert spec["exact_gate"]["all_139_must_pass"] is True


def test_campaign128_summary_requires_every_ordered_strict_pass() -> None:
    results, order = _results()
    summary = audit.summarize_comparisons(results, order)
    assert summary["comparison_factor_count"] == 139
    assert summary["comparison_order_matches_preregistration"] is True
    assert summary["all_required_numeric_comparisons_passed"] is True


def test_campaign128_summary_rejects_reorder_boundary_and_missing() -> None:
    results, order = _results()
    results[0], results[1] = results[1], results[0]
    assert (
        audit.summarize_comparisons(results, order)[
            "all_required_numeric_comparisons_passed"
        ]
        is False
    )
    results, order = _results()
    results[-1]["absolute_median_daily_rank_correlation"] = 0.8
    results[-1]["gate_passed"] = False
    assert (
        audit.summarize_comparisons(results, order)[
            "all_required_numeric_comparisons_passed"
        ]
        is False
    )
    assert (
        audit.summarize_comparisons(results[:-1], order)[
            "all_required_numeric_comparisons_passed"
        ]
        is False
    )


def test_campaign128_comparator_139_binding_is_exact() -> None:
    assert audit.C121_MANIFEST_SHA256 == (
        "e5789da9896535d8d67e0f0f3a7b2704f41292e4694b127a27999224abfad724"
    )
    assert audit.C121_DATASET_SHA256 == (
        "cb476bcc93e7c88df6e2666af9d60d470c90f8a7670ea4553d2e9b877ab8a5b2"
    )
    assert audit.EXPECTED_QUALITY_LISTING_CANDIDATE_ROWS == 1319946


def test_campaign128_output_absent_before_uniqueness() -> None:
    assert audit.OUTPUT_PATH.exists() is False
    assert audit.CANDIDATE_MANIFEST_SHA256 == (
        "6ddc6358bffbfd6ae412744e96479b7bc6bc179ee0ae20cff9b3cb3e85b86e2f"
    )


def test_campaign128_eligible_panel_preserves_legal_missing_support() -> None:
    factor = audit.candidate.FACTOR_NAME
    frame = pd.DataFrame(
        {
            "trade_date": ["2025-01-02", "2025-01-02", "2025-01-03"],
            "symbol": ["SH600000", "SH600001", "SH600000"],
            factor: [0.2, np.nan, -0.3],
            f"{factor}_eligible": [True, False, True],
        }
    )
    keys = frame[["trade_date", "symbol"]].copy()
    panel = audit.eligible_candidate_panel(frame, keys)
    assert panel[["trade_date", "symbol"]].values.tolist() == [
        ["2025-01-02", "SH600000"],
        ["2025-01-03", "SH600000"],
    ]
    assert panel[factor].tolist() == [0.2, -0.3]
