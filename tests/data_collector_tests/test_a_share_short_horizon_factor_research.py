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
            "market_breadth_5": [-0.01, 0.01, 0.02],
            "market_breadth_20": [-0.02, 0.02, 0.01],
        }
    )
    assert RESEARCH.apply_regime_filter(frame, "breadth_5_positive").index.tolist() == [1, 2]
    assert RESEARCH.apply_regime_filter(frame, "breadth_5_above_20").index.tolist() == [0, 2]
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
