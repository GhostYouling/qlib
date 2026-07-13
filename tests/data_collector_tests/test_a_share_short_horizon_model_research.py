"""Offline safety tests for the three-day walk-forward model audit."""

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "a_share_short_horizon_model_research.py"
SPEC = importlib.util.spec_from_file_location("a_share_short_horizon_model_research", SCRIPT_PATH)
MODEL = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODEL
SPEC.loader.exec_module(MODEL)


def test_annual_segments_keep_later_dates_out_of_development_selection():
    dates = pd.DatetimeIndex(
        pd.to_datetime(["2022-12-30", "2023-01-03", "2023-12-29", "2024-01-02", "2024-12-31", "2026-01-05"])
    )
    segments = MODEL.annual_evaluation_segments(dates, "2023-01-01", "2024-12-31")
    assert [(name, values.tolist()) for name, values in segments] == [
        ("development_2023", [pd.Timestamp("2023-01-03"), pd.Timestamp("2023-12-29")]),
        ("development_2024", [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-12-31")]),
        ("test", [pd.Timestamp("2026-01-05")]),
    ]


def test_model_audit_reuses_the_main_research_fundamental_snapshot_default():
    assert MODEL.DEFAULT_FUNDAMENTALS == MODEL.research.DEFAULT_FUNDAMENTALS


def test_model_feature_set_is_immutable_when_exploratory_diagnostic_catalog_grows():
    expected = {factor for candidate in MODEL.research.V7_CANDIDATES for factor in candidate.weights}
    assert set(MODEL.DEFAULT_FEATURES) == expected
    assert "momentum_3" in MODEL.research.FACTOR_DIAGNOSTIC_COLUMNS
    assert "momentum_3" not in MODEL.DEFAULT_FEATURES


def test_deterministic_daily_sample_is_label_independent_and_capped():
    rows = []
    for signal_date in pd.to_datetime(["2024-01-02", "2024-01-05"]):
        for instrument, label in zip(["A", "B", "C", "D"], [99.0, -99.0, 50.0, -50.0]):
            rows.append({"signal_date": signal_date, "instrument": instrument, "forward_gross_return": label})
    frame = pd.DataFrame(rows)
    sampled = MODEL.deterministic_daily_sample(frame, 2)
    relabeled = frame.copy()
    relabeled["forward_gross_return"] *= -1.0
    sampled_relabeled = MODEL.deterministic_daily_sample(relabeled, 2)
    assert sampled.groupby("signal_date").size().tolist() == [2, 2]
    assert sampled[["signal_date", "instrument"]].equals(sampled_relabeled[["signal_date", "instrument"]])


def test_topk_model_rounds_hold_cash_if_a_selected_future_quote_is_missing():
    signal = pd.Timestamp("2024-01-02")
    predictions = pd.DataFrame(
        {
            "signal_date": [signal] * 4,
            "instrument": ["A", "B", "C", "D"],
            "score": [0.9, 0.8, 0.7, 0.6],
        }
    )
    labels = pd.DataFrame(
        {
            "signal_date": [signal] * 3,
            "instrument": ["A", "B", "D"],
            "forward_gross_return": [0.10, 0.20, 0.50],
        }
    )
    rounds, metrics = MODEL.score_topk_rounds(
        predictions, labels, pd.DatetimeIndex([signal]), topk=3, open_cost=0.0, close_cost=0.0
    )
    assert rounds.loc[0, "holdings"] == 0
    assert rounds.loc[0, "net_return"] == 0.0
    assert metrics["traded_rounds"] == 0


def test_topk_model_rounds_hold_cash_when_a_close_known_regime_is_inactive():
    first, second = pd.to_datetime(["2024-01-02", "2024-01-05"])
    predictions = pd.DataFrame(
        {
            "signal_date": [first] * 3 + [second] * 3,
            "instrument": ["A", "B", "C"] * 2,
            "score": [0.9, 0.8, 0.7] * 2,
        }
    )
    labels = pd.DataFrame(
        {
            "signal_date": [first] * 3 + [second] * 3,
            "instrument": ["A", "B", "C"] * 2,
            "forward_gross_return": [0.03, 0.02, 0.01] * 2,
        }
    )
    rounds, metrics = MODEL.score_topk_rounds(
        predictions,
        labels,
        pd.DatetimeIndex([first, second]),
        topk=3,
        open_cost=0.0,
        close_cost=0.0,
        active_signal_dates=pd.DatetimeIndex([second]),
    )
    assert rounds["regime_active"].tolist() == [False, True]
    assert rounds["holdings"].tolist() == [0, 3]
    assert rounds["net_return"].tolist() == pytest.approx([0.0, 0.02])
    assert metrics["rounds"] == 2
    assert metrics["traded_rounds"] == 1


def test_active_regime_dates_rejects_unknown_market_gate():
    with pytest.raises(ValueError, match="unknown model regime_filter"):
        MODEL.active_regime_dates(
            pd.DataFrame({"datetime": pd.to_datetime(["2024-01-02"]), "quality_eligible": [True]}),
            pd.DatetimeIndex([pd.Timestamp("2024-01-02")]),
            "not_a_real_gate",
        )


def test_model_selection_requires_all_development_years_positive_and_drawdown_gate():
    years = [
        {"topk": {"net_cumulative_return": 0.04}},
        {"topk": {"net_cumulative_return": 0.02}},
    ]
    assert MODEL.configuration_selection_score(years, {"max_drawdown": -0.10}) == pytest.approx(-0.03)
    assert MODEL.configuration_selection_score(years, {"max_drawdown": -0.21}) is None
    assert MODEL.configuration_selection_score(
        [{"topk": {"net_cumulative_return": 0.04}}, {"topk": {"net_cumulative_return": -0.01}}],
        {"max_drawdown": -0.10},
    ) is None
