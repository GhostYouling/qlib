from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from scripts import a_share_three_day_walkforward_campaign057_features as runner


def _profile(scale: float = 1.0) -> np.ndarray:
    return scale * np.arange(1.0, runner.SELECTED_BAR_COUNT + 1.0)


def _raw_session(date: str, *, symbol: str = "SH600000") -> pd.DataFrame:
    morning = pd.date_range(f"{date} 09:30", periods=121, freq="1min")
    afternoon = pd.date_range(f"{date} 13:01", periods=120, freq="1min")
    timestamps = morning.append(afternoon)
    increments = np.resize(np.array([0.0, 0.001, -0.002, 0.003]), len(timestamps))
    closes = 10.0 * np.exp(np.cumsum(increments))
    return pd.DataFrame(
        {
            "datetime": timestamps,
            "symbol": symbol,
            "provider": "tushare",
            "close": closes,
        }
    ).loc[:, runner.RAW_COLUMNS]


def test_protocol_and_comparison_catalog_are_fingerprint_bound() -> None:
    protocol = runner._load_protocol()
    uniqueness = protocol["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]
    comparisons = uniqueness["comparison_factors"]
    assert len(comparisons) == runner.COMPARISON_COUNT == 80
    assert runner._comparison_order_digest(comparisons) == runner.COMPARISON_ORDER_SHA256
    assert comparisons[-1] == {
        "name": "intraday_day_over_day_amount_profile_similarity_240b",
        "score_direction": "higher",
    }


def test_similarity_identical_and_scale_invariant_profiles_equal_one() -> None:
    profile = _profile()
    values, eligible, quality = runner.compute_similarity_values(
        np.stack([profile, 11.0 * profile]),
        np.stack([3.0 * profile, 0.5 * profile]),
    )
    assert eligible.tolist() == [True, True]
    assert values == pytest.approx([1.0, 1.0], abs=1e-12)
    assert quality["eligible_rows"] == 2


def test_similarity_disjoint_clock_mass_equals_zero() -> None:
    current = np.zeros((1, runner.SELECTED_BAR_COUNT), dtype=float)
    prior = np.zeros_like(current)
    current[0, 0] = 1.0
    prior[0, -1] = 1.0
    values, eligible, _ = runner.compute_similarity_values(current, prior)
    assert eligible.tolist() == [True]
    assert values[0] == pytest.approx(0.0, abs=1e-12)


def test_similarity_retains_zero_bins_and_rejects_invalid_totals() -> None:
    current = np.stack([_profile(), np.zeros(238), _profile(), _profile()])
    prior = np.stack([_profile(), _profile(), _profile(), _profile()])
    current[2, 5] = -1.0
    prior[3, 7] = np.nan
    values, eligible, quality = runner.compute_similarity_values(current, prior)
    assert eligible.tolist() == [True, False, False, False]
    assert np.isnan(values[1:]).all()
    assert quality["nonpositive_current_total_absolute_return_rows"] == 1
    assert quality["negative_current_absolute_return_rows"] == 1
    assert quality["nonfinite_prior_absolute_return_rows"] == 1


def test_extract_profiles_enforces_grid_and_excludes_lunch_transition() -> None:
    raw = pd.concat(
        [_raw_session("2020-01-02"), _raw_session("2020-01-03")],
        ignore_index=True,
    )
    profiles, quality = runner.extract_absolute_return_profiles(
        raw, symbol="SH600000"
    )
    assert list(profiles) == [pd.Timestamp("2020-01-02"), pd.Timestamp("2020-01-03")]
    assert all(value.shape == (238,) for value in profiles.values())
    assert np.isfinite(np.concatenate(list(profiles.values()))).all()
    assert quality["source_sessions"] == 2
    bad = raw.drop(index=0).reset_index(drop=True)
    with pytest.raises(runner.Campaign057FeatureError, match="241 rows"):
        runner.extract_absolute_return_profiles(bad, symbol="SH600000")


def test_extract_profiles_rejects_nonpositive_close_without_repair() -> None:
    raw = _raw_session("2020-01-02")
    raw.loc[10, "close"] = 0.0
    profiles, quality = runner.extract_absolute_return_profiles(
        raw, symbol="SH600000"
    )
    assert np.isnan(profiles[pd.Timestamp("2020-01-02")]).all()
    assert quality["source_nonpositive_close_rows"] == 1


def test_output_uses_exact_previous_market_session_without_bridging() -> None:
    sessions = tuple(pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-06"]))
    previous = runner.previous_session_map(sessions)
    profile = _profile()
    base = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2020-01-02", "2020-01-03"]),
            "symbol": "SH600000",
            "provider": "tushare",
        }
    ).loc[:, runner.BASE_COLUMNS]
    profiles = {
        pd.Timestamp("2020-01-02"): profile,
        pd.Timestamp("2020-01-03"): 2.0 * profile,
    }
    output, quality = runner.compute_output_frame(
        base, profiles, previous, symbol="SH600000"
    )
    assert output[f"{runner.FACTOR_NAME}_eligible"].tolist() == [False, True]
    assert output.loc[1, runner.FACTOR_NAME] == pytest.approx(1.0, abs=1e-12)
    assert quality[f"{runner.FACTOR_NAME}__missing_prior_calendar_rows"] == 1

    suspended_base = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2020-01-02", "2020-01-06"]),
            "symbol": "SH600000",
            "provider": "tushare",
        }
    ).loc[:, runner.BASE_COLUMNS]
    suspended_profiles = {
        pd.Timestamp("2020-01-02"): profile,
        pd.Timestamp("2020-01-06"): profile,
    }
    suspended, suspended_quality = runner.compute_output_frame(
        suspended_base, suspended_profiles, previous, symbol="SH600000"
    )
    assert suspended[f"{runner.FACTOR_NAME}_eligible"].tolist() == [False, False]
    assert suspended_quality[f"{runner.FACTOR_NAME}__missing_prior_stock_session_rows"] == 1


def test_preregistration_records_no_value_and_no_return_boundary() -> None:
    concept = json.loads(
        (
            runner.REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_057_concept_scouting.json"
        ).read_text(encoding="utf-8")
    )
    mechanism = json.loads(
        (
            runner.REPO_ROOT
            / "docs/a_share_three_day_walkforward_campaign_057_mechanism_overlap_audit.json"
        ).read_text(encoding="utf-8")
    )
    protocol = json.loads(runner.DEFAULT_PROTOCOL.read_text(encoding="utf-8"))
    assert concept["research_boundary"]["external_campaign057_minute_partitions_read"] is False
    assert mechanism["decision"]["conceptual_independence_passed"] is True
    assert protocol["research_boundary"]["forward_return_fields_read_before_admissibility"] is False
    assert protocol["research_boundary"]["candidate49_ledgers_may_change"] is False
