from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign263_features as features


ROOT = Path(__file__).resolve().parents[2]
FRONTIER = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_264_local_schema_independent_mechanism_frontier_20260824.json"
)
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_264/research_attempt_ledger_v1.json"
)
RESULT = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_264_terminal_result_20260824.json"
)
POLICY = (
    ROOT
    / "docs/a_share_three_day_walkforward_future_numeric_comparison_eligibility_policy_v415_20260824.json"
)
TERMINAL_REPORT = (
    ROOT / "docs/a_share_three_day_walkforward_campaign_264_terminal_report.md"
)
SIGNAL = ROOT / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
EXECUTION = (
    ROOT / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
REPORTS = (
    ROOT / "data/experiments/short_horizon/current_research_report.md",
    ROOT / "data/experiments/short_horizon/three_day_research_report.md",
)


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(path: str) -> Path:
    target = Path(path)
    return target if target.is_absolute() else ROOT / target


def _assert_bindings(bindings: dict) -> None:
    for binding in bindings.values():
        target = _resolve(binding["path"])
        assert target.is_file()
        assert _sha256(target) == binding["sha256"]


def _campaign264_entry_hash(entry: dict) -> str:
    payload = "|".join(
        (
            "campaign264",
            entry["attempt_id"],
            entry["previous_entry_sha256"],
            entry["phase"],
            entry["status"],
        )
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def test_reference_graph_and_frozen_artifact_hashes_are_exact() -> None:
    frontier = _load(FRONTIER)
    result = _load(RESULT)
    policy = _load(POLICY)
    assert _sha256(FRONTIER) == (
        "4ff4834dd6044d6937f1abde82edbe316351b05dca839b5985597de944199c8b"
    )
    assert _sha256(LEDGER) == (
        "a97c2cfa64f2d86fb40386479ac301d1ad5dfa04e53d3ff54263dfdabbb85bb6"
    )
    assert _sha256(RESULT) == (
        "c746ac55551bec7eef833ab312d710ee64fa765d7e266397e676bc7a1dec362e"
    )
    assert _sha256(POLICY) == (
        "9af0c77afb9a3f9a1e9434914de8178c57a507f680ea17587a128aebd989b77d"
    )
    assert _sha256(TERMINAL_REPORT) == (
        "0f7ced26eb814dd5eecd072b73d70739c04fb5392ce4f4c75cfc57ed6974356a"
    )
    _assert_bindings(frontier["authoritative_inputs"])
    _assert_bindings(result["authoritative_inputs"])
    _assert_bindings(policy["authoritative_inputs"])
    _assert_bindings({"superseded": policy["supersedes_without_rewriting"]})


def test_finite_frontier_is_terminal_before_any_candidate_value() -> None:
    frontier = _load(FRONTIER)
    catalog = frontier["finite_prevalue_catalog"]
    assert [item["route_id"] for item in catalog] == [
        "c264_01",
        "c264_02",
        "c264_03",
        "c264_04",
        "c264_05",
        "c264_06",
        "c264_07",
    ]
    assert all(item["decision"].startswith("reject_") for item in catalog)
    gate = frontier["gate_summary"]
    assert gate["finite_route_count"] == 7
    assert gate["terminal_overlap_or_post_exposure_rejection_count"] == 7
    assert gate["selected_factor_count"] == 0
    assert gate["numeric_formula_or_direction_frozen"] is False
    assert gate["candidate_or_comparator_value_read"] is False
    assert gate["historical_daily_price_or_forward_return_read"] is False
    assert gate["development_trial_count"] == 0
    assert gate["stress_trial_count_2024_2025"] == 0
    assert gate["complete_definition_or_numeric_comparator_append_allowed"] is False


def test_complete_definition_and_numeric_comparator_orders_are_unchanged() -> None:
    policy = _load(POLICY)
    definitions = features.reconstruct_complete_definitions()
    comparators = features.reconstruct_comparisons()
    comparators.append({"name": features.FACTOR_NAME, "score_direction": "higher"})
    library = policy["complete_historical_feature_library"]
    numeric = policy["numerical_comparator_eligibility"]
    assert len(definitions) == library["factor_definition_count"] == 162
    assert (
        features._order_digest(definitions)
        == library["order_sha256"]
        == ("974f2c1f16a85eb43a0bd1e8db768dbe120cd8826c1754d5f220bf9f1d4a3ea0")
    )
    assert len(comparators) == numeric["eligible_numeric_comparator_count"] == 143
    assert (
        features._order_digest(comparators)
        == numeric["order_sha256"]
        == ("f4fbf3d578e2c80c29425716a30d60a3df01d67d04e37f1651236c4dff899588")
    )
    assert library["campaign264_definition_appended"] is False
    assert numeric["campaign264_numeric_comparator_appended"] is False


def test_append_only_attempt_chain_and_cumulative_accounting_are_exact() -> None:
    ledger = _load(LEDGER)
    previous = ledger["authoritative_predecessor"]["chain_tip_sha256"]
    assert (
        ledger["authoritative_predecessor"][
            "cumulative_historical_research_attempt_count"
        ]
        == 2597
    )
    for ordinal, entry in enumerate(ledger["entries"], 1):
        assert entry["ordinal"] == ordinal
        assert entry["attempt_id"] == f"campaign264_scientific_{ordinal:03d}"
        assert entry["route_id"] == f"c264_{ordinal:02d}"
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _campaign264_entry_hash(entry)
        assert entry["scientific_attempt"] is True
        assert entry["result_consumed"] is True
        previous = entry["entry_sha256"]
    assert (
        previous
        == ledger["chain_tip_sha256"]
        == ("19f0cc33cef72207d8e0c62721b86c5fc8d36d56a024503a76ef240b6359e49d")
    )
    assert ledger["effective_entry_count"] == 7
    assert ledger["effective_infrastructure_failure_attempt_count"] == 0
    assert ledger["effective_complete_factor_attempt_count"] == 0
    assert ledger["return_reading_development_trial_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 2604
    assert ledger["cumulative_return_reading_development_trial_count"] == 315


def test_result_candidate49_and_next_campaign_semantics_are_closed() -> None:
    result = _load(RESULT)
    policy = _load(POLICY)
    scientific = result["scientific_result"]
    assert scientific["selected_factor_count"] == 0
    assert scientific["development_survivor_count"] == 0
    assert scientific["stress_trial_count_2024_2025"] == 0
    assert policy["version"] == 415
    future = policy["future_campaign_boundary"]
    assert future["next_campaign"] == 265
    assert future["campaign264_seven_rejected_routes_may_not_be_retried_or_rescued"]
    assert future["historical_offline_prevalue_work_may_continue_at_any_local_time"]
    assert _sha256(SIGNAL) == (
        "5193f00d7f36da003f53cec387900da4c3d002299f5dfcfc1a95eaa199ed3a79"
    )
    assert _sha256(EXECUTION) == (
        "d57a3e61eac969e42cafa418ccd8c0a5ee65dcf69da145bb2c096c2a02a2ea4f"
    )
    assert _load(SIGNAL)["entries"] == []
    assert _load(EXECUTION)["entries"] == []


def test_research_boundary_has_only_the_declared_metadata_read() -> None:
    for artifact in (_load(FRONTIER), _load(RESULT), _load(POLICY)):
        boundary = artifact["research_boundary"]
        assert (
            boundary.pop(
                "repository_metadata_terminal_history_and_parquet_schema_metadata_read"
            )
            is True
        )
        assert boundary
        assert not any(boundary.values())


def test_unified_reports_have_one_matching_campaign264_section() -> None:
    policy = _load(POLICY)
    heading = "## Campaign264：本地原始通道独立机制值前终止（2026-08-24）"
    expected = (
        policy["mutable_unified_reports"]["current"]["sha256_at_publication"],
        policy["mutable_unified_reports"]["three_day"]["sha256_at_publication"],
    )
    for path, expected_sha256 in zip(REPORTS, expected, strict=True):
        text = path.read_text(encoding="utf-8")
        assert text.count(heading) == 1
        assert "2,604" in text
        assert "Campaign265" in text
        assert _sha256(path) == expected_sha256
