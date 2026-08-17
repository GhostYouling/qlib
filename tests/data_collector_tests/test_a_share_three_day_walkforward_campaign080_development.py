from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign080 as campaign


ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / "docs/a_share_three_day_walkforward_campaign_080_development_implementation_freeze_20260806.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_development_preregistration_bindings_and_single_trial_catalog() -> None:
    report = bindings.validate_record(campaign.DEFAULT_PREREGISTRATION)
    assert report["all_bindings_passed"] is True
    effective, digest = campaign.load_campaign(campaign.DEFAULT_PREREGISTRATION)
    assert digest == "6ccc49c13dc2e7ba2b0955720efa7a24f94d23d19f13414b2fefc3ceebcd0b10"
    catalog = campaign.build_trial_catalog(effective)
    assert len(catalog) == 1
    assert catalog[0]["trial_id"] == campaign.FROZEN_TRIAL_ID
    assert catalog[0]["feature_set"] == [campaign.ADMITTED_FACTOR]
    assert catalog[0]["weights"] == [1.0]


def test_predevelopment_status_has_zero_ledger_and_closed_stress() -> None:
    status = campaign.status(
        argparse.Namespace(
            campaign=str(campaign.DEFAULT_PREREGISTRATION),
            output_root=str(
                ROOT
                / "data/experiments/short_horizon/historical_walkforward/campaign_080/walkforward"
            ),
        )
    )
    assert status["campaign_id"] == "a_share_three_day_walkforward_campaign_080"
    assert status["expected_trial_count"] == 1
    assert status["ledger_entry_count"] == 0
    assert status["stress_intent_exists"] is False
    assert status["stress_record_exists"] is False
    assert status["candidate49_historical_return_read"] is False
    assert status["current_scoring_selection_sizing_or_orders_allowed"] is False


def test_no_return_admission_and_candidate49_boundary_are_bound() -> None:
    spec = json.loads(campaign.DEFAULT_PREREGISTRATION.read_text(encoding="utf-8"))
    assert spec["factor_library"][0]["name"] == campaign.ADMITTED_FACTOR
    assert spec["search_space"]["expected_trial_count"] == 1
    assert spec["search_space"]["weight_fitting"] is False
    assert spec["candidate49_boundary"]["historical_return_read_allowed"] is False
    assert spec["research_output_boundary"]["orders_allowed"] is False


def test_development_implementation_freeze_is_live() -> None:
    record = json.loads(FREEZE.read_text(encoding="utf-8"))
    assert record["status"] == "frozen_before_campaign080_2019_2023_development_return_read"
    assert record["development_runner"]["sha256"] == _sha(Path(campaign.__file__).resolve())
    assert record["tests"]["sha256"] == _sha(Path(__file__).resolve())
    assert record["historical_daily_price_fields_read_before_freeze"] == []
    assert record["historical_forward_returns_read_before_freeze"] is False
