from __future__ import annotations

import copy
import json
from pathlib import Path

import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign as CAMPAIGN


REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN_CAMPAIGN_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_001r1_preregistration.json"
)
FINAL_RECORD_PATH = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_001r1_research_record.json"
)


def catalog_campaign() -> dict:
    return {
        "factor_library": [
            {"name": f"factor_{index}"} for index in range(8)
        ],
        "search_space": {
            "pair_weight_grid_for_canonical_factor_order": [
                [0.25, 0.75],
                [0.50, 0.50],
                [0.75, 0.25],
            ],
            "expected_trial_count": 92,
        },
    }


def test_frozen_catalog_has_all_singles_and_weighted_pairs() -> None:
    trials = CAMPAIGN.build_trial_catalog(catalog_campaign())

    assert len(trials) == 92
    assert sum(item["kind"] == "single_factor" for item in trials) == 8
    assert sum(item["kind"] == "pair_rank_blend" for item in trials) == 84
    assert len({item["trial_id"] for item in trials}) == 92


def test_catalog_rejects_candidate49() -> None:
    campaign = catalog_campaign()
    campaign["factor_library"][0]["name"] = (
        "intraday_cumulative_vwap_crossing_rate_240m"
    )

    with pytest.raises(CAMPAIGN.WalkForwardError, match="Candidate49"):
        CAMPAIGN.build_trial_catalog(campaign)


def test_fieldwise_overlay_outer_unions_supplement_keys() -> None:
    base = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2021-01-04"]),
            "instrument": ["SH600000"],
            "factor": [1.0],
        }
    )
    overlay = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2021-01-04", "2021-01-05"]),
            "instrument": ["SH600000", "SZ000001"],
            "factor": [2.0, 3.0],
        }
    )

    result = CAMPAIGN.apply_fieldwise_overlay(base, overlay, ["factor"])

    assert len(result) == 2
    assert result.set_index(["trade_date", "instrument"]).loc[
        (pd.Timestamp("2021-01-04"), "SH600000"), "factor"
    ] == 2.0
    assert result.set_index(["trade_date", "instrument"]).loc[
        (pd.Timestamp("2021-01-05"), "SZ000001"), "factor"
    ] == 3.0


def test_purged_schedule_contains_labels_and_drops_three_signals_each_side() -> None:
    calendar = pd.bdate_range("2021-01-01", periods=90)
    schedule = CAMPAIGN.global_signal_schedule(calendar)

    purged = CAMPAIGN.purged_period_schedule(
        schedule,
        calendar[6].date().isoformat(),
        calendar[-7].date().isoformat(),
        purge_signal_count=3,
    )

    assert not purged.empty
    assert purged["entry_date"].min() >= calendar[6]
    assert purged["exit_date"].max() <= calendar[-7]
    contained_without_purge = schedule.loc[
        schedule["signal_date"].between(calendar[6], calendar[-7])
        & schedule["entry_date"].between(calendar[6], calendar[-7])
        & schedule["exit_date"].between(calendar[6], calendar[-7])
    ]
    assert len(purged) == len(contained_without_purge) - 6
    assert purged.iloc[0]["signal_date"] == contained_without_purge.iloc[3][
        "signal_date"
    ]
    assert purged.iloc[-1]["signal_date"] == contained_without_purge.iloc[-4][
        "signal_date"
    ]


def test_append_only_ledger_detects_coherently_unlinked_edit(tmp_path: Path) -> None:
    campaign_path = tmp_path / "campaign.json"
    campaign_path.write_text("{}\n", encoding="utf-8")
    campaign_sha = CAMPAIGN.file_sha256(campaign_path)
    ledger_path = tmp_path / "ledger.json"
    ledger = CAMPAIGN.load_or_initialize_ledger(
        ledger_path, campaign_path, campaign_sha
    )
    payload = {
        "trial_id": "trial_1",
        "phase": "development_walkforward",
        "created_at": "2026-07-27T00:00:00+00:00",
    }
    ledger = CAMPAIGN.append_ledger_entry(
        ledger_path,
        ledger,
        payload,
        campaign_path,
        campaign_sha,
    )
    assert ledger["chain_tip_sha256"] != CAMPAIGN.CHAIN_GENESIS

    tampered = copy.deepcopy(ledger)
    tampered["entries"][0]["phase"] = "changed"
    ledger_path.write_text(
        json.dumps(tampered, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(CAMPAIGN.WalkForwardError, match="payload hash"):
        CAMPAIGN.validate_ledger(
            CAMPAIGN.load_json(ledger_path), campaign_path, campaign_sha
        )


def test_normalized_replay_uses_next_open_and_third_close() -> None:
    calendar = pd.bdate_range("2021-01-04", periods=8)
    quotes = {}
    for date in calendar:
        for instrument in ("SH600000", "SZ000001", "SZ300001"):
            quotes[(date, instrument)] = {
                "open": 10.0,
                "high": 10.5,
                "low": 9.5,
                "close": 10.0,
                "volume": 1_000_000.0,
                "amount": 10_000_000.0,
                "factor": 1.0,
            }
    for instrument in ("SH600000", "SZ000001", "SZ300001"):
        quotes[(calendar[3], instrument)]["close"] = 11.0
    schedule = pd.DataFrame(
        [
            {
                "signal_date": calendar[0],
                "entry_date": calendar[1],
                "exit_date": calendar[3],
            }
        ]
    )
    baskets = {
        calendar[0]: [
            {
                "signal_date": calendar[0],
                "entry_date": calendar[1],
                "planned_exit_date": calendar[3],
                "instrument": instrument,
                "rank": rank,
                "signal_close": 10.0,
                "signal_factor": 1.0,
            }
            for rank, instrument in enumerate(
                ("SH600000", "SZ000001", "SZ300001"), start=1
            )
        ]
    }

    result = CAMPAIGN.simulate_portfolio(
        quotes,
        calendar,
        schedule,
        baskets,
        pilot=False,
        slippage=0.0,
    )

    assert result["registered_signal_count"] == 1
    assert result["filled_entry_slot_count"] == 3
    assert result["terminal_unresolved_position_count"] == 0
    assert result["net_cumulative_return"] > 0.09


def test_real_campaign_freezes_92_trials_and_excludes_candidate49() -> None:
    frozen, _ = CAMPAIGN.load_campaign(FROZEN_CAMPAIGN_PATH)
    trials = CAMPAIGN.build_trial_catalog(frozen)
    names = {factor["name"] for factor in frozen["factor_library"]}

    assert len(trials) == 92
    assert "intraday_cumulative_vwap_crossing_rate_240m" not in names
    assert frozen["candidate49_boundary"]["historical_return_read_allowed"] is False
    assert frozen["lockbox"]["current_scoring_selection_sizing_or_orders_allowed"] is False
    assert frozen["survivor_rule"]["maximum_lockbox_survivors"] == 8


def test_completed_campaign_record_binds_full_ledger_and_zero_passers() -> None:
    record = json.loads(FINAL_RECORD_PATH.read_text(encoding="utf-8"))
    campaign, campaign_sha = CAMPAIGN.load_campaign(FROZEN_CAMPAIGN_PATH)
    ledger_binding = record["completed_artifacts"]["trial_ledger"]
    ledger_path = CAMPAIGN.resolve_bound_path(ledger_binding["path"])
    ledger = CAMPAIGN.validate_ledger(
        json.loads(ledger_path.read_text(encoding="utf-8")),
        FROZEN_CAMPAIGN_PATH.resolve(),
        campaign_sha,
    )

    assert record["status"] == "completed_lockbox_consumed_no_final_gate_passer"
    assert record["lockbox_outcome"]["final_gate_passer_count"] == 0
    assert record["candidate49_boundary"]["historical_return_read"] is False
    assert record["candidate49_boundary"]["candidate50_started"] is False
    assert CAMPAIGN.file_sha256(ledger_path) == ledger_binding["sha256"]
    assert len(ledger["entries"]) == 100
    assert sum(entry["phase"] == "development_walkforward" for entry in ledger["entries"]) == 92
    assert sum(
        entry["phase"] == "locked_2024_2025_backtest"
        for entry in ledger["entries"]
    ) == 8
    assert all(
        entry["status_and_rejection_reason"]["status"] == "lockbox_rejected"
        for entry in ledger["entries"][-8:]
    )
    assert (
        campaign["candidate49_boundary"]["historical_return_read_allowed"] is False
    )
