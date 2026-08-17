from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign152_features as features


ROOT = Path(__file__).resolve().parents[2]
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_171_board_oversight_structure_source_frontier_20260815.json"
)
FAILURES = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_171_prevalue_infrastructure_failures_20260815.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_171/research_attempt_ledger.json"
)
RECOVERY_LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_171/research_attempt_ledger_v2.json"
)
REGRESSION_LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_171/research_attempt_ledger_v3.json"
)
EFFECTIVE_LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_171/research_attempt_ledger_v4.json"
)
BLACK_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_171_black_check_failure_20260815.json"
)
REGRESSION_FAILURES = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_171_regression_infrastructure_failures_20260815.json"
)
SYNTAX_FAILURE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_171_independent_validation_syntax_failure_20260815.json"
)
TERMINAL = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_171_terminal_result_v4_20260815.json"
)
REPORT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_171_terminal_report_v4_20260815.md"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v252_20260815.json"
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


def test_campaign171_bindings_and_finite_frontier() -> None:
    for record_path in (FRONTIER, TERMINAL, POLICY):
        _verify_bindings(_load(record_path))

    routes = _load(FRONTIER)["finite_prevalue_catalog"]
    assert [item["catalog_id"] for item in routes] == [
        f"c171_0{i}" for i in range(1, 8)
    ]
    assert all(item["formula"] is None and item["direction"] is None for item in routes)
    assert all(
        not item["parameters_filters_subsets_combinations_models"] for item in routes
    )
    assert sum(item["new_issuer_state"] for item in routes) == 4
    assert sum(item["complete_local_source_contract"] for item in routes) == 0
    summary = _load(FRONTIER)["gate_summary"]
    assert summary["source_admission_deferrals_not_factor_failures"] == 4
    assert summary["terminal_or_operator_route_rejections"] == 3
    assert summary["selected_candidate_count"] == 0


def test_campaign171_source_gate_failures_and_attempt_chain() -> None:
    frontier = _load(FRONTIER)
    gate = frontier["mandatory_source_admission_gate"]
    assert len(gate["must_freeze_before_any_formula_or_direction"]) == 12
    assert (
        gate[
            "formula_direction_parameter_filter_subset_combination_or_model_choice_allowed_before_gate"
        ]
        is False
    )
    failures = _load(FAILURES)
    assert len(failures["failures"]) == 3
    assert all(item["write_result"] == "zero_write" for item in failures["failures"])
    assert (
        failures["recovery_assertions"]["failed_exit_or_subcommand_masking_ignored"]
        is False
    )

    previous = _load(LEDGER)["authoritative_predecessor"]["chain_tip_sha256"]
    for ledger_path in (
        LEDGER,
        RECOVERY_LEDGER,
        REGRESSION_LEDGER,
        EFFECTIVE_LEDGER,
    ):
        ledger = _load(ledger_path)
        predecessor = ledger["authoritative_predecessor"]
        assert _sha(ROOT / predecessor["path"]) == predecessor["sha256"]
        assert predecessor["chain_tip_sha256"] == previous
        for entry in ledger["delta_entries"]:
            assert entry["previous_entry_sha256"] == previous
            payload = "|".join(
                [
                    "campaign171",
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
    assert effective["campaign_effective_entry_count"] == 14
    assert effective["campaign_effective_prevalue_scientific_attempt_count"] == 7
    assert effective["campaign_effective_infrastructure_failure_attempt_count"] == 7
    assert effective["cumulative_historical_research_attempt_count"] == 1509
    assert effective["cumulative_return_reading_development_trial_count"] == 314
    assert _load(BLACK_FAILURE)["attempt"]["write_result"] == "zero_write"
    regression_failures = _load(REGRESSION_FAILURES)
    assert len(regression_failures["failures"]) == 2
    assert (
        regression_failures["recovery_assertions"][
            "future_exact_historical_lifecycle_node_count"
        ]
        == 4
    )
    assert _load(SYNTAX_FAILURE)["attempt"]["execution_reached"] is False


def test_campaign171_library_policy_and_candidate49_boundaries() -> None:
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
    assert policy["complete_historical_feature_library"]["unchanged_from_v251"]
    assert policy["numerical_comparator_eligibility"]["unchanged_from_v251"]
    assert policy["future_campaign_boundary"]["next_campaign"] == 172
    assert policy["future_campaign_boundary"][
        "2024_2025_source_or_returns_remain_closed"
    ]
    assert _sha(SIGNAL_LEDGER) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha(EXECUTION_LEDGER) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert policy["candidate49"]["signal_entry_count"] == 0
    assert policy["candidate49"]["execution_entry_count"] == 0


def test_campaign171_reports_are_appended_exactly_once() -> None:
    heading = "## Campaign171 历史点时董事会结构与监督来源前沿值前终止"
    assert "14 次尝试（7 科学、7 基础设施）" in REPORT.read_text(encoding="utf-8")
    for report_path in (
        ROOT / "data/experiments/short_horizon/current_research_report.md",
        ROOT / "data/experiments/short_horizon/three_day_research_report.md",
    ):
        text = report_path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert "Campaign171 有效会计为 10 次尝试（7 科学、3 基础设施）" in text
        assert text.count("### Campaign171 测试格式门禁恢复会计") == 1
        assert "Campaign171 最终有效会计为 11 次尝试（7 科学、4 基础设施）" in text
        assert text.count("### Campaign171 累计回归生命周期恢复最终会计") == 1
        assert "Campaign171 最终有效会计为 13 次尝试（7 科学、6 基础设施）" in text
        assert text.count("### Campaign171 独立验证脚本恢复最终会计") == 1
        assert "Campaign171 最终有效会计为 14 次尝试（7 科学、7 基础设施）" in text


def test_campaign171_records_use_reached_wall_clock_timestamps() -> None:
    for record_path in (
        FRONTIER,
        FAILURES,
        LEDGER,
        BLACK_FAILURE,
        RECOVERY_LEDGER,
        REGRESSION_FAILURES,
        REGRESSION_LEDGER,
        SYNTAX_FAILURE,
        EFFECTIVE_LEDGER,
        TERMINAL,
        POLICY,
    ):
        recorded_at = datetime.fromisoformat(_load(record_path)["recorded_at"])
        modified_at = datetime.fromtimestamp(
            record_path.stat().st_mtime, tz=recorded_at.tzinfo
        )
        assert recorded_at <= modified_at
