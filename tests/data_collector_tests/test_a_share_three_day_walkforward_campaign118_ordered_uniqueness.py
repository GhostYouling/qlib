from __future__ import annotations

from scripts import (
    a_share_three_day_walkforward_campaign118_ordered_uniqueness as audit,
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


def test_campaign118_uniqueness_protocol_and_order_are_frozen() -> None:
    spec = audit.load_protocol()
    definitions = audit.candidate.reconstruct_comparisons()
    assert len(definitions) == 135
    assert definitions[-2]["name"] == audit.c117_base.c110.FACTOR_NAME
    assert definitions[-1] == {
        "name": audit.c117_candidate.FACTOR_NAME,
        "score_direction": "higher",
    }
    assert spec["exact_gate"]["all_135_must_pass"] is True


def test_campaign118_adapter_recovery_accepts_only_current_skill_drift() -> None:
    record = audit.adapter_recovery.validate_contract()
    assert record["kind"] == (
        "a_share_three_day_walkforward_campaign107_raw_comparator_adapter_contract"
    )
    assert audit.c117_base.c110_v1.adapter.validate_contract is (
        audit.adapter_recovery.validate_contract
    )


def test_campaign118_summary_requires_every_ordered_strict_pass() -> None:
    results, order = _results()
    summary = audit.summarize_comparisons(results, order)
    assert summary["comparison_factor_count"] == 135
    assert summary["comparison_order_matches_preregistration"] is True
    assert summary["all_required_numeric_comparisons_passed"] is True


def test_campaign118_summary_rejects_reorder_and_boundary_equality() -> None:
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
