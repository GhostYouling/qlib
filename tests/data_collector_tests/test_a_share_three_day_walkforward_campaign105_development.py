from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign105 as campaign


ROOT = Path(__file__).resolve().parents[2]
FREEZE = (
    ROOT
    / "docs/a_share_three_day_walkforward_campaign_105_development_implementation_freeze_20260808.json"
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


def test_predevelopment_status_has_zero_ledger_and_closed_stress(
    tmp_path: Path,
) -> None:
    payload = campaign.status(
        argparse.Namespace(
            campaign=str(campaign.DEFAULT_PREREGISTRATION),
            output_root=str(tmp_path),
        )
    )
    assert payload["campaign_id"] == "a_share_three_day_walkforward_campaign_105"
    assert payload["expected_trial_count"] == 1
    assert payload["ledger_entry_count"] == 0
    assert payload["stress_intent_exists"] is False
    assert payload["stress_record_exists"] is False
    assert payload["candidate49_historical_return_read"] is False
    assert payload["current_scoring_selection_sizing_or_orders_allowed"] is False


def test_no_return_admission_and_research_boundaries_are_frozen() -> None:
    spec = json.loads(campaign.DEFAULT_PREREGISTRATION.read_text(encoding="utf-8"))
    audit = json.loads(
        (ROOT / spec["no_return_bindings"]["audit"]["path"]).read_text(encoding="utf-8")
    )
    assert audit["status"] == (
        "completed_with_one_admissible_factor_pending_walkforward_preregistration"
    )
    assert audit["admissible_factor_names"] == [campaign.ADMITTED_FACTOR]
    assert audit["historical_forward_return_fields_read"] is False
    assert spec["factor_library"][0]["direction"] == "higher"
    assert spec["search_space"]["expected_trial_count"] == 1
    assert spec["search_space"]["weight_fitting"] is False
    assert spec["candidate49_boundary"]["historical_return_read_allowed"] is False
    assert spec["research_output_boundary"]["orders_allowed"] is False


def test_development_activation_fails_before_data_access_when_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if campaign.DEVELOPMENT_ACTIVATION.exists():
        pytest.skip("activation binding has been frozen")
    inherited_called = False

    def forbidden_inherited_call(args: Any) -> dict[str, Any]:
        nonlocal inherited_called
        inherited_called = True
        raise AssertionError("inherited development runner reached before activation")

    monkeypatch.setattr(
        campaign, "_inherited_run_development", forbidden_inherited_call
    )
    with pytest.raises(campaign.Campaign105Error, match="activation is absent"):
        campaign.run_development(argparse.Namespace())
    assert inherited_called is False


def test_development_implementation_freeze_is_absent_or_live() -> None:
    if not FREEZE.exists():
        return
    record = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert record["status"] == (
        "frozen_before_campaign105_2019_2023_development_return_read"
    )
    assert record["development_runner"]["sha256"] == _sha(
        Path(campaign.__file__).resolve()
    )
    assert record["tests"]["sha256"] == _sha(Path(__file__).resolve())
    assert record["historical_daily_price_fields_read_before_freeze"] == []
    assert record["historical_forward_returns_read_before_freeze"] is False


def test_development_activation_is_absent_or_live() -> None:
    if not campaign.DEVELOPMENT_ACTIVATION.exists():
        return
    record = campaign._validate_development_activation()
    assert record["trial_count"] == 1
    assert record["trial_id"] == campaign.FROZEN_TRIAL_ID
    assert record["single_use"] is True
    assert record["stress_2024_2025_opened_before_activation"] is False
    assert record["candidate49_ledgers_changed_before_activation"] is False
    assert record["provider_request_issued_before_activation"] is False
