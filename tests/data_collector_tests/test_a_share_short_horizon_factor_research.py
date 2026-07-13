"""Offline tests for short-horizon factor research safeguards."""

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "a_share_short_horizon_factor_research.py"
SPEC = importlib.util.spec_from_file_location("a_share_short_horizon_factor_research", SCRIPT_PATH)
RESEARCH = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = RESEARCH
SPEC.loader.exec_module(RESEARCH)


def test_annual_report_dates_and_symbol_mapping():
    assert RESEARCH.annual_report_dates(2023, 2025) == ["2023-12-31", "2024-12-31", "2025-12-31"]
    assert RESEARCH.qlib_symbol("600000") == "SH600000"
    assert RESEARCH.qlib_symbol("300001") == "SZ300001"
    assert RESEARCH.qlib_symbol("200001") is None


def test_quality_join_waits_until_next_trading_day():
    market = pd.DataFrame(
        {
            "instrument": ["SZ000001"] * 4,
            "datetime": pd.to_datetime(["2024-04-29", "2024-04-30", "2024-05-06", "2024-05-07"]),
        }
    )
    fundamentals = pd.DataFrame(
        {
            "instrument": ["SZ000001"],
            "report_date": pd.to_datetime(["2023-12-31"]),
            "announcement_date": pd.to_datetime(["2024-04-30"]),
            "roe": [8.0],
            "net_profit": [1.0],
            "revenue_yoy": [5.0],
            "profit_yoy": [10.0],
        }
    )
    joined = RESEARCH.attach_quality_asof(market, fundamentals)
    assert not joined.loc[joined["datetime"] == pd.Timestamp("2024-04-30"), "quality_eligible"].item()
    effective = joined.loc[joined["datetime"] == pd.Timestamp("2024-05-06")].iloc[0]
    assert effective["quality_eligible"]
    assert effective["quality_effective_date"] == pd.Timestamp("2024-05-06")


def test_winner_uses_development_only():
    summaries = [
        {"candidate": "development_winner", "development_selection_score": 0.20, "test": {"annualized_return": -0.99}},
        {"candidate": "test_winner", "development_selection_score": 0.10, "test": {"annualized_return": 9.99}},
    ]
    assert RESEARCH.choose_winner(summaries) == "development_winner"


def test_no_development_candidate_is_selected_when_every_policy_score_is_missing():
    summaries = [
        {"candidate": "one", "selection_scores": {"positive_year_stability_mdd20": None}},
        {"candidate": "two", "selection_scores": {"positive_year_stability_mdd20": None}},
    ]
    assert RESEARCH.choose_winner(summaries, "positive_year_stability_mdd20") is None


def test_stability_selection_prefers_the_best_worst_development_year_without_test_metrics():
    summaries = [
        {
            "candidate": "pooled_only",
            "development_selection_score": 0.30,
            "selection_scores": {"positive_year_stability": 0.01},
            "test": {"net_cumulative_return": 9.0},
        },
        {
            "candidate": "stable",
            "development_selection_score": 0.10,
            "selection_scores": {"positive_year_stability": 0.03},
            "test": {"net_cumulative_return": -9.0},
        },
    ]
    assert RESEARCH.choose_winner(summaries, "positive_year_stability") == "stable"


def test_regime_ranking_uses_development_score_only_and_keeps_unqualified_rules_last():
    summaries = [
        (
            "always",
            {
                "selection_scores": {"positive_year_stability_mdd20": 0.01},
                "test": {"net_cumulative_return": -9.0},
            },
        ),
        (
            "breadth_5_above_20",
            {
                "selection_scores": {"positive_year_stability_mdd20": 0.03},
                "test": {"net_cumulative_return": -99.0},
            },
        ),
        (
            "breadth_20_positive",
            {
                "selection_scores": {"positive_year_stability_mdd20": None},
                "test": {"net_cumulative_return": 99.0},
            },
        ),
    ]
    ranked = RESEARCH.rank_regimes_by_development(summaries, "positive_year_stability_mdd20")
    assert [item[0] for item in ranked] == ["breadth_5_above_20", "always", "breadth_20_positive"]


def test_basket_overlap_summary_counts_common_dates_and_pairwise_similarity():
    left = {"2025-01-01": {"A", "B", "C"}, "2025-01-06": {"D", "E", "F"}}
    right = {"2025-01-01": {"A", "B", "G"}, "2025-01-06": {"D", "E", "F"}, "2025-01-09": {"X", "Y", "Z"}}
    metrics = RESEARCH.basket_overlap_metrics(left, right)
    assert metrics["common_signal_dates"] == 2
    assert metrics["mean_jaccard"] == pytest.approx(0.75)
    assert metrics["exact_basket_rate"] == pytest.approx(0.5)
    assert metrics["any_overlap_rate"] == pytest.approx(1.0)


def test_basket_correlation_uses_only_trailing_close_known_returns():
    dates = pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07"])
    scored = pd.DataFrame(
        {
            "datetime": list(dates) * 3,
            "instrument": ["A"] * 4 + ["B"] * 4 + ["C"] * 4,
            "close": [100.0, 110.0, 99.0, 108.9, 100.0, 120.0, 96.0, 115.2, 100.0, 90.0, 99.0, 89.1],
        }
    )
    rows = RESEARCH.basket_correlation_rows(scored, {"2025-01-07": {"A", "B", "C"}}, lookback_days=3)
    row = rows.iloc[0]
    assert row["valid_return_days"] == 3
    assert row["mean_pairwise_correlation"] == pytest.approx(-1.0 / 3.0)
    assert row["max_pairwise_correlation"] == pytest.approx(1.0)
    summary = RESEARCH.summarize_basket_correlation(
        rows, pd.DataFrame({"signal_date": dates[-1:], "net_return": [-0.02]}), lookback_days=3
    )
    assert summary["basket_count"] == 1
    assert summary["valid_correlation_basket_count"] == 1
    with pytest.raises(ValueError, match="at least two"):
        RESEARCH.basket_correlation_rows(scored, {"2025-01-07": {"A", "B"}}, lookback_days=1)


def test_diversified_topk_skips_highly_correlated_name_and_requires_a_complete_basket():
    dates = pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07", "2025-01-08"])
    scored = pd.DataFrame(
        {
            "datetime": list(dates) * 3,
            "instrument": ["A"] * 5 + ["B"] * 5 + ["C"] * 5,
            "close": [100.0, 110.0, 99.0, 108.9, 98.01, 100.0, 120.0, 96.0, 115.2, 92.16, 100.0, 90.0, 99.0, 89.1, 98.01],
            "score": [0.9] * 5 + [0.8] * 5 + [0.7] * 5,
        }
    )
    selected, statuses = RESEARCH.select_diversified_topk(
        scored,
        hold_days=1,
        topk=2,
        regime_filter="always",
        max_pairwise_correlation=0.5,
        correlation_lookback=2,
        candidate_pool=3,
    )
    latest_signal = dates[2]
    assert statuses.loc[statuses["datetime"] == latest_signal, "diversification_basket_formed"].item()
    assert set(selected.loc[selected["datetime"] == latest_signal, "instrument"]) == {"A", "C"}
    assert not statuses.loc[statuses["datetime"] == dates[0], "diversification_basket_formed"].item()
    with pytest.raises(ValueError, match="between -1 and 1"):
        RESEARCH.select_diversified_topk(scored, 1, 2, "always", 1.1, 2, 3)


def test_selection_risk_gates_require_close_known_low_volatility_and_low_range_ranks():
    frame = pd.DataFrame(
        {
            "volatility_low_20": [0.10, 0.30, 0.50],
            "amplitude_low": [0.50, 0.30, 0.60],
        }
    )
    assert RESEARCH.apply_selection_risk_gates(frame, 0.20, None).index.tolist() == [1, 2]
    assert RESEARCH.apply_selection_risk_gates(frame, None, 0.40).index.tolist() == [0, 2]
    assert RESEARCH.apply_selection_risk_gates(frame, 0.20, 0.40).index.tolist() == [2]
    with pytest.raises(ValueError, match="between zero and one"):
        RESEARCH.apply_selection_risk_gates(frame, 1.01, None)


def test_selected_basket_trade_details_uses_next_open_and_scheduled_exit_close():
    dates = pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07"])
    scored = pd.DataFrame(
        {
            "datetime": list(dates) * 2,
            "instrument": ["A"] * 4 + ["B"] * 4,
            "open": [10.0, 10.0, 11.0, 12.0, 20.0, 20.0, 19.0, 18.0],
            "close": [10.0, 10.5, 11.0, 12.0, 20.0, 19.5, 19.0, 18.0],
            "score": [0.9] * 4 + [0.8] * 4,
        }
    )
    details = RESEARCH.selected_basket_trade_details(
        scored, {"2025-01-02": {"A", "B"}}, hold_days=2, open_cost=0.0, close_cost=0.0
    )
    assert details["instrument"].tolist() == ["A", "B"]
    assert details["entry_date"].tolist() == [pd.Timestamp("2025-01-03")] * 2
    assert details["exit_date"].tolist() == [pd.Timestamp("2025-01-06")] * 2
    assert details["entry_gap_return"].tolist() == pytest.approx([0.0, 0.0])
    assert details.loc[details["instrument"] == "A", "net_return"].item() == pytest.approx(0.10)
    assert details.loc[details["instrument"] == "B", "net_return"].item() == pytest.approx(-0.05)


def test_entry_gap_cap_holds_cash_for_the_entire_incomplete_topk_cohort():
    dates = pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07"])
    rows = []
    for instrument, opening_prices in {
        "A": [10.0, 10.0, 10.0, 10.0],
        "B": [10.0, 10.0, 10.0, 10.0],
        "C": [10.0, 11.0, 10.0, 10.0],
    }.items():
        for date, opening_price in zip(dates, opening_prices):
            rows.append(
                {
                    "datetime": date,
                    "instrument": instrument,
                    "open": opening_price,
                    "close": 10.0,
                    "score": {"A": 0.9, "B": 0.8, "C": 0.7}[instrument],
                }
            )
    rounds, _ = RESEARCH.evaluate_candidate(
        pd.DataFrame(rows),
        RESEARCH.Candidate("entry_gap_test", "test", {"quality_score": 1.0}),
        hold_days=1,
        topk=3,
        open_cost=0.0,
        close_cost=0.0,
        development_end="2025-12-31",
        max_entry_gap=0.04,
    )
    assert rounds["entry_gap_basket_formed"].tolist() == [False, True]
    assert rounds["holdings"].tolist() == [0, 3]
    assert rounds["net_return"].tolist() == pytest.approx([0.0, 0.0])
    with pytest.raises(ValueError, match="strictly between zero and one"):
        RESEARCH.validate_entry_gap_cap(0.0)


def test_missing_future_quote_remains_as_a_cash_cohort_instead_of_being_dropped():
    dates = pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07"])
    rows = []
    for instrument in ("A", "B", "C"):
        for date in dates:
            if instrument == "C" and date == pd.Timestamp("2025-01-03"):
                continue
            rows.append(
                {
                    "datetime": date,
                    "instrument": instrument,
                    "open": 10.0,
                    "close": 10.0,
                    "score": {"A": 0.9, "B": 0.8, "C": 0.7}[instrument],
                }
            )
    rounds, _ = RESEARCH.evaluate_candidate(
        pd.DataFrame(rows),
        RESEARCH.Candidate("missing_quote_test", "test", {"quality_score": 1.0}),
        hold_days=1,
        topk=3,
        open_cost=0.0,
        close_cost=0.0,
        development_end="2025-12-31",
    )
    assert rounds["market_data_basket_formed"].tolist() == [False]
    assert rounds["holdings"].tolist() == [0]
    assert rounds["net_return"].tolist() == pytest.approx([0.0])


def test_human_report_includes_no_eligible_pressure_scans_without_creating_a_winner():
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []},
        {"signals": [], "settlements": []},
        no_eligible_studies=[
            {
                "run_id": "long-history",
                "candidate_library": "v4_freshness",
                "candidate_count": 176,
                "selection_policy": "positive_year_stability_mdd20",
            }
        ],
    )
    assert "未产生合格候选的压力扫描" in report
    assert "long-history" in report
    assert "无合格候选" in report


def test_strict_stability_policy_requires_a_development_drawdown_at_or_above_minus_twenty_percent():
    assert RESEARCH.stability_score_with_drawdown_cap(0.02, -0.20) == pytest.approx(0.02)
    assert RESEARCH.stability_score_with_drawdown_cap(0.02, -0.200001) is None
    assert RESEARCH.stability_score_with_drawdown_cap(None, -0.05) is None
    summaries = [
        {
            "candidate": "too_much_drawdown",
            "selection_scores": {"positive_year_stability_mdd20": None},
            "test": {"net_cumulative_return": 9.0},
        },
        {
            "candidate": "risk_capped",
            "selection_scores": {"positive_year_stability_mdd20": 0.01},
            "test": {"net_cumulative_return": -9.0},
        },
    ]
    assert RESEARCH.choose_winner(summaries, "positive_year_stability_mdd20") == "risk_capped"


def test_positive_year_stability_requires_every_development_year_to_be_positive():
    assert RESEARCH.positive_year_stability_score([0.03, 0.01], -0.08) == pytest.approx(-0.03)
    assert RESEARCH.positive_year_stability_score([0.03, -0.01, 0.08], -0.08) is None
    assert RESEARCH.positive_year_stability_score([0.03], -0.08) is None
    assert RESEARCH.positive_year_stability_score([0.03, 0.01], None) is None


def test_close_loss_cap_uses_the_first_breaching_daily_close_without_reallocating():
    trades = pd.DataFrame(
        {
            "instrument": ["SZ000001", "SZ000002"],
            "entry_date": pd.to_datetime(["2025-01-02", "2025-01-02"]),
            "exit_date": pd.to_datetime(["2025-01-06", "2025-01-06"]),
            "entry_open": [100.0, 100.0],
            "planned_exit_close": [101.0, 99.0],
        }
    )
    quotes = pd.DataFrame(
        {
            "instrument": ["SZ000001"] * 3 + ["SZ000002"] * 3,
            "datetime": pd.to_datetime(
                ["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-02", "2025-01-03", "2025-01-06"]
            ),
            "close": [98.0, 94.0, 101.0, 96.0, 97.0, 99.0],
        }
    )
    capped = RESEARCH.apply_close_loss_cap(trades, quotes, 0.05)
    first, second = capped.itertuples(index=False)
    assert first.close_loss_cap_triggered
    assert first.actual_exit_date == pd.Timestamp("2025-01-03")
    assert first.actual_exit_close == pytest.approx(94.0)
    assert not second.close_loss_cap_triggered
    assert second.actual_exit_date == pd.Timestamp("2025-01-06")
    assert second.actual_exit_close == pytest.approx(99.0)
    uncapped = RESEARCH.apply_close_loss_cap(trades, quotes, None)
    assert not uncapped["close_loss_cap_triggered"].any()
    with pytest.raises(ValueError, match="strictly between zero and one"):
        RESEARCH.apply_close_loss_cap(trades, quotes, 0.0)


def test_candidate_lookup_rejects_unrecorded_factor_mix():
    assert RESEARCH.candidate_by_name("quality_trend_pullback").weights["momentum_10"] == 0.25
    assert RESEARCH.candidate_by_name("expanded_multi_horizon_q25_profit").weights["quality_profit"] == 0.25
    with pytest.raises(ValueError, match="unknown candidate"):
        RESEARCH.candidate_by_name("made_up_factor_mix")


def test_candidate_library_contains_exactly_one_hundred_predeclared_strategies():
    candidates = RESEARCH.CANDIDATES
    assert len(candidates) == 100
    assert len({candidate.name for candidate in candidates}) == 100
    assert len(RESEARCH.BASELINE_CANDIDATES) == 5
    assert len(RESEARCH.EXPANDED_SIGNAL_BLUEPRINTS) == 19
    assert len(RESEARCH.QUALITY_OVERLAYS) == 5
    assert all(sum(candidate.weights.values()) == pytest.approx(1.0) for candidate in candidates)


def test_v2_microstructure_library_is_versioned_and_keeps_v1_intact():
    v1 = RESEARCH.candidate_library("v1")
    v2 = RESEARCH.candidate_library("v2_microstructure")
    assert len(v1) == 100
    assert len(v2) == 150
    assert tuple(candidate.name for candidate in v2[:100]) == tuple(candidate.name for candidate in v1)
    assert RESEARCH.candidate_by_name("expanded_v2_micro_reversal_1_q05_composite", "v2_microstructure").weights[
        "reversal_1"
    ] == pytest.approx(0.304)
    assert RESEARCH.candidate_library_fingerprint(v1) != RESEARCH.candidate_library_fingerprint(v2)
    with pytest.raises(ValueError, match="unknown candidate_library"):
        RESEARCH.candidate_library("unrecorded")


def test_v3_quality_grid_is_a_nonduplicating_systematic_extension_of_v2():
    v2 = RESEARCH.candidate_library("v2_microstructure")
    v3 = RESEARCH.candidate_library("v3_quality_grid")
    additions = v3[len(v2) :]
    assert len(v3) == 170
    assert len(additions) == 20
    assert tuple(candidate.name for candidate in v3[: len(v2)]) == tuple(candidate.name for candidate in v2)
    assert {candidate.weights.get("quality_revenue") for candidate in additions if "quality_revenue" in candidate.weights} == {
        0.05,
        0.10,
        0.15,
        0.20,
        0.25,
    }
    v2_signatures = {tuple(sorted(candidate.weights.items())) for candidate in v2}
    assert all(tuple(sorted(candidate.weights.items())) not in v2_signatures for candidate in additions)
    assert RESEARCH.candidate_by_name("expanded_v3_quiet_long_trend_q10_growth", "v3_quality_grid").weights[
        "trend_ma_60"
    ] == pytest.approx(0.27)


def test_v4_freshness_library_adds_close_known_disclosure_age_weight_variants():
    v3 = RESEARCH.candidate_library("v3_quality_grid")
    v4 = RESEARCH.candidate_library("v4_freshness")
    additions = v4[len(v3) :]
    assert len(v4) == 176
    assert len(additions) == 6
    assert tuple(candidate.name for candidate in v4[: len(v3)]) == tuple(candidate.name for candidate in v3)
    candidate = RESEARCH.candidate_by_name("expanded_v4_quiet_long_trend_q15_revenue_f10", "v4_freshness")
    assert candidate.weights["quality_revenue"] == pytest.approx(0.15)
    assert candidate.weights["quality_freshness"] == pytest.approx(0.10)
    assert candidate.weights["trend_ma_60"] == pytest.approx(0.225)


def test_v5_defensive_library_systematically_adds_low_volatility_and_low_range_variants():
    v4 = RESEARCH.candidate_library("v4_freshness")
    v5 = RESEARCH.candidate_library("v5_defensive")
    additions = v5[len(v4) :]
    assert len(v5) == 206
    assert len(additions) == 30
    assert tuple(candidate.name for candidate in v5[: len(v4)]) == tuple(candidate.name for candidate in v4)
    assert {candidate.name.split("_q", 1)[0] for candidate in additions} == {
        "expanded_v5_defensive_low_volatility",
        "expanded_v5_defensive_low_range",
        "expanded_v5_defensive_dual_risk",
    }
    assert {candidate.weights.get("quality_roe") for candidate in additions if "quality_roe" in candidate.weights} == {
        0.10,
        0.15,
    }
    low_volatility = RESEARCH.candidate_by_name("expanded_v5_defensive_low_volatility_q15_revenue", "v5_defensive")
    dual_risk = RESEARCH.candidate_by_name("expanded_v5_defensive_dual_risk_q10_growth", "v5_defensive")
    assert low_volatility.weights["volatility_low_20"] == pytest.approx(0.17)
    assert dual_risk.weights["volatility_low_20"] == pytest.approx(0.18)
    assert dual_risk.weights["amplitude_low"] == pytest.approx(0.162)


def test_iteration_registry_is_append_only_and_uses_a_predeclared_test_gate(tmp_path):
    winner = {
        "candidate": "expanded_reversal_trend_20_q25_profit",
        "development_selection_score": 0.12,
        "development": {"rounds": 100, "net_cumulative_return": 0.25, "max_drawdown": -0.10},
        "test": {"rounds": 24, "net_cumulative_return": 0.05, "max_drawdown": -0.08},
    }
    iteration = RESEARCH.build_iteration_record(
        run_id="iteration-one",
        label="hold_3d_top_20",
        strategy={"holding_period_trading_days": 3, "topk": 20},
        study_path=tmp_path / "study.json",
        winner=winner,
        candidate_count=100,
        data={"calendar_end": "2026-07-13"},
    )
    assert iteration["promotion"]["status"] == "passed_initial_test"
    assert not iteration["selection"]["test_metrics_used_for_selection"]
    registry_path = tmp_path / "strategy_registry.json"
    RESEARCH.append_strategy_registry(registry_path, iteration)
    with pytest.raises(ValueError, match="already contains"):
        RESEARCH.append_strategy_registry(registry_path, iteration)
    stored = json.loads(registry_path.read_text(encoding="utf-8"))
    assert stored["iterations"][0]["candidate_library"]["count"] == 100


def test_initial_test_gate_rejects_short_or_loss_making_test_periods():
    passed, failures = RESEARCH.initial_test_gate(
        {"rounds": 19, "net_cumulative_return": -0.01, "max_drawdown": -0.21}
    )
    assert not passed
    assert len(failures) == 3


def test_top_three_requires_three_valid_members_instead_of_an_impossible_floor_of_five():
    assert RESEARCH.minimum_required_holdings(3) == 3
    assert RESEARCH.minimum_required_holdings(4) == 4
    assert RESEARCH.minimum_required_holdings(10) == 8
    with pytest.raises(ValueError, match="topk must be positive"):
        RESEARCH.minimum_required_holdings(0)


def test_research_only_iteration_cannot_be_promoted_even_if_its_historical_test_passes(tmp_path):
    winner = {
        "candidate": "expanded_trend_ma_confirmation_q20_composite",
        "development_selection_score": 0.12,
        "development": {"rounds": 100, "net_cumulative_return": 0.25, "max_drawdown": -0.10},
        "test": {"rounds": 24, "net_cumulative_return": 0.05, "max_drawdown": -0.08},
    }
    iteration = RESEARCH.build_iteration_record(
        run_id="historical-diagnostic",
        label="top3-historical",
        strategy={"holding_period_trading_days": 3, "topk": 3},
        study_path=tmp_path / "study.json",
        winner=winner,
        candidate_count=100,
        data={"calendar_end": "2026-07-13"},
        promotion_eligible=False,
    )
    assert iteration["promotion"]["status"] == "research_only_not_promoted"
    assert not iteration["promotion"]["eligible_for_promotion"]
    assert "not eligible for promotion" in iteration["promotion"]["failures"][-1]


def test_market_breadth_regime_filter_is_close_known_and_validated():
    frame = pd.DataFrame(
        {
            "market_breadth_5": [-0.01, 0.01, 0.02, 0.01],
            "market_breadth_20": [-0.02, 0.02, 0.01, -0.02],
        }
    )
    assert RESEARCH.apply_regime_filter(frame, "breadth_5_positive").index.tolist() == [1, 2, 3]
    assert RESEARCH.apply_regime_filter(frame, "breadth_20_positive").index.tolist() == [1, 2]
    assert RESEARCH.apply_regime_filter(frame, "breadth_5_above_20").index.tolist() == [0, 2, 3]
    assert RESEARCH.apply_regime_filter(frame, "breadth_5_and_20_positive").index.tolist() == [1, 2]
    assert RESEARCH.apply_regime_filter(frame, "breadth_5_positive_and_above_20").index.tolist() == [2, 3]
    assert RESEARCH.apply_regime_filter(frame, "breadth_5_above_20_and_20_positive").index.tolist() == [2]
    with pytest.raises(ValueError, match="unknown regime_filter"):
        RESEARCH.apply_regime_filter(frame, "not_a_regime")


def test_execution_plan_refuses_an_inactive_regime_screen(tmp_path):
    screen_path = tmp_path / "inactive_screen.json"
    screen_path.write_text(json.dumps({"execution_allowed": False, "top_candidates": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="regime is inactive"):
        RESEARCH.run_execution_plan(SimpleNamespace(screen_path=str(screen_path)))


def test_paper_settlement_waits_for_future_sessions_and_applies_research_costs():
    calendar = pd.DatetimeIndex(pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-05", "2026-01-06"]))
    instruments = [f"SZ00000{number}" for number in range(1, 6)]
    signal = {
        "signal_id": "iteration:2026-01-01",
        "signal_date": "2026-01-01",
        "strategy": {"holding_period_trading_days": 3, "open_cost": 0.001, "close_cost": 0.002},
        "top_candidates": [{"instrument": instrument} for instrument in instruments],
    }
    quotes = pd.DataFrame(
        [
            {"datetime": calendar[1], "instrument": instrument, "open": 10.0, "close": 10.0}
            for instrument in instruments
        ]
        + [
            {"datetime": calendar[3], "instrument": instrument, "open": 11.0, "close": 11.0}
            for instrument in instruments
        ]
    )
    settlement = RESEARCH.paper_settlement(signal, calendar, quotes)
    assert settlement is not None
    assert settlement["entry_date"] == "2026-01-02"
    assert settlement["exit_date"] == "2026-01-06"
    assert settlement["holdings"] == 5
    assert settlement["net_return"] == pytest.approx((1 - 0.001) * 1.1 * (1 - 0.002) - 1)
    assert RESEARCH.paper_settlement(signal, calendar[:3], quotes) is None


def test_promoted_iteration_selects_the_latest_passed_record(tmp_path):
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "iterations": [
                    {"iteration_id": "failed", "promotion": {"status": "research_only_not_promoted"}},
                    {"iteration_id": "passed", "promotion": {"status": "passed_initial_test"}},
                ],
            }
        ),
        encoding="utf-8",
    )
    assert RESEARCH.promoted_iteration(registry_path)["iteration_id"] == "passed"
    assert RESEARCH.promoted_iteration(registry_path, "passed")["iteration_id"] == "passed"


def test_development_only_iteration_can_be_explicitly_registered_for_separate_forward_observation(tmp_path):
    iteration = {
        "iteration_id": "v2-development-only",
        "strategy": {"candidate_library": "v2_microstructure"},
        "selection": {"winner": "expanded_v2_quiet_long_trend_q20_composite"},
        "data": {"calendar_end": "2025-12-31", "development_end": "2025-12-31"},
        "initial_test": {"rounds": 0},
        "promotion": {"status": "research_only_not_promoted"},
    }
    registry_path = tmp_path / "strategy_registry.json"
    registry_path.write_text(json.dumps({"schema_version": 1, "iterations": [iteration]}), encoding="utf-8")
    selected = RESEARCH.research_observation_iteration(registry_path, "v2-development-only")
    shadow_path = tmp_path / "shadow_observations.json"
    plan = RESEARCH.append_shadow_observation(
        shadow_path, iteration=selected, not_before="2026-07-14"
    )
    assert plan["observations"][0]["candidate"] == "expanded_v2_quiet_long_trend_q20_composite"
    assert plan["observations"][0]["not_before"] == "2026-07-14"
    with pytest.raises(ValueError, match="already contains"):
        RESEARCH.append_shadow_observation(shadow_path, iteration=selected, not_before="2026-07-14")


def test_shadow_observation_refuses_an_iteration_with_a_historical_test_window(tmp_path):
    registry_path = tmp_path / "strategy_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "iterations": [
                    {
                        "iteration_id": "historical-diagnostic",
                        "data": {"calendar_end": "2026-07-13", "development_end": "2025-12-31"},
                        "initial_test": {"rounds": 38},
                        "promotion": {"status": "research_only_not_promoted"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="no historical test window"):
        RESEARCH.research_observation_iteration(registry_path, "historical-diagnostic")


def test_research_report_renders_registry_and_only_counts_settled_paper_returns():
    registry = {
        "iterations": [
            {
                "label": "three_day_cycle",
                "strategy": {"holding_period_trading_days": 3, "topk": 10, "regime_filter": "breadth_5_above_20"},
                "selection": {"winner": "candidate", "development": {"net_cumulative_return": 0.1}},
                "initial_test": {"net_cumulative_return": 0.02, "max_drawdown": -0.05},
                "promotion": {"status": "passed_initial_test"},
            }
        ]
    }
    ledger = {
        "signals": [{"signal_id": "settled"}, {"signal_id": "pending"}],
        "settlements": [{"signal_id": "settled", "net_return": 0.03}],
    }
    report = RESEARCH.render_three_day_research_report(registry, ledger)
    assert "three_day_cycle" in report
    assert "已记录信号：2 笔；已结算：1 笔；待结算：1 笔。" in report
    assert "已结算纸面累计净收益：+3.00%" in report


def test_research_report_marks_non_promotable_historical_diagnostics():
    registry = {
        "iterations": [
            {
                "label": "historical-top3",
                "strategy": {"holding_period_trading_days": 3, "topk": 3},
                "selection": {"winner": "candidate", "development": {}},
                "initial_test": {},
                "promotion": {
                    "status": "research_only_not_promoted",
                    "eligible_for_promotion": False,
                },
            }
        ]
    }
    assert "历史诊断，不可晋级" in RESEARCH.render_three_day_research_report(registry, {"signals": [], "settlements": []})


def test_regime_audits_are_retained_in_the_research_report_without_promotion(tmp_path):
    (tmp_path / "20260713T152638Z_regime_audit.json").write_text(
        json.dumps(
            {
                "run_id": "20260713T152638Z",
                "status": "completed",
                "candidate": {"name": "defensive_candidate"},
                "data": {"calendar_start": "2019-01-02", "calendar_end": "2025-12-31"},
                "selection_policy": "positive_year_stability_mdd20",
                "winner_regime_selected_on_development_only": None,
                "ranking_by_development": [
                    {"development_selection_score": None},
                    {"development_selection_score": None},
                ],
            }
        ),
        encoding="utf-8",
    )
    audits = RESEARCH.load_regime_audits(tmp_path)
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []}, {"signals": [], "settlements": []}, regime_audits=audits
    )
    assert "市场状态审计" in report
    assert "defensive_candidate" in report
    assert "无合格状态（0/2）" in report
    assert "不能回写既有策略" in report


def test_loss_cap_audits_are_retained_in_the_research_report_without_promotion(tmp_path):
    (tmp_path / "20260713T160011Z_loss_cap_audit.json").write_text(
        json.dumps(
            {
                "run_id": "20260713T160011Z",
                "status": "completed",
                "candidate": {"name": "defensive_candidate"},
                "data": {"calendar_start": "2019-01-02", "calendar_end": "2025-12-31"},
                "selection_policy": "positive_year_stability_mdd20",
                "winner_close_loss_cap_selected_on_development_only": None,
                "ranking_by_development": [
                    {"close_loss_cap": None, "development_selection_score": None},
                    {"close_loss_cap": 0.05, "development_selection_score": None},
                ],
            }
        ),
        encoding="utf-8",
    )
    audits = RESEARCH.load_loss_cap_audits(tmp_path)
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []}, {"signals": [], "settlements": []}, loss_cap_audits=audits
    )
    assert "收盘损失上限审计" in report
    assert "defensive_candidate" in report
    assert "无合格损失上限（0/2）" in report
    assert "原三日周期内保持现金" in report


def test_entry_gap_audits_are_retained_in_the_research_report_without_promotion(tmp_path):
    (tmp_path / "20260713T164955Z_entry_gap_audit.json").write_text(
        json.dumps(
            {
                "run_id": "20260713T164955Z",
                "status": "completed",
                "candidate": {"name": "defensive_candidate"},
                "data": {"calendar_start": "2019-01-02", "calendar_end": "2026-07-13"},
                "selection_policy": "positive_year_stability_mdd20",
                "winner_max_entry_gap_selected_on_development_only": None,
                "has_development_qualified_entry_gap": False,
                "ranking_by_development": [
                    {"max_entry_gap": None, "development_selection_score": None},
                    {"max_entry_gap": 0.02, "development_selection_score": None},
                ],
            }
        ),
        encoding="utf-8",
    )
    audits = RESEARCH.load_entry_gap_audits(tmp_path)
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []}, {"signals": [], "settlements": []}, entry_gap_audits=audits
    )
    assert "次日开盘跳空审计" in report
    assert "defensive_candidate" in report
    assert "无合格跳空上限（0/2）" in report


def test_correlation_audits_record_full_windows_and_unqualified_diversification(tmp_path):
    (tmp_path / "old_basket_correlation_audit.json").write_text(
        json.dumps({"status": "completed", "correlation_summary": {}}), encoding="utf-8"
    )
    (tmp_path / "full_basket_correlation_audit.json").write_text(
        json.dumps(
            {
                "run_id": "full-window",
                "status": "completed",
                "candidate": {"name": "defensive_candidate"},
                "data": {"calendar_start": "2019-01-02", "calendar_end": "2025-12-31"},
                "correlation_summary": {
                    "required_return_days": 20,
                    "valid_correlation_basket_count": 12,
                    "max_pairwise_correlation_p90": 0.68,
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "20260713T161805Z_diversification_audit.json").write_text(
        json.dumps(
            {
                "run_id": "diversification",
                "status": "completed",
                "candidate": {"name": "defensive_candidate"},
                "data": {"calendar_start": "2019-01-02", "calendar_end": "2025-12-31"},
                "selection_policy": "positive_year_stability_mdd20",
                "winner_max_pairwise_correlation_selected_on_development_only": None,
                "has_development_qualified_diversification_cap": False,
                "ranking_by_development": [
                    {"development_selection_score": None},
                    {"development_selection_score": None},
                ],
            }
        ),
        encoding="utf-8",
    )
    correlation_audits = RESEARCH.load_basket_correlation_audits(tmp_path)
    diversification_audits = RESEARCH.load_diversification_audits(tmp_path)
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []},
        {"signals": [], "settlements": []},
        basket_correlation_audits=correlation_audits,
        diversification_audits=diversification_audits,
    )
    assert len(correlation_audits) == 1
    assert "篮子相关性审计" in report
    assert "0.68" in report
    assert "相关性分散化审计" in report
    assert "无合格上限（0/2）" in report


def test_research_report_labels_development_only_preregistration_for_forward_observation():
    registry = {
        "iterations": [
            {
                "label": "v2-development-only",
                "strategy": {"holding_period_trading_days": 3, "topk": 3},
                "data": {"calendar_end": "2025-12-31", "development_end": "2025-12-31"},
                "selection": {"winner": "candidate", "development": {}},
                "initial_test": {"rounds": 0},
                "promotion": {"status": "research_only_not_promoted", "eligible_for_promotion": False},
            }
        ]
    }
    assert "开发期预登记，前瞻观察" in RESEARCH.render_three_day_research_report(
        registry, {"signals": [], "settlements": []}
    )


def test_research_report_keeps_shadow_observation_results_separate():
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []},
        {"signals": [], "settlements": []},
        {
            "signals": [{"signal_id": "shadow"}],
            "settlements": [{"signal_id": "shadow", "net_return": 0.02}],
        },
    )
    assert "研究候选前瞻纸面观察" in report
    assert "已结算纸面累计净收益：+2.00%" in report


def test_shadow_observation_report_breaks_out_each_candidate_instead_of_pooling_them():
    shadow_registry = {
        "observations": [
            {
                "iteration_id": "first",
                "candidate": "candidate_one",
                "candidate_library": "v2_microstructure",
                "not_before": "2026-07-14",
            },
            {
                "iteration_id": "second",
                "candidate": "candidate_two",
                "candidate_library": "v2_microstructure",
                "not_before": "2026-07-14",
            },
        ]
    }
    shadow_ledger = {
        "signals": [
            {"signal_id": "first:2026-07-14", "iteration_id": "first"},
            {"signal_id": "second:2026-07-14", "iteration_id": "second"},
        ],
        "settlements": [{"signal_id": "first:2026-07-14", "net_return": 0.03}],
    }
    report = RESEARCH.render_three_day_research_report(
        {"iterations": []}, {"signals": [], "settlements": []}, shadow_ledger, shadow_registry
    )
    assert "candidate_one" in report
    assert "candidate_two" in report
    assert "| candidate_one | v2_microstructure | 2026-07-14 | 1 | 1 | 0 | +3.00% |" in report
    assert "| candidate_two | v2_microstructure | 2026-07-14 | 1 | 0 | 1 | — |" in report


def test_current_st_names_are_excluded_from_screen_by_default():
    screen = pd.DataFrame({"instrument": ["SZ000001", "SZ000002"]})
    metadata = {"SZ000001": {"is_st": False}, "SZ000002": {"is_st": True}}
    assert RESEARCH.filter_st_candidates(screen, metadata, include_st=False)["instrument"].tolist() == ["SZ000001"]
    assert len(RESEARCH.filter_st_candidates(screen, metadata, include_st=True)) == 2


def test_return_metrics_include_cost_adjusted_cumulative_return():
    rounds = pd.DataFrame(
        {
            "net_return": [0.10, -0.05],
            "gross_return": [0.11, -0.04],
            "holdings": [30, 28],
        }
    )
    metrics = RESEARCH.return_metrics(rounds, hold_days=5)
    assert metrics["rounds"] == 2
    assert round(metrics["net_cumulative_return"], 6) == round(1.10 * 0.95 - 1.0, 6)
    assert metrics["max_drawdown"] < 0


def test_a_share_fee_rules_apply_user_commission_and_sell_stamp_duty():
    rules = RESEARCH.AShareExecutionRules()
    buy = RESEARCH.a_share_trade_fees(10_000.0, "buy", rules)
    sell = RESEARCH.a_share_trade_fees(10_000.0, "sell", rules)
    assert buy == {"commission": 1.0, "transfer_fee": 0.2, "stamp_duty": 0.0, "total": 1.2}
    assert sell == {"commission": 1.0, "transfer_fee": 0.2, "stamp_duty": 5.0, "total": 6.2}


def test_board_lot_plan_skips_unaffordable_name_without_reallocating_cash():
    rules = RESEARCH.AShareExecutionRules()
    candidates = [
        {"rank": 1, "instrument": "SZ300972", "name": "万辰集团", "reference_close": 192.28},
        {"rank": 2, "instrument": "SZ300043", "name": "星辉娱乐", "reference_close": 4.81},
        {"rank": 3, "instrument": "SZ300251", "name": "光线传媒", "reference_close": 11.80},
    ]
    plan = RESEARCH.plan_lot_orders(candidates, 100_000.0, rules)
    high_price, star, light = plan["orders"]
    assert high_price["status"] == "skipped_insufficient_budget_for_one_lot"
    assert star["quantity"] == 1000
    assert light["quantity"] == 400
    assert plan["summary"]["planned_candidates"] == 2
    assert plan["summary"]["actual_gross_exposure"] < 0.15
    assert plan["summary"]["unused_pilot_budget"] > 0
