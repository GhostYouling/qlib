from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign263 as campaign


ROOT = Path(__file__).resolve().parents[2]
LEDGER = (
    ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_263/research_attempt_ledger_v7.json"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _entry_hash(entry: dict[str, Any]) -> str:
    body = {key: value for key, value in entry.items() if key != "entry_sha256"}
    payload = json.dumps(
        body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def test_development_preregistration_bindings_and_single_trial_catalog() -> None:
    report = bindings.validate_record(campaign.DEFAULT_PREREGISTRATION)
    assert report["all_bindings_passed"] is True
    assert report["binding_count"] == 17
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


def test_no_return_admission_is_bound_to_all_142_authority() -> None:
    spec = json.loads(campaign.DEFAULT_PREREGISTRATION.read_text(encoding="utf-8"))
    interface_path = ROOT / spec["no_return_bindings"]["audit"]["path"]
    interface = json.loads(interface_path.read_text(encoding="utf-8"))
    authority_path = ROOT / interface["authoritative_no_return_audit"]["path"]
    authority = json.loads(authority_path.read_text(encoding="utf-8"))
    assert interface["interface_only_no_recomputation"] is True
    assert interface["admissible_factor_names"] == [campaign.ADMITTED_FACTOR]
    assert interface["all_142_numeric_comparisons_passed"] is True
    assert authority["factor"] == campaign.ADMITTED_FACTOR
    assert authority["summary"]["comparison_factor_count"] == 142
    assert authority["summary"]["all_required_numeric_comparisons_passed"] is True
    assert authority["historical_daily_price_or_forward_return_values_read"] is False
    assert _sha(authority_path) == interface["authoritative_no_return_audit"]["sha256"]


def test_folds_purge_survivor_execution_and_closed_stress_are_inherited() -> None:
    effective, _ = campaign.load_campaign(campaign.DEFAULT_PREREGISTRATION)
    assert [
        item["validation"]["start"][:4] for item in effective["walkforward_folds"]
    ] == ["2021", "2022", "2023"]
    assert effective["split_protocol"]["purge_signal_sessions_each_boundary"] == 3
    assert effective["split_protocol"]["label_containment_required"] is True
    assert effective["survivor_rule"]["positive_ic_fold_count_gte"] == 2
    assert effective["survivor_rule"]["positive_normalized_return_fold_count_gte"] == 2
    assert effective["survivor_rule"]["development_aggregate_20bp_return_gt"] == 0.0
    assert set(effective["execution_policy_bindings"]) == {
        "normalized_execution",
        "cny_200000_board_lot_pilot",
    }
    assert effective["exposed_stress_replay"]["start"] == "2024-01-01"
    assert effective["exposed_stress_replay"]["pass_can_activate_candidate50"] is False


def test_minute_snapshot_adapter_preserves_zero_and_missing_without_ohlcv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    factor = campaign.ADMITTED_FACTOR
    frame = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2019-01-02", "2019-01-03"]),
            "symbol": ["sh600000", "sh600000"],
            "provider": ["tushare", "tushare"],
            factor: [0.0, float("nan")],
            f"{factor}_eligible": [True, False],
        }
    )
    partition = tmp_path / "sh600000-2019.parquet"
    pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), partition)
    (tmp_path / "snapshot_manifest.json").write_text(
        json.dumps({"files": [{"path": str(partition)}]}), encoding="utf-8"
    )
    monkeypatch.setattr(campaign.feature_source, "output_root", lambda _root: tmp_path)
    monkeypatch.setattr(campaign, "_snapshot_verified", True)
    spec = {
        "factor_library": [
            {
                "name": factor,
                "direction": "higher",
                "partition_root": str(tmp_path),
            }
        ]
    }
    output = campaign._campaign263_load_factor_panel(
        spec,
        [2019],
        pd.DatetimeIndex(["2019-01-02", "2019-01-03"]),
    )
    assert list(output.columns) == ["trade_date", "instrument", factor]
    assert output["instrument"].tolist() == ["SH600000", "SH600000"]
    assert output[factor].iloc[0] == 0.0
    assert pd.isna(output[factor].iloc[1])


def test_predevelopment_ledger_reconstructs_from_campaign262_tip() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    previous = ledger["authoritative_predecessor"]["chain_tip_sha256"]
    for ordinal, entry in enumerate(ledger["entries"], 1):
        assert entry["ordinal"] == ordinal
        assert entry["previous_entry_sha256"] == previous
        assert entry["entry_sha256"] == _entry_hash(entry)
        previous = entry["entry_sha256"]
    assert previous == ledger["chain_tip_sha256"]
    assert ledger["effective_entry_count"] == 28
    assert ledger["effective_infrastructure_failure_attempt_count"] == 20
    assert ledger["effective_prevalue_scientific_attempt_count"] == 8
    assert ledger["effective_return_reading_development_trial_count"] == 0
    assert ledger["cumulative_historical_research_attempt_count"] == 2591
    assert ledger["cumulative_return_reading_development_trial_count"] == 314


def test_predevelopment_status_has_zero_return_ledger_and_closed_stress(
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
    assert not campaign.DEVELOPMENT_ACTIVATION.exists()
    inherited_called = False

    def forbidden(_args: Any) -> dict[str, Any]:
        nonlocal inherited_called
        inherited_called = True
        raise AssertionError("return loader reached before activation")

    monkeypatch.setattr(campaign, "_inherited_run_development", forbidden)
    with pytest.raises(campaign.Campaign263Error, match="activation is absent"):
        campaign.run_development(argparse.Namespace())
    assert inherited_called is False


def test_snapshot_verification_and_value_range_are_frozen() -> None:
    receipt = json.loads(campaign.VERIFICATION_RECEIPT.read_text(encoding="utf-8"))
    assert _sha(campaign.VERIFICATION_RECEIPT) == campaign.VERIFICATION_RECEIPT_SHA256
    assert receipt["partitions"] == 33_015
    assert receipt["rows"] == 7_724_498
    assert receipt["eligible_rows"] == 7_724_491
    assert receipt["missing_rows"] == 7
    assert receipt["historical_daily_price_or_forward_return_values_read"] is False
