from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign152_features as features


ROOT = Path(__file__).resolve().parents[2]
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_173_enterprise_tax_position_compliance_source_frontier_20260815.json"
)
INITIAL_LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_173/research_attempt_ledger.json"
)
EFFECTIVE_LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_173/research_attempt_ledger_v5.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_173_terminal_result_v5_20260815.json"
)
REPORT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_173_terminal_report_v5_20260815.md"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v259_20260815.json"
)
TIMESTAMP_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_173_focused_timestamp_gate_failure_20260815.json"
)
PLACEHOLDER_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_173_timestamp_correction_placeholder_failure_20260815.json"
)
INVALID_CORRECTION = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_173_recorded_at_correction_20260815.json"
)
EFFECTIVE_CORRECTION = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_173_recorded_at_correction_v2_20260815.json"
)
VALIDATION_SCOPE_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_173_independent_validation_scope_failure_20260815.json"
)
PATCH_CONTEXT_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_173_test_binding_patch_context_failure_20260815.json"
)
TIMESTAMP_SUBSET_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_173_effective_timestamp_subset_failure_20260815.json"
)
SIGNAL_LEDGER = (
    ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER = (
    ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bound_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _verify_bindings(record: dict) -> None:
    superseded = record.get("supersedes_without_rewriting")
    if isinstance(superseded, dict) and "path" in superseded:
        bound = _bound_path(superseded["path"])
        assert bound.is_file()
        assert _sha(bound) == superseded["sha256"]
    for binding in record.get("authoritative_inputs", {}).values():
        if isinstance(binding, dict) and "path" in binding:
            bound = _bound_path(binding["path"])
            assert bound.is_file()
            assert _sha(bound) == binding["sha256"]


def test_campaign173_bindings_and_finite_frontier() -> None:
    for record_path in (FRONTIER, TERMINAL, POLICY, EFFECTIVE_CORRECTION):
        _verify_bindings(_load(record_path))

    frontier = _load(FRONTIER)
    routes = frontier["finite_prevalue_catalog"]
    assert [item["catalog_id"] for item in routes] == [
        f"c173_0{i}" for i in range(1, 8)
    ]
    assert all(item["formula"] is None and item["direction"] is None for item in routes)
    assert all(
        not item["parameters_filters_subsets_combinations_models"] for item in routes
    )
    assert sum(item["new_issuer_state"] for item in routes) == 4
    assert sum(item["complete_local_source_contract"] for item in routes) == 0
    assert (
        len(
            frontier["mandatory_source_admission_gate"][
                "must_freeze_before_any_formula_or_direction"
            ]
        )
        == 12
    )
    summary = frontier["gate_summary"]
    assert summary["source_admission_deferrals_not_factor_failures"] == 4
    assert summary["relabeling_or_operator_route_rejections"] == 3
    assert summary["selected_candidate_count"] == 0


def test_campaign173_attempt_chain_and_accounting() -> None:
    initial = _load(INITIAL_LEDGER)
    predecessor = initial["authoritative_predecessor"]
    assert _sha(ROOT / predecessor["path"]) == predecessor["sha256"]
    previous = predecessor["chain_tip_sha256"]
    for ledger_path, expected_delta_count in (
        (INITIAL_LEDGER, 7),
        (
            ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_173/research_attempt_ledger_v2.json",
            2,
        ),
        (
            ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_173/research_attempt_ledger_v3.json",
            1,
        ),
        (
            ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_173/research_attempt_ledger_v4.json",
            1,
        ),
        (EFFECTIVE_LEDGER, 1),
    ):
        ledger = _load(ledger_path)
        predecessor = ledger["authoritative_predecessor"]
        assert _sha(ROOT / predecessor["path"]) == predecessor["sha256"]
        assert predecessor["chain_tip_sha256"] == previous
        assert len(ledger["delta_entries"]) == expected_delta_count
        for entry in ledger["delta_entries"]:
            assert entry["previous_entry_sha256"] == previous
            payload = "|".join(
                [
                    "campaign173",
                    entry["attempt_id"],
                    previous,
                    entry["phase"],
                    entry["status"],
                ]
            )
            previous = hashlib.sha256(payload.encode()).hexdigest()
            assert entry["entry_sha256"] == previous
            assert (
                entry["candidate_comparator_security_price_or_return_value_read"]
                is False
            )
        assert previous == ledger["chain_tip_sha256"]
    effective = _load(EFFECTIVE_LEDGER)
    assert effective["campaign_effective_entry_count"] == 12
    assert effective["campaign_effective_infrastructure_failure_attempt_count"] == 5
    assert effective["cumulative_historical_research_attempt_count"] == 1530
    assert effective["cumulative_return_reading_development_trial_count"] == 314


def test_campaign173_library_policy_and_candidate49_boundaries() -> None:
    definitions = features.reconstruct_complete_definitions()
    definitions.append(
        {"name": "eastmoney_debt_maturity_resilience", "score_direction": "higher"}
    )
    comparisons = features.reconstruct_comparisons()
    policy = _load(POLICY)
    assert len(definitions) == 158
    assert features._order_digest(definitions) == (
        "4819c7fd7c0795d7598a52f3c615e3f117d5f4ecd9332974bc8e3dfa57c96667"
    )
    assert len(comparisons) == 142
    assert features._order_digest(comparisons) == (
        "5d1b35fb5a0d8ac9293008db9963c4a60a94dc940c237c3ed259e5ce44f14aaf"
    )
    assert policy["complete_historical_feature_library"]["unchanged_from_v258"]
    assert policy["numerical_comparator_eligibility"]["unchanged_from_v258"]
    assert policy["future_campaign_boundary"]["next_campaign"] == 174
    assert policy["future_campaign_boundary"][
        "2024_2025_source_or_returns_remain_closed"
    ]
    lifecycle = policy["cumulative_regression_boundary"][
        "required_exact_historical_lifecycle_nodes"
    ]
    assert len(lifecycle) == 5
    assert len(set(lifecycle)) == 5
    assert (
        policy["cumulative_regression_boundary"][
            "campaign173_policy_binds_mutable_reports_as_current_hashes"
        ]
        is False
    )
    assert _sha(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert policy["candidate49"]["signal_entry_count"] == 0
    assert policy["candidate49"]["execution_entry_count"] == 0


def test_campaign173_reports_are_appended_exactly_once() -> None:
    heading = "## Campaign173 企业税务状态与合规暴露来源前沿值前终止"
    report_text = REPORT.read_text(encoding="utf-8")
    assert "12 次尝试（7 科学、5 基础设施）" in report_text
    assert "累计历史研究尝试为 `1530`" in report_text
    for report_path in (
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = report_path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert "Campaign173 共 7 次科学尝试、0 次基础设施失败" in text
        assert "累计历史尝试 `1525`" in text
        assert text.count("### Campaign173 时间戳门禁与更正发布恢复会计") == 1
        assert "Campaign173 最终有效会计为 9 次尝试（7 科学、2 基础设施）" in text
        assert "累计历史尝试 `1527`" in text
        assert text.count("### Campaign173 独立验证负控范围恢复会计") == 1
        assert "Campaign173 最终有效会计为 10 次尝试（7 科学、3 基础设施）" in text
        assert "累计历史尝试 `1528`" in text
        assert text.count("### Campaign173 测试有效绑定补丁恢复会计") == 1
        assert "Campaign173 最终有效会计为 11 次尝试（7 科学、4 基础设施）" in text
        assert "累计历史尝试 `1529`" in text
        assert text.count("### Campaign173 有效时间戳子集恢复会计") == 1
        assert "Campaign173 最终有效会计为 12 次尝试（7 科学、5 基础设施）" in text
        assert "累计历史尝试 `1530`" in text


def test_campaign173_records_use_reached_wall_clock_timestamps() -> None:
    for record_path in (
        TIMESTAMP_FAILURE,
        PLACEHOLDER_FAILURE,
        EFFECTIVE_CORRECTION,
        VALIDATION_SCOPE_FAILURE,
        PATCH_CONTEXT_FAILURE,
        TIMESTAMP_SUBSET_FAILURE,
        EFFECTIVE_LEDGER,
        TERMINAL,
        POLICY,
    ):
        recorded_at = datetime.fromisoformat(_load(record_path)["recorded_at"])
        modified_at = datetime.fromtimestamp(
            record_path.stat().st_mtime, tz=recorded_at.tzinfo
        )
        assert recorded_at <= modified_at
    correction = _load(EFFECTIVE_CORRECTION)
    assert correction["scientific_result_changed"] is False
    assert (
        _sha(INVALID_CORRECTION) == correction["supersedes_without_rewriting"]["sha256"]
    )
    assert "TO_BE_BOUND_AFTER_FAILURE_PUBLICATION" in INVALID_CORRECTION.read_text(
        encoding="utf-8"
    )
    assert len(correction["preserved_original_records"]) == 4
    for original in correction["preserved_original_records"]:
        assert _sha(ROOT / original["path"]) == original["sha256"]
        assert datetime.fromisoformat(original["original_recorded_at"]) > (
            datetime.fromisoformat(original["observed_filesystem_modified_at_seconds"])
        )
