from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from scripts import a_share_tushare_limit_up_queue_walkforward as campaign

ROOT = Path(__file__).resolve().parents[2]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_protocol_freezes_one_trial_folds_purge_costs_and_closed_stress() -> None:
    record = campaign._validate_protocol()
    assert record["search_space"]["trials"] == [
        {
            "trial_id": campaign.FROZEN_TRIAL_ID,
            "kind": "single_factor",
            "feature_set": [campaign.FACTOR_NAME],
            "weights": [1.0],
            "complexity": 1,
        }
    ]
    assert [
        item["validation"]["start"][:4] for item in record["development_folds"]
    ] == [
        "2021",
        "2022",
        "2023",
    ]
    assert record["split_protocol"]["purge_signal_sessions_each_boundary"] == 3
    assert (
        record["split_protocol"][
            "t_plus_1_and_t_plus_3_must_be_inside_the_same_train_or_validation_partition"
        ]
        is True
    )
    assert (
        record["fixed_execution_policy"]["primary_adverse_slippage_rate_each_side"]
        == 0.001
    )
    assert record["survivor_rule"]["development_aggregate_20bp_return_gt"] == 0.0
    assert record["exposed_stress_2024_2025"]["closed_during_development"] is True
    assert (
        record["exposed_stress_2024_2025"][
            "runner_command_exposed_in_this_implementation_stage"
        ]
        is False
    )


def test_real_plan_is_metadata_only_and_closed_before_admission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("Parquet value loader reached by plan")

    monkeypatch.setattr(pd, "read_parquet", forbidden)
    payload = campaign.build_plan()
    assert payload["ready"] is False
    assert payload["exit_code_if_executed"] == 2
    assert payload["checks"]["development_protocol_valid"] is True
    assert payload["checks"]["ordered_no_return_audit_admitted_one_factor"] is False
    assert payload["candidate_or_comparator_values_read"] is False
    assert payload["historical_daily_price_or_forward_return_values_read"] is False
    assert payload["partition_year_2024_or_2025_values_read"] is False
    assert payload["credential_loaded"] is False
    assert payload["provider_request_issued"] is False


def test_confirmed_run_cannot_reach_return_engine_while_plan_is_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reached = False

    def forbidden(_args: Any) -> dict[str, Any]:
        nonlocal reached
        reached = True
        raise AssertionError("return engine reached")

    monkeypatch.setattr(campaign, "_inherited_run_development", forbidden)
    with pytest.raises(campaign.Campaign115DevelopmentError, match="plan is not ready"):
        campaign.run_development(
            argparse.Namespace(confirm_development_trial=True, batch_size=8)
        )
    assert reached is False


def test_development_confirmation_is_mandatory() -> None:
    with pytest.raises(
        campaign.Campaign115DevelopmentError,
        match="confirmation is required",
    ):
        campaign.run_development(
            argparse.Namespace(confirm_development_trial=False, batch_size=8)
        )


def test_custom_factor_loader_reads_only_selected_2019_2023_session_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "source"
    dates = pd.DatetimeIndex(["2021-01-04", "2022-01-04"])
    for index, timestamp in enumerate(dates):
        root = source / "sessions" / timestamp.date().isoformat()
        root.mkdir(parents=True)
        pd.DataFrame(
            {
                "trade_date": [timestamp, timestamp],
                "instrument": ["SH600000", "SZ000001"],
                campaign.FACTOR_NAME: [0.0, 0.25 + 0.1 * index],
                "is_official_limit_up_event": [False, True],
                "provider": ["tushare", "tushare"],
            }
        ).to_parquet(root / "factor.parquet", index=False)
    monkeypatch.setattr(campaign, "SOURCE_ROOT", source)
    panel = campaign._factor_panel({}, range(2019, 2024), dates)
    assert list(panel.columns) == ["trade_date", "instrument", campaign.FACTOR_NAME]
    assert len(panel) == 4
    assert panel[campaign.FACTOR_NAME].between(0.0, 1.0).all()
    assert set(panel["trade_date"].dt.year) == {2021, 2022}


def test_factor_loader_rejects_any_2024_or_2025_request() -> None:
    with pytest.raises(campaign.Campaign115DevelopmentError, match="only 2019-2023"):
        campaign._factor_panel({}, range(2020, 2025), pd.DatetimeIndex(["2024-01-02"]))


def test_effective_campaign_is_exact_one_factor_when_admission_is_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        campaign,
        "_validate_admission",
        lambda: {
            "audit_sha256": "a" * 64,
            "semantic_receipt_sha256": "b" * 64,
            "source_manifest_sha256": "c" * 64,
            "source_dataset_sha256": "d" * 64,
        },
    )
    monkeypatch.setattr(campaign, "_validate_implementation_freeze", lambda: {})
    effective, protocol_sha = campaign.load_campaign(campaign.PROTOCOL)
    assert protocol_sha == campaign.PROTOCOL_SHA256
    assert [item["name"] for item in effective["factor_library"]] == [
        campaign.FACTOR_NAME
    ]
    assert campaign._build_trial_catalog(effective) == [
        {
            "trial_id": campaign.FROZEN_TRIAL_ID,
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": [campaign.FACTOR_NAME],
            "weights": [1.0],
            "complexity": 1,
        }
    ]
    assert effective["split_protocol"]["purge_signal_sessions_each_boundary"] == 3
    assert effective["survivor_rule"]["maximum_exposed_stress_survivors"] == 1


def test_inspect_before_any_trial_is_zero_value_and_zero_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "absent"
    monkeypatch.setattr(campaign, "OUTPUT_ROOT", output)
    payload = campaign.inspect_trial()
    assert payload["status"] == "no_campaign115_development_trial"
    assert payload["trial_ledger_present"] is False
    assert (
        payload["historical_daily_price_or_forward_return_values_read_by_inspection"]
        is False
    )
    assert payload["partition_year_2024_or_2025_values_read"] is False
    assert not output.exists()


def test_implementation_freeze_is_absent_or_binds_live_runner_and_tests() -> None:
    if not campaign.IMPLEMENTATION_FREEZE.exists():
        return
    record = json.loads(campaign.IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    assert record["protocol"]["sha256"] == campaign.PROTOCOL_SHA256
    assert record["runner"]["sha256"] == _sha(Path(campaign.__file__).resolve())
    assert record["tests"]["sha256"] == _sha(Path(__file__).resolve())
    assert (
        record["research_boundary"][
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        ]
        is False
    )


def test_candidate49_and_current_use_boundaries_remain_closed() -> None:
    record = campaign._validate_protocol()
    assert record["candidate49_boundary"]["only_active_prospective_candidate"] is True
    assert record["candidate49_boundary"]["historical_return_read_allowed"] is False
    assert (
        record["candidate49_boundary"]["prospective_ledgers_changed_by_campaign"]
        is False
    )
    assert record["research_output_boundary"]["current_scoring_allowed"] is False
    assert record["research_output_boundary"]["selection_allowed"] is False
    assert record["research_output_boundary"]["orders_allowed"] is False
    assert record["research_output_boundary"]["investment_advice"] is False
