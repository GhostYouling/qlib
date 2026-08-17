import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.a_share_three_day_walkforward_campaign020_features as FEATURES
import scripts.a_share_three_day_walkforward_campaign020 as WALKFORWARD


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_freshness_decay_has_exact_session_semantics() -> None:
    values, eligible, quality = FEATURES.compute_factor_values(
        trade_positions=np.array([100, 130, 160, 100], dtype=np.int64),
        effective_event_positions=np.array([100, 100, 100, -1], dtype=np.int64),
    )
    observed = values[FEATURES.FACTOR_NAME]
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [True, True, True, False]
    assert observed[:3].tolist() == pytest.approx([1.0, 2 ** -0.5, 0.5])
    assert np.isnan(observed[3])
    assert quality[
        f"{FEATURES.FACTOR_NAME}__no_prior_effective_disclosure_rows"
    ] == 1
    assert quality[f"{FEATURES.FACTOR_NAME}__eligible_rows"] == 3


def test_negative_age_and_invalid_shapes_fail_closed() -> None:
    with pytest.raises(FEATURES.Campaign020FeatureError):
        FEATURES.compute_factor_values(
            trade_positions=np.ones((1, 2), dtype=np.int64),
            effective_event_positions=np.ones((1, 2), dtype=np.int64),
        )
    values, eligible, quality = FEATURES.compute_factor_values(
        trade_positions=np.array([10], dtype=np.int64),
        effective_event_positions=np.array([11], dtype=np.int64),
    )
    assert eligible[FEATURES.FACTOR_NAME].tolist() == [False]
    assert np.isnan(values[FEATURES.FACTOR_NAME][0])
    assert quality[f"{FEATURES.FACTOR_NAME}__negative_session_age_rows"] == 1


def test_partition_reads_identity_only_and_uses_latest_effective_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    codes = [570] + list(FEATURES.market.CONTINUOUS_MINUTE_CODES)
    timestamps = [
        pd.Timestamp("2020-01-02") + pd.Timedelta(minutes=int(code))
        for code in codes
    ]
    raw = pd.DataFrame(
        {
            "datetime": timestamps,
            "symbol": "SH600000",
            "provider": "tushare",
        }
    ).loc[:, FEATURES.RAW_COLUMNS]
    base = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2020-01-02")],
            "symbol": ["SH600000"],
        }
    )
    calendar = np.array(
        ["2019-12-31", "2020-01-02"], dtype="datetime64[ns]"
    )
    monkeypatch.setitem(
        FEATURES.compute_partition_frame.__globals__,
        "_load_disclosure_events",
        lambda: (calendar, {"SH600000": np.array([0], dtype=np.int64)}),
    )
    frame, quality = FEATURES.compute_partition_frame(
        raw,
        base,
        None,
        symbol="SH600000",
    )
    assert tuple(frame.columns) == FEATURES.OUTPUT_COLUMNS
    assert frame["provider"].tolist() == ["eastmoney_disclosure_timing"]
    assert frame[f"{FEATURES.FACTOR_NAME}_eligible"].tolist() == [True]
    assert frame[FEATURES.FACTOR_NAME].tolist() == pytest.approx([2 ** (-1 / 60)])
    assert quality["base_rows"] == 1
    assert FEATURES.RAW_COLUMNS == ("datetime", "symbol", "provider")


def test_partition_rejects_changed_source_grid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = pd.DataFrame(
        {
            "datetime": [pd.Timestamp("2020-01-02 09:30")],
            "symbol": ["SH600000"],
            "provider": ["tushare"],
        }
    )
    base = pd.DataFrame(
        {
            "trade_date": [pd.Timestamp("2020-01-02")],
            "symbol": ["SH600000"],
        }
    )
    monkeypatch.setitem(
        FEATURES.compute_partition_frame.__globals__,
        "_load_disclosure_events",
        lambda: (
            np.array(["2020-01-02"], dtype="datetime64[ns]"),
            {"SH600000": np.array([0], dtype=np.int64)},
        ),
    )
    with pytest.raises(
        FEATURES.Campaign020FeatureError,
        match="241 identity rows",
    ):
        FEATURES.compute_partition_frame(
            raw.loc[:, FEATURES.RAW_COLUMNS],
            base,
            None,
            symbol="SH600000",
        )


def test_protocol_and_source_are_fingerprint_bound_before_values() -> None:
    concept = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_020_concept_scouting.json"
        ).read_text()
    )
    audit = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_020_mechanism_overlap_audit.json"
        ).read_text()
    )
    protocol = FEATURES.load_protocol()
    assert (
        FEATURES._sha256(FEATURES.CAMPAIGN019_FEATURE_RUNNER)
        == FEATURES.CAMPAIGN019_FEATURE_RUNNER_SHA256
    )
    assert FEATURES._sha256(FEATURES.DISCLOSURE_PATH) == FEATURES.DISCLOSURE_SHA256
    assert (
        FEATURES._sha256(FEATURES.DISCLOSURE_MANIFEST_PATH)
        == FEATURES.DISCLOSURE_MANIFEST_SHA256
    )
    assert concept["selected_concept"]["selected_decay_scale_sessions"] == 60
    assert concept["research_boundary"]["campaign020_candidate_values_read"] is False
    assert audit["selected_mechanism"]["name"] == FEATURES.FACTOR_NAME
    assert audit["decision"]["conceptually_independent"] is True
    comparisons = protocol["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]["comparison_factors"]
    assert len(comparisons) == 41
    assert comparisons[-1]["name"] == "intraday_bar_direction_continuity_238p"
    assert protocol["finite_post_admissibility_search"][
        "development_trial_count"
    ] == 1


def test_disclosure_loader_returns_only_timing_state() -> None:
    calendar, events = FEATURES.engine_namespace["_load_disclosure_events"]()
    assert calendar.ndim == 1
    assert calendar.dtype == np.dtype("datetime64[ns]")
    assert events
    assert all(
        isinstance(symbol, str)
        and positions.ndim == 1
        and positions.dtype == np.dtype("int64")
        and np.all(np.diff(positions) > 0)
        for symbol, positions in events.items()
    )


def test_generated_source_records_no_price_or_activity_read_boundary() -> None:
    source = FEATURES._source
    assert '"stock_day_datetime_symbol_provider_identity_read": True' in source
    assert '"quarterly_instrument_report_announcement_fields_read": True' in source
    assert '"quarterly_value_fields_read": False' in source
    assert '"minute_open_high_low_read": False' in source
    assert '"minute_close_read": False' in source
    assert '"minute_volume_read": False' in source
    assert 'value["source_open_high_low_read"] = False' in source
    assert 'value["source_close_read"] = False' in source
    assert 'value["source_volume_read"] = False' in source


def test_walkforward_catalog_is_the_single_frozen_trial() -> None:
    campaign, campaign_sha256 = WALKFORWARD.load_campaign(
        WALKFORWARD.engine_namespace["DEFAULT_CAMPAIGN"]
    )
    assert campaign_sha256 == (
        "1ff0bfc55247826eaed4aaa189888e51bb1580c71716c25a37a82c6e1c76b5ea"
    )
    assert WALKFORWARD.build_trial_catalog(campaign) == [
        {
            "trial_id": "wf020_single__quarterly_announcement_freshness_60s",
            "parent_trial_id": None,
            "kind": "single_factor",
            "feature_set": [FEATURES.FACTOR_NAME],
            "weights": [1.0],
            "complexity": 1,
        }
    ]


def test_terminal_record_and_additive_state_preserve_closed_stress() -> None:
    record = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_020_research_record.json"
        ).read_text()
    )
    state = json.loads(
        (
            REPO_ROOT
            / "docs/a_share_three_day_iteration_status_20260729_campaign020.json"
        ).read_text()
    )
    no_return = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_020"
            / "no_return/20260729T032544Z_campaign020_no_return_audit.json"
        ).read_text()
    )
    ledger = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_020"
            / "walkforward/trial_ledger.json"
        ).read_text()
    )
    survivors = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_020"
            / "walkforward/development_survivors.json"
        ).read_text()
    )
    stress = json.loads(
        (
            REPO_ROOT
            / "data/experiments/short_horizon/historical_walkforward/campaign_020"
            / "walkforward/exposed_stress_consumption_record.json"
        ).read_text()
    )
    manifest = json.loads(
        (
            FEATURES.output_root(Path("/Volumes/DIsk/qlib-a-share-tushare-1m"))
            / "snapshot_manifest.json"
        ).read_text()
    )
    assert manifest["source_fields_read"] == list(FEATURES.RAW_COLUMNS)
    assert manifest["quarterly_value_fields_read"] == []
    assert manifest["daily_price_fields_read"] == []
    assert manifest["forward_return_fields_read"] is False
    assert no_return["admissible_factor_names"] == [FEATURES.FACTOR_NAME]
    uniqueness = no_return["uniqueness"][FEATURES.FACTOR_NAME]
    assert uniqueness["all_required_comparisons_passed"] is True
    assert len(uniqueness["comparisons"]) == 41
    assert uniqueness[
        "maximum_observed_absolute_median_daily_rank_correlation"
    ] == pytest.approx(0.08488195024812292)
    assert len(ledger["entries"]) == 1
    assert record["status"] == (
        "completed_zero_development_survivors_stress_interval_not_opened"
    )
    assert record["development_result"]["frozen_trial_count"] == 1
    assert record["development_result"]["operationally_admissible_trial_count"] == 1
    assert record["development_result"]["trial"][
        "development_survivor_gate_passed"
    ] is False
    assert record["development_result"]["trial"][
        "positive_validation_mean_rank_ic_fold_count"
    ] == 2
    assert record["development_result"]["trial"][
        "positive_validation_pilot_10bp_return_fold_count"
    ] == 0
    assert survivors["selected_survivor_count"] == 0
    assert survivors["stress_return_fields_read"] is False
    assert stress["status"] == "not_opened_zero_development_survivors"
    assert stress["stress_interval_opened"] is False
    assert stress["stress_return_fields_read"] is False
    assert state["research_counts"][
        "recorded_historical_development_trial_count"
    ] == 242
    assert state["active_prospective_candidate"]["signal_ledger"]["entry_count"] == 0
    assert state["active_prospective_candidate"]["execution_ledger"]["entry_count"] == 0
    assert state["decision"][
        "campaign021_concept_scouting_and_separate_no_return_research_allowed"
    ] is True
