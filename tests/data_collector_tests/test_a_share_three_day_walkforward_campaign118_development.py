from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign118 as campaign


ROOT = Path(__file__).resolve().parents[2]
FREEZE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_118_development_implementation_freeze_20260813.json"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_development_preregistration_bindings_and_single_trial_catalog() -> None:
    report = bindings.validate_record(campaign.DEFAULT_PREREGISTRATION)
    assert report["all_bindings_passed"] is True
    effective, digest = campaign.load_campaign(campaign.DEFAULT_PREREGISTRATION)
    assert digest == _sha(campaign.DEFAULT_PREREGISTRATION)
    assert campaign.build_trial_catalog(effective) == [
        {
            "trial_id": campaign.FROZEN_TRIAL_ID,
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": [campaign.ADMITTED_FACTOR],
            "weights": [1.0],
            "complexity": 1,
        }
    ]


def test_no_return_admission_is_interface_only_and_bound_to_authority() -> None:
    spec = json.loads(campaign.DEFAULT_PREREGISTRATION.read_text(encoding="utf-8"))
    interface_path = ROOT / spec["no_return_bindings"]["audit"]["path"]
    interface = json.loads(interface_path.read_text(encoding="utf-8"))
    authority_path = ROOT / interface["authoritative_no_return_audit"]["path"]
    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    assert interface["interface_only_no_recomputation"] is True
    assert interface["admissible_factor_names"] == [campaign.ADMITTED_FACTOR]
    assert interface["all_135_numeric_comparisons_passed"] is True
    assert authority["admissible_factor_names"] == [campaign.ADMITTED_FACTOR]
    assert authority["comparison_summary"]["comparison_factor_count"] == 135
    assert authority["historical_forward_return_fields_read"] is False
    assert _sha(authority_path) == interface["authoritative_no_return_audit"]["sha256"]


def test_folds_purge_survivor_and_execution_policy_are_inherited_exactly() -> None:
    effective, _ = campaign.load_campaign(campaign.DEFAULT_PREREGISTRATION)
    assert [
        item["validation"]["start"][:4] for item in effective["walkforward_folds"]
    ] == [
        "2021",
        "2022",
        "2023",
    ]
    assert effective["split_protocol"]["purge_signal_sessions_each_boundary"] == 3
    assert effective["split_protocol"]["label_containment_required"] is True
    assert effective["survivor_rule"]["positive_ic_fold_count_gte"] == 2
    assert effective["survivor_rule"]["positive_normalized_return_fold_count_gte"] == 2
    assert effective["survivor_rule"]["development_aggregate_20bp_return_gt"] == 0.0
    assert set(effective["execution_policy_bindings"]) == {
        "normalized_execution",
        "cny_200000_board_lot_pilot",
    }


def test_finite_search_and_closed_stress_boundary() -> None:
    effective, _ = campaign.load_campaign(campaign.DEFAULT_PREREGISTRATION)
    search = effective["search_space"]
    assert search["expected_trial_count"] == 1
    assert search["weight_fitting"] is False
    assert search["threshold_search"] is False
    assert search["year_subset_search"] is False
    assert search["filter_search"] is False
    assert effective["exposed_stress_replay"]["start"] == "2024-01-01"
    assert effective["exposed_stress_replay"]["pass_is_research_only"] is True
    assert effective["exposed_stress_replay"]["pass_can_activate_candidate50"] is False


def test_predevelopment_status_has_zero_ledger_and_closed_stress(
    tmp_path: Path,
) -> None:
    payload = campaign.status(
        argparse.Namespace(
            campaign=str(campaign.DEFAULT_PREREGISTRATION),
            output_root=str(tmp_path),
        )
    )
    assert payload["expected_trial_count"] == 1
    assert payload["ledger_entry_count"] == 0
    assert payload["stress_intent_exists"] is False
    assert payload["stress_record_exists"] is False
    assert payload["candidate49_historical_return_read"] is False
    assert payload["current_scoring_selection_sizing_or_orders_allowed"] is False


def test_development_activation_fails_before_return_loader_when_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if campaign.DEVELOPMENT_ACTIVATION.exists():
        pytest.skip("development activation has been frozen")
    inherited_called = False

    def forbidden(_args: Any) -> dict[str, Any]:
        nonlocal inherited_called
        inherited_called = True
        raise AssertionError("return loader reached before activation")

    monkeypatch.setattr(campaign, "_inherited_run_development", forbidden)
    with pytest.raises(campaign.Campaign118Error, match="activation is absent"):
        campaign.run_development(argparse.Namespace())
    assert inherited_called is False


def test_implementation_freeze_is_absent_or_live() -> None:
    if not FREEZE.exists():
        return
    record = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert record["status"] == (
        "frozen_before_campaign118_2019_2023_development_return_read"
    )
    assert record["development_runner"]["sha256"] == _sha(
        Path(campaign.__file__).resolve()
    )
    assert record["tests"]["sha256"] == _sha(Path(__file__).resolve())
    assert record["historical_daily_price_fields_read_before_freeze"] == []
    assert record["historical_forward_returns_read_before_freeze"] is False
