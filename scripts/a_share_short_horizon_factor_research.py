#!/usr/bin/env python3
"""Research short-horizon A-share price-volume factors with a quality gate.

The script deliberately separates two operations:

``sync-fundamentals``
    Downloads annual-report quality fields from Eastmoney and preserves the
    public announcement date needed for a conservative point-in-time join.

``run``
    Evaluates predefined five-session long-only factor combinations.  Every
    candidate is written to its own JSON file below ``data/experiments``;
    selection uses only the development period and is then reported on the
    later, untouched test period.

This is a research harness, not investment advice or an execution system.  It
does not claim exchange-grade point-in-time accounting data or
limit-up/limit-down execution.  The ``plan`` command adds auditable A-share
lot sizing for a current screen, but it is deliberately separate from the
adjusted-price historical research backtest.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "data"
DEFAULT_PROVIDER_URI = DATA_ROOT / "qlib" / "cn_a_share"
DEFAULT_FUNDAMENTALS = DATA_ROOT / "raw" / "a_share" / "fundamentals" / "annual_quality.parquet"
DEFAULT_FUNDAMENTAL_MANIFEST = DATA_ROOT / "metadata" / "annual_quality_manifest.json"
DEFAULT_QUARTERLY_FUNDAMENTALS = DATA_ROOT / "raw" / "a_share" / "fundamentals" / "quarterly_quality.parquet"
DEFAULT_QUARTERLY_FUNDAMENTAL_MANIFEST = DATA_ROOT / "metadata" / "quarterly_quality_manifest.json"
DEFAULT_PERFORMANCE_FORECASTS = DATA_ROOT / "raw" / "a_share" / "fundamentals" / "performance_forecasts.parquet"
DEFAULT_PERFORMANCE_FORECAST_MANIFEST = DATA_ROOT / "metadata" / "performance_forecasts_manifest.json"
DEFAULT_BILLBOARD_EVENTS = DATA_ROOT / "raw" / "a_share" / "events" / "daily_billboard.parquet"
DEFAULT_BILLBOARD_EVENT_MANIFEST = DATA_ROOT / "metadata" / "daily_billboard_manifest.json"
DEFAULT_MAJOR_HOLDER_EVENTS = DATA_ROOT / "raw" / "a_share" / "events" / "major_holder_changes.parquet"
DEFAULT_MAJOR_HOLDER_EVENT_MANIFEST = DATA_ROOT / "metadata" / "major_holder_changes_manifest.json"
DEFAULT_BLOCK_TRADE_EVENTS = DATA_ROOT / "raw" / "a_share" / "events" / "block_trades.parquet"
DEFAULT_BLOCK_TRADE_EVENT_MANIFEST = DATA_ROOT / "metadata" / "block_trades_manifest.json"
DEFAULT_MARGIN_FINANCING_EVENTS = DATA_ROOT / "raw" / "a_share" / "events" / "margin_financing_top_flows.parquet"
DEFAULT_MARGIN_FINANCING_EVENT_MANIFEST = DATA_ROOT / "metadata" / "margin_financing_top_flows_manifest.json"
DEFAULT_INSTITUTIONAL_SURVEY_EVENTS = DATA_ROOT / "raw" / "a_share" / "events" / "institutional_surveys.parquet"
DEFAULT_INSTITUTIONAL_SURVEY_EVENT_MANIFEST = DATA_ROOT / "metadata" / "institutional_surveys_manifest.json"
DEFAULT_REPURCHASE_EVENTS = DATA_ROOT / "raw" / "a_share" / "events" / "repurchase_plans.parquet"
DEFAULT_REPURCHASE_EVENT_MANIFEST = DATA_ROOT / "metadata" / "repurchase_plans_manifest.json"
DEFAULT_HOLDER_COUNT_EVENTS = DATA_ROOT / "raw" / "a_share" / "events" / "holder_count_changes.parquet"
DEFAULT_HOLDER_COUNT_EVENT_MANIFEST = DATA_ROOT / "metadata" / "holder_count_changes_manifest.json"
DEFAULT_PLEDGE_EVENTS = DATA_ROOT / "raw" / "a_share" / "events" / "share_pledges.parquet"
DEFAULT_PLEDGE_EVENT_MANIFEST = DATA_ROOT / "metadata" / "share_pledges_manifest.json"
DEFAULT_DIVIDEND_PLAN_EVENTS = DATA_ROOT / "raw" / "a_share" / "events" / "dividend_plans.parquet"
DEFAULT_DIVIDEND_PLAN_EVENT_MANIFEST = DATA_ROOT / "metadata" / "dividend_plans_manifest.json"
DEFAULT_EXPERIMENT_ROOT = DATA_ROOT / "experiments" / "short_horizon"
DEFAULT_STRATEGY_REGISTRY = DEFAULT_EXPERIMENT_ROOT / "strategy_registry.json"
DEFAULT_PAPER_LEDGER = DEFAULT_EXPERIMENT_ROOT / "three_day_paper_ledger.json"
DEFAULT_SHADOW_OBSERVATION_REGISTRY = DEFAULT_EXPERIMENT_ROOT / "shadow_observation_registry.json"
DEFAULT_SHADOW_SUSPENSION_REGISTRY = DEFAULT_EXPERIMENT_ROOT / "shadow_observation_suspensions.json"
DEFAULT_SHADOW_PAPER_LEDGER = DEFAULT_EXPERIMENT_ROOT / "three_day_shadow_paper_ledger.json"
DEFAULT_PROSPECTIVE_FACTOR_REGISTRY = DEFAULT_EXPERIMENT_ROOT / "prospective_factor_registry.json"
DEFAULT_PROSPECTIVE_FACTOR_LEDGER = DEFAULT_EXPERIMENT_ROOT / "three_day_prospective_factor_ledger.json"
DEFAULT_RESEARCH_REPORT = DEFAULT_EXPERIMENT_ROOT / "three_day_research_report.md"
DEFAULT_FACTOR_DIAGNOSTIC_INVALIDATIONS = REPO_ROOT / "docs" / "a_share_factor_diagnostic_invalidations.json"
DEFAULT_PILOT_CAPITALS = (200_000.0,)
REQUIRED_PRICE_BASIS = "close_known_raw_pct_chg_chain_v1"
PRICE_BASIS_MANIFEST_NAME = "price_basis.json"

PROSPECTIVE_VWAP_FACTOR = "close_below_vwap_1"
PROSPECTIVE_VWAP_SOURCE_FACTOR = "close_above_vwap_1"
PROSPECTIVE_VWAP_REGISTRATION_ID = "prospective_close_below_vwap_1_20260714"
PROSPECTIVE_VWAP_EARLIEST_NOT_BEFORE = "2026-07-14"
PROSPECTIVE_VWAP_SOURCE_RUN_ID = "20260714T082752Z"
PROSPECTIVE_VWAP_SOURCE_DIAGNOSTIC = (
    DEFAULT_EXPERIMENT_ROOT / "20260714T082752Z_factor_diagnostic.json"
)
PROSPECTIVE_VWAP_HYPOTHESIS = (
    "Within the close-known, quality-eligible and non-ST A-share universe, stocks whose closing price ranks "
    "lower relative to the same-session VWAP will have a higher return from the next session open to the "
    "third trading-session close."
)
PROSPECTIVE_VWAP_TOPK = 3
PROSPECTIVE_VWAP_HOLD_DAYS = 3
PROSPECTIVE_VWAP_OPEN_COST = 0.00012
PROSPECTIVE_VWAP_CLOSE_COST = 0.00062


def complete_rolling_window_expression(expression: str, required_prior_sessions: int) -> str:
    """Require the declared local history without changing complete-window values."""

    if required_prior_sessions < 1:
        raise ValueError("required_prior_sessions must be positive")
    return f"({expression}) + 0*Ref($close, {required_prior_sessions})"


SIGNED_EFFICIENCY_RATIO_10_EXPRESSION = (
    "($close/Ref($close, 10) - 1)/Sum(Abs($close/Ref($close, 1) - 1), 10)"
)
RETURN_TURNOVER_CORRELATION_10_EXPRESSION = complete_rolling_window_expression(
    "Corr($close/Ref($close, 1) - 1, $turnover, 10)", 10
)
# Qlib's rolling ``Max`` accepts a partial history by default.  Multiplying a
# 20-session reference by zero makes the expression missing until that
# reference exists, enforcing the preregistered complete-window requirement
# without altering any valid 20-session value.
MAX_RETURN_20_EXPRESSION = "Max($close/Ref($close, 1) - 1, 20) + 0*Ref($close, 20)"
COMPRESSION_CONSENSUS_MIN_COMPONENTS = (
    "amplitude_low",
    "amplitude_low_1",
    "volatility_low_20",
    "volume_dry_up",
)

EASTMONEY_DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
EASTMONEY_REPORT = "RPT_LICO_FN_CPD"
EASTMONEY_PERFORMANCE_FORECAST_REPORT = "RPT_PUBLIC_OP_NEWPREDICT"
EASTMONEY_BILLBOARD_REPORT = "RPT_DAILYBILLBOARD_DETAILSNEW"
EASTMONEY_MAJOR_HOLDER_REPORT = "RPT_SHARE_HOLDER_INCREASE"
EASTMONEY_BLOCK_TRADE_REPORT = "RPT_DATA_BLOCKTRADE"
EASTMONEY_MARGIN_FINANCING_REPORT = "RPTA_WEB_RZRQ_GGMX"
EASTMONEY_INSTITUTIONAL_SURVEY_REPORT = "RPT_ORG_SURVEY"
EASTMONEY_REPURCHASE_REPORT = "RPTA_WEB_GETHGLIST_NEW"
EASTMONEY_HOLDER_COUNT_REPORT = "RPT_HOLDERNUM_DET"
EASTMONEY_PLEDGE_REPORT = "RPTA_APP_ACCUMDETAILS"
EASTMONEY_DIVIDEND_PLAN_REPORT = "RPT_SHAREBONUS_DET"
FUNDAMENTAL_COLUMNS = (
    "instrument",
    "report_date",
    "announcement_date",
    "roe",
    "net_profit",
    "revenue_yoy",
    "profit_yoy",
)
PERFORMANCE_FORECAST_COLUMNS = (
    "instrument",
    "report_date",
    "announcement_date",
    "forecast_type",
    "forecast_turnaround",
    "forecast_profit_yoy",
    "forecast_profit_yoy_width",
)
FORECAST_FACTOR_DIAGNOSTIC_COLUMNS = (
    "forecast_profit_yoy",
    "forecast_profit_yoy_precision",
    "forecast_freshness",
    "forecast_turnaround",
)
BILLBOARD_EVENT_COLUMNS = (
    "instrument",
    "trade_date",
    "billboard_net_flow_to_float",
    "billboard_net_flow_to_deal",
    "billboard_deal_to_float",
    "billboard_reason_count",
)
BILLBOARD_FACTOR_DIAGNOSTIC_COLUMNS = (
    "billboard_net_flow_to_float",
    "billboard_net_flow_to_deal",
    "billboard_deal_to_float",
    "billboard_reason_count",
    "billboard_freshness",
)
MAJOR_HOLDER_EVENT_COLUMNS = (
    "instrument",
    "announcement_date",
    "major_holder_net_change_free_ratio",
    "major_holder_increase_free_ratio",
    "major_holder_decrease_free_ratio",
    "major_holder_event_count",
)
MAJOR_HOLDER_FACTOR_DIAGNOSTIC_COLUMNS = (
    "major_holder_net_change_free_ratio",
    "major_holder_increase_free_ratio",
    "major_holder_decrease_free_ratio",
    "major_holder_event_count",
    "major_holder_freshness",
)
BLOCK_TRADE_EVENT_COLUMNS = (
    "instrument",
    "trade_date",
    "block_trade_premium_ratio",
    "block_trade_turnover_rate",
    "block_trade_event_count",
)
BLOCK_TRADE_FACTOR_DIAGNOSTIC_COLUMNS = (
    "block_trade_premium_ratio",
    "block_trade_turnover_rate",
    "block_trade_event_count",
    "block_trade_freshness",
)
MARGIN_FINANCING_EVENT_COLUMNS = (
    "instrument",
    "trade_date",
    "margin_net_buy_to_market_cap",
    "margin_buy_to_market_cap",
    "margin_balance_to_market_cap",
    "margin_financing_balance_growth",
)
MARGIN_FINANCING_FACTOR_DIAGNOSTIC_COLUMNS = (
    "margin_net_buy_to_market_cap",
    "margin_buy_to_market_cap",
    "margin_balance_to_market_cap",
    "margin_financing_balance_growth",
)
INSTITUTIONAL_SURVEY_EVENT_COLUMNS = (
    "instrument",
    "announcement_date",
    "institutional_survey_org_count",
    "institutional_survey_event_count",
)
INSTITUTIONAL_SURVEY_FACTOR_DIAGNOSTIC_COLUMNS = (
    "institutional_survey_org_count",
    "institutional_survey_event_count",
    "institutional_survey_freshness",
)
REPURCHASE_EVENT_COLUMNS = (
    "instrument",
    "announcement_date",
    "repurchase_planned_share_ratio",
    "repurchase_planned_amount",
)
REPURCHASE_FACTOR_DIAGNOSTIC_COLUMNS = (
    "repurchase_planned_share_ratio",
    "repurchase_planned_amount",
    "repurchase_freshness",
)
HOLDER_COUNT_EVENT_COLUMNS = (
    "instrument",
    "announcement_date",
    "holder_count_change_ratio",
    "holder_count_change_absolute",
)
HOLDER_COUNT_FACTOR_DIAGNOSTIC_COLUMNS = (
    "holder_count_change_ratio",
    "holder_count_change_absolute",
    "holder_count_freshness",
)
PLEDGE_EVENT_COLUMNS = (
    "instrument",
    "announcement_date",
    "pledge_share_count",
    "pledge_total_share_ratio",
    "pledge_event_count",
)
PLEDGE_FACTOR_DIAGNOSTIC_COLUMNS = (
    "pledge_share_count",
    "pledge_total_share_ratio",
    "pledge_event_count",
    "pledge_freshness",
)
DIVIDEND_PLAN_EVENT_COLUMNS = (
    "instrument",
    "announcement_date",
    "dividend_cash_per_ten",
    "dividend_share_ratio",
    "dividend_plan_event_count",
)
DIVIDEND_PLAN_FACTOR_DIAGNOSTIC_COLUMNS = (
    "dividend_cash_per_ten",
    "dividend_share_ratio",
    "dividend_plan_event_count",
    "dividend_plan_freshness",
)
MARGIN_FINANCING_TOP_N = 100
# This direction is deliberately not part of the development diagnostic
# catalog.  It was formed after reading the completed 2019--2025 diagnostic,
# so it may only be evaluated in a separately recorded post-development
# holdout; it is never automatically eligible as a candidate-library factor.
BILLBOARD_HOLDOUT_FACTOR = "billboard_low_deal_to_float"
BILLBOARD_HOLDOUT_HYPOTHESIS = (
    "Among quality-eligible stocks with a daily billboard event no older than the declared window, "
    "a lower billboard deal amount relative to free-float market capitalization is associated with a higher "
    "subsequent three-trading-day return."
)


@dataclass(frozen=True)
class Candidate:
    """One predeclared factor combination used in the first research sweep."""

    name: str
    description: str
    weights: dict[str, float]


@dataclass(frozen=True)
class SelectionMultiplicityInput:
    """Development-only candidate returns retained for a selection-bias audit."""

    study: dict[str, Any]
    candidates: tuple[str, ...]
    signal_dates: pd.DatetimeIndex
    net_returns: np.ndarray
    holdings: np.ndarray
    observed: np.ndarray


@dataclass(frozen=True)
class AShareExecutionRules:
    """Execution conventions for a small, long-only A-share pilot.

    ``commission_rate`` is the user's all-in broker commission quote.  The
    exchange handling fee is intentionally not added a second time because it
    is commonly embedded in that quote; configure it separately only if a
    broker statement proves it is charged separately.
    """

    lot_size: int = 100
    commission_rate: float = 0.0001
    commission_min: float = 0.0
    transfer_fee_rate: float = 0.00002
    stamp_duty_rate: float = 0.0005
    max_gross_exposure: float = 0.15
    target_weight: float = 0.05

    def validate(self) -> None:
        if self.lot_size < 1:
            raise ValueError("lot_size must be positive")
        for name, value in (
            ("commission_rate", self.commission_rate),
            ("commission_min", self.commission_min),
            ("transfer_fee_rate", self.transfer_fee_rate),
            ("stamp_duty_rate", self.stamp_duty_rate),
            ("max_gross_exposure", self.max_gross_exposure),
            ("target_weight", self.target_weight),
        ):
            if value < 0:
                raise ValueError(f"{name} must not be negative")
        if self.max_gross_exposure > 1.0 or self.target_weight > 1.0:
            raise ValueError("portfolio weights must be no greater than one")


# All candidates intentionally use the same accounting-quality gate.  This
# makes their comparison about the short-horizon price-volume signal rather
# than about a different quality universe.  The five original candidates are
# kept as stable baselines; the 95 expanded candidates are generated from
# deterministic signal blueprints and quality overlays before any backtest is
# run.  They are not tuned using the 2026 test period.
BASELINE_CANDIDATES = (
    Candidate(
        name="quality_breakout",
        description="Five/ten-day continuation with volume and turnover expansion near a 20-day high.",
        weights={
            "momentum_5": 0.20,
            "momentum_10": 0.20,
            "volume_surge": 0.20,
            "turnover_surge": 0.15,
            "near_high_20": 0.10,
            "volatility_target": 0.05,
            "quality_score": 0.10,
        },
    ),
    Candidate(
        name="quality_acceleration",
        description="Volume/turnover acceleration with positive intraday strength and moderate-high volatility.",
        weights={
            "momentum_10": 0.20,
            "volume_surge": 0.25,
            "turnover_surge": 0.20,
            "intraday_strength": 0.15,
            "volatility_target": 0.10,
            "near_high_20": 0.05,
            "quality_score": 0.05,
        },
    ),
    Candidate(
        name="quality_pullback",
        description="Short-term pullback/reversal inside a profitable, growing-company universe.",
        weights={
            "reversal_3": 0.30,
            "volume_surge": 0.15,
            "turnover_surge": 0.15,
            "intraday_strength": 0.05,
            "volatility_target": 0.10,
            "near_high_20": 0.05,
            "quality_score": 0.20,
        },
    ),
    Candidate(
        name="quality_trend_pullback",
        description="Three-day pullback within a ten-day uptrend, near a 20-day high and without a volume spike.",
        weights={
            "reversal_3": 0.25,
            "momentum_10": 0.25,
            "near_high_20": 0.15,
            "volume_dry_up": 0.10,
            "turnover_surge": 0.05,
            "volatility_target": 0.05,
            "quality_score": 0.15,
        },
    ),
    Candidate(
        name="quality_balanced",
        description="Balanced continuation, liquidity, intraday strength and quality composite.",
        weights={
            "momentum_5": 0.15,
            "momentum_10": 0.15,
            "volume_surge": 0.15,
            "turnover_surge": 0.15,
            "near_high_20": 0.10,
            "intraday_strength": 0.10,
            "volatility_target": 0.05,
            "quality_score": 0.15,
        },
    ),
)


EXPANDED_SIGNAL_BLUEPRINTS = (
    Candidate(
        name="reversal_trend_10",
        description="Three-day reversal inside a ten-day trend near the twenty-day high.",
        weights={"reversal_3": 0.30, "momentum_10": 0.25, "near_high_20": 0.15, "volume_dry_up": 0.15, "volatility_target": 0.15},
    ),
    Candidate(
        name="reversal_trend_20",
        description="Five-day reversal aligned with a twenty-day trend and moderate volatility.",
        weights={"reversal_5": 0.30, "momentum_20": 0.25, "near_high_20": 0.15, "volume_dry_up": 0.15, "volatility_target_20": 0.15},
    ),
    Candidate(
        name="gap_reclaim",
        description="Gap-down reversal with intraday reclaim and contained range.",
        weights={"gap_reversal": 0.20, "reversal_3": 0.25, "reversal_5": 0.20, "intraday_strength": 0.15, "trend_ma_5": 0.10, "amplitude_low": 0.10},
    ),
    Candidate(
        name="drawdown_recovery",
        description="Recovery from a twenty-day drawdown with short reversal and turnover confirmation.",
        weights={"drawdown_20": 0.30, "reversal_3": 0.25, "intraday_strength": 0.15, "turnover_surge_3": 0.10, "volatility_target": 0.20},
    ),
    Candidate(
        name="trend_5_20",
        description="Five-, ten-, and twenty-day trend alignment near a short breakout.",
        weights={"momentum_5": 0.25, "momentum_10": 0.25, "momentum_20": 0.20, "near_high_10": 0.15, "volatility_target": 0.15},
    ),
    Candidate(
        name="trend_10_60",
        description="Ten- to sixty-day continuation with volume confirmation.",
        weights={"momentum_10": 0.30, "momentum_20": 0.25, "momentum_60": 0.20, "near_high_20": 0.10, "volume_surge": 0.15},
    ),
    Candidate(
        name="trend_ma_confirmation",
        description="Trend above five- and twenty-day moving averages with a calm range.",
        weights={"trend_ma_5": 0.25, "trend_ma_20": 0.25, "momentum_10": 0.20, "near_high_20": 0.15, "amplitude_low": 0.15},
    ),
    Candidate(
        name="breakout_10",
        description="Ten-day breakout confirmed by short volume, turnover, and intraday strength.",
        weights={"momentum_5": 0.20, "near_high_10": 0.30, "volume_surge_3": 0.20, "turnover_surge_3": 0.15, "intraday_strength": 0.15},
    ),
    Candidate(
        name="breakout_20",
        description="Twenty-day breakout confirmed by broad volume and moving-average trend.",
        weights={"momentum_10": 0.20, "near_high_20": 0.30, "volume_surge": 0.20, "turnover_surge": 0.15, "trend_ma_20": 0.15},
    ),
    Candidate(
        name="volume_dry_pullback",
        description="Low-volume short pullback within a liquid ten-day uptrend.",
        weights={"reversal_3": 0.25, "momentum_10": 0.25, "volume_dry_up": 0.25, "liquidity_5": 0.10, "near_high_20": 0.15},
    ),
    Candidate(
        name="volume_confirmation",
        description="Five- and twenty-day trend with persistent volume and turnover expansion.",
        weights={"momentum_5": 0.20, "momentum_20": 0.20, "volume_surge": 0.25, "turnover_surge": 0.20, "near_high_20": 0.15},
    ),
    Candidate(
        name="turnover_confirmation",
        description="Ten-day trend with short turnover acceleration and liquid intraday strength.",
        weights={"momentum_10": 0.20, "turnover_surge_3": 0.30, "liquidity_5": 0.20, "intraday_strength": 0.15, "volatility_target": 0.15},
    ),
    Candidate(
        name="intraday_gap_strength",
        description="Positive opening gap and intraday strength inside a five-day continuation.",
        weights={"intraday_strength": 0.30, "gap_strength": 0.15, "momentum_5": 0.20, "near_high_10": 0.15, "turnover_surge": 0.10, "amplitude_low": 0.10},
    ),
    Candidate(
        name="gap_reversal_pullback",
        description="Gap-down pullback that remains above the twenty-day moving-average trend.",
        weights={"gap_reversal": 0.25, "reversal_3": 0.25, "trend_ma_20": 0.20, "volume_dry_up": 0.15, "volatility_target": 0.15},
    ),
    Candidate(
        name="low_range_trend",
        description="Low-amplitude trend continuation with a ten- to twenty-day return signal.",
        weights={"amplitude_low": 0.30, "momentum_10": 0.25, "momentum_20": 0.20, "trend_ma_20": 0.15, "volume_dry_up": 0.10},
    ),
    Candidate(
        name="range_recovery",
        description="Twenty-day drawdown reversal with a strong close and short liquidity surge.",
        weights={"drawdown_20": 0.25, "reversal_5": 0.25, "intraday_strength": 0.20, "liquidity_5": 0.15, "turnover_surge_3": 0.15},
    ),
    Candidate(
        name="volatility_middle",
        description="Moderate-volatility trend close to its twenty-day high without a volume spike.",
        weights={"volatility_target": 0.35, "momentum_10": 0.25, "near_high_20": 0.15, "turnover_surge": 0.10, "volume_dry_up": 0.15},
    ),
    Candidate(
        name="liquidity_trend",
        description="Liquid twenty-day trend with turnover expansion and contained amplitude.",
        weights={"liquidity_5": 0.25, "momentum_20": 0.25, "turnover_surge": 0.20, "near_high_20": 0.15, "amplitude_low": 0.15},
    ),
    Candidate(
        name="multi_horizon",
        description="Diversified short reversal and five- to sixty-day momentum blend.",
        weights={"reversal_3": 0.15, "momentum_5": 0.15, "momentum_10": 0.20, "momentum_20": 0.20, "momentum_60": 0.15, "near_high_20": 0.15},
    ),
)


QUALITY_OVERLAYS = (
    ("q05_composite", "quality_score", 0.05),
    ("q10_roe", "quality_roe", 0.10),
    ("q15_growth", "quality_growth", 0.15),
    ("q20_composite", "quality_score", 0.20),
    ("q25_profit", "quality_profit", 0.25),
)


def build_candidate_library() -> tuple[Candidate, ...]:
    """Return the 100 predeclared combinations used by the strategy sweep."""

    expanded: list[Candidate] = []
    for blueprint in EXPANDED_SIGNAL_BLUEPRINTS:
        if not math.isclose(sum(blueprint.weights.values()), 1.0, abs_tol=1e-9):
            raise ValueError(f"blueprint weights must sum to one: {blueprint.name}")
        for suffix, quality_factor, quality_weight in QUALITY_OVERLAYS:
            weights = {factor: weight * (1.0 - quality_weight) for factor, weight in blueprint.weights.items()}
            weights[quality_factor] = quality_weight
            expanded.append(
                Candidate(
                    name=f"expanded_{blueprint.name}_{suffix}",
                    description=f"{blueprint.description} Quality overlay: {quality_factor} at {quality_weight:.0%}.",
                    weights=weights,
                )
            )
    candidates = (*BASELINE_CANDIDATES, *expanded)
    names = [candidate.name for candidate in candidates]
    if len(candidates) != 100 or len(set(names)) != len(names):
        raise RuntimeError("candidate library must contain exactly 100 uniquely named strategies")
    return candidates


CANDIDATES = build_candidate_library()

# V2 is a separately named, predeclared expansion.  It is intentionally not a
# replacement for V1: a later run records exactly which library was searched
# and must earn its own forward evidence.  All inputs are known at the signal
# close and use only daily OHLCV data already available in this repository.
MICROSTRUCTURE_SIGNAL_BLUEPRINTS = (
    Candidate(
        name="micro_reversal_1",
        description="One- and two-day pullback inside a twenty-day trend, closing near the session high on quiet volume.",
        weights={"reversal_1": 0.32, "reversal_2": 0.18, "trend_ma_20": 0.20, "close_to_high": 0.15, "volume_dry_up": 0.15},
    ),
    Candidate(
        name="two_day_reclaim",
        description="Two-day pullback and gap-down reclaim confirmed by a strong close and fresh turnover.",
        weights={"reversal_2": 0.30, "gap_reversal": 0.20, "intraday_strength": 0.15, "close_to_high": 0.20, "turnover_surge_1": 0.15},
    ),
    Candidate(
        name="close_high_trend",
        description="Close near the session high with five- and twenty-day trend confirmation.",
        weights={"close_to_high": 0.30, "trend_ma_5": 0.20, "trend_ma_20": 0.20, "momentum_10": 0.20, "amplitude_low": 0.10},
    ),
    Candidate(
        name="micro_breakout",
        description="One- and five-day impulse with a strong close and one-day volume/turnover confirmation.",
        weights={"momentum_1": 0.15, "momentum_5": 0.20, "close_to_high": 0.20, "volume_surge_1": 0.25, "turnover_surge_1": 0.20},
    ),
    Candidate(
        name="quiet_long_trend",
        description="Calm continuation above a sixty-day average with persistent medium-term momentum.",
        weights={"trend_ma_60": 0.30, "momentum_20": 0.25, "momentum_60": 0.20, "amplitude_low_1": 0.15, "volume_dry_up": 0.10},
    ),
    Candidate(
        name="volatility_compression",
        description="Short volatility and range compression inside a twenty-day trend near the high.",
        weights={"volatility_target_5": 0.25, "amplitude_low_1": 0.25, "trend_ma_20": 0.20, "near_high_20": 0.15, "volume_dry_up": 0.15},
    ),
    Candidate(
        name="liquid_impulse",
        description="Liquid two-day impulse with a strong close and current turnover expansion.",
        weights={"turnover_surge_1": 0.25, "liquidity_5": 0.20, "momentum_2": 0.20, "close_to_high": 0.20, "intraday_strength": 0.15},
    ),
    Candidate(
        name="gap_close_reclaim",
        description="Gap-down reclaim followed by a close near the high with contained short volatility.",
        weights={"gap_reversal": 0.25, "close_to_high": 0.25, "reversal_1": 0.20, "turnover_surge_1": 0.15, "volatility_target_5": 0.15},
    ),
    Candidate(
        name="short_long_confluence",
        description="Two-day impulse aligned with ten-day momentum and the sixty-day trend.",
        weights={"momentum_2": 0.20, "momentum_10": 0.20, "trend_ma_60": 0.25, "close_to_high": 0.20, "volatility_target_5": 0.15},
    ),
    Candidate(
        name="volume_climax_pullback",
        description="One-day pullback in a twenty-day trend with fresh volume and turnover participation.",
        weights={"reversal_1": 0.25, "volume_surge_1": 0.25, "turnover_surge_1": 0.20, "close_to_high": 0.15, "trend_ma_20": 0.15},
    ),
)


def _expanded_candidates(blueprints: tuple[Candidate, ...], prefix: str = "expanded") -> tuple[Candidate, ...]:
    """Cross deterministic signal blueprints with the shared quality overlays."""

    expanded: list[Candidate] = []
    for blueprint in blueprints:
        if not math.isclose(sum(blueprint.weights.values()), 1.0, abs_tol=1e-9):
            raise ValueError(f"blueprint weights must sum to one: {blueprint.name}")
        for suffix, quality_factor, quality_weight in QUALITY_OVERLAYS:
            weights = {factor: weight * (1.0 - quality_weight) for factor, weight in blueprint.weights.items()}
            weights[quality_factor] = quality_weight
            expanded.append(
                Candidate(
                    name=f"{prefix}_{blueprint.name}_{suffix}",
                    description=f"{blueprint.description} Quality overlay: {quality_factor} at {quality_weight:.0%}.",
                    weights=weights,
                )
            )
    return tuple(expanded)


V2_CANDIDATES = (*CANDIDATES, *_expanded_candidates(MICROSTRUCTURE_SIGNAL_BLUEPRINTS, prefix="expanded_v2"))
if len(V2_CANDIDATES) != 150 or len({candidate.name for candidate in V2_CANDIDATES}) != len(V2_CANDIDATES):
    raise RuntimeError("V2 candidate library must contain 150 uniquely named strategies")

# V2's five quality overlays change both the quality input and its weight at
# once.  The V3 grid isolates those two decisions around the only V2 signal
# family that survived the initial stability and drawdown audit.  It excludes
# the five exact V2 combinations, so every added candidate is genuinely new.
QUALITY_GRID_OVERLAYS = tuple(
    (f"q{int(weight * 100):02d}_{name}", factor, weight)
    for name, factor in (
        ("roe", "quality_roe"),
        ("revenue", "quality_revenue"),
        ("growth", "quality_growth"),
        ("composite", "quality_score"),
        ("profit", "quality_profit"),
    )
    for weight in (0.05, 0.10, 0.15, 0.20, 0.25)
)


def build_v3_quality_grid_candidates() -> tuple[Candidate, ...]:
    """Expand quiet-long-trend with a factor-type × weight quality grid.

    Keeping V2's candidates in the V3 library lets development-period
    selection reject the new grid rather than forcing a newly added variant.
    """

    quiet_long_trend = next(
        candidate for candidate in MICROSTRUCTURE_SIGNAL_BLUEPRINTS if candidate.name == "quiet_long_trend"
    )
    v2_weight_signatures = {tuple(sorted(candidate.weights.items())) for candidate in V2_CANDIDATES}
    additions: list[Candidate] = []
    for suffix, quality_factor, quality_weight in QUALITY_GRID_OVERLAYS:
        weights = {factor: weight * (1.0 - quality_weight) for factor, weight in quiet_long_trend.weights.items()}
        weights[quality_factor] = quality_weight
        if tuple(sorted(weights.items())) in v2_weight_signatures:
            continue
        additions.append(
            Candidate(
                name=f"expanded_v3_quiet_long_trend_{suffix}",
                description=(
                    "Calm continuation above a sixty-day average with a systematic quality-input and weight probe. "
                    f"Quality overlay: {quality_factor} at {quality_weight:.0%}."
                ),
                weights=weights,
            )
        )
    if len(additions) != 20 or len({candidate.name for candidate in additions}) != len(additions):
        raise RuntimeError("V3 quality grid must contain 20 new unique strategies")
    return tuple(additions)


V3_QUALITY_GRID_CANDIDATES = build_v3_quality_grid_candidates()
V3_CANDIDATES = (*V2_CANDIDATES, *V3_QUALITY_GRID_CANDIDATES)
if len(V3_CANDIDATES) != 170 or len({candidate.name for candidate in V3_CANDIDATES}) != len(V3_CANDIDATES):
    raise RuntimeError("V3 candidate library must contain 170 uniquely named strategies")

# Financial quality is attached only after its announcement date, but older
# annual reports can remain eligible for many months.  V4 tests whether a
# cross-sectional preference for more recent disclosures adds information to
# the V3 revenue-growth family.  The six combinations independently vary the
# revenue and freshness allocations while keeping all prices close-known.
FRESHNESS_REVENUE_OVERLAYS = (
    ("q10_revenue_f05", 0.10, 0.05),
    ("q15_revenue_f05", 0.15, 0.05),
    ("q20_revenue_f05", 0.20, 0.05),
    ("q10_revenue_f10", 0.10, 0.10),
    ("q15_revenue_f10", 0.15, 0.10),
    ("q20_revenue_f10", 0.20, 0.10),
)


def build_v4_freshness_candidates() -> tuple[Candidate, ...]:
    """Add revenue-quality and disclosure-freshness probes to V3."""

    quiet_long_trend = next(
        candidate for candidate in MICROSTRUCTURE_SIGNAL_BLUEPRINTS if candidate.name == "quiet_long_trend"
    )
    additions: list[Candidate] = []
    for suffix, revenue_weight, freshness_weight in FRESHNESS_REVENUE_OVERLAYS:
        signal_weight = 1.0 - revenue_weight - freshness_weight
        weights = {factor: weight * signal_weight for factor, weight in quiet_long_trend.weights.items()}
        weights["quality_revenue"] = revenue_weight
        weights["quality_freshness"] = freshness_weight
        additions.append(
            Candidate(
                name=f"expanded_v4_quiet_long_trend_{suffix}",
                description=(
                    "Calm sixty-day trend with revenue quality and cross-sectional annual-report freshness. "
                    f"Revenue weight: {revenue_weight:.0%}; freshness weight: {freshness_weight:.0%}."
                ),
                weights=weights,
            )
        )
    if len(additions) != 6 or len({candidate.name for candidate in additions}) != len(additions):
        raise RuntimeError("V4 freshness library must contain six unique strategies")
    return tuple(additions)


V4_FRESHNESS_CANDIDATES = build_v4_freshness_candidates()
V4_CANDIDATES = (*V3_CANDIDATES, *V4_FRESHNESS_CANDIDATES)
if len(V4_CANDIDATES) != 176 or len({candidate.name for candidate in V4_CANDIDATES}) != len(V4_CANDIDATES):
    raise RuntimeError("V4 candidate library must contain 176 uniquely named strategies")

# V5 asks a distinct question raised by the long-history drawdown audit: can a
# cross-sectional preference for genuinely low twenty-day volatility and/or a
# consistently narrow five-day range make the three-day continuation basket
# more defensive?  These are not the earlier "moderate volatility" targets.
# The full 3 x 5 x 2 grid avoids choosing one quality input or weight after
# inspecting a specific result.  All components are known at the signal close.
DEFENSIVE_SIGNAL_BLUEPRINTS = (
    Candidate(
        name="defensive_low_volatility",
        description="Sixty-day continuation with an explicit preference for low twenty-day realized volatility.",
        weights={
            "trend_ma_60": 0.24,
            "momentum_20": 0.20,
            "momentum_60": 0.16,
            "amplitude_low_1": 0.12,
            "volume_dry_up": 0.08,
            "volatility_low_20": 0.20,
        },
    ),
    Candidate(
        name="defensive_low_range",
        description="Sixty-day continuation whose calmness is measured with a low five-day average intraday range.",
        weights={
            "trend_ma_60": 0.30,
            "momentum_20": 0.25,
            "momentum_60": 0.20,
            "amplitude_low": 0.15,
            "volume_dry_up": 0.10,
        },
    ),
    Candidate(
        name="defensive_dual_risk",
        description="Sixty-day continuation requiring both low twenty-day realized volatility and a narrow five-day range.",
        weights={
            "trend_ma_60": 0.22,
            "momentum_20": 0.18,
            "momentum_60": 0.14,
            "amplitude_low": 0.18,
            "volume_dry_up": 0.08,
            "volatility_low_20": 0.20,
        },
    ),
)

DEFENSIVE_QUALITY_OVERLAYS = tuple(
    (f"q{int(weight * 100):02d}_{name}", factor, weight)
    for name, factor in (
        ("roe", "quality_roe"),
        ("revenue", "quality_revenue"),
        ("growth", "quality_growth"),
        ("composite", "quality_score"),
        ("profit", "quality_profit"),
    )
    for weight in (0.10, 0.15)
)


def build_v5_defensive_candidates() -> tuple[Candidate, ...]:
    """Cross three defensive trend blueprints with a small quality grid."""

    additions: list[Candidate] = []
    for blueprint in DEFENSIVE_SIGNAL_BLUEPRINTS:
        if not math.isclose(sum(blueprint.weights.values()), 1.0, abs_tol=1e-9):
            raise ValueError(f"defensive blueprint weights must sum to one: {blueprint.name}")
        for suffix, quality_factor, quality_weight in DEFENSIVE_QUALITY_OVERLAYS:
            weights = {factor: weight * (1.0 - quality_weight) for factor, weight in blueprint.weights.items()}
            weights[quality_factor] = quality_weight
            additions.append(
                Candidate(
                    name=f"expanded_v5_{blueprint.name}_{suffix}",
                    description=f"{blueprint.description} Quality overlay: {quality_factor} at {quality_weight:.0%}.",
                    weights=weights,
                )
            )
    if len(additions) != 30 or len({candidate.name for candidate in additions}) != len(additions):
        raise RuntimeError("V5 defensive grid must contain 30 new unique strategies")
    return tuple(additions)


V5_DEFENSIVE_CANDIDATES = build_v5_defensive_candidates()
V5_CANDIDATES = (*V4_CANDIDATES, *V5_DEFENSIVE_CANDIDATES)
if len(V5_CANDIDATES) != 206 or len({candidate.name for candidate in V5_CANDIDATES}) != len(V5_CANDIDATES):
    raise RuntimeError("V5 candidate library must contain 206 uniquely named strategies")

# V6 follows the cohort attribution evidence without turning it into a hard
# eligibility filter.  The worst V5 cohorts closed materially nearer to their
# same-day highs than the overall selected set, while hard low-volatility,
# range and opening-gap gates all failed their sensitivity audits.  These four
# blueprints therefore test soft close-pullback and one-day-reversal ranking
# within the same three-day continuation family.  The full 4 x 5 x 2 grid is
# declared before running the historical pressure scan.
SOFT_RISK_SIGNAL_BLUEPRINTS = (
    Candidate(
        name="soft_close_pullback_defensive",
        description="Calm sixty-day continuation with a soft preference against an overextended daily close.",
        weights={
            "trend_ma_60": 0.27,
            "momentum_20": 0.22,
            "momentum_60": 0.17,
            "amplitude_low": 0.14,
            "volume_dry_up": 0.07,
            "close_pullback": 0.13,
        },
    ),
    Candidate(
        name="soft_short_reversal_defensive",
        description="Calm sixty-day continuation with a soft one-day pullback preference.",
        weights={
            "trend_ma_60": 0.27,
            "momentum_20": 0.22,
            "momentum_60": 0.17,
            "amplitude_low": 0.14,
            "volume_dry_up": 0.07,
            "reversal_1": 0.13,
        },
    ),
    Candidate(
        name="soft_close_pullback_low_volatility",
        description="Calm continuation balancing a non-overextended close and low twenty-day realized volatility.",
        weights={
            "trend_ma_60": 0.23,
            "momentum_20": 0.19,
            "momentum_60": 0.15,
            "amplitude_low": 0.13,
            "volume_dry_up": 0.06,
            "close_pullback": 0.12,
            "volatility_low_20": 0.12,
        },
    ),
    Candidate(
        name="soft_short_reversal_low_volatility",
        description="Calm continuation balancing a one-day pullback and low twenty-day realized volatility.",
        weights={
            "trend_ma_60": 0.20,
            "momentum_20": 0.17,
            "momentum_60": 0.13,
            "amplitude_low": 0.12,
            "volume_dry_up": 0.05,
            "reversal_1": 0.11,
            "volatility_low_20": 0.11,
            "close_pullback": 0.11,
        },
    ),
)


def build_v6_soft_risk_candidates() -> tuple[Candidate, ...]:
    """Add soft pullback and short-reversal probes to the defensive trend family."""

    additions: list[Candidate] = []
    for blueprint in SOFT_RISK_SIGNAL_BLUEPRINTS:
        if not math.isclose(sum(blueprint.weights.values()), 1.0, abs_tol=1e-9):
            raise RuntimeError(f"V6 soft-risk blueprint weights must sum to one: {blueprint.name}")
        for suffix, quality_factor, quality_weight in DEFENSIVE_QUALITY_OVERLAYS:
            weights = {factor: weight * (1.0 - quality_weight) for factor, weight in blueprint.weights.items()}
            weights[quality_factor] = quality_weight
            additions.append(
                Candidate(
                    name=f"expanded_v6_{blueprint.name}_{suffix}",
                    description=f"{blueprint.description} Quality overlay: {quality_factor} at {quality_weight:.0%}.",
                    weights=weights,
                )
            )
    if len(additions) != 40 or len({candidate.name for candidate in additions}) != len(additions):
        raise RuntimeError("V6 soft-risk grid must contain 40 new unique strategies")
    return tuple(additions)


V6_SOFT_RISK_CANDIDATES = build_v6_soft_risk_candidates()
V6_CANDIDATES = (*V5_CANDIDATES, *V6_SOFT_RISK_CANDIDATES)
if len(V6_CANDIDATES) != 246 or len({candidate.name for candidate in V6_CANDIDATES}) != len(V6_CANDIDATES):
    raise RuntimeError("V6 candidate library must contain 246 uniquely named strategies")

# V7 is deliberately small and explicitly diagnostic-driven: development-only
# single-factor evidence found negative three-day association for the existing
# long-trend inputs, while reversal_5, volume_dry_up and gap_strength showed a
# positive extreme-basket spread.  It is therefore a historical sensitivity
# library only; no V7 result may be promoted or registered for forward
# observation without a separately predeclared, genuinely unseen evaluation.
REVERSION_IC_SIGNAL_BLUEPRINTS = (
    Candidate(
        name="reversal_dry_gap_pullback",
        description="Five-day pullback with quiet volume, a strong opening gap, and an intraday close pullback.",
        weights={
            "reversal_5": 0.35,
            "volume_dry_up": 0.30,
            "gap_strength": 0.20,
            "close_pullback": 0.15,
        },
    ),
    Candidate(
        name="reversal_dry_gap",
        description="Five-day pullback with quiet volume and a strong opening gap, without trend confirmation.",
        weights={
            "reversal_5": 0.45,
            "volume_dry_up": 0.35,
            "gap_strength": 0.20,
        },
    ),
    Candidate(
        name="gap_dry_reversal",
        description="Strong opening gap with quiet-volume and five-day pullback confirmation.",
        weights={
            "gap_strength": 0.35,
            "reversal_5": 0.25,
            "volume_dry_up": 0.25,
            "close_pullback": 0.15,
        },
    ),
    Candidate(
        name="quiet_reversal_pullback",
        description="Five-day pullback with quiet volume, a less overextended close, and a modest one-day range preference.",
        weights={
            "reversal_5": 0.35,
            "volume_dry_up": 0.25,
            "close_pullback": 0.20,
            "amplitude_low_1": 0.20,
        },
    ),
)
REVERSION_IC_QUALITY_OVERLAYS: tuple[tuple[str, str | None, float], ...] = (
    ("gate_only", None, 0.0),
    ("q05_growth", "quality_growth", 0.05),
    ("q10_composite", "quality_score", 0.10),
)


def build_v7_reversion_ic_candidates() -> tuple[Candidate, ...]:
    """Add a compact, diagnostic-driven mean-reversion sensitivity grid."""

    additions: list[Candidate] = []
    for blueprint in REVERSION_IC_SIGNAL_BLUEPRINTS:
        if not math.isclose(sum(blueprint.weights.values()), 1.0, abs_tol=1e-9):
            raise RuntimeError(f"V7 reversion blueprint weights must sum to one: {blueprint.name}")
        for suffix, quality_factor, quality_weight in REVERSION_IC_QUALITY_OVERLAYS:
            weights = {factor: weight * (1.0 - quality_weight) for factor, weight in blueprint.weights.items()}
            if quality_factor is not None:
                weights[quality_factor] = quality_weight
            additions.append(
                Candidate(
                    name=f"expanded_v7_{blueprint.name}_{suffix}",
                    description=(
                        f"{blueprint.description} Quality overlay: "
                        f"{quality_factor or 'quality_gate_only'} at {quality_weight:.0%}."
                    ),
                    weights=weights,
                )
            )
    if len(additions) != 12 or len({candidate.name for candidate in additions}) != len(additions):
        raise RuntimeError("V7 reversion grid must contain 12 new unique strategies")
    return tuple(additions)


V7_REVERSION_IC_CANDIDATES = build_v7_reversion_ic_candidates()
V7_CANDIDATES = (*V6_CANDIDATES, *V7_REVERSION_IC_CANDIDATES)
if len(V7_CANDIDATES) != 258 or len({candidate.name for candidate in V7_CANDIDATES}) != len(V7_CANDIDATES):
    raise RuntimeError("V7 candidate library must contain 258 uniquely named strategies")

# V8 tests a distinct signal horizon rather than retuning V7.  A
# development-only expanded diagnostic found that the previously unused
# ten-day reversal has a positive three-day Rank IC and a positive Top3-minus-
# Bottom3 spread, while three-day momentum has the opposite direction.  The
# four blueprints and three quality modes are fully declared before this
# historical sensitivity run.  Results must remain research-only because the
# development evidence has already informed this design.
TEN_DAY_REVERSION_SIGNAL_BLUEPRINTS = (
    Candidate(
        name="reversal_10_dry_gap",
        description="Ten-day pullback with quiet volume and a strong opening gap.",
        weights={"reversal_10": 0.45, "volume_dry_up": 0.35, "gap_strength": 0.20},
    ),
    Candidate(
        name="reversal_10_dry_gap_pullback",
        description="Ten-day pullback with quiet volume, strong gap, and a less overextended close.",
        weights={"reversal_10": 0.35, "volume_dry_up": 0.25, "gap_strength": 0.20, "close_pullback": 0.20},
    ),
    Candidate(
        name="reversal_10_dry_gap_low_volatility",
        description="Ten-day pullback with quiet volume, strong gap, and low twenty-day realized volatility.",
        weights={"reversal_10": 0.35, "volume_dry_up": 0.25, "gap_strength": 0.15, "volatility_low_20": 0.25},
    ),
    Candidate(
        name="reversal_10_dry_gap_short_reversal",
        description="Ten-day pullback with quiet volume, strong gap, and a soft one-day pullback preference.",
        weights={"reversal_10": 0.35, "volume_dry_up": 0.25, "gap_strength": 0.15, "reversal_1": 0.25},
    ),
)


def build_v8_ten_day_reversion_candidates() -> tuple[Candidate, ...]:
    """Build the compact diagnostic-driven ten-day-reversal sensitivity grid."""

    additions: list[Candidate] = []
    for blueprint in TEN_DAY_REVERSION_SIGNAL_BLUEPRINTS:
        if not math.isclose(sum(blueprint.weights.values()), 1.0, abs_tol=1e-9):
            raise RuntimeError(f"V8 ten-day-reversion blueprint weights must sum to one: {blueprint.name}")
        for suffix, quality_factor, quality_weight in REVERSION_IC_QUALITY_OVERLAYS:
            weights = {factor: weight * (1.0 - quality_weight) for factor, weight in blueprint.weights.items()}
            if quality_factor is not None:
                weights[quality_factor] = quality_weight
            additions.append(
                Candidate(
                    name=f"expanded_v8_{blueprint.name}_{suffix}",
                    description=(
                        f"{blueprint.description} Quality overlay: "
                        f"{quality_factor or 'quality_gate_only'} at {quality_weight:.0%}."
                    ),
                    weights=weights,
                )
            )
    if len(additions) != 12 or len({candidate.name for candidate in additions}) != len(additions):
        raise RuntimeError("V8 ten-day-reversion grid must contain 12 new unique strategies")
    return tuple(additions)


V8_TEN_DAY_REVERSION_CANDIDATES = build_v8_ten_day_reversion_candidates()
if len({candidate.name for candidate in V8_TEN_DAY_REVERSION_CANDIDATES}) != 12:
    raise RuntimeError("V8 candidate library must contain 12 uniquely named strategies")

# V9 isolates the strongest consistent development-only associations instead
# of blending them with the previously rejected long-trend family. Low range,
# low volatility and ten-day reversal are tested as a compact sensitivity grid.
# The diagnostic has already seen the development period, so no V9 result can
# be registered or promoted without a genuinely unseen future evaluation.
COMPRESSION_REVERSION_SIGNAL_BLUEPRINTS = (
    Candidate(
        name="reversal_10_quiet_compression",
        description="Ten-day pullback with quiet volume, low twenty-day volatility, and a narrow five-day range.",
        weights={"reversal_10": 0.40, "volume_dry_up": 0.15, "volatility_low_20": 0.25, "amplitude_low": 0.20},
    ),
    Candidate(
        name="reversal_10_quiet_one_day_compression",
        description="Ten-day pullback with quiet volume, low twenty-day volatility, and a narrow current-day range.",
        weights={"reversal_10": 0.40, "volume_dry_up": 0.15, "volatility_low_20": 0.20, "amplitude_low_1": 0.25},
    ),
    Candidate(
        name="reversal_10_dual_compression",
        description="Ten-day pullback with quiet volume and both five-day and one-day range compression.",
        weights={"reversal_10": 0.35, "volume_dry_up": 0.10, "volatility_low_20": 0.20, "amplitude_low": 0.20, "amplitude_low_1": 0.15},
    ),
    Candidate(
        name="quiet_dual_compression",
        description="Pure quiet-volatility and dual-range-compression baseline, without a trend or reversal component.",
        weights={"volume_dry_up": 0.20, "volatility_low_20": 0.30, "amplitude_low": 0.25, "amplitude_low_1": 0.25},
    ),
)


def build_v9_compression_reversion_candidates() -> tuple[Candidate, ...]:
    """Build a compact diagnostic-driven compression/reversion sensitivity grid."""

    additions: list[Candidate] = []
    for blueprint in COMPRESSION_REVERSION_SIGNAL_BLUEPRINTS:
        if not math.isclose(sum(blueprint.weights.values()), 1.0, abs_tol=1e-9):
            raise RuntimeError(f"V9 compression blueprint weights must sum to one: {blueprint.name}")
        for suffix, quality_factor, quality_weight in REVERSION_IC_QUALITY_OVERLAYS:
            weights = {factor: weight * (1.0 - quality_weight) for factor, weight in blueprint.weights.items()}
            if quality_factor is not None:
                weights[quality_factor] = quality_weight
            additions.append(
                Candidate(
                    name=f"expanded_v9_{blueprint.name}_{suffix}",
                    description=(
                        f"{blueprint.description} Quality overlay: "
                        f"{quality_factor or 'quality_gate_only'} at {quality_weight:.0%}."
                    ),
                    weights=weights,
                )
            )
    if len(additions) != 12 or len({candidate.name for candidate in additions}) != len(additions):
        raise RuntimeError("V9 compression grid must contain 12 new unique strategies")
    return tuple(additions)


V9_COMPRESSION_REVERSION_CANDIDATES = build_v9_compression_reversion_candidates()
if len({candidate.name for candidate in V9_COMPRESSION_REVERSION_CANDIDATES}) != 12:
    raise RuntimeError("V9 candidate library must contain 12 uniquely named strategies")

CANDIDATE_LIBRARIES = {
    "v1": CANDIDATES,
    "v2_microstructure": V2_CANDIDATES,
    "v3_quality_grid": V3_CANDIDATES,
    "v4_freshness": V4_CANDIDATES,
    "v5_defensive": V5_CANDIDATES,
    "v6_soft_risk": V6_CANDIDATES,
    "v7_reversion_ic": V7_CANDIDATES,
    "v8_reversal_10_ic": V8_TEN_DAY_REVERSION_CANDIDATES,
    "v9_compression_reversal_ic": V9_COMPRESSION_REVERSION_CANDIDATES,
}
CANDIDATE_LIBRARY_DESCRIPTIONS = {
    "v1": "5 fixed baselines plus 19 fixed signal blueprints crossed with 5 fixed quality overlays",
    "v2_microstructure": (
        "V1 plus 10 predeclared close-known microstructure blueprints (one/two-day reversal, close location, "
        "one-day volume/turnover, short range/volatility and sixty-day trend) crossed with 5 quality overlays"
    ),
    "v3_quality_grid": (
        "V2 plus 20 non-duplicate quiet-long-trend candidates that independently cross ROE, revenue, growth, "
        "composite and profit quality inputs with 5%, 10%, 15%, 20% and 25% weights"
    ),
    "v4_freshness": (
        "V3 plus six quiet-long-trend combinations that independently vary revenue-quality and annual-report "
        "freshness weights; freshness is ranked from the close-known days since the effective announcement date"
    ),
    "v5_defensive": (
        "V4 plus thirty systematic defensive-continuation combinations: three low-volatility/low-range signal "
        "blueprints crossed with five quality inputs and 10%/15% quality weights"
    ),
    "v6_soft_risk": (
        "V5 plus forty defensive-continuation combinations: four soft close-pullback/short-reversal signal blueprints "
        "crossed with five quality inputs and 10%/15% quality weights"
    ),
    "v7_reversion_ic": (
        "V6 plus twelve diagnostic-driven historical sensitivity combinations: four short-reversal/quiet-volume/gap "
        "blueprints crossed with quality-gate-only, 5% growth, and 10% composite quality modes"
    ),
    "v8_reversal_10_ic": (
        "12 diagnostic-driven historical sensitivity combinations: four ten-day-reversal/quiet-volume/gap blueprints "
        "crossed with quality-gate-only, 5% growth, and 10% composite quality modes"
    ),
    "v9_compression_reversal_ic": (
        "12 diagnostic-driven historical sensitivity combinations: four low-volatility/range-compression and ten-day "
        "reversal blueprints crossed with quality-gate-only, 5% growth, and 10% composite quality modes"
    ),
}

# These are existing close-known fields from ``rank_factor_frame`` that have
# not all been used by a candidate library.  Keeping their directions explicit
# in the diagnostic catalog lets us reject or motivate a later library from
# development-only evidence instead of hand-picking a new formula first.
EXPLORATORY_DIAGNOSTIC_FACTORS = (
    "momentum_2",
    "momentum_3",
    "momentum_5",
    "momentum_10",
    "reversal_2",
    "reversal_3",
    "reversal_10",
    "trend_ma_5",
    "trend_ma_20",
    "volume_surge_1",
    "volume_surge_3",
    "turnover_surge",
    "turnover_surge_1",
    "turnover_surge_3",
    "liquidity_5",
    "volatility_target_5",
    "volatility_target",
    "volatility_target_20",
    "gap_reversal",
    "near_high_10",
    "near_high_20",
    "drawdown_20",
    "intraday_strength",
    "roe_change",
    "revenue_yoy_acceleration",
    "profit_yoy_acceleration",
    "free_float_cap_small",
    "up_day_consistency_5",
    "signed_volume_pressure_5",
    "close_above_vwap_1",
    "signed_efficiency_ratio_10",
    "return_turnover_correlation_10",
    "compression_consensus_min",
    "max_return_20_low",
)

# This diagnostic catalog is fixed before a new candidate library exists.  It
# combines prior-library factors with unused, close-known technical fields.
# It is evidence for forming a future library; it never selects or promotes an
# existing candidate.
FACTOR_DIAGNOSTIC_COLUMNS = tuple(
    sorted({factor for candidate in V7_CANDIDATES for factor in candidate.weights} | set(EXPLORATORY_DIAGNOSTIC_FACTORS))
)
FACTOR_DIAGNOSTIC_BUCKET_COUNT = 5
FACTOR_DIAGNOSTIC_WORST_COHORT_COUNT = 5
FACTOR_TAIL_ATTRIBUTION_COLUMNS = (
    "liquidity_5",
    "free_float_cap_small",
    "volatility_low_20",
    "amplitude_low",
    "volume_dry_up",
    "momentum_1",
    "momentum_20",
    "close_to_high",
)
# Minimum number of earlier non-missing close observations required before a
# declared rolling field can have a value.  Same-session price/volume windows
# need N-1 earlier observations; windows of daily returns need N earlier
# closes.  This map is an input-semantics contract and never reads a future
# return or changes a strategy score.
ROLLING_FACTOR_PRIOR_CLOSE_REQUIREMENTS = {
    "momentum_1": 1,
    "momentum_2": 2,
    "momentum_3": 3,
    "momentum_5": 5,
    "up_day_ratio_5": 5,
    "momentum_10": 10,
    "momentum_20": 20,
    "momentum_60": 60,
    "trend_ma_5": 4,
    "trend_ma_20": 19,
    "trend_ma_60": 59,
    "volume_surge_1": 19,
    "volume_surge": 19,
    "volume_surge_3": 9,
    "turnover_surge": 19,
    "turnover_surge_3": 9,
    "turnover_surge_1": 19,
    "liquidity_5": 4,
    "volatility_5": 5,
    "volatility_10": 10,
    "volatility_20": 20,
    "amplitude_5": 4,
    "gap_1": 1,
    "near_high_10": 9,
    "near_high_20": 19,
    "signed_efficiency_ratio_10": 10,
    "return_turnover_correlation_10": 10,
    "signed_volume_pressure_5": 4,
    "max_return_20": 20,
}
COMPLETE_WINDOW_SEMANTICS_EFFECTIVE_RUN_ID = "20260714T095117Z"
WINDOW_SEMANTICS_AFFECTED_FACTORS = frozenset(
    {
        "up_day_ratio_5",
        "up_day_consistency_5",
        "trend_ma_5",
        "trend_ma_20",
        "trend_ma_60",
        "volume_surge_1",
        "volume_surge",
        "volume_surge_3",
        "volume_dry_up",
        "turnover_surge",
        "turnover_surge_3",
        "turnover_surge_1",
        "liquidity_5",
        "volatility_5",
        "volatility_10",
        "volatility_20",
        "volatility_target_5",
        "volatility_target",
        "volatility_target_20",
        "volatility_low_20",
        "amplitude_5",
        "amplitude_low",
        "near_high_10",
        "near_high_20",
        "drawdown_20",
        "return_turnover_correlation_10",
        "signed_volume_pressure_5",
        "compression_consensus_min",
    }
)
SELECTION_MULTIPLICITY_DEFAULT_BOOTSTRAP_REPLICATES = 1000
SELECTION_MULTIPLICITY_DEFAULT_BLOCK_COHORTS = 5
SELECTION_MULTIPLICITY_DEFAULT_SEED = 17
LIMIT_LIKE_MAIN_RETURN_THRESHOLD = 0.095
LIMIT_LIKE_CHINEXT_RETURN_THRESHOLD = 0.195
LIMIT_LIKE_CLOSE_TO_HIGH_MIN = 0.995
LIMIT_LIKE_EVENT_MIN_COHORTS = 200
LIMIT_LIKE_EVENT_MAX_DRAWDOWN = -0.20
QUARTERLY_EVENT_CAPACITY_MIN_COHORTS = 200
QUARTERLY_ACCELERATION_METRICS = {
    "profit_yoy_acceleration": "same-fiscal-quarter profit YoY acceleration",
    "revenue_yoy_acceleration": "same-fiscal-quarter revenue YoY acceleration",
    "roe_change": "same-fiscal-quarter ROE change",
}


def candidate_library(library_id: str) -> tuple[Candidate, ...]:
    """Return one named immutable candidate library."""

    try:
        return CANDIDATE_LIBRARIES[library_id]
    except KeyError as exc:
        choices = ", ".join(sorted(CANDIDATE_LIBRARIES))
        raise ValueError(f"unknown candidate_library {library_id!r}; choose one of: {choices}") from exc

REGIME_FILTERS = {
    "always": "Trade every eligible rebalance cohort.",
    "breadth_5_positive": "Trade only when the eligible-universe mean five-day return is positive.",
    "breadth_20_positive": "Trade only when the eligible-universe mean twenty-day return is positive.",
    "breadth_5_above_20": "Trade only when five-day eligible-universe breadth exceeds twenty-day breadth.",
    "breadth_5_and_20_positive": "Trade only when both five-day and twenty-day eligible-universe breadth are positive.",
    "breadth_5_positive_and_above_20": (
        "Trade only when five-day eligible-universe breadth is positive and exceeds twenty-day breadth."
    ),
    "breadth_5_above_20_and_20_positive": (
        "Trade only when five-day eligible-universe breadth exceeds a positive twenty-day breadth."
    ),
    "breadth_20_positive_and_volatility_below_trailing_p75": (
        "Trade only when twenty-day eligible-universe breadth is positive and median twenty-day volatility "
        "does not exceed its strictly trailing 252-session 75th percentile."
    ),
    "breadth_20_positive_and_volatility_below_trailing_p50": (
        "Trade only when twenty-day eligible-universe breadth is positive and median twenty-day volatility "
        "does not exceed its strictly trailing 252-session median."
    ),
    "breadth_20_positive_and_dispersion_below_trailing_p75": (
        "Trade only when twenty-day eligible-universe breadth is positive and one-day cross-sectional return "
        "dispersion does not exceed its strictly trailing 252-session 75th percentile."
    ),
    "breadth_20_positive_and_above_ma20_majority": (
        "Trade only when twenty-day eligible-universe breadth is positive and a majority of eligible names "
        "close above their twenty-day moving average."
    ),
    "breadth_20_positive_and_volatility_below_trailing_p75_and_above_ma20_majority": (
        "Trade only when positive twenty-day breadth, below-trailing-75th-percentile median volatility, and "
        "a majority above the twenty-day moving average all hold."
    ),
    "breadth_20_positive_and_volatility_below_trailing_p50_and_above_ma20_majority": (
        "Trade only when positive twenty-day breadth, below-trailing-median median volatility, and a majority "
        "above the twenty-day moving average all hold."
    ),
}

SELECTION_POLICIES = {
    "pooled_return_drawdown": "maximize development annualized_return - 0.5 * abs(development max_drawdown)",
    "positive_year_stability": (
        "maximize the worst development calendar-year net cumulative return - 0.5 * abs(full-development max_drawdown); "
        "requires at least two development years and every observed development calendar year to be positive"
    ),
    "positive_year_stability_mdd20": (
        "require at least two development years, every observed development calendar year to be positive, and "
        "development max_drawdown no worse than -20%; "
        "then maximize the worst development calendar-year net cumulative return - 0.5 * abs(full-development max_drawdown)"
    ),
}

# This cap matches the initial-test risk gate.  It is deliberately part of a
# separately named selection policy so a later research cycle cannot rewrite
# the winner of a prior, looser stability rule.
STRICT_DEVELOPMENT_MAX_DRAWDOWN = -0.20
FACTOR_STABILITY_MIN_CALENDAR_YEARS = 5
FACTOR_STABILITY_MIN_COHORTS = 200
DEFAULT_CLOSE_LOSS_CAPS = (0.05, 0.08, 0.10)
DEFAULT_ENTRY_GAP_CAPS = (0.02, 0.04, 0.06)
DEFAULT_BASKET_CORRELATION_LOOKBACK = 20
CORRELATION_DIAGNOSTIC_THRESHOLDS = (0.50, 0.70, 0.80, 0.90)
DEFAULT_MAX_PAIRWISE_CORRELATION_CAPS = (0.50, 0.60, 0.70)
DEFAULT_DIVERSIFICATION_CANDIDATE_POOL = 30
RISK_GATE_LEVELS = (None, 0.20, 0.40)


def candidate_library_fingerprint(candidates: tuple[Candidate, ...] = CANDIDATES) -> str:
    """Return a stable fingerprint for the exact predeclared strategy library."""

    payload = [
        {"name": candidate.name, "description": candidate.description, "weights": candidate.weights}
        for candidate in candidates
    ]
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def stability_score_with_drawdown_cap(
    stability_score: float | None,
    max_drawdown: float | None,
    cap: float = STRICT_DEVELOPMENT_MAX_DRAWDOWN,
) -> float | None:
    """Keep a stability score only when its development drawdown satisfies ``cap``."""

    if stability_score is None or max_drawdown is None or float(max_drawdown) < cap:
        return None
    return float(stability_score)


def positive_year_stability_score(year_returns: list[float], max_drawdown: float | None) -> float | None:
    """Score only a development sample with at least two, all-positive calendar years."""

    if len(year_returns) < 2 or any(value <= 0.0 for value in year_returns) or max_drawdown is None:
        return None
    return float(min(year_returns) - 0.5 * abs(float(max_drawdown)))


def apply_regime_filter(frame: pd.DataFrame, regime_filter: str) -> pd.DataFrame:
    """Return signal rows allowed by a close-known market-breadth state."""

    if regime_filter not in REGIME_FILTERS:
        choices = ", ".join(sorted(REGIME_FILTERS))
        raise ValueError(f"unknown regime_filter {regime_filter!r}; choose one of: {choices}")
    if regime_filter == "always":
        return frame
    if regime_filter == "breadth_5_positive":
        condition = frame["market_breadth_5"].gt(0.0)
    elif regime_filter == "breadth_20_positive":
        condition = frame["market_breadth_20"].gt(0.0)
    elif regime_filter == "breadth_5_above_20":
        condition = frame["market_breadth_5"].gt(frame["market_breadth_20"])
    elif regime_filter == "breadth_5_and_20_positive":
        condition = frame["market_breadth_5"].gt(0.0) & frame["market_breadth_20"].gt(0.0)
    elif regime_filter == "breadth_5_positive_and_above_20":
        condition = frame["market_breadth_5"].gt(0.0) & frame["market_breadth_5"].gt(frame["market_breadth_20"])
    elif regime_filter == "breadth_5_above_20_and_20_positive":
        condition = frame["market_breadth_5"].gt(frame["market_breadth_20"]) & frame["market_breadth_20"].gt(0.0)
    elif regime_filter == "breadth_20_positive_and_volatility_below_trailing_p75":
        condition = frame["market_breadth_20"].gt(0.0) & frame["market_volatility_20"].le(
            frame["market_volatility_20_trailing_p75"]
        )
    elif regime_filter == "breadth_20_positive_and_volatility_below_trailing_p50":
        condition = frame["market_breadth_20"].gt(0.0) & frame["market_volatility_20"].le(
            frame["market_volatility_20_trailing_p50"]
        )
    elif regime_filter == "breadth_20_positive_and_dispersion_below_trailing_p75":
        condition = frame["market_breadth_20"].gt(0.0) & frame["market_return_dispersion_1"].le(
            frame["market_return_dispersion_1_trailing_p75"]
        )
    elif regime_filter == "breadth_20_positive_and_above_ma20_majority":
        condition = frame["market_breadth_20"].gt(0.0) & frame["market_above_ma20_fraction"].gt(0.5)
    elif regime_filter == "breadth_20_positive_and_volatility_below_trailing_p75_and_above_ma20_majority":
        condition = (
            frame["market_breadth_20"].gt(0.0)
            & frame["market_volatility_20"].le(frame["market_volatility_20_trailing_p75"])
            & frame["market_above_ma20_fraction"].gt(0.5)
        )
    else:
        condition = (
            frame["market_breadth_20"].gt(0.0)
            & frame["market_volatility_20"].le(frame["market_volatility_20_trailing_p50"])
            & frame["market_above_ma20_fraction"].gt(0.5)
        )
    return frame.loc[condition.fillna(False)].copy()


def _timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _atomic_write_text(destination: Path, content: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=destination.parent, delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(destination)


def _atomic_write_parquet(destination: Path, frame: pd.DataFrame) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".parquet", dir=destination.parent, delete=False) as handle:
        temporary = Path(handle.name)
    frame.to_parquet(temporary, index=False, compression="zstd")
    temporary.replace(destination)


def _json_default(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp, dt.datetime, dt.date)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"cannot serialize {type(value).__name__}")


def a_share_trade_fees(notional: float, side: str, rules: AShareExecutionRules) -> dict[str, float]:
    """Calculate the configurable fees for one ordinary A-share stock trade."""

    rules.validate()
    if notional < 0:
        raise ValueError("notional must not be negative")
    if side not in {"buy", "sell"}:
        raise ValueError("side must be 'buy' or 'sell'")
    commission = max(notional * rules.commission_rate, rules.commission_min) if notional else 0.0
    transfer_fee = notional * rules.transfer_fee_rate
    stamp_duty = notional * rules.stamp_duty_rate if side == "sell" else 0.0
    return {
        "commission": float(commission),
        "transfer_fee": float(transfer_fee),
        "stamp_duty": float(stamp_duty),
        "total": float(commission + transfer_fee + stamp_duty),
    }


def buy_cash_required(price: float, quantity: int, rules: AShareExecutionRules) -> float:
    """Return cash needed to buy an integer number of shares, including fees."""

    if price <= 0:
        raise ValueError("price must be positive")
    if quantity < 0 or quantity % rules.lot_size:
        raise ValueError("quantity must be a non-negative whole number of board lots")
    notional = price * quantity
    return float(notional + a_share_trade_fees(notional, "buy", rules)["total"])


def affordable_board_lots(price: float, budget: float, rules: AShareExecutionRules) -> int:
    """Return the largest board-lot quantity whose buy cash does not exceed budget."""

    if budget < 0:
        raise ValueError("budget must not be negative")
    if price <= 0:
        raise ValueError("price must be positive")
    one_lot_cost = buy_cash_required(price, rules.lot_size, rules)
    if one_lot_cost > budget:
        return 0
    estimated_lots = int(budget // (price * rules.lot_size * (1.0 + rules.commission_rate + rules.transfer_fee_rate)))
    lots = max(1, estimated_lots)
    while lots and buy_cash_required(price, lots * rules.lot_size, rules) > budget + 1e-9:
        lots -= 1
    return lots * rules.lot_size


def plan_lot_orders(
    candidates: list[dict[str, Any]], capital: float, rules: AShareExecutionRules
) -> dict[str, Any]:
    """Create an order-sized pilot plan without redistributing skipped slots.

    A skipped expensive stock intentionally leaves cash unused.  Reassigning
    that cash to a lower-ranked name would make a different, untested strategy.
    """

    rules.validate()
    if capital <= 0:
        raise ValueError("capital must be positive")
    if not candidates:
        raise ValueError("at least one candidate is required")
    if len(candidates) * rules.target_weight > rules.max_gross_exposure + 1e-12:
        raise ValueError("candidate target weights exceed max_gross_exposure")

    target_cash = capital * rules.target_weight
    orders: list[dict[str, Any]] = []
    for fallback_rank, candidate in enumerate(candidates, start=1):
        price = float(candidate["reference_close"])
        quantity = affordable_board_lots(price, target_cash, rules)
        rank = int(candidate.get("rank", fallback_rank))
        name = str(candidate.get("name", ""))
        instrument = str(candidate["instrument"])
        if quantity == 0:
            one_lot_cash = buy_cash_required(price, rules.lot_size, rules)
            orders.append(
                {
                    "rank": rank,
                    "instrument": instrument,
                    "name": name,
                    "reference_close": price,
                    "target_weight": rules.target_weight,
                    "status": "skipped_insufficient_budget_for_one_lot",
                    "minimum_one_lot_cash": one_lot_cash,
                    "target_cash": target_cash,
                    "reason": "Cash is not reallocated to preserve the declared equal-weight candidate rule.",
                }
            )
            continue

        notional = price * quantity
        buy_fees = a_share_trade_fees(notional, "buy", rules)
        sell_fees_at_reference = a_share_trade_fees(notional, "sell", rules)
        buy_cash = notional + buy_fees["total"]
        orders.append(
            {
                "rank": rank,
                "instrument": instrument,
                "name": name,
                "reference_close": price,
                "target_weight": rules.target_weight,
                "status": "planned_at_reference_price",
                "quantity": quantity,
                "board_lots": quantity // rules.lot_size,
                "notional": notional,
                "buy_fees": buy_fees,
                "estimated_buy_cash": buy_cash,
                "estimated_sell_fees_at_reference": sell_fees_at_reference,
                "estimated_round_trip_fees_at_reference": buy_fees["total"] + sell_fees_at_reference["total"],
                "actual_portfolio_weight": buy_cash / capital,
            }
        )

    planned = [order for order in orders if order["status"] == "planned_at_reference_price"]
    total_buy_cash = float(sum(order["estimated_buy_cash"] for order in planned))
    max_buy_cash = capital * rules.max_gross_exposure
    if total_buy_cash > max_buy_cash + 1e-9:
        raise RuntimeError("lot plan exceeds configured max_gross_exposure")
    return {
        "capital": capital,
        "rules": {
            "lot_size": rules.lot_size,
            "commission_rate": rules.commission_rate,
            "commission_min": rules.commission_min,
            "transfer_fee_rate": rules.transfer_fee_rate,
            "stamp_duty_rate": rules.stamp_duty_rate,
            "max_gross_exposure": rules.max_gross_exposure,
            "target_weight": rules.target_weight,
        },
        "target_cash_per_candidate": target_cash,
        "max_pilot_cash": max_buy_cash,
        "orders": orders,
        "summary": {
            "requested_candidates": len(candidates),
            "planned_candidates": len(planned),
            "skipped_candidates": len(candidates) - len(planned),
            "estimated_buy_cash": total_buy_cash,
            "actual_gross_exposure": total_buy_cash / capital,
            "cash_remaining_after_plan": capital - total_buy_cash,
            "unused_pilot_budget": max_buy_cash - total_buy_cash,
        },
        "limitations": [
            "Reference close is for sizing only; it is not a live quote, order price, or buy instruction.",
            "The plan does not model intraday price movement, limit-up/limit-down, suspension, slippage, or order fills.",
            "Skipped slots are not reallocated; changing that rule requires a separately tested portfolio construction policy.",
        ],
    }


def file_sha256(path: Path) -> str:
    """Return the content fingerprint recorded alongside every experiment."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def qlib_symbol(code: Any) -> str | None:
    """Convert a mainland A-share code to the Qlib symbol form used locally."""

    raw = str(code).strip().zfill(6)
    if raw.startswith("6"):
        return f"SH{raw}"
    if raw.startswith(("0", "3")):
        return f"SZ{raw}"
    return None


def annual_report_dates(start_year: int, end_year: int) -> list[str]:
    """Return inclusive annual accounting-period dates in ISO form."""

    if end_year < start_year:
        raise ValueError("--end-year must not be earlier than --start-year")
    return [f"{year}-12-31" for year in range(start_year, end_year + 1)]


def quarterly_report_dates(start_year: int, end_year: int) -> list[str]:
    """Return every cumulative quarterly financial-report period in chronological order."""

    if end_year < start_year:
        raise ValueError("--end-year must not be earlier than --start-year")
    return [
        f"{year}-{month_day}"
        for year in range(start_year, end_year + 1)
        for month_day in ("03-31", "06-30", "09-30", "12-31")
    ]


def _eastmoney_request(session: requests.Session, report_date: str, page_number: int) -> dict[str, Any]:
    params = {
        "reportName": EASTMONEY_REPORT,
        "columns": "ALL",
        "filter": f"(REPORTDATE='{report_date}')",
        "pageNumber": page_number,
        "pageSize": 500,
        "sortTypes": "1,1",
        "sortColumns": "SECURITY_CODE,NOTICE_DATE",
        "source": "WEB",
        "client": "WEB",
    }
    errors: list[str] = []
    for attempt in range(4):
        try:
            response = session.get(EASTMONEY_DATACENTER_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload.get("result"), dict):
                raise ValueError("Eastmoney response does not contain a result object")
            return payload
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            time.sleep(min(8.0, 0.5 * (2**attempt)))
    raise RuntimeError(f"cannot fetch annual report {report_date} page {page_number}: {errors[-1]}")


def _eastmoney_performance_forecast_request(
    session: requests.Session, report_date: str, page_number: int
) -> dict[str, Any]:
    """Fetch one page of public performance forecasts for an accounting period."""

    params = {
        "reportName": EASTMONEY_PERFORMANCE_FORECAST_REPORT,
        "columns": "ALL",
        "filter": f"(REPORT_DATE='{report_date}')",
        "pageNumber": page_number,
        "pageSize": 500,
        "sortTypes": "1,1",
        "sortColumns": "SECURITY_CODE,NOTICE_DATE",
        "source": "WEB",
        "client": "WEB",
    }
    errors: list[str] = []
    for attempt in range(4):
        try:
            response = session.get(EASTMONEY_DATACENTER_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload.get("result"), dict):
                raise ValueError("Eastmoney response does not contain a result object")
            return payload
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            time.sleep(min(8.0, 0.5 * (2**attempt)))
    raise RuntimeError(f"cannot fetch performance forecast {report_date} page {page_number}: {errors[-1]}")


def _eastmoney_billboard_request(
    session: requests.Session, start_date: str, end_date: str, page_number: int
) -> dict[str, Any]:
    """Fetch one page of daily billboard records for an inclusive date range.

    The endpoint also exposes D1/D2/D5/D10 post-event returns.  They are
    deliberately not requested here, so a later normalizer cannot accidentally
    turn an outcome field into a score-time feature.
    """

    params = {
        "reportName": EASTMONEY_BILLBOARD_REPORT,
        "columns": (
            "SECURITY_CODE,SECUCODE,TRADE_DATE,EXPLANATION,"
            "BILLBOARD_NET_AMT,BILLBOARD_DEAL_AMT,FREE_MARKET_CAP"
        ),
        "filter": f"(TRADE_DATE>='{start_date}')(TRADE_DATE<='{end_date}')",
        "pageNumber": page_number,
        "pageSize": 500,
        "sortTypes": "1,1",
        "sortColumns": "TRADE_DATE,SECURITY_CODE",
        "source": "WEB",
        "client": "WEB",
    }
    errors: list[str] = []
    for attempt in range(4):
        try:
            response = session.get(EASTMONEY_DATACENTER_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload.get("result"), dict):
                raise ValueError("Eastmoney response does not contain a result object")
            return payload
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            time.sleep(min(8.0, 0.5 * (2**attempt)))
    raise RuntimeError(f"cannot fetch daily billboard {start_date} to {end_date} page {page_number}: {errors[-1]}")


def _eastmoney_major_holder_request(
    session: requests.Session, start_date: str, end_date: str, page_number: int
) -> dict[str, Any]:
    """Fetch one page of dated major-holder change notices.

    The source's ``END_DATE``/``TRADE_DATE`` describes when a change occurred,
    which may be long before it became public.  This request obtains only the
    filing date plus disclosed direction and free-float ratio, so research can
    use the strictly later local session rather than an unavailable trade date.
    """

    params = {
        "reportName": EASTMONEY_MAJOR_HOLDER_REPORT,
        "columns": "SECURITY_CODE,NOTICE_DATE,DIRECTION,CHANGE_FREE_RATIO",
        "filter": f"(NOTICE_DATE>='{start_date}')(NOTICE_DATE<='{end_date}')",
        "pageNumber": page_number,
        "pageSize": 500,
        "sortTypes": "1,1",
        "sortColumns": "NOTICE_DATE,SECURITY_CODE",
        "source": "WEB",
        "client": "WEB",
    }
    errors: list[str] = []
    for attempt in range(4):
        try:
            response = session.get(EASTMONEY_DATACENTER_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload.get("result"), dict):
                raise ValueError("Eastmoney response does not contain a result object")
            return payload
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            time.sleep(min(8.0, 0.5 * (2**attempt)))
    raise RuntimeError(f"cannot fetch major-holder notices {start_date} to {end_date} page {page_number}: {errors[-1]}")


def _eastmoney_block_trade_request(
    session: requests.Session, start_date: str, end_date: str, page_number: int
) -> dict[str, Any]:
    """Fetch one page of daily block-trade records with only same-close inputs.

    The provider offers CHANGE_RATE_1DAYS/5DAYS/10DAYS/20DAYS in the same
    report.  Those are post-trade outcomes and are deliberately excluded from
    the requested schema, along with raw prices and broker names.
    """

    params = {
        "reportName": EASTMONEY_BLOCK_TRADE_REPORT,
        "columns": "TRADE_DATE,SECURITY_CODE,PREMIUM_RATIO,DEAL_AMT,TURNOVER_RATE",
        "filter": f"(TRADE_DATE>='{start_date}')(TRADE_DATE<='{end_date}')",
        "pageNumber": page_number,
        "pageSize": 500,
        "sortTypes": "1,1",
        "sortColumns": "TRADE_DATE,SECURITY_CODE",
        "source": "WEB",
        "client": "WEB",
    }
    errors: list[str] = []
    for attempt in range(4):
        try:
            response = session.get(EASTMONEY_DATACENTER_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload.get("result"), dict):
                raise ValueError("Eastmoney response does not contain a result object")
            return payload
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            time.sleep(min(8.0, 0.5 * (2**attempt)))
    raise RuntimeError(f"cannot fetch block trades {start_date} to {end_date} page {page_number}: {errors[-1]}")


def _eastmoney_margin_financing_top_flow_request(
    session: requests.Session, trade_date: str, top_n: int
) -> dict[str, Any]:
    """Fetch one fixed top-N financing-flow page for one market session.

    The provider includes ``RCHANGE3DCP``/``RCHANGE5DCP``/``RCHANGE10DCP`` in
    its complete report.  Those are post-session outcomes, so this request
    names only contemporaneous financing fields and market capitalization.
    ``top_n`` is intentionally capped at the public API's 500-row page size:
    the hypothesis is a stable, declared high-financing-flow event sample, not
    a full-universe missing-data proxy.
    """

    if not 1 <= top_n <= 500:
        raise ValueError("top_n must be between 1 and 500")
    params = {
        "reportName": EASTMONEY_MARGIN_FINANCING_REPORT,
        "columns": "DATE,SCODE,RZJME,RZMRE,RZYE,SZ,FIN_BALANCE_GR,TRADE_MARKET_CODE",
        "filter": f"(DATE='{trade_date}')",
        "pageNumber": 1,
        "pageSize": top_n,
        "sortTypes": "-1",
        "sortColumns": "RZJME",
        "source": "WEB",
        "client": "WEB",
    }
    errors: list[str] = []
    for attempt in range(4):
        try:
            response = session.get(EASTMONEY_DATACENTER_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            # A later local daily bar can precede the public margin update.  A
            # no-data source response is evidence of that lag, not a download
            # failure and must remain visible in the manifest.
            if payload.get("success") is False and payload.get("code") == 9201:
                return {"result": {"data": []}, "source_status": "not_published"}
            if not isinstance(payload.get("result"), dict):
                raise ValueError("Eastmoney response does not contain a result object")
            return payload
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            time.sleep(min(8.0, 0.5 * (2**attempt)))
    raise RuntimeError(f"cannot fetch margin-financing top flows for {trade_date}: {errors[-1]}")


def _eastmoney_institutional_survey_request(
    session: requests.Session, start_date: str, end_date: str, page_number: int
) -> dict[str, Any]:
    """Fetch one page of dated institutional-survey disclosures.

    ``RPT_ORG_SURVEYNEW`` is the smaller summary report exposed on the web
    page, but it retains only a short recent history.  The detailed report has
    the required long history.  Its ``NUMBERNEW=1`` marker leaves one detail
    row per disclosed survey while retaining the disclosure's aggregate
    ``SUM``.  Request only issuer code, public notice date, received-date
    range, and reported institution count.  Participant names, current
    prices, and any post-event performance fields are neither requested nor
    stored.
    """

    params = {
        "reportName": EASTMONEY_INSTITUTIONAL_SURVEY_REPORT,
        "columns": "SECURITY_CODE,NOTICE_DATE,RECEIVE_START_DATE,RECEIVE_END_DATE,SUM",
        "filter": (
            f"(NUMBERNEW=\"1\")(IS_SOURCE=\"1\")"
            f"(NOTICE_DATE>='{start_date}')(NOTICE_DATE<='{end_date}')"
        ),
        "pageNumber": page_number,
        # This report rejects larger page sizes with a 9701 server-busy
        # response.  Keep its documented/observed 50-row page contract.
        "pageSize": 50,
        "sortTypes": "1,1,1,1",
        "sortColumns": "NOTICE_DATE,RECEIVE_START_DATE,SECURITY_CODE,NUMBERNEW",
        "source": "WEB",
        "client": "WEB",
    }
    errors: list[str] = []
    for attempt in range(6):
        try:
            response = session.get(EASTMONEY_DATACENTER_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            if payload.get("success") is False and payload.get("code") == 9201:
                return {"result": {"data": [], "pages": 0}}
            if not isinstance(payload.get("result"), dict):
                raise ValueError(
                    "Eastmoney response does not contain a result object: "
                    f"code={payload.get('code')}, message={payload.get('message')}"
                )
            return payload
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            time.sleep(min(8.0, 0.5 * (2**attempt)))
    raise RuntimeError(
        f"cannot fetch institutional-survey notices {start_date} to {end_date} page {page_number}: {errors[-1]}"
    )


def _eastmoney_repurchase_request(session: requests.Session, page_number: int) -> dict[str, Any]:
    """Fetch one historical repurchase-plan page without post-plan outcomes.

    ``UPDATEDATE``, implementation progress, and completed repurchase amount
    can be changed after the initial plan and are intentionally excluded.  The
    dated plan fields retained here are the initial record date, proposed
    maximum share ratio, and proposed maximum cash amount.
    """

    params = {
        "reportName": EASTMONEY_REPURCHASE_REPORT,
        "columns": "DIM_SCODE,DIM_DATE,ZSZSX,JESX",
        "pageNumber": page_number,
        "pageSize": 500,
        "sortTypes": "-1,-1,-1",
        "sortColumns": "UPD,DIM_DATE,DIM_SCODE",
        "source": "WEB",
        "client": "WEB",
    }
    errors: list[str] = []
    for attempt in range(4):
        try:
            response = session.get(EASTMONEY_DATACENTER_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload.get("result"), dict):
                raise ValueError("Eastmoney response does not contain a result object")
            return payload
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            time.sleep(min(8.0, 0.5 * (2**attempt)))
    raise RuntimeError(f"cannot fetch repurchase-plan page {page_number}: {errors[-1]}")


def _eastmoney_holder_count_request(
    session: requests.Session, end_date: str, page_number: int
) -> dict[str, Any]:
    """Fetch one shareholder-count reporting-period page with notice timing.

    The report also exposes period price change, household market value, and
    total market capitalization.  Those price-derived fields are excluded at
    request time.  The only candidate inputs are the disclosed holder-count
    changes, and they become usable only after ``HOLD_NOTICE_DATE``.
    """

    params = {
        "reportName": EASTMONEY_HOLDER_COUNT_REPORT,
        "columns": (
            "SECURITY_CODE,END_DATE,HOLD_NOTICE_DATE,HOLDER_NUM,PRE_HOLDER_NUM,"
            "HOLDER_NUM_CHANGE,HOLDER_NUM_RATIO"
        ),
        "filter": f"(END_DATE='{end_date}')",
        "pageNumber": page_number,
        "pageSize": 500,
        "sortTypes": "-1,-1",
        "sortColumns": "HOLD_NOTICE_DATE,SECURITY_CODE",
        "source": "WEB",
        "client": "WEB",
    }
    errors: list[str] = []
    for attempt in range(4):
        try:
            response = session.get(EASTMONEY_DATACENTER_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload.get("result"), dict):
                raise ValueError("Eastmoney response does not contain a result object")
            return payload
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            time.sleep(min(8.0, 0.5 * (2**attempt)))
    raise RuntimeError(f"cannot fetch holder-count report {end_date} page {page_number}: {errors[-1]}")


def _eastmoney_pledge_request(session: requests.Session, year: int, page_number: int) -> dict[str, Any]:
    """Fetch one page of dated pledge disclosures without current-state fields.

    The public report also exposes current prices, warning/liquidation lines,
    present unfreeze state, market value, and a current trade date.  They are
    deliberately excluded at request time.  The retained fields are the
    report's notice date and the disclosed pledge quantity / reported share
    capital ratio for that dated record.
    """

    params = {
        "reportName": EASTMONEY_PLEDGE_REPORT,
        "columns": "SECURITY_CODE,NOTICE_DATE,PF_NUM,PF_TSR",
        "filter": f"(NOTICE_DATE>='{year}-01-01')(NOTICE_DATE<='{year}-12-31')",
        "pageNumber": page_number,
        "pageSize": 500,
        "sortTypes": "-1,-1",
        "sortColumns": "NOTICE_DATE,SECURITY_CODE",
        "source": "WEB",
        "client": "WEB",
    }
    errors: list[str] = []
    for attempt in range(4):
        try:
            response = session.get(EASTMONEY_DATACENTER_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload.get("result"), dict):
                raise ValueError("Eastmoney response does not contain a result object")
            return payload
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            time.sleep(min(8.0, 0.5 * (2**attempt)))
    raise RuntimeError(f"cannot fetch pledge notices {year} page {page_number}: {errors[-1]}")


def _eastmoney_dividend_plan_request(session: requests.Session, year: int, page_number: int) -> dict[str, Any]:
    """Fetch one page of initial dividend-plan notices without later outcomes.

    The report carries later implementation state, ex-dividend timing, latest
    announcement date, dividend yield, and forward return fields.  They are
    excluded at request time.  Only the date labelled as the plan notice and
    terms announced in that plan are candidate inputs.
    """

    params = {
        "reportName": EASTMONEY_DIVIDEND_PLAN_REPORT,
        "columns": "SECURITY_CODE,PLAN_NOTICE_DATE,PRETAX_BONUS_RMB,BONUS_IT_RATIO",
        "filter": f"(PLAN_NOTICE_DATE>='{year}-01-01')(PLAN_NOTICE_DATE<='{year}-12-31')",
        "pageNumber": page_number,
        "pageSize": 500,
        "sortTypes": "-1,-1",
        "sortColumns": "PLAN_NOTICE_DATE,SECURITY_CODE",
        "source": "WEB",
        "client": "WEB",
    }
    errors: list[str] = []
    for attempt in range(4):
        try:
            response = session.get(EASTMONEY_DATACENTER_URL, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload.get("result"), dict):
                raise ValueError("Eastmoney response does not contain a result object")
            return payload
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            time.sleep(min(8.0, 0.5 * (2**attempt)))
    raise RuntimeError(f"cannot fetch dividend-plan notices {year} page {page_number}: {errors[-1]}")


def fetch_annual_report_rows(session: requests.Session, report_date: str) -> list[dict[str, Any]]:
    """Fetch all pages for one annual report period from the public endpoint."""

    first = _eastmoney_request(session, report_date, page_number=1)
    result = first["result"]
    pages = int(result.get("pages") or 0)
    if pages < 1:
        return []
    rows = list(result.get("data") or [])
    for page_number in range(2, pages + 1):
        payload = _eastmoney_request(session, report_date, page_number=page_number)
        rows.extend((payload.get("result") or {}).get("data") or [])
    return rows


def fetch_performance_forecast_rows(session: requests.Session, report_date: str) -> list[dict[str, Any]]:
    """Fetch all public performance-forecast pages for one report period."""

    first = _eastmoney_performance_forecast_request(session, report_date, page_number=1)
    result = first["result"]
    pages = int(result.get("pages") or 0)
    if pages < 1:
        return []
    rows = list(result.get("data") or [])
    for page_number in range(2, pages + 1):
        payload = _eastmoney_performance_forecast_request(session, report_date, page_number=page_number)
        rows.extend((payload.get("result") or {}).get("data") or [])
    return rows


def fetch_billboard_rows(session: requests.Session, start_date: str, end_date: str) -> list[dict[str, Any]]:
    """Fetch every daily-billboard page for one inclusive calendar range."""

    first = _eastmoney_billboard_request(session, start_date, end_date, page_number=1)
    result = first["result"]
    pages = int(result.get("pages") or 0)
    if pages < 1:
        return []
    rows = list(result.get("data") or [])
    for page_number in range(2, pages + 1):
        payload = _eastmoney_billboard_request(session, start_date, end_date, page_number=page_number)
        rows.extend((payload.get("result") or {}).get("data") or [])
    return rows


def fetch_major_holder_rows(session: requests.Session, start_date: str, end_date: str) -> list[dict[str, Any]]:
    """Fetch every major-holder change-notice page in one inclusive date range."""

    first = _eastmoney_major_holder_request(session, start_date, end_date, page_number=1)
    result = first["result"]
    pages = int(result.get("pages") or 0)
    if pages < 1:
        return []
    rows = list(result.get("data") or [])
    for page_number in range(2, pages + 1):
        payload = _eastmoney_major_holder_request(session, start_date, end_date, page_number=page_number)
        rows.extend((payload.get("result") or {}).get("data") or [])
    return rows


def fetch_block_trade_rows(session: requests.Session, start_date: str, end_date: str) -> list[dict[str, Any]]:
    """Fetch every public block-trade page in one inclusive date range."""

    first = _eastmoney_block_trade_request(session, start_date, end_date, page_number=1)
    result = first["result"]
    pages = int(result.get("pages") or 0)
    if pages < 1:
        return []
    rows = list(result.get("data") or [])
    for page_number in range(2, pages + 1):
        payload = _eastmoney_block_trade_request(session, start_date, end_date, page_number=page_number)
        rows.extend((payload.get("result") or {}).get("data") or [])
    return rows


def fetch_margin_financing_top_flow_rows(
    session: requests.Session, trade_date: str, top_n: int
) -> list[dict[str, Any]]:
    """Fetch the declared high-financing-flow event universe for one session."""

    payload = _eastmoney_margin_financing_top_flow_request(session, trade_date, top_n)
    return list((payload.get("result") or {}).get("data") or [])


def normalize_fundamental_rows(rows: Iterable[dict[str, Any]], report_date: str) -> pd.DataFrame:
    """Reduce provider-specific financial rows to the PIT fields needed by research.

    Eastmoney can expose later corrections for a prior report.  Keeping the
    earliest notice per instrument/report period is a conservative approximation
    of the first public disclosure, but it is not an immutable vendor PIT data
    set; that caveat is carried into every experiment record.
    """

    raw = pd.DataFrame(rows)
    if raw.empty:
        return pd.DataFrame(columns=FUNDAMENTAL_COLUMNS)
    frame = pd.DataFrame(
        {
            "instrument": raw.get("SECURITY_CODE", pd.Series(dtype="object")).map(qlib_symbol),
            "report_date": pd.to_datetime(report_date),
            "announcement_date": pd.to_datetime(raw.get("NOTICE_DATE"), errors="coerce"),
            "roe": pd.to_numeric(raw.get("WEIGHTAVG_ROE"), errors="coerce"),
            "net_profit": pd.to_numeric(raw.get("PARENT_NETPROFIT"), errors="coerce"),
            "revenue_yoy": pd.to_numeric(raw.get("YSTZ"), errors="coerce"),
            "profit_yoy": pd.to_numeric(raw.get("SJLTZ"), errors="coerce"),
        }
    )
    frame = frame.dropna(subset=["instrument", "announcement_date"])
    frame = frame.sort_values(["instrument", "report_date", "announcement_date"], kind="stable")
    return frame.drop_duplicates(["instrument", "report_date"], keep="first").reset_index(drop=True)


def normalize_performance_forecast_rows(rows: Iterable[dict[str, Any]], report_date: str) -> pd.DataFrame:
    """Reduce forecast notices to dated, numerically auditable event fields.

    The endpoint mixes revenue, EPS, non-recurring-profit, and net-profit
    forecasts.  Only its ``PREDICT_FINANCE_CODE == '004'`` rows describe the
    parent-company net profit stated by this research hypothesis.  The lower
    and upper YoY forecast midpoint is the directional forecast and their
    distance is its disclosed uncertainty.  A later announcement is retained
    as a new event: when it was publicly filed it could have superseded an
    earlier forecast.
    """

    raw = pd.DataFrame(rows)
    if raw.empty:
        return pd.DataFrame(columns=PERFORMANCE_FORECAST_COLUMNS)
    finance_code = raw.get("PREDICT_FINANCE_CODE", pd.Series(index=raw.index, dtype="object"))
    raw = raw.loc[finance_code.astype("string").eq("004")].copy()
    if raw.empty:
        return pd.DataFrame(columns=PERFORMANCE_FORECAST_COLUMNS)
    lower = pd.to_numeric(raw.get("ADD_AMP_LOWER", pd.Series(index=raw.index, dtype="float64")), errors="coerce")
    upper = pd.to_numeric(raw.get("ADD_AMP_UPPER", pd.Series(index=raw.index, dtype="float64")), errors="coerce")
    midpoint = pd.concat([lower, upper], axis=1).mean(axis=1)
    frame = pd.DataFrame(
        {
            "instrument": raw.get("SECURITY_CODE", pd.Series(dtype="object")).map(qlib_symbol),
            "report_date": pd.to_datetime(report_date),
            "announcement_date": pd.to_datetime(raw.get("NOTICE_DATE"), errors="coerce"),
            "forecast_type": raw.get("PREDICT_TYPE", pd.Series(index=raw.index, dtype="object")).astype("string"),
            "forecast_turnaround": raw.get("PREDICT_TYPE", pd.Series(index=raw.index, dtype="object"))
            .astype("string")
            .fillna("")
            .eq("扭亏")
            .astype(float),
            "forecast_profit_yoy": midpoint,
            "forecast_profit_yoy_width": (upper - lower).abs(),
        }
    )
    frame = frame.dropna(subset=["instrument", "announcement_date"])
    frame = frame.sort_values(["instrument", "report_date", "announcement_date"], kind="stable")
    return frame.drop_duplicates(["instrument", "report_date", "announcement_date"], keep="first").reset_index(drop=True)


def normalize_billboard_rows(rows: Iterable[dict[str, Any]]) -> pd.DataFrame:
    """Aggregate same-day billboard reasons into only close-known event inputs.

    A stock can satisfy multiple disclosure reasons on a session.  The raw
    money fields can be identical for duplicate reasons or differ for separate
    abnormal-trading windows, so each ratio is represented by its same-day
    median rather than an unsafe sum.  The number of distinct reasons is
    retained as an independent event-intensity measure.  Provider fields that
    describe returns after the event are intentionally absent from this
    schema.
    """

    raw = pd.DataFrame(rows)
    if raw.empty:
        return pd.DataFrame(columns=BILLBOARD_EVENT_COLUMNS)
    net = pd.to_numeric(raw.get("BILLBOARD_NET_AMT", pd.Series(index=raw.index, dtype="float64")), errors="coerce")
    deal = pd.to_numeric(raw.get("BILLBOARD_DEAL_AMT", pd.Series(index=raw.index, dtype="float64")), errors="coerce")
    floating = pd.to_numeric(raw.get("FREE_MARKET_CAP", pd.Series(index=raw.index, dtype="float64")), errors="coerce")
    with np.errstate(divide="ignore", invalid="ignore"):
        net_to_float = net / floating
        net_to_deal = net / deal
        deal_to_float = deal / floating
    frame = pd.DataFrame(
        {
            "instrument": raw.get("SECURITY_CODE", pd.Series(dtype="object")).map(qlib_symbol),
            "trade_date": pd.to_datetime(raw.get("TRADE_DATE"), errors="coerce"),
            "billboard_net_flow_to_float": net_to_float,
            "billboard_net_flow_to_deal": net_to_deal,
            "billboard_deal_to_float": deal_to_float,
            "_reason": raw.get("EXPLANATION", pd.Series(index=raw.index, dtype="object")).astype("string"),
        }
    )
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna(subset=["instrument", "trade_date"])
    aggregated = (
        frame.groupby(["instrument", "trade_date"], as_index=False, sort=True)
        .agg(
            billboard_net_flow_to_float=("billboard_net_flow_to_float", "median"),
            billboard_net_flow_to_deal=("billboard_net_flow_to_deal", "median"),
            billboard_deal_to_float=("billboard_deal_to_float", "median"),
            billboard_reason_count=("_reason", "nunique"),
        )
        .loc[:, list(BILLBOARD_EVENT_COLUMNS)]
    )
    aggregated["billboard_reason_count"] = pd.to_numeric(
        aggregated["billboard_reason_count"], errors="coerce"
    ).astype(float)
    return aggregated.sort_values(["instrument", "trade_date"], kind="stable").reset_index(drop=True)


def normalize_major_holder_rows(rows: Iterable[dict[str, Any]]) -> pd.DataFrame:
    """Aggregate major-holder changes by the date they were publicly noticed.

    ``CHANGE_FREE_RATIO`` is a disclosed percentage of freely tradable shares.
    It is treated as a magnitude and signed only by the provider's explicit
    ``DIRECTION`` label, not by the historical transaction date or the source
    price.  This deliberately leaves all current quotes, execution prices,
    and unannounced transaction dates out of the event snapshot.
    """

    raw = pd.DataFrame(rows)
    if raw.empty:
        return pd.DataFrame(columns=MAJOR_HOLDER_EVENT_COLUMNS)
    direction = raw.get("DIRECTION", pd.Series(index=raw.index, dtype="object")).astype("string")
    ratio = pd.to_numeric(
        raw.get("CHANGE_FREE_RATIO", pd.Series(index=raw.index, dtype="float64")), errors="coerce"
    ).abs()
    increase = ratio.where(direction.eq("增持"), 0.0)
    decrease = ratio.where(direction.eq("减持"), 0.0)
    frame = pd.DataFrame(
        {
            "instrument": raw.get("SECURITY_CODE", pd.Series(dtype="object")).map(qlib_symbol),
            "announcement_date": pd.to_datetime(raw.get("NOTICE_DATE"), errors="coerce"),
            "major_holder_increase_free_ratio": increase,
            "major_holder_decrease_free_ratio": decrease,
        }
    )
    frame = frame.dropna(subset=["instrument", "announcement_date"])
    frame["major_holder_net_change_free_ratio"] = (
        frame["major_holder_increase_free_ratio"] - frame["major_holder_decrease_free_ratio"]
    )
    aggregated = (
        frame.groupby(["instrument", "announcement_date"], as_index=False, sort=True)
        .agg(
            major_holder_net_change_free_ratio=("major_holder_net_change_free_ratio", "sum"),
            major_holder_increase_free_ratio=("major_holder_increase_free_ratio", "sum"),
            major_holder_decrease_free_ratio=("major_holder_decrease_free_ratio", "sum"),
            major_holder_event_count=("instrument", "size"),
        )
        .loc[:, list(MAJOR_HOLDER_EVENT_COLUMNS)]
    )
    for column in MAJOR_HOLDER_EVENT_COLUMNS[2:]:
        aggregated[column] = pd.to_numeric(aggregated[column], errors="coerce")
    return aggregated.sort_values(["instrument", "announcement_date"], kind="stable").reset_index(drop=True)


def normalize_block_trade_rows(rows: Iterable[dict[str, Any]]) -> pd.DataFrame:
    """Aggregate block trades to same-close stock/day features without outcomes.

    The premium/discount is weighted by disclosed deal amount, while turnover
    ratio and count accumulate across all transactions of that stock/session.
    Raw prices are not retained: only the provider's already-derived
    contemporaneous premium and turnover ratio enter the event snapshot.
    """

    raw = pd.DataFrame(rows)
    if raw.empty:
        return pd.DataFrame(columns=BLOCK_TRADE_EVENT_COLUMNS)
    amount = pd.to_numeric(raw.get("DEAL_AMT", pd.Series(index=raw.index, dtype="float64")), errors="coerce")
    premium = pd.to_numeric(raw.get("PREMIUM_RATIO", pd.Series(index=raw.index, dtype="float64")), errors="coerce")
    turnover = pd.to_numeric(raw.get("TURNOVER_RATE", pd.Series(index=raw.index, dtype="float64")), errors="coerce")
    frame = pd.DataFrame(
        {
            "instrument": raw.get("SECURITY_CODE", pd.Series(dtype="object")).map(qlib_symbol),
            "trade_date": pd.to_datetime(raw.get("TRADE_DATE"), errors="coerce"),
            "_amount": amount,
            "_premium_x_amount": premium * amount,
            "_premium_weight": amount.where(premium.notna()),
            "block_trade_turnover_rate": turnover,
        }
    )
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna(subset=["instrument", "trade_date"])
    grouped = frame.groupby(["instrument", "trade_date"], as_index=False, sort=True).agg(
        _amount=("_amount", "sum"),
        _premium_x_amount=("_premium_x_amount", "sum"),
        _premium_weight=("_premium_weight", "sum"),
        block_trade_turnover_rate=("block_trade_turnover_rate", "sum"),
        block_trade_event_count=("instrument", "size"),
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        grouped["block_trade_premium_ratio"] = grouped["_premium_x_amount"] / grouped["_premium_weight"]
    aggregated = grouped.loc[:, list(BLOCK_TRADE_EVENT_COLUMNS)].replace([np.inf, -np.inf], np.nan)
    for column in BLOCK_TRADE_EVENT_COLUMNS[2:]:
        aggregated[column] = pd.to_numeric(aggregated[column], errors="coerce")
    return aggregated.sort_values(["instrument", "trade_date"], kind="stable").reset_index(drop=True)


def normalize_margin_financing_top_flow_rows(rows: Iterable[dict[str, Any]]) -> pd.DataFrame:
    """Reduce public financing data to same-close, size-normalized event fields.

    The input is already the declared daily Top-N by financing net buy.  It is
    *not* treated as an observation of no financing activity for omitted
    stocks.  Ratio normalization uses the provider's same-session market cap
    and excludes ETFs/non-A-share codes through ``qlib_symbol``.  No source
    price, same-day return, or post-event return field is retained.
    """

    raw = pd.DataFrame(rows)
    if raw.empty:
        return pd.DataFrame(columns=MARGIN_FINANCING_EVENT_COLUMNS)
    net_buy = pd.to_numeric(raw.get("RZJME", pd.Series(index=raw.index, dtype="float64")), errors="coerce")
    buy = pd.to_numeric(raw.get("RZMRE", pd.Series(index=raw.index, dtype="float64")), errors="coerce")
    balance = pd.to_numeric(raw.get("RZYE", pd.Series(index=raw.index, dtype="float64")), errors="coerce")
    market_cap = pd.to_numeric(raw.get("SZ", pd.Series(index=raw.index, dtype="float64")), errors="coerce")
    with np.errstate(divide="ignore", invalid="ignore"):
        net_buy_to_market_cap = net_buy / market_cap
        buy_to_market_cap = buy / market_cap
        balance_to_market_cap = balance / market_cap
    frame = pd.DataFrame(
        {
            "instrument": raw.get("SCODE", pd.Series(index=raw.index, dtype="object")).map(qlib_symbol),
            "trade_date": pd.to_datetime(raw.get("DATE"), errors="coerce"),
            "margin_net_buy_to_market_cap": net_buy_to_market_cap,
            "margin_buy_to_market_cap": buy_to_market_cap,
            "margin_balance_to_market_cap": balance_to_market_cap,
            "margin_financing_balance_growth": pd.to_numeric(
                raw.get("FIN_BALANCE_GR", pd.Series(index=raw.index, dtype="float64")), errors="coerce"
            ),
        }
    )
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna(subset=["instrument", "trade_date"])
    for column in MARGIN_FINANCING_EVENT_COLUMNS[2:]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return (
        frame.loc[:, list(MARGIN_FINANCING_EVENT_COLUMNS)]
        .sort_values(["instrument", "trade_date"], kind="stable")
        .drop_duplicates(["instrument", "trade_date"], keep="last")
        .reset_index(drop=True)
    )


def _institutional_survey_detail_frame(rows: Iterable[dict[str, Any]]) -> pd.DataFrame:
    """Collapse repeated participant rows to one dated survey event.

    The detailed Eastmoney report emits one row per received institution while
    repeating ``SUM`` for the disclosure.  The source does not expose a stable
    survey identifier, so the conservative event key is issuer plus public
    notice date and disclosed received-date range.  This helper retains no
    participant identity and is kept separate so sync pagination cannot double
    count a disclosure split between two API pages.
    """

    raw = pd.DataFrame(rows)
    if raw.empty:
        return pd.DataFrame(
            columns=[
                "instrument",
                "announcement_date",
                "receive_start_date",
                "receive_end_date",
                "institutional_survey_org_count",
            ]
        )
    start = pd.to_datetime(
        raw.get("RECEIVE_START_DATE", pd.Series(index=raw.index, dtype="object")), errors="coerce"
    )
    end = pd.to_datetime(
        raw.get("RECEIVE_END_DATE", pd.Series(index=raw.index, dtype="object")), errors="coerce"
    )
    frame = pd.DataFrame(
        {
            "instrument": raw.get("SECURITY_CODE", pd.Series(index=raw.index, dtype="object")).map(qlib_symbol),
            "announcement_date": pd.to_datetime(
                raw.get("NOTICE_DATE", pd.Series(index=raw.index, dtype="object")), errors="coerce"
            ),
            "receive_start_date": start,
            "receive_end_date": end.fillna(start),
            "institutional_survey_org_count": pd.to_numeric(
                raw.get("SUM", pd.Series(index=raw.index, dtype="float64")), errors="coerce"
            ),
        }
    )
    frame = frame.dropna(subset=["instrument", "announcement_date", "receive_start_date"])
    return (
        frame.groupby(
            ["instrument", "announcement_date", "receive_start_date", "receive_end_date"],
            as_index=False,
            sort=True,
            dropna=False,
        )["institutional_survey_org_count"]
        .max()
        .sort_values(["instrument", "announcement_date", "receive_start_date"], kind="stable")
        .reset_index(drop=True)
    )


def normalize_institutional_survey_rows(rows: Iterable[dict[str, Any]]) -> pd.DataFrame:
    """Aggregate public institutional-survey notices without participant data.

    The per-event maximum of source ``SUM`` is the reported number of received
    institutions, rather than the count of duplicated detail rows.  If a
    company discloses multiple received-date ranges on one notice date, their
    reported counts are summed and the separate events are retained as a
    second, independent intensity field.  Missing reported counts stay missing
    rather than being imputed as no institutional attention.
    """

    details = _institutional_survey_detail_frame(rows)
    return aggregate_institutional_survey_details(details)


def aggregate_institutional_survey_details(details: pd.DataFrame) -> pd.DataFrame:
    """Aggregate page-level institutional-survey events to score-time rows."""

    required = {
        "instrument",
        "announcement_date",
        "receive_start_date",
        "receive_end_date",
        "institutional_survey_org_count",
    }
    if missing := sorted(required - set(details.columns)):
        raise ValueError("institutional-survey detail frame is missing columns: " + ", ".join(missing))
    if details.empty:
        return pd.DataFrame(columns=INSTITUTIONAL_SURVEY_EVENT_COLUMNS)
    source = details.loc[:, sorted(required)].copy()
    for column in ("announcement_date", "receive_start_date", "receive_end_date"):
        source[column] = pd.to_datetime(source[column], errors="coerce")
    source["institutional_survey_org_count"] = pd.to_numeric(
        source["institutional_survey_org_count"], errors="coerce"
    )
    source = source.dropna(subset=["instrument", "announcement_date", "receive_start_date"])
    events = (
        source.groupby(
            ["instrument", "announcement_date", "receive_start_date", "receive_end_date"],
            as_index=False,
            sort=True,
            dropna=False,
        )["institutional_survey_org_count"]
        .max()
    )
    result = (
        events.groupby(["instrument", "announcement_date"], as_index=False, sort=True)
        .agg(
            institutional_survey_org_count=("institutional_survey_org_count", lambda values: values.sum(min_count=1)),
            institutional_survey_event_count=("receive_start_date", "size"),
        )
        .loc[:, list(INSTITUTIONAL_SURVEY_EVENT_COLUMNS)]
    )
    result["institutional_survey_event_count"] = pd.to_numeric(
        result["institutional_survey_event_count"], errors="coerce"
    ).astype(float)
    return result.sort_values(["instrument", "announcement_date"], kind="stable").reset_index(drop=True)


def normalize_repurchase_plan_rows(rows: Iterable[dict[str, Any]]) -> pd.DataFrame:
    """Reduce public repurchase plans to first-plan-date, non-outcome fields."""

    raw = pd.DataFrame(rows)
    if raw.empty:
        return pd.DataFrame(columns=REPURCHASE_EVENT_COLUMNS)
    frame = pd.DataFrame(
        {
            "instrument": raw.get("DIM_SCODE", pd.Series(index=raw.index, dtype="object")).map(qlib_symbol),
            "announcement_date": pd.to_datetime(
                raw.get("DIM_DATE", pd.Series(index=raw.index, dtype="object")), errors="coerce"
            ),
            "repurchase_planned_share_ratio": pd.to_numeric(
                raw.get("ZSZSX", pd.Series(index=raw.index, dtype="float64")), errors="coerce"
            ),
            "repurchase_planned_amount": pd.to_numeric(
                raw.get("JESX", pd.Series(index=raw.index, dtype="float64")), errors="coerce"
            ),
        }
    )
    frame = frame.dropna(subset=["instrument", "announcement_date"])
    return (
        frame.loc[:, list(REPURCHASE_EVENT_COLUMNS)]
        .sort_values(["instrument", "announcement_date"], kind="stable")
        .drop_duplicates(["instrument", "announcement_date"], keep="first")
        .reset_index(drop=True)
    )


def normalize_holder_count_rows(rows: Iterable[dict[str, Any]]) -> pd.DataFrame:
    """Reduce holder-count notices to announced, non-price change inputs."""

    raw = pd.DataFrame(rows)
    if raw.empty:
        return pd.DataFrame(columns=HOLDER_COUNT_EVENT_COLUMNS)
    frame = pd.DataFrame(
        {
            "instrument": raw.get("SECURITY_CODE", pd.Series(index=raw.index, dtype="object")).map(qlib_symbol),
            "announcement_date": pd.to_datetime(
                raw.get("HOLD_NOTICE_DATE", pd.Series(index=raw.index, dtype="object")), errors="coerce"
            ),
            "holder_count_change_ratio": pd.to_numeric(
                raw.get("HOLDER_NUM_RATIO", pd.Series(index=raw.index, dtype="float64")), errors="coerce"
            ),
            "holder_count_change_absolute": pd.to_numeric(
                raw.get("HOLDER_NUM_CHANGE", pd.Series(index=raw.index, dtype="float64")), errors="coerce"
            ),
        }
    )
    frame = frame.dropna(subset=["instrument", "announcement_date"])
    return (
        frame.loc[:, list(HOLDER_COUNT_EVENT_COLUMNS)]
        .sort_values(["instrument", "announcement_date"], kind="stable")
        .drop_duplicates(["instrument", "announcement_date"], keep="last")
        .reset_index(drop=True)
    )


def normalize_pledge_rows(rows: Iterable[dict[str, Any]]) -> pd.DataFrame:
    """Aggregate each notice-day's disclosed pledge quantities without live fields."""

    raw = pd.DataFrame(rows)
    if raw.empty:
        return pd.DataFrame(columns=PLEDGE_EVENT_COLUMNS)
    detail = pd.DataFrame(
        {
            "instrument": raw.get("SECURITY_CODE", pd.Series(index=raw.index, dtype="object")).map(qlib_symbol),
            "announcement_date": pd.to_datetime(
                raw.get("NOTICE_DATE", pd.Series(index=raw.index, dtype="object")), errors="coerce"
            ),
            "pledge_share_count": pd.to_numeric(
                raw.get("PF_NUM", pd.Series(index=raw.index, dtype="float64")), errors="coerce"
            ),
            "pledge_total_share_ratio": pd.to_numeric(
                raw.get("PF_TSR", pd.Series(index=raw.index, dtype="float64")), errors="coerce"
            ),
        }
    ).dropna(subset=["instrument", "announcement_date"])
    if detail.empty:
        return pd.DataFrame(columns=PLEDGE_EVENT_COLUMNS)
    result = (
        detail.groupby(["instrument", "announcement_date"], as_index=False, sort=True)
        .agg(
            pledge_share_count=("pledge_share_count", lambda values: values.sum(min_count=1)),
            pledge_total_share_ratio=("pledge_total_share_ratio", lambda values: values.sum(min_count=1)),
            pledge_event_count=("instrument", "size"),
        )
        .loc[:, list(PLEDGE_EVENT_COLUMNS)]
    )
    result["pledge_event_count"] = pd.to_numeric(result["pledge_event_count"], errors="coerce").astype(float)
    return result.sort_values(["instrument", "announcement_date"], kind="stable").reset_index(drop=True)


def normalize_dividend_plan_rows(rows: Iterable[dict[str, Any]]) -> pd.DataFrame:
    """Aggregate initial public dividend-plan terms by instrument and notice date."""

    raw = pd.DataFrame(rows)
    if raw.empty:
        return pd.DataFrame(columns=DIVIDEND_PLAN_EVENT_COLUMNS)
    detail = pd.DataFrame(
        {
            "instrument": raw.get("SECURITY_CODE", pd.Series(index=raw.index, dtype="object")).map(qlib_symbol),
            "announcement_date": pd.to_datetime(
                raw.get("PLAN_NOTICE_DATE", pd.Series(index=raw.index, dtype="object")), errors="coerce"
            ),
            "dividend_cash_per_ten": pd.to_numeric(
                raw.get("PRETAX_BONUS_RMB", pd.Series(index=raw.index, dtype="float64")), errors="coerce"
            ),
            "dividend_share_ratio": pd.to_numeric(
                raw.get("BONUS_IT_RATIO", pd.Series(index=raw.index, dtype="float64")), errors="coerce"
            ),
        }
    ).dropna(subset=["instrument", "announcement_date"])
    if detail.empty:
        return pd.DataFrame(columns=DIVIDEND_PLAN_EVENT_COLUMNS)
    result = (
        detail.groupby(["instrument", "announcement_date"], as_index=False, sort=True)
        .agg(
            dividend_cash_per_ten=("dividend_cash_per_ten", lambda values: values.sum(min_count=1)),
            dividend_share_ratio=("dividend_share_ratio", lambda values: values.sum(min_count=1)),
            dividend_plan_event_count=("instrument", "size"),
        )
        .loc[:, list(DIVIDEND_PLAN_EVENT_COLUMNS)]
    )
    result["dividend_plan_event_count"] = pd.to_numeric(
        result["dividend_plan_event_count"], errors="coerce"
    ).astype(float)
    return result.sort_values(["instrument", "announcement_date"], kind="stable").reset_index(drop=True)


def merge_margin_financing_event_frames(existing: pd.DataFrame, fetched: pd.DataFrame) -> pd.DataFrame:
    """Append a newer event retrieval without silently retaining duplicate days.

    Daily public source rows can be corrected after an earlier download.  On an
    explicit incremental refresh, newly fetched rows therefore replace an
    existing instrument/date pair, while all untouched historical dates remain
    in the auditable local snapshot.
    """

    frames: list[pd.DataFrame] = []
    for frame in (existing, fetched):
        if frame.empty:
            continue
        missing = sorted(set(MARGIN_FINANCING_EVENT_COLUMNS) - set(frame.columns))
        if missing:
            raise ValueError(f"margin-financing event frame is missing columns: {', '.join(missing)}")
        frames.append(frame.loc[:, list(MARGIN_FINANCING_EVENT_COLUMNS)].copy())
    if not frames:
        return pd.DataFrame(columns=MARGIN_FINANCING_EVENT_COLUMNS)
    merged = pd.concat(frames, ignore_index=True)
    merged["trade_date"] = pd.to_datetime(merged["trade_date"], errors="coerce")
    return (
        merged.dropna(subset=["instrument", "trade_date"])
        .sort_values(["instrument", "trade_date"], kind="stable")
        .drop_duplicates(["instrument", "trade_date"], keep="last")
        .reset_index(drop=True)
    )


def _eastmoney_session() -> requests.Session:
    """Create the common public-datacenter session used by dated snapshots."""

    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://data.eastmoney.com/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        }
    )
    return session


def sync_fundamental_reports(
    report_dates: Iterable[str], output: Path, manifest: Path, *, report_frequency: str
) -> dict[str, Any]:
    """Download dated public financial reports and write an auditable local snapshot."""

    dates = list(report_dates)
    if report_frequency not in {"annual", "quarterly"}:
        raise ValueError("report_frequency must be annual or quarterly")
    if not dates:
        raise ValueError("at least one report date is required")

    session = _eastmoney_session()
    frames: list[pd.DataFrame] = []
    counts: dict[str, int] = {}
    for report_date in dates:
        rows = fetch_annual_report_rows(session, report_date)
        normalized = normalize_fundamental_rows(rows, report_date)
        frames.append(normalized)
        counts[report_date] = len(normalized)
        print(f"{report_date}: {len(normalized)} normalized {report_frequency}-report rows")

    merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=FUNDAMENTAL_COLUMNS)
    merged = merged.sort_values(["instrument", "report_date", "announcement_date"], kind="stable")
    merged = merged.drop_duplicates(["instrument", "report_date"], keep="first").reset_index(drop=True)
    if merged.empty:
        raise RuntimeError(f"{report_frequency}-report sync produced no usable rows")
    _atomic_write_parquet(output, merged)
    result = {
        "status": "completed",
        "source": {
            "provider": "Eastmoney public datacenter",
            "endpoint": EASTMONEY_DATACENTER_URL,
            "report": EASTMONEY_REPORT,
            "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        },
        "report_frequency": report_frequency,
        "report_dates": dates,
        "rows_by_report_date": counts,
        "rows_written": len(merged),
        "output": str(output.resolve()),
        "sha256": file_sha256(output),
        "limitations": [
            "The public source is queried as it exists today; later corrections may not reproduce the original disclosure values.",
            "The research join waits until the trading day after announcement_date, but it is not a substitute for an exchange-grade point-in-time fundamentals vendor.",
        ],
    }
    _atomic_write_text(manifest, json.dumps(result, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return result


def sync_fundamentals(start_year: int, end_year: int, output: Path, manifest: Path) -> dict[str, Any]:
    """Download annual quality inputs and write an auditable local snapshot."""

    return sync_fundamental_reports(
        annual_report_dates(start_year, end_year), output, manifest, report_frequency="annual"
    )


def sync_quarterly_fundamentals(
    start_year: int,
    end_year: int,
    output: Path,
    manifest: Path,
    through_report_date: str | None = None,
) -> dict[str, Any]:
    """Download quarterly quality inputs for post-announcement short-horizon research."""

    dates = quarterly_report_dates(start_year, end_year)
    if through_report_date is not None:
        through = pd.Timestamp(through_report_date).normalize()
        if pd.isna(through):
            raise ValueError("through_report_date must be a valid ISO date")
        dates = [date for date in dates if pd.Timestamp(date) <= through]
        if not dates:
            raise ValueError("through_report_date precedes the requested quarterly range")
    return sync_fundamental_reports(
        dates, output, manifest, report_frequency="quarterly"
    )


def sync_performance_forecasts(
    start_year: int,
    end_year: int,
    output: Path,
    manifest: Path,
    through_report_date: str | None = None,
) -> dict[str, Any]:
    """Download public net-profit forecast notices as dated event observations."""

    dates = quarterly_report_dates(start_year, end_year)
    if through_report_date is not None:
        through = pd.Timestamp(through_report_date).normalize()
        if pd.isna(through):
            raise ValueError("through_report_date must be a valid ISO date")
        dates = [date for date in dates if pd.Timestamp(date) <= through]
        if not dates:
            raise ValueError("through_report_date precedes the requested forecast range")
    session = _eastmoney_session()
    frames: list[pd.DataFrame] = []
    counts: dict[str, int] = {}
    for report_date in dates:
        rows = fetch_performance_forecast_rows(session, report_date)
        normalized = normalize_performance_forecast_rows(rows, report_date)
        frames.append(normalized)
        counts[report_date] = len(normalized)
        print(f"{report_date}: {len(normalized)} normalized performance-forecast rows")
    merged = (
        pd.concat(frames, ignore_index=True)
        if frames
        else pd.DataFrame(columns=PERFORMANCE_FORECAST_COLUMNS)
    )
    merged = merged.sort_values(["instrument", "report_date", "announcement_date"], kind="stable")
    merged = merged.drop_duplicates(["instrument", "report_date", "announcement_date"], keep="first").reset_index(drop=True)
    if merged.empty:
        raise RuntimeError("performance-forecast sync produced no usable rows")
    _atomic_write_parquet(output, merged)
    result = {
        "status": "completed",
        "source": {
            "provider": "Eastmoney public datacenter",
            "endpoint": EASTMONEY_DATACENTER_URL,
            "report": EASTMONEY_PERFORMANCE_FORECAST_REPORT,
            "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        },
        "report_frequency": "quarterly_forecast_event",
        "report_dates": dates,
        "rows_by_report_date": counts,
        "rows_written": len(merged),
        "output": str(output.resolve()),
        "sha256": file_sha256(output),
        "limitations": [
            "The public source is queried as it exists today; it may revise or omit the historical forecast visible on an earlier date.",
            "Only the provider's parent-company net-profit forecast rows (PREDICT_FINANCE_CODE=004) are retained; revenue, EPS, and non-recurring-profit forecasts are excluded.",
            "The research join waits until the trading day after announcement_date and retains later forecast notices as later events.",
            "This is a research event snapshot, not an exchange-grade point-in-time announcement database.",
        ],
    }
    _atomic_write_text(manifest, json.dumps(result, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return result


def sync_billboard_events(start_year: int, end_year: int, output: Path, manifest: Path) -> dict[str, Any]:
    """Download daily public billboard events as one auditable local snapshot."""

    if end_year < start_year:
        raise ValueError("--end-year must not be earlier than --start-year")
    session = _eastmoney_session()
    frames: list[pd.DataFrame] = []
    counts: dict[str, int] = {}
    for year in range(start_year, end_year + 1):
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        rows = fetch_billboard_rows(session, start_date, end_date)
        normalized = normalize_billboard_rows(rows)
        frames.append(normalized)
        counts[str(year)] = len(normalized)
        print(f"{year}: {len(normalized)} normalized daily-billboard events")
    merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=BILLBOARD_EVENT_COLUMNS)
    merged = merged.sort_values(["instrument", "trade_date"], kind="stable")
    merged = merged.drop_duplicates(["instrument", "trade_date"], keep="last").reset_index(drop=True)
    if merged.empty:
        raise RuntimeError("daily-billboard sync produced no usable events")
    _atomic_write_parquet(output, merged)
    result = {
        "status": "completed",
        "source": {
            "provider": "Eastmoney public datacenter",
            "endpoint": EASTMONEY_DATACENTER_URL,
            "report": EASTMONEY_BILLBOARD_REPORT,
            "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        },
        "event_frequency": "daily_after_close_billboard",
        "years": list(range(start_year, end_year + 1)),
        "rows_by_year": counts,
        "rows_written": len(merged),
        "output": str(output.resolve()),
        "sha256": file_sha256(output),
        "limitations": [
            "The public source is queried as it exists today and may revise or omit historical billboard entries.",
            "The source exposes D1/D2/D5/D10 post-event returns; this snapshot deliberately excludes them from both storage and scoring features.",
            "The join treats trade_date as a post-close event available before the next local session open; this timing assumption should be checked against an exchange-grade announcement feed before any live use.",
            "This is a research event snapshot, not an exchange-grade point-in-time disclosure database.",
        ],
    }
    _atomic_write_text(manifest, json.dumps(result, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return result


def sync_major_holder_events(start_year: int, end_year: int, output: Path, manifest: Path) -> dict[str, Any]:
    """Download public major-holder change notices as an auditable event snapshot."""

    if end_year < start_year:
        raise ValueError("--end-year must not be earlier than --start-year")
    session = _eastmoney_session()
    frames: list[pd.DataFrame] = []
    counts: dict[str, int] = {}
    for year in range(start_year, end_year + 1):
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        rows = fetch_major_holder_rows(session, start_date, end_date)
        normalized = normalize_major_holder_rows(rows)
        frames.append(normalized)
        counts[str(year)] = len(normalized)
        print(f"{year}: {len(normalized)} normalized major-holder notice events")
    merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=MAJOR_HOLDER_EVENT_COLUMNS)
    merged = merged.sort_values(["instrument", "announcement_date"], kind="stable")
    merged = merged.drop_duplicates(["instrument", "announcement_date"], keep="last").reset_index(drop=True)
    if merged.empty:
        raise RuntimeError("major-holder event sync produced no usable events")
    _atomic_write_parquet(output, merged)
    result = {
        "status": "completed",
        "source": {
            "provider": "Eastmoney public datacenter",
            "endpoint": EASTMONEY_DATACENTER_URL,
            "report": EASTMONEY_MAJOR_HOLDER_REPORT,
            "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        },
        "event_frequency": "dated_major_holder_change_notice",
        "years": list(range(start_year, end_year + 1)),
        "rows_by_year": counts,
        "rows_written": len(merged),
        "output": str(output.resolve()),
        "sha256": file_sha256(output),
        "limitations": [
            "The public source is queried as it exists today and may revise or omit historical change notices.",
            "END_DATE and TRADE_DATE are transaction-period fields and are deliberately neither stored nor used for signal timing.",
            "The join waits until the local trading day after NOTICE_DATE because the public source does not provide a reliable intraday filing timestamp.",
            "The event is a report of holder transactions that can have occurred over a prior period; it is not a real-time order-flow signal.",
            "This is a research event snapshot, not an exchange-grade point-in-time announcement database.",
        ],
    }
    _atomic_write_text(manifest, json.dumps(result, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return result


def sync_block_trade_events(start_year: int, end_year: int, output: Path, manifest: Path) -> dict[str, Any]:
    """Download daily public block-trade aggregates as an auditable event snapshot."""

    if end_year < start_year:
        raise ValueError("--end-year must not be earlier than --start-year")
    session = _eastmoney_session()
    frames: list[pd.DataFrame] = []
    counts: dict[str, int] = {}
    for year in range(start_year, end_year + 1):
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        rows = fetch_block_trade_rows(session, start_date, end_date)
        normalized = normalize_block_trade_rows(rows)
        frames.append(normalized)
        counts[str(year)] = len(normalized)
        print(f"{year}: {len(normalized)} normalized block-trade stock/day events")
    merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=BLOCK_TRADE_EVENT_COLUMNS)
    merged = merged.sort_values(["instrument", "trade_date"], kind="stable")
    merged = merged.drop_duplicates(["instrument", "trade_date"], keep="last").reset_index(drop=True)
    if merged.empty:
        raise RuntimeError("block-trade event sync produced no usable events")
    _atomic_write_parquet(output, merged)
    result = {
        "status": "completed",
        "source": {
            "provider": "Eastmoney public datacenter",
            "endpoint": EASTMONEY_DATACENTER_URL,
            "report": EASTMONEY_BLOCK_TRADE_REPORT,
            "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        },
        "event_frequency": "daily_after_close_block_trade",
        "years": list(range(start_year, end_year + 1)),
        "rows_by_year": counts,
        "rows_written": len(merged),
        "output": str(output.resolve()),
        "sha256": file_sha256(output),
        "limitations": [
            "The public source is queried as it exists today and may revise or omit historical block-trade entries.",
            "The source exposes 1/5/10/20-day post-trade price-change fields; they are deliberately excluded from both request and storage.",
            "The join treats trade_date as a post-close event available before the next local session open; this timing assumption should be checked against an exchange-grade dissemination feed before live use.",
            "This is a research event snapshot, not an exchange-grade point-in-time block-trade database.",
        ],
    }
    _atomic_write_text(manifest, json.dumps(result, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return result


def sync_margin_financing_top_flow_events(
    provider_uri: Path,
    start: str,
    end: str | None,
    top_n: int,
    output: Path,
    manifest: Path,
    merge_existing: bool = False,
) -> dict[str, Any]:
    """Download one fixed daily Top-N financing-flow snapshot from local sessions.

    The local calendar determines which sessions are requested, so Chinese
    market holidays are not mistaken for failed provider calls.  If the public
    source has not yet published a local session, it is retained separately as
    source lag; no stale row is invented for that session.
    """

    if not 1 <= top_n <= 500:
        raise ValueError("top_n must be between 1 and 500")
    start_date = pd.Timestamp(start).normalize()
    if pd.isna(start_date):
        raise ValueError("start must be a valid ISO date")
    calendar = local_trading_calendar(provider_uri, end=end)
    end_date = pd.Timestamp(end).normalize() if end is not None else calendar.max().normalize()
    if pd.isna(end_date) or end_date < start_date:
        raise ValueError("end must be a valid ISO date not earlier than start")
    sessions = calendar[(calendar >= start_date) & (calendar <= end_date)]
    if not len(sessions):
        raise ValueError("no local trading sessions fall within the requested margin-financing range")
    session = _eastmoney_session()
    frames: list[pd.DataFrame] = []
    unavailable_dates: list[str] = []
    rows_by_year: dict[str, int] = {}
    sessions_by_year: dict[str, int] = {}
    for position, trade_date in enumerate(sessions, start=1):
        date_text = pd.Timestamp(trade_date).date().isoformat()
        raw = fetch_margin_financing_top_flow_rows(session, date_text, top_n)
        normalized = normalize_margin_financing_top_flow_rows(raw)
        year = str(pd.Timestamp(trade_date).year)
        sessions_by_year[year] = sessions_by_year.get(year, 0) + 1
        rows_by_year[year] = rows_by_year.get(year, 0) + len(normalized)
        if normalized.empty:
            unavailable_dates.append(date_text)
        else:
            frames.append(normalized)
        if position % 50 == 0 or position == len(sessions):
            print(
                f"margin financing: {position}/{len(sessions)} sessions; "
                f"{sum(len(frame) for frame in frames)} normalized stock/day events"
            )
        # The public endpoint is queried once per local market session.  Keep a
        # small, fixed inter-request pause instead of parallelizing the source.
        time.sleep(0.05)
    fetched = (
        pd.concat(frames, ignore_index=True)
        if frames
        else pd.DataFrame(columns=MARGIN_FINANCING_EVENT_COLUMNS)
    )
    fetched = merge_margin_financing_event_frames(pd.DataFrame(), fetched)
    existing = load_margin_financing_events(output) if merge_existing and output.exists() else pd.DataFrame()
    merged = merge_margin_financing_event_frames(existing, fetched)
    if merged.empty:
        raise RuntimeError("margin-financing top-flow sync produced no usable A-share events")
    _atomic_write_parquet(output, merged)
    result = {
        "status": "completed",
        "source": {
            "provider": "Eastmoney public datacenter",
            "endpoint": EASTMONEY_DATACENTER_URL,
            "report": EASTMONEY_MARGIN_FINANCING_REPORT,
            "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        },
        "event_frequency": "daily_after_close_margin_financing_top_flow",
        "selection_rule": {
            "sort": "RZJME descending (same-session financing net buy amount)",
            "top_n": top_n,
            "not_observed_means_zero": False,
        },
        "requested_calendar_start": sessions.min().date().isoformat(),
        "requested_calendar_end": sessions.max().date().isoformat(),
        "sessions_requested": int(len(sessions)),
        "sessions_by_year": sessions_by_year,
        "fetched_rows_by_year": rows_by_year,
        "rows_by_year": {
            str(year): int(len(group))
            for year, group in merged.groupby(pd.to_datetime(merged["trade_date"]).dt.year, sort=True)
        },
        "source_not_published_dates": unavailable_dates,
        "merge_existing": merge_existing,
        "existing_rows_before_merge": int(len(existing)),
        "fetched_rows": int(len(fetched)),
        "rows_written": len(merged),
        "output": str(output.resolve()),
        "sha256": file_sha256(output),
        "limitations": [
            "Only the predeclared top N financing net-buy rows per local session are retained; omitted stocks are not treated as zero flow.",
            "The public report exposes RCHANGE3DCP/RCHANGE5DCP/RCHANGE10DCP post-session price changes. They are excluded from the request, storage, and scoring schema.",
            "The source is a current public snapshot and can revise or omit historical rows; it is not an exchange-grade point-in-time financing database.",
            "The event is treated as available after its session close for a next-local-session-open decision; the source does not provide a publication timestamp to prove an earlier availability.",
        ],
    }
    _atomic_write_text(manifest, json.dumps(result, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return result


def sync_institutional_survey_events(
    start_year: int, end_year: int, output: Path, manifest: Path
) -> dict[str, Any]:
    """Download long-history institutional-survey notice aggregates.

    The detailed public report is paginated.  Its fixed ``NUMBERNEW=1`` filter
    selects one row per disclosure, then each page is normalized immediately
    and only non-identifying event aggregates are kept in memory.  A final
    re-aggregation across all pages prevents an event split by pagination from
    being counted twice.
    """

    if end_year < start_year:
        raise ValueError("--end-year must not be earlier than --start-year")
    session = _eastmoney_session()
    detail_frames: list[pd.DataFrame] = []
    pages_by_year: dict[str, int] = {}
    source_detail_rows_by_year: dict[str, int] = {}
    for year in range(start_year, end_year + 1):
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        first = _eastmoney_institutional_survey_request(session, start_date, end_date, page_number=1)
        result = first["result"]
        pages = int(result.get("pages") or 0)
        pages_by_year[str(year)] = pages
        source_rows = 0
        for page_number in range(1, pages + 1):
            payload = first if page_number == 1 else _eastmoney_institutional_survey_request(
                session, start_date, end_date, page_number=page_number
            )
            rows = list((payload.get("result") or {}).get("data") or [])
            source_rows += len(rows)
            normalized = _institutional_survey_detail_frame(rows)
            if not normalized.empty:
                detail_frames.append(normalized)
            if page_number % 100 == 0 or page_number == pages:
                print(
                    f"institutional surveys {year}: {page_number}/{pages} pages; "
                    f"{source_rows} source detail rows"
                )
            # The detailed report begins returning 9701 (server busy) when
            # paged too quickly.  Keep the history sync single-threaded and
            # deliberately below that observed limit; retry backoff above is
            # retained for transient provider pressure.
            time.sleep(1.25)
        source_detail_rows_by_year[str(year)] = source_rows
    details = (
        pd.concat(detail_frames, ignore_index=True)
        if detail_frames
        else pd.DataFrame(
            columns=[
                "instrument",
                "announcement_date",
                "receive_start_date",
                "receive_end_date",
                "institutional_survey_org_count",
            ]
        )
    )
    merged = aggregate_institutional_survey_details(details)
    if merged.empty:
        raise RuntimeError("institutional-survey sync produced no usable A-share notice events")
    _atomic_write_parquet(output, merged)
    result = {
        "status": "completed",
        "source": {
            "provider": "Eastmoney public datacenter",
            "endpoint": EASTMONEY_DATACENTER_URL,
            "report": EASTMONEY_INSTITUTIONAL_SURVEY_REPORT,
            "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        },
        "event_frequency": "dated_institutional_survey_notice",
        "years": list(range(start_year, end_year + 1)),
        "pages_by_year": pages_by_year,
        "source_detail_rows_by_year": source_detail_rows_by_year,
        "rows_by_announcement_year": {
            str(year): int(len(group))
            for year, group in merged.groupby(pd.to_datetime(merged["announcement_date"]).dt.year, sort=True)
        },
        "rows_written": len(merged),
        "output": str(output.resolve()),
        "sha256": file_sha256(output),
        "limitations": [
            "The public source is queried as it exists today and may revise or omit historical survey notices.",
            "The compact survey-statistics report retains only short recent history, so this snapshot aggregates the long-history detailed report by issuer, NOTICE_DATE, and received-date range.",
            "The request fixes NUMBERNEW=1 to retain a single detailed row per disclosure; participant names and identities are neither requested nor stored, while SUM is retained as the provider's reported institution count.",
            "The join waits until the local trading day after NOTICE_DATE because the source has no reliable intraday publication timestamp.",
            "This is a research event snapshot, not an exchange-grade point-in-time announcement database.",
        ],
    }
    _atomic_write_text(manifest, json.dumps(result, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return result


def sync_repurchase_plan_events(output: Path, manifest: Path) -> dict[str, Any]:
    """Download the complete public repurchase-plan list as a dated snapshot."""

    session = _eastmoney_session()
    first = _eastmoney_repurchase_request(session, page_number=1)
    result = first["result"]
    pages = int(result.get("pages") or 0)
    if pages < 1:
        raise RuntimeError("repurchase-plan source reported no pages")
    frames: list[pd.DataFrame] = []
    source_rows = 0
    for page_number in range(1, pages + 1):
        payload = first if page_number == 1 else _eastmoney_repurchase_request(session, page_number)
        rows = list((payload.get("result") or {}).get("data") or [])
        source_rows += len(rows)
        normalized = normalize_repurchase_plan_rows(rows)
        if not normalized.empty:
            frames.append(normalized)
    merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=REPURCHASE_EVENT_COLUMNS)
    merged = (
        merged.sort_values(["instrument", "announcement_date"], kind="stable")
        .drop_duplicates(["instrument", "announcement_date"], keep="first")
        .reset_index(drop=True)
    )
    if merged.empty:
        raise RuntimeError("repurchase-plan sync produced no usable A-share plan events")
    _atomic_write_parquet(output, merged)
    report = {
        "status": "completed",
        "source": {
            "provider": "Eastmoney public datacenter",
            "endpoint": EASTMONEY_DATACENTER_URL,
            "report": EASTMONEY_REPURCHASE_REPORT,
            "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        },
        "event_frequency": "dated_repurchase_plan_announcement",
        "pages": pages,
        "source_rows": source_rows,
        "rows_by_announcement_year": {
            str(year): int(len(group))
            for year, group in merged.groupby(pd.to_datetime(merged["announcement_date"]).dt.year, sort=True)
        },
        "rows_written": len(merged),
        "output": str(output.resolve()),
        "sha256": file_sha256(output),
        "limitations": [
            "The source is a current public snapshot and may revise or omit historical plans.",
            "DIM_DATE is treated as the initial public plan-record date and is made effective only on the strictly next local trading session.",
            "UPDATEDATE, implementation progress, completed share count, and completed repurchase amount are excluded because they can reflect later information.",
            "This is a research event snapshot, not an exchange-grade point-in-time disclosure database.",
        ],
    }
    _atomic_write_text(manifest, json.dumps(report, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return report


def sync_holder_count_events(start_year: int, end_year: int, output: Path, manifest: Path) -> dict[str, Any]:
    """Download dated public shareholder-count changes for every quarter end."""

    report_dates = quarterly_report_dates(start_year, end_year)
    session = _eastmoney_session()
    frames: list[pd.DataFrame] = []
    pages_by_report_date: dict[str, int] = {}
    source_rows_by_report_date: dict[str, int] = {}
    for report_date in report_dates:
        first = _eastmoney_holder_count_request(session, report_date, page_number=1)
        result = first["result"]
        pages = int(result.get("pages") or 0)
        pages_by_report_date[report_date] = pages
        source_rows = 0
        for page_number in range(1, pages + 1):
            payload = first if page_number == 1 else _eastmoney_holder_count_request(
                session, report_date, page_number
            )
            rows = list((payload.get("result") or {}).get("data") or [])
            source_rows += len(rows)
            normalized = normalize_holder_count_rows(rows)
            if not normalized.empty:
                frames.append(normalized)
        source_rows_by_report_date[report_date] = source_rows
        print(f"{report_date}: {pages} pages; {source_rows} holder-count source rows")
    merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=HOLDER_COUNT_EVENT_COLUMNS)
    merged = (
        merged.sort_values(["instrument", "announcement_date"], kind="stable")
        .drop_duplicates(["instrument", "announcement_date"], keep="last")
        .reset_index(drop=True)
    )
    if merged.empty:
        raise RuntimeError("holder-count sync produced no usable A-share notice events")
    _atomic_write_parquet(output, merged)
    result = {
        "status": "completed",
        "source": {
            "provider": "Eastmoney public datacenter",
            "endpoint": EASTMONEY_DATACENTER_URL,
            "report": EASTMONEY_HOLDER_COUNT_REPORT,
            "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        },
        "event_frequency": "quarterly_end_dated_holder_count_notice",
        "report_dates": report_dates,
        "pages_by_report_date": pages_by_report_date,
        "source_rows_by_report_date": source_rows_by_report_date,
        "rows_by_announcement_year": {
            str(year): int(len(group))
            for year, group in merged.groupby(pd.to_datetime(merged["announcement_date"]).dt.year, sort=True)
        },
        "rows_written": len(merged),
        "output": str(output.resolve()),
        "sha256": file_sha256(output),
        "limitations": [
            "The public source is queried as it exists today and can revise or omit historical records.",
            "END_DATE is a holder-count cutoff, not a score-time date; the join uses only the strictly later local session after HOLD_NOTICE_DATE.",
            "INTERVAL_CHRATE, AVG_MARKET_CAP, AVG_HOLD_NUM, TOTAL_MARKET_CAP, and TOTAL_A_SHARES are excluded at request time because they are price- or later-state-derived fields outside this hypothesis.",
            "This is a research event snapshot, not an exchange-grade point-in-time disclosure database.",
        ],
    }
    _atomic_write_text(manifest, json.dumps(result, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return result


def sync_pledge_events(start_year: int, end_year: int, output: Path, manifest: Path) -> dict[str, Any]:
    """Download all dated public share-pledge notices in the requested years."""

    if start_year > end_year:
        raise ValueError("start_year must not be after end_year")
    session = _eastmoney_session()
    frames: list[pd.DataFrame] = []
    pages_by_year: dict[str, int] = {}
    source_rows_by_year: dict[str, int] = {}
    for year in range(start_year, end_year + 1):
        first = _eastmoney_pledge_request(session, year, page_number=1)
        result = first["result"]
        pages = int(result.get("pages") or 0)
        pages_by_year[str(year)] = pages
        source_rows = 0
        for page_number in range(1, pages + 1):
            payload = first if page_number == 1 else _eastmoney_pledge_request(session, year, page_number)
            rows = list((payload.get("result") or {}).get("data") or [])
            source_rows += len(rows)
            normalized = normalize_pledge_rows(rows)
            if not normalized.empty:
                frames.append(normalized)
        source_rows_by_year[str(year)] = source_rows
        print(f"{year}: {pages} pages; {source_rows} pledge source rows")
    merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=PLEDGE_EVENT_COLUMNS)
    merged = (
        merged.groupby(["instrument", "announcement_date"], as_index=False, sort=True)
        .agg(
            pledge_share_count=("pledge_share_count", lambda values: values.sum(min_count=1)),
            pledge_total_share_ratio=("pledge_total_share_ratio", lambda values: values.sum(min_count=1)),
            pledge_event_count=("pledge_event_count", "sum"),
        )
        .loc[:, list(PLEDGE_EVENT_COLUMNS)]
        .sort_values(["instrument", "announcement_date"], kind="stable")
        .reset_index(drop=True)
    )
    if merged.empty:
        raise RuntimeError("pledge sync produced no usable A-share notice events")
    _atomic_write_parquet(output, merged)
    result = {
        "status": "completed",
        "source": {
            "provider": "Eastmoney public datacenter",
            "endpoint": EASTMONEY_DATACENTER_URL,
            "report": EASTMONEY_PLEDGE_REPORT,
            "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        },
        "event_frequency": "dated_share_pledge_notice",
        "years": list(range(start_year, end_year + 1)),
        "pages_by_year": pages_by_year,
        "source_rows_by_year": source_rows_by_year,
        "rows_by_announcement_year": {
            str(year): int(len(group))
            for year, group in merged.groupby(pd.to_datetime(merged["announcement_date"]).dt.year, sort=True)
        },
        "rows_written": len(merged),
        "output": str(output.resolve()),
        "sha256": file_sha256(output),
        "limitations": [
            "The public source is queried as it exists today and can revise or omit historical disclosures.",
            "NOTICE_DATE is treated as the public notice date and is made effective only on the strictly next local trading session.",
            "Only PF_NUM (disclosed pledged share count) and PF_TSR (the notice record's reported total-share ratio) are requested. Current prices, current trade date, current market value, warning/liquidation lines, and unfreeze state/dates are excluded at request time.",
            "This is a research event snapshot, not an exchange-grade point-in-time disclosure database.",
        ],
    }
    _atomic_write_text(manifest, json.dumps(result, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return result


def sync_dividend_plan_events(start_year: int, end_year: int, output: Path, manifest: Path) -> dict[str, Any]:
    """Download all dated public dividend-plan notices in the requested years."""

    if start_year > end_year:
        raise ValueError("start_year must not be after end_year")
    session = _eastmoney_session()
    frames: list[pd.DataFrame] = []
    pages_by_year: dict[str, int] = {}
    source_rows_by_year: dict[str, int] = {}
    for year in range(start_year, end_year + 1):
        first = _eastmoney_dividend_plan_request(session, year, page_number=1)
        result = first["result"]
        pages = int(result.get("pages") or 0)
        pages_by_year[str(year)] = pages
        source_rows = 0
        for page_number in range(1, pages + 1):
            payload = first if page_number == 1 else _eastmoney_dividend_plan_request(session, year, page_number)
            rows = list((payload.get("result") or {}).get("data") or [])
            source_rows += len(rows)
            normalized = normalize_dividend_plan_rows(rows)
            if not normalized.empty:
                frames.append(normalized)
        source_rows_by_year[str(year)] = source_rows
        print(f"{year}: {pages} pages; {source_rows} dividend-plan source rows")
    merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=DIVIDEND_PLAN_EVENT_COLUMNS)
    merged = (
        merged.groupby(["instrument", "announcement_date"], as_index=False, sort=True)
        .agg(
            dividend_cash_per_ten=("dividend_cash_per_ten", lambda values: values.sum(min_count=1)),
            dividend_share_ratio=("dividend_share_ratio", lambda values: values.sum(min_count=1)),
            dividend_plan_event_count=("dividend_plan_event_count", "sum"),
        )
        .loc[:, list(DIVIDEND_PLAN_EVENT_COLUMNS)]
        .sort_values(["instrument", "announcement_date"], kind="stable")
        .reset_index(drop=True)
    )
    if merged.empty:
        raise RuntimeError("dividend-plan sync produced no usable A-share notice events")
    _atomic_write_parquet(output, merged)
    result = {
        "status": "completed",
        "source": {
            "provider": "Eastmoney public datacenter",
            "endpoint": EASTMONEY_DATACENTER_URL,
            "report": EASTMONEY_DIVIDEND_PLAN_REPORT,
            "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        },
        "event_frequency": "dated_dividend_plan_notice",
        "years": list(range(start_year, end_year + 1)),
        "pages_by_year": pages_by_year,
        "source_rows_by_year": source_rows_by_year,
        "rows_by_announcement_year": {
            str(year): int(len(group))
            for year, group in merged.groupby(pd.to_datetime(merged["announcement_date"]).dt.year, sort=True)
        },
        "rows_written": len(merged),
        "output": str(output.resolve()),
        "sha256": file_sha256(output),
        "limitations": [
            "The public source is queried as it exists today and can revise or omit historical plan records.",
            "PLAN_NOTICE_DATE is treated as the initial public plan notice and is made effective only on the strictly next local trading session.",
            "Only PRETAX_BONUS_RMB (cash dividend per ten shares) and BONUS_IT_RATIO (announced total bonus/share-transfer ratio) are requested. ASSIGN_PROGRESS, NOTICE_DATE, equity-record/ex-dividend dates, dividend yield, financial fields, and forward-return fields are excluded at request time.",
            "This is a research event snapshot, not an exchange-grade point-in-time disclosure database.",
        ],
    }
    _atomic_write_text(manifest, json.dumps(result, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return result


def merge_quarterly_fundamentals(input_paths: Iterable[Path], output: Path, manifest: Path) -> dict[str, Any]:
    """Atomically combine independently downloaded quarterly snapshot chunks.

    Public report downloads can be lengthy.  This recovery path permits small
    date-range downloads without treating any individual chunk as a complete
    research source.  The final output remains a single de-duplicated,
    auditable snapshot.
    """

    paths = [Path(path).expanduser() for path in input_paths]
    if not paths:
        raise ValueError("at least one quarterly snapshot input is required")
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"quarterly snapshot inputs do not exist: {', '.join(missing)}")
    frames = [load_fundamentals(path) for path in paths]
    merged = pd.concat(frames, ignore_index=True)
    merged = merged.sort_values(["instrument", "report_date", "announcement_date"], kind="stable")
    merged = merged.drop_duplicates(["instrument", "report_date"], keep="first").reset_index(drop=True)
    if merged.empty:
        raise RuntimeError("quarterly snapshot merge produced no usable rows")
    report_dates = sorted(pd.Timestamp(value).date().isoformat() for value in merged["report_date"].unique())
    rows_by_report_date = {
        report_date: int((merged["report_date"] == pd.Timestamp(report_date)).sum()) for report_date in report_dates
    }
    _atomic_write_parquet(output, merged)
    result = {
        "status": "completed",
        "report_frequency": "quarterly",
        "source": {
            "provider": "Eastmoney public datacenter",
            "merged_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "input_files": [str(path.resolve()) for path in paths],
            "input_sha256": {str(path.resolve()): file_sha256(path) for path in paths},
        },
        "report_dates": report_dates,
        "rows_by_report_date": rows_by_report_date,
        "rows_written": len(merged),
        "output": str(output.expanduser().resolve()),
        "sha256": file_sha256(output),
        "limitations": [
            "Every chunk is a current public snapshot; later corrections may not reproduce the original disclosure values.",
            "The research join waits until the trading day after announcement_date, but it is not a substitute for an exchange-grade point-in-time fundamentals vendor.",
        ],
    }
    _atomic_write_text(manifest, json.dumps(result, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return result


def load_fundamentals(path: Path) -> pd.DataFrame:
    """Load and validate the local accounting-quality snapshot."""

    if not path.exists():
        raise FileNotFoundError(f"fundamental snapshot does not exist: {path}; run sync-fundamentals first")
    frame = pd.read_parquet(path)
    missing = sorted(set(FUNDAMENTAL_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"fundamental snapshot is missing columns: {', '.join(missing)}")
    frame = frame.loc[:, list(FUNDAMENTAL_COLUMNS)].copy()
    for column in ("report_date", "announcement_date"):
        frame[column] = pd.to_datetime(frame[column], errors="coerce")
    for column in ("roe", "net_profit", "revenue_yoy", "profit_yoy"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["instrument", "report_date", "announcement_date"])
    return frame.sort_values(["instrument", "announcement_date", "report_date"], kind="stable").reset_index(drop=True)


def load_performance_forecasts(path: Path) -> pd.DataFrame:
    """Load and validate the local public performance-forecast event snapshot."""

    if not path.exists():
        raise FileNotFoundError(
            f"performance-forecast snapshot does not exist: {path}; run sync-performance-forecasts first"
        )
    frame = pd.read_parquet(path)
    missing = sorted(set(PERFORMANCE_FORECAST_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"performance-forecast snapshot is missing columns: {', '.join(missing)}")
    frame = frame.loc[:, list(PERFORMANCE_FORECAST_COLUMNS)].copy()
    for column in ("report_date", "announcement_date"):
        frame[column] = pd.to_datetime(frame[column], errors="coerce")
    for column in ("forecast_profit_yoy", "forecast_profit_yoy_width"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["instrument", "report_date", "announcement_date"])
    return frame.sort_values(["instrument", "announcement_date", "report_date"], kind="stable").reset_index(drop=True)


def load_billboard_events(path: Path) -> pd.DataFrame:
    """Load and validate the local daily-billboard event snapshot."""

    if not path.exists():
        raise FileNotFoundError(f"daily-billboard snapshot does not exist: {path}; run sync-billboard-events first")
    frame = pd.read_parquet(path)
    missing = sorted(set(BILLBOARD_EVENT_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"daily-billboard snapshot is missing columns: {', '.join(missing)}")
    frame = frame.loc[:, list(BILLBOARD_EVENT_COLUMNS)].copy()
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce")
    for column in BILLBOARD_EVENT_COLUMNS[2:]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["instrument", "trade_date"])
    return frame.sort_values(["instrument", "trade_date"], kind="stable").reset_index(drop=True)


def load_major_holder_events(path: Path) -> pd.DataFrame:
    """Load and validate the local major-holder notice event snapshot."""

    if not path.exists():
        raise FileNotFoundError(f"major-holder event snapshot does not exist: {path}; run sync-major-holder-events first")
    frame = pd.read_parquet(path)
    missing = sorted(set(MAJOR_HOLDER_EVENT_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"major-holder event snapshot is missing columns: {', '.join(missing)}")
    frame = frame.loc[:, list(MAJOR_HOLDER_EVENT_COLUMNS)].copy()
    frame["announcement_date"] = pd.to_datetime(frame["announcement_date"], errors="coerce")
    for column in MAJOR_HOLDER_EVENT_COLUMNS[2:]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["instrument", "announcement_date"])
    return frame.sort_values(["instrument", "announcement_date"], kind="stable").reset_index(drop=True)


def load_block_trade_events(path: Path) -> pd.DataFrame:
    """Load and validate the local daily block-trade event snapshot."""

    if not path.exists():
        raise FileNotFoundError(f"block-trade snapshot does not exist: {path}; run sync-block-trade-events first")
    frame = pd.read_parquet(path)
    missing = sorted(set(BLOCK_TRADE_EVENT_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"block-trade snapshot is missing columns: {', '.join(missing)}")
    frame = frame.loc[:, list(BLOCK_TRADE_EVENT_COLUMNS)].copy()
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce")
    for column in BLOCK_TRADE_EVENT_COLUMNS[2:]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["instrument", "trade_date"])
    return frame.sort_values(["instrument", "trade_date"], kind="stable").reset_index(drop=True)


def load_margin_financing_events(path: Path) -> pd.DataFrame:
    """Load and validate the fixed daily Top-N financing-flow event snapshot."""

    if not path.exists():
        raise FileNotFoundError(
            f"margin-financing snapshot does not exist: {path}; run sync-margin-financing-events first"
        )
    frame = pd.read_parquet(path)
    missing = sorted(set(MARGIN_FINANCING_EVENT_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"margin-financing snapshot is missing columns: {', '.join(missing)}")
    frame = frame.loc[:, list(MARGIN_FINANCING_EVENT_COLUMNS)].copy()
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce")
    for column in MARGIN_FINANCING_EVENT_COLUMNS[2:]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["instrument", "trade_date"])
    return frame.sort_values(["instrument", "trade_date"], kind="stable").reset_index(drop=True)


def load_institutional_survey_events(path: Path) -> pd.DataFrame:
    """Load the non-identifying institutional-survey notice event snapshot."""

    if not path.exists():
        raise FileNotFoundError(
            f"institutional-survey snapshot does not exist: {path}; run sync-institutional-survey-events first"
        )
    frame = pd.read_parquet(path)
    missing = sorted(set(INSTITUTIONAL_SURVEY_EVENT_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"institutional-survey snapshot is missing columns: {', '.join(missing)}")
    frame = frame.loc[:, list(INSTITUTIONAL_SURVEY_EVENT_COLUMNS)].copy()
    frame["announcement_date"] = pd.to_datetime(frame["announcement_date"], errors="coerce")
    for column in INSTITUTIONAL_SURVEY_EVENT_COLUMNS[2:]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["instrument", "announcement_date"])
    return frame.sort_values(["instrument", "announcement_date"], kind="stable").reset_index(drop=True)


def load_repurchase_plan_events(path: Path) -> pd.DataFrame:
    """Load the dated non-outcome repurchase-plan event snapshot."""

    if not path.exists():
        raise FileNotFoundError(f"repurchase-plan snapshot does not exist: {path}; run sync-repurchase-plan-events first")
    frame = pd.read_parquet(path)
    missing = sorted(set(REPURCHASE_EVENT_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"repurchase-plan snapshot is missing columns: {', '.join(missing)}")
    frame = frame.loc[:, list(REPURCHASE_EVENT_COLUMNS)].copy()
    frame["announcement_date"] = pd.to_datetime(frame["announcement_date"], errors="coerce")
    for column in REPURCHASE_EVENT_COLUMNS[2:]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna(subset=["instrument", "announcement_date"]).sort_values(
        ["instrument", "announcement_date"], kind="stable"
    ).reset_index(drop=True)


def load_holder_count_events(path: Path) -> pd.DataFrame:
    """Load dated shareholder-count change notices without price-derived fields."""

    if not path.exists():
        raise FileNotFoundError(f"holder-count snapshot does not exist: {path}; run sync-holder-count-events first")
    frame = pd.read_parquet(path)
    missing = sorted(set(HOLDER_COUNT_EVENT_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"holder-count snapshot is missing columns: {', '.join(missing)}")
    frame = frame.loc[:, list(HOLDER_COUNT_EVENT_COLUMNS)].copy()
    frame["announcement_date"] = pd.to_datetime(frame["announcement_date"], errors="coerce")
    for column in HOLDER_COUNT_EVENT_COLUMNS[2:]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna(subset=["instrument", "announcement_date"]).sort_values(
        ["instrument", "announcement_date"], kind="stable"
    ).reset_index(drop=True)


def load_pledge_events(path: Path) -> pd.DataFrame:
    """Load dated share-pledge notices without current-state fields."""

    if not path.exists():
        raise FileNotFoundError(f"pledge snapshot does not exist: {path}; run sync-pledge-events first")
    frame = pd.read_parquet(path)
    missing = sorted(set(PLEDGE_EVENT_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"pledge snapshot is missing columns: {', '.join(missing)}")
    frame = frame.loc[:, list(PLEDGE_EVENT_COLUMNS)].copy()
    frame["announcement_date"] = pd.to_datetime(frame["announcement_date"], errors="coerce")
    for column in PLEDGE_EVENT_COLUMNS[2:]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna(subset=["instrument", "announcement_date"]).sort_values(
        ["instrument", "announcement_date"], kind="stable"
    ).reset_index(drop=True)


def load_dividend_plan_events(path: Path) -> pd.DataFrame:
    """Load dated initial dividend-plan notices without implementation fields."""

    if not path.exists():
        raise FileNotFoundError(f"dividend-plan snapshot does not exist: {path}; run sync-dividend-plan-events first")
    frame = pd.read_parquet(path)
    missing = sorted(set(DIVIDEND_PLAN_EVENT_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"dividend-plan snapshot is missing columns: {', '.join(missing)}")
    frame = frame.loc[:, list(DIVIDEND_PLAN_EVENT_COLUMNS)].copy()
    frame["announcement_date"] = pd.to_datetime(frame["announcement_date"], errors="coerce")
    for column in DIVIDEND_PLAN_EVENT_COLUMNS[2:]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna(subset=["instrument", "announcement_date"]).sort_values(
        ["instrument", "announcement_date"], kind="stable"
    ).reset_index(drop=True)


def _first_trading_day_after(calendar: pd.DatetimeIndex, announced: pd.Series) -> pd.Series:
    """Map announcements to the strictly next local trading day.

    The source does not tell us whether a filing was made before market open,
    therefore using the next session avoids same-day information leakage.
    """

    lookup = calendar.searchsorted(pd.DatetimeIndex(announced), side="right")
    mapped = pd.Series(pd.NaT, index=announced.index, dtype="datetime64[ns]")
    valid = lookup < len(calendar)
    mapped.loc[valid] = calendar.take(lookup[valid]).values
    return mapped


FUNDAMENTAL_ACCELERATION_COLUMNS = (
    "roe_change",
    "revenue_yoy_acceleration",
    "profit_yoy_acceleration",
)


def attach_fundamental_accelerations(events: pd.DataFrame) -> pd.DataFrame:
    """Add same-fiscal-quarter year-over-year changes using only earlier reports.

    These values belong to the newer report and therefore become usable only
    when that report itself is made effective after its announcement date in
    ``attach_quality_asof``.  No later report is used to backfill an earlier
    disclosure.
    """

    required = {"instrument", "report_date", "announcement_date", "roe", "revenue_yoy", "profit_yoy"}
    if missing := sorted(required - set(events.columns)):
        raise ValueError(f"fundamental events are missing columns: {', '.join(missing)}")
    result = events.sort_values(["instrument", "report_date", "announcement_date"], kind="stable").copy()
    # Annual data only has month 12, so this exactly preserves the original
    # year-to-year calculation.  Quarterly data must compare Q1 with the
    # previous Q1 (and so on), not with Q4's cumulative statement.
    result["_report_month"] = pd.to_datetime(result["report_date"]).dt.month
    for field, acceleration in (
        ("roe", "roe_change"),
        ("revenue_yoy", "revenue_yoy_acceleration"),
        ("profit_yoy", "profit_yoy_acceleration"),
    ):
        result[acceleration] = result.groupby(["instrument", "_report_month"], sort=False)[field].diff()
    return result.drop(columns="_report_month")


def attach_quality_asof(market: pd.DataFrame, fundamentals: pd.DataFrame, max_age_days: int = 550) -> pd.DataFrame:
    """Attach only already-announced accounting data to every market row.

    The operation is performed on a combined per-instrument timeline instead
    of a global ``merge_asof`` so a filing cannot be carried into another
    instrument.  ``quality_effective_date`` is retained for audit checks.
    """

    required_market = {"instrument", "datetime"}
    if missing := sorted(required_market - set(market.columns)):
        raise ValueError(f"market frame is missing columns: {', '.join(missing)}")
    market = market.reset_index(drop=True).copy()
    calendar = pd.DatetimeIndex(sorted(pd.to_datetime(market["datetime"]).dropna().unique()))
    events = attach_fundamental_accelerations(fundamentals)
    events["quality_effective_date"] = _first_trading_day_after(calendar, events["announcement_date"])
    events = events.dropna(subset=["quality_effective_date"])
    events = events.sort_values(
        ["instrument", "quality_effective_date", "report_date", "announcement_date"], kind="stable"
    ).drop_duplicates(["instrument", "quality_effective_date"], keep="last")

    quality_columns = [
        "report_date",
        "announcement_date",
        "roe",
        "net_profit",
        "revenue_yoy",
        "profit_yoy",
        *FUNDAMENTAL_ACCELERATION_COLUMNS,
        "quality_effective_date",
    ]
    daily = market[["instrument", "datetime"]].copy()
    daily["_kind"] = 1
    daily["_row"] = np.arange(len(daily))
    for column in ("report_date", "announcement_date", "quality_effective_date"):
        daily[column] = pd.NaT
    for column in ("roe", "net_profit", "revenue_yoy", "profit_yoy", *FUNDAMENTAL_ACCELERATION_COLUMNS):
        daily[column] = np.nan
    event_rows = events.rename(columns={"quality_effective_date": "datetime"})[
        ["instrument", "datetime", *[column for column in quality_columns if column != "quality_effective_date"]]
    ].copy()
    event_rows["quality_effective_date"] = event_rows["datetime"]
    event_rows["_kind"] = 0
    event_rows["_row"] = np.nan
    combined = pd.concat([daily, event_rows], ignore_index=True, sort=False)
    combined = combined.sort_values(["instrument", "datetime", "_kind"], kind="stable")
    combined[quality_columns] = combined.groupby("instrument", sort=False)[quality_columns].ffill()
    attached = combined.loc[combined["_row"].notna(), ["_row", *quality_columns]].copy()
    attached["_row"] = attached["_row"].astype(int)
    result = market.copy()
    result = result.join(attached.set_index("_row"), how="left")
    result["quality_age_days"] = (pd.to_datetime(result["datetime"]) - pd.to_datetime(result["quality_effective_date"])).dt.days
    result["quality_eligible"] = (
        result["roe"].ge(5.0)
        & result["net_profit"].gt(0.0)
        & result["revenue_yoy"].gt(0.0)
        & result["profit_yoy"].gt(0.0)
        & result["quality_age_days"].between(0, max_age_days)
    )
    return result


def attach_performance_forecasts_asof(
    market: pd.DataFrame, forecasts: pd.DataFrame, max_age_days: int = 30
) -> pd.DataFrame:
    """Attach public forecast events only after the following local session.

    This is intentionally independent from ``quality_eligible``: forecasts do
    not make a stock quality-qualified.  They only provide an event sample for
    measuring whether a fresh public profit forecast explains the next three
    trading days within the already-qualified universe.
    """

    required_market = {"instrument", "datetime"}
    if missing := sorted(required_market - set(market.columns)):
        raise ValueError(f"market frame is missing columns: {', '.join(missing)}")
    required_forecasts = set(PERFORMANCE_FORECAST_COLUMNS)
    if missing := sorted(required_forecasts - set(forecasts.columns)):
        raise ValueError(f"performance-forecast events are missing columns: {', '.join(missing)}")
    result = market.reset_index(drop=True).copy()
    calendar = pd.DatetimeIndex(sorted(pd.to_datetime(result["datetime"]).dropna().unique()))
    events = forecasts.loc[:, list(PERFORMANCE_FORECAST_COLUMNS)].copy()
    events["forecast_effective_date"] = _first_trading_day_after(calendar, events["announcement_date"])
    events = events.dropna(subset=["forecast_effective_date"])
    events = events.sort_values(
        ["instrument", "forecast_effective_date", "announcement_date", "report_date"], kind="stable"
    ).drop_duplicates(["instrument", "forecast_effective_date"], keep="last")

    forecast_columns = [
        "forecast_report_date",
        "forecast_announcement_date",
        "forecast_type",
        "forecast_turnaround",
        "forecast_profit_yoy",
        "forecast_profit_yoy_width",
        "forecast_effective_date",
    ]
    daily = result[["instrument", "datetime"]].copy()
    daily["_kind"] = 1
    daily["_row"] = np.arange(len(daily))
    for column in ("forecast_report_date", "forecast_announcement_date", "forecast_effective_date"):
        daily[column] = pd.NaT
    daily["forecast_type"] = pd.Series(pd.NA, index=daily.index, dtype="string")
    for column in ("forecast_turnaround", "forecast_profit_yoy", "forecast_profit_yoy_width"):
        daily[column] = np.nan
    event_rows = events.rename(
        columns={
            "forecast_effective_date": "datetime",
            "report_date": "forecast_report_date",
            "announcement_date": "forecast_announcement_date",
        }
    )[["instrument", "datetime", *[column for column in forecast_columns if column != "forecast_effective_date"]]].copy()
    event_rows["forecast_effective_date"] = event_rows["datetime"]
    event_rows["_kind"] = 0
    event_rows["_row"] = np.nan
    combined = pd.concat([daily, event_rows], ignore_index=True, sort=False)
    combined = combined.sort_values(["instrument", "datetime", "_kind"], kind="stable")
    combined[forecast_columns] = combined.groupby("instrument", sort=False)[forecast_columns].ffill()
    attached = combined.loc[combined["_row"].notna(), ["_row", *forecast_columns]].copy()
    attached["_row"] = attached["_row"].astype(int)
    result = result.join(attached.set_index("_row"), how="left")
    result["forecast_age_days"] = (
        pd.to_datetime(result["datetime"]) - pd.to_datetime(result["forecast_effective_date"])
    ).dt.days
    result["forecast_available"] = result["forecast_announcement_date"].notna() & result["forecast_age_days"].between(
        0, max_age_days
    )
    return result


def attach_billboard_events_asof(
    market: pd.DataFrame, events: pd.DataFrame, max_age_days: int = 3
) -> pd.DataFrame:
    """Attach same-close daily billboard events for next-session-open decisions.

    A daily billboard is a post-close disclosure.  This research score is
    formed after that same close and enters at the next local open, so the
    event's trade date is the effective signal date.  It never relaxes the
    accounting-quality gate; it only forms a bounded-age event sample within
    it.
    """

    if max_age_days < 0:
        raise ValueError("max_age_days must not be negative")
    required_market = {"instrument", "datetime"}
    if missing := sorted(required_market - set(market.columns)):
        raise ValueError(f"market frame is missing columns: {', '.join(missing)}")
    if missing := sorted(set(BILLBOARD_EVENT_COLUMNS) - set(events.columns)):
        raise ValueError(f"daily-billboard events are missing columns: {', '.join(missing)}")
    result = market.reset_index(drop=True).copy()
    calendar = pd.DatetimeIndex(sorted(pd.to_datetime(result["datetime"]).dropna().unique()))
    source_events = events.loc[:, list(BILLBOARD_EVENT_COLUMNS)].copy()
    source_events["billboard_effective_date"] = pd.to_datetime(source_events["trade_date"])
    source_events = source_events.loc[source_events["billboard_effective_date"].isin(calendar)].copy()
    source_events = source_events.sort_values(
        ["instrument", "billboard_effective_date", "trade_date"], kind="stable"
    ).drop_duplicates(["instrument", "billboard_effective_date"], keep="last")

    billboard_columns = [
        "billboard_trade_date",
        "billboard_net_flow_to_float",
        "billboard_net_flow_to_deal",
        "billboard_deal_to_float",
        "billboard_reason_count",
        "billboard_effective_date",
    ]
    daily = result[["instrument", "datetime"]].copy()
    daily["_kind"] = 1
    daily["_row"] = np.arange(len(daily))
    for column in ("billboard_trade_date", "billboard_effective_date"):
        daily[column] = pd.NaT
    for column in billboard_columns[1:-1]:
        daily[column] = np.nan
    event_rows = source_events.rename(
        columns={"billboard_effective_date": "datetime", "trade_date": "billboard_trade_date"}
    )[["instrument", "datetime", *[column for column in billboard_columns if column != "billboard_effective_date"]]].copy()
    event_rows["billboard_effective_date"] = event_rows["datetime"]
    event_rows["_kind"] = 0
    event_rows["_row"] = np.nan
    combined = pd.concat([daily, event_rows], ignore_index=True, sort=False)
    combined = combined.sort_values(["instrument", "datetime", "_kind"], kind="stable")
    combined[billboard_columns] = combined.groupby("instrument", sort=False)[billboard_columns].ffill()
    attached = combined.loc[combined["_row"].notna(), ["_row", *billboard_columns]].copy()
    attached["_row"] = attached["_row"].astype(int)
    result = result.join(attached.set_index("_row"), how="left")
    result["billboard_age_days"] = (
        pd.to_datetime(result["datetime"]) - pd.to_datetime(result["billboard_effective_date"])
    ).dt.days
    result["billboard_available"] = result["billboard_trade_date"].notna() & result["billboard_age_days"].between(
        0, max_age_days
    )
    return result


def attach_major_holder_events_asof(
    market: pd.DataFrame, events: pd.DataFrame, max_age_days: int = 3
) -> pd.DataFrame:
    """Attach major-holder notices only after the following local session.

    The provider exposes historical transaction dates, but those are not used:
    a public notice can summarize activity that occurred days or months earlier.
    It becomes available only after its ``announcement_date``, conservatively
    on the next local trading day, and remains a short bounded-age event.
    """

    if max_age_days < 0:
        raise ValueError("max_age_days must not be negative")
    required_market = {"instrument", "datetime"}
    if missing := sorted(required_market - set(market.columns)):
        raise ValueError(f"market frame is missing columns: {', '.join(missing)}")
    if missing := sorted(set(MAJOR_HOLDER_EVENT_COLUMNS) - set(events.columns)):
        raise ValueError(f"major-holder events are missing columns: {', '.join(missing)}")
    result = market.reset_index(drop=True).copy()
    calendar = pd.DatetimeIndex(sorted(pd.to_datetime(result["datetime"]).dropna().unique()))
    source_events = events.loc[:, list(MAJOR_HOLDER_EVENT_COLUMNS)].copy()
    source_events["major_holder_effective_date"] = _first_trading_day_after(
        calendar, source_events["announcement_date"]
    )
    source_events = source_events.dropna(subset=["major_holder_effective_date"])
    source_events = source_events.sort_values(
        ["instrument", "major_holder_effective_date", "announcement_date"], kind="stable"
    ).drop_duplicates(["instrument", "major_holder_effective_date"], keep="last")

    holder_columns = [
        "major_holder_announcement_date",
        "major_holder_net_change_free_ratio",
        "major_holder_increase_free_ratio",
        "major_holder_decrease_free_ratio",
        "major_holder_event_count",
        "major_holder_effective_date",
    ]
    daily = result[["instrument", "datetime"]].copy()
    daily["_kind"] = 1
    daily["_row"] = np.arange(len(daily))
    for column in ("major_holder_announcement_date", "major_holder_effective_date"):
        daily[column] = pd.NaT
    for column in holder_columns[1:-1]:
        daily[column] = np.nan
    event_rows = source_events.rename(
        columns={
            "major_holder_effective_date": "datetime",
            "announcement_date": "major_holder_announcement_date",
        }
    )[["instrument", "datetime", *[column for column in holder_columns if column != "major_holder_effective_date"]]].copy()
    event_rows["major_holder_effective_date"] = event_rows["datetime"]
    event_rows["_kind"] = 0
    event_rows["_row"] = np.nan
    combined = pd.concat([daily, event_rows], ignore_index=True, sort=False)
    combined = combined.sort_values(["instrument", "datetime", "_kind"], kind="stable")
    combined[holder_columns] = combined.groupby("instrument", sort=False)[holder_columns].ffill()
    attached = combined.loc[combined["_row"].notna(), ["_row", *holder_columns]].copy()
    attached["_row"] = attached["_row"].astype(int)
    result = result.join(attached.set_index("_row"), how="left")
    result["major_holder_age_days"] = (
        pd.to_datetime(result["datetime"]) - pd.to_datetime(result["major_holder_effective_date"])
    ).dt.days
    result["major_holder_available"] = result["major_holder_announcement_date"].notna() & result[
        "major_holder_age_days"
    ].between(0, max_age_days)
    return result


def attach_block_trade_events_asof(
    market: pd.DataFrame, events: pd.DataFrame, max_age_days: int = 3
) -> pd.DataFrame:
    """Attach same-close block-trade events for next-session-open decisions."""

    if max_age_days < 0:
        raise ValueError("max_age_days must not be negative")
    required_market = {"instrument", "datetime"}
    if missing := sorted(required_market - set(market.columns)):
        raise ValueError(f"market frame is missing columns: {', '.join(missing)}")
    if missing := sorted(set(BLOCK_TRADE_EVENT_COLUMNS) - set(events.columns)):
        raise ValueError(f"block-trade events are missing columns: {', '.join(missing)}")
    result = market.reset_index(drop=True).copy()
    calendar = pd.DatetimeIndex(sorted(pd.to_datetime(result["datetime"]).dropna().unique()))
    source_events = events.loc[:, list(BLOCK_TRADE_EVENT_COLUMNS)].copy()
    source_events["block_trade_effective_date"] = pd.to_datetime(source_events["trade_date"])
    source_events = source_events.loc[source_events["block_trade_effective_date"].isin(calendar)].copy()
    source_events = source_events.sort_values(
        ["instrument", "block_trade_effective_date", "trade_date"], kind="stable"
    ).drop_duplicates(["instrument", "block_trade_effective_date"], keep="last")

    block_columns = [
        "block_trade_trade_date",
        "block_trade_premium_ratio",
        "block_trade_turnover_rate",
        "block_trade_event_count",
        "block_trade_effective_date",
    ]
    daily = result[["instrument", "datetime"]].copy()
    daily["_kind"] = 1
    daily["_row"] = np.arange(len(daily))
    for column in ("block_trade_trade_date", "block_trade_effective_date"):
        daily[column] = pd.NaT
    for column in block_columns[1:-1]:
        daily[column] = np.nan
    event_rows = source_events.rename(
        columns={"block_trade_effective_date": "datetime", "trade_date": "block_trade_trade_date"}
    )[["instrument", "datetime", *[column for column in block_columns if column != "block_trade_effective_date"]]].copy()
    event_rows["block_trade_effective_date"] = event_rows["datetime"]
    event_rows["_kind"] = 0
    event_rows["_row"] = np.nan
    combined = pd.concat([daily, event_rows], ignore_index=True, sort=False)
    combined = combined.sort_values(["instrument", "datetime", "_kind"], kind="stable")
    combined[block_columns] = combined.groupby("instrument", sort=False)[block_columns].ffill()
    attached = combined.loc[combined["_row"].notna(), ["_row", *block_columns]].copy()
    attached["_row"] = attached["_row"].astype(int)
    result = result.join(attached.set_index("_row"), how="left")
    result["block_trade_age_days"] = (
        pd.to_datetime(result["datetime"]) - pd.to_datetime(result["block_trade_effective_date"])
    ).dt.days
    result["block_trade_available"] = result["block_trade_trade_date"].notna() & result[
        "block_trade_age_days"
    ].between(0, max_age_days)
    return result


def attach_margin_financing_events_asof(
    market: pd.DataFrame, events: pd.DataFrame, max_age_days: int = 0
) -> pd.DataFrame:
    """Attach same-close daily financing events for next-session-open decisions.

    A session's financing ledger is treated as a post-close input.  Its rank
    can therefore score the next local open, but not the session's own open.
    The default zero-day age avoids silently carrying a daily flow into later
    sessions; callers may only widen it through an explicit diagnostic option.
    """

    if max_age_days < 0:
        raise ValueError("max_age_days must not be negative")
    required_market = {"instrument", "datetime"}
    if missing := sorted(required_market - set(market.columns)):
        raise ValueError(f"market frame is missing columns: {', '.join(missing)}")
    if missing := sorted(set(MARGIN_FINANCING_EVENT_COLUMNS) - set(events.columns)):
        raise ValueError(f"margin-financing events are missing columns: {', '.join(missing)}")
    result = market.reset_index(drop=True).copy()
    calendar = pd.DatetimeIndex(sorted(pd.to_datetime(result["datetime"]).dropna().unique()))
    source_events = events.loc[:, list(MARGIN_FINANCING_EVENT_COLUMNS)].copy()
    source_events["margin_financing_effective_date"] = pd.to_datetime(source_events["trade_date"])
    source_events = source_events.loc[
        source_events["margin_financing_effective_date"].isin(calendar)
    ].copy()
    source_events = source_events.sort_values(
        ["instrument", "margin_financing_effective_date", "trade_date"], kind="stable"
    ).drop_duplicates(["instrument", "margin_financing_effective_date"], keep="last")
    margin_columns = [
        "margin_financing_trade_date",
        "margin_net_buy_to_market_cap",
        "margin_buy_to_market_cap",
        "margin_balance_to_market_cap",
        "margin_financing_balance_growth",
        "margin_financing_effective_date",
    ]
    daily = result[["instrument", "datetime"]].copy()
    daily["_kind"] = 1
    daily["_row"] = np.arange(len(daily))
    for column in ("margin_financing_trade_date", "margin_financing_effective_date"):
        daily[column] = pd.NaT
    for column in margin_columns[1:-1]:
        daily[column] = np.nan
    event_rows = source_events.rename(
        columns={"margin_financing_effective_date": "datetime", "trade_date": "margin_financing_trade_date"}
    )[["instrument", "datetime", *[column for column in margin_columns if column != "margin_financing_effective_date"]]].copy()
    event_rows["margin_financing_effective_date"] = event_rows["datetime"]
    event_rows["_kind"] = 0
    event_rows["_row"] = np.nan
    combined = pd.concat([daily, event_rows], ignore_index=True, sort=False)
    combined = combined.sort_values(["instrument", "datetime", "_kind"], kind="stable")
    combined[margin_columns] = combined.groupby("instrument", sort=False)[margin_columns].ffill()
    attached = combined.loc[combined["_row"].notna(), ["_row", *margin_columns]].copy()
    attached["_row"] = attached["_row"].astype(int)
    result = result.join(attached.set_index("_row"), how="left")
    result["margin_financing_age_days"] = (
        pd.to_datetime(result["datetime"]) - pd.to_datetime(result["margin_financing_effective_date"])
    ).dt.days
    result["margin_financing_available"] = result["margin_financing_trade_date"].notna() & result[
        "margin_financing_age_days"
    ].between(0, max_age_days)
    return result


def attach_institutional_survey_events_asof(
    market: pd.DataFrame, events: pd.DataFrame, max_age_days: int = 3
) -> pd.DataFrame:
    """Attach dated institutional-survey notices strictly after public notice.

    A survey's received dates can precede its public filing.  Its score-time
    availability is therefore based only on ``announcement_date`` and begins
    on the next local session, never on the survey date itself.
    """

    if max_age_days < 0:
        raise ValueError("max_age_days must not be negative")
    required_market = {"instrument", "datetime"}
    if missing := sorted(required_market - set(market.columns)):
        raise ValueError(f"market frame is missing columns: {', '.join(missing)}")
    if missing := sorted(set(INSTITUTIONAL_SURVEY_EVENT_COLUMNS) - set(events.columns)):
        raise ValueError(f"institutional-survey events are missing columns: {', '.join(missing)}")
    result = market.reset_index(drop=True).copy()
    calendar = pd.DatetimeIndex(sorted(pd.to_datetime(result["datetime"]).dropna().unique()))
    source_events = events.loc[:, list(INSTITUTIONAL_SURVEY_EVENT_COLUMNS)].copy()
    source_events["institutional_survey_effective_date"] = _first_trading_day_after(
        calendar, source_events["announcement_date"]
    )
    source_events = source_events.dropna(subset=["institutional_survey_effective_date"])
    source_events = source_events.sort_values(
        ["instrument", "institutional_survey_effective_date", "announcement_date"], kind="stable"
    ).drop_duplicates(["instrument", "institutional_survey_effective_date"], keep="last")

    survey_columns = [
        "institutional_survey_announcement_date",
        "institutional_survey_org_count",
        "institutional_survey_event_count",
        "institutional_survey_effective_date",
    ]
    daily = result[["instrument", "datetime"]].copy()
    daily["_kind"] = 1
    daily["_row"] = np.arange(len(daily))
    for column in ("institutional_survey_announcement_date", "institutional_survey_effective_date"):
        daily[column] = pd.NaT
    for column in survey_columns[1:-1]:
        daily[column] = np.nan
    event_rows = source_events.rename(
        columns={
            "institutional_survey_effective_date": "datetime",
            "announcement_date": "institutional_survey_announcement_date",
        }
    )[["instrument", "datetime", *[column for column in survey_columns if column != "institutional_survey_effective_date"]]].copy()
    event_rows["institutional_survey_effective_date"] = event_rows["datetime"]
    event_rows["_kind"] = 0
    event_rows["_row"] = np.nan
    combined = pd.concat([daily, event_rows], ignore_index=True, sort=False)
    combined = combined.sort_values(["instrument", "datetime", "_kind"], kind="stable")
    combined[survey_columns] = combined.groupby("instrument", sort=False)[survey_columns].ffill()
    attached = combined.loc[combined["_row"].notna(), ["_row", *survey_columns]].copy()
    attached["_row"] = attached["_row"].astype(int)
    result = result.join(attached.set_index("_row"), how="left")
    result["institutional_survey_age_days"] = (
        pd.to_datetime(result["datetime"]) - pd.to_datetime(result["institutional_survey_effective_date"])
    ).dt.days
    result["institutional_survey_available"] = result["institutional_survey_announcement_date"].notna() & result[
        "institutional_survey_age_days"
    ].between(0, max_age_days)
    return result


def attach_repurchase_plan_events_asof(
    market: pd.DataFrame, events: pd.DataFrame, max_age_days: int = 3
) -> pd.DataFrame:
    """Attach initial repurchase-plan disclosures strictly after DIM_DATE."""

    if max_age_days < 0:
        raise ValueError("max_age_days must not be negative")
    if missing := sorted({"instrument", "datetime"} - set(market.columns)):
        raise ValueError(f"market frame is missing columns: {', '.join(missing)}")
    if missing := sorted(set(REPURCHASE_EVENT_COLUMNS) - set(events.columns)):
        raise ValueError(f"repurchase-plan events are missing columns: {', '.join(missing)}")
    result = market.reset_index(drop=True).copy()
    calendar = pd.DatetimeIndex(sorted(pd.to_datetime(result["datetime"]).dropna().unique()))
    source = events.loc[:, list(REPURCHASE_EVENT_COLUMNS)].copy()
    source["repurchase_effective_date"] = _first_trading_day_after(calendar, source["announcement_date"])
    source = source.dropna(subset=["repurchase_effective_date"]).sort_values(
        ["instrument", "repurchase_effective_date", "announcement_date"], kind="stable"
    ).drop_duplicates(["instrument", "repurchase_effective_date"], keep="last")
    columns = [
        "repurchase_announcement_date", "repurchase_planned_share_ratio", "repurchase_planned_amount",
        "repurchase_effective_date",
    ]
    daily = result[["instrument", "datetime"]].copy()
    daily["_kind"], daily["_row"] = 1, np.arange(len(daily))
    for column in ("repurchase_announcement_date", "repurchase_effective_date"):
        daily[column] = pd.NaT
    for column in columns[1:-1]:
        daily[column] = np.nan
    event_rows = source.rename(columns={"repurchase_effective_date": "datetime", "announcement_date": "repurchase_announcement_date"})[
        ["instrument", "datetime", *[column for column in columns if column != "repurchase_effective_date"]]
    ].copy()
    event_rows["repurchase_effective_date"] = event_rows["datetime"]
    event_rows["_kind"], event_rows["_row"] = 0, np.nan
    combined = pd.concat([daily, event_rows], ignore_index=True, sort=False).sort_values(
        ["instrument", "datetime", "_kind"], kind="stable"
    )
    combined[columns] = combined.groupby("instrument", sort=False)[columns].ffill()
    attached = combined.loc[combined["_row"].notna(), ["_row", *columns]].copy()
    attached["_row"] = attached["_row"].astype(int)
    result = result.join(attached.set_index("_row"), how="left")
    result["repurchase_age_days"] = (
        pd.to_datetime(result["datetime"]) - pd.to_datetime(result["repurchase_effective_date"])
    ).dt.days
    result["repurchase_available"] = result["repurchase_announcement_date"].notna() & result[
        "repurchase_age_days"
    ].between(0, max_age_days)
    return result


def attach_holder_count_events_asof(
    market: pd.DataFrame, events: pd.DataFrame, max_age_days: int = 3
) -> pd.DataFrame:
    """Attach holder-count changes strictly after their published notice date."""

    if max_age_days < 0:
        raise ValueError("max_age_days must not be negative")
    if missing := sorted({"instrument", "datetime"} - set(market.columns)):
        raise ValueError(f"market frame is missing columns: {', '.join(missing)}")
    if missing := sorted(set(HOLDER_COUNT_EVENT_COLUMNS) - set(events.columns)):
        raise ValueError(f"holder-count events are missing columns: {', '.join(missing)}")
    result = market.reset_index(drop=True).copy()
    calendar = pd.DatetimeIndex(sorted(pd.to_datetime(result["datetime"]).dropna().unique()))
    source = events.loc[:, list(HOLDER_COUNT_EVENT_COLUMNS)].copy()
    source["holder_count_effective_date"] = _first_trading_day_after(calendar, source["announcement_date"])
    source = source.dropna(subset=["holder_count_effective_date"]).sort_values(
        ["instrument", "holder_count_effective_date", "announcement_date"], kind="stable"
    ).drop_duplicates(["instrument", "holder_count_effective_date"], keep="last")
    columns = [
        "holder_count_announcement_date", "holder_count_change_ratio", "holder_count_change_absolute",
        "holder_count_effective_date",
    ]
    daily = result[["instrument", "datetime"]].copy()
    daily["_kind"], daily["_row"] = 1, np.arange(len(daily))
    for column in ("holder_count_announcement_date", "holder_count_effective_date"):
        daily[column] = pd.NaT
    for column in columns[1:-1]:
        daily[column] = np.nan
    event_rows = source.rename(columns={"holder_count_effective_date": "datetime", "announcement_date": "holder_count_announcement_date"})[
        ["instrument", "datetime", *[column for column in columns if column != "holder_count_effective_date"]]
    ].copy()
    event_rows["holder_count_effective_date"] = event_rows["datetime"]
    event_rows["_kind"], event_rows["_row"] = 0, np.nan
    combined = pd.concat([daily, event_rows], ignore_index=True, sort=False).sort_values(
        ["instrument", "datetime", "_kind"], kind="stable"
    )
    combined[columns] = combined.groupby("instrument", sort=False)[columns].ffill()
    attached = combined.loc[combined["_row"].notna(), ["_row", *columns]].copy()
    attached["_row"] = attached["_row"].astype(int)
    result = result.join(attached.set_index("_row"), how="left")
    result["holder_count_age_days"] = (
        pd.to_datetime(result["datetime"]) - pd.to_datetime(result["holder_count_effective_date"])
    ).dt.days
    result["holder_count_available"] = result["holder_count_announcement_date"].notna() & result[
        "holder_count_age_days"
    ].between(0, max_age_days)
    return result


def attach_pledge_events_asof(
    market: pd.DataFrame, events: pd.DataFrame, max_age_days: int = 3
) -> pd.DataFrame:
    """Attach share-pledge notices strictly after their published notice date."""

    if max_age_days < 0:
        raise ValueError("max_age_days must not be negative")
    if missing := sorted({"instrument", "datetime"} - set(market.columns)):
        raise ValueError(f"market frame is missing columns: {', '.join(missing)}")
    if missing := sorted(set(PLEDGE_EVENT_COLUMNS) - set(events.columns)):
        raise ValueError(f"pledge events are missing columns: {', '.join(missing)}")
    result = market.reset_index(drop=True).copy()
    calendar = pd.DatetimeIndex(sorted(pd.to_datetime(result["datetime"]).dropna().unique()))
    source = events.loc[:, list(PLEDGE_EVENT_COLUMNS)].copy()
    source["pledge_effective_date"] = _first_trading_day_after(calendar, source["announcement_date"])
    source = source.dropna(subset=["pledge_effective_date"]).sort_values(
        ["instrument", "pledge_effective_date", "announcement_date"], kind="stable"
    ).drop_duplicates(["instrument", "pledge_effective_date"], keep="last")
    columns = [
        "pledge_announcement_date", "pledge_share_count", "pledge_total_share_ratio", "pledge_event_count",
        "pledge_effective_date",
    ]
    daily = result[["instrument", "datetime"]].copy()
    daily["_kind"], daily["_row"] = 1, np.arange(len(daily))
    for column in ("pledge_announcement_date", "pledge_effective_date"):
        daily[column] = pd.NaT
    for column in columns[1:-1]:
        daily[column] = np.nan
    event_rows = source.rename(columns={"pledge_effective_date": "datetime", "announcement_date": "pledge_announcement_date"})[
        ["instrument", "datetime", *[column for column in columns if column != "pledge_effective_date"]]
    ].copy()
    event_rows["pledge_effective_date"] = event_rows["datetime"]
    event_rows["_kind"], event_rows["_row"] = 0, np.nan
    combined = pd.concat([daily, event_rows], ignore_index=True, sort=False).sort_values(
        ["instrument", "datetime", "_kind"], kind="stable"
    )
    combined[columns] = combined.groupby("instrument", sort=False)[columns].ffill()
    attached = combined.loc[combined["_row"].notna(), ["_row", *columns]].copy()
    attached["_row"] = attached["_row"].astype(int)
    result = result.join(attached.set_index("_row"), how="left")
    result["pledge_age_days"] = (
        pd.to_datetime(result["datetime"]) - pd.to_datetime(result["pledge_effective_date"])
    ).dt.days
    result["pledge_available"] = result["pledge_announcement_date"].notna() & result[
        "pledge_age_days"
    ].between(0, max_age_days)
    return result


def attach_dividend_plan_events_asof(
    market: pd.DataFrame, events: pd.DataFrame, max_age_days: int = 3
) -> pd.DataFrame:
    """Attach initial dividend-plan notices strictly after their notice date."""

    if max_age_days < 0:
        raise ValueError("max_age_days must not be negative")
    if missing := sorted({"instrument", "datetime"} - set(market.columns)):
        raise ValueError(f"market frame is missing columns: {', '.join(missing)}")
    if missing := sorted(set(DIVIDEND_PLAN_EVENT_COLUMNS) - set(events.columns)):
        raise ValueError(f"dividend-plan events are missing columns: {', '.join(missing)}")
    result = market.reset_index(drop=True).copy()
    calendar = pd.DatetimeIndex(sorted(pd.to_datetime(result["datetime"]).dropna().unique()))
    source = events.loc[:, list(DIVIDEND_PLAN_EVENT_COLUMNS)].copy()
    source["dividend_plan_effective_date"] = _first_trading_day_after(calendar, source["announcement_date"])
    source = source.dropna(subset=["dividend_plan_effective_date"]).sort_values(
        ["instrument", "dividend_plan_effective_date", "announcement_date"], kind="stable"
    ).drop_duplicates(["instrument", "dividend_plan_effective_date"], keep="last")
    columns = [
        "dividend_plan_announcement_date", "dividend_cash_per_ten", "dividend_share_ratio",
        "dividend_plan_event_count", "dividend_plan_effective_date",
    ]
    daily = result[["instrument", "datetime"]].copy()
    daily["_kind"], daily["_row"] = 1, np.arange(len(daily))
    for column in ("dividend_plan_announcement_date", "dividend_plan_effective_date"):
        daily[column] = pd.NaT
    for column in columns[1:-1]:
        daily[column] = np.nan
    event_rows = source.rename(
        columns={"dividend_plan_effective_date": "datetime", "announcement_date": "dividend_plan_announcement_date"}
    )[["instrument", "datetime", *[column for column in columns if column != "dividend_plan_effective_date"]]].copy()
    event_rows["dividend_plan_effective_date"] = event_rows["datetime"]
    event_rows["_kind"], event_rows["_row"] = 0, np.nan
    combined = pd.concat([daily, event_rows], ignore_index=True, sort=False).sort_values(
        ["instrument", "datetime", "_kind"], kind="stable"
    )
    combined[columns] = combined.groupby("instrument", sort=False)[columns].ffill()
    attached = combined.loc[combined["_row"].notna(), ["_row", *columns]].copy()
    attached["_row"] = attached["_row"].astype(int)
    result = result.join(attached.set_index("_row"), how="left")
    result["dividend_plan_age_days"] = (
        pd.to_datetime(result["datetime"]) - pd.to_datetime(result["dividend_plan_effective_date"])
    ).dt.days
    result["dividend_plan_available"] = result["dividend_plan_announcement_date"].notna() & result[
        "dividend_plan_age_days"
    ].between(0, max_age_days)
    return result


def require_research_price_basis(provider_uri: Path) -> dict[str, Any]:
    """Require a passed, point-in-time price-basis manifest before research."""

    manifest_path = provider_uri.expanduser().resolve() / PRICE_BASIS_MANIFEST_NAME
    if not manifest_path.exists():
        raise RuntimeError(
            "research is blocked because the Qlib provider has no price-basis acceptance manifest; "
            "run a full `a_share_data_pipeline.py sync --force-full --adjust point_in_time` refresh"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "passed" or manifest.get("price_basis") != REQUIRED_PRICE_BASIS:
        raise RuntimeError(
            "research is blocked because the Qlib provider price basis has not passed acceptance: "
            f"status={manifest.get('status')!r}, price_basis={manifest.get('price_basis')!r}"
        )
    if manifest.get("failures"):
        raise RuntimeError("research is blocked because the price-basis manifest contains failures")
    return manifest


def uses_required_price_basis(record: dict[str, Any]) -> bool:
    """Return whether an immutable research record names the accepted basis."""

    return (record.get("data") or {}).get("price_basis") == REQUIRED_PRICE_BASIS


def require_record_price_basis(record: dict[str, Any], *, record_kind: str) -> None:
    """Prevent legacy qfq/raw-VWAP evidence from becoming executable again."""

    observed = (record.get("data") or {}).get("price_basis")
    if observed != REQUIRED_PRICE_BASIS:
        raise ValueError(
            f"{record_kind} is invalid under the research price-basis contract: "
            f"expected {REQUIRED_PRICE_BASIS!r}, got {observed!r}"
        )


def research_price_basis_metadata(provider_uri: Path) -> dict[str, Any]:
    """Fingerprint the accepted provider basis into every new research record."""

    provider_uri = provider_uri.expanduser().resolve()
    manifest = require_research_price_basis(provider_uri)
    manifest_path = provider_uri / PRICE_BASIS_MANIFEST_NAME
    return {
        "price_basis": manifest["price_basis"],
        "price_basis_manifest": str(manifest_path),
        "price_basis_manifest_sha256": file_sha256(manifest_path),
        "future_corporate_actions_used": bool(manifest.get("future_corporate_actions_used", False)),
    }


def require_diagnostic_price_basis(diagnostic: dict[str, Any]) -> None:
    """Reject historical diagnostics created before the price-basis contract."""

    observed = (diagnostic.get("data") or {}).get("price_basis")
    if observed != REQUIRED_PRICE_BASIS:
        raise ValueError(
            "factor diagnostic is invalid under the research price-basis contract: "
            f"expected {REQUIRED_PRICE_BASIS!r}, got {observed!r}"
        )


def load_market_data(
    provider_uri: Path,
    start: str,
    end: str | None,
    batch_size: int,
    max_sessions_per_instrument: int | None = None,
) -> pd.DataFrame:
    """Load the local buyable universe and precompute only non-forward factors."""

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    import qlib
    from qlib.data import D

    if batch_size < 1:
        raise ValueError("--batch-size must be positive")
    if max_sessions_per_instrument is not None and max_sessions_per_instrument < 1:
        raise ValueError("max_sessions_per_instrument must be positive when provided")
    provider_uri = provider_uri.expanduser().resolve()
    if not provider_uri.exists():
        raise FileNotFoundError(f"Qlib provider directory does not exist: {provider_uri}")
    require_research_price_basis(provider_uri)
    qlib.init(provider_uri=str(provider_uri), region="cn", kernels=1)
    market = D.instruments(market="buyable_main_chinext")
    instruments = D.list_instruments(market, start_time=start, end_time=end, as_list=True)
    if not instruments:
        raise RuntimeError("buyable_main_chinext has no local instruments in the requested window")
    fields = {
        "close": "$close",
        "open": "$open",
        "momentum_1": "$close/Ref($close, 1) - 1",
        "momentum_2": "$close/Ref($close, 2) - 1",
        "momentum_3": "$close/Ref($close, 3) - 1",
        "momentum_5": "$close/Ref($close, 5) - 1",
        # The fraction of positive close-to-close sessions is a path-quality
        # measure, not a magnitude measure like five-day momentum.  It is
        # formed at the signal close and is available before next-open entry.
        "up_day_ratio_5": complete_rolling_window_expression(
            "Mean($close>Ref($close, 1), 5)", 5
        ),
        "momentum_10": "$close/Ref($close, 10) - 1",
        "momentum_20": "$close/Ref($close, 20) - 1",
        "momentum_60": "$close/Ref($close, 60) - 1",
        "trend_ma_5": complete_rolling_window_expression("$close/Mean($close, 5) - 1", 4),
        "trend_ma_20": complete_rolling_window_expression("$close/Mean($close, 20) - 1", 19),
        "trend_ma_60": complete_rolling_window_expression("$close/Mean($close, 60) - 1", 59),
        "volume_surge_1": complete_rolling_window_expression("$volume/Mean($volume, 20) - 1", 19),
        "volume_surge": complete_rolling_window_expression(
            "Mean($volume, 5)/Mean($volume, 20) - 1", 19
        ),
        "volume_surge_3": complete_rolling_window_expression(
            "Mean($volume, 3)/Mean($volume, 10) - 1", 9
        ),
        "turnover_surge": complete_rolling_window_expression(
            "Mean($turnover, 5)/Mean($turnover, 20) - 1", 19
        ),
        "turnover_surge_3": complete_rolling_window_expression(
            "Mean($turnover, 3)/Mean($turnover, 10) - 1", 9
        ),
        "turnover_surge_1": complete_rolling_window_expression(
            "$turnover/Mean($turnover, 20) - 1", 19
        ),
        "liquidity_5": complete_rolling_window_expression("Mean($turnover, 5)", 4),
        # Eastmoney's daily amount is in RMB and turnover is a percentage of
        # free float.  Their ratio differs from free-float market value only
        # by the common 100x percentage conversion, which does not affect a
        # same-day cross-sectional rank.  Both inputs are known at the close.
        "free_float_cap_proxy": "$amount/$turnover",
        "volatility_5": complete_rolling_window_expression(
            "Std($close/Ref($close, 1) - 1, 5)", 5
        ),
        "volatility_10": complete_rolling_window_expression(
            "Std($close/Ref($close, 1) - 1, 10)", 10
        ),
        "volatility_20": complete_rolling_window_expression(
            "Std($close/Ref($close, 1) - 1, 20)", 20
        ),
        "amplitude_1": "$high/$low - 1",
        "amplitude_5": complete_rolling_window_expression("Mean($high/$low - 1, 5)", 4),
        "gap_1": "$open/Ref($close, 1) - 1",
        "near_high_10": complete_rolling_window_expression("$close/Max($high, 10) - 1", 9),
        "near_high_20": complete_rolling_window_expression("$close/Max($high, 20) - 1", 19),
        "intraday_strength": "$close/$open - 1",
        "close_to_high": "$close/$high",
        # Same-session close relative to the day's transaction-weighted
        # average price.  A positive value is predeclared as late-session
        # demand persistence; it is distinct from the OHLC-only close-to-high
        # location and remains fully known at the signal close.
        "close_above_vwap_1": "$close/$vwap - 1",
        # Signed ten-session path efficiency.  The numerator is the net
        # close-to-close move and the denominator is the total absolute path
        # length.  A high value is a smooth upward path rather than merely a
        # large endpoint return; the ten-session, positive direction is fixed
        # before its isolated development diagnostic is run.
        "signed_efficiency_ratio_10": SIGNED_EFFICIENCY_RATIO_10_EXPRESSION,
        # Ten-session price-participation confirmation.  A high correlation
        # means turnover tends to be higher on positive-return sessions and
        # lower on negative-return sessions.  This interaction is distinct
        # from the turnover-level and turnover-surge factors already tested.
        "return_turnover_correlation_10": RETURN_TURNOVER_CORRELATION_10_EXPRESSION,
        # Maximum close-to-close return over the last twenty sessions.  The
        # diagnostic direction is added after the cross-sectional rank so a
        # high score means low MAX, matching the predeclared lottery-demand
        # hypothesis while keeping the raw measurement auditable.
        "max_return_20": MAX_RETURN_20_EXPRESSION,
        # Five-day close-location value weighted by each session's volume.
        # The sign is positive when volume repeatedly trades on bars that
        # finish nearer their high than their low.  This is a close-known
        # daily proxy for accumulation, not a substitute for licensed order
        # flow or Level-2 data.
        "signed_volume_pressure_5": complete_rolling_window_expression(
            "Sum($volume*(2*$close-$high-$low)/($high-$low), 5)/Sum($volume, 5)", 4
        ),
    }
    frames: list[pd.DataFrame] = []
    expressions = list(fields.values())
    for offset in range(0, len(instruments), batch_size):
        batch = instruments[offset : offset + batch_size]
        frame = D.features(batch, expressions, start_time=start, end_time=end, freq="day")
        frame = frame.rename(columns={expression: name for name, expression in fields.items()}).reset_index()
        if max_sessions_per_instrument is not None:
            frame = (
                frame.sort_values(["instrument", "datetime"], kind="stable")
                .groupby("instrument", sort=False, group_keys=False)
                .head(max_sessions_per_instrument)
            )
        frames.append(frame)
        print(f"loaded {min(offset + len(batch), len(instruments))}/{len(instruments)} instruments")
    result = pd.concat(frames, ignore_index=True)
    result["datetime"] = pd.to_datetime(result["datetime"])
    result["instrument"] = result["instrument"].astype(str)
    return result.sort_values(["datetime", "instrument"], kind="stable").reset_index(drop=True)


def market_state_frame(frame: pd.DataFrame, eligible: pd.Series) -> pd.DataFrame:
    """Aggregate close-known market state and build strictly trailing risk thresholds."""

    required = {
        "datetime",
        "momentum_1",
        "momentum_5",
        "momentum_20",
        "volatility_20",
        "trend_ma_20",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"market state frame is missing columns: {', '.join(missing)}")
    state = (
        frame.loc[eligible.fillna(False)]
        .groupby("datetime", sort=False)
        .agg(
            market_breadth_5=("momentum_5", "mean"),
            market_breadth_20=("momentum_20", "mean"),
            market_volatility_20=("volatility_20", "median"),
            market_return_dispersion_1=("momentum_1", "std"),
            market_above_ma20_fraction=("trend_ma_20", lambda values: values.gt(0.0).mean()),
        )
        .sort_index()
    )
    # A state at today's close can use today's realized market measures.  Its
    # reference distribution, however, is fixed before the close: shift first,
    # then calculate each rolling quantile.
    state["market_volatility_20_trailing_p75"] = (
        state["market_volatility_20"].shift(1).rolling(252, min_periods=60).quantile(0.75)
    )
    state["market_volatility_20_trailing_p50"] = (
        state["market_volatility_20"].shift(1).rolling(252, min_periods=60).quantile(0.50)
    )
    state["market_return_dispersion_1_trailing_p75"] = (
        state["market_return_dispersion_1"].shift(1).rolling(252, min_periods=60).quantile(0.75)
    )
    return state


def summarize_rolling_window_semantics(
    frame: pd.DataFrame,
    requirements: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Detect rolling fields populated before their declared history exists.

    This is a pure input-semantics audit.  It uses only the instrument/date
    order, same-day close availability, and already computed close-known
    fields; it never loads or derives a forward return.
    """

    requirements = dict(requirements or ROLLING_FACTOR_PRIOR_CLOSE_REQUIREMENTS)
    required = {"instrument", "datetime", "close", *requirements}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError("rolling-window semantics frame is missing columns: " + ", ".join(missing))
    invalid_requirements = sorted(name for name, prior in requirements.items() if int(prior) < 0)
    if invalid_requirements:
        raise ValueError("rolling-window prior-session requirements must be non-negative")

    source = frame.sort_values(["instrument", "datetime"], kind="stable").reset_index(drop=True)
    session_number = source.groupby("instrument", sort=False).cumcount() + 1
    current_close_available = pd.to_numeric(source["close"], errors="coerce").gt(0.0)
    decisions: list[dict[str, Any]] = []
    for factor, prior_sessions in requirements.items():
        prior_sessions = int(prior_sessions)
        values = pd.to_numeric(source[factor], errors="coerce")
        finite = values.notna() & np.isfinite(values)
        early = current_close_available & session_number.le(prior_sessions)
        violations = early & finite
        valid_current = current_close_available & finite
        example_rows = source.loc[violations, ["instrument", "datetime"]].head(5)
        decisions.append(
            {
                "factor": factor,
                "required_prior_sessions": prior_sessions,
                "expected_first_valid_session_number": prior_sessions + 1,
                "first_observed_valid_session_number": (
                    int(session_number.loc[valid_current].min()) if valid_current.any() else None
                ),
                "early_non_missing_rows": int(violations.sum()),
                "instruments_with_early_values": int(source.loc[violations, "instrument"].nunique()),
                "passed": not bool(violations.any()),
                "examples": [
                    {
                        "instrument": str(row.instrument),
                        "datetime": pd.Timestamp(row.datetime),
                        "session_number": int(session_number.loc[row.Index]),
                        "value": float(values.loc[row.Index]),
                    }
                    for row in example_rows.itertuples()
                ],
            }
        )
    failed = [item["factor"] for item in decisions if not item["passed"]]
    return {
        "passed": not failed,
        "factor_count": len(decisions),
        "failed_factor_count": len(failed),
        "failed_factors": failed,
        "factor_decisions": decisions,
        "forward_return_fields_read": False,
    }


def rank_factor_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Turn raw factors into daily comparable [0, 1] scores without look-ahead."""

    result = frame.copy()
    raw_columns = [
        "momentum_1",
        "momentum_2",
        "momentum_3",
        "momentum_5",
        "up_day_ratio_5",
        "momentum_10",
        "momentum_20",
        "momentum_60",
        "trend_ma_5",
        "trend_ma_20",
        "trend_ma_60",
        "volume_surge_1",
        "volume_surge",
        "volume_surge_3",
        "turnover_surge",
        "turnover_surge_3",
        "turnover_surge_1",
        "liquidity_5",
        "free_float_cap_proxy",
        "volatility_5",
        "volatility_10",
        "volatility_20",
        "amplitude_1",
        "amplitude_5",
        "gap_1",
        "near_high_10",
        "near_high_20",
        "intraday_strength",
        "close_to_high",
        "close_above_vwap_1",
        "signed_efficiency_ratio_10",
        "return_turnover_correlation_10",
        "max_return_20",
        "signed_volume_pressure_5",
        "roe",
        "revenue_yoy",
        "profit_yoy",
        "quality_age_days",
        "roe_change",
        "revenue_yoy_acceleration",
        "profit_yoy_acceleration",
    ]
    forecast_raw_columns = [
        column
        for column in ("forecast_turnaround", "forecast_profit_yoy", "forecast_profit_yoy_width", "forecast_age_days")
        if column in result.columns
    ]
    raw_columns.extend(forecast_raw_columns)
    billboard_raw_columns = [
        column
        for column in (
            "billboard_net_flow_to_float",
            "billboard_net_flow_to_deal",
            "billboard_deal_to_float",
            "billboard_reason_count",
            "billboard_age_days",
        )
        if column in result.columns
    ]
    raw_columns.extend(billboard_raw_columns)
    major_holder_raw_columns = [
        column
        for column in (
            "major_holder_net_change_free_ratio",
            "major_holder_increase_free_ratio",
            "major_holder_decrease_free_ratio",
            "major_holder_event_count",
            "major_holder_age_days",
        )
        if column in result.columns
    ]
    raw_columns.extend(major_holder_raw_columns)
    block_trade_raw_columns = [
        column
        for column in (
            "block_trade_premium_ratio",
            "block_trade_turnover_rate",
            "block_trade_event_count",
            "block_trade_age_days",
        )
        if column in result.columns
    ]
    raw_columns.extend(block_trade_raw_columns)
    margin_financing_raw_columns = [
        column
        for column in (
            "margin_net_buy_to_market_cap",
            "margin_buy_to_market_cap",
            "margin_balance_to_market_cap",
            "margin_financing_balance_growth",
            "margin_financing_age_days",
        )
        if column in result.columns
    ]
    raw_columns.extend(margin_financing_raw_columns)
    institutional_survey_raw_columns = [
        column
        for column in (
            "institutional_survey_org_count",
            "institutional_survey_event_count",
            "institutional_survey_age_days",
        )
        if column in result.columns
    ]
    raw_columns.extend(institutional_survey_raw_columns)
    repurchase_raw_columns = [
        column
        for column in (
            "repurchase_planned_share_ratio",
            "repurchase_planned_amount",
            "repurchase_age_days",
        )
        if column in result.columns
    ]
    raw_columns.extend(repurchase_raw_columns)
    holder_count_raw_columns = [
        column
        for column in (
            "holder_count_change_ratio",
            "holder_count_change_absolute",
            "holder_count_age_days",
        )
        if column in result.columns
    ]
    raw_columns.extend(holder_count_raw_columns)
    pledge_raw_columns = [
        column
        for column in (
            "pledge_share_count",
            "pledge_total_share_ratio",
            "pledge_event_count",
            "pledge_age_days",
        )
        if column in result.columns
    ]
    raw_columns.extend(pledge_raw_columns)
    dividend_plan_raw_columns = [
        column
        for column in (
            "dividend_cash_per_ten",
            "dividend_share_ratio",
            "dividend_plan_event_count",
            "dividend_plan_age_days",
        )
        if column in result.columns
    ]
    raw_columns.extend(dividend_plan_raw_columns)
    for column in raw_columns:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    # A zero or unavailable turnover cannot support a free-float-capitalization
    # proxy.  It must remain missing rather than become an infinite extreme
    # rank that could dominate a factor diagnostic.
    result["free_float_cap_proxy"] = result["free_float_cap_proxy"].where(
        np.isfinite(result["free_float_cap_proxy"])
    )
    # A flat bar has a zero high-low denominator in the source expression.
    # Keep such observations missing rather than letting +/-inf obtain an
    # artificial extreme rank.
    result["signed_volume_pressure_5"] = result["signed_volume_pressure_5"].where(
        np.isfinite(result["signed_volume_pressure_5"])
    )
    result["close_above_vwap_1"] = result["close_above_vwap_1"].where(
        np.isfinite(result["close_above_vwap_1"])
    )
    result["signed_efficiency_ratio_10"] = result["signed_efficiency_ratio_10"].where(
        np.isfinite(result["signed_efficiency_ratio_10"])
    )
    result["return_turnover_correlation_10"] = result["return_turnover_correlation_10"].where(
        np.isfinite(result["return_turnover_correlation_10"])
    )
    result["max_return_20"] = result["max_return_20"].where(np.isfinite(result["max_return_20"]))
    # Event rows are forward-filled only so each row retains the event context
    # for auditing.  Once the explicitly declared event window expires, those
    # raw values must not participate in a cross-sectional rank; otherwise a
    # stale announcement or billboard would silently become a live signal.
    for available_column, event_columns in (
        ("forecast_available", forecast_raw_columns),
        ("billboard_available", billboard_raw_columns),
        ("major_holder_available", major_holder_raw_columns),
        ("block_trade_available", block_trade_raw_columns),
        ("margin_financing_available", margin_financing_raw_columns),
        ("institutional_survey_available", institutional_survey_raw_columns),
        ("repurchase_available", repurchase_raw_columns),
        ("holder_count_available", holder_count_raw_columns),
        ("pledge_available", pledge_raw_columns),
        ("dividend_plan_available", dividend_plan_raw_columns),
    ):
        if available_column in result.columns:
            result.loc[~result[available_column].fillna(False), event_columns] = np.nan
    eligible = result["quality_eligible"].fillna(False)
    result = result.join(market_state_frame(result, eligible), on="datetime")
    # Rank one raw factor at a time.  Building the full rank matrix in one
    # operation is faster on small fixtures, but on the all-market frame it
    # duplicates too much data at once and can exhaust memory/swap before a
    # diagnostic is written.  The incremental path deliberately trades some
    # speed for a bounded peak working set.
    for column in raw_columns:
        ranked = result.loc[eligible].groupby("datetime", sort=False)[column].rank(pct=True)
        result.loc[eligible, f"rank_{column}"] = ranked
    result["reversal_1"] = 1.0 - result["rank_momentum_1"]
    result["reversal_2"] = 1.0 - result["rank_momentum_2"]
    result["reversal_3"] = 1.0 - result["rank_momentum_3"]
    result["reversal_5"] = 1.0 - result["rank_momentum_5"]
    result["up_day_consistency_5"] = result["rank_up_day_ratio_5"]
    result["reversal_10"] = 1.0 - result["rank_momentum_10"]
    result["volume_dry_up"] = 1.0 - result["rank_volume_surge"]
    result["volatility_target_5"] = 1.0 - (result["rank_volatility_5"] - 0.50).abs()
    result["volatility_target"] = 1.0 - (result["rank_volatility_10"] - 0.65).abs()
    result["volatility_target_20"] = 1.0 - (result["rank_volatility_20"] - 0.50).abs()
    result["volatility_low_20"] = 1.0 - result["rank_volatility_20"]
    result["amplitude_low_1"] = 1.0 - result["rank_amplitude_1"]
    result["amplitude_low"] = 1.0 - result["rank_amplitude_5"]
    # Non-compensating aggregation of the only four close-known price-volume
    # directions that passed the fixed cross-year single-factor stability
    # audit.  V9 tested a weighted sum, which permits one weak component to be
    # offset by another; the row-wise minimum requires all four ranks to be
    # jointly strong.  Because the inputs were selected on this development
    # period, this remains a historical sensitivity factor, never promotion
    # evidence by itself.
    result["compression_consensus_min"] = result[
        list(COMPRESSION_CONSENSUS_MIN_COMPONENTS)
    ].min(axis=1, skipna=False)
    result["gap_reversal"] = 1.0 - result["rank_gap_1"]
    result["gap_strength"] = result["rank_gap_1"]
    result["close_pullback"] = 1.0 - result["rank_close_to_high"]
    result["drawdown_20"] = 1.0 - result["rank_near_high_20"]
    result["free_float_cap_small"] = 1.0 - result["rank_free_float_cap_proxy"]
    result["quality_roe"] = result["rank_roe"]
    result["quality_revenue"] = result["rank_revenue_yoy"]
    result["quality_profit"] = result["rank_profit_yoy"]
    result["quality_freshness"] = 1.0 - result["rank_quality_age_days"]
    result["quality_growth"] = result[["rank_revenue_yoy", "rank_profit_yoy"]].mean(axis=1)
    result["quality_score"] = result[["rank_roe", "rank_revenue_yoy", "rank_profit_yoy"]].mean(axis=1)
    result["roe_change"] = result["rank_roe_change"]
    result["revenue_yoy_acceleration"] = result["rank_revenue_yoy_acceleration"]
    result["profit_yoy_acceleration"] = result["rank_profit_yoy_acceleration"]
    if "rank_forecast_profit_yoy" in result.columns:
        result["forecast_profit_yoy"] = result["rank_forecast_profit_yoy"]
    if "rank_forecast_turnaround" in result.columns:
        result["forecast_turnaround"] = result["rank_forecast_turnaround"]
    if "rank_forecast_profit_yoy_width" in result.columns:
        result["forecast_profit_yoy_precision"] = 1.0 - result["rank_forecast_profit_yoy_width"]
    if "rank_forecast_age_days" in result.columns:
        result["forecast_freshness"] = 1.0 - result["rank_forecast_age_days"]
    for column in (
        "billboard_net_flow_to_float",
        "billboard_net_flow_to_deal",
        "billboard_deal_to_float",
        "billboard_reason_count",
    ):
        rank_column = f"rank_{column}"
        if rank_column in result.columns:
            result[column] = result[rank_column]
    if "rank_billboard_age_days" in result.columns:
        result["billboard_freshness"] = 1.0 - result["rank_billboard_age_days"]
    for column in (
        "major_holder_net_change_free_ratio",
        "major_holder_increase_free_ratio",
        "major_holder_decrease_free_ratio",
        "major_holder_event_count",
    ):
        rank_column = f"rank_{column}"
        if rank_column in result.columns:
            result[column] = result[rank_column]
    if "rank_major_holder_age_days" in result.columns:
        result["major_holder_freshness"] = 1.0 - result["rank_major_holder_age_days"]
    for column in (
        "block_trade_premium_ratio",
        "block_trade_turnover_rate",
        "block_trade_event_count",
    ):
        rank_column = f"rank_{column}"
        if rank_column in result.columns:
            result[column] = result[rank_column]
    if "rank_block_trade_age_days" in result.columns:
        result["block_trade_freshness"] = 1.0 - result["rank_block_trade_age_days"]
    for column in MARGIN_FINANCING_FACTOR_DIAGNOSTIC_COLUMNS:
        rank_column = f"rank_{column}"
        if rank_column in result.columns:
            result[column] = result[rank_column]
    for column in ("institutional_survey_org_count", "institutional_survey_event_count"):
        rank_column = f"rank_{column}"
        if rank_column in result.columns:
            result[column] = result[rank_column]
    if "rank_institutional_survey_age_days" in result.columns:
        result["institutional_survey_freshness"] = 1.0 - result["rank_institutional_survey_age_days"]
    for column in ("repurchase_planned_share_ratio", "repurchase_planned_amount"):
        rank_column = f"rank_{column}"
        if rank_column in result.columns:
            result[column] = result[rank_column]
    if "rank_repurchase_age_days" in result.columns:
        result["repurchase_freshness"] = 1.0 - result["rank_repurchase_age_days"]
    for column in ("holder_count_change_ratio", "holder_count_change_absolute"):
        rank_column = f"rank_{column}"
        if rank_column in result.columns:
            result[column] = result[rank_column]
    if "rank_holder_count_age_days" in result.columns:
        result["holder_count_freshness"] = 1.0 - result["rank_holder_count_age_days"]
    for column in ("pledge_share_count", "pledge_total_share_ratio", "pledge_event_count"):
        rank_column = f"rank_{column}"
        if rank_column in result.columns:
            result[column] = result[rank_column]
    if "rank_pledge_age_days" in result.columns:
        result["pledge_freshness"] = 1.0 - result["rank_pledge_age_days"]
    for column in ("dividend_cash_per_ten", "dividend_share_ratio", "dividend_plan_event_count"):
        rank_column = f"rank_{column}"
        if rank_column in result.columns:
            result[column] = result[rank_column]
    if "rank_dividend_plan_age_days" in result.columns:
        result["dividend_plan_freshness"] = 1.0 - result["rank_dividend_plan_age_days"]
    result["momentum_1"] = result["rank_momentum_1"]
    result["momentum_2"] = result["rank_momentum_2"]
    result["momentum_3"] = result["rank_momentum_3"]
    result["momentum_5"] = result["rank_momentum_5"]
    result["momentum_10"] = result["rank_momentum_10"]
    result["momentum_20"] = result["rank_momentum_20"]
    result["momentum_60"] = result["rank_momentum_60"]
    result["trend_ma_5"] = result["rank_trend_ma_5"]
    result["trend_ma_20"] = result["rank_trend_ma_20"]
    result["trend_ma_60"] = result["rank_trend_ma_60"]
    result["volume_surge_1"] = result["rank_volume_surge_1"]
    result["volume_surge"] = result["rank_volume_surge"]
    result["volume_surge_3"] = result["rank_volume_surge_3"]
    result["turnover_surge"] = result["rank_turnover_surge"]
    result["turnover_surge_3"] = result["rank_turnover_surge_3"]
    result["turnover_surge_1"] = result["rank_turnover_surge_1"]
    result["liquidity_5"] = result["rank_liquidity_5"]
    result["near_high_10"] = result["rank_near_high_10"]
    result["near_high_20"] = result["rank_near_high_20"]
    result["intraday_strength"] = result["rank_intraday_strength"]
    result["close_to_high"] = result["rank_close_to_high"]
    result["close_above_vwap_1"] = result["rank_close_above_vwap_1"]
    result["signed_efficiency_ratio_10"] = result["rank_signed_efficiency_ratio_10"]
    result["return_turnover_correlation_10"] = result["rank_return_turnover_correlation_10"]
    result["max_return_20_low"] = 1.0 - result["rank_max_return_20"]
    result["signed_volume_pressure_5"] = result["rank_signed_volume_pressure_5"]
    return result


def add_billboard_holdout_factor(ranked: pd.DataFrame) -> pd.DataFrame:
    """Add the one explicitly post-development billboard holdout direction.

    The direct ``billboard_deal_to_float`` factor was negative in every year
    of the completed development diagnostic.  Reversing it is therefore a
    newly formed hypothesis, not retrospective confirmation.  Keep it out of
    normal candidate libraries and evaluate it only through
    ``billboard-holdout`` on a subsequent untouched period.
    """

    if "billboard_deal_to_float" not in ranked.columns:
        raise ValueError("billboard holdout factor requires billboard_deal_to_float")
    result = ranked.copy()
    result[BILLBOARD_HOLDOUT_FACTOR] = 1.0 - pd.to_numeric(
        result["billboard_deal_to_float"], errors="coerce"
    )
    return result


def add_prospective_vwap_reversal_factor(ranked: pd.DataFrame) -> pd.DataFrame:
    """Add a future-only direction without admitting it to historical diagnostics.

    ``close_below_vwap_1`` was formed only after the completed 2019--2025
    ``close_above_vwap_1`` diagnostic was read.  It therefore remains outside
    ``FACTOR_DIAGNOSTIC_COLUMNS`` and every candidate library.  This helper is
    used exclusively by the separately registered prospective monitor.
    """

    if PROSPECTIVE_VWAP_SOURCE_FACTOR not in ranked.columns:
        raise ValueError(
            f"prospective VWAP reversal requires {PROSPECTIVE_VWAP_SOURCE_FACTOR}"
        )
    result = ranked.copy()
    result[PROSPECTIVE_VWAP_FACTOR] = 1.0 - pd.to_numeric(
        result[PROSPECTIVE_VWAP_SOURCE_FACTOR], errors="coerce"
    )
    return result


def score_candidate(ranked: pd.DataFrame, candidate: Candidate) -> pd.DataFrame:
    """Apply a predeclared factor mix and discard rows with incomplete signals."""

    if not math.isclose(sum(candidate.weights.values()), 1.0, abs_tol=1e-9):
        raise ValueError(f"candidate weights must sum to one: {candidate.name}")
    missing = sorted(set(candidate.weights) - set(ranked.columns))
    if missing:
        raise ValueError(f"candidate {candidate.name} refers to missing factors: {', '.join(missing)}")
    result = ranked.loc[ranked["quality_eligible"].fillna(False)].copy()
    result["score"] = sum(result[column] * weight for column, weight in candidate.weights.items())
    required = ["instrument", "datetime", "open", "close", "score", *candidate.weights]
    return result.dropna(subset=required)


def minimum_required_holdings(topk: int) -> int:
    """Require at least 80% of a declared basket, including baskets below five.

    The previous fixed floor of five made a Top-3 strategy impossible to
    evaluate or settle.  For a three-name execution policy, all three names
    must have valid quotes; larger baskets retain the existing 80% rule.
    """

    if topk < 1:
        raise ValueError("topk must be positive")
    return max(1, math.ceil(topk * 0.8))


def validate_close_loss_cap(close_loss_cap: float | None) -> None:
    """Validate an optional close-confirmed loss cap expressed as a decimal."""

    if close_loss_cap is not None and not 0.0 < float(close_loss_cap) < 1.0:
        raise ValueError("close_loss_cap must be strictly between zero and one when supplied")


def validate_entry_gap_cap(max_entry_gap: float | None) -> None:
    """Validate an optional next-open entry-gap ceiling expressed as a decimal."""

    if max_entry_gap is not None and not 0.0 < float(max_entry_gap) < 1.0:
        raise ValueError("max_entry_gap must be strictly between zero and one when supplied")


def apply_close_loss_cap(trades: pd.DataFrame, quotes: pd.DataFrame, close_loss_cap: float | None) -> pd.DataFrame:
    """Apply an assumed same-close exit after a close-confirmed loss breach.

    The cap is deliberately based on a daily close, not an unobservable
    intraday trigger.  Cash from an early exit remains idle until the cohort's
    scheduled three-day exit, so it cannot be silently reallocated into an
    untested replacement position.
    """

    validate_close_loss_cap(close_loss_cap)
    required_trades = {"instrument", "entry_date", "exit_date", "entry_open", "planned_exit_close"}
    missing_trades = sorted(required_trades - set(trades.columns))
    if missing_trades:
        raise ValueError(f"trades are missing columns for close-loss cap: {', '.join(missing_trades)}")
    required_quotes = {"datetime", "instrument", "close"}
    missing_quotes = sorted(required_quotes - set(quotes.columns))
    if missing_quotes:
        raise ValueError(f"quotes are missing columns for close-loss cap: {', '.join(missing_quotes)}")

    result = trades.reset_index(drop=True).copy()
    result["actual_exit_date"] = result["exit_date"]
    result["actual_exit_close"] = result["planned_exit_close"]
    result["close_loss_cap_triggered"] = False
    if result.empty or close_loss_cap is None:
        return result

    result["_trade_id"] = np.arange(len(result))
    paths = result[["_trade_id", "instrument", "entry_date", "exit_date", "entry_open"]].merge(
        quotes[["datetime", "instrument", "close"]], on="instrument", how="inner", sort=False
    )
    paths = paths.loc[
        paths["datetime"].ge(paths["entry_date"])
        & paths["datetime"].le(paths["exit_date"])
        & paths["entry_open"].gt(0.0)
        & paths["close"].gt(0.0)
    ].copy()
    paths["gross_return_at_close"] = paths["close"] / paths["entry_open"] - 1.0
    breaches = (
        paths.loc[paths["gross_return_at_close"].le(-float(close_loss_cap))]
        .sort_values(["_trade_id", "datetime"], kind="stable")
        .drop_duplicates("_trade_id", keep="first")
        .rename(columns={"datetime": "cap_exit_date", "close": "cap_exit_close"})
    )
    result = result.merge(breaches[["_trade_id", "cap_exit_date", "cap_exit_close"]], on="_trade_id", how="left", sort=False)
    triggered = result["cap_exit_date"].notna()
    result.loc[triggered, "actual_exit_date"] = result.loc[triggered, "cap_exit_date"]
    result.loc[triggered, "actual_exit_close"] = result.loc[triggered, "cap_exit_close"]
    result["close_loss_cap_triggered"] = triggered
    return result.drop(columns=["_trade_id", "cap_exit_date", "cap_exit_close"])


def evaluate_candidate(
    scored: pd.DataFrame,
    candidate: Candidate,
    hold_days: int,
    topk: int,
    open_cost: float,
    close_cost: float,
    development_end: str,
    regime_filter: str = "always",
    close_loss_cap: float | None = None,
    max_pairwise_correlation: float | None = None,
    correlation_lookback: int = DEFAULT_BASKET_CORRELATION_LOOKBACK,
    diversification_candidate_pool: int = DEFAULT_DIVERSIFICATION_CANDIDATE_POOL,
    min_volatility_low_20: float | None = None,
    min_amplitude_low: float | None = None,
    max_entry_gap: float | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run non-overlapping cohorts from close signal to next-open entry.

    A signal is formed after the market close.  The portfolio buys on the next
    session's open and sells on the close after ``hold_days`` sessions.  This
    deliberately avoids using a future price in factor ranking.
    """

    if hold_days < 1 or topk < 1:
        raise ValueError("--hold-days and --topk must both be positive")
    validate_entry_gap_cap(max_entry_gap)
    calendar = pd.DatetimeIndex(sorted(scored["datetime"].unique()))
    if len(calendar) <= hold_days + 1:
        raise ValueError("research window is too short for the requested holding period")
    date_to_position = {date: position for position, date in enumerate(calendar)}
    rebalances = calendar[: -(hold_days + 1) : hold_days]
    base_pool = scored.loc[scored["datetime"].isin(rebalances)].copy()
    base_pool = base_pool.sort_values(["datetime", "score", "instrument"], ascending=[True, False, True], kind="stable")
    minimum_holdings = minimum_required_holdings(topk)
    base_selected = base_pool.groupby("datetime", sort=False).head(topk).copy()
    base_selected["entry_date"] = base_selected["datetime"].map(lambda value: calendar[date_to_position[value] + 1])
    base_selected["exit_date"] = base_selected["datetime"].map(lambda value: calendar[date_to_position[value] + hold_days])
    cohort_index = (
        base_selected.groupby(["datetime", "entry_date", "exit_date"], sort=True)
        .agg(available_holdings=("instrument", "nunique"))
        .reset_index()
        .rename(columns={"datetime": "signal_date"})
    )
    cohort_index = cohort_index.loc[cohort_index["available_holdings"] >= minimum_holdings].copy()

    risk_gate_configured = min_volatility_low_20 is not None or min_amplitude_low is not None
    entry_gap_configured = max_entry_gap is not None
    if max_pairwise_correlation is not None and risk_gate_configured:
        raise ValueError("correlation diversification and selection risk gates must be audited as separate hypotheses")
    if entry_gap_configured and (
        close_loss_cap is not None or max_pairwise_correlation is not None or risk_gate_configured
    ):
        raise ValueError("entry-gap caps must be audited separately from other execution and selection hypotheses")
    regime_pool = apply_regime_filter(base_pool, regime_filter)
    pool = regime_pool
    if risk_gate_configured:
        pool = apply_selection_risk_gates(pool, min_volatility_low_20, min_amplitude_low)
    diversification_status: pd.DataFrame | None = None
    if max_pairwise_correlation is None:
        selected = pool.groupby("datetime", sort=False).head(topk).copy()
    else:
        selected, diversification_status = select_diversified_topk(
            scored,
            hold_days=hold_days,
            topk=topk,
            regime_filter=regime_filter,
            max_pairwise_correlation=max_pairwise_correlation,
            correlation_lookback=correlation_lookback,
            candidate_pool=diversification_candidate_pool,
        )
    selected["entry_date"] = selected["datetime"].map(lambda value: calendar[date_to_position[value] + 1])
    selected["exit_date"] = selected["datetime"].map(lambda value: calendar[date_to_position[value] + hold_days])

    quotes = scored[["datetime", "instrument", "open", "close"]].drop_duplicates(["datetime", "instrument"])
    entry = quotes.rename(columns={"datetime": "entry_date", "open": "entry_open"})[["entry_date", "instrument", "entry_open"]]
    exit_quote = quotes.rename(columns={"datetime": "exit_date", "close": "planned_exit_close"})[
        ["exit_date", "instrument", "planned_exit_close"]
    ]
    trades = selected.merge(entry, on=["entry_date", "instrument"], how="left")
    trades = trades.merge(exit_quote, on=["exit_date", "instrument"], how="left")
    trades = trades.dropna(subset=["entry_open", "planned_exit_close"])
    trades = trades.loc[
        (trades["close"] > 0) & (trades["entry_open"] > 0) & (trades["planned_exit_close"] > 0)
    ].copy()
    trades["entry_gap_return"] = trades["entry_open"] / trades["close"] - 1.0
    entry_gap_status: pd.DataFrame | None = None
    if entry_gap_configured:
        entry_gap_status = (
            trades.groupby("datetime", sort=True)
            .agg(
                entry_gap_holdings=("instrument", "nunique"),
                maximum_entry_gap_return=("entry_gap_return", "max"),
            )
            .reset_index()
            .rename(columns={"datetime": "signal_date"})
        )
        entry_gap_status["entry_gap_basket_formed"] = (
            entry_gap_status["entry_gap_holdings"].ge(minimum_holdings)
            & entry_gap_status["maximum_entry_gap_return"].le(float(max_entry_gap))
        )
        permitted_dates = set(
            entry_gap_status.loc[entry_gap_status["entry_gap_basket_formed"], "signal_date"].unique()
        )
        trades = trades.loc[trades["datetime"].isin(permitted_dates)].copy()
    trades = apply_close_loss_cap(trades, quotes, close_loss_cap)
    trades["gross_return"] = trades["actual_exit_close"] / trades["entry_open"] - 1.0
    trades["net_return"] = (1.0 - open_cost) * (1.0 + trades["gross_return"]) * (1.0 - close_cost) - 1.0
    traded_rounds = (
        trades.groupby(["datetime", "entry_date", "exit_date"], sort=True)
        .agg(
            net_return=("net_return", "mean"),
            gross_return=("gross_return", "mean"),
            holdings=("instrument", "nunique"),
            early_exit_holdings=("close_loss_cap_triggered", "sum"),
        )
        .reset_index()
        .rename(columns={"datetime": "signal_date"})
    )
    rounds = cohort_index.merge(traded_rounds, on=["signal_date", "entry_date", "exit_date"], how="left")
    rounds["market_data_basket_formed"] = rounds["holdings"].ge(minimum_holdings)
    if entry_gap_status is not None:
        rounds = rounds.merge(
            entry_gap_status[["signal_date", "entry_gap_basket_formed"]], on="signal_date", how="left"
        )
        rounds["entry_gap_basket_formed"] = rounds["entry_gap_basket_formed"].fillna(False).astype(bool)
    else:
        rounds["entry_gap_basket_formed"] = True
    active_dates = set(regime_pool["datetime"].unique())
    rounds["regime_active"] = rounds["signal_date"].isin(active_dates)
    if diversification_status is not None:
        formed_dates = set(
            diversification_status.loc[diversification_status["diversification_basket_formed"], "datetime"].unique()
        )
        rounds["diversification_basket_formed"] = rounds["signal_date"].isin(formed_dates)
        rounds["net_return"] = rounds["net_return"].fillna(0.0)
        rounds["gross_return"] = rounds["gross_return"].fillna(0.0)
        rounds["holdings"] = rounds["holdings"].fillna(0).astype(int)
        rounds["early_exit_holdings"] = rounds["early_exit_holdings"].fillna(0).astype(int)
        rounds["risk_gate_basket_formed"] = True
    elif entry_gap_configured:
        rounds["net_return"] = rounds["net_return"].fillna(0.0)
        rounds["gross_return"] = rounds["gross_return"].fillna(0.0)
        rounds["holdings"] = rounds["holdings"].fillna(0).astype(int)
        rounds["early_exit_holdings"] = rounds["early_exit_holdings"].fillna(0).astype(int)
        incomplete = ~rounds["entry_gap_basket_formed"]
        rounds.loc[incomplete, ["net_return", "gross_return"]] = 0.0
        rounds.loc[incomplete, ["holdings", "early_exit_holdings"]] = 0
        rounds["diversification_basket_formed"] = True
        rounds["risk_gate_basket_formed"] = True
    elif risk_gate_configured:
        rounds["risk_gate_basket_formed"] = rounds["holdings"].ge(minimum_holdings)
        rounds["net_return"] = rounds["net_return"].fillna(0.0)
        rounds["gross_return"] = rounds["gross_return"].fillna(0.0)
        rounds["holdings"] = rounds["holdings"].fillna(0).astype(int)
        rounds["early_exit_holdings"] = rounds["early_exit_holdings"].fillna(0).astype(int)
        incomplete = ~rounds["risk_gate_basket_formed"]
        rounds.loc[incomplete, ["net_return", "gross_return"]] = 0.0
        rounds.loc[incomplete, ["holdings", "early_exit_holdings"]] = 0
        rounds["diversification_basket_formed"] = True
    elif regime_filter == "always":
        # A signal that cannot form a complete basket because a future open or
        # exit close is unavailable must remain on the calendar as cash.  The
        # old behavior dropped the entire cohort, making it incomparable with
        # execution-gate audits that already kept such cohorts as cash.
        rounds["net_return"] = rounds["net_return"].fillna(0.0)
        rounds["gross_return"] = rounds["gross_return"].fillna(0.0)
        rounds["holdings"] = rounds["holdings"].fillna(0).astype(int)
        rounds["early_exit_holdings"] = rounds["early_exit_holdings"].fillna(0).astype(int)
        incomplete = ~rounds["market_data_basket_formed"]
        rounds.loc[incomplete, ["net_return", "gross_return"]] = 0.0
        rounds.loc[incomplete, ["holdings", "early_exit_holdings"]] = 0
        rounds["diversification_basket_formed"] = True
        rounds["risk_gate_basket_formed"] = True
    else:
        active_but_untradable = rounds["regime_active"] & ~rounds["holdings"].ge(minimum_holdings)
        rounds = rounds.loc[~active_but_untradable].copy()
        rounds["net_return"] = rounds["net_return"].fillna(0.0)
        rounds["gross_return"] = rounds["gross_return"].fillna(0.0)
        rounds["holdings"] = rounds["holdings"].fillna(0).astype(int)
        rounds["early_exit_holdings"] = rounds["early_exit_holdings"].fillna(0).astype(int)
        rounds["diversification_basket_formed"] = True
        rounds["risk_gate_basket_formed"] = True
    rounds["segment"] = np.where(rounds["signal_date"] <= pd.Timestamp(development_end), "development", "test")
    development_rounds = rounds.loc[rounds["segment"] == "development"]
    development_by_year = {
        str(year): return_metrics(group, hold_days)
        for year, group in development_rounds.groupby(development_rounds["signal_date"].dt.year, sort=True)
    }
    summary = {
        "candidate": candidate.name,
        "description": candidate.description,
        "weights": candidate.weights,
        "regime_filter": regime_filter,
        "close_loss_cap": close_loss_cap,
        "max_pairwise_correlation": max_pairwise_correlation,
        "correlation_lookback": correlation_lookback if max_pairwise_correlation is not None else None,
        "diversification_candidate_pool": diversification_candidate_pool if max_pairwise_correlation is not None else None,
        "min_volatility_low_20": min_volatility_low_20,
        "min_amplitude_low": min_amplitude_low,
        "max_entry_gap": max_entry_gap,
        "development": return_metrics(development_rounds, hold_days),
        "development_by_signal_year": development_by_year,
        "test": return_metrics(rounds.loc[rounds["segment"] == "test"], hold_days),
        "metrics_by_signal_year": {
            str(year): return_metrics(group, hold_days)
            for year, group in rounds.groupby(rounds["signal_date"].dt.year, sort=True)
        },
        "cohorts": [
            {
                "signal_date": row.signal_date.date().isoformat(),
                "entry_date": row.entry_date.date().isoformat(),
                "exit_date": row.exit_date.date().isoformat(),
                "segment": row.segment,
                "gross_return": float(row.gross_return),
                "net_return": float(row.net_return),
                "holdings": int(row.holdings),
                "early_exit_holdings": int(row.early_exit_holdings),
                "market_data_basket_formed": bool(row.market_data_basket_formed),
                "diversification_basket_formed": bool(row.diversification_basket_formed),
                "risk_gate_basket_formed": bool(row.risk_gate_basket_formed),
                "entry_gap_basket_formed": bool(row.entry_gap_basket_formed),
                "regime_active": bool(row.regime_active),
            }
            for row in rounds.itertuples(index=False)
        ],
    }
    development = summary["development"]
    # Precommitted selection functions.  The test metrics are deliberately not
    # referenced here: they remain an untouched check on the winner.
    pooled_score = (
        development["annualized_return"] - 0.5 * abs(development["max_drawdown"])
        if development["rounds"]
        else None
    )
    year_returns = [
        float(metrics["net_cumulative_return"])
        for metrics in development_by_year.values()
        if metrics.get("net_cumulative_return") is not None
    ]
    stability_score = positive_year_stability_score(year_returns, development.get("max_drawdown"))
    strict_stability_score = stability_score_with_drawdown_cap(
        stability_score,
        development.get("max_drawdown"),
    )
    summary["development_stability"] = {
        "calendar_year_count": len(year_returns),
        "positive_calendar_year_count": sum(value > 0.0 for value in year_returns),
        "worst_calendar_year_net_cumulative_return": min(year_returns) if year_returns else None,
        "selection_score": stability_score,
        "max_drawdown_cap": STRICT_DEVELOPMENT_MAX_DRAWDOWN,
        "passes_max_drawdown_cap": strict_stability_score is not None,
    }
    summary["selection_scores"] = {
        "pooled_return_drawdown": pooled_score,
        "positive_year_stability": stability_score,
        "positive_year_stability_mdd20": strict_stability_score,
    }
    # Backward-compatible shorthand for the original policy.
    summary["development_selection_score"] = pooled_score
    return rounds, summary


def selected_baskets_by_signal(
    scored: pd.DataFrame,
    hold_days: int,
    topk: int,
    regime_filter: str,
) -> dict[str, set[str]]:
    """Return close-known TopK baskets on each active non-overlapping signal date."""

    if hold_days < 1 or topk < 1:
        raise ValueError("--hold-days and --topk must both be positive")
    calendar = pd.DatetimeIndex(sorted(scored["datetime"].unique()))
    if len(calendar) <= hold_days + 1:
        raise ValueError("research window is too short for the requested holding period")
    rebalances = calendar[: -(hold_days + 1) : hold_days]
    pool = scored.loc[scored["datetime"].isin(rebalances)].copy()
    pool = pool.sort_values(["datetime", "score", "instrument"], ascending=[True, False, True], kind="stable")
    pool = apply_regime_filter(pool, regime_filter)
    selected = pool.groupby("datetime", sort=False).head(topk)
    baskets: dict[str, set[str]] = {}
    for date, group in selected.groupby("datetime", sort=True):
        instruments = set(group["instrument"].astype(str))
        if len(instruments) == topk:
            baskets[pd.Timestamp(date).date().isoformat()] = instruments
    return baskets


def selected_basket_trade_details(
    scored: pd.DataFrame,
    baskets: dict[str, set[str]],
    hold_days: int,
    open_cost: float,
    close_cost: float,
) -> pd.DataFrame:
    """Reconstruct selected baskets, their next-open gaps, and scheduled returns."""

    if hold_days < 1:
        raise ValueError("hold_days must be positive")
    calendar = pd.DatetimeIndex(sorted(scored["datetime"].unique()))
    date_to_position = {date: position for position, date in enumerate(calendar)}
    pieces: list[pd.DataFrame] = []
    for raw_signal_date, instruments in sorted(baskets.items()):
        signal_date = pd.Timestamp(raw_signal_date)
        if signal_date not in date_to_position or date_to_position[signal_date] + hold_days >= len(calendar):
            continue
        rows = scored.loc[
            (scored["datetime"] == signal_date) & scored["instrument"].isin(instruments)
        ].copy()
        if len(rows) != len(instruments):
            continue
        rows["entry_date"] = calendar[date_to_position[signal_date] + 1]
        rows["exit_date"] = calendar[date_to_position[signal_date] + hold_days]
        pieces.append(rows)
    if not pieces:
        return pd.DataFrame()
    selected = pd.concat(pieces, ignore_index=True)
    quotes = scored[["datetime", "instrument", "open", "close"]].drop_duplicates(["datetime", "instrument"])
    entry = quotes.rename(columns={"datetime": "entry_date", "open": "entry_open"})[
        ["entry_date", "instrument", "entry_open"]
    ]
    exit_quote = quotes.rename(columns={"datetime": "exit_date", "close": "exit_close"})[
        ["exit_date", "instrument", "exit_close"]
    ]
    details = selected.merge(entry, on=["entry_date", "instrument"], how="left")
    details = details.merge(exit_quote, on=["exit_date", "instrument"], how="left")
    details = details.dropna(subset=["entry_open", "exit_close"])
    details = details.loc[
        (details["close"] > 0.0) & (details["entry_open"] > 0.0) & (details["exit_close"] > 0.0)
    ].copy()
    # This is observable only once the entry session opens.  It is retained
    # separately from the close-known factor ranks for execution attribution.
    details["entry_gap_return"] = details["entry_open"] / details["close"] - 1.0
    details["gross_return"] = details["exit_close"] / details["entry_open"] - 1.0
    details["net_return"] = (1.0 - open_cost) * (1.0 + details["gross_return"]) * (1.0 - close_cost) - 1.0
    return details.sort_values(["datetime", "score", "instrument"], ascending=[True, False, True], kind="stable")


def basket_overlap_metrics(left: dict[str, set[str]], right: dict[str, set[str]]) -> dict[str, float | int | None]:
    """Summarize pairwise TopK overlap only on dates where both baskets exist."""

    common_dates = sorted(set(left) & set(right))
    if not common_dates:
        return {
            "common_signal_dates": 0,
            "mean_jaccard": None,
            "exact_basket_rate": None,
            "any_overlap_rate": None,
        }
    jaccard = [len(left[date] & right[date]) / len(left[date] | right[date]) for date in common_dates]
    return {
        "common_signal_dates": len(common_dates),
        "mean_jaccard": float(np.mean(jaccard)),
        "exact_basket_rate": float(np.mean([left[date] == right[date] for date in common_dates])),
        "any_overlap_rate": float(np.mean([bool(left[date] & right[date]) for date in common_dates])),
    }


def basket_correlation_rows(
    scored: pd.DataFrame, baskets: dict[str, set[str]], lookback_days: int
) -> pd.DataFrame:
    """Measure close-known pairwise return correlation within each selected basket."""

    if lookback_days < 2:
        raise ValueError("correlation lookback_days must be at least two")
    columns = [
        "signal_date",
        "basket_size",
        "valid_return_days",
        "mean_pairwise_correlation",
        "max_pairwise_correlation",
    ]
    if not baskets:
        return pd.DataFrame(columns=columns)
    selected_instruments = sorted(set().union(*baskets.values()))
    prices = (
        scored.loc[scored["instrument"].isin(selected_instruments), ["datetime", "instrument", "close"]]
        .pivot_table(index="datetime", columns="instrument", values="close", aggfunc="last")
        .sort_index()
    )
    returns = prices.pct_change(fill_method=None)
    rows: list[dict[str, Any]] = []
    for raw_signal_date, instruments in sorted(baskets.items()):
        signal_date = pd.Timestamp(raw_signal_date)
        names = sorted(instruments)
        window = returns.reindex(columns=names).loc[:signal_date].tail(lookback_days).dropna(how="any")
        values: np.ndarray = np.array([], dtype=float)
        if len(names) >= 2 and len(window) >= 2:
            matrix = window.corr().to_numpy(dtype=float)
            values = matrix[np.triu_indices_from(matrix, k=1)]
            values = values[np.isfinite(values)]
        rows.append(
            {
                "signal_date": signal_date,
                "basket_size": len(names),
                "valid_return_days": int(len(window)),
                "mean_pairwise_correlation": float(values.mean()) if len(values) else np.nan,
                "max_pairwise_correlation": float(values.max()) if len(values) else np.nan,
            }
        )
    return pd.DataFrame(rows, columns=columns)


def summarize_basket_correlation(rows: pd.DataFrame, rounds: pd.DataFrame, lookback_days: int) -> dict[str, Any]:
    """Summarize concentration and realized cohort returns without selecting on them."""

    if lookback_days < 2:
        raise ValueError("correlation lookback_days must be at least two")
    valid = rows.loc[rows["valid_return_days"].ge(lookback_days)].dropna(
        subset=["mean_pairwise_correlation", "max_pairwise_correlation"]
    ).copy()
    summary: dict[str, Any] = {
        "basket_count": int(len(rows)),
        "valid_correlation_basket_count": int(len(valid)),
        "required_return_days": lookback_days,
        "mean_pairwise_correlation": float(valid["mean_pairwise_correlation"].mean()) if len(valid) else None,
        "median_pairwise_correlation": float(valid["mean_pairwise_correlation"].median()) if len(valid) else None,
        "mean_max_pairwise_correlation": float(valid["max_pairwise_correlation"].mean()) if len(valid) else None,
        "max_pairwise_correlation_p90": float(valid["max_pairwise_correlation"].quantile(0.90)) if len(valid) else None,
        "max_pairwise_correlation_max": float(valid["max_pairwise_correlation"].max()) if len(valid) else None,
    }
    cohort_returns = rounds[["signal_date", "net_return"]].copy()
    joined = valid.merge(cohort_returns, on="signal_date", how="inner")
    summary["max_correlation_to_three_day_return"] = (
        float(joined["max_pairwise_correlation"].corr(joined["net_return"]))
        if len(joined) >= 2
        and joined["max_pairwise_correlation"].std(ddof=0) > 0.0
        and joined["net_return"].std(ddof=0) > 0.0
        else None
    )
    summary["return_by_max_correlation_threshold"] = [
        {
            "threshold": threshold,
            "at_or_above_count": int((joined["max_pairwise_correlation"] >= threshold).sum()),
            "at_or_above_mean_three_day_net_return": float(
                joined.loc[joined["max_pairwise_correlation"] >= threshold, "net_return"].mean()
            )
            if (joined["max_pairwise_correlation"] >= threshold).any()
            else None,
            "below_count": int((joined["max_pairwise_correlation"] < threshold).sum()),
            "below_mean_three_day_net_return": float(
                joined.loc[joined["max_pairwise_correlation"] < threshold, "net_return"].mean()
            )
            if (joined["max_pairwise_correlation"] < threshold).any()
            else None,
        }
        for threshold in CORRELATION_DIAGNOSTIC_THRESHOLDS
    ]
    return summary


def validate_diversification_inputs(max_pairwise_correlation: float, correlation_lookback: int, candidate_pool: int, topk: int) -> None:
    """Validate close-known correlation-constrained basket construction inputs."""

    if not -1.0 <= float(max_pairwise_correlation) <= 1.0:
        raise ValueError("max_pairwise_correlation must be between -1 and 1")
    if correlation_lookback < 2:
        raise ValueError("correlation_lookback must be at least two")
    if candidate_pool < topk:
        raise ValueError("diversification candidate_pool must be at least topk")


def select_diversified_topk(
    scored: pd.DataFrame,
    hold_days: int,
    topk: int,
    regime_filter: str,
    max_pairwise_correlation: float,
    correlation_lookback: int,
    candidate_pool: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Greedily form complete TopK baskets whose close-known pair correlations stay below a cap.

    Each signal first considers only the highest factor-scored ``candidate_pool``
    names.  If it cannot form all ``topk`` names using a complete trailing
    return window, the whole cohort is intentionally left in cash.
    """

    validate_diversification_inputs(max_pairwise_correlation, correlation_lookback, candidate_pool, topk)
    calendar = pd.DatetimeIndex(sorted(scored["datetime"].unique()))
    if len(calendar) <= hold_days + 1:
        raise ValueError("research window is too short for the requested holding period")
    rebalances = calendar[: -(hold_days + 1) : hold_days]
    pool = scored.loc[scored["datetime"].isin(rebalances)].copy()
    pool = pool.sort_values(["datetime", "score", "instrument"], ascending=[True, False, True], kind="stable")
    pool = apply_regime_filter(pool, regime_filter)
    candidate_rows = pool.groupby("datetime", sort=False).head(candidate_pool).copy()
    candidate_instruments = sorted(candidate_rows["instrument"].unique())
    prices = (
        scored.loc[scored["instrument"].isin(candidate_instruments), ["datetime", "instrument", "close"]]
        .pivot_table(index="datetime", columns="instrument", values="close", aggfunc="last")
        .sort_index()
    )
    returns = prices.pct_change(fill_method=None)
    selections: list[pd.DataFrame] = []
    statuses: list[dict[str, Any]] = []
    for signal_date, group in candidate_rows.groupby("datetime", sort=True):
        chosen: list[str] = []
        chosen_rows: list[int] = []
        for row in group.itertuples():
            candidate = str(row.instrument)
            candidate_history = returns.reindex(columns=[candidate]).loc[:signal_date].tail(correlation_lookback).dropna()
            if len(candidate_history) != correlation_lookback:
                continue
            if chosen:
                window = returns.reindex(columns=[*chosen, candidate]).loc[:signal_date].tail(correlation_lookback).dropna(how="any")
                if len(window) != correlation_lookback:
                    continue
                pairwise = window.corr().loc[candidate, chosen].to_numpy(dtype=float)
                if not np.isfinite(pairwise).all() or float(pairwise.max()) > max_pairwise_correlation:
                    continue
            chosen.append(candidate)
            chosen_rows.append(row.Index)
            if len(chosen) == topk:
                break
        formed = len(chosen) == topk
        statuses.append(
            {
                "datetime": signal_date,
                "diversification_basket_formed": formed,
                "diversification_selected_holdings": len(chosen),
                "diversification_candidates_considered": int(len(group)),
            }
        )
        if formed:
            selections.append(candidate_rows.loc[chosen_rows])
    selected = pd.concat(selections, ignore_index=False) if selections else candidate_rows.iloc[0:0].copy()
    return selected, pd.DataFrame(statuses)


def validate_selection_risk_gate(value: float | None, factor_name: str) -> None:
    """Validate an optional cross-sectional rank floor for a selected-stock risk feature."""

    if value is not None and not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{factor_name} gate must be between zero and one")


def apply_selection_risk_gates(
    frame: pd.DataFrame, min_volatility_low_20: float | None, min_amplitude_low: float | None
) -> pd.DataFrame:
    """Keep only names meeting explicitly configured close-known risk-rank floors."""

    validate_selection_risk_gate(min_volatility_low_20, "volatility_low_20")
    validate_selection_risk_gate(min_amplitude_low, "amplitude_low")
    condition = pd.Series(True, index=frame.index)
    if min_volatility_low_20 is not None:
        condition &= frame["volatility_low_20"].ge(float(min_volatility_low_20))
    if min_amplitude_low is not None:
        condition &= frame["amplitude_low"].ge(float(min_amplitude_low))
    return frame.loc[condition.fillna(False)].copy()


def return_metrics(rounds: pd.DataFrame, hold_days: int) -> dict[str, float | int | None]:
    """Calculate net return, risk and drawdown from non-overlapping cohorts."""

    if rounds.empty:
        return {
            "rounds": 0,
            "traded_rounds": 0,
            "traded_round_rate": None,
            "regime_active_rounds": 0,
            "regime_active_rate": None,
            "gross_cumulative_return": None,
            "net_cumulative_return": None,
            "annualized_return": None,
            "annualized_volatility": None,
            "sharpe_like": None,
            "max_drawdown": None,
            "win_rate": None,
            "median_holdings": None,
        }
    net = rounds["net_return"].astype(float)
    gross = rounds["gross_return"].astype(float)
    equity = (1.0 + net).cumprod()
    # Include the starting capital in the high-water mark.  Without this,
    # a loss in the first evaluated cohort would incorrectly report zero
    # drawdown because the first post-trade equity value became its own peak.
    equity_with_initial = pd.concat([pd.Series([1.0]), equity.reset_index(drop=True)], ignore_index=True)
    drawdown = equity_with_initial / equity_with_initial.cummax() - 1.0
    periods_per_year = 252.0 / hold_days
    traded = rounds["holdings"].fillna(0).gt(0) if "holdings" in rounds else net.ne(0.0)
    regime_active = rounds["regime_active"].fillna(False).astype(bool) if "regime_active" in rounds else traded
    annualized_volatility = float(net.std(ddof=0) * math.sqrt(periods_per_year))
    return {
        "rounds": int(len(rounds)),
        "traded_rounds": int(traded.sum()),
        "traded_round_rate": float(traded.mean()),
        "regime_active_rounds": int(regime_active.sum()),
        "regime_active_rate": float(regime_active.mean()),
        "gross_cumulative_return": float((1.0 + gross).prod() - 1.0),
        "net_cumulative_return": float(equity.iloc[-1] - 1.0),
        "annualized_return": float(equity.iloc[-1] ** (periods_per_year / len(rounds)) - 1.0),
        "annualized_volatility": annualized_volatility,
        "sharpe_like": float(net.mean() / net.std(ddof=0) * math.sqrt(periods_per_year)) if net.std(ddof=0) else None,
        "max_drawdown": float(drawdown.min()),
        "win_rate": float((net > 0).mean()),
        "median_holdings": float(rounds["holdings"].median()),
    }


def load_selection_multiplicity_input(study_path: Path) -> SelectionMultiplicityInput:
    """Rebuild a study's development-only candidate-return matrix from immutable records.

    Candidates can have an absent signal date when no executable basket was
    formed.  Such a date is kept distinct from an observed cash cohort: the
    common calendar carries an explicit availability mask and candidate scores
    only consume observations that the original candidate actually recorded.
    Test cohorts are deliberately ignored even though they remain available
    in the per-candidate records for the original initial test; the
    multiplicity audit only asks how fragile the *development* winner was
    among the alternatives that were searched.
    """

    try:
        study = json.loads(study_path.expanduser().read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"study is not valid JSON: {study_path}") from error
    ranking = list(study.get("ranking_by_development") or [])
    if len(ranking) < 2:
        raise ValueError("selection multiplicity audit requires at least two recorded candidates")
    candidates: list[str] = []
    candidate_development: list[tuple[str, pd.DataFrame]] = []
    for item in ranking:
        candidate = str(item.get("candidate") or "")
        destination = Path(str(item.get("path") or "")).expanduser()
        if not candidate or not destination.exists():
            raise ValueError("study ranking must contain an existing per-candidate record path")
        try:
            record = json.loads(destination.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"candidate record is not valid JSON: {destination}") from error
        if str(record.get("candidate")) != candidate:
            raise ValueError(f"candidate record does not match study ranking: {destination}")
        cohorts = pd.DataFrame(record.get("cohorts") or [])
        required = {"signal_date", "segment", "net_return", "holdings"}
        missing = sorted(required - set(cohorts.columns))
        if missing:
            raise ValueError(f"candidate record is missing cohort fields: {', '.join(missing)}")
        development = cohorts.loc[cohorts["segment"].eq("development")].copy()
        development["signal_date"] = pd.to_datetime(development["signal_date"], errors="coerce")
        development["net_return"] = pd.to_numeric(development["net_return"], errors="coerce")
        development["holdings"] = pd.to_numeric(development["holdings"], errors="coerce")
        development = development.sort_values("signal_date", kind="stable")
        if development.empty or development["signal_date"].isna().any() or development["signal_date"].duplicated().any():
            raise ValueError("candidate development cohorts must contain unique valid signal dates")
        if development[["net_return", "holdings"]].isna().any().any() or not np.isfinite(
            development[["net_return", "holdings"]].to_numpy(dtype=float)
        ).all():
            raise ValueError("candidate development cohorts contain non-finite return or holdings values")
        candidates.append(candidate)
        candidate_development.append((candidate, development))
    signal_dates = pd.DatetimeIndex(
        sorted(
            {
                date
                for _, development in candidate_development
                for date in development["signal_date"].tolist()
            }
        )
    )
    if len(signal_dates) < 20:
        raise ValueError("selection multiplicity audit requires at least 20 development cohorts")
    net_returns = np.zeros((len(signal_dates), len(candidates)), dtype=float)
    holdings = np.zeros((len(signal_dates), len(candidates)), dtype=float)
    observed = np.zeros((len(signal_dates), len(candidates)), dtype=bool)
    calendar_positions = {date: position for position, date in enumerate(signal_dates)}
    for column, (_, development) in enumerate(candidate_development):
        positions = [calendar_positions[date] for date in development["signal_date"]]
        net_returns[positions, column] = development["net_return"].to_numpy(dtype=float)
        holdings[positions, column] = development["holdings"].to_numpy(dtype=float)
        observed[positions, column] = True
    return SelectionMultiplicityInput(
        study=study,
        candidates=tuple(candidates),
        signal_dates=signal_dates,
        net_returns=net_returns,
        holdings=holdings,
        observed=observed,
    )


def pooled_return_drawdown_scores(
    net_returns: np.ndarray,
    hold_days: int,
    observed: np.ndarray | None = None,
    *,
    include_initial_equity: bool = True,
) -> np.ndarray:
    """Apply the pooled-return-minus-drawdown selection rule per candidate.

    ``include_initial_equity`` is normally true.  The explicit false option
    exists only to reproduce an immutable legacy study whose saved selection
    scores were calculated before the initial-equity drawdown correction.
    """

    values = np.asarray(net_returns, dtype=float)
    if values.ndim != 2 or not values.shape[0] or not values.shape[1]:
        raise ValueError("net return matrix must have at least one cohort and one candidate")
    availability = np.ones(values.shape, dtype=bool) if observed is None else np.asarray(observed, dtype=bool)
    if availability.shape != values.shape:
        raise ValueError("cohort availability mask must match the net return matrix")
    if hold_days < 1 or not np.isfinite(values[availability]).all() or (values[availability] <= -1.0).any():
        raise ValueError("net return matrix contains invalid values for selection scoring")
    scores = np.full(values.shape[1], -np.inf, dtype=float)
    for column in range(values.shape[1]):
        candidate_returns = values[availability[:, column], column]
        if not len(candidate_returns):
            continue
        equity = np.cumprod(1.0 + candidate_returns)
        equity_for_drawdown = np.concatenate(([1.0], equity)) if include_initial_equity else equity
        drawdown = equity_for_drawdown / np.maximum.accumulate(equity_for_drawdown) - 1.0
        annualized = equity[-1] ** ((252.0 / hold_days) / len(candidate_returns)) - 1.0
        scores[column] = annualized - 0.5 * abs(float(drawdown.min()))
    return scores


def infer_selection_score_drawdown_convention(
    selection_input: SelectionMultiplicityInput, hold_days: int
) -> dict[str, Any]:
    """Pin a saved study to the drawdown convention that produced its stored scores.

    Historical study files before the initial-capital drawdown correction do
    not declare an implementation version.  Comparing every persisted score
    against both conventions is a read-only integrity check; the resulting
    legacy setting reproduces the old selection for this audit only and never
    changes the corrected convention for new research.
    """

    score_by_candidate = {
        str(item.get("candidate")): item.get("development_selection_score")
        for item in list(selection_input.study.get("ranking_by_development") or [])
    }
    expected: list[float] = []
    columns: list[int] = []
    for column, candidate in enumerate(selection_input.candidates):
        value = score_by_candidate.get(candidate)
        try:
            score = float(value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(score):
            expected.append(score)
            columns.append(column)
    if not expected:
        return {
            "drawdown_convention": "initial_equity_high_water",
            "include_initial_equity": True,
            "stored_scores_verified": False,
            "verified_candidate_count": 0,
            "maximum_absolute_score_difference": None,
        }
    stored = np.asarray(expected, dtype=float)
    current_scores = pooled_return_drawdown_scores(
        selection_input.net_returns,
        hold_days,
        selection_input.observed,
        include_initial_equity=True,
    )[columns]
    legacy_scores = pooled_return_drawdown_scores(
        selection_input.net_returns,
        hold_days,
        selection_input.observed,
        include_initial_equity=False,
    )[columns]
    current_max_difference = float(np.abs(current_scores - stored).max())
    legacy_max_difference = float(np.abs(legacy_scores - stored).max())
    tolerance = 1e-10
    if current_max_difference <= tolerance:
        return {
            "drawdown_convention": "initial_equity_high_water",
            "include_initial_equity": True,
            "stored_scores_verified": True,
            "verified_candidate_count": len(columns),
            "maximum_absolute_score_difference": current_max_difference,
        }
    if legacy_max_difference <= tolerance:
        return {
            "drawdown_convention": "legacy_post_first_cohort_high_water",
            "include_initial_equity": False,
            "stored_scores_verified": True,
            "verified_candidate_count": len(columns),
            "maximum_absolute_score_difference": legacy_max_difference,
        }
    raise ValueError(
        "stored development selection scores cannot be reproduced by either supported drawdown convention "
        f"(initial={current_max_difference:.6g}, legacy={legacy_max_difference:.6g})"
    )


def circular_block_bootstrap_indices(
    cohort_count: int, block_cohorts: int, rng: np.random.Generator
) -> np.ndarray:
    """Sample a cohort calendar with circular, fixed-length blocks."""

    if cohort_count < 1 or block_cohorts < 1:
        raise ValueError("cohort_count and block_cohorts must be positive")
    starts = rng.integers(0, cohort_count, size=math.ceil(cohort_count / block_cohorts))
    offsets = np.arange(block_cohorts, dtype=int)
    return ((starts[:, None] + offsets[None, :]) % cohort_count).ravel()[:cohort_count]


def selection_multiplicity_bootstrap(
    selection_input: SelectionMultiplicityInput,
    *,
    hold_days: int,
    replicates: int,
    block_cohorts: int,
    seed: int,
    include_initial_equity: bool = True,
) -> dict[str, Any]:
    """Audit a stored development winner for search multiplicity without reading its test window.

    The circular blocks preserve serial clustering and all candidates share
    every sampled row, retaining their real cross-candidate dependence.  For
    the global-null tail probability, each candidate's *traded* development
    returns are centered independently while cash cohorts remain zero.  This
    asks whether the best score among the searched library is unusual if no
    candidate has an average traded excess return; it is not a promotion rule.
    """

    if replicates < 100:
        raise ValueError("selection multiplicity audit requires at least 100 bootstrap replicates")
    returns = selection_input.net_returns
    holdings = selection_input.holdings
    observed = selection_input.observed
    actual_scores = pooled_return_drawdown_scores(
        returns, hold_days, observed, include_initial_equity=include_initial_equity
    )
    actual_index = int(np.argmax(actual_scores))
    stored_winner = str(selection_input.study.get("winner_selected_on_development_only") or "")
    if stored_winner and selection_input.candidates[actual_index] != stored_winner:
        raise ValueError("stored development winner cannot be reproduced from its recorded development cohorts")
    centered = returns.copy()
    for column in range(centered.shape[1]):
        traded = observed[:, column] & (holdings[:, column] > 0)
        if traded.any():
            centered[traded, column] -= centered[traded, column].mean()
    rng = np.random.default_rng(seed)
    raw_winner_counts = np.zeros(returns.shape[1], dtype=int)
    null_max_scores = np.empty(replicates, dtype=float)
    for replicate in range(replicates):
        indices = circular_block_bootstrap_indices(returns.shape[0], block_cohorts, rng)
        raw_scores = pooled_return_drawdown_scores(
            returns[indices], hold_days, observed[indices], include_initial_equity=include_initial_equity
        )
        raw_winner_counts[int(np.argmax(raw_scores))] += 1
        null_max_scores[replicate] = float(
            pooled_return_drawdown_scores(
                centered[indices], hold_days, observed[indices], include_initial_equity=include_initial_equity
            ).max()
        )
    observed_score = float(actual_scores[actual_index])
    return {
        "winner": selection_input.candidates[actual_index],
        "winner_development_selection_score": observed_score,
        "candidate_scores": [
            {"candidate": candidate, "development_selection_score": float(score)}
            for candidate, score in zip(selection_input.candidates, actual_scores, strict=True)
        ],
        "winner_resample_frequency": float(raw_winner_counts[actual_index] / replicates),
        "resample_winner_frequencies": [
            {"candidate": candidate, "frequency": float(count / replicates)}
            for candidate, count in zip(selection_input.candidates, raw_winner_counts, strict=True)
        ],
        "global_null_max_score_p_value": float((1 + np.count_nonzero(null_max_scores >= observed_score)) / (replicates + 1)),
        "global_null_max_score_quantiles": {
            "p50": float(np.quantile(null_max_scores, 0.50)),
            "p90": float(np.quantile(null_max_scores, 0.90)),
            "p95": float(np.quantile(null_max_scores, 0.95)),
            "p99": float(np.quantile(null_max_scores, 0.99)),
        },
    }


def run_selection_multiplicity_audit(args: argparse.Namespace) -> dict[str, Any]:
    """Write a development-only block-bootstrap audit for one saved factor sweep."""

    study_path = Path(args.study).expanduser()
    selection_input = load_selection_multiplicity_input(study_path)
    policy = str(selection_input.study.get("selection_policy") or "pooled_return_drawdown")
    if policy != "pooled_return_drawdown":
        raise ValueError("selection multiplicity audit currently supports only pooled_return_drawdown studies")
    convention = infer_selection_score_drawdown_convention(selection_input, int(args.hold_days))
    bootstrap = selection_multiplicity_bootstrap(
        selection_input,
        hold_days=int(args.hold_days),
        replicates=int(args.bootstrap_replicates),
        block_cohorts=int(args.block_cohorts),
        seed=int(args.seed),
        include_initial_equity=bool(convention["include_initial_equity"]),
    )
    run_id = _timestamp()
    audit = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "development_only_candidate_selection_multiplicity_audit_not_investment_advice",
        "study": {
            "path": str(study_path.resolve()),
            "run_id": selection_input.study.get("run_id"),
            "candidate_library_fingerprint_sha256": selection_input.study.get("candidate_library_fingerprint_sha256"),
            "selection_policy": policy,
            "stored_winner_selected_on_development_only": selection_input.study.get("winner_selected_on_development_only"),
            "selection_score_reproducibility": convention,
        },
        "data": {
            "development_signal_start": selection_input.signal_dates.min().date().isoformat(),
            "development_signal_end": selection_input.signal_dates.max().date().isoformat(),
            "development_cohort_count": int(len(selection_input.signal_dates)),
            "candidate_development_cohort_count": {
                "minimum": int(selection_input.observed.sum(axis=0).min()),
                "maximum": int(selection_input.observed.sum(axis=0).max()),
            },
            "candidate_count": int(len(selection_input.candidates)),
            "test_period_used": False,
        },
        "bootstrap": {
            "method": "candidate-dependence-preserving circular block bootstrap",
            "replicates": int(args.bootstrap_replicates),
            "block_cohorts": int(args.block_cohorts),
            "seed": int(args.seed),
            "global_null": "candidate-wise centered traded returns; cash cohorts remain zero",
        },
        "result": {
            **bootstrap,
            "global_null_significance_level": 0.05,
            "global_null_max_score_unusual": bool(bootstrap["global_null_max_score_p_value"] < 0.05),
        },
        "limitations": [
            "This is a development-only selection-bias diagnostic; it does not promote, suspend, replace, or create a strategy.",
            "The bootstrap quantifies instability and a centered global-null tail probability, not an economic guarantee or a probability of future profit.",
            "Candidate returns require the accepted point-in-time price basis but still share a current-listing universe, so survivorship and execution limitations remain.",
            "When a legacy drawdown convention is required to reproduce a stored study, that convention is used only to audit the historical selection and must not be used for new research.",
            "The original test period is intentionally not read; future paper evidence remains the only new validation.",
        ],
    }
    root = Path(args.experiment_root).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    destination = root / f"{run_id}_selection_multiplicity_audit.json"
    _atomic_write_text(destination, json.dumps(audit, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return {
        "status": "completed",
        "audit_path": str(destination.resolve()),
        "winner": bootstrap["winner"],
        "winner_resample_frequency": bootstrap["winner_resample_frequency"],
        "global_null_max_score_p_value": bootstrap["global_null_max_score_p_value"],
    }


def limit_like_return_threshold(instruments: pd.Series) -> pd.Series:
    """Return the fixed daily-return hurdle for a limit-like close event.

    This is deliberately a *limit-like* heuristic rather than an exchange
    limit-up flag: the daily Qlib quotes cannot model every board rule, ST
    exception, corporate-action adjustment, or order-book fill.  ChiNext
    symbols use the 19.5% hurdle; the remaining buyable main-board symbols use
    9.5%.  STAR symbols are outside the holding universe.
    """

    normalized = instruments.astype(str)
    chinext = normalized.str.startswith(("SZ300", "SZ301"), na=False)
    return pd.Series(
        np.where(chinext, LIMIT_LIKE_CHINEXT_RETURN_THRESHOLD, LIMIT_LIKE_MAIN_RETURN_THRESHOLD),
        index=instruments.index,
        dtype=float,
    )


def limit_like_event_mask(frame: pd.DataFrame) -> pd.Series:
    """Identify fixed close-known strong-close events without future price use."""

    required = {"instrument", "momentum_1", "close_to_high"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError("limit-like event frame is missing columns: " + ", ".join(missing))
    momentum = pd.to_numeric(frame["momentum_1"], errors="coerce")
    close_to_high = pd.to_numeric(frame["close_to_high"], errors="coerce")
    threshold = limit_like_return_threshold(frame["instrument"])
    return momentum.ge(threshold) & close_to_high.ge(LIMIT_LIKE_CLOSE_TO_HIGH_MIN)


def limit_like_event_rounds(
    ranked: pd.DataFrame,
    *,
    hold_days: int,
    topk: int,
    open_cost: float,
    close_cost: float,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Evaluate the fixed limit-like continuation basket on non-overlapping cohorts.

    On each eligible signal close, eligible limit-like events are ranked only
    by same-close one-day turnover surge.  The first ``topk`` form one basket,
    which enters at the next local open and exits on the close after
    ``hold_days`` sessions.  Fewer than a complete declared basket are cash,
    not silently filled with non-event stocks.
    """

    if hold_days < 1 or topk < 1:
        raise ValueError("hold_days and topk must both be positive")
    required = {
        "datetime",
        "instrument",
        "open",
        "close",
        "momentum_1",
        "close_to_high",
        "turnover_surge_1",
        "quality_eligible",
    }
    missing = sorted(required - set(ranked.columns))
    if missing:
        raise ValueError("limit-like event audit is missing fields: " + ", ".join(missing))
    calendar = pd.DatetimeIndex(sorted(pd.to_datetime(ranked["datetime"]).dropna().unique()))
    if len(calendar) <= hold_days + 1:
        raise ValueError("research window is too short for the requested holding period")
    date_to_position = {date: position for position, date in enumerate(calendar)}
    rebalances = calendar[: -(hold_days + 1) : hold_days]
    base = ranked.loc[
        ranked["quality_eligible"].fillna(False) & ranked["datetime"].isin(rebalances)
    ].copy()
    base["limit_like_event"] = limit_like_event_mask(base)
    events = base.loc[base["limit_like_event"]].copy()
    events["turnover_surge_1"] = pd.to_numeric(events["turnover_surge_1"], errors="coerce")
    events = events.dropna(subset=["turnover_surge_1"])
    events = events.sort_values(
        ["datetime", "turnover_surge_1", "momentum_1", "instrument"],
        ascending=[True, False, False, True],
        kind="stable",
    )
    selected = events.groupby("datetime", sort=False).head(topk).copy()
    selected["entry_date"] = selected["datetime"].map(lambda value: calendar[date_to_position[value] + 1])
    selected["exit_date"] = selected["datetime"].map(lambda value: calendar[date_to_position[value] + hold_days])
    quotes = ranked[["datetime", "instrument", "open", "close"]].drop_duplicates(["datetime", "instrument"])
    entry = quotes.rename(columns={"datetime": "entry_date", "open": "entry_open"})[
        ["entry_date", "instrument", "entry_open"]
    ]
    exit_quote = quotes.rename(columns={"datetime": "exit_date", "close": "exit_close"})[
        ["exit_date", "instrument", "exit_close"]
    ]
    trades = selected.merge(entry, on=["entry_date", "instrument"], how="left")
    trades = trades.merge(exit_quote, on=["exit_date", "instrument"], how="left")
    trades = trades.dropna(subset=["entry_open", "exit_close"])
    trades = trades.loc[(trades["entry_open"] > 0.0) & (trades["exit_close"] > 0.0)].copy()
    trades["gross_return"] = trades["exit_close"] / trades["entry_open"] - 1.0
    trades["net_return"] = (1.0 - open_cost) * (1.0 + trades["gross_return"]) * (1.0 - close_cost) - 1.0
    minimum_holdings = minimum_required_holdings(topk)
    rounds = (
        trades.groupby(["datetime", "entry_date", "exit_date"], as_index=False, sort=True)
        .agg(
            gross_return=("gross_return", "mean"),
            net_return=("net_return", "mean"),
            holdings=("instrument", "nunique"),
        )
        .rename(columns={"datetime": "signal_date"})
    )
    rounds = rounds.loc[rounds["holdings"] >= minimum_holdings].copy()
    rounds["regime_active"] = True
    rounds = rounds.sort_values("signal_date", kind="stable").reset_index(drop=True)
    event_dates = events["datetime"].nunique()
    status = {
        "eligible_rebalance_cohorts": int(len(rebalances)),
        "event_rebalance_cohorts": int(event_dates),
        "complete_executable_cohorts": int(len(rounds)),
        "discarded_incomplete_or_unquoted_event_cohorts": int(max(event_dates - len(rounds), 0)),
    }
    return rounds, status


def direct_event_basket_decision(rounds: pd.DataFrame, hold_days: int) -> dict[str, Any]:
    """Apply one fixed direct-event viability gate without selecting a strategy."""

    performance = return_metrics(rounds, hold_days)
    by_year = {
        str(year): return_metrics(group, hold_days)
        for year, group in rounds.groupby(rounds["signal_date"].dt.year, sort=True)
    }
    annual_net_returns = {
        year: metrics.get("net_cumulative_return") for year, metrics in by_year.items()
    }
    failures: list[str] = []
    if performance["rounds"] < LIMIT_LIKE_EVENT_MIN_COHORTS:
        failures.append(f"fewer than {LIMIT_LIKE_EVENT_MIN_COHORTS} executable event cohorts")
    if performance["net_cumulative_return"] is None or performance["net_cumulative_return"] <= 0.0:
        failures.append("non-positive event-basket net cumulative return")
    if performance["max_drawdown"] is None or performance["max_drawdown"] < LIMIT_LIKE_EVENT_MAX_DRAWDOWN:
        failures.append(f"event-basket maximum drawdown worse than {LIMIT_LIKE_EVENT_MAX_DRAWDOWN:.0%}")
    if len(by_year) < FACTOR_STABILITY_MIN_CALENDAR_YEARS:
        failures.append(f"fewer than {FACTOR_STABILITY_MIN_CALENDAR_YEARS} observed calendar years")
    non_positive_years = [
        year for year, value in annual_net_returns.items() if value is None or float(value) <= 0.0
    ]
    if non_positive_years:
        failures.append("non-positive annual event-basket net cumulative return: " + ", ".join(non_positive_years))
    return {
        "passed": not failures,
        "failures": failures,
        "performance": performance,
        "by_signal_year": by_year,
        "criteria": {
            "minimum_executable_event_cohorts": LIMIT_LIKE_EVENT_MIN_COHORTS,
            "net_cumulative_return_gt": 0.0,
            "max_drawdown_gte": LIMIT_LIKE_EVENT_MAX_DRAWDOWN,
            "minimum_calendar_years": FACTOR_STABILITY_MIN_CALENDAR_YEARS,
            "every_observed_calendar_year_net_cumulative_return_gt": 0.0,
        },
    }


def limit_like_event_decision(rounds: pd.DataFrame, hold_days: int) -> dict[str, Any]:
    """Apply the shared direct-event gate to the limit-like continuation hypothesis."""

    return direct_event_basket_decision(rounds, hold_days)


def run_limit_like_event_audit(args: argparse.Namespace) -> dict[str, Any]:
    """Run one fixed development-only strong-close event hypothesis audit."""

    provider_uri = Path(args.provider_uri).expanduser()
    fundamental_path = Path(args.fundamentals).expanduser()
    experiment_root = Path(args.experiment_root).expanduser()
    fundamentals = load_fundamentals(fundamental_path)
    market = load_market_data(provider_uri, args.start, args.end, args.batch_size)
    if market["datetime"].max() > pd.Timestamp(args.development_end):
        raise ValueError(
            "limit-like-event-audit is development-only; pass --end no later than --development-end"
        )
    market = attach_quality_asof(market, fundamentals, max_age_days=args.max_quality_age_days)
    ranked = rank_factor_frame(market)
    rounds, cohort_status = limit_like_event_rounds(
        ranked,
        hold_days=args.hold_days,
        topk=args.topk,
        open_cost=args.open_cost,
        close_cost=args.close_cost,
    )
    decision = limit_like_event_decision(rounds, args.hold_days)
    run_id = _timestamp()
    audit = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "development_only_limit_like_strong_close_event_audit_research_not_investment_advice",
        "hypothesis": {
            "name": "limit_like_strong_close_high_turnover_continuation",
            "statement": (
                "Among quality-eligible stocks with a fixed limit-like same-close return and close-near-high event, "
                "the three highest same-day turnover-surges form a next-open to third-close continuation basket."
            ),
            "direction": "continuation",
        },
        "definition": {
            "main_board_daily_return_gte": LIMIT_LIKE_MAIN_RETURN_THRESHOLD,
            "chinext_daily_return_gte": LIMIT_LIKE_CHINEXT_RETURN_THRESHOLD,
            "chinext_symbol_prefixes": ["SZ300", "SZ301"],
            "close_to_high_gte": LIMIT_LIKE_CLOSE_TO_HIGH_MIN,
            "within_event_selection": "descending same-close turnover_surge_1, then momentum_1, then instrument",
            "incomplete_baskets": "discarded; non-event stocks never fill a basket",
        },
        "strategy_timing": {
            "universe": "buyable_main_chinext",
            "holding_period_trading_days": args.hold_days,
            "rebalancing": "non_overlapping_every_holding_period",
            "topk": args.topk,
            "signal_time": "market close",
            "entry": "next local trading-session open",
            "exit": "local close after holding_period_trading_days",
            "open_cost": args.open_cost,
            "close_cost": args.close_cost,
        },
        "quality_gate": {
            "source": str(fundamental_path.resolve()),
            "sha256": file_sha256(fundamental_path),
            "effective_date": "strictly next local trading day after announcement_date",
            "max_quality_age_days": args.max_quality_age_days,
        },
        "data": {
            "provider_uri": str(provider_uri.resolve()),
            "calendar_start": market["datetime"].min().date().isoformat(),
            "calendar_end": market["datetime"].max().date().isoformat(),
            "development_end": args.development_end,
            "test_period_used": False,
            **cohort_status,
        },
        "result": decision,
        "limitations": [
            "This is a fixed development-only event audit, not a strategy registration, stock list, or trading recommendation.",
            "Limit-like events are inferred from accepted point-in-time daily price fields and are not official exchange limit-up flags.",
            "The audit cannot determine whether a next-open order would be blocked by a limit, suspension, queue, or liquidity condition.",
            "The current holding universe is derived from a current listing snapshot and can introduce survivorship bias.",
        ],
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    destination = experiment_root / f"{run_id}_limit_like_event_audit.json"
    _atomic_write_text(destination, json.dumps(audit, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return {
        "status": "completed",
        "audit_path": str(destination.resolve()),
        "passed": decision["passed"],
        "executable_event_cohorts": decision["performance"]["rounds"],
        "net_cumulative_return": decision["performance"]["net_cumulative_return"],
        "max_drawdown": decision["performance"]["max_drawdown"],
    }


def quarterly_acceleration_event_capacity(
    fundamentals: pd.DataFrame,
    calendar: pd.DatetimeIndex,
    instrument_intervals: dict[str, list[tuple[pd.Timestamp, pd.Timestamp]]],
    *,
    acceleration_column: str,
    hold_days: int,
    topk: int,
    minimum_cohorts: int = QUARTERLY_EVENT_CAPACITY_MIN_COHORTS,
) -> dict[str, Any]:
    """Count potential non-overlapping event baskets without reading any return.

    Sparse event ideas must be able to satisfy the existing independent-cohort
    gate before a forward-return audit is allowed.  This function uses only
    filing fields, the local calendar, and buyable-instrument activity spans;
    OHLC fields and post-signal outcomes are neither accepted nor loaded.
    """

    if acceleration_column not in QUARTERLY_ACCELERATION_METRICS:
        choices = ", ".join(sorted(QUARTERLY_ACCELERATION_METRICS))
        raise ValueError(f"unknown quarterly acceleration metric; choose one of: {choices}")
    if hold_days < 1 or topk < 1 or minimum_cohorts < 1:
        raise ValueError("hold_days, topk, and minimum_cohorts must all be positive")
    sessions = pd.DatetimeIndex(pd.to_datetime(calendar)).normalize().unique().sort_values()
    if len(sessions) <= hold_days + 1:
        raise ValueError("capacity window is too short for the requested holding period")
    rebalances = sessions[: -(hold_days + 1) : hold_days]
    events = attach_fundamental_accelerations(fundamentals)
    events["quality_effective_date"] = _first_trading_day_after(sessions, events["announcement_date"])
    events = events.dropna(subset=["quality_effective_date"])
    events = events.sort_values(
        ["instrument", "quality_effective_date", "report_date", "announcement_date"], kind="stable"
    ).drop_duplicates(["instrument", "quality_effective_date"], keep="last")
    events = events.loc[events["quality_effective_date"].isin(rebalances)].copy()

    def active_on_event(row: Any) -> bool:
        event_date = pd.Timestamp(row.quality_effective_date)
        return any(
            pd.Timestamp(start).normalize() <= event_date <= pd.Timestamp(end).normalize()
            for start, end in instrument_intervals.get(str(row.instrument), [])
        )

    events["buyable_active"] = [active_on_event(row) for row in events.itertuples(index=False)]
    quality = (
        events["buyable_active"]
        & events["roe"].ge(5.0)
        & events["net_profit"].gt(0.0)
        & events["revenue_yoy"].gt(0.0)
        & events["profit_yoy"].gt(0.0)
    )
    acceleration = pd.to_numeric(events[acceleration_column], errors="coerce")
    positive = events.loc[quality & acceleration.gt(0.0)].copy()
    counts = positive.groupby("quality_effective_date", sort=True)["instrument"].nunique()
    complete = counts.loc[counts.ge(topk)]
    by_year = {
        str(int(year)): int(count)
        for year, count in complete.groupby(complete.index.year).size().items()
    }
    complete_cohorts = int(len(complete))
    return {
        "metric": acceleration_column,
        "metric_description": QUARTERLY_ACCELERATION_METRICS[acceleration_column],
        "holding_period_trading_days": hold_days,
        "topk": topk,
        "minimum_required_cohorts": minimum_cohorts,
        "calendar_sessions": int(len(sessions)),
        "non_overlapping_rebalance_capacity": int(len(rebalances)),
        "newly_effective_positive_quality_rows": int(len(positive)),
        "event_dates_with_any_positive_name": int(len(counts)),
        "complete_topk_event_cohorts": complete_cohorts,
        "complete_topk_event_cohorts_by_year": by_year,
        "capacity_gate_passed": complete_cohorts >= minimum_cohorts,
        "forward_return_fields_read": False,
        "rule": "If capacity_gate_passed is false, no return audit may be run for this event definition.",
    }


def local_market_instrument_intervals(
    provider_uri: Path, *, market: str, start: str, end: str
) -> tuple[pd.DatetimeIndex, dict[str, list[tuple[pd.Timestamp, pd.Timestamp]]]]:
    """Load only calendar and instrument-activity spans for a no-outcome capacity audit."""

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    import qlib
    from qlib.data import D

    qlib.init(provider_uri=str(provider_uri.expanduser().resolve()), region="cn", kernels=1)
    calendar = pd.DatetimeIndex(D.calendar(start_time=start, end_time=end, freq="day"))
    intervals = D.list_instruments(
        D.instruments(market=market), start_time=start, end_time=end, as_list=False
    )
    return calendar, {
        str(instrument): [(pd.Timestamp(span_start), pd.Timestamp(span_end)) for span_start, span_end in spans]
        for instrument, spans in intervals.items()
    }


def run_quarterly_event_capacity_audit(args: argparse.Namespace) -> dict[str, Any]:
    """Persist a no-return feasibility gate for one quarterly event definition."""

    if pd.Timestamp(args.end) > pd.Timestamp(args.development_end):
        raise ValueError("quarterly-event-capacity-audit must stop no later than development_end")
    provider_uri = Path(args.provider_uri).expanduser()
    fundamental_path = Path(args.fundamentals).expanduser()
    fundamentals = load_fundamentals(fundamental_path)
    calendar, intervals = local_market_instrument_intervals(
        provider_uri, market="buyable_main_chinext", start=args.start, end=args.end
    )
    capacity = quarterly_acceleration_event_capacity(
        fundamentals,
        calendar,
        intervals,
        acceleration_column=args.metric,
        hold_days=args.hold_days,
        topk=args.topk,
        minimum_cohorts=args.minimum_cohorts,
    )
    run_id = _timestamp()
    audit = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "quarterly_event_capacity_gate_without_forward_returns",
        "candidate_event": {
            "metric": args.metric,
            "direction": "positive acceleration only; descending raw acceleration",
            "availability": "strictly next local trading day after announcement_date",
        },
        "data": {
            "provider_uri": str(provider_uri.resolve()),
            "fundamentals": str(fundamental_path.resolve()),
            "fundamentals_sha256": file_sha256(fundamental_path),
            "calendar_start": pd.Timestamp(calendar.min()).date().isoformat(),
            "calendar_end": pd.Timestamp(calendar.max()).date().isoformat(),
            "development_end": args.development_end,
            "test_period_used": False,
        },
        "capacity": capacity,
        "decision": (
            "eligible_for_preregistered_return_audit"
            if capacity["capacity_gate_passed"]
            else "rejected_before_return_audit_insufficient_independent_cohorts"
        ),
        "limitations": [
            "No open, close, forward-return, or performance field is loaded by this audit.",
            "The public quarterly snapshot can contain later revisions and is not exchange-grade point-in-time data.",
            "The holding universe is derived from the repository's current listing snapshot and retains survivorship bias.",
        ],
    }
    root = Path(args.experiment_root).expanduser()
    destination = root / f"{run_id}_quarterly_event_capacity_audit.json"
    _atomic_write_text(destination, json.dumps(audit, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return {
        "status": "completed",
        "audit_path": str(destination.resolve()),
        "metric": args.metric,
        "complete_topk_event_cohorts": capacity["complete_topk_event_cohorts"],
        "minimum_required_cohorts": capacity["minimum_required_cohorts"],
        "capacity_gate_passed": capacity["capacity_gate_passed"],
        "decision": audit["decision"],
    }


def quarterly_profit_acceleration_event_rounds(
    market: pd.DataFrame,
    *,
    hold_days: int,
    topk: int,
    open_cost: float,
    close_cost: float,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Evaluate newly effective positive quarterly profit-acceleration events.

    An announcement becomes visible only on ``quality_effective_date`` (the
    next local session after its public date).  On that first safe close, the
    event requires a positive same-fiscal-quarter profit-yoy acceleration and
    a quality-qualified issuer.  The three greatest raw accelerations form a
    next-open, three-day basket; no stale report and no non-event name fills a
    missing basket.
    """

    if hold_days < 1 or topk < 1:
        raise ValueError("hold_days and topk must both be positive")
    required = {
        "datetime",
        "instrument",
        "open",
        "close",
        "quality_eligible",
        "quality_effective_date",
        "profit_yoy_acceleration",
    }
    missing = sorted(required - set(market.columns))
    if missing:
        raise ValueError("quarterly acceleration event audit is missing fields: " + ", ".join(missing))
    calendar = pd.DatetimeIndex(sorted(pd.to_datetime(market["datetime"]).dropna().unique()))
    if len(calendar) <= hold_days + 1:
        raise ValueError("research window is too short for the requested holding period")
    date_to_position = {date: position for position, date in enumerate(calendar)}
    rebalances = calendar[: -(hold_days + 1) : hold_days]
    base = market.loc[
        market["quality_eligible"].fillna(False) & market["datetime"].isin(rebalances)
    ].copy()
    base["quality_effective_date"] = pd.to_datetime(base["quality_effective_date"], errors="coerce")
    base["profit_yoy_acceleration"] = pd.to_numeric(base["profit_yoy_acceleration"], errors="coerce")
    events = base.loc[
        base["quality_effective_date"].eq(base["datetime"])
        & base["profit_yoy_acceleration"].gt(0.0)
    ].copy()
    events = events.sort_values(
        ["datetime", "profit_yoy_acceleration", "instrument"],
        ascending=[True, False, True],
        kind="stable",
    )
    selected = events.groupby("datetime", sort=False).head(topk).copy()
    selected["entry_date"] = selected["datetime"].map(lambda value: calendar[date_to_position[value] + 1])
    selected["exit_date"] = selected["datetime"].map(lambda value: calendar[date_to_position[value] + hold_days])
    quotes = market[["datetime", "instrument", "open", "close"]].drop_duplicates(["datetime", "instrument"])
    entry = quotes.rename(columns={"datetime": "entry_date", "open": "entry_open"})[
        ["entry_date", "instrument", "entry_open"]
    ]
    exit_quote = quotes.rename(columns={"datetime": "exit_date", "close": "exit_close"})[
        ["exit_date", "instrument", "exit_close"]
    ]
    trades = selected.merge(entry, on=["entry_date", "instrument"], how="left")
    trades = trades.merge(exit_quote, on=["exit_date", "instrument"], how="left")
    trades = trades.dropna(subset=["entry_open", "exit_close"])
    trades = trades.loc[(trades["entry_open"] > 0.0) & (trades["exit_close"] > 0.0)].copy()
    trades["gross_return"] = trades["exit_close"] / trades["entry_open"] - 1.0
    trades["net_return"] = (1.0 - open_cost) * (1.0 + trades["gross_return"]) * (1.0 - close_cost) - 1.0
    minimum_holdings = minimum_required_holdings(topk)
    rounds = (
        trades.groupby(["datetime", "entry_date", "exit_date"], as_index=False, sort=True)
        .agg(
            gross_return=("gross_return", "mean"),
            net_return=("net_return", "mean"),
            holdings=("instrument", "nunique"),
        )
        .rename(columns={"datetime": "signal_date"})
    )
    rounds = rounds.loc[rounds["holdings"] >= minimum_holdings].copy()
    rounds["regime_active"] = True
    rounds = rounds.sort_values("signal_date", kind="stable").reset_index(drop=True)
    event_dates = events["datetime"].nunique()
    status = {
        "eligible_rebalance_cohorts": int(len(rebalances)),
        "event_rebalance_cohorts": int(event_dates),
        "complete_executable_cohorts": int(len(rounds)),
        "discarded_incomplete_or_unquoted_event_cohorts": int(max(event_dates - len(rounds), 0)),
    }
    return rounds, status


def quarterly_profit_acceleration_event_decision(rounds: pd.DataFrame, hold_days: int) -> dict[str, Any]:
    """Apply the shared direct-event gate to newly effective quarterly reports."""

    return direct_event_basket_decision(rounds, hold_days)


def run_quarterly_profit_acceleration_event_audit(args: argparse.Namespace) -> dict[str, Any]:
    """Run one fixed development-only quarterly announcement drift audit."""

    provider_uri = Path(args.provider_uri).expanduser()
    fundamental_path = Path(args.fundamentals).expanduser()
    experiment_root = Path(args.experiment_root).expanduser()
    fundamentals = load_fundamentals(fundamental_path)
    market = load_market_data(provider_uri, args.start, args.end, args.batch_size)
    if market["datetime"].max() > pd.Timestamp(args.development_end):
        raise ValueError(
            "quarterly-profit-acceleration-event-audit is development-only; pass --end no later than --development-end"
        )
    market = attach_quality_asof(market, fundamentals, max_age_days=args.max_quality_age_days)
    rounds, cohort_status = quarterly_profit_acceleration_event_rounds(
        market,
        hold_days=args.hold_days,
        topk=args.topk,
        open_cost=args.open_cost,
        close_cost=args.close_cost,
    )
    decision = quarterly_profit_acceleration_event_decision(rounds, args.hold_days)
    run_id = _timestamp()
    audit = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "development_only_quarterly_profit_acceleration_event_audit_research_not_investment_advice",
        "hypothesis": {
            "name": "newly_effective_positive_quarterly_profit_acceleration_drift",
            "statement": (
                "On the first safe close after a newly announced quarterly report, quality-qualified issuers with "
                "positive same-fiscal-quarter profit-yoy acceleration are ranked by raw acceleration; the top three "
                "form a next-open to third-close drift basket."
            ),
            "direction": "continuation",
        },
        "definition": {
            "report_availability": "strictly next local trading day after announcement_date",
            "event_signal_date": "quality_effective_date close",
            "profit_yoy_acceleration_gt": 0.0,
            "within_event_selection": "descending raw same-fiscal-quarter profit_yoy_acceleration, then instrument",
            "incomplete_baskets": "discarded; stale-report and non-event stocks never fill a basket",
        },
        "strategy_timing": {
            "universe": "buyable_main_chinext",
            "holding_period_trading_days": args.hold_days,
            "rebalancing": "non_overlapping_every_holding_period",
            "topk": args.topk,
            "signal_time": "quality_effective_date market close",
            "entry": "next local trading-session open",
            "exit": "local close after holding_period_trading_days",
            "open_cost": args.open_cost,
            "close_cost": args.close_cost,
        },
        "quality_gate": {
            "source": str(fundamental_path.resolve()),
            "sha256": file_sha256(fundamental_path),
            "effective_date": "strictly next local trading day after announcement_date",
            "max_quality_age_days": args.max_quality_age_days,
        },
        "data": {
            "provider_uri": str(provider_uri.resolve()),
            "calendar_start": market["datetime"].min().date().isoformat(),
            "calendar_end": market["datetime"].max().date().isoformat(),
            "development_end": args.development_end,
            "test_period_used": False,
            **cohort_status,
        },
        "result": decision,
        "limitations": [
            "This is a fixed development-only event audit, not a strategy registration, stock list, or trading recommendation.",
            "Quarterly public records can be revised or incomplete; this is not an exchange-grade point-in-time filing database.",
            "The one-session availability delay is conservative and cannot prove the original publication timestamp.",
            "The current holding universe is derived from a current listing snapshot and can introduce survivorship bias.",
        ],
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    destination = experiment_root / f"{run_id}_quarterly_profit_acceleration_event_audit.json"
    _atomic_write_text(destination, json.dumps(audit, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return {
        "status": "completed",
        "audit_path": str(destination.resolve()),
        "passed": decision["passed"],
        "executable_event_cohorts": decision["performance"]["rounds"],
        "net_cumulative_return": decision["performance"]["net_cumulative_return"],
        "max_drawdown": decision["performance"]["max_drawdown"],
    }


def forward_factor_return_frame(ranked: pd.DataFrame, hold_days: int) -> pd.DataFrame:
    """Pair every close-known eligible signal with its next-open three-day return.

    This intentionally mirrors the research harness timing but makes no
    portfolio decision.  It is used only for cross-sectional factor
    diagnostics, and therefore retains every eligible name with complete
    future quotes rather than choosing a TopK basket first.
    """

    if hold_days < 1:
        raise ValueError("hold_days must be positive")
    calendar = pd.DatetimeIndex(sorted(ranked["datetime"].unique()))
    if len(calendar) <= hold_days + 1:
        raise ValueError("research window is too short for the requested holding period")
    date_to_position = {date: position for position, date in enumerate(calendar)}
    rebalances = calendar[: -(hold_days + 1) : hold_days]
    signals = ranked.loc[
        ranked["quality_eligible"].fillna(False) & ranked["datetime"].isin(rebalances)
    ].copy()
    signals["entry_date"] = signals["datetime"].map(lambda value: calendar[date_to_position[value] + 1])
    signals["exit_date"] = signals["datetime"].map(lambda value: calendar[date_to_position[value] + hold_days])
    quotes = ranked[["datetime", "instrument", "open", "close"]].drop_duplicates(["datetime", "instrument"])
    entry = quotes.rename(columns={"datetime": "entry_date", "open": "entry_open"})[
        ["entry_date", "instrument", "entry_open"]
    ]
    exit_quote = quotes.rename(columns={"datetime": "exit_date", "close": "exit_close"})[
        ["exit_date", "instrument", "exit_close"]
    ]
    result = signals.merge(entry, on=["entry_date", "instrument"], how="left")
    result = result.merge(exit_quote, on=["exit_date", "instrument"], how="left")
    result = result.dropna(subset=["close", "entry_open", "exit_close"])
    result = result.loc[
        (result["close"] > 0.0) & (result["entry_open"] > 0.0) & (result["exit_close"] > 0.0)
    ].copy()
    result = result.rename(columns={"datetime": "signal_date"})
    result["forward_gross_return"] = result["exit_close"] / result["entry_open"] - 1.0
    return result.sort_values(["signal_date", "instrument"], kind="stable")


def summarize_factor_diagnostics(
    forward_returns: pd.DataFrame,
    factor_columns: Iterable[str],
    hold_days: int,
    topk: int,
    open_cost: float,
    close_cost: float,
) -> list[dict[str, Any]]:
    """Describe each close-known factor's non-overlapping forward association.

    Higher factor values are always interpreted according to their already
    declared candidate direction.  Rank IC is computed within each signal
    cross-section; the TopK-minus-BottomK figure is a descriptive gross return
    spread, not a tradable long-short claim.
    """

    if hold_days < 1 or topk < 1:
        raise ValueError("hold_days and topk must both be positive")
    required = {"signal_date", "instrument", "forward_gross_return"}
    missing = sorted(required - set(forward_returns.columns))
    if missing:
        raise ValueError(f"forward_returns is missing required columns: {', '.join(missing)}")

    def optional_finite_float(value: Any) -> float | None:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        return numeric if np.isfinite(numeric) else None

    summaries: list[dict[str, Any]] = []
    for factor in factor_columns:
        if factor not in forward_returns.columns:
            continue
        cohorts: list[dict[str, Any]] = []
        quintile_means: list[dict[str, Any]] = []
        for signal_date, group in forward_returns.groupby("signal_date", sort=True):
            context_columns = [
                column
                for column in (
                    "entry_date",
                    "exit_date",
                    "close",
                    "entry_open",
                    *FACTOR_TAIL_ATTRIBUTION_COLUMNS,
                )
                if column in group.columns and column != factor
            ]
            valid = group[["instrument", factor, "forward_gross_return", *context_columns]].dropna(
                subset=[factor, "forward_gross_return"]
            )
            if len(valid) < max(2, 2 * topk) or valid[factor].nunique() < 2:
                continue
            rank_ic = valid[factor].corr(valid["forward_gross_return"], method="spearman")
            if pd.isna(rank_ic):
                continue
            ordered = valid.sort_values([factor, "instrument"], ascending=[False, True], kind="stable")
            selected = ordered.head(topk).copy()
            top = selected["forward_gross_return"]
            bottom = ordered.tail(topk)["forward_gross_return"]
            top_gross_return = float(top.mean())
            top_net_return = float((1.0 - open_cost) * (1.0 + top_gross_return) * (1.0 - close_cost) - 1.0)
            selected_stocks: list[dict[str, Any]] = []
            for row in selected.to_dict(orient="records"):
                entry_gap_return = None
                close_value = optional_finite_float(row.get("close"))
                entry_open_value = optional_finite_float(row.get("entry_open"))
                if close_value is not None and entry_open_value is not None and close_value > 0.0:
                    entry_gap_return = entry_open_value / close_value - 1.0
                selected_stocks.append(
                    {
                        "instrument": str(row["instrument"]),
                        "factor_value": float(row[factor]),
                        "forward_gross_return": float(row["forward_gross_return"]),
                        "entry_date": row.get("entry_date"),
                        "exit_date": row.get("exit_date"),
                        "entry_gap_return": entry_gap_return,
                        "close_known_feature_ranks": {
                            column: optional_finite_float(row.get(column))
                            for column in FACTOR_TAIL_ATTRIBUTION_COLUMNS
                            if column in row
                        },
                    }
                )
            factor_rank = valid[factor].rank(method="first")
            quintile = pd.qcut(factor_rank, FACTOR_DIAGNOSTIC_BUCKET_COUNT, labels=False)
            for bucket, bucket_returns in valid.groupby(quintile, observed=True)["forward_gross_return"]:
                quintile_means.append(
                    {
                        "signal_date": pd.Timestamp(signal_date),
                        "quintile": int(bucket) + 1,
                        "mean_forward_gross_return": float(bucket_returns.mean()),
                    }
                )
            cohorts.append(
                {
                    "signal_date": pd.Timestamp(signal_date),
                    "rank_ic": float(rank_ic),
                    "topk_gross_return": top_gross_return,
                    "topk_net_return": top_net_return,
                    "top_minus_bottom_gross_return": float(top.mean() - bottom.mean()),
                    "selected_stocks": selected_stocks,
                }
            )
        if not cohorts:
            continue
        cohort_frame = pd.DataFrame(cohorts)
        quintile_frame = pd.DataFrame(quintile_means)
        topk_rounds = cohort_frame.rename(
            columns={"topk_net_return": "net_return", "topk_gross_return": "gross_return"}
        )
        topk_rounds["holdings"] = topk
        topk_net_returns = cohort_frame["topk_net_return"]
        worst_cohorts = cohort_frame.nsmallest(
            min(FACTOR_DIAGNOSTIC_WORST_COHORT_COUNT, len(cohort_frame)), "topk_net_return"
        )
        topk_tail_risk = {
            "p01_net_return": float(topk_net_returns.quantile(0.01)),
            "p05_net_return": float(topk_net_returns.quantile(0.05)),
            "median_net_return": float(topk_net_returns.median()),
            "negative_return_rate": float((topk_net_returns < 0.0).mean()),
            "below_minus_5pct_rate": float((topk_net_returns < -0.05).mean()),
            "below_minus_10pct_rate": float((topk_net_returns < -0.10).mean()),
            "worst_net_return": float(topk_net_returns.min()),
            "worst_cohorts": [
                {
                    "signal_date": row.signal_date,
                    "rank_ic": float(row.rank_ic),
                    "topk_gross_return": float(row.topk_gross_return),
                    "topk_net_return": float(row.topk_net_return),
                    "top_minus_bottom_gross_return": float(row.top_minus_bottom_gross_return),
                    "selected_stocks": row.selected_stocks,
                }
                for row in worst_cohorts.itertuples(index=False)
            ],
        }
        by_year = {
            str(year): {
                "cohorts": int(len(group)),
                "mean_rank_ic": float(group["rank_ic"].mean()),
                "positive_rank_ic_rate": float((group["rank_ic"] > 0.0).mean()),
                "topk_net_cumulative_return": float((1.0 + group["topk_net_return"]).prod() - 1.0),
            }
            for year, group in cohort_frame.groupby(cohort_frame["signal_date"].dt.year, sort=True)
        }
        summaries.append(
            {
                "factor": factor,
                "cohorts": int(len(cohort_frame)),
                "mean_rank_ic": float(cohort_frame["rank_ic"].mean()),
                "median_rank_ic": float(cohort_frame["rank_ic"].median()),
                "positive_rank_ic_rate": float((cohort_frame["rank_ic"] > 0.0).mean()),
                "mean_top_minus_bottom_gross_return": float(cohort_frame["top_minus_bottom_gross_return"].mean()),
                "mean_forward_gross_return_by_factor_quintile": {
                    str(quintile): float(group["mean_forward_gross_return"].mean())
                    for quintile, group in quintile_frame.groupby("quintile", sort=True)
                },
                "topk": return_metrics(topk_rounds, hold_days),
                "topk_tail_risk": topk_tail_risk,
                "by_signal_year": by_year,
            }
        )
    return sorted(
        summaries,
        key=lambda item: (float(item["mean_rank_ic"]), float(item["mean_top_minus_bottom_gross_return"])),
        reverse=True,
    )


def factor_stability_decision(
    summary: dict[str, Any],
    *,
    minimum_calendar_years: int = FACTOR_STABILITY_MIN_CALENDAR_YEARS,
    minimum_cohorts: int = FACTOR_STABILITY_MIN_COHORTS,
) -> dict[str, Any]:
    """Apply one fixed development-only screen to a factor diagnostic summary.

    The screen is deliberately stricter than a positive pooled Rank IC.  It
    asks for enough non-overlapping cohorts, a positive overall association and
    descriptive TopK spread, plus a positive mean Rank IC in every observed
    calendar year.  Passing this screen records a hypothesis worth a separate,
    predeclared strategy test; it never selects or promotes a strategy.
    """

    if minimum_calendar_years < 1 or minimum_cohorts < 1:
        raise ValueError("minimum_calendar_years and minimum_cohorts must both be positive")
    annual = dict(summary.get("by_signal_year") or {})
    annual_mean_rank_ic: dict[str, float | None] = {}
    for year, metrics in sorted(annual.items()):
        value = (metrics or {}).get("mean_rank_ic") if isinstance(metrics, dict) else None
        annual_mean_rank_ic[str(year)] = float(value) if value is not None and np.isfinite(value) else None
    failures: list[str] = []
    cohorts = int(summary.get("cohorts") or 0)
    mean_rank_ic = summary.get("mean_rank_ic")
    positive_rank_ic_rate = summary.get("positive_rank_ic_rate")
    spread = summary.get("mean_top_minus_bottom_gross_return")
    if cohorts < minimum_cohorts:
        failures.append(f"fewer than {minimum_cohorts} non-overlapping cohorts")
    if len(annual_mean_rank_ic) < minimum_calendar_years:
        failures.append(f"fewer than {minimum_calendar_years} observed calendar years")
    if mean_rank_ic is None or not np.isfinite(mean_rank_ic) or float(mean_rank_ic) <= 0.0:
        failures.append("non-positive pooled mean Rank IC")
    if positive_rank_ic_rate is None or not np.isfinite(positive_rank_ic_rate) or float(positive_rank_ic_rate) <= 0.50:
        failures.append("positive Rank IC rate is not above 50%")
    if spread is None or not np.isfinite(spread) or float(spread) <= 0.0:
        failures.append("non-positive mean TopK-minus-BottomK gross spread")
    non_positive_years = [
        year for year, value in annual_mean_rank_ic.items() if value is None or value <= 0.0
    ]
    if non_positive_years:
        failures.append("non-positive annual mean Rank IC: " + ", ".join(non_positive_years))
    return {
        "factor": str(summary.get("factor", "")),
        "passed": not failures,
        "failures": failures,
        "observed_calendar_years": list(annual_mean_rank_ic),
        "annual_mean_rank_ic": annual_mean_rank_ic,
        "metrics": {
            "cohorts": cohorts,
            "mean_rank_ic": None if mean_rank_ic is None else float(mean_rank_ic),
            "positive_rank_ic_rate": None if positive_rank_ic_rate is None else float(positive_rank_ic_rate),
            "mean_top_minus_bottom_gross_return": None if spread is None else float(spread),
        },
        "criteria": {
            "minimum_calendar_years": minimum_calendar_years,
            "minimum_cohorts": minimum_cohorts,
            "mean_rank_ic_gt": 0.0,
            "positive_rank_ic_rate_gt": 0.50,
            "mean_top_minus_bottom_gross_return_gt": 0.0,
            "every_observed_calendar_year_mean_rank_ic_gt": 0.0,
        },
    }


def factor_topk_viability_decision(
    summary: dict[str, Any],
    *,
    minimum_calendar_years: int = FACTOR_STABILITY_MIN_CALENDAR_YEARS,
    minimum_cohorts: int = FACTOR_STABILITY_MIN_COHORTS,
) -> dict[str, Any]:
    """Screen a stable single factor as the exact diagnostic TopK basket.

    A Rank IC measures a cross-sectional relationship, not whether repeatedly
    holding the TopK names can survive costs and drawdowns.  This second screen
    therefore requires the association screen first, then applies the same
    three-day TopK timing and costs retained in the diagnostic.  It remains a
    development-only rejection/triage tool rather than a strategy promotion
    mechanism.
    """

    association = factor_stability_decision(
        summary,
        minimum_calendar_years=minimum_calendar_years,
        minimum_cohorts=minimum_cohorts,
    )
    topk = dict(summary.get("topk") or {})
    annual = dict(summary.get("by_signal_year") or {})
    annual_topk_net_returns: dict[str, float | None] = {}
    for year, metrics in sorted(annual.items()):
        value = (metrics or {}).get("topk_net_cumulative_return") if isinstance(metrics, dict) else None
        annual_topk_net_returns[str(year)] = float(value) if value is not None and np.isfinite(value) else None
    failures = [f"association screen failed: {failure}" for failure in association["failures"]]
    rounds = int(topk.get("rounds") or 0)
    net_return = topk.get("net_cumulative_return")
    max_drawdown = topk.get("max_drawdown")
    if rounds < minimum_cohorts:
        failures.append(f"fewer than {minimum_cohorts} executable TopK cohorts")
    if net_return is None or not np.isfinite(net_return) or float(net_return) <= 0.0:
        failures.append("non-positive TopK net cumulative return after diagnostic costs")
    if max_drawdown is None or not np.isfinite(max_drawdown) or float(max_drawdown) < STRICT_DEVELOPMENT_MAX_DRAWDOWN:
        failures.append(f"TopK maximum drawdown worse than {STRICT_DEVELOPMENT_MAX_DRAWDOWN:.0%}")
    non_positive_years = [
        year for year, value in annual_topk_net_returns.items() if value is None or value <= 0.0
    ]
    if non_positive_years:
        failures.append("non-positive annual TopK net cumulative return: " + ", ".join(non_positive_years))
    return {
        "factor": str(summary.get("factor", "")),
        "passed": not failures,
        "association_screen_passed": association["passed"],
        "failures": failures,
        "observed_calendar_years": list(annual_topk_net_returns),
        "annual_topk_net_cumulative_return": annual_topk_net_returns,
        "topk_metrics": {
            "rounds": rounds,
            "net_cumulative_return": None if net_return is None else float(net_return),
            "max_drawdown": None if max_drawdown is None else float(max_drawdown),
            "median_holdings": topk.get("median_holdings"),
        },
        "criteria": {
            "requires_factor_association_stability_screen": True,
            "minimum_executable_topk_cohorts": minimum_cohorts,
            "topk_net_cumulative_return_gt": 0.0,
            "topk_max_drawdown_gte": STRICT_DEVELOPMENT_MAX_DRAWDOWN,
            "every_observed_calendar_year_topk_net_cumulative_return_gt": 0.0,
        },
    }


def choose_winner(summaries: list[dict[str, Any]], selection_policy: str = "pooled_return_drawdown") -> str | None:
    """Choose only from development-period results; reject missing metrics."""

    if selection_policy not in SELECTION_POLICIES:
        choices = ", ".join(sorted(SELECTION_POLICIES))
        raise ValueError(f"unknown selection_policy {selection_policy!r}; choose one of: {choices}")

    def score(item: dict[str, Any]) -> Any:
        return development_selection_score(item, selection_policy)

    eligible = [item for item in summaries if score(item) is not None]
    if not eligible:
        return None
    winner = max(eligible, key=lambda item: float(score(item)))
    return str(winner["candidate"])


def development_selection_score(item: dict[str, Any], selection_policy: str) -> float | None:
    """Read one development-only score with the original-policy fallback."""

    if selection_policy not in SELECTION_POLICIES:
        choices = ", ".join(sorted(SELECTION_POLICIES))
        raise ValueError(f"unknown selection_policy {selection_policy!r}; choose one of: {choices}")
    scores = item.get("selection_scores") or {}
    score = scores.get(selection_policy)
    if selection_policy == "pooled_return_drawdown" and score is None:
        score = item.get("development_selection_score")
    return None if score is None else float(score)


def summarize_development_window(rounds: pd.DataFrame, hold_days: int) -> dict[str, Any]:
    """Calculate the precommitted selection fields for an arbitrary completed cohort window.

    Walk-forward selection needs exactly the same annual-stability and drawdown
    logic as a normal study, but its training window changes by fold.  Keeping
    this calculation in one helper makes it explicit that only completed
    cohorts in the fold's historical window may choose a candidate.
    """

    development = return_metrics(rounds, hold_days)
    by_year = {
        str(year): return_metrics(group, hold_days)
        for year, group in rounds.groupby(rounds["signal_date"].dt.year, sort=True)
    }
    year_returns = [
        float(metrics["net_cumulative_return"])
        for metrics in by_year.values()
        if metrics.get("net_cumulative_return") is not None
    ]
    stability_score = positive_year_stability_score(year_returns, development.get("max_drawdown"))
    strict_stability_score = stability_score_with_drawdown_cap(
        stability_score,
        development.get("max_drawdown"),
    )
    return {
        "development": development,
        "development_by_signal_year": by_year,
        "development_stability": {
            "calendar_year_count": len(year_returns),
            "positive_calendar_year_count": sum(value > 0.0 for value in year_returns),
            "worst_calendar_year_net_cumulative_return": min(year_returns) if year_returns else None,
            "selection_score": stability_score,
            "max_drawdown_cap": STRICT_DEVELOPMENT_MAX_DRAWDOWN,
            "passes_max_drawdown_cap": strict_stability_score is not None,
        },
        "selection_scores": {
            "pooled_return_drawdown": (
                development["annualized_return"] - 0.5 * abs(development["max_drawdown"])
                if development["rounds"]
                else None
            ),
            "positive_year_stability": stability_score,
            "positive_year_stability_mdd20": strict_stability_score,
        },
    }


def completed_rounds_in_window(rounds: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Keep only signals whose scheduled exits are fully inside one historical window."""

    start = pd.Timestamp(start).normalize()
    end = pd.Timestamp(end).normalize()
    if end < start:
        raise ValueError("walk-forward window end must not precede its start")
    return rounds.loc[
        rounds["signal_date"].ge(start)
        & rounds["signal_date"].le(end)
        & rounds["exit_date"].le(end)
    ].copy()


def walk_forward_fold_result(
    candidate_rounds: dict[str, pd.DataFrame],
    *,
    train_start: pd.Timestamp,
    train_end: pd.Timestamp,
    test_start: pd.Timestamp,
    test_end: pd.Timestamp,
    hold_days: int,
    selection_policy: str,
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Select on one completed training window and return the untouched next-window cohorts."""

    if test_start <= train_end:
        raise ValueError("walk-forward test window must begin after its training window")
    candidates: list[dict[str, Any]] = []
    for candidate, rounds in candidate_rounds.items():
        training_rounds = completed_rounds_in_window(rounds, train_start, train_end)
        summary = summarize_development_window(training_rounds, hold_days)
        candidates.append({"candidate": candidate, **summary})
    winner = choose_winner(candidates, selection_policy)
    winner_summary = next((item for item in candidates if item["candidate"] == winner), None)
    test_rounds = (
        completed_rounds_in_window(candidate_rounds[winner], test_start, test_end)
        if winner is not None
        else pd.DataFrame()
    )
    return (
        {
            "train_start": pd.Timestamp(train_start).date().isoformat(),
            "train_end": pd.Timestamp(train_end).date().isoformat(),
            "test_start": pd.Timestamp(test_start).date().isoformat(),
            "test_end": pd.Timestamp(test_end).date().isoformat(),
            "candidate_count": len(candidates),
            "eligible_candidate_count": sum(
                development_selection_score(item, selection_policy) is not None for item in candidates
            ),
            "winner_selected_on_training_only": winner,
            "winner_training_selection_score": (
                development_selection_score(winner_summary, selection_policy) if winner_summary is not None else None
            ),
            "winner_training": winner_summary["development"] if winner_summary is not None else None,
            "winner_training_stability": (
                winner_summary["development_stability"] if winner_summary is not None else None
            ),
            "test": return_metrics(test_rounds, hold_days),
        },
        test_rounds,
    )


def rank_regimes_by_development(
    summaries: list[tuple[str, dict[str, Any]]], selection_policy: str
) -> list[tuple[str, dict[str, Any], float | None]]:
    """Rank predeclared market-state rules without consulting any test result."""

    ranked = [
        (regime_filter, summary, development_selection_score(summary, selection_policy))
        for regime_filter, summary in summaries
    ]
    return sorted(
        ranked,
        key=lambda item: float(item[2]) if item[2] is not None else float("-inf"),
        reverse=True,
    )


def candidate_by_name(name: str, library_id: str = "v1") -> Candidate:
    """Return a predefined candidate, rejecting arbitrary unrecorded weights."""

    for candidate in candidate_library(library_id):
        if candidate.name == name:
            return candidate
    choices = ", ".join(candidate.name for candidate in candidate_library(library_id))
    raise ValueError(f"unknown candidate {name!r} in {library_id}; choose one of: {choices}")


def latest_provider_date(provider_uri: Path) -> pd.Timestamp:
    """Read the latest local Qlib session without consulting a network source."""

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    import qlib
    from qlib.data import D

    provider_uri = provider_uri.expanduser().resolve()
    qlib.init(provider_uri=str(provider_uri), region="cn", kernels=1)
    calendar = pd.DatetimeIndex(D.calendar(freq="day"))
    if calendar.empty:
        raise RuntimeError("the local Qlib provider has no daily calendar")
    return pd.Timestamp(calendar[-1])


def _universe_metadata() -> dict[str, dict[str, Any]]:
    """Load latest local names and ST flags for an explicit screen safety filter."""

    path = DATA_ROOT / "metadata" / "universe_latest.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(item["symbol"]): {
            "name": str(item.get("name") or ""),
            "is_st": bool(item.get("is_st", False)),
        }
        for item in payload
    }


def filter_st_candidates(screen: pd.DataFrame, metadata: dict[str, dict[str, Any]], include_st: bool) -> pd.DataFrame:
    """Exclude current ST-tagged names by default from a buyable research screen."""

    if include_st:
        return screen
    is_st = screen["instrument"].map(lambda symbol: bool(metadata.get(symbol, {}).get("is_st", False)))
    return screen.loc[~is_st].copy()


def load_prospective_factor_registry(path: Path) -> dict[str, Any]:
    """Load the append-only registry for hypotheses formed after development."""

    path = path.expanduser()
    if not path.exists():
        return {"schema_version": 1, "registrations": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or not isinstance(payload.get("registrations"), list):
        raise ValueError("prospective factor registry has an unsupported schema")
    return payload


def prospective_vwap_source_record(path: Path) -> dict[str, Any]:
    """Verify and fingerprint the completed diagnostic that prompted the new direction."""

    source_path = path.expanduser().resolve()
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    require_diagnostic_price_basis(payload)
    catalog = list(payload.get("factor_catalog") or [])
    ranking = list(payload.get("ranking_by_development_rank_ic") or [])
    source_rows = [item for item in ranking if item.get("factor") == PROSPECTIVE_VWAP_SOURCE_FACTOR]
    if (
        payload.get("status") != "completed"
        or payload.get("run_id") != PROSPECTIVE_VWAP_SOURCE_RUN_ID
        or catalog != [PROSPECTIVE_VWAP_SOURCE_FACTOR]
        or len(source_rows) != 1
    ):
        raise ValueError(
            "prospective VWAP registration requires the completed isolated close_above_vwap_1 diagnostic"
        )
    calendar_end = pd.Timestamp((payload.get("data") or {}).get("calendar_end")).normalize()
    if (
        pd.isna(calendar_end)
        or calendar_end != pd.Timestamp("2025-12-31")
        or bool((payload.get("data") or {}).get("test_period_used_for_factor_design", True))
    ):
        raise ValueError("prospective VWAP source diagnostic must be the isolated development-only 2019-2025 run")
    mean_rank_ic = float(source_rows[0].get("mean_rank_ic"))
    if not np.isfinite(mean_rank_ic) or mean_rank_ic >= 0.0:
        raise ValueError("prospective VWAP source diagnostic does not contain the recorded negative direction")
    return {
        "run_id": str(payload["run_id"]),
        "path": str(source_path),
        "sha256": file_sha256(source_path),
        "factor_catalog": catalog,
        "calendar_end": calendar_end.date().isoformat(),
        "price_basis": (payload.get("data") or {}).get("price_basis"),
        "price_basis_manifest_sha256": (payload.get("data") or {}).get("price_basis_manifest_sha256"),
    }


def append_prospective_vwap_registration(
    path: Path,
    *,
    not_before: str,
    latest_observed: str | pd.Timestamp,
    source: dict[str, Any],
) -> dict[str, Any]:
    """Pre-register the fixed inverse direction only before its first eligible close exists."""

    start = pd.Timestamp(not_before).normalize()
    latest = pd.Timestamp(latest_observed).normalize()
    earliest = pd.Timestamp(PROSPECTIVE_VWAP_EARLIEST_NOT_BEFORE)
    if pd.isna(start) or pd.isna(latest):
        raise ValueError("prospective VWAP dates must be valid ISO dates")
    if start < earliest:
        raise ValueError(
            f"prospective VWAP not_before cannot precede {PROSPECTIVE_VWAP_EARLIEST_NOT_BEFORE}"
        )
    if start <= latest:
        raise ValueError("prospective VWAP not_before must be strictly later than the latest observed close")
    registry = load_prospective_factor_registry(path)
    known = {str(item.get("registration_id")) for item in registry["registrations"]}
    if PROSPECTIVE_VWAP_REGISTRATION_ID in known:
        raise ValueError(f"prospective factor registry already contains {PROSPECTIVE_VWAP_REGISTRATION_ID}")
    registry["registrations"].append(
        {
            "registration_id": PROSPECTIVE_VWAP_REGISTRATION_ID,
            "factor": PROSPECTIVE_VWAP_FACTOR,
            "source_factor": PROSPECTIVE_VWAP_SOURCE_FACTOR,
            "hypothesis": PROSPECTIVE_VWAP_HYPOTHESIS,
            "construction": "1 - percentile_rank($close/$vwap - 1) within the same signal close",
            "not_before": start.date().isoformat(),
            "latest_observed_at_registration": latest.date().isoformat(),
            "registered_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "source_diagnostic": dict(source),
            "data": {
                "price_basis": source.get("price_basis"),
                "price_basis_manifest_sha256": source.get("price_basis_manifest_sha256"),
            },
            "universe": "buyable_main_chinext; annual-quality eligible; current ST excluded",
            "strategy": {
                "holding_period_trading_days": PROSPECTIVE_VWAP_HOLD_DAYS,
                "topk": PROSPECTIVE_VWAP_TOPK,
                "open_cost": PROSPECTIVE_VWAP_OPEN_COST,
                "close_cost": PROSPECTIVE_VWAP_CLOSE_COST,
                "signal_timing": "signal at close; enter next local session open; exit third local session close",
                "rebalance_rule": "non-overlapping three-session grid anchored at the first local session on or after not_before",
            },
            "status": "research_only_forward_observation",
            "guardrails": [
                "No 2019-2025 inverse-direction backtest, diagnostic, candidate-library admission, or promotion.",
                "No signal date before not_before and no reconstruction of a missed historical signal date.",
                "Settled forward observations remain research evidence and cannot generate an execution plan.",
            ],
        }
    )
    _atomic_write_text(path, json.dumps(registry, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return registry


def prospective_vwap_registration(registry_path: Path, registration_id: str | None = None) -> dict[str, Any]:
    """Return one fixed forward registration, latest by default."""

    registrations = list(load_prospective_factor_registry(registry_path).get("registrations") or [])
    if registration_id is not None:
        registrations = [item for item in registrations if item.get("registration_id") == registration_id]
    if not registrations:
        detail = f" {registration_id}" if registration_id else ""
        raise ValueError(f"prospective factor registration not found:{detail}")
    registration = registrations[-1]
    require_record_price_basis(registration, record_kind="prospective factor registration")
    if registration.get("factor") != PROSPECTIVE_VWAP_FACTOR:
        raise ValueError("prospective monitor only accepts the fixed close_below_vwap_1 registration")
    return registration


def run_latest_screen(args: argparse.Namespace) -> dict[str, Any]:
    """Create an auditable latest-available candidate screen from local data."""

    candidate = candidate_by_name(args.candidate, args.candidate_library)
    provider_uri = Path(args.provider_uri).expanduser()
    fundamentals_path = Path(args.fundamentals).expanduser()
    latest_local_date = latest_provider_date(provider_uri)
    end = args.as_of or latest_local_date.date().isoformat()
    start = args.start or (pd.Timestamp(end) - pd.Timedelta(days=args.lookback_calendar_days)).date().isoformat()
    fundamentals = load_fundamentals(fundamentals_path)
    market = load_market_data(provider_uri, start=start, end=end, batch_size=args.batch_size)
    market = attach_quality_asof(market, fundamentals, max_age_days=args.max_quality_age_days)
    ranked = rank_factor_frame(market)
    scored = score_candidate(ranked, candidate)
    as_of = pd.Timestamp(scored["datetime"].max())
    latest_scored = scored.loc[scored["datetime"] == as_of].copy()
    screened_by_regime = apply_regime_filter(scored, args.regime_filter)
    regime_active = bool((screened_by_regime["datetime"] == as_of).any())
    screen = screened_by_regime.loc[screened_by_regime["datetime"] == as_of].sort_values(
        ["score", "instrument"], ascending=[False, True]
    )
    metadata = _universe_metadata()
    screen = filter_st_candidates(screen, metadata, include_st=args.include_st)
    screen = screen.head(args.topk).copy()
    if regime_active and len(screen) < args.topk:
        raise RuntimeError(f"only {len(screen)} complete candidates exist on {as_of.date()}, need {args.topk}")
    factor_columns = list(candidate.weights)
    records: list[dict[str, Any]] = []
    for rank, row in enumerate(screen.itertuples(index=False), start=1):
        records.append(
            {
                "rank": rank,
                "instrument": row.instrument,
                "name": str(metadata.get(row.instrument, {}).get("name", "")),
                "score": float(row.score),
                "reference_close": float(row.close),
                "roe": float(row.roe),
                "revenue_yoy": float(row.revenue_yoy),
                "profit_yoy": float(row.profit_yoy),
                "quality_report_date": pd.Timestamp(row.report_date).date().isoformat(),
                "quality_announcement_date": pd.Timestamp(row.announcement_date).date().isoformat(),
                "quality_age_days": int(row.quality_age_days),
                "factor_percentiles": {column: float(getattr(row, column)) for column in factor_columns},
            }
        )
    run_id = _timestamp()
    report = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "latest_available_research_screen_not_trade_instruction",
        "as_of": as_of.date().isoformat(),
        "latest_local_provider_date": latest_local_date.date().isoformat(),
        "candidate": candidate.name,
        "candidate_library": args.candidate_library,
        "description": candidate.description,
        "weights": candidate.weights,
        "regime_filter": args.regime_filter,
        "regime_filter_description": REGIME_FILTERS[args.regime_filter],
        "regime_active": regime_active,
        "execution_allowed": regime_active,
        "latest_market_breadth": {
            "five_day": float(latest_scored["market_breadth_5"].iloc[0]),
            "twenty_day": float(latest_scored["market_breadth_20"].iloc[0]),
        },
        "universe": "buyable_main_chinext",
        "exclude_current_st": not args.include_st,
        "topk": args.topk,
        "quality_gate": {
            "source": str(fundamentals_path.resolve()),
            "sha256": file_sha256(fundamentals_path),
            "annual_report_only": True,
            "effective_date": "strictly next local trading day after announcement_date",
        },
        "top_candidates": records,
        "limitations": [
            "This is a model screen using the latest locally available daily close, not a buy/sell instruction.",
            "It does not model intraday news, current-day limits, suspensions, lot-size constraints, tax, or order execution.",
            "A public financial-data snapshot and a current listing universe cannot eliminate accounting-restatement and survivorship bias.",
        ],
    }
    root = Path(args.experiment_root).expanduser()
    destination = root / f"{run_id}_screen_{candidate.name}.json"
    _atomic_write_text(destination, json.dumps(report, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    report["screen_path"] = str(destination.resolve())
    return report


def run_execution_plan(args: argparse.Namespace) -> dict[str, Any]:
    """Size a fresh model screen into auditable A-share board-lot plans."""

    screen_path = Path(args.screen_path).expanduser().resolve()
    screen = json.loads(screen_path.read_text(encoding="utf-8"))
    if screen.get("execution_allowed") is False:
        raise ValueError("screen regime is inactive; no order plan may be generated")
    candidates = list(screen.get("top_candidates") or [])[: args.topk]
    if not candidates:
        raise ValueError("screen file does not contain top_candidates")
    missing_prices = [str(item.get("instrument", "")) for item in candidates if "reference_close" not in item]
    if missing_prices:
        raise ValueError(
            "screen file lacks reference_close for "
            + ", ".join(missing_prices)
            + "; generate a new screen with the current script before planning"
        )
    rules = AShareExecutionRules(
        lot_size=args.lot_size,
        commission_rate=args.commission_rate,
        commission_min=args.commission_min,
        transfer_fee_rate=args.transfer_fee_rate,
        stamp_duty_rate=args.stamp_duty_rate,
        max_gross_exposure=args.max_gross_exposure,
        target_weight=args.target_weight,
    )
    capitals = tuple(args.capital) if args.capital else DEFAULT_PILOT_CAPITALS
    plans = [plan_lot_orders(candidates, capital, rules) for capital in capitals]
    report = {
        "run_id": _timestamp(),
        "status": "completed",
        "purpose": "research_execution_plan_not_trade_instruction",
        "source_screen": str(screen_path),
        "screen_as_of": screen.get("as_of"),
        "candidate": screen.get("candidate"),
        "candidate_count": len(candidates),
        "reference_price": "latest local daily close recorded in the source screen",
        "plans": plans,
        "fee_assumptions": {
            "commission": "0.01% per side by default (the user's stated RMB 1 per RMB 10,000), with no minimum by default",
            "transfer_fee": "0.002% per side by default",
            "stamp_duty": "0.05% on the sell side by default",
            "exchange_handling_fee": "not separately added to avoid double-counting an all-in broker commission quote",
        },
    }
    output = Path(args.output).expanduser() if args.output else screen_path.parent / f"{report['run_id']}_execution_plan.json"
    _atomic_write_text(output, json.dumps(report, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    report["plan_path"] = str(output.resolve())
    return report


def write_experiment_record(root: Path, record: dict[str, Any]) -> Path:
    """Persist one self-contained candidate result without overwriting history."""

    root.mkdir(parents=True, exist_ok=True)
    destination = root / f"{record['run_id']}_{record['candidate']}.json"
    _atomic_write_text(destination, json.dumps(record, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return destination


def initial_test_gate(metrics: dict[str, Any]) -> tuple[bool, list[str]]:
    """Apply a predeclared, deliberately modest promotion gate to test results."""

    failures: list[str] = []
    if int(metrics.get("rounds") or 0) < 20:
        failures.append("fewer than 20 independent test cohorts")
    if float(metrics.get("net_cumulative_return") or 0.0) <= 0.0:
        failures.append("non-positive test cumulative return")
    if float(metrics.get("max_drawdown") or 0.0) < -0.20:
        failures.append("test maximum drawdown worse than -20%")
    return not failures, failures


def build_iteration_record(
    *,
    run_id: str,
    label: str,
    strategy: dict[str, Any],
    study_path: Path,
    winner: dict[str, Any],
    candidate_count: int,
    data: dict[str, Any],
    promotion_eligible: bool = True,
    candidate_library_id: str = "v1",
    candidate_library_sha256: str | None = None,
    selection_policy: str = "pooled_return_drawdown",
) -> dict[str, Any]:
    """Build one immutable research-cycle record from a development-selected winner."""

    if selection_policy not in SELECTION_POLICIES:
        choices = ", ".join(sorted(SELECTION_POLICIES))
        raise ValueError(f"unknown selection_policy {selection_policy!r}; choose one of: {choices}")
    passed, failures = initial_test_gate(winner["test"])
    if not promotion_eligible:
        failures = [
            *failures,
            "research-only diagnostic is not eligible for promotion because its test window is not a newly reserved validation set",
        ]
    return {
        "iteration_id": run_id,
        "label": label,
        "candidate_library": {
            "id": candidate_library_id,
            "count": candidate_count,
            "fingerprint_sha256": candidate_library_sha256
            or candidate_library_fingerprint(candidate_library(candidate_library_id)),
        },
        "strategy": strategy,
        "data": data,
        "selection": {
            "rule": SELECTION_POLICIES[selection_policy],
            "policy": selection_policy,
            "test_metrics_used_for_selection": False,
            "winner": winner["candidate"],
            "development_selection_score": (winner.get("selection_scores") or {}).get(
                selection_policy, winner.get("development_selection_score")
            ),
            "development": winner["development"],
            "development_stability": winner.get("development_stability"),
        },
        "initial_test": winner["test"],
        "promotion": {
            "status": "passed_initial_test" if passed and promotion_eligible else "research_only_not_promoted",
            "eligible_for_promotion": promotion_eligible,
            "criteria": {
                "minimum_test_cohorts": 20,
                "net_cumulative_return_gt": 0.0,
                "max_drawdown_gte": -0.20,
            },
            "failures": failures,
        },
        "study_path": str(study_path.resolve()),
        "recording_rule": "Append-only registry; later factor iterations must create a new record and preserve this one.",
    }


def append_strategy_registry(registry_path: Path, iteration: dict[str, Any]) -> Path:
    """Append a completed research cycle without allowing historic replacement."""

    require_record_price_basis(iteration, record_kind="strategy iteration")
    registry_path = registry_path.expanduser()
    if registry_path.exists():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    else:
        registry = {"schema_version": 1, "iterations": []}
    if registry.get("schema_version") != 1 or not isinstance(registry.get("iterations"), list):
        raise ValueError("strategy registry has an unsupported schema")
    known_ids = {str(item.get("iteration_id")) for item in registry["iterations"]}
    if str(iteration["iteration_id"]) in known_ids:
        raise ValueError(f"strategy registry already contains iteration {iteration['iteration_id']}")
    registry["iterations"].append(iteration)
    _atomic_write_text(registry_path, json.dumps(registry, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return registry_path


def promoted_iteration(registry_path: Path, iteration_id: str | None = None) -> dict[str, Any]:
    """Load one passed-initial-test strategy, latest by default."""

    registry = json.loads(registry_path.expanduser().read_text(encoding="utf-8"))
    iterations = list(registry.get("iterations") or [])
    if iteration_id is not None:
        iterations = [item for item in iterations if item.get("iteration_id") == iteration_id]
    for iteration in reversed(iterations):
        if (
            iteration.get("promotion", {}).get("status") == "passed_initial_test"
            and uses_required_price_basis(iteration)
        ):
            return iteration
    detail = f" {iteration_id}" if iteration_id else ""
    raise ValueError(
        f"no passed_initial_test strategy with price_basis={REQUIRED_PRICE_BASIS} found in registry{detail}"
    )


def research_observation_iteration(registry_path: Path, iteration_id: str) -> dict[str, Any]:
    """Return one explicit development-only iteration for forward paper observation.

    This is deliberately separate from ``promoted_iteration``.  A shadow
    observation is research evidence only and cannot become an execution plan
    merely because the scheduler has collected a few returns.
    """

    registry = json.loads(registry_path.expanduser().read_text(encoding="utf-8"))
    iterations = [item for item in registry.get("iterations", []) if item.get("iteration_id") == iteration_id]
    if not iterations:
        raise ValueError(f"research iteration not found: {iteration_id}")
    iteration = iterations[-1]
    require_record_price_basis(iteration, record_kind="research-only strategy iteration")
    promotion = iteration.get("promotion") or {}
    data = iteration.get("data") or {}
    test = iteration.get("initial_test") or {}
    if promotion.get("status") != "research_only_not_promoted":
        raise ValueError("shadow observation only accepts a research-only iteration")
    if int(test.get("rounds") or 0) != 0 or data.get("calendar_end") != data.get("development_end"):
        raise ValueError("shadow observation requires an iteration with no historical test window")
    return iteration


def load_shadow_observation_registry(path: Path) -> dict[str, Any]:
    """Load the append-only list of development-only strategies under forward observation."""

    path = path.expanduser()
    if not path.exists():
        return {"schema_version": 1, "observations": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or not isinstance(payload.get("observations"), list):
        raise ValueError("shadow observation registry has an unsupported schema")
    return payload


def append_shadow_observation(
    path: Path, *, iteration: dict[str, Any], not_before: str
) -> dict[str, Any]:
    """Append one explicit future-only paper observation plan."""

    date = pd.Timestamp(not_before).normalize()
    if pd.isna(date):
        raise ValueError("not_before must be a valid ISO date")
    registry = load_shadow_observation_registry(path)
    known = {str(item.get("iteration_id")) for item in registry["observations"]}
    iteration_id = str(iteration["iteration_id"])
    if iteration_id in known:
        raise ValueError(f"shadow observation already contains iteration {iteration_id}")
    registry["observations"].append(
        {
            "iteration_id": iteration_id,
            "candidate": iteration["selection"]["winner"],
            "candidate_library": (iteration.get("strategy") or {}).get("candidate_library", "v1"),
            "not_before": date.date().isoformat(),
            "registered_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "data": {
                "price_basis": (iteration.get("data") or {}).get("price_basis"),
                "price_basis_manifest_sha256": (iteration.get("data") or {}).get(
                    "price_basis_manifest_sha256"
                ),
            },
            "rule": "Forward paper observation only; the date must be the first genuinely unseen signal close.",
        }
    )
    _atomic_write_text(path, json.dumps(registry, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return registry


def load_shadow_suspension_registry(path: Path) -> dict[str, Any]:
    """Load append-only suspensions for forward shadow observations."""

    path = path.expanduser()
    if not path.exists():
        return {"schema_version": 1, "suspensions": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or not isinstance(payload.get("suspensions"), list):
        raise ValueError("shadow suspension registry has an unsupported schema")
    return payload


def append_shadow_suspension(path: Path, *, iteration_id: str, reason: str) -> dict[str, Any]:
    """Append a suspension without rewriting the original forward registration."""

    cleaned_reason = str(reason).strip()
    if not cleaned_reason:
        raise ValueError("shadow suspension reason must not be blank")
    registry = load_shadow_suspension_registry(path)
    known = {str(item.get("iteration_id")) for item in registry["suspensions"]}
    if str(iteration_id) in known:
        raise ValueError(f"shadow observation {iteration_id} is already suspended")
    registry["suspensions"].append(
        {
            "iteration_id": str(iteration_id),
            "reason": cleaned_reason,
            "suspended_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "rule": "Suspension preserves the original registration and prevents new shadow signals until a corrected re-evaluation is registered.",
        }
    )
    _atomic_write_text(path, json.dumps(registry, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return registry


def local_trading_calendar(provider_uri: Path, end: str | None = None) -> pd.DatetimeIndex:
    """Read the local Qlib trading calendar without querying a network source."""

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    import qlib
    from qlib.data import D

    qlib.init(provider_uri=str(provider_uri.expanduser().resolve()), region="cn", kernels=1)
    calendar = pd.DatetimeIndex(D.calendar(start_time=None, end_time=end, freq="day"))
    return pd.DatetimeIndex(sorted(calendar.unique()))


def load_open_close_quotes(provider_uri: Path, instruments: list[str], start: str, end: str) -> pd.DataFrame:
    """Load the two close-known execution fields needed for paper settlement."""

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    import qlib
    from qlib.data import D

    if not instruments:
        return pd.DataFrame(columns=["instrument", "datetime", "open", "close"])
    qlib.init(provider_uri=str(provider_uri.expanduser().resolve()), region="cn", kernels=1)
    quotes = D.features(instruments, ["$open", "$close"], start_time=start, end_time=end, freq="day")
    return quotes.rename(columns={"$open": "open", "$close": "close"}).reset_index()


def load_paper_ledger(ledger_path: Path) -> dict[str, Any]:
    """Load the append-only signal and settlement ledger, creating its schema in memory if absent."""

    ledger_path = ledger_path.expanduser()
    if not ledger_path.exists():
        return {"schema_version": 1, "signals": [], "settlements": []}
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    if ledger.get("schema_version") != 1:
        raise ValueError("paper ledger has an unsupported schema")
    if not isinstance(ledger.get("signals"), list) or not isinstance(ledger.get("settlements"), list):
        raise ValueError("paper ledger is missing signals or settlements")
    return ledger


def paper_settlement(
    signal: dict[str, Any], calendar: pd.DatetimeIndex, quotes: pd.DataFrame
) -> dict[str, Any] | None:
    """Settle a paper signal only when all required future local sessions are available."""

    signal_date = pd.Timestamp(signal["signal_date"])
    matching = np.flatnonzero(calendar == signal_date)
    hold_days = int(signal["strategy"]["holding_period_trading_days"])
    if len(matching) != 1 or matching[0] + hold_days >= len(calendar):
        return None
    entry_date = calendar[matching[0] + 1]
    exit_date = calendar[matching[0] + hold_days]
    instruments = [str(item["instrument"]) for item in signal["top_candidates"]]
    entry = quotes.loc[quotes["datetime"] == entry_date, ["instrument", "open"]].rename(columns={"open": "entry_open"})
    exit_quote = quotes.loc[quotes["datetime"] == exit_date, ["instrument", "close"]].rename(columns={"close": "exit_close"})
    members = pd.DataFrame({"instrument": instruments}).merge(entry, on="instrument", how="left").merge(
        exit_quote, on="instrument", how="left"
    )
    members = members.dropna(subset=["entry_open", "exit_close"])
    members = members.loc[(members["entry_open"] > 0) & (members["exit_close"] > 0)].copy()
    minimum_holdings = minimum_required_holdings(len(instruments))
    if len(members) < minimum_holdings:
        return None
    members["gross_return"] = members["exit_close"] / members["entry_open"] - 1.0
    strategy = signal["strategy"]
    members["net_return"] = (
        (1.0 - float(strategy["open_cost"]))
        * (1.0 + members["gross_return"])
        * (1.0 - float(strategy["close_cost"]))
        - 1.0
    )
    return {
        "signal_id": signal["signal_id"],
        "signal_date": signal["signal_date"],
        "entry_date": entry_date.date().isoformat(),
        "exit_date": exit_date.date().isoformat(),
        "holdings": int(len(members)),
        "gross_return": float(members["gross_return"].mean()),
        "net_return": float(members["net_return"].mean()),
        "member_returns": [
            {
                "instrument": str(row.instrument),
                "entry_open": float(row.entry_open),
                "exit_close": float(row.exit_close),
                "gross_return": float(row.gross_return),
                "net_return": float(row.net_return),
            }
            for row in members.itertuples(index=False)
        ],
    }


def run_paper_monitor(args: argparse.Namespace) -> dict[str, Any]:
    """Append new eligible paper signals and settle older three-day signals."""

    # A promoted result's historical test window is still already-observed
    # evidence.  Do not let a bare monitor invocation silently turn its final
    # historical date into a paper signal; the caller must record the first
    # genuinely unseen signal close before the ledger is touched.
    not_before = getattr(args, "not_before", None)
    if not_before is None:
        raise ValueError(
            "paper monitor requires --not-before with the first genuinely unseen signal-close date"
        )
    not_before_date = pd.Timestamp(not_before).normalize()
    if pd.isna(not_before_date):
        raise ValueError("paper monitor --not-before must be a valid ISO date")
    provider_uri = Path(args.provider_uri).expanduser()
    registry_path = Path(args.registry_path).expanduser()
    ledger_path = Path(args.ledger_path).expanduser()
    if getattr(args, "allow_research_only", False):
        if not args.iteration_id:
            raise ValueError("research-only paper observation requires --iteration-id")
        iteration = research_observation_iteration(registry_path, args.iteration_id)
    else:
        iteration = promoted_iteration(registry_path, args.iteration_id)
    strategy = dict(iteration["strategy"])
    candidate = str(iteration["selection"]["winner"])
    latest_date = pd.Timestamp(args.as_of) if args.as_of else latest_provider_date(provider_uri)
    if latest_date.normalize() < not_before_date:
        return {
            "status": "not_started",
            "as_of": latest_date.date().isoformat(),
            "iteration_id": iteration["iteration_id"],
            "not_before": not_before_date.date().isoformat(),
            "reason": "forward observation begins only on the registered unseen signal date",
        }
    calendar = local_trading_calendar(provider_uri, end=latest_date.date().isoformat())
    ledger = load_paper_ledger(ledger_path)
    settled_ids = {str(item.get("signal_id")) for item in ledger["settlements"]}
    new_settlements: list[dict[str, Any]] = []
    for signal in ledger["signals"]:
        if str(signal.get("iteration_id")) != str(iteration["iteration_id"]):
            continue
        signal_id = str(signal.get("signal_id"))
        if signal_id in settled_ids:
            continue
        instruments = [str(item["instrument"]) for item in signal.get("top_candidates", [])]
        quotes = load_open_close_quotes(
            provider_uri,
            instruments,
            start=str(signal["signal_date"]),
            end=latest_date.date().isoformat(),
        )
        settlement = paper_settlement(signal, calendar, quotes)
        if settlement is not None:
            new_settlements.append(settlement)
    ledger["settlements"].extend(new_settlements)

    screen_args = argparse.Namespace(
        provider_uri=str(provider_uri),
        fundamentals=args.fundamentals,
        experiment_root=args.experiment_root,
        candidate=candidate,
        candidate_library=strategy.get("candidate_library", "v1"),
        regime_filter=strategy["regime_filter"],
        as_of=latest_date.date().isoformat(),
        start=None,
        lookback_calendar_days=args.lookback_calendar_days,
        topk=int(strategy["topk"]),
        include_st=False,
        max_quality_age_days=args.max_quality_age_days,
        batch_size=args.batch_size,
    )
    screen = run_latest_screen(screen_args)
    signal_id = f"{iteration['iteration_id']}:{screen['as_of']}"
    known_signal_ids = {str(item.get("signal_id")) for item in ledger["signals"]}
    new_signal: dict[str, Any] | None = None
    if screen["execution_allowed"] and signal_id not in known_signal_ids:
        new_signal = {
            "signal_id": signal_id,
            "iteration_id": iteration["iteration_id"],
            "candidate": candidate,
            "signal_date": screen["as_of"],
            "strategy": strategy,
            "screen_path": screen["screen_path"],
            "top_candidates": screen["top_candidates"],
            "recording_rule": "Paper-only signal; entry and exit are settled only after future local daily bars exist.",
        }
        ledger["signals"].append(new_signal)
    _atomic_write_text(ledger_path, json.dumps(ledger, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return {
        "status": "completed",
        "as_of": latest_date.date().isoformat(),
        "iteration_id": iteration["iteration_id"],
        "candidate": candidate,
        "regime_filter": strategy["regime_filter"],
        "screen_path": screen["screen_path"],
        "execution_allowed": screen["execution_allowed"],
        "new_signal": new_signal,
        "new_settlements": new_settlements,
        "ledger_path": str(ledger_path.resolve()),
    }


def register_prospective_vwap_factor(args: argparse.Namespace) -> dict[str, Any]:
    """Record the post-diagnostic inverse direction before any eligible close is observed."""

    provider_uri = Path(args.provider_uri).expanduser()
    registry_path = Path(args.prospective_registry_path).expanduser()
    source = prospective_vwap_source_record(Path(args.source_diagnostic))
    latest = latest_provider_date(provider_uri).normalize()
    registry = append_prospective_vwap_registration(
        registry_path,
        not_before=args.not_before,
        latest_observed=latest,
        source=source,
    )
    registration = registry["registrations"][-1]
    return {
        "status": "completed",
        "registration_id": registration["registration_id"],
        "factor": registration["factor"],
        "not_before": registration["not_before"],
        "latest_observed_at_registration": registration["latest_observed_at_registration"],
        "source_diagnostic": source,
        "prospective_registry_path": str(registry_path.resolve()),
        "recording_rule": "Pure forward observation only; no historical inverse-direction evaluation or signal backfill.",
    }


def prospective_rebalance_due(
    calendar: pd.DatetimeIndex,
    *,
    not_before: str | pd.Timestamp,
    as_of: str | pd.Timestamp,
    hold_days: int,
) -> bool:
    """Return whether the latest close is on the fixed, non-overlapping forward grid."""

    if hold_days < 1:
        raise ValueError("prospective hold_days must be positive")
    normalized = pd.DatetimeIndex(pd.to_datetime(calendar)).normalize().unique().sort_values()
    start = pd.Timestamp(not_before).normalize()
    latest = pd.Timestamp(as_of).normalize()
    start_position = int(normalized.searchsorted(start, side="left"))
    matching = np.flatnonzero(normalized == latest)
    if start_position >= len(normalized) or len(matching) != 1 or matching[0] < start_position:
        return False
    return (int(matching[0]) - start_position) % hold_days == 0


def run_prospective_vwap_screen(
    args: argparse.Namespace,
    *,
    registration: dict[str, Any],
    as_of: pd.Timestamp,
) -> dict[str, Any]:
    """Rank only the current registered forward close; never evaluate prior outcomes."""

    provider_uri = Path(args.provider_uri).expanduser()
    fundamentals_path = Path(args.fundamentals).expanduser()
    end = as_of.date().isoformat()
    start = (as_of - pd.Timedelta(days=args.lookback_calendar_days)).date().isoformat()
    fundamentals = load_fundamentals(fundamentals_path)
    market = load_market_data(provider_uri, start=start, end=end, batch_size=args.batch_size)
    market = attach_quality_asof(market, fundamentals, max_age_days=args.max_quality_age_days)
    ranked = add_prospective_vwap_reversal_factor(rank_factor_frame(market))
    latest = ranked.loc[
        ranked["datetime"].eq(as_of)
        & ranked["quality_eligible"].fillna(False)
        & ranked[PROSPECTIVE_VWAP_FACTOR].notna()
    ].copy()
    metadata = _universe_metadata()
    latest = filter_st_candidates(latest, metadata, include_st=False)
    topk = int(registration["strategy"]["topk"])
    screen = latest.sort_values(
        [PROSPECTIVE_VWAP_FACTOR, "instrument"], ascending=[False, True], kind="stable"
    ).head(topk)
    if len(screen) < topk:
        raise RuntimeError(f"only {len(screen)} complete prospective candidates exist on {end}, need {topk}")
    records: list[dict[str, Any]] = []
    for rank, row in enumerate(screen.itertuples(index=False), start=1):
        records.append(
            {
                "rank": rank,
                "instrument": str(row.instrument),
                "name": str(metadata.get(str(row.instrument), {}).get("name", "")),
                "score": float(getattr(row, PROSPECTIVE_VWAP_FACTOR)),
                "close_above_vwap_percentile": float(getattr(row, PROSPECTIVE_VWAP_SOURCE_FACTOR)),
                "reference_close": float(row.close),
                "roe": float(row.roe),
                "revenue_yoy": float(row.revenue_yoy),
                "profit_yoy": float(row.profit_yoy),
                "quality_report_date": pd.Timestamp(row.report_date).date().isoformat(),
                "quality_announcement_date": pd.Timestamp(row.announcement_date).date().isoformat(),
                "quality_age_days": int(row.quality_age_days),
            }
        )
    report = {
        "run_id": _timestamp(),
        "status": "completed",
        "purpose": "registered_future_only_factor_screen_not_trade_instruction",
        "registration_id": registration["registration_id"],
        "factor": PROSPECTIVE_VWAP_FACTOR,
        "hypothesis": registration["hypothesis"],
        "as_of": end,
        "not_before": registration["not_before"],
        "historical_backfill": False,
        "historical_inverse_evaluation": False,
        "universe": registration["universe"],
        "exclude_current_st": True,
        "topk": topk,
        "execution_allowed": False,
        "quality_gate": {
            "source": str(fundamentals_path.resolve()),
            "sha256": file_sha256(fundamentals_path),
            "annual_report_only": True,
            "effective_date": "strictly next local trading day after announcement_date",
        },
        "top_candidates": records,
        "limitations": [
            "This is one immutable forward paper signal, not a buy/sell instruction or a promoted strategy.",
            "No historical result for close_below_vwap_1 was calculated when producing this screen.",
            "The current listing universe retains survivorship bias and daily bars cannot reproduce intraday execution.",
        ],
    }
    root = Path(args.experiment_root).expanduser()
    destination = root / f"{report['run_id']}_prospective_screen_{PROSPECTIVE_VWAP_FACTOR}.json"
    _atomic_write_text(destination, json.dumps(report, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    report["screen_path"] = str(destination.resolve())
    return report


def run_prospective_vwap_monitor(args: argparse.Namespace) -> dict[str, Any]:
    """Append current-close signals and future settlements for the registered inverse direction."""

    provider_uri = Path(args.provider_uri).expanduser()
    registry_path = Path(args.prospective_registry_path).expanduser()
    ledger_path = Path(args.prospective_ledger_path).expanduser()
    registration = prospective_vwap_registration(registry_path, args.registration_id)
    latest = latest_provider_date(provider_uri).normalize()
    not_before = pd.Timestamp(registration["not_before"]).normalize()
    registered_latest = pd.Timestamp(registration["latest_observed_at_registration"]).normalize()
    if not_before <= registered_latest:
        raise ValueError("prospective registration is invalid because its start was not genuinely unseen")
    if latest < not_before:
        return {
            "status": "not_started",
            "as_of": latest.date().isoformat(),
            "registration_id": registration["registration_id"],
            "factor": registration["factor"],
            "not_before": not_before.date().isoformat(),
            "ledger_written": False,
            "reason": "forward observation begins only on the registered unseen signal date",
        }
    calendar = local_trading_calendar(provider_uri, end=latest.date().isoformat())
    ledger = load_paper_ledger(ledger_path)
    settled_ids = {str(item.get("signal_id")) for item in ledger["settlements"]}
    new_settlements: list[dict[str, Any]] = []
    for signal in ledger["signals"]:
        if str(signal.get("registration_id")) != str(registration["registration_id"]):
            continue
        signal_id = str(signal.get("signal_id"))
        if signal_id in settled_ids:
            continue
        instruments = [str(item["instrument"]) for item in signal.get("top_candidates", [])]
        quotes = load_open_close_quotes(
            provider_uri,
            instruments,
            start=str(signal["signal_date"]),
            end=latest.date().isoformat(),
        )
        settlement = paper_settlement(signal, calendar, quotes)
        if settlement is not None:
            new_settlements.append(settlement)
    ledger["settlements"].extend(new_settlements)

    strategy = dict(registration["strategy"])
    signal_due = prospective_rebalance_due(
        calendar,
        not_before=not_before,
        as_of=latest,
        hold_days=int(strategy["holding_period_trading_days"]),
    )
    signal_id = f"{registration['registration_id']}:{latest.date().isoformat()}"
    known_signal_ids = {str(item.get("signal_id")) for item in ledger["signals"]}
    new_signal: dict[str, Any] | None = None
    screen: dict[str, Any] | None = None
    if signal_due and signal_id not in known_signal_ids:
        screen = run_prospective_vwap_screen(args, registration=registration, as_of=latest)
        new_signal = {
            "signal_id": signal_id,
            "registration_id": registration["registration_id"],
            "factor": registration["factor"],
            "signal_date": latest.date().isoformat(),
            "strategy": strategy,
            "screen_path": screen["screen_path"],
            "top_candidates": screen["top_candidates"],
            "recording_rule": "Current-close forward paper signal only; missed dates are never reconstructed.",
        }
        ledger["signals"].append(new_signal)
    ledger_written = bool(new_signal or new_settlements)
    if ledger_written:
        _atomic_write_text(ledger_path, json.dumps(ledger, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return {
        "status": "completed",
        "as_of": latest.date().isoformat(),
        "registration_id": registration["registration_id"],
        "factor": registration["factor"],
        "signal_due": signal_due,
        "signal_already_recorded": signal_due and signal_id in known_signal_ids,
        "new_signal": new_signal,
        "new_settlements": new_settlements,
        "screen_path": screen["screen_path"] if screen else None,
        "ledger_written": ledger_written,
        "prospective_ledger_path": str(ledger_path.resolve()),
        "recording_rule": "Latest local close only; no historical signal backfill and no execution-plan eligibility.",
    }


def register_shadow_observation(args: argparse.Namespace) -> dict[str, Any]:
    """Register a development-only candidate for a future, separate paper ledger."""

    iteration = research_observation_iteration(Path(args.registry_path), args.iteration_id)
    path = Path(args.shadow_registry_path)
    registry = append_shadow_observation(path, iteration=iteration, not_before=args.not_before)
    return {
        "status": "completed",
        "iteration_id": iteration["iteration_id"],
        "candidate": iteration["selection"]["winner"],
        "not_before": registry["observations"][-1]["not_before"],
        "shadow_registry_path": str(path.expanduser().resolve()),
        "recording_rule": "Forward paper observation only; this does not promote or enable an execution plan.",
    }


def suspend_shadow_observation(args: argparse.Namespace) -> dict[str, Any]:
    """Suspend a registered forward observation pending a documented review."""

    iteration = research_observation_iteration(Path(args.registry_path), args.iteration_id)
    observations = load_shadow_observation_registry(Path(args.shadow_registry_path))
    registered = {str(item.get("iteration_id")) for item in observations["observations"]}
    if str(iteration["iteration_id"]) not in registered:
        raise ValueError("shadow suspension requires an existing forward observation registration")
    path = Path(args.shadow_suspension_registry_path)
    registry = append_shadow_suspension(path, iteration_id=str(iteration["iteration_id"]), reason=args.reason)
    return {
        "status": "suspended",
        "iteration_id": str(iteration["iteration_id"]),
        "candidate": iteration["selection"]["winner"],
        "reason": registry["suspensions"][-1]["reason"],
        "shadow_suspension_registry_path": str(path.expanduser().resolve()),
        "recording_rule": "The original forward registration is preserved, but shadow-monitor will not create new signals for this iteration.",
    }


def run_shadow_monitor(args: argparse.Namespace) -> dict[str, Any]:
    """Collect forward paper evidence for every explicitly registered research candidate."""

    plan_path = Path(args.shadow_registry_path)
    plan = load_shadow_observation_registry(plan_path)
    suspension_path = Path(
        getattr(args, "shadow_suspension_registry_path", DEFAULT_SHADOW_SUSPENSION_REGISTRY)
    )
    suspension_registry = load_shadow_suspension_registry(suspension_path)
    suspensions = {str(item.get("iteration_id")): item for item in suspension_registry["suspensions"]}
    if not plan["observations"]:
        return {
            "status": "completed",
            "observations": [],
            "message": "no forward shadow observations are registered",
            "shadow_registry_path": str(plan_path.expanduser().resolve()),
        }
    reports: list[dict[str, Any]] = []
    for observation in plan["observations"]:
        iteration_id = str(observation["iteration_id"])
        if iteration_id in suspensions:
            reports.append(
                {
                    "status": "suspended",
                    "iteration_id": iteration_id,
                    "candidate": observation.get("candidate"),
                    "reason": suspensions[iteration_id].get("reason"),
                }
            )
            continue
        monitor_args = argparse.Namespace(**vars(args))
        monitor_args.iteration_id = iteration_id
        monitor_args.ledger_path = args.shadow_ledger_path
        monitor_args.allow_research_only = True
        monitor_args.not_before = str(observation["not_before"])
        reports.append(run_paper_monitor(monitor_args))
    return {
        "status": "completed",
        "observation_count": len(reports),
        "observations": reports,
        "shadow_registry_path": str(plan_path.expanduser().resolve()),
        "shadow_suspension_registry_path": str(suspension_path.expanduser().resolve()),
        "shadow_ledger_path": str(Path(args.shadow_ledger_path).expanduser().resolve()),
        "recording_rule": "Separate forward paper evidence for research-only candidates; never an execution recommendation.",
    }


def _percent(value: Any) -> str:
    """Format an optional decimal return for the human research log."""

    return "—" if value is None else f"{float(value):+.2%}"


def _paper_ledger_summary(ledger: dict[str, Any]) -> tuple[int, int, int, float]:
    """Return signal, settlement, pending and compounded-return counts for one ledger."""

    settlements = list(ledger.get("settlements") or [])
    signals = list(ledger.get("signals") or [])
    settled_ids = {str(item.get("signal_id")) for item in settlements}
    pending = [item for item in signals if str(item.get("signal_id")) not in settled_ids]
    equity = float(np.prod([1.0 + float(item["net_return"]) for item in settlements]) - 1.0) if settlements else 0.0
    return len(signals), len(settlements), len(pending), equity


def filter_paper_ledger(
    ledger: dict[str, Any], *, identity_field: str, accepted_ids: set[str]
) -> dict[str, Any]:
    """Retain only signals whose immutable source record has an accepted basis."""

    signals = [
        item for item in ledger.get("signals") or [] if str(item.get(identity_field)) in accepted_ids
    ]
    signal_ids = {str(item.get("signal_id")) for item in signals}
    settlements = [
        item for item in ledger.get("settlements") or [] if str(item.get("signal_id")) in signal_ids
    ]
    return {"schema_version": ledger.get("schema_version", 1), "signals": signals, "settlements": settlements}


def _shadow_observation_rows(
    plan: dict[str, Any],
    ledger: dict[str, Any],
    suspension_registry: dict[str, Any] | None = None,
    valid_iteration_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Summarize separate forward evidence for each explicitly registered candidate."""

    signals = list(ledger.get("signals") or [])
    settlements = list(ledger.get("settlements") or [])
    suspended = {
        str(item.get("iteration_id")) for item in (suspension_registry or {}).get("suspensions") or []
    }
    rows: list[dict[str, Any]] = []
    for observation in plan.get("observations") or []:
        iteration_id = str(observation.get("iteration_id", ""))
        basis_valid = valid_iteration_ids is None or iteration_id in valid_iteration_ids
        candidate_signals = [
            item for item in signals if basis_valid and str(item.get("iteration_id")) == iteration_id
        ]
        signal_ids = {str(item.get("signal_id")) for item in candidate_signals}
        candidate_settlements = [item for item in settlements if str(item.get("signal_id")) in signal_ids]
        settled_ids = {str(item.get("signal_id")) for item in candidate_settlements}
        pending = [item for item in candidate_signals if str(item.get("signal_id")) not in settled_ids]
        equity = (
            float(np.prod([1.0 + float(item["net_return"]) for item in candidate_settlements]) - 1.0)
            if candidate_settlements
            else 0.0
        )
        rows.append(
            {
                "iteration_id": iteration_id,
                "candidate": str(observation.get("candidate", "—")),
                "candidate_library": str(observation.get("candidate_library", "—")),
                "not_before": str(observation.get("not_before", "—")),
                "status": (
                    "价格基准失效"
                    if not basis_valid
                    else "已暂停"
                    if iteration_id in suspended
                    else "前瞻观察中"
                ),
                "signals": len(candidate_signals),
                "settlements": len(candidate_settlements),
                "pending": len(pending),
                "net_cumulative_return": equity,
            }
        )
    return rows


def _prospective_factor_rows(
    registry: dict[str, Any], ledger: dict[str, Any], valid_registration_ids: set[str] | None = None
) -> list[dict[str, Any]]:
    """Summarize each post-development factor without mixing its returns into another strategy."""

    signals = list(ledger.get("signals") or [])
    settlements = list(ledger.get("settlements") or [])
    rows: list[dict[str, Any]] = []
    for registration in registry.get("registrations") or []:
        registration_id = str(registration.get("registration_id", ""))
        basis_valid = valid_registration_ids is None or registration_id in valid_registration_ids
        factor_signals = [
            item
            for item in signals
            if basis_valid and str(item.get("registration_id")) == registration_id
        ]
        signal_ids = {str(item.get("signal_id")) for item in factor_signals}
        factor_settlements = [item for item in settlements if str(item.get("signal_id")) in signal_ids]
        settled_ids = {str(item.get("signal_id")) for item in factor_settlements}
        equity = (
            float(np.prod([1.0 + float(item["net_return"]) for item in factor_settlements]) - 1.0)
            if factor_settlements
            else 0.0
        )
        rows.append(
            {
                "registration_id": registration_id,
                "factor": str(registration.get("factor", "—")),
                "not_before": str(registration.get("not_before", "—")),
                "source_run_id": str((registration.get("source_diagnostic") or {}).get("run_id", "—")),
                "status": "有效" if basis_valid else "价格基准失效",
                "signals": len(factor_signals),
                "settlements": len(factor_settlements),
                "pending": sum(str(item.get("signal_id")) not in settled_ids for item in factor_signals),
                "net_cumulative_return": equity,
            }
        )
    return rows


def load_no_eligible_studies(experiment_root: Path) -> list[dict[str, Any]]:
    """Read completed sweeps that correctly found no development-eligible strategy."""

    studies: list[dict[str, Any]] = []
    for path in sorted(experiment_root.expanduser().glob("*_study.json")):
        try:
            study = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if study.get("status") != "no_eligible_candidate":
            continue
        studies.append(
            {
                "run_id": str(study.get("run_id", path.stem)),
                "candidate_library": str(study.get("candidate_library", "—")),
                "candidate_count": int(study.get("candidate_count") or 0),
                "selection_policy": str(study.get("selection_policy", "—")),
                "reason": str(study.get("reason", "No candidate satisfied the development-only policy.")),
                "path": str(path.resolve()),
            }
        )
    return studies


def load_factor_diagnostic_invalidations(
    path: Path = DEFAULT_FACTOR_DIAGNOSTIC_INVALIDATIONS,
) -> dict[str, dict[str, Any]]:
    """Load the versioned registry that supersedes immutable bad diagnostics."""

    source = path.expanduser()
    if not source.exists():
        return {}
    payload = json.loads(source.read_text(encoding="utf-8"))
    entries = payload.get("invalidations") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        raise ValueError("factor diagnostic invalidation registry must contain an invalidations list")
    result: dict[str, dict[str, Any]] = {}
    for item in entries:
        if not isinstance(item, dict):
            raise ValueError("factor diagnostic invalidation entries must be objects")
        run_id = str(item.get("diagnostic_run_id") or "").strip()
        reason = str(item.get("reason") or "").strip()
        if not run_id or not reason:
            raise ValueError("factor diagnostic invalidation requires diagnostic_run_id and reason")
        if run_id in result:
            raise ValueError(f"duplicate factor diagnostic invalidation: {run_id}")
        result[run_id] = item
    return result


def load_rolling_window_semantics_audits(experiment_root: Path) -> list[dict[str, Any]]:
    """Read no-return rolling-window input audits for the research report."""

    audits: list[dict[str, Any]] = []
    for path in sorted(experiment_root.expanduser().glob("*_rolling_window_semantics_audit.json")):
        try:
            audit = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if audit.get("status") != "completed":
            continue
        data = audit.get("data") or {}
        audits.append(
            {
                "run_id": str(audit.get("run_id", path.stem)),
                "calendar_start": str(data.get("calendar_start", "—")),
                "calendar_end": str(data.get("calendar_end", "—")),
                "factor_count": int(audit.get("factor_count") or 0),
                "failed_factor_count": int(audit.get("failed_factor_count") or 0),
                "failed_factors": [str(item) for item in audit.get("failed_factors") or []],
                "passed": bool(audit.get("passed", False)),
                "forward_return_fields_read": bool(audit.get("forward_return_fields_read", True)),
                "path": str(path.resolve()),
            }
        )
    return audits


def pre_complete_window_invalid_factors(run_id: str, factors: Iterable[str]) -> set[str]:
    """Identify factor rows invalidated by the fixed full-window semantics audit."""

    is_timestamp_run = (
        len(run_id) >= 16
        and run_id[:8].isdigit()
        and run_id[8] == "T"
        and run_id[9:15].isdigit()
        and run_id[15] == "Z"
    )
    if not is_timestamp_run or run_id >= COMPLETE_WINDOW_SEMANTICS_EFFECTIVE_RUN_ID:
        return set()
    return set(map(str, factors)) & set(WINDOW_SEMANTICS_AFFECTED_FACTORS)


def load_factor_diagnostics(
    experiment_root: Path,
    invalidation_path: Path = DEFAULT_FACTOR_DIAGNOSTIC_INVALIDATIONS,
) -> list[dict[str, Any]]:
    """Read development-only single-factor diagnostics for the research log."""

    diagnostics: list[dict[str, Any]] = []
    invalidations = load_factor_diagnostic_invalidations(invalidation_path)
    for path in sorted(experiment_root.expanduser().glob("*_factor_diagnostic.json")):
        try:
            diagnostic = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if diagnostic.get("status") != "completed":
            continue
        ranking = list(diagnostic.get("ranking_by_development_rank_ic") or [])
        data = diagnostic.get("data") or {}
        quality_gate = diagnostic.get("quality_gate") or {}
        forecast_events = diagnostic.get("performance_forecast_events") or {}
        billboard_events = diagnostic.get("daily_billboard_events") or {}
        major_holder_events = diagnostic.get("major_holder_events") or {}
        block_trade_events = diagnostic.get("block_trade_events") or {}
        margin_financing_events = diagnostic.get("margin_financing_events") or {}
        institutional_survey_events = diagnostic.get("institutional_survey_events") or {}
        repurchase_events = diagnostic.get("repurchase_events") or {}
        holder_count_events = diagnostic.get("holder_count_events") or {}
        pledge_events = diagnostic.get("pledge_events") or {}
        dividend_plan_events = diagnostic.get("dividend_plan_events") or {}
        run_id = str(diagnostic.get("run_id", path.stem))
        invalidation = invalidations.get(run_id)
        price_basis_invalid = data.get("price_basis") != REQUIRED_PRICE_BASIS
        expected_sha256 = str((invalidation or {}).get("source_sha256", "")).strip()
        if expected_sha256 and file_sha256(path) != expected_sha256:
            raise ValueError(f"factor diagnostic invalidation fingerprint mismatch: {run_id}")
        ranking_factors = [str(item.get("factor", "")) for item in ranking]
        semantic_invalid_factors = pre_complete_window_invalid_factors(run_id, ranking_factors)
        invalidated_factors = (
            set(ranking_factors) if invalidation or price_basis_invalid else semantic_invalid_factors
        )
        valid_ranking = [item for item in ranking if str(item.get("factor", "")) not in invalidated_factors]
        # A fully invalidated run remains visible for auditability, but a
        # partially invalidated catalog must display its best still-valid
        # factor rather than silently retaining an affected winner.
        top = valid_ranking[0] if valid_ranking else (ranking[0] if ranking else {})
        top_tail = top.get("topk_tail_risk") or {}
        evidence_status = (
            "invalidated"
            if ranking and not valid_ranking
            else "partially_invalidated" if invalidated_factors else "valid"
        )
        diagnostics.append(
            {
                "run_id": run_id,
                "calendar_start": str(data.get("calendar_start", "—")),
                "calendar_end": str(data.get("calendar_end", "—")),
                "fundamental_source": str(quality_gate.get("source", "—")),
                "performance_forecast_source": str(forecast_events.get("source", "—")),
                "billboard_event_source": str(billboard_events.get("source", "—")),
                "major_holder_event_source": str(major_holder_events.get("source", "—")),
                "block_trade_event_source": str(block_trade_events.get("source", "—")),
                "margin_financing_event_source": str(margin_financing_events.get("source", "—")),
                "institutional_survey_event_source": str(institutional_survey_events.get("source", "—")),
                "repurchase_event_source": str(repurchase_events.get("source", "—")),
                "holder_count_event_source": str(holder_count_events.get("source", "—")),
                "pledge_event_source": str(pledge_events.get("source", "—")),
                "dividend_plan_event_source": str(dividend_plan_events.get("source", "—")),
                "factor_count": len(ranking),
                "valid_factor_count": len(valid_ranking),
                "invalidated_factors": sorted(invalidated_factors),
                "top_factor": str(top.get("factor", "—")),
                "top_factor_mean_rank_ic": top.get("mean_rank_ic"),
                "top_factor_p05_net_return": top_tail.get("p05_net_return"),
                "top_factor_worst_net_return": top_tail.get("worst_net_return"),
                "evidence_status": evidence_status,
                "invalidation_reason": str(
                    (invalidation or {}).get(
                        "reason",
                        "diagnostic used the legacy mixed qfq/raw-VWAP basis without restoration factors"
                        if price_basis_invalid
                        else "pre-complete-window diagnostic rows used Qlib partial rolling values"
                        if semantic_invalid_factors
                        else "",
                    )
                ),
                "replacement_run_id": str((invalidation or {}).get("replacement_run_id", "")),
                "path": str(path.resolve()),
            }
        )
    return diagnostics


def load_factor_stability_audits(experiment_root: Path) -> list[dict[str, Any]]:
    """Read fixed-policy development factor-stability audits for the research log."""

    audits: list[dict[str, Any]] = []
    invalidations = load_factor_diagnostic_invalidations()
    for path in sorted(experiment_root.expanduser().glob("*_factor_stability_audit.json")):
        try:
            audit = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if audit.get("status") != "completed":
            continue
        decisions = list(audit.get("factor_decisions") or [])
        source = audit.get("input_diagnostic") or {}
        policy = audit.get("policy") or {}
        source_run_id = str(source.get("run_id", "—"))
        source_path = Path(str(source.get("path", ""))).expanduser()
        source_price_basis_invalid = False
        if source_path.is_file():
            try:
                source_diagnostic = json.loads(source_path.read_text(encoding="utf-8"))
                source_price_basis_invalid = (
                    (source_diagnostic.get("data") or {}).get("price_basis") != REQUIRED_PRICE_BASIS
                )
            except (OSError, json.JSONDecodeError):
                source_price_basis_invalid = True
        decision_factors = [str(item.get("factor", "")) for item in decisions]
        invalid_decision_factors = (
            set(decision_factors)
            if source_run_id in invalidations or source_price_basis_invalid
            else pre_complete_window_invalid_factors(source_run_id, decision_factors)
        )
        invalid_factor_count = len(invalid_decision_factors)
        qualified = [
            str(item.get("factor"))
            for item in decisions
            if item.get("passed") and str(item.get("factor")) not in invalid_decision_factors
        ]
        input_status = (
            "invalidated"
            if decisions and invalid_factor_count == len(decisions)
            else "partially_invalidated" if invalid_factor_count else "valid"
        )
        audits.append(
            {
                "run_id": str(audit.get("run_id", path.stem)),
                "input_diagnostic_run_id": source_run_id,
                "input_evidence_status": input_status,
                "factor_count": len(decisions),
                "qualified_factors": qualified,
                "minimum_calendar_years": policy.get("minimum_calendar_years"),
                "minimum_cohorts": policy.get("minimum_cohorts"),
                "path": str(path.resolve()),
            }
        )
    return audits


def load_factor_topk_viability_audits(experiment_root: Path) -> list[dict[str, Any]]:
    """Read development-only TopK viability screens for the research log."""

    audits: list[dict[str, Any]] = []
    invalidations = load_factor_diagnostic_invalidations()
    for path in sorted(experiment_root.expanduser().glob("*_factor_topk_viability_audit.json")):
        try:
            audit = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if audit.get("status") != "completed":
            continue
        decisions = list(audit.get("factor_decisions") or [])
        source = audit.get("input_diagnostic") or {}
        source_run_id = str(source.get("run_id", "—"))
        source_path = Path(str(source.get("path", ""))).expanduser()
        source_price_basis_invalid = False
        if source_path.is_file():
            try:
                source_diagnostic = json.loads(source_path.read_text(encoding="utf-8"))
                source_price_basis_invalid = (
                    (source_diagnostic.get("data") or {}).get("price_basis") != REQUIRED_PRICE_BASIS
                )
            except (OSError, json.JSONDecodeError):
                source_price_basis_invalid = True
        decision_factors = [str(item.get("factor", "")) for item in decisions]
        invalid_decision_factors = (
            set(decision_factors)
            if source_run_id in invalidations or source_price_basis_invalid
            else pre_complete_window_invalid_factors(source_run_id, decision_factors)
        )
        invalid_factor_count = len(invalid_decision_factors)
        qualified = [
            str(item.get("factor"))
            for item in decisions
            if item.get("passed") and str(item.get("factor")) not in invalid_decision_factors
        ]
        input_status = (
            "invalidated"
            if decisions and invalid_factor_count == len(decisions)
            else "partially_invalidated" if invalid_factor_count else "valid"
        )
        audits.append(
            {
                "run_id": str(audit.get("run_id", path.stem)),
                "input_diagnostic_run_id": source_run_id,
                "input_evidence_status": input_status,
                "factor_count": len(decisions),
                "qualified_factors": qualified,
                "path": str(path.resolve()),
            }
        )
    return audits


def load_event_factor_holdouts(experiment_root: Path) -> list[dict[str, Any]]:
    """Read explicitly post-development event-factor holdouts for the log."""

    holdouts: list[dict[str, Any]] = []
    for path in sorted(experiment_root.expanduser().glob("*_event_factor_holdout.json")):
        try:
            audit = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if audit.get("status") != "completed":
            continue
        data = audit.get("data") or {}
        hypothesis = audit.get("hypothesis") or {}
        result = audit.get("result") or {}
        holdouts.append(
            {
                "run_id": str(audit.get("run_id", path.stem)),
                "factor": str(hypothesis.get("factor", "—")),
                "development_diagnostic_run_id": str(hypothesis.get("development_diagnostic_run_id", "—")),
                "holdout_start": str(data.get("holdout_start", "—")),
                "holdout_end": str(data.get("holdout_end", "—")),
                "cohorts": int(result.get("cohorts") or 0),
                "mean_rank_ic": result.get("mean_rank_ic"),
                "mean_top_minus_bottom_gross_return": result.get("mean_top_minus_bottom_gross_return"),
                "supportive": bool(audit.get("supportive_holdout_association", False)),
                "path": str(path.resolve()),
            }
        )
    return holdouts


def load_walk_forward_selection_audits(experiment_root: Path) -> list[dict[str, Any]]:
    """Read expanding-window selection audits for the human research log."""

    audits: list[dict[str, Any]] = []
    for path in sorted(experiment_root.expanduser().glob("*_walk_forward_selection_audit.json")):
        try:
            audit = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if audit.get("status") != "completed":
            continue
        library = audit.get("candidate_library") or {}
        data = audit.get("data") or {}
        protocol = audit.get("protocol") or {}
        aggregate = audit.get("aggregate_selected_out_of_sample") or {}
        folds = list(audit.get("folds") or [])
        audits.append(
            {
                "run_id": str(audit.get("run_id", path.stem)),
                "candidate_library": str(library.get("id", "—")),
                "candidate_count": int(library.get("count") or 0),
                "calendar_start": str(data.get("calendar_start", "—")),
                "calendar_end": str(data.get("calendar_end", "—")),
                "first_test_year": protocol.get("first_test_year"),
                "last_test_year": protocol.get("last_test_year"),
                "fold_count": len(folds),
                "qualified_fold_count": sum(
                    fold.get("winner_selected_on_training_only") is not None for fold in folds
                ),
                "aggregate_net_return": aggregate.get("net_cumulative_return"),
                "aggregate_max_drawdown": aggregate.get("max_drawdown"),
                "path": str(path.resolve()),
            }
        )
    return audits


def load_selection_multiplicity_audits(experiment_root: Path) -> list[dict[str, Any]]:
    """Read development-only candidate-search multiplicity audits for the research log."""

    audits: list[dict[str, Any]] = []
    for path in sorted(experiment_root.expanduser().glob("*_selection_multiplicity_audit.json")):
        try:
            audit = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if audit.get("status") != "completed":
            continue
        study = audit.get("study") or {}
        data = audit.get("data") or {}
        bootstrap = audit.get("bootstrap") or {}
        result = audit.get("result") or {}
        reproducibility = study.get("selection_score_reproducibility") or {}
        candidate_cohort_count = data.get("candidate_development_cohort_count") or {}
        cohort_minimum = int(candidate_cohort_count.get("minimum") or data.get("development_cohort_count") or 0)
        cohort_maximum = int(candidate_cohort_count.get("maximum") or data.get("development_cohort_count") or 0)
        audits.append(
            {
                "run_id": str(audit.get("run_id", path.stem)),
                "study_run_id": str(study.get("run_id", "—")),
                "candidate_count": int(data.get("candidate_count") or 0),
                "development_cohort_count": (
                    str(cohort_minimum)
                    if cohort_minimum == cohort_maximum
                    else f"{cohort_minimum}–{cohort_maximum}"
                ),
                "winner": str(result.get("winner", "—")),
                "winner_resample_frequency": result.get("winner_resample_frequency"),
                "global_null_max_score_p_value": result.get("global_null_max_score_p_value"),
                "global_null_max_score_unusual": bool(result.get("global_null_max_score_unusual", False)),
                "drawdown_convention": str(reproducibility.get("drawdown_convention", "—")),
                "replicates": int(bootstrap.get("replicates") or 0),
                "block_cohorts": int(bootstrap.get("block_cohorts") or 0),
                "test_period_used": bool(data.get("test_period_used", False)),
                "path": str(path.resolve()),
            }
        )
    return audits


def load_limit_like_event_audits(experiment_root: Path) -> list[dict[str, Any]]:
    """Read fixed strong-close event audits for the human research log."""

    audits: list[dict[str, Any]] = []
    for path in sorted(experiment_root.expanduser().glob("*_limit_like_event_audit.json")):
        try:
            audit = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if audit.get("status") != "completed":
            continue
        data = audit.get("data") or {}
        result = audit.get("result") or {}
        performance = result.get("performance") or {}
        audits.append(
            {
                "run_id": str(audit.get("run_id", path.stem)),
                "calendar_start": str(data.get("calendar_start", "—")),
                "calendar_end": str(data.get("calendar_end", "—")),
                "event_cohorts": int(performance.get("rounds") or 0),
                "event_signal_cohorts": int(data.get("event_rebalance_cohorts") or 0),
                "net_cumulative_return": performance.get("net_cumulative_return"),
                "max_drawdown": performance.get("max_drawdown"),
                "passed": bool(result.get("passed", False)),
                "test_period_used": bool(data.get("test_period_used", False)),
                "path": str(path.resolve()),
            }
        )
    return audits


def load_quarterly_profit_acceleration_event_audits(experiment_root: Path) -> list[dict[str, Any]]:
    """Read fixed quarterly-announcement drift audits for the research log."""

    audits: list[dict[str, Any]] = []
    for path in sorted(experiment_root.expanduser().glob("*_quarterly_profit_acceleration_event_audit.json")):
        try:
            audit = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if audit.get("status") != "completed":
            continue
        data = audit.get("data") or {}
        result = audit.get("result") or {}
        performance = result.get("performance") or {}
        audits.append(
            {
                "run_id": str(audit.get("run_id", path.stem)),
                "calendar_start": str(data.get("calendar_start", "—")),
                "calendar_end": str(data.get("calendar_end", "—")),
                "event_cohorts": int(performance.get("rounds") or 0),
                "event_signal_cohorts": int(data.get("event_rebalance_cohorts") or 0),
                "net_cumulative_return": performance.get("net_cumulative_return"),
                "max_drawdown": performance.get("max_drawdown"),
                "passed": bool(result.get("passed", False)),
                "test_period_used": bool(data.get("test_period_used", False)),
                "path": str(path.resolve()),
            }
        )
    return audits


def load_quarterly_event_capacity_audits(experiment_root: Path) -> list[dict[str, Any]]:
    """Read no-outcome event-capacity gates so rejected ideas remain visible."""

    audits: list[dict[str, Any]] = []
    for path in sorted(experiment_root.expanduser().glob("*_quarterly_event_capacity_audit.json")):
        try:
            audit = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if audit.get("status") != "completed":
            continue
        data = audit.get("data") or {}
        capacity = audit.get("capacity") or {}
        audits.append(
            {
                "run_id": str(audit.get("run_id", path.stem)),
                "metric": str(capacity.get("metric", "—")),
                "calendar_start": str(data.get("calendar_start", "—")),
                "calendar_end": str(data.get("calendar_end", "—")),
                "complete_cohorts": int(capacity.get("complete_topk_event_cohorts") or 0),
                "minimum_cohorts": int(capacity.get("minimum_required_cohorts") or 0),
                "passed": bool(capacity.get("capacity_gate_passed", False)),
                "forward_return_fields_read": bool(capacity.get("forward_return_fields_read", True)),
                "decision": str(audit.get("decision", "—")),
                "path": str(path.resolve()),
            }
        )
    return audits


def load_candidate_overlap_audits(experiment_root: Path) -> list[dict[str, Any]]:
    """Read basket-overlap evidence without treating similar candidates as independent."""

    audits: list[dict[str, Any]] = []
    for path in sorted(experiment_root.expanduser().glob("*_candidate_overlap_audit.json")):
        try:
            audit = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if audit.get("status") != "completed":
            continue
        pairs = list(audit.get("pairwise_overlap") or [])
        data = audit.get("data") or {}
        reported_test_use = bool(data.get("test_period_used_for_pair_assessment", False))
        try:
            inferred_test_use = overlap_uses_post_development_observations(
                data.get("calendar_end"), str(data.get("development_end"))
            )
        except (TypeError, ValueError):
            inferred_test_use = False
        jaccards = [float(item["mean_jaccard"]) for item in pairs if item.get("mean_jaccard") is not None]
        correlations = [
            float(item["cohort_net_return_correlation"])
            for item in pairs
            if item.get("cohort_net_return_correlation") is not None
        ]
        libraries = audit.get("candidate_libraries") or [audit.get("candidate_library")]
        audits.append(
            {
                "run_id": str(audit.get("run_id", path.stem)),
                "candidate_count": len(audit.get("candidates") or []),
                "candidate_libraries": ", ".join(str(item) for item in libraries if item),
                "calendar_start": str(data.get("calendar_start", "—")),
                "calendar_end": str(data.get("calendar_end", "—")),
                "test_period_used_for_pair_assessment": reported_test_use or inferred_test_use,
                "pair_count": len(pairs),
                "mean_jaccard": float(np.mean(jaccards)) if jaccards else None,
                "maximum_return_correlation": float(max(correlations)) if correlations else None,
                "path": str(path.resolve()),
            }
        )
    return audits


def load_regime_audits(experiment_root: Path) -> list[dict[str, Any]]:
    """Read completed market-state audits for the human research log.

    An audit is evidence about a fixed candidate, not a registered strategy
    iteration.  Retaining unsuccessful audits in the report prevents a later
    state rule from silently replacing the previously recorded one.
    """

    audits: list[dict[str, Any]] = []
    for path in sorted(experiment_root.expanduser().glob("*_regime_audit.json")):
        try:
            audit = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if audit.get("status") != "completed":
            continue
        ranking = list(audit.get("ranking_by_development") or [])
        candidate = audit.get("candidate") or {}
        data = audit.get("data") or {}
        audits.append(
            {
                "run_id": str(audit.get("run_id", path.stem)),
                "candidate": str(candidate.get("name", "—")),
                "calendar_start": str(data.get("calendar_start", "—")),
                "calendar_end": str(data.get("calendar_end", "—")),
                "selection_policy": str(audit.get("selection_policy", "—")),
                "winner_regime": audit.get("winner_regime_selected_on_development_only"),
                "regime_count": len(ranking),
                "eligible_regime_count": sum(
                    item.get("development_selection_score") is not None for item in ranking
                ),
                "path": str(path.resolve()),
            }
        )
    return audits


def load_model_audits(experiment_root: Path) -> list[dict[str, Any]]:
    """Read time-safe three-day model diagnostics without treating them as strategies."""

    audits: list[dict[str, Any]] = []
    for path in sorted(experiment_root.expanduser().glob("*_model_audit.json")):
        try:
            audit = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if audit.get("status") != "completed":
            continue
        ranking = list(audit.get("ranking_by_development") or [])
        data = audit.get("data") or {}
        protocol = audit.get("protocol") or {}
        audits.append(
            {
                "run_id": str(audit.get("run_id", path.stem)),
                "calendar_start": str(data.get("calendar_start", "—")),
                "calendar_end": str(data.get("calendar_end", "—")),
                "development_start": str(protocol.get("development_start", "—")),
                "development_end": str(protocol.get("development_end", "—")),
                "configuration_count": len(ranking),
                "winner_configuration": audit.get("winner_configuration_selected_on_development_only"),
                "eligible_configuration_count": sum(
                    item.get("development_selection_score") is not None for item in ranking
                ),
                "path": str(path.resolve()),
            }
        )
    return audits


def load_loss_cap_audits(experiment_root: Path) -> list[dict[str, Any]]:
    """Read completed close-loss-cap sensitivity audits for the research log."""

    audits: list[dict[str, Any]] = []
    for path in sorted(experiment_root.expanduser().glob("*_loss_cap_audit.json")):
        try:
            audit = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if audit.get("status") != "completed":
            continue
        ranking = list(audit.get("ranking_by_development") or [])
        candidate = audit.get("candidate") or {}
        data = audit.get("data") or {}
        audits.append(
            {
                "run_id": str(audit.get("run_id", path.stem)),
                "candidate": str(candidate.get("name", "—")),
                "calendar_start": str(data.get("calendar_start", "—")),
                "calendar_end": str(data.get("calendar_end", "—")),
                "selection_policy": str(audit.get("selection_policy", "—")),
                "winner_close_loss_cap": audit.get("winner_close_loss_cap_selected_on_development_only"),
                "has_qualified_loss_cap": bool(
                    audit.get(
                        "has_development_qualified_loss_cap",
                        any(item.get("development_selection_score") is not None for item in ranking),
                    )
                ),
                "cap_count": len(ranking),
                "eligible_cap_count": sum(
                    item.get("development_selection_score") is not None for item in ranking
                ),
                "path": str(path.resolve()),
            }
        )
    return audits


def load_entry_gap_audits(experiment_root: Path) -> list[dict[str, Any]]:
    """Read completed next-open entry-gap sensitivity audits for the research log."""

    audits: list[dict[str, Any]] = []
    for path in sorted(experiment_root.expanduser().glob("*_entry_gap_audit.json")):
        try:
            audit = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if audit.get("status") != "completed":
            continue
        ranking = list(audit.get("ranking_by_development") or [])
        candidate = audit.get("candidate") or {}
        data = audit.get("data") or {}
        audits.append(
            {
                "run_id": str(audit.get("run_id", path.stem)),
                "candidate": str(candidate.get("name", "—")),
                "calendar_start": str(data.get("calendar_start", "—")),
                "calendar_end": str(data.get("calendar_end", "—")),
                "selection_policy": str(audit.get("selection_policy", "—")),
                "winner_max_entry_gap": audit.get("winner_max_entry_gap_selected_on_development_only"),
                "has_qualified_entry_gap": bool(
                    audit.get(
                        "has_development_qualified_entry_gap",
                        any(item.get("development_selection_score") is not None for item in ranking),
                    )
                ),
                "cap_count": len(ranking),
                "path": str(path.resolve()),
            }
        )
    return audits


def load_basket_correlation_audits(experiment_root: Path) -> list[dict[str, Any]]:
    """Read only full-window within-basket correlation diagnostics for the report."""

    audits: list[dict[str, Any]] = []
    for path in sorted(experiment_root.expanduser().glob("*_basket_correlation_audit.json")):
        try:
            audit = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if audit.get("status") != "completed":
            continue
        summary = audit.get("correlation_summary") or {}
        # Earlier exploratory diagnostics allowed partial return windows.  Do
        # not mix those noisy figures with the full-window evidence.
        if summary.get("required_return_days") is None:
            continue
        candidate = audit.get("candidate") or {}
        data = audit.get("data") or {}
        audits.append(
            {
                "run_id": str(audit.get("run_id", path.stem)),
                "candidate": str(candidate.get("name", "—")),
                "calendar_start": str(data.get("calendar_start", "—")),
                "calendar_end": str(data.get("calendar_end", "—")),
                "lookback_days": int(summary["required_return_days"]),
                "valid_basket_count": int(summary.get("valid_correlation_basket_count") or 0),
                "max_correlation_p90": summary.get("max_pairwise_correlation_p90"),
                "path": str(path.resolve()),
            }
        )
    return audits


def load_diversification_audits(experiment_root: Path) -> list[dict[str, Any]]:
    """Read completed correlation-cap sensitivity audits for the research log."""

    audits: list[dict[str, Any]] = []
    for path in sorted(experiment_root.expanduser().glob("*_diversification_audit.json")):
        try:
            audit = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if audit.get("status") != "completed":
            continue
        ranking = list(audit.get("ranking_by_development") or [])
        candidate = audit.get("candidate") or {}
        data = audit.get("data") or {}
        audits.append(
            {
                "run_id": str(audit.get("run_id", path.stem)),
                "candidate": str(candidate.get("name", "—")),
                "calendar_start": str(data.get("calendar_start", "—")),
                "calendar_end": str(data.get("calendar_end", "—")),
                "selection_policy": str(audit.get("selection_policy", "—")),
                "winner_max_pairwise_correlation": audit.get(
                    "winner_max_pairwise_correlation_selected_on_development_only"
                ),
                "has_qualified_cap": bool(
                    audit.get(
                        "has_development_qualified_diversification_cap",
                        any(item.get("development_selection_score") is not None for item in ranking),
                    )
                ),
                "cap_count": len(ranking),
                "path": str(path.resolve()),
            }
        )
    return audits


def load_cohort_risk_audits(experiment_root: Path) -> list[dict[str, Any]]:
    """Read descriptive worst-cohort attribution records for the research log."""

    audits: list[dict[str, Any]] = []
    for path in sorted(experiment_root.expanduser().glob("*_cohort_risk_audit.json")):
        try:
            audit = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if audit.get("status") != "completed":
            continue
        candidate = audit.get("candidate") or {}
        data = audit.get("data") or {}
        worst = list(audit.get("worst_cohorts") or [])
        audits.append(
            {
                "run_id": str(audit.get("run_id", path.stem)),
                "candidate": str(candidate.get("name", "—")),
                "calendar_start": str(data.get("calendar_start", "—")),
                "calendar_end": str(data.get("calendar_end", "—")),
                "worst_cohort_count": int(audit.get("worst_cohort_count") or len(worst)),
                "worst_net_return": worst[0].get("net_return") if worst else None,
                "path": str(path.resolve()),
            }
        )
    return audits


def load_risk_gate_audits(experiment_root: Path) -> list[dict[str, Any]]:
    """Read completed low-volatility/low-range eligibility-gate audits."""

    audits: list[dict[str, Any]] = []
    for path in sorted(experiment_root.expanduser().glob("*_risk_gate_audit.json")):
        try:
            audit = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if audit.get("status") != "completed":
            continue
        ranking = list(audit.get("ranking_by_development") or [])
        candidate = audit.get("candidate") or {}
        data = audit.get("data") or {}
        audits.append(
            {
                "run_id": str(audit.get("run_id", path.stem)),
                "candidate": str(candidate.get("name", "—")),
                "calendar_start": str(data.get("calendar_start", "—")),
                "calendar_end": str(data.get("calendar_end", "—")),
                "selection_policy": str(audit.get("selection_policy", "—")),
                "has_qualified_gate": bool(
                    audit.get(
                        "has_development_qualified_risk_gate",
                        any(item.get("development_selection_score") is not None for item in ranking),
                    )
                ),
                "gate_count": len(ranking),
                "path": str(path.resolve()),
            }
        )
    return audits


def render_three_day_research_report(
    registry: dict[str, Any],
    ledger: dict[str, Any],
    shadow_ledger: dict[str, Any] | None = None,
    shadow_observation_registry: dict[str, Any] | None = None,
    no_eligible_studies: list[dict[str, Any]] | None = None,
    factor_diagnostics: list[dict[str, Any]] | None = None,
    regime_audits: list[dict[str, Any]] | None = None,
    model_audits: list[dict[str, Any]] | None = None,
    loss_cap_audits: list[dict[str, Any]] | None = None,
    entry_gap_audits: list[dict[str, Any]] | None = None,
    basket_correlation_audits: list[dict[str, Any]] | None = None,
    diversification_audits: list[dict[str, Any]] | None = None,
    cohort_risk_audits: list[dict[str, Any]] | None = None,
    risk_gate_audits: list[dict[str, Any]] | None = None,
    candidate_overlap_audits: list[dict[str, Any]] | None = None,
    shadow_suspension_registry: dict[str, Any] | None = None,
    walk_forward_selection_audits: list[dict[str, Any]] | None = None,
    event_factor_holdouts: list[dict[str, Any]] | None = None,
    factor_stability_audits: list[dict[str, Any]] | None = None,
    factor_topk_viability_audits: list[dict[str, Any]] | None = None,
    selection_multiplicity_audits: list[dict[str, Any]] | None = None,
    limit_like_event_audits: list[dict[str, Any]] | None = None,
    quarterly_profit_acceleration_event_audits: list[dict[str, Any]] | None = None,
    prospective_factor_registry: dict[str, Any] | None = None,
    prospective_factor_ledger: dict[str, Any] | None = None,
    quarterly_event_capacity_audits: list[dict[str, Any]] | None = None,
    rolling_window_semantics_audits: list[dict[str, Any]] | None = None,
) -> str:
    """Render the append-only machine records into a concise human research log."""

    iterations = list(registry.get("iterations") or [])
    valid_iteration_ids = {
        str(item.get("iteration_id")) for item in iterations if uses_required_price_basis(item)
    }
    valid_ledger = filter_paper_ledger(
        ledger, identity_field="iteration_id", accepted_ids=valid_iteration_ids
    )
    signals, settlements, pending, paper_equity = _paper_ledger_summary(valid_ledger)
    invalid_iteration_count = len(iterations) - len(valid_iteration_ids)
    lines = [
        "# 三日短线研究日志",
        "",
        "本报告由策略注册表和纸面台账生成。它记录研究证据，不构成买卖建议或收益承诺。",
        (
            f"旧 qfq/raw-VWAP 价格基准下的 {invalid_iteration_count} 个策略轮次及其纸面收益已失效，"
            "仅保留审计记录；它们不会被监控、结算或用于选股。下文任何未携带已验收 price_basis 的"
            "旧因子、模型、敏感性或收益数字同样无效，即使其表格未逐行重复标记。"
            if invalid_iteration_count
            else f"所有可用策略轮次均要求价格基准 `{REQUIRED_PRICE_BASIS}`。"
        ),
        "",
        "## 策略迭代",
        "",
        "| 轮次 | 选择规则 | 持有期 / TopK | 状态条件 | 开发期胜者 | 开发期净收益 | 测试净收益 | 测试回撤 | 结论 |",
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for item in iterations:
        strategy = item.get("strategy") or {}
        selection = item.get("selection") or {}
        initial_test = item.get("initial_test") or {}
        promotion = item.get("promotion") or {}
        data = item.get("data") or {}
        holding = strategy.get("holding_period_trading_days", "—")
        topk = strategy.get("topk", "—")
        regime = strategy.get("regime_filter", "always")
        policy = selection.get("policy", strategy.get("selection_policy", "pooled_return_drawdown"))
        status = str(promotion.get("status", "—"))
        if not uses_required_price_basis(item):
            status = "价格基准失效（仅审计保留）"
        if promotion.get("eligible_for_promotion") is False:
            is_development_preregistration = (
                int(initial_test.get("rounds") or 0) == 0
                and data.get("calendar_end") is not None
                and data.get("development_end") is not None
                and data.get("calendar_end") == data.get("development_end")
            )
            status += "（开发期预登记，前瞻观察）" if is_development_preregistration else "（历史诊断，不可晋级）"
        lines.append(
            "| {label} | {policy} | {holding} 日 / {topk} | {regime} | {winner} | {development} | {test} | {mdd} | {status} |".format(
                label=item.get("label", item.get("iteration_id", "—")),
                policy=policy,
                holding=holding,
                topk=topk,
                regime=regime,
                winner=selection.get("winner", "—"),
                development=_percent((selection.get("development") or {}).get("net_cumulative_return")),
                test=_percent(initial_test.get("net_cumulative_return")),
                mdd=_percent(initial_test.get("max_drawdown")),
                status=status,
            )
        )
    if not iterations:
        lines.append("| — | — | — | — | 尚无研究轮次 | — | — | — | — |")
    if no_eligible_studies:
        lines.extend(
            [
                "",
                "## 未产生合格候选的压力扫描",
                "",
                "这些扫描严格按开发期规则执行且没有登记赢家；它们是淘汰证据，不能通过放松规则事后改写。",
                "",
                "| 扫描 | 候选库 / 数量 | 选择规则 | 结论 |",
                "| --- | --- | --- | --- |",
            ]
        )
        for study in no_eligible_studies:
            lines.append(
                "| {run_id} | {library} / {count} | {policy} | 无合格候选 |".format(
                    run_id=study["run_id"],
                    library=study["candidate_library"],
                    count=study["candidate_count"],
                    policy=study["selection_policy"],
                )
            )
        lines.append("")
    if rolling_window_semantics_audits:
        lines.extend(
            [
                "",
                "## 滚动因子完整窗口语义审计",
                "",
                "本节只检查收盘已知字段是否在声明窗口形成前意外非空；任何一行读取未来收益都使审计无效。",
                "",
                "| 审计 | 历史范围 | 检查字段 | 失败字段 | 未来收益字段 | 结论 |",
                "| --- | --- | ---: | ---: | --- | --- |",
            ]
        )
        for audit in rolling_window_semantics_audits:
            conclusion = "通过" if audit["passed"] else "失败：" + "、".join(audit["failed_factors"])
            lines.append(
                "| {run_id} | {start} 至 {end} | {count} | {failed} | {forward} | {conclusion} |".format(
                    run_id=audit["run_id"],
                    start=audit["calendar_start"],
                    end=audit["calendar_end"],
                    count=audit["factor_count"],
                    failed=audit["failed_factor_count"],
                    forward="是" if audit["forward_return_fields_read"] else "否",
                    conclusion=conclusion,
                )
            )
        lines.append("")
    if factor_diagnostics:
        lines.extend(
            [
                "",
                "## 开发期单因子三日预测诊断",
                "",
                "诊断只描述每个已声明因子与其后完整三日收益的横截面秩相关；它不选择策略，不能替代组合的独立测试或前瞻观察。",
                "",
                "| 诊断 | 证据状态 | 财务 / 事件快照 | 历史范围 | 因子数 | 开发期最高平均 Rank IC 因子 | 平均 Rank IC | TopK 净收益 P5 | 最差 TopK |",
                "| --- | --- | --- | --- | ---: | --- | ---: | ---: | ---: |",
            ]
        )
        for diagnostic in factor_diagnostics:
            mean_ic = diagnostic["top_factor_mean_rank_ic"]
            formatted_ic = "—" if mean_ic is None else f"{float(mean_ic):.4f}"
            p05 = diagnostic["top_factor_p05_net_return"]
            worst = diagnostic["top_factor_worst_net_return"]
            if diagnostic["evidence_status"] == "invalidated":
                evidence_status = f"无效 → {diagnostic['replacement_run_id'] or '待替代'}"
            elif diagnostic["evidence_status"] == "partially_invalidated":
                evidence_status = f"部分无效（{len(diagnostic['invalidated_factors'])} 因子）"
            else:
                evidence_status = "有效"
            factor_count = (
                str(diagnostic["factor_count"])
                if diagnostic["valid_factor_count"] == diagnostic["factor_count"]
                else f"{diagnostic['valid_factor_count']}/{diagnostic['factor_count']} 有效"
            )
            lines.append(
                "| {run_id} | {evidence_status} | {fundamentals} | {start} 至 {end} | {count} | {factor} | {mean_ic} | {p05} | {worst} |".format(
                    run_id=diagnostic["run_id"],
                    evidence_status=evidence_status,
                    fundamentals=" / ".join(
                        Path(source).name
                        for source in (
                            diagnostic["fundamental_source"],
                            diagnostic["performance_forecast_source"],
                            diagnostic["billboard_event_source"],
                            diagnostic["major_holder_event_source"],
                            diagnostic["block_trade_event_source"],
                            diagnostic["margin_financing_event_source"],
                            diagnostic["institutional_survey_event_source"],
                            diagnostic["repurchase_event_source"],
                            diagnostic["holder_count_event_source"],
                            diagnostic["pledge_event_source"],
                            diagnostic["dividend_plan_event_source"],
                        )
                        if source != "—"
                    )
                    or "—",
                    start=diagnostic["calendar_start"],
                    end=diagnostic["calendar_end"],
                    count=factor_count,
                    factor=diagnostic["top_factor"],
                    mean_ic=formatted_ic,
                    p05=_percent(p05),
                    worst=_percent(worst),
                )
            )
        lines.append("")
    if factor_stability_audits:
        lines.extend(
            [
                "",
                "## 开发期因子稳定性审计",
                "",
                "审计以固定门槛筛除偶然的单因子关联：至少 5 个自然年、200 个非重叠 cohort、总体 Rank IC 与 Top3‑末3 收益差为正、Rank IC 正值比例高于 50%，且每个已观察自然年的平均 Rank IC 均为正。通过只表示可以另行预注册策略测试，绝不自动选股、登记或晋级。",
                "",
                "| 审计 | 输入诊断 | 输入状态 | 审计因子数 | 通过因子 | 最低年份 / Cohort |",
                "| --- | --- | --- | ---: | --- | --- |",
            ]
        )
        for audit in factor_stability_audits:
            qualified = "、".join(audit["qualified_factors"]) or "无"
            lines.append(
                "| {run_id} | {source} | {source_status} | {count} | {qualified} | {years} / {cohorts} |".format(
                    run_id=audit["run_id"],
                    source=audit["input_diagnostic_run_id"],
                    source_status={
                        "invalidated": "无效输入",
                        "partially_invalidated": "部分无效",
                    }.get(audit.get("input_evidence_status"), "有效"),
                    count=audit["factor_count"],
                    qualified=qualified,
                    years=audit["minimum_calendar_years"] if audit["minimum_calendar_years"] is not None else "—",
                    cohorts=audit["minimum_cohorts"] if audit["minimum_cohorts"] is not None else "—",
                )
            )
        lines.append("")
    if factor_topk_viability_audits:
        lines.extend(
            [
                "",
                "## 单因子 Top‑3 组合可行性审计",
                "",
                "本节把通过关联稳定性审计的因子按诊断中同一收盘信号、次日开盘买入、第 3 日收盘卖出及研究成本形成 Top‑3 篮子。它要求关联审计通过、逐年 Top‑3 净累计收益为正、整体净累计收益为正且最大回撤不差于 −20%。结果只用于淘汰/分流，绝不自动形成策略或选股名单。",
                "",
                "| 审计 | 输入诊断 | 输入状态 | 审计因子数 | 可行因子 |",
                "| --- | --- | --- | ---: | --- |",
            ]
        )
        for audit in factor_topk_viability_audits:
            qualified = "、".join(audit["qualified_factors"]) or "无"
            lines.append(
                "| {run_id} | {source} | {source_status} | {count} | {qualified} |".format(
                    run_id=audit["run_id"],
                    source=audit["input_diagnostic_run_id"],
                    source_status={
                        "invalidated": "无效输入",
                        "partially_invalidated": "部分无效",
                    }.get(audit.get("input_evidence_status"), "有效"),
                    count=audit["factor_count"],
                    qualified=qualified,
                )
            )
        lines.append("")
    if event_factor_holdouts:
        lines.extend(
            [
                "",
                "## 事件因子留出期验证",
                "",
                "这里的方向在开发期诊断结束后才被明确，因此仅展示严格后续区间的条件化事件篮子结果；它不是完整日频策略，也不能晋级或生成选股名单。",
                "",
                "| 验证 | 因子 | 发展期诊断 | 留出期 | Cohort | 平均 Rank IC | Top3-末3 毛收益差 | 关联方向 |",
                "| --- | --- | --- | --- | ---: | ---: | ---: | --- |",
            ]
        )
        for holdout in event_factor_holdouts:
            mean_ic = holdout["mean_rank_ic"]
            spread = holdout["mean_top_minus_bottom_gross_return"]
            lines.append(
                "| {run_id} | {factor} | {development} | {start} 至 {end} | {cohorts} | {mean_ic} | {spread} | {supportive} |".format(
                    run_id=holdout["run_id"],
                    factor=holdout["factor"],
                    development=holdout["development_diagnostic_run_id"],
                    start=holdout["holdout_start"],
                    end=holdout["holdout_end"],
                    cohorts=holdout["cohorts"],
                    mean_ic="—" if mean_ic is None else f"{float(mean_ic):.4f}",
                    spread="—" if spread is None else _percent(float(spread)),
                    supportive="方向一致（仍不可晋级）" if holdout["supportive"] else "不支持（停止）",
                )
            )
        lines.append("")
    if walk_forward_selection_audits:
        lines.extend(
            [
                "",
                "## 滚动候选选择审计",
                "",
                "每个自然年测试段只使用此前完整持有周期的历史数据从候选库选胜者；下一年结果不参与该轮选择。它不能自动晋级或替换前瞻候选，但否定结果可作为明确暂停观察的证据。",
                "",
                "| 审计 | 因子库 / 数量 | 历史范围 | 测试年度 | 有合格胜者的折数 | 汇总样本外净收益 | 汇总样本外回撤 |",
                "| --- | --- | --- | --- | ---: | ---: | ---: |",
            ]
        )
        for audit in walk_forward_selection_audits:
            test_years = "—"
            if audit["first_test_year"] is not None and audit["last_test_year"] is not None:
                test_years = f"{audit['first_test_year']}–{audit['last_test_year']}"
            lines.append(
                "| {run_id} | {library} / {count} | {start} 至 {end} | {years} | {qualified}/{folds} | {net} | {mdd} |".format(
                    run_id=audit["run_id"],
                    library=audit["candidate_library"],
                    count=audit["candidate_count"],
                    start=audit["calendar_start"],
                    end=audit["calendar_end"],
                    years=test_years,
                    qualified=audit["qualified_fold_count"],
                    folds=audit["fold_count"],
                    net=_percent(audit["aggregate_net_return"]),
                    mdd=_percent(audit["aggregate_max_drawdown"]),
                )
            )
        lines.append("")
    if selection_multiplicity_audits:
        lines.extend(
            [
                "",
                "## 候选选择多重尝试审计",
                "",
                "本节只读取原始因子库在开发期保存的逐 cohort 收益：以共同的 5‑cohort 循环区块重采样保留候选之间的相关性，并在全局零收益比较中仅对实际持仓收益去均值、空仓维持零。它量化从整库挑出赢家后的稳定性与选择偏差，绝不读取测试期、生成选股名单或自动改变前瞻策略。",
                "",
                "| 审计 | 原始研究 | 候选 / 开发 Cohort | 胜者 | 重采样仍为胜者 | 全局零收益极值 p 值 | 评分回撤约定 | 设置 | 测试期参与 |",
                "| --- | --- | ---: | --- | ---: | ---: | --- | --- | --- |",
            ]
        )
        for audit in selection_multiplicity_audits:
            winner_frequency = audit["winner_resample_frequency"]
            p_value = audit["global_null_max_score_p_value"]
            lines.append(
                "| {run_id} | {study} | {candidates} / {cohorts} | {winner} | {frequency} | {p_value} | {convention} | {replicates} 次 / {block} cohort | {uses_test} |".format(
                    run_id=audit["run_id"],
                    study=audit["study_run_id"],
                    candidates=audit["candidate_count"],
                    cohorts=audit["development_cohort_count"],
                    winner=audit["winner"],
                    frequency="—" if winner_frequency is None else _percent(float(winner_frequency)),
                    p_value="—" if p_value is None else f"{float(p_value):.4f}",
                    convention=audit["drawdown_convention"],
                    replicates=audit["replicates"],
                    block=audit["block_cohorts"],
                    uses_test="是（无效记录）" if audit["test_period_used"] else "否",
                )
            )
        lines.append("")
    if limit_like_event_audits:
        lines.extend(
            [
                "",
                "## 限价样强势收盘事件审计",
                "",
                "该审计固定使用主板 9.5% / 创业板 19.5% 同日收益、收盘距日高不超过 0.5%，仅在事件内按同日换手异常度取完整 Top‑3，次日开盘进入、第 3 日收盘退出。它不是官方涨停识别，不能模拟次日开盘封板、停牌或排队成交；结果只用于淘汰或形成后续独立前瞻假设。",
                "",
                "| 审计 | 开发期 | 事件日 / 可执行 Cohort | 净累计收益 | 最大回撤 | 固定门槛结论 | 测试期参与 |",
                "| --- | --- | ---: | ---: | ---: | --- | --- |",
            ]
        )
        for audit in limit_like_event_audits:
            lines.append(
                "| {run_id} | {start} 至 {end} | {signals} / {cohorts} | {net} | {mdd} | {conclusion} | {uses_test} |".format(
                    run_id=audit["run_id"],
                    start=audit["calendar_start"],
                    end=audit["calendar_end"],
                    signals=audit["event_signal_cohorts"],
                    cohorts=audit["event_cohorts"],
                    net=_percent(audit["net_cumulative_return"]),
                    mdd=_percent(audit["max_drawdown"]),
                    conclusion="通过（仍不可直接选股）" if audit["passed"] else "不通过（停止）",
                    uses_test="是（无效记录）" if audit["test_period_used"] else "否",
                )
            )
        lines.append("")
    if quarterly_profit_acceleration_event_audits:
        lines.extend(
            [
                "",
                "## 季度利润加速公告事件审计",
                "",
                "该审计只在公告后下一本地交易日的首个安全收盘形成信号：质量合格且同财季利润同比加速为正的公司按原始加速幅度取完整 Top‑3，次日开盘进入、第 3 日收盘退出。它不使用公告当日、陈旧报告或非事件股票补篮子；通过也只能形成新的独立前瞻假设。",
                "",
                "| 审计 | 开发期 | 事件日 / 可执行 Cohort | 净累计收益 | 最大回撤 | 固定门槛结论 | 测试期参与 |",
                "| --- | --- | ---: | ---: | ---: | --- | --- |",
            ]
        )
        for audit in quarterly_profit_acceleration_event_audits:
            lines.append(
                "| {run_id} | {start} 至 {end} | {signals} / {cohorts} | {net} | {mdd} | {conclusion} | {uses_test} |".format(
                    run_id=audit["run_id"],
                    start=audit["calendar_start"],
                    end=audit["calendar_end"],
                    signals=audit["event_signal_cohorts"],
                    cohorts=audit["event_cohorts"],
                    net=_percent(audit["net_cumulative_return"]),
                    mdd=_percent(audit["max_drawdown"]),
                    conclusion="通过（仍不可直接选股）" if audit["passed"] else "不通过（停止）",
                    uses_test="是（无效记录）" if audit["test_period_used"] else "否",
                )
            )
        lines.append("")
    if quarterly_event_capacity_audits:
        lines.extend(
            [
                "",
                "## 季度事件样本容量审计",
                "",
                "本节在读取任何未来收益前，只按公告生效日、质量条件、非重叠三日网格和完整 Top‑3 计算最大可用 cohort。低于固定 200 cohort 的事件定义直接停止，不允许通过放宽门槛进入收益回测。",
                "",
                "| 审计 | 指标 | 开发期 | 完整 Cohort / 门槛 | 容量结论 | 读取未来收益 |",
                "| --- | --- | --- | ---: | --- | --- |",
            ]
        )
        for audit in quarterly_event_capacity_audits:
            lines.append(
                "| {run_id} | {metric} | {start} 至 {end} | {cohorts} / {minimum} | {decision} | {returns} |".format(
                    run_id=audit["run_id"],
                    metric=audit["metric"],
                    start=audit["calendar_start"],
                    end=audit["calendar_end"],
                    cohorts=audit["complete_cohorts"],
                    minimum=audit["minimum_cohorts"],
                    decision="通过容量门（仍需预注册）" if audit["passed"] else "容量不足（停止）",
                    returns="是（无效）" if audit["forward_return_fields_read"] else "否",
                )
            )
        lines.append("")
    if candidate_overlap_audits:
        lines.extend(
            [
                "",
                "## 候选篮子重叠审计",
                "",
                "重叠和收益相关性用于防止把相似候选的样本外表现当成多份独立证据；它不选择策略或改写任何前瞻登记。",
                "",
                "| 审计 | 因子库 | 候选数 / 配对数 | 历史范围 | 测试期参与相似度 | 平均篮子 Jaccard | 最高收益相关性 |",
                "| --- | --- | ---: | --- | --- | ---: | ---: |",
            ]
        )
        for audit in candidate_overlap_audits:
            mean_jaccard = "—" if audit["mean_jaccard"] is None else f"{float(audit['mean_jaccard']):.2f}"
            correlation = (
                "—"
                if audit["maximum_return_correlation"] is None
                else f"{float(audit['maximum_return_correlation']):.2f}"
            )
            lines.append(
                "| {run_id} | {libraries} | {candidates} / {pairs} | {start} 至 {end} | {uses_test} | {jaccard} | {correlation} |".format(
                    run_id=audit["run_id"],
                    libraries=audit["candidate_libraries"] or "—",
                    candidates=audit["candidate_count"],
                    pairs=audit["pair_count"],
                    start=audit["calendar_start"],
                    end=audit["calendar_end"],
                    uses_test="是（仅描述）" if audit["test_period_used_for_pair_assessment"] else "否",
                    jaccard=mean_jaccard,
                    correlation=correlation,
                )
            )
        lines.append("")
    if regime_audits:
        lines.extend(
            [
                "",
                "## 市场状态审计",
                "",
                "状态审计只对固定候选按开发期指标比较；即使有状态通过，也不能回写既有策略或替代前瞻样本。",
                "",
                "| 审计 | 候选 | 历史范围 | 选择规则 | 状态结论 |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for audit in regime_audits:
            conclusion = (
                str(audit["winner_regime"])
                if audit["winner_regime"]
                else f"无合格状态（{audit['eligible_regime_count']}/{audit['regime_count']}）"
            )
            lines.append(
                "| {run_id} | {candidate} | {start} 至 {end} | {policy} | {conclusion} |".format(
                    run_id=audit["run_id"],
                    candidate=audit["candidate"],
                    start=audit["calendar_start"],
                    end=audit["calendar_end"],
                    policy=audit["selection_policy"],
                    conclusion=conclusion,
                )
            )
        lines.append("")
    if model_audits:
        lines.extend(
            [
                "",
                "## 三日滚动模型审计",
                "",
                "模型按年度用此前信号日重新训练；后续历史区间不参与配置选择。该结果仅检验预测能力，不能注册策略、创建信号或替代前瞻观察。",
                "",
                "| 审计 | 历史范围 | 开发期 | 模型数 | 模型结论 |",
                "| --- | --- | --- | ---: | --- |",
            ]
        )
        for audit in model_audits:
            conclusion = (
                str(audit["winner_configuration"])
                if audit["winner_configuration"]
                else f"无合格模型（{audit['eligible_configuration_count']}/{audit['configuration_count']}）"
            )
            lines.append(
                "| {run_id} | {start} 至 {end} | {development_start} 至 {development_end} | {count} | {conclusion} |".format(
                    run_id=audit["run_id"],
                    start=audit["calendar_start"],
                    end=audit["calendar_end"],
                    development_start=audit["development_start"],
                    development_end=audit["development_end"],
                    count=audit["configuration_count"],
                    conclusion=conclusion,
                )
            )
        lines.append("")
    if loss_cap_audits:
        lines.extend(
            [
                "",
                "## 收盘损失上限审计",
                "",
                "此审计只比较固定候选在每日收盘确认损失后的假设性同收盘退出；提前卖出资金在原三日周期内保持现金，且结果不能自动修改前瞻策略。",
                "",
                "| 审计 | 候选 | 历史范围 | 选择规则 | 损失上限结论 |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for audit in loss_cap_audits:
            winner = audit["winner_close_loss_cap"]
            if not audit["has_qualified_loss_cap"]:
                conclusion = f"无合格损失上限（0/{audit['cap_count']}）"
            elif winner is None:
                conclusion = "无上限"
            else:
                conclusion = f"{float(winner):.0%}"
            lines.append(
                "| {run_id} | {candidate} | {start} 至 {end} | {policy} | {conclusion} |".format(
                    run_id=audit["run_id"],
                    candidate=audit["candidate"],
                    start=audit["calendar_start"],
                    end=audit["calendar_end"],
                    policy=audit["selection_policy"],
                    conclusion=conclusion,
                )
            )
        lines.append("")
    if entry_gap_audits:
        lines.extend(
            [
                "",
                "## 次日开盘跳空审计",
                "",
                "此审计只在次日开盘后检查完整 TopK 的实际跳空；任一股票超过上限则整组空仓，不替换为未检验的第四只。它是执行敏感性研究，不能修改前瞻策略。",
                "",
                "| 审计 | 候选 | 历史范围 | 选择规则 | 跳空上限结论 |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for audit in entry_gap_audits:
            if not audit["has_qualified_entry_gap"]:
                conclusion = f"无合格跳空上限（0/{audit['cap_count']}）"
            elif audit["winner_max_entry_gap"] is None:
                conclusion = "无跳空上限"
            else:
                conclusion = f"开发期最优上限 {audit['winner_max_entry_gap']:.0%}"
            lines.append(
                "| {run_id} | {candidate} | {start} 至 {end} | {policy} | {conclusion} |".format(
                    run_id=audit["run_id"],
                    candidate=audit["candidate"],
                    start=audit["calendar_start"],
                    end=audit["calendar_end"],
                    policy=audit["selection_policy"],
                    conclusion=conclusion,
                )
            )
        lines.append("")
    if basket_correlation_audits:
        lines.extend(
            [
                "",
                "## 篮子相关性审计",
                "",
                "仅保留具有完整回看窗口的相关性诊断；相关性是集中度代理，不能替代行业分类或直接成为交易规则。",
                "",
                "| 审计 | 候选 | 历史范围 | 回看日数 | 有效篮子 | 最大两两相关性 P90 |",
                "| --- | --- | --- | ---: | ---: | ---: |",
            ]
        )
        for audit in basket_correlation_audits:
            p90 = "—" if audit["max_correlation_p90"] is None else f"{float(audit['max_correlation_p90']):.2f}"
            lines.append(
                "| {run_id} | {candidate} | {start} 至 {end} | {lookback} | {count} | {p90} |".format(
                    run_id=audit["run_id"],
                    candidate=audit["candidate"],
                    start=audit["calendar_start"],
                    end=audit["calendar_end"],
                    lookback=audit["lookback_days"],
                    count=audit["valid_basket_count"],
                    p90=p90,
                )
            )
        lines.append("")
    if diversification_audits:
        lines.extend(
            [
                "",
                "## 相关性分散化审计",
                "",
                "此审计只比较固定候选的完整 TopK 相关性上限；无法凑足完整低相关篮子时按空仓记录，结果不能修改前瞻策略。",
                "",
                "| 审计 | 候选 | 历史范围 | 选择规则 | 分散化上限结论 |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for audit in diversification_audits:
            if not audit["has_qualified_cap"]:
                conclusion = f"无合格上限（0/{audit['cap_count']}）"
            elif audit["winner_max_pairwise_correlation"] is None:
                conclusion = "无约束"
            else:
                conclusion = f"{float(audit['winner_max_pairwise_correlation']):.2f}"
            lines.append(
                "| {run_id} | {candidate} | {start} 至 {end} | {policy} | {conclusion} |".format(
                    run_id=audit["run_id"],
                    candidate=audit["candidate"],
                    start=audit["calendar_start"],
                    end=audit["calendar_end"],
                    policy=audit["selection_policy"],
                    conclusion=conclusion,
                )
            )
        lines.append("")
    if cohort_risk_audits:
        lines.extend(
            [
                "",
                "## 最差 Cohort 风险归因",
                "",
                "归因仅描述已选出的历史最差 cohort 的同日特征排名，不能把个别股票或当前名称标签误作因果证据。",
                "",
                "| 审计 | 候选 | 历史范围 | 归因 Cohort 数 | 最差三日净收益 |",
                "| --- | --- | --- | ---: | ---: |",
            ]
        )
        for audit in cohort_risk_audits:
            lines.append(
                "| {run_id} | {candidate} | {start} 至 {end} | {count} | {worst} |".format(
                    run_id=audit["run_id"],
                    candidate=audit["candidate"],
                    start=audit["calendar_start"],
                    end=audit["calendar_end"],
                    count=audit["worst_cohort_count"],
                    worst=_percent(audit["worst_net_return"]),
                )
            )
        lines.append("")
    if risk_gate_audits:
        lines.extend(
            [
                "",
                "## 波动/振幅资格门审计",
                "",
                "此审计比较固定候选的同日低波动与低振幅排名门槛；无法形成完整 TopK 时按空仓记录，结果不能修改前瞻策略。",
                "",
                "| 审计 | 候选 | 历史范围 | 选择规则 | 资格门结论 |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for audit in risk_gate_audits:
            conclusion = "存在合格资格门" if audit["has_qualified_gate"] else f"无合格资格门（0/{audit['gate_count']}）"
            lines.append(
                "| {run_id} | {candidate} | {start} 至 {end} | {policy} | {conclusion} |".format(
                    run_id=audit["run_id"],
                    candidate=audit["candidate"],
                    start=audit["calendar_start"],
                    end=audit["calendar_end"],
                    policy=audit["selection_policy"],
                    conclusion=conclusion,
                )
            )
        lines.append("")
    lines.extend(
        [
            "",
            "## 纸面样本外观察",
            "",
            f"- 已记录信号：{signals} 笔；已结算：{settlements} 笔；待结算：{pending} 笔。",
            f"- 已结算纸面累计净收益：{_percent(paper_equity)}。",
            "- 未结算信号不计入收益；状态不满足时不创建信号，代表策略空仓。",
            "",
        ]
    )
    if shadow_ledger is not None:
        valid_shadow_ledger = filter_paper_ledger(
            shadow_ledger, identity_field="iteration_id", accepted_ids=valid_iteration_ids
        )
        shadow_signals, shadow_settlements, shadow_pending, shadow_equity = _paper_ledger_summary(
            valid_shadow_ledger
        )
        lines.extend(
            [
                "## 研究候选前瞻纸面观察",
                "",
                f"- 已记录信号：{shadow_signals} 笔；已结算：{shadow_settlements} 笔；待结算：{shadow_pending} 笔。",
                f"- 已结算纸面累计净收益：{_percent(shadow_equity)}。",
                "- 此处只跟踪显式登记且从未见过收盘日开始的研究候选；它不能产生下单计划或取代已晋级策略。",
                "",
            ]
        )
        observation_rows = _shadow_observation_rows(
            shadow_observation_registry or {},
            valid_shadow_ledger,
            shadow_suspension_registry,
            valid_iteration_ids,
        )
        if observation_rows:
            lines.extend(
                [
                    "| 轮次 | 候选 | 候选库 | 首个可用收盘日 | 状态 | 信号 | 已结算 | 待结算 | 已结算累计净收益 |",
                    "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
                ]
            )
            for row in observation_rows:
                lines.append(
                    "| {iteration_id} | {candidate} | {library} | {not_before} | {status} | {signals} | {settlements} | {pending} | {net_return} |".format(
                        iteration_id=row["iteration_id"],
                        candidate=row["candidate"],
                        library=row["candidate_library"],
                        not_before=row["not_before"],
                        status=row["status"],
                        signals=row["signals"],
                        settlements=row["settlements"],
                        pending=row["pending"],
                        net_return=_percent(row["net_cumulative_return"]) if row["settlements"] else "—",
                    )
                )
            lines.append("")
        suspensions = list((shadow_suspension_registry or {}).get("suspensions") or [])
        if suspensions:
            lines.extend(
                [
                    "### 已暂停的前瞻观察",
                    "",
                    "暂停不会删除原始登记或历史记录；在明确重新评估并新登记前，监控器不会为这些轮次创建新信号。",
                    "",
                    "| 轮次 | 原因 | 暂停时间 |",
                    "| --- | --- | --- |",
                ]
            )
            for suspension in suspensions:
                lines.append(
                    "| {iteration_id} | {reason} | {suspended_at} |".format(
                        iteration_id=suspension.get("iteration_id", "—"),
                        reason=suspension.get("reason", "—"),
                        suspended_at=suspension.get("suspended_at", "—"),
                    )
                )
            lines.append("")
    if prospective_factor_registry is not None and prospective_factor_ledger is not None:
        valid_registration_ids = {
            str(item.get("registration_id"))
            for item in prospective_factor_registry.get("registrations") or []
            if uses_required_price_basis(item)
        }
        valid_prospective_ledger = filter_paper_ledger(
            prospective_factor_ledger,
            identity_field="registration_id",
            accepted_ids=valid_registration_ids,
        )
        prospective_signals, prospective_settlements, prospective_pending, prospective_equity = (
            _paper_ledger_summary(valid_prospective_ledger)
        )
        lines.extend(
            [
                "## 事后形成因子的纯前瞻观察",
                "",
                f"- 已记录信号：{prospective_signals} 笔；已结算：{prospective_settlements} 笔；待结算：{prospective_pending} 笔。",
                f"- 已结算前瞻累计净收益：{_percent(prospective_equity)}。",
                "- 这些方向在读完开发期结果后才形成；禁止历史反向回测、补录错过的信号、加入候选库或生成下单计划。",
                "",
            ]
        )
        prospective_rows = _prospective_factor_rows(
            prospective_factor_registry, valid_prospective_ledger, valid_registration_ids
        )
        if prospective_rows:
            lines.extend(
                [
                    "| 登记 | 因子 | 来源诊断 | 首个未见收盘日 | 状态 | 信号 | 已结算 | 待结算 | 已结算累计净收益 |",
                    "| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
                ]
            )
            for row in prospective_rows:
                lines.append(
                    "| {registration_id} | {factor} | {source} | {not_before} | {status} | {signals} | {settlements} | {pending} | {net_return} |".format(
                        registration_id=row["registration_id"],
                        factor=row["factor"],
                        source=row["source_run_id"],
                        not_before=row["not_before"],
                        status=row["status"],
                        signals=row["signals"],
                        settlements=row["settlements"],
                        pending=row["pending"],
                        net_return=_percent(row["net_cumulative_return"]) if row["settlements"] else "—",
                    )
                )
            lines.append("")
    lines.extend(
        [
            "## 下一步规则",
            "",
            "1. 只对携带已验收 `price_basis` 的新登记运行 `monitor`、`shadow-monitor` 或 `prospective-monitor`；定时器会跳过所有旧登记。",
            "2. 新因子/权重必须作为新一轮写入注册表；不得改写已见测试段的结论。",
            "3. 只有纸面样本继续积累且回撤、成本、可交易性都可接受时，才讨论扩大模拟仓位。",
            "",
        ]
    )
    return "\n".join(lines)


def run_research_report(args: argparse.Namespace) -> dict[str, Any]:
    """Write a human-readable report from the immutable research records."""

    registry_path = Path(args.registry_path).expanduser()
    ledger_path = Path(args.ledger_path).expanduser()
    registry = json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else {"iterations": []}
    ledger = load_paper_ledger(ledger_path)
    shadow_ledger_path = Path(args.shadow_ledger_path).expanduser()
    shadow_ledger = load_paper_ledger(shadow_ledger_path)
    shadow_observation_registry_path = Path(args.shadow_observation_registry_path).expanduser()
    shadow_observation_registry = load_shadow_observation_registry(shadow_observation_registry_path)
    shadow_suspension_registry_path = Path(args.shadow_suspension_registry_path).expanduser()
    shadow_suspension_registry = load_shadow_suspension_registry(shadow_suspension_registry_path)
    prospective_factor_registry_path = Path(args.prospective_factor_registry_path).expanduser()
    prospective_factor_registry = load_prospective_factor_registry(prospective_factor_registry_path)
    prospective_factor_ledger_path = Path(args.prospective_factor_ledger_path).expanduser()
    prospective_factor_ledger = load_paper_ledger(prospective_factor_ledger_path)
    experiment_root = Path(args.experiment_root).expanduser()
    no_eligible_studies = load_no_eligible_studies(experiment_root)
    factor_diagnostics = load_factor_diagnostics(experiment_root)
    rolling_window_semantics_audits = load_rolling_window_semantics_audits(experiment_root)
    factor_stability_audits = load_factor_stability_audits(experiment_root)
    factor_topk_viability_audits = load_factor_topk_viability_audits(experiment_root)
    event_factor_holdouts = load_event_factor_holdouts(experiment_root)
    walk_forward_selection_audits = load_walk_forward_selection_audits(experiment_root)
    selection_multiplicity_audits = load_selection_multiplicity_audits(experiment_root)
    limit_like_event_audits = load_limit_like_event_audits(experiment_root)
    quarterly_profit_acceleration_event_audits = load_quarterly_profit_acceleration_event_audits(experiment_root)
    quarterly_event_capacity_audits = load_quarterly_event_capacity_audits(experiment_root)
    candidate_overlap_audits = load_candidate_overlap_audits(experiment_root)
    regime_audits = load_regime_audits(experiment_root)
    model_audits = load_model_audits(experiment_root)
    loss_cap_audits = load_loss_cap_audits(experiment_root)
    entry_gap_audits = load_entry_gap_audits(experiment_root)
    basket_correlation_audits = load_basket_correlation_audits(experiment_root)
    diversification_audits = load_diversification_audits(experiment_root)
    cohort_risk_audits = load_cohort_risk_audits(experiment_root)
    risk_gate_audits = load_risk_gate_audits(experiment_root)
    report = render_three_day_research_report(
        registry,
        ledger,
        shadow_ledger,
        shadow_observation_registry,
        no_eligible_studies,
        factor_diagnostics,
        regime_audits,
        model_audits,
        loss_cap_audits,
        entry_gap_audits,
        basket_correlation_audits,
        diversification_audits,
        cohort_risk_audits,
        risk_gate_audits,
        candidate_overlap_audits,
        shadow_suspension_registry,
        walk_forward_selection_audits,
        event_factor_holdouts,
        factor_stability_audits,
        factor_topk_viability_audits,
        selection_multiplicity_audits,
        limit_like_event_audits,
        quarterly_profit_acceleration_event_audits,
        prospective_factor_registry=prospective_factor_registry,
        prospective_factor_ledger=prospective_factor_ledger,
        quarterly_event_capacity_audits=quarterly_event_capacity_audits,
        rolling_window_semantics_audits=rolling_window_semantics_audits,
    )
    output = Path(args.output).expanduser()
    _atomic_write_text(output, report)
    return {
        "status": "completed",
        "registry_path": str(registry_path.resolve()),
        "ledger_path": str(ledger_path.resolve()),
        "shadow_ledger_path": str(shadow_ledger_path.resolve()),
        "shadow_observation_registry_path": str(shadow_observation_registry_path.resolve()),
        "shadow_suspension_registry_path": str(shadow_suspension_registry_path.resolve()),
        "prospective_factor_registry_path": str(prospective_factor_registry_path.resolve()),
        "prospective_factor_ledger_path": str(prospective_factor_ledger_path.resolve()),
        "report_path": str(output.resolve()),
        "iterations": len(registry.get("iterations") or []),
        "signals": len(ledger["signals"]),
        "settlements": len(ledger["settlements"]),
        "shadow_signals": len(shadow_ledger["signals"]),
        "shadow_settlements": len(shadow_ledger["settlements"]),
        "shadow_suspensions": len(shadow_suspension_registry["suspensions"]),
        "prospective_factor_registrations": len(prospective_factor_registry["registrations"]),
        "prospective_factor_signals": len(prospective_factor_ledger["signals"]),
        "prospective_factor_settlements": len(prospective_factor_ledger["settlements"]),
        "no_eligible_studies": len(no_eligible_studies),
        "factor_diagnostics": len(factor_diagnostics),
        "rolling_window_semantics_audits": len(rolling_window_semantics_audits),
        "factor_stability_audits": len(factor_stability_audits),
        "factor_topk_viability_audits": len(factor_topk_viability_audits),
        "event_factor_holdouts": len(event_factor_holdouts),
        "walk_forward_selection_audits": len(walk_forward_selection_audits),
        "selection_multiplicity_audits": len(selection_multiplicity_audits),
        "limit_like_event_audits": len(limit_like_event_audits),
        "quarterly_profit_acceleration_event_audits": len(quarterly_profit_acceleration_event_audits),
        "quarterly_event_capacity_audits": len(quarterly_event_capacity_audits),
        "candidate_overlap_audits": len(candidate_overlap_audits),
        "regime_audits": len(regime_audits),
        "model_audits": len(model_audits),
        "loss_cap_audits": len(loss_cap_audits),
        "entry_gap_audits": len(entry_gap_audits),
        "basket_correlation_audits": len(basket_correlation_audits),
        "diversification_audits": len(diversification_audits),
        "cohort_risk_audits": len(cohort_risk_audits),
        "risk_gate_audits": len(risk_gate_audits),
    }


def overlap_candidate_references(
    candidate_names: Iterable[str] | None,
    candidate_library: str | None,
    candidate_specs: Iterable[str] | None,
) -> list[tuple[str, str, Candidate]]:
    """Resolve same-library or explicit cross-library overlap candidates.

    ``--candidate`` retains the original compact form for one library.  The
    ``library:candidate`` form is intentionally explicit when comparing
    candidates from different predeclared libraries, so a name is never looked
    up in an unintended factor definition.
    """

    names = list(candidate_names or [])
    specs = list(candidate_specs or [])
    if names and specs:
        raise ValueError("use either --candidate with --candidate-library or --candidate-spec, not both")
    references: list[tuple[str, str, Candidate]] = []
    if specs:
        for spec in specs:
            library_id, separator, name = str(spec).partition(":")
            if not separator or not library_id or not name:
                raise ValueError("--candidate-spec must use library_id:candidate_name")
            candidate = candidate_by_name(name, library_id)
            references.append((f"{library_id}:{candidate.name}", library_id, candidate))
    else:
        if not candidate_library:
            raise ValueError("--candidate-library is required when --candidate is used")
        for name in names:
            candidate = candidate_by_name(str(name), candidate_library)
            references.append((candidate.name, candidate_library, candidate))
    unique = {reference: (reference, library_id, candidate) for reference, library_id, candidate in references}
    if len(unique) < 2:
        raise ValueError("supply at least two distinct overlap candidates")
    return list(unique.values())


def overlap_uses_post_development_observations(last_date: Any, development_end: str) -> bool:
    """Return whether an overlap calculation reaches beyond its development cut-off."""

    return bool(pd.Timestamp(last_date).normalize() > pd.Timestamp(development_end).normalize())


def run_candidate_overlap_audit(args: argparse.Namespace) -> dict[str, Any]:
    """Measure whether recorded candidates are genuinely distinct baskets."""

    references = overlap_candidate_references(
        getattr(args, "candidate", None),
        getattr(args, "candidate_library", None),
        getattr(args, "candidate_spec", None),
    )
    provider_uri = Path(args.provider_uri).expanduser()
    fundamental_path = Path(args.fundamentals).expanduser()
    experiment_root = Path(args.experiment_root).expanduser()
    fundamentals = load_fundamentals(fundamental_path)
    market = load_market_data(provider_uri, args.start, args.end, args.batch_size)
    market = attach_quality_asof(market, fundamentals, max_age_days=args.max_quality_age_days)
    ranked = rank_factor_frame(market)
    results: dict[str, dict[str, Any]] = {}
    for reference, library_id, candidate in references:
        scored = score_candidate(ranked, candidate)
        baskets = selected_baskets_by_signal(scored, args.hold_days, args.topk, args.regime_filter)
        rounds, summary = evaluate_candidate(
            scored,
            candidate,
            hold_days=args.hold_days,
            topk=args.topk,
            open_cost=args.open_cost,
            close_cost=args.close_cost,
            development_end=args.development_end,
            regime_filter=args.regime_filter,
        )
        returns = rounds.set_index("signal_date")["net_return"].astype(float)
        results[reference] = {
            "reference": reference,
            "candidate_library": library_id,
            "candidate": candidate,
            "baskets": baskets,
            "returns": returns,
            "summary": summary,
        }

    pairs: list[dict[str, Any]] = []
    for left_position, (left_name, left_library, _) in enumerate(references):
        for right_name, right_library, _ in references[left_position + 1 :]:
            left = results[left_name]
            right = results[right_name]
            overlap = basket_overlap_metrics(left["baskets"], right["baskets"])
            common_returns = pd.concat(
                [left["returns"].rename("left"), right["returns"].rename("right")], axis=1, join="inner"
            ).dropna()
            return_correlation = (
                float(common_returns["left"].corr(common_returns["right"]))
                if len(common_returns) >= 2
                and common_returns["left"].std(ddof=0) > 0.0
                and common_returns["right"].std(ddof=0) > 0.0
                else None
            )
            pairs.append(
                {
                    "left_candidate": left_name,
                    "left_candidate_library": left_library,
                    "right_candidate": right_name,
                    "right_candidate_library": right_library,
                    **overlap,
                    "common_return_cohorts": int(len(common_returns)),
                    "cohort_net_return_correlation": return_correlation,
                }
            )

    run_id = _timestamp()
    audit = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "candidate_overlap_research_only_not_investment_advice",
        "candidate_library": args.candidate_library if not getattr(args, "candidate_spec", None) else None,
        "candidate_libraries": sorted({library_id for _, library_id, _ in references}),
        "candidates": [
            {
                "reference": reference,
                "candidate_library": library_id,
                "name": candidate.name,
                "description": candidate.description,
                "weights": candidate.weights,
                "active_complete_baskets": len(results[reference]["baskets"]),
                "return_cohorts": int(len(results[reference]["returns"])),
                "development": results[reference]["summary"]["development"],
                "development_stability": results[reference]["summary"].get("development_stability"),
                "test": results[reference]["summary"]["test"],
            }
            for reference, library_id, candidate in references
        ],
        "strategy": {
            "universe": "buyable_main_chinext",
            "holding_period_trading_days": args.hold_days,
            "topk": args.topk,
            "regime_filter": args.regime_filter,
            "regime_filter_description": REGIME_FILTERS[args.regime_filter],
            "open_cost": args.open_cost,
            "close_cost": args.close_cost,
        },
        "data": {
            "provider_uri": str(provider_uri.resolve()),
            "calendar_start": market["datetime"].min().date().isoformat(),
            "calendar_end": market["datetime"].max().date().isoformat(),
            "development_end": args.development_end,
            "test_period_used_for_pair_assessment": overlap_uses_post_development_observations(
                market["datetime"].max(), args.development_end
            ),
        },
        "pairwise_overlap": pairs,
        "limitations": [
            "Basket overlap is a similarity diagnostic, not a strategy-selection or promotion rule.",
            "Only complete active TopK baskets are compared; inactive regimes are intentionally absent from basket overlap.",
            "When the requested end date is after development_end, post-development observations are used only to describe similarity and must not select, promote, or alter a forward observation.",
            "The current holding universe is derived from a current listing snapshot and can introduce survivorship bias in historical results.",
        ],
    }
    destination = experiment_root / f"{run_id}_candidate_overlap_audit.json"
    _atomic_write_text(destination, json.dumps(audit, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return {
        "status": "completed",
        "audit_path": str(destination.resolve()),
        "candidate_count": len(references),
        "pairwise_overlap": pairs,
    }


def run_rolling_window_semantics_audit(args: argparse.Namespace) -> dict[str, Any]:
    """Persist a no-forward-return audit of every declared rolling field."""

    provider_uri = Path(args.provider_uri).expanduser().resolve()
    experiment_root = Path(args.experiment_root).expanduser()
    calendar_path = provider_uri / "calendars" / "day.txt"
    if not calendar_path.exists():
        raise FileNotFoundError(f"Qlib day calendar does not exist: {calendar_path}")
    calendar_lines = [line.strip() for line in calendar_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not calendar_lines:
        raise ValueError("Qlib day calendar is empty")
    provider_start = pd.Timestamp(calendar_lines[0]).normalize()
    requested_start = pd.Timestamp(args.start).normalize()
    if requested_start > provider_start:
        raise ValueError(
            "rolling-window-semantics-audit must start no later than the provider calendar start "
            f"{provider_start.date().isoformat()} so prior history is not hidden"
        )
    market = load_market_data(
        provider_uri,
        args.start,
        args.end,
        args.batch_size,
        max_sessions_per_instrument=max(ROLLING_FACTOR_PRIOR_CLOSE_REQUIREMENTS.values()) + 1,
    )
    summary = summarize_rolling_window_semantics(market)
    run_id = _timestamp()
    audit = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "close_known_rolling_window_semantics_audit_without_forward_returns",
        "policy": {
            "provider_calendar_start_required": provider_start.date().isoformat(),
            "partial_window_values_allowed": False,
            "future_return_fields_allowed": False,
            "selection_or_promotion_allowed": False,
        },
        "data": {
            "provider_uri": str(provider_uri),
            "requested_start": args.start,
            "calendar_start": market["datetime"].min().date().isoformat(),
            "calendar_end": market["datetime"].max().date().isoformat(),
            "market_rows": int(len(market)),
            "instrument_count": int(market["instrument"].nunique()),
        },
        **summary,
        "limitations": [
            "This checks when close-known fields first become non-missing; it does not read returns after the signal date.",
            "A failure invalidates the declared complete-window semantics, but does not reveal whether fixing it improves or worsens returns.",
            "The local provider begins in 2015 and the current instrument snapshot can still introduce survivorship bias.",
        ],
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    destination = experiment_root / f"{run_id}_rolling_window_semantics_audit.json"
    _atomic_write_text(destination, json.dumps(audit, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return {
        "status": "completed",
        "audit_path": str(destination.resolve()),
        "passed": summary["passed"],
        "factor_count": summary["factor_count"],
        "failed_factor_count": summary["failed_factor_count"],
        "failed_factors": summary["failed_factors"],
        "forward_return_fields_read": False,
    }


def run_factor_diagnostic(args: argparse.Namespace) -> dict[str, Any]:
    """Measure development-only forward association for the declared factor catalog."""

    provider_uri = Path(args.provider_uri).expanduser()
    fundamental_path = Path(args.fundamentals).expanduser()
    forecast_path = Path(args.performance_forecasts).expanduser() if args.performance_forecasts else None
    billboard_path = Path(args.billboard_events).expanduser() if args.billboard_events else None
    major_holder_path = Path(args.major_holder_events).expanduser() if args.major_holder_events else None
    block_trade_path = Path(args.block_trade_events).expanduser() if args.block_trade_events else None
    margin_financing_path = Path(args.margin_financing_events).expanduser() if args.margin_financing_events else None
    institutional_survey_path = (
        Path(args.institutional_survey_events).expanduser() if args.institutional_survey_events else None
    )
    repurchase_path = Path(args.repurchase_events).expanduser() if args.repurchase_events else None
    holder_count_path = Path(args.holder_count_events).expanduser() if args.holder_count_events else None
    pledge_path = Path(args.pledge_events).expanduser() if args.pledge_events else None
    dividend_plan_path = Path(args.dividend_plan_events).expanduser() if args.dividend_plan_events else None
    experiment_root = Path(args.experiment_root).expanduser()
    price_basis_manifest = require_research_price_basis(provider_uri)
    price_basis_manifest_path = provider_uri.expanduser().resolve() / PRICE_BASIS_MANIFEST_NAME
    fundamentals = load_fundamentals(fundamental_path)
    market = load_market_data(provider_uri, args.start, args.end, args.batch_size)
    market_end = market["datetime"].max()
    if market_end > pd.Timestamp(args.development_end):
        raise ValueError(
            "factor-diagnostic is development-only; pass --end no later than --development-end so reserved test data cannot guide factor design"
        )
    market = attach_quality_asof(market, fundamentals, max_age_days=args.max_quality_age_days)
    if forecast_path is not None:
        forecasts = load_performance_forecasts(forecast_path)
        market = attach_performance_forecasts_asof(
            market, forecasts, max_age_days=args.max_forecast_age_days
        )
    if billboard_path is not None:
        billboard_events = load_billboard_events(billboard_path)
        market = attach_billboard_events_asof(
            market, billboard_events, max_age_days=args.max_billboard_age_days
        )
    if major_holder_path is not None:
        major_holder_events = load_major_holder_events(major_holder_path)
        market = attach_major_holder_events_asof(
            market, major_holder_events, max_age_days=args.max_major_holder_age_days
        )
    if block_trade_path is not None:
        block_trade_events = load_block_trade_events(block_trade_path)
        market = attach_block_trade_events_asof(
            market, block_trade_events, max_age_days=args.max_block_trade_age_days
        )
    if margin_financing_path is not None:
        margin_financing_events = load_margin_financing_events(margin_financing_path)
        market = attach_margin_financing_events_asof(
            market, margin_financing_events, max_age_days=args.max_margin_financing_age_days
        )
    if institutional_survey_path is not None:
        institutional_survey_events = load_institutional_survey_events(institutional_survey_path)
        market = attach_institutional_survey_events_asof(
            market, institutional_survey_events, max_age_days=args.max_institutional_survey_age_days
        )
    if repurchase_path is not None:
        repurchase_events = load_repurchase_plan_events(repurchase_path)
        market = attach_repurchase_plan_events_asof(
            market, repurchase_events, max_age_days=args.max_repurchase_age_days
        )
    if holder_count_path is not None:
        holder_count_events = load_holder_count_events(holder_count_path)
        market = attach_holder_count_events_asof(
            market, holder_count_events, max_age_days=args.max_holder_count_age_days
        )
    if pledge_path is not None:
        pledge_events = load_pledge_events(pledge_path)
        market = attach_pledge_events_asof(market, pledge_events, max_age_days=args.max_pledge_age_days)
    if dividend_plan_path is not None:
        dividend_plan_events = load_dividend_plan_events(dividend_plan_path)
        market = attach_dividend_plan_events_asof(
            market, dividend_plan_events, max_age_days=args.max_dividend_plan_age_days
        )
    ranked = rank_factor_frame(market)
    forward_returns = forward_factor_return_frame(ranked, args.hold_days)
    factor_catalog = [
        factor
        for factor in (
            *FACTOR_DIAGNOSTIC_COLUMNS,
            *FORECAST_FACTOR_DIAGNOSTIC_COLUMNS,
            *BILLBOARD_FACTOR_DIAGNOSTIC_COLUMNS,
            *MAJOR_HOLDER_FACTOR_DIAGNOSTIC_COLUMNS,
            *BLOCK_TRADE_FACTOR_DIAGNOSTIC_COLUMNS,
            *MARGIN_FINANCING_FACTOR_DIAGNOSTIC_COLUMNS,
            *INSTITUTIONAL_SURVEY_FACTOR_DIAGNOSTIC_COLUMNS,
            *REPURCHASE_FACTOR_DIAGNOSTIC_COLUMNS,
            *HOLDER_COUNT_FACTOR_DIAGNOSTIC_COLUMNS,
            *PLEDGE_FACTOR_DIAGNOSTIC_COLUMNS,
            *DIVIDEND_PLAN_FACTOR_DIAGNOSTIC_COLUMNS,
        )
        if factor in ranked.columns
    ]
    requested_factors = list(getattr(args, "factor", None) or [])
    if requested_factors:
        missing = sorted(set(requested_factors) - set(factor_catalog))
        if missing:
            raise ValueError("requested factor is absent from the diagnostic catalog: " + ", ".join(missing))
        # Preserve the user's first-seen order while preventing a duplicated
        # factor from masquerading as another independent test.
        factor_catalog = list(dict.fromkeys(requested_factors))
    summaries = summarize_factor_diagnostics(
        forward_returns,
        factor_catalog,
        hold_days=args.hold_days,
        topk=args.topk,
        open_cost=args.open_cost,
        close_cost=args.close_cost,
    )
    if not summaries:
        raise RuntimeError("no factor diagnostics could be computed from complete future quotes")
    run_id = _timestamp()
    audit = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "development_only_single_factor_forward_diagnostic_research_not_investment_advice",
        "factor_catalog": factor_catalog,
        "strategy_timing": {
            "universe": "buyable_main_chinext",
            "holding_period_trading_days": args.hold_days,
            "rebalancing": "non_overlapping_every_holding_period",
            "signal_time": "market close",
            "entry": "next local trading-session open",
            "exit": "local close after holding_period_trading_days",
            "diagnostic_topk": args.topk,
            "open_cost": args.open_cost,
            "close_cost": args.close_cost,
        },
        "quality_gate": {
            "source": str(fundamental_path.resolve()),
            "sha256": file_sha256(fundamental_path),
            "effective_date": "strictly next local trading day after announcement_date",
            "max_quality_age_days": args.max_quality_age_days,
        },
        "performance_forecast_events": (
            {
                "source": str(forecast_path.resolve()),
                "sha256": file_sha256(forecast_path),
                "effective_date": "strictly next local trading day after announcement_date",
                "max_forecast_age_days": args.max_forecast_age_days,
                "available_rows": int(market["forecast_available"].sum()),
                "eligible_available_rows": int(
                    (market["quality_eligible"].fillna(False) & market["forecast_available"].fillna(False)).sum()
                ),
            }
            if forecast_path is not None
            else None
        ),
        "daily_billboard_events": (
            {
                "source": str(billboard_path.resolve()),
                "sha256": file_sha256(billboard_path),
                "effective_date": "same trade_date close, scored after close for next local session open",
                "max_billboard_age_days": args.max_billboard_age_days,
                "available_rows": int(market["billboard_available"].sum()),
                "eligible_available_rows": int(
                    (market["quality_eligible"].fillna(False) & market["billboard_available"].fillna(False)).sum()
                ),
                "future_return_fields_stored": False,
            }
            if billboard_path is not None
            else None
        ),
        "major_holder_events": (
            {
                "source": str(major_holder_path.resolve()),
                "sha256": file_sha256(major_holder_path),
                "effective_date": "strictly next local trading day after announcement_date",
                "max_major_holder_age_days": args.max_major_holder_age_days,
                "available_rows": int(market["major_holder_available"].sum()),
                "eligible_available_rows": int(
                    (market["quality_eligible"].fillna(False) & market["major_holder_available"].fillna(False)).sum()
                ),
                "transaction_dates_stored": False,
            }
            if major_holder_path is not None
            else None
        ),
        "block_trade_events": (
            {
                "source": str(block_trade_path.resolve()),
                "sha256": file_sha256(block_trade_path),
                "effective_date": "same trade_date close, scored after close for next local session open",
                "max_block_trade_age_days": args.max_block_trade_age_days,
                "available_rows": int(market["block_trade_available"].sum()),
                "eligible_available_rows": int(
                    (market["quality_eligible"].fillna(False) & market["block_trade_available"].fillna(False)).sum()
                ),
                "future_return_fields_stored": False,
            }
            if block_trade_path is not None
            else None
        ),
        "margin_financing_events": (
            {
                "source": str(margin_financing_path.resolve()),
                "sha256": file_sha256(margin_financing_path),
                "effective_date": "same trade_date close, scored after close for next local session open",
                "max_margin_financing_age_days": args.max_margin_financing_age_days,
                "available_rows": int(market["margin_financing_available"].sum()),
                "eligible_available_rows": int(
                    (
                        market["quality_eligible"].fillna(False)
                        & market["margin_financing_available"].fillna(False)
                    ).sum()
                ),
                "top_n_rule": "read from the event snapshot manifest; omitted stocks are not treated as zero flow",
                "future_return_fields_stored": False,
            }
            if margin_financing_path is not None
            else None
        ),
        "institutional_survey_events": (
            {
                "source": str(institutional_survey_path.resolve()),
                "sha256": file_sha256(institutional_survey_path),
                "effective_date": "strictly next local trading day after announcement_date",
                "max_institutional_survey_age_days": args.max_institutional_survey_age_days,
                "available_rows": int(market["institutional_survey_available"].sum()),
                "eligible_available_rows": int(
                    (
                        market["quality_eligible"].fillna(False)
                        & market["institutional_survey_available"].fillna(False)
                    ).sum()
                ),
                "participant_identities_stored": False,
            }
            if institutional_survey_path is not None
            else None
        ),
        "repurchase_events": (
            {
                "source": str(repurchase_path.resolve()),
                "sha256": file_sha256(repurchase_path),
                "effective_date": "strictly next local trading day after DIM_DATE",
                "max_repurchase_age_days": args.max_repurchase_age_days,
                "available_rows": int(market["repurchase_available"].sum()),
                "eligible_available_rows": int(
                    (market["quality_eligible"].fillna(False) & market["repurchase_available"].fillna(False)).sum()
                ),
                "future_implementation_fields_stored": False,
            }
            if repurchase_path is not None
            else None
        ),
        "holder_count_events": (
            {
                "source": str(holder_count_path.resolve()),
                "sha256": file_sha256(holder_count_path),
                "effective_date": "strictly next local trading day after HOLD_NOTICE_DATE",
                "max_holder_count_age_days": args.max_holder_count_age_days,
                "available_rows": int(market["holder_count_available"].sum()),
                "eligible_available_rows": int(
                    (market["quality_eligible"].fillna(False) & market["holder_count_available"].fillna(False)).sum()
                ),
                "price_derived_fields_stored": False,
            }
            if holder_count_path is not None
            else None
        ),
        "pledge_events": (
            {
                "source": str(pledge_path.resolve()),
                "sha256": file_sha256(pledge_path),
                "effective_date": "strictly next local trading day after NOTICE_DATE",
                "max_pledge_age_days": args.max_pledge_age_days,
                "available_rows": int(market["pledge_available"].sum()),
                "eligible_available_rows": int(
                    (market["quality_eligible"].fillna(False) & market["pledge_available"].fillna(False)).sum()
                ),
                "current_price_or_state_fields_stored": False,
            }
            if pledge_path is not None
            else None
        ),
        "dividend_plan_events": (
            {
                "source": str(dividend_plan_path.resolve()),
                "sha256": file_sha256(dividend_plan_path),
                "effective_date": "strictly next local trading day after PLAN_NOTICE_DATE",
                "max_dividend_plan_age_days": args.max_dividend_plan_age_days,
                "available_rows": int(market["dividend_plan_available"].sum()),
                "eligible_available_rows": int(
                    (
                        market["quality_eligible"].fillna(False)
                        & market["dividend_plan_available"].fillna(False)
                    ).sum()
                ),
                "implementation_or_forward_fields_stored": False,
            }
            if dividend_plan_path is not None
            else None
        ),
        "data": {
            "provider_uri": str(provider_uri.resolve()),
            "price_basis": price_basis_manifest.get("price_basis"),
            "price_basis_manifest": str(price_basis_manifest_path),
            "price_basis_manifest_sha256": file_sha256(price_basis_manifest_path),
            "future_corporate_actions_used": price_basis_manifest.get("future_corporate_actions_used"),
            "calendar_start": market["datetime"].min().date().isoformat(),
            "calendar_end": market_end.date().isoformat(),
            "market_rows": int(len(market)),
            "eligible_rows": int(market["quality_eligible"].sum()),
            "complete_forward_name_observations": int(len(forward_returns)),
            "development_end": args.development_end,
            "test_period_used_for_factor_design": False,
        },
        "ranking_by_development_rank_ic": summaries,
        "limitations": [
            "This ranks individual factor associations only; it does not select, register, or promote a trading strategy.",
            "TopK-minus-BottomK is a descriptive gross cross-sectional spread, not an executable long-short simulation.",
            "A later factor library must be declared independently and evaluated with an untouched future period; this diagnostic does not validate a combined model.",
            "The current holding universe is derived from a current listing snapshot and can introduce survivorship bias in historical results.",
            "Prices use the accepted close-known adjusted/raw restoration contract; exchange limit queues, suspensions, and market impact are still not simulated exactly.",
        ],
    }
    destination = experiment_root / f"{run_id}_factor_diagnostic.json"
    _atomic_write_text(destination, json.dumps(audit, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return {
        "status": "completed",
        "audit_path": str(destination.resolve()),
        "factor_count": len(summaries),
        "top_factors_by_development_rank_ic": summaries[: min(10, len(summaries))],
    }


def run_factor_stability_audit(args: argparse.Namespace) -> dict[str, Any]:
    """Persist the fixed-policy development screen for one factor diagnostic."""

    diagnostic_path = Path(args.diagnostic).expanduser()
    if not diagnostic_path.exists():
        raise FileNotFoundError(f"factor diagnostic not found: {diagnostic_path}")
    try:
        diagnostic = json.loads(diagnostic_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"factor diagnostic is not valid JSON: {diagnostic_path}") from error
    if diagnostic.get("status") != "completed":
        raise ValueError("factor stability audit requires a completed factor diagnostic")
    require_diagnostic_price_basis(diagnostic)
    ranking = list(diagnostic.get("ranking_by_development_rank_ic") or [])
    if not ranking:
        raise ValueError("factor diagnostic contains no factor summaries")
    requested_factors = list(getattr(args, "factor", None) or [])
    available = {str(item.get("factor")): item for item in ranking}
    if requested_factors:
        missing = sorted(set(requested_factors) - set(available))
        if missing:
            raise ValueError("requested factor is absent from the diagnostic: " + ", ".join(missing))
        summaries = [available[factor] for factor in requested_factors]
    else:
        summaries = ranking
    decisions = [
        factor_stability_decision(
            summary,
            minimum_calendar_years=args.minimum_calendar_years,
            minimum_cohorts=args.minimum_cohorts,
        )
        for summary in summaries
    ]
    run_id = _timestamp()
    experiment_root = Path(args.experiment_root).expanduser()
    audit = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "development_only_factor_stability_screen_research_not_investment_advice",
        "input_diagnostic": {
            "run_id": str(diagnostic.get("run_id", diagnostic_path.stem)),
            "path": str(diagnostic_path.resolve()),
            "sha256": file_sha256(diagnostic_path),
            "calendar_start": (diagnostic.get("data") or {}).get("calendar_start"),
            "calendar_end": (diagnostic.get("data") or {}).get("calendar_end"),
            "development_end": (diagnostic.get("data") or {}).get("development_end"),
        },
        "policy": {
            "minimum_calendar_years": args.minimum_calendar_years,
            "minimum_cohorts": args.minimum_cohorts,
            "mean_rank_ic_gt": 0.0,
            "positive_rank_ic_rate_gt": 0.50,
            "mean_top_minus_bottom_gross_return_gt": 0.0,
            "every_observed_calendar_year_mean_rank_ic_gt": 0.0,
            "selection_or_promotion_allowed": False,
        },
        "requested_factors": requested_factors or None,
        "factor_decisions": decisions,
        "qualified_factors": [decision["factor"] for decision in decisions if decision["passed"]],
        "limitations": [
            "This applies a fixed screen to development-only factor associations; it does not select factor weights or a trading strategy.",
            "A passing factor still requires a separately predeclared full-strategy evaluation and genuinely future paper observations before any execution discussion.",
            "The current holding universe is derived from a current listing snapshot and can introduce survivorship bias in historical diagnostics.",
        ],
    }
    destination = experiment_root / f"{run_id}_factor_stability_audit.json"
    _atomic_write_text(destination, json.dumps(audit, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return {
        "status": "completed",
        "audit_path": str(destination.resolve()),
        "input_diagnostic_run_id": audit["input_diagnostic"]["run_id"],
        "factor_count": len(decisions),
        "qualified_factors": audit["qualified_factors"],
    }


def run_factor_topk_viability_audit(args: argparse.Namespace) -> dict[str, Any]:
    """Persist the development-only TopK viability screen for a factor diagnostic."""

    diagnostic_path = Path(args.diagnostic).expanduser()
    if not diagnostic_path.exists():
        raise FileNotFoundError(f"factor diagnostic not found: {diagnostic_path}")
    try:
        diagnostic = json.loads(diagnostic_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"factor diagnostic is not valid JSON: {diagnostic_path}") from error
    if diagnostic.get("status") != "completed":
        raise ValueError("factor TopK viability audit requires a completed factor diagnostic")
    require_diagnostic_price_basis(diagnostic)
    ranking = list(diagnostic.get("ranking_by_development_rank_ic") or [])
    if not ranking:
        raise ValueError("factor diagnostic contains no factor summaries")
    requested_factors = list(getattr(args, "factor", None) or [])
    available = {str(item.get("factor")): item for item in ranking}
    if requested_factors:
        missing = sorted(set(requested_factors) - set(available))
        if missing:
            raise ValueError("requested factor is absent from the diagnostic: " + ", ".join(missing))
        summaries = [available[factor] for factor in requested_factors]
    else:
        summaries = ranking
    decisions = [factor_topk_viability_decision(summary) for summary in summaries]
    run_id = _timestamp()
    experiment_root = Path(args.experiment_root).expanduser()
    audit = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "development_only_single_factor_topk_viability_screen_research_not_investment_advice",
        "input_diagnostic": {
            "run_id": str(diagnostic.get("run_id", diagnostic_path.stem)),
            "path": str(diagnostic_path.resolve()),
            "sha256": file_sha256(diagnostic_path),
            "calendar_start": (diagnostic.get("data") or {}).get("calendar_start"),
            "calendar_end": (diagnostic.get("data") or {}).get("calendar_end"),
            "development_end": (diagnostic.get("data") or {}).get("development_end"),
        },
        "policy": {
            "factor_association_stability_screen": "factor_stability_decision with fixed default thresholds",
            "minimum_executable_topk_cohorts": FACTOR_STABILITY_MIN_COHORTS,
            "topk_net_cumulative_return_gt": 0.0,
            "topk_max_drawdown_gte": STRICT_DEVELOPMENT_MAX_DRAWDOWN,
            "every_observed_calendar_year_topk_net_cumulative_return_gt": 0.0,
            "selection_or_promotion_allowed": False,
        },
        "requested_factors": requested_factors or None,
        "factor_decisions": decisions,
        "qualified_factors": [decision["factor"] for decision in decisions if decision["passed"]],
        "limitations": [
            "This screen uses the factor diagnostic's development-only TopK reconstruction and is not an independent strategy test.",
            "Passing it still requires a separately predeclared full-strategy evaluation and genuinely future paper observations before any execution discussion.",
            "Prices use the accepted point-in-time restoration contract but do not provide exact limit-queue or fill simulation.",
        ],
    }
    destination = experiment_root / f"{run_id}_factor_topk_viability_audit.json"
    _atomic_write_text(destination, json.dumps(audit, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return {
        "status": "completed",
        "audit_path": str(destination.resolve()),
        "input_diagnostic_run_id": audit["input_diagnostic"]["run_id"],
        "factor_count": len(decisions),
        "qualified_factors": audit["qualified_factors"],
    }


def run_billboard_holdout(args: argparse.Namespace) -> dict[str, Any]:
    """Evaluate the one post-development billboard hypothesis on a held-out interval.

    This command purposefully scores only the fixed inverse turnover direction
    and never writes to the strategy registry.  It is a conditional event
    association check; a positive result still needs a separately
    pre-registered full-strategy test and a future paper observation.
    """

    holdout_start = pd.Timestamp(args.holdout_start)
    development_end = pd.Timestamp(args.development_end)
    if holdout_start <= development_end:
        raise ValueError("--holdout-start must be strictly after --development-end")
    provider_uri = Path(args.provider_uri).expanduser()
    fundamental_path = Path(args.fundamentals).expanduser()
    billboard_path = Path(args.billboard_events).expanduser()
    experiment_root = Path(args.experiment_root).expanduser()
    fundamentals = load_fundamentals(fundamental_path)
    market = load_market_data(provider_uri, args.holdout_start, args.end, args.batch_size)
    market_end = pd.Timestamp(market["datetime"].max())
    if market_end <= holdout_start:
        raise ValueError("holdout needs at least one trading session after --holdout-start")
    market = attach_quality_asof(market, fundamentals, max_age_days=args.max_quality_age_days)
    billboard_events = load_billboard_events(billboard_path)
    market = attach_billboard_events_asof(market, billboard_events, max_age_days=args.max_billboard_age_days)
    ranked = add_billboard_holdout_factor(rank_factor_frame(market))
    forward_returns = forward_factor_return_frame(ranked, args.hold_days)
    forward_returns = forward_returns.loc[
        pd.to_datetime(forward_returns["signal_date"]) >= holdout_start
    ].copy()
    summaries = summarize_factor_diagnostics(
        forward_returns,
        (BILLBOARD_HOLDOUT_FACTOR,),
        hold_days=args.hold_days,
        topk=args.topk,
        open_cost=args.open_cost,
        close_cost=args.close_cost,
    )
    if len(summaries) != 1:
        raise RuntimeError("the billboard holdout did not produce a complete conditional event diagnostic")
    summary = summaries[0]
    supportive = bool(
        summary["mean_rank_ic"] > 0.0 and summary["mean_top_minus_bottom_gross_return"] > 0.0
    )
    run_id = _timestamp()
    audit = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "strict_post_development_conditional_billboard_event_holdout_not_a_strategy_or_investment_advice",
        "hypothesis": {
            "factor": BILLBOARD_HOLDOUT_FACTOR,
            "description": BILLBOARD_HOLDOUT_HYPOTHESIS,
            "development_diagnostic_run_id": args.development_diagnostic_run_id,
            "development_end": development_end.date().isoformat(),
            "direction_was_fixed_before_holdout_run": True,
        },
        "strategy_timing": {
            "universe": "buyable_main_chinext",
            "signal_time": "market close on billboard trade_date",
            "entry": "next local trading-session open",
            "exit": "local close after holding_period_trading_days",
            "holding_period_trading_days": args.hold_days,
            "diagnostic_topk": args.topk,
            "open_cost": args.open_cost,
            "close_cost": args.close_cost,
        },
        "quality_gate": {
            "source": str(fundamental_path.resolve()),
            "sha256": file_sha256(fundamental_path),
            "effective_date": "strictly next local trading day after announcement_date",
            "max_quality_age_days": args.max_quality_age_days,
        },
        "daily_billboard_events": {
            "source": str(billboard_path.resolve()),
            "sha256": file_sha256(billboard_path),
            "effective_date": "same trade_date close, scored after close for next local session open",
            "max_billboard_age_days": args.max_billboard_age_days,
            "future_return_fields_stored": False,
            "eligible_available_rows": int(
                (market["quality_eligible"].fillna(False) & market["billboard_available"].fillna(False)).sum()
            ),
        },
        "data": {
            "provider_uri": str(provider_uri.resolve()),
            "holdout_start": holdout_start.date().isoformat(),
            "holdout_end": market_end.date().isoformat(),
            "market_rows": int(len(market)),
            "eligible_rows": int(market["quality_eligible"].sum()),
            "complete_forward_name_observations": int(len(forward_returns)),
            "holdout_used_for_factor_design": False,
        },
        "result": summary,
        "supportive_holdout_association": supportive,
        "promotion": {
            "eligible_for_promotion": False,
            "status": "holdout_diagnostic_only",
            "next_step": (
                "If this conditional association is supportive, pre-register a full event strategy and evaluate it only "
                "on a new future period before any paper observation; otherwise retain this as rejection evidence."
            ),
        },
        "limitations": [
            "This is a conditional sample of eligible stocks with a recent billboard event, not a daily long-only strategy.",
            "The inverse direction was formed from an already-observed development diagnostic; this one holdout does not erase multiple-testing risk.",
            "The public billboard snapshot can revise historical entries and is not an exchange-grade point-in-time disclosure database.",
            "The current holding universe is derived from a current listing snapshot and can introduce survivorship bias.",
            "Prices use the accepted point-in-time restoration contract but do not simulate exact tradability, price limits, or suspensions.",
        ],
    }
    destination = experiment_root / f"{run_id}_event_factor_holdout.json"
    _atomic_write_text(destination, json.dumps(audit, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return {
        "status": "completed",
        "audit_path": str(destination.resolve()),
        "factor": BILLBOARD_HOLDOUT_FACTOR,
        "supportive_holdout_association": supportive,
        "result": summary,
    }


def run_basket_correlation_audit(args: argparse.Namespace) -> dict[str, Any]:
    """Measure whether one TopK basket is concentrated in correlated names.

    This diagnostic intentionally does not alter ranking or execution.  It is
    evidence for deciding whether a separately named diversification rule is
    worth testing, not a promotion path for the fixed candidate.
    """

    provider_uri = Path(args.provider_uri).expanduser()
    fundamental_path = Path(args.fundamentals).expanduser()
    experiment_root = Path(args.experiment_root).expanduser()
    candidate = candidate_by_name(args.candidate, args.candidate_library)
    fundamentals = load_fundamentals(fundamental_path)
    market = load_market_data(provider_uri, args.start, args.end, args.batch_size)
    market = attach_quality_asof(market, fundamentals, max_age_days=args.max_quality_age_days)
    ranked = rank_factor_frame(market)
    scored = score_candidate(ranked, candidate)
    baskets = selected_baskets_by_signal(scored, args.hold_days, args.topk, args.regime_filter)
    rounds, model_summary = evaluate_candidate(
        scored,
        candidate,
        hold_days=args.hold_days,
        topk=args.topk,
        open_cost=args.open_cost,
        close_cost=args.close_cost,
        development_end=args.development_end,
        regime_filter=args.regime_filter,
    )
    rows = basket_correlation_rows(scored, baskets, args.correlation_lookback)
    summary = summarize_basket_correlation(rows, rounds, args.correlation_lookback)
    cohort_rows = rows.merge(
        rounds[["signal_date", "net_return", "regime_active"]], on="signal_date", how="left"
    ).sort_values("signal_date", kind="stable")
    run_id = _timestamp()
    audit = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "basket_correlation_concentration_research_only_not_investment_advice",
        "candidate": {
            "name": candidate.name,
            "description": candidate.description,
            "weights": candidate.weights,
            "candidate_library": args.candidate_library,
        },
        "strategy": {
            "universe": "buyable_main_chinext",
            "holding_period_trading_days": args.hold_days,
            "rebalancing": "non_overlapping_every_holding_period",
            "topk": args.topk,
            "regime_filter": args.regime_filter,
            "regime_filter_description": REGIME_FILTERS[args.regime_filter],
            "signal_time": "market close",
            "entry": "next local trading-session open",
            "exit": "local close after holding_period_trading_days",
            "open_cost": args.open_cost,
            "close_cost": args.close_cost,
            "correlation_measure": (
                f"pairwise Pearson correlation of daily close-to-close returns over the latest {args.correlation_lookback} "
                "calendar observations ending at the signal close"
            ),
        },
        "quality_gate": {
            "source": str(fundamental_path.resolve()),
            "sha256": file_sha256(fundamental_path),
            "effective_date": "strictly next local trading day after announcement_date",
            "max_quality_age_days": args.max_quality_age_days,
        },
        "data": {
            "provider_uri": str(provider_uri.resolve()),
            "calendar_start": market["datetime"].min().date().isoformat(),
            "calendar_end": market["datetime"].max().date().isoformat(),
            "development_end": args.development_end,
            "test_period_used_for_correlation_diagnostic": False,
        },
        "candidate_development": model_summary["development"],
        "candidate_development_stability": model_summary.get("development_stability"),
        "correlation_summary": summary,
        "cohorts": [
            {
                "signal_date": row.signal_date.date().isoformat(),
                "basket_size": int(row.basket_size),
                "valid_return_days": int(row.valid_return_days),
                "mean_pairwise_correlation": None
                if pd.isna(row.mean_pairwise_correlation)
                else float(row.mean_pairwise_correlation),
                "max_pairwise_correlation": None
                if pd.isna(row.max_pairwise_correlation)
                else float(row.max_pairwise_correlation),
                "three_day_net_return": None if pd.isna(row.net_return) else float(row.net_return),
                "regime_active": bool(row.regime_active) if pd.notna(row.regime_active) else False,
            }
            for row in cohort_rows.itertuples(index=False)
        ],
        "limitations": [
            "Return correlation is a statistical concentration proxy, not an industry classification or proof of common economic exposure.",
            "Twenty daily observations make the estimate noisy; this diagnostic does not itself filter or reorder a basket.",
            "The current holding universe is derived from a current listing snapshot and can introduce survivorship bias in historical results.",
            "Prices use the accepted point-in-time restoration contract but do not provide exact limit-queue or fill simulation.",
        ],
    }
    destination = experiment_root / f"{run_id}_basket_correlation_audit.json"
    _atomic_write_text(destination, json.dumps(audit, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return {
        "status": "completed",
        "audit_path": str(destination.resolve()),
        "candidate": candidate.name,
        "correlation_summary": summary,
    }


def run_cohort_risk_audit(args: argparse.Namespace) -> dict[str, Any]:
    """Attribute the worst scheduled cohorts to close-known selected-stock characteristics."""

    provider_uri = Path(args.provider_uri).expanduser()
    fundamental_path = Path(args.fundamentals).expanduser()
    experiment_root = Path(args.experiment_root).expanduser()
    candidate = candidate_by_name(args.candidate, args.candidate_library)
    fundamentals = load_fundamentals(fundamental_path)
    market = load_market_data(provider_uri, args.start, args.end, args.batch_size)
    market = attach_quality_asof(market, fundamentals, max_age_days=args.max_quality_age_days)
    ranked = rank_factor_frame(market)
    scored = score_candidate(ranked, candidate)
    baskets = selected_baskets_by_signal(scored, args.hold_days, args.topk, args.regime_filter)
    details = selected_basket_trade_details(scored, baskets, args.hold_days, args.open_cost, args.close_cost)
    if details.empty:
        raise RuntimeError("no complete selected basket trades are available for cohort risk attribution")
    metadata = _universe_metadata()
    details["name"] = details["instrument"].map(lambda value: metadata.get(str(value), {}).get("name", ""))
    cohorts = (
        details.groupby("datetime", sort=True)
        .agg(net_return=("net_return", "mean"), gross_return=("gross_return", "mean"), holdings=("instrument", "nunique"))
        .reset_index()
        .rename(columns={"datetime": "signal_date"})
    )
    worst_cohorts = cohorts.nsmallest(args.worst_cohorts, "net_return")
    worst_dates = set(worst_cohorts["signal_date"])
    feature_columns = [
        column
        for column in (
            "liquidity_5",
            "volatility_low_20",
            "amplitude_low",
            "close_to_high",
            "quality_score",
            "quality_revenue",
            "momentum_20",
        )
        if column in details.columns
    ]
    feature_summary = {
        column: {
            "all_selected_median": float(details[column].median()),
            "worst_cohort_holdings_median": float(details.loc[details["datetime"].isin(worst_dates), column].median()),
        }
        for column in feature_columns
    }
    entry_execution_summary = {
        "entry_gap_return": {
            "all_selected_median": float(details["entry_gap_return"].median()),
            "worst_cohort_holdings_median": float(
                details.loc[details["datetime"].isin(worst_dates), "entry_gap_return"].median()
            ),
        }
    }
    run_id = _timestamp()
    audit = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "worst_cohort_risk_attribution_research_only_not_investment_advice",
        "candidate": {
            "name": candidate.name,
            "description": candidate.description,
            "weights": candidate.weights,
            "candidate_library": args.candidate_library,
        },
        "strategy": {
            "universe": "buyable_main_chinext",
            "holding_period_trading_days": args.hold_days,
            "topk": args.topk,
            "regime_filter": args.regime_filter,
            "regime_filter_description": REGIME_FILTERS[args.regime_filter],
            "signal_time": "market close",
            "entry": "next local trading-session open",
            "exit": "local close after holding_period_trading_days",
            "open_cost": args.open_cost,
            "close_cost": args.close_cost,
        },
        "quality_gate": {
            "source": str(fundamental_path.resolve()),
            "sha256": file_sha256(fundamental_path),
            "effective_date": "strictly next local trading day after announcement_date",
            "max_quality_age_days": args.max_quality_age_days,
        },
        "data": {
            "provider_uri": str(provider_uri.resolve()),
            "calendar_start": market["datetime"].min().date().isoformat(),
            "calendar_end": market["datetime"].max().date().isoformat(),
            "development_end": args.development_end,
            "test_period_used_for_risk_attribution": False,
        },
        "worst_cohort_count": args.worst_cohorts,
        "feature_rank_medians": feature_summary,
        "entry_execution_medians": entry_execution_summary,
        "worst_cohorts": [
            {
                "signal_date": cohort.signal_date.date().isoformat(),
                "net_return": float(cohort.net_return),
                "gross_return": float(cohort.gross_return),
                "holdings": int(cohort.holdings),
                "selected_stocks": [
                    {
                        "instrument": str(row.instrument),
                        "name": str(row.name),
                        "score": float(row.score),
                        "entry_date": row.entry_date.date().isoformat(),
                        "exit_date": row.exit_date.date().isoformat(),
                        "entry_gap_return": float(row.entry_gap_return),
                        "gross_return": float(row.gross_return),
                        "net_return": float(row.net_return),
                        **{column: float(getattr(row, column)) for column in feature_columns},
                    }
                    for row in details.loc[details["datetime"] == cohort.signal_date]
                    .sort_values(["score", "instrument"], ascending=[False, True], kind="stable")
                    .itertuples(index=False)
                ],
            }
            for cohort in worst_cohorts.itertuples(index=False)
        ],
        "limitations": [
            "This is descriptive attribution of selected historical cohorts, not a causal test or a strategy-selection rule.",
            "The reported feature values are same-day cross-sectional ranks, not absolute liquidity or volatility guarantees.",
            "Entry gap is observable only at the next session's open, so it is an execution variable rather than a close-known factor.",
            "Names and ST flags are drawn from a current metadata snapshot and are not historical point-in-time classifications.",
            "The current holding universe is derived from a current listing snapshot and can introduce survivorship bias in historical results.",
            "Prices use the accepted point-in-time restoration contract but do not provide exact limit-queue or fill simulation.",
        ],
    }
    destination = experiment_root / f"{run_id}_cohort_risk_audit.json"
    _atomic_write_text(destination, json.dumps(audit, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return {
        "status": "completed",
        "audit_path": str(destination.resolve()),
        "candidate": candidate.name,
        "worst_cohorts": [
            {"signal_date": item["signal_date"], "net_return": item["net_return"]} for item in audit["worst_cohorts"]
        ],
        "feature_rank_medians": feature_summary,
        "entry_execution_medians": entry_execution_summary,
    }


def run_risk_gate_audit(args: argparse.Namespace) -> dict[str, Any]:
    """Compare a small cross-product of close-known low-volatility and low-range gates."""

    provider_uri = Path(args.provider_uri).expanduser()
    fundamental_path = Path(args.fundamentals).expanduser()
    experiment_root = Path(args.experiment_root).expanduser()
    candidate = candidate_by_name(args.candidate, args.candidate_library)
    volatility_levels = args.min_volatility_low_20 or list(RISK_GATE_LEVELS)
    amplitude_levels = args.min_amplitude_low or list(RISK_GATE_LEVELS)
    for value in volatility_levels:
        validate_selection_risk_gate(value, "volatility_low_20")
    for value in amplitude_levels:
        validate_selection_risk_gate(value, "amplitude_low")
    configurations = [
        (volatility, amplitude)
        for volatility in dict.fromkeys(volatility_levels)
        for amplitude in dict.fromkeys(amplitude_levels)
    ]

    fundamentals = load_fundamentals(fundamental_path)
    market = load_market_data(provider_uri, args.start, args.end, args.batch_size)
    market = attach_quality_asof(market, fundamentals, max_age_days=args.max_quality_age_days)
    ranked = rank_factor_frame(market)
    scored = score_candidate(ranked, candidate)
    records: list[tuple[float | None, float | None, dict[str, Any], int]] = []
    for min_volatility_low_20, min_amplitude_low in configurations:
        rounds, summary = evaluate_candidate(
            scored,
            candidate,
            hold_days=args.hold_days,
            topk=args.topk,
            open_cost=args.open_cost,
            close_cost=args.close_cost,
            development_end=args.development_end,
            regime_filter=args.regime_filter,
            min_volatility_low_20=min_volatility_low_20,
            min_amplitude_low=min_amplitude_low,
        )
        active_cash_cohorts = int((rounds["regime_active"] & ~rounds["risk_gate_basket_formed"]).sum())
        records.append((min_volatility_low_20, min_amplitude_low, summary, active_cash_cohorts))

    ranking = sorted(
        records,
        key=lambda item: float((item[2].get("selection_scores") or {}).get(args.selection_policy))
        if (item[2].get("selection_scores") or {}).get(args.selection_policy) is not None
        else float("-inf"),
        reverse=True,
    )
    winning_record = next(
        (
            item
            for item in ranking
            if (item[2].get("selection_scores") or {}).get(args.selection_policy) is not None
        ),
        None,
    )
    winner = (
        {
            "min_volatility_low_20": winning_record[0],
            "min_amplitude_low": winning_record[1],
        }
        if winning_record is not None
        else None
    )
    run_id = _timestamp()
    audit = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "selection_risk_gate_sensitivity_research_only_not_investment_advice",
        "candidate": {
            "name": candidate.name,
            "description": candidate.description,
            "weights": candidate.weights,
            "candidate_library": args.candidate_library,
        },
        "strategy": {
            "universe": "buyable_main_chinext",
            "holding_period_trading_days": args.hold_days,
            "rebalancing": "non_overlapping_every_holding_period",
            "topk": args.topk,
            "regime_filter": args.regime_filter,
            "regime_filter_description": REGIME_FILTERS[args.regime_filter],
            "signal_time": "market close",
            "entry": "next local trading-session open",
            "exit": "local close after holding_period_trading_days",
            "open_cost": args.open_cost,
            "close_cost": args.close_cost,
            "risk_gate_rule": (
                "selected names must meet the configured same-close cross-sectional floors for volatility_low_20 "
                "and amplitude_low; if a complete TopK basket cannot be formed, hold cash for that cohort"
            ),
        },
        "quality_gate": {
            "source": str(fundamental_path.resolve()),
            "sha256": file_sha256(fundamental_path),
            "effective_date": "strictly next local trading day after announcement_date",
            "max_quality_age_days": args.max_quality_age_days,
        },
        "data": {
            "provider_uri": str(provider_uri.resolve()),
            "calendar_start": market["datetime"].min().date().isoformat(),
            "calendar_end": market["datetime"].max().date().isoformat(),
            "market_rows": int(len(market)),
            "eligible_rows": int(market["quality_eligible"].sum()),
            "development_end": args.development_end,
            "test_period_used_for_gate_selection": False,
        },
        "selection_policy": args.selection_policy,
        "selection_rule": f"{SELECTION_POLICIES[args.selection_policy]}; no test metrics are used for gate ranking",
        "winner_risk_gate_selected_on_development_only": winner,
        "has_development_qualified_risk_gate": winning_record is not None,
        "ranking_by_development": [
            {
                "min_volatility_low_20": min_volatility_low_20,
                "min_amplitude_low": min_amplitude_low,
                "development_selection_score": (summary.get("selection_scores") or {}).get(args.selection_policy),
                "development": summary["development"],
                "development_stability": summary.get("development_stability"),
                "test": summary["test"],
                "active_cash_cohorts_from_incomplete_risk_gate": active_cash_cohorts,
            }
            for min_volatility_low_20, min_amplitude_low, summary, active_cash_cohorts in ranking
        ],
        "limitations": [
            "This is a risk-gate sensitivity audit, not authorization to alter an existing forward candidate.",
            "The two risk features are cross-sectional ranks, not absolute volatility or intraday loss guarantees.",
            "A missing complete eligible basket is modeled as cash, not as a partial basket or replacement allocation.",
            "The current holding universe is derived from a current listing snapshot and can introduce survivorship bias in historical results.",
            "Prices use the accepted point-in-time restoration contract but do not provide exact limit-queue or fill simulation.",
        ],
    }
    destination = experiment_root / f"{run_id}_risk_gate_audit.json"
    _atomic_write_text(destination, json.dumps(audit, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return {
        "status": "completed",
        "audit_path": str(destination.resolve()),
        "candidate": candidate.name,
        "winner_risk_gate_selected_on_development_only": winner,
        "has_development_qualified_risk_gate": winning_record is not None,
        "ranking_by_development": audit["ranking_by_development"],
    }


def run_diversification_audit(args: argparse.Namespace) -> dict[str, Any]:
    """Compare small, predeclared within-basket correlation caps for one candidate."""

    provider_uri = Path(args.provider_uri).expanduser()
    fundamental_path = Path(args.fundamentals).expanduser()
    experiment_root = Path(args.experiment_root).expanduser()
    candidate = candidate_by_name(args.candidate, args.candidate_library)
    requested_caps = args.max_pairwise_correlation or list(DEFAULT_MAX_PAIRWISE_CORRELATION_CAPS)
    for max_pairwise_correlation in requested_caps:
        validate_diversification_inputs(
            max_pairwise_correlation,
            args.correlation_lookback,
            args.diversification_candidate_pool,
            args.topk,
        )
    caps: list[float | None] = [None, *sorted(set(float(value) for value in requested_caps))]

    fundamentals = load_fundamentals(fundamental_path)
    market = load_market_data(provider_uri, args.start, args.end, args.batch_size)
    market = attach_quality_asof(market, fundamentals, max_age_days=args.max_quality_age_days)
    ranked = rank_factor_frame(market)
    scored = score_candidate(ranked, candidate)
    records: list[tuple[float | None, dict[str, Any], int]] = []
    for max_pairwise_correlation in caps:
        rounds, summary = evaluate_candidate(
            scored,
            candidate,
            hold_days=args.hold_days,
            topk=args.topk,
            open_cost=args.open_cost,
            close_cost=args.close_cost,
            development_end=args.development_end,
            regime_filter=args.regime_filter,
            max_pairwise_correlation=max_pairwise_correlation,
            correlation_lookback=args.correlation_lookback,
            diversification_candidate_pool=args.diversification_candidate_pool,
        )
        active_cash_cohorts = int(
            (rounds["regime_active"] & ~rounds["diversification_basket_formed"]).sum()
        )
        records.append((max_pairwise_correlation, summary, active_cash_cohorts))

    ranking = sorted(
        records,
        key=lambda item: float((item[1].get("selection_scores") or {}).get(args.selection_policy))
        if (item[1].get("selection_scores") or {}).get(args.selection_policy) is not None
        else float("-inf"),
        reverse=True,
    )
    winning_record = next(
        (
            item
            for item in ranking
            if (item[1].get("selection_scores") or {}).get(args.selection_policy) is not None
        ),
        None,
    )
    winner = winning_record[0] if winning_record is not None else None
    run_id = _timestamp()
    audit = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "basket_diversification_sensitivity_research_only_not_investment_advice",
        "candidate": {
            "name": candidate.name,
            "description": candidate.description,
            "weights": candidate.weights,
            "candidate_library": args.candidate_library,
        },
        "strategy": {
            "universe": "buyable_main_chinext",
            "holding_period_trading_days": args.hold_days,
            "rebalancing": "non_overlapping_every_holding_period",
            "topk": args.topk,
            "regime_filter": args.regime_filter,
            "regime_filter_description": REGIME_FILTERS[args.regime_filter],
            "signal_time": "market close",
            "entry": "next local trading-session open",
            "exit": "local close after holding_period_trading_days",
            "open_cost": args.open_cost,
            "close_cost": args.close_cost,
            "correlation_lookback": args.correlation_lookback,
            "diversification_candidate_pool": args.diversification_candidate_pool,
            "diversification_rule": (
                "greedily take factor-ranked names from the top candidate pool only when every pair's trailing "
                "close-to-close return correlation is at or below the cap; if a complete TopK basket cannot be "
                "formed, hold cash for that cohort"
            ),
        },
        "quality_gate": {
            "source": str(fundamental_path.resolve()),
            "sha256": file_sha256(fundamental_path),
            "effective_date": "strictly next local trading day after announcement_date",
            "max_quality_age_days": args.max_quality_age_days,
        },
        "data": {
            "provider_uri": str(provider_uri.resolve()),
            "calendar_start": market["datetime"].min().date().isoformat(),
            "calendar_end": market["datetime"].max().date().isoformat(),
            "market_rows": int(len(market)),
            "eligible_rows": int(market["quality_eligible"].sum()),
            "development_end": args.development_end,
            "test_period_used_for_cap_selection": False,
        },
        "selection_policy": args.selection_policy,
        "selection_rule": f"{SELECTION_POLICIES[args.selection_policy]}; no test metrics are used for cap ranking",
        "winner_max_pairwise_correlation_selected_on_development_only": winner,
        "has_development_qualified_diversification_cap": winning_record is not None,
        "ranking_by_development": [
            {
                "max_pairwise_correlation": max_pairwise_correlation,
                "development_selection_score": (summary.get("selection_scores") or {}).get(args.selection_policy),
                "development": summary["development"],
                "development_stability": summary.get("development_stability"),
                "test": summary["test"],
                "active_cash_cohorts_from_incomplete_diversification": active_cash_cohorts,
            }
            for max_pairwise_correlation, summary, active_cash_cohorts in ranking
        ],
        "limitations": [
            "This diversification sensitivity audit is not authorization to alter an existing forward candidate.",
            "Return correlation is a short-window statistical proxy, not industry classification or proof of economic independence.",
            "A missing complete low-correlation basket is modeled as cash, not as a partial basket or replacement allocation.",
            "The current holding universe is derived from a current listing snapshot and can introduce survivorship bias in historical results.",
            "Prices use the accepted point-in-time restoration contract but do not provide exact limit-queue or fill simulation.",
        ],
    }
    destination = experiment_root / f"{run_id}_diversification_audit.json"
    _atomic_write_text(destination, json.dumps(audit, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return {
        "status": "completed",
        "audit_path": str(destination.resolve()),
        "candidate": candidate.name,
        "winner_max_pairwise_correlation_selected_on_development_only": winner,
        "has_development_qualified_diversification_cap": winning_record is not None,
        "ranking_by_development": audit["ranking_by_development"],
    }


def run_regime_audit(args: argparse.Namespace) -> dict[str, Any]:
    """Compare every close-known regime rule for one recorded factor mix.

    This is a sensitivity audit, not a promotion path.  The ranking explicitly
    reads only the development-period score, even when a caller supplies a
    later historical window for diagnostics.
    """

    provider_uri = Path(args.provider_uri).expanduser()
    fundamental_path = Path(args.fundamentals).expanduser()
    experiment_root = Path(args.experiment_root).expanduser()
    candidate = candidate_by_name(args.candidate, args.candidate_library)
    fundamentals = load_fundamentals(fundamental_path)
    market = load_market_data(provider_uri, args.start, args.end, args.batch_size)
    market = attach_quality_asof(market, fundamentals, max_age_days=args.max_quality_age_days)
    ranked = rank_factor_frame(market)
    scored = score_candidate(ranked, candidate)
    run_id = _timestamp()
    summaries: list[tuple[str, dict[str, Any]]] = []
    for regime_filter in REGIME_FILTERS:
        _, summary = evaluate_candidate(
            scored,
            candidate,
            hold_days=args.hold_days,
            topk=args.topk,
            open_cost=args.open_cost,
            close_cost=args.close_cost,
            development_end=args.development_end,
            regime_filter=regime_filter,
        )
        summaries.append((regime_filter, summary))
    ranking = rank_regimes_by_development(summaries, args.selection_policy)
    winner = next((regime_filter for regime_filter, _, score in ranking if score is not None), None)
    audit = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "regime_sensitivity_research_only_not_investment_advice",
        "candidate": {
            "name": candidate.name,
            "description": candidate.description,
            "weights": candidate.weights,
            "candidate_library": args.candidate_library,
        },
        "strategy": {
            "universe": "buyable_main_chinext",
            "holding_period_trading_days": args.hold_days,
            "rebalancing": "non_overlapping_every_holding_period",
            "topk": args.topk,
            "signal_time": "market close",
            "entry": "next local trading-session open",
            "exit": "local close after holding_period_trading_days",
            "open_cost": args.open_cost,
            "close_cost": args.close_cost,
        },
        "quality_gate": {
            "source": str(fundamental_path.resolve()),
            "sha256": file_sha256(fundamental_path),
            "effective_date": "strictly next local trading day after announcement_date",
            "max_quality_age_days": args.max_quality_age_days,
        },
        "data": {
            "provider_uri": str(provider_uri.resolve()),
            "calendar_start": market["datetime"].min().date().isoformat(),
            "calendar_end": market["datetime"].max().date().isoformat(),
            "market_rows": int(len(market)),
            "eligible_rows": int(market["quality_eligible"].sum()),
            "development_end": args.development_end,
            "test_period_used_for_regime_selection": False,
        },
        "selection_policy": args.selection_policy,
        "selection_rule": f"{SELECTION_POLICIES[args.selection_policy]}; no test metrics are used for regime ranking",
        "winner_regime_selected_on_development_only": winner,
        "ranking_by_development": [
            {
                "regime_filter": regime_filter,
                "regime_filter_description": REGIME_FILTERS[regime_filter],
                "development_selection_score": score,
                "development": summary["development"],
                "development_stability": summary.get("development_stability"),
                "test": summary["test"],
                "cohorts": summary["cohorts"],
            }
            for regime_filter, summary, score in ranking
        ],
        "limitations": [
            "This is a regime sensitivity audit, not an authorization to change a registered forward candidate.",
            "The current holding universe is derived from a current listing snapshot and can introduce survivorship bias in historical results.",
            "Restoration factors support raw-price reconstruction, but exact taxes, limit queues, suspensions, and fills remain unsimulated.",
        ],
    }
    destination = experiment_root / f"{run_id}_regime_audit.json"
    _atomic_write_text(destination, json.dumps(audit, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return {
        "status": "completed",
        "audit_path": str(destination.resolve()),
        "candidate": candidate.name,
        "winner_regime_selected_on_development_only": winner,
        "ranking_by_development": [
            {
                "regime_filter": regime_filter,
                "development_selection_score": score,
                "development": summary["development"],
                "test": summary["test"],
            }
            for regime_filter, summary, score in ranking
        ],
    }


def run_loss_cap_audit(args: argparse.Namespace) -> dict[str, Any]:
    """Compare close-confirmed loss caps for one fixed factor candidate.

    This is an exploratory, research-only risk-control sensitivity audit.  It
    never registers a strategy, even if an in-sample cap happens to qualify.
    """

    provider_uri = Path(args.provider_uri).expanduser()
    fundamental_path = Path(args.fundamentals).expanduser()
    experiment_root = Path(args.experiment_root).expanduser()
    candidate = candidate_by_name(args.candidate, args.candidate_library)
    requested_caps = args.close_loss_cap or list(DEFAULT_CLOSE_LOSS_CAPS)
    for close_loss_cap in requested_caps:
        validate_close_loss_cap(close_loss_cap)
    caps: list[float | None] = [None, *sorted(set(float(value) for value in requested_caps))]

    fundamentals = load_fundamentals(fundamental_path)
    market = load_market_data(provider_uri, args.start, args.end, args.batch_size)
    market = attach_quality_asof(market, fundamentals, max_age_days=args.max_quality_age_days)
    ranked = rank_factor_frame(market)
    scored = score_candidate(ranked, candidate)
    records: list[tuple[float | None, dict[str, Any], int]] = []
    for close_loss_cap in caps:
        rounds, summary = evaluate_candidate(
            scored,
            candidate,
            hold_days=args.hold_days,
            topk=args.topk,
            open_cost=args.open_cost,
            close_cost=args.close_cost,
            development_end=args.development_end,
            regime_filter=args.regime_filter,
            close_loss_cap=close_loss_cap,
        )
        early_exit_holdings = int(rounds.get("early_exit_holdings", pd.Series(dtype="int64")).sum())
        records.append((close_loss_cap, summary, early_exit_holdings))

    ranking = sorted(
        records,
        key=lambda item: float((item[1].get("selection_scores") or {}).get(args.selection_policy))
        if (item[1].get("selection_scores") or {}).get(args.selection_policy) is not None
        else float("-inf"),
        reverse=True,
    )
    winning_record = next(
        (
            item
            for item in ranking
            if (item[1].get("selection_scores") or {}).get(args.selection_policy) is not None
        ),
        None,
    )
    winner = winning_record[0] if winning_record is not None else None
    run_id = _timestamp()
    audit = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "close_loss_cap_sensitivity_research_only_not_investment_advice",
        "candidate": {
            "name": candidate.name,
            "description": candidate.description,
            "weights": candidate.weights,
            "candidate_library": args.candidate_library,
        },
        "strategy": {
            "universe": "buyable_main_chinext",
            "holding_period_trading_days": args.hold_days,
            "rebalancing": "non_overlapping_every_holding_period",
            "topk": args.topk,
            "signal_time": "market close",
            "entry": "next local trading-session open",
            "scheduled_exit": "local close after holding_period_trading_days",
            "close_loss_cap_rule": (
                "when a holding's daily close from entry through scheduled exit is at or below "
                "entry_open * (1 - close_loss_cap), assume exit at that same daily close; cash remains idle until "
                "the scheduled cohort end"
            ),
            "open_cost": args.open_cost,
            "close_cost": args.close_cost,
            "regime_filter": args.regime_filter,
            "regime_filter_description": REGIME_FILTERS[args.regime_filter],
        },
        "quality_gate": {
            "source": str(fundamental_path.resolve()),
            "sha256": file_sha256(fundamental_path),
            "effective_date": "strictly next local trading day after announcement_date",
            "max_quality_age_days": args.max_quality_age_days,
        },
        "data": {
            "provider_uri": str(provider_uri.resolve()),
            "calendar_start": market["datetime"].min().date().isoformat(),
            "calendar_end": market["datetime"].max().date().isoformat(),
            "market_rows": int(len(market)),
            "eligible_rows": int(market["quality_eligible"].sum()),
            "development_end": args.development_end,
            "test_period_used_for_cap_selection": False,
        },
        "selection_policy": args.selection_policy,
        "selection_rule": f"{SELECTION_POLICIES[args.selection_policy]}; no test metrics are used for cap ranking",
        "winner_close_loss_cap_selected_on_development_only": winner,
        "has_development_qualified_loss_cap": winning_record is not None,
        "ranking_by_development": [
            {
                "close_loss_cap": close_loss_cap,
                "development_selection_score": (summary.get("selection_scores") or {}).get(args.selection_policy),
                "development": summary["development"],
                "development_stability": summary.get("development_stability"),
                "test": summary["test"],
                "early_exit_holdings": early_exit_holdings,
            }
            for close_loss_cap, summary, early_exit_holdings in ranking
        ],
        "limitations": [
            "This is a loss-cap sensitivity audit, not authorization to apply a cap to an existing forward candidate.",
            "An assumed same-close exit is a market-on-close approximation, not proof that an order would fill at that price.",
            "The accepted restoration contract supports raw prices and lot sizing, but cannot simulate exact limit availability, suspensions, fills, or taxes.",
            "The current holding universe is derived from a current listing snapshot and can introduce survivorship bias in historical results.",
        ],
    }
    destination = experiment_root / f"{run_id}_loss_cap_audit.json"
    _atomic_write_text(destination, json.dumps(audit, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return {
        "status": "completed",
        "audit_path": str(destination.resolve()),
        "candidate": candidate.name,
        "winner_close_loss_cap_selected_on_development_only": winner,
        "has_development_qualified_loss_cap": winning_record is not None,
        "ranking_by_development": audit["ranking_by_development"],
    }


def run_entry_gap_audit(args: argparse.Namespace) -> dict[str, Any]:
    """Compare predeclared next-open entry-gap ceilings for one fixed candidate.

    The decision is intentionally made at the next session's open: if any of
    the scheduled TopK names gaps above the ceiling, the whole cohort holds
    cash.  This preserves a complete-basket assumption and avoids replacing a
    rejected name with an untested fourth choice.
    """

    provider_uri = Path(args.provider_uri).expanduser()
    fundamental_path = Path(args.fundamentals).expanduser()
    experiment_root = Path(args.experiment_root).expanduser()
    candidate = candidate_by_name(args.candidate, args.candidate_library)
    requested_caps = args.max_entry_gap or list(DEFAULT_ENTRY_GAP_CAPS)
    for max_entry_gap in requested_caps:
        validate_entry_gap_cap(max_entry_gap)
    caps: list[float | None] = [None, *sorted(set(float(value) for value in requested_caps))]

    fundamentals = load_fundamentals(fundamental_path)
    market = load_market_data(provider_uri, args.start, args.end, args.batch_size)
    market = attach_quality_asof(market, fundamentals, max_age_days=args.max_quality_age_days)
    ranked = rank_factor_frame(market)
    scored = score_candidate(ranked, candidate)
    records: list[tuple[float | None, dict[str, Any], int]] = []
    for max_entry_gap in caps:
        rounds, summary = evaluate_candidate(
            scored,
            candidate,
            hold_days=args.hold_days,
            topk=args.topk,
            open_cost=args.open_cost,
            close_cost=args.close_cost,
            development_end=args.development_end,
            regime_filter=args.regime_filter,
            max_entry_gap=max_entry_gap,
        )
        cash_cohorts = int((rounds["regime_active"] & rounds["holdings"].eq(0)).sum())
        records.append((max_entry_gap, summary, cash_cohorts))

    ranking = sorted(
        records,
        key=lambda item: float((item[1].get("selection_scores") or {}).get(args.selection_policy))
        if (item[1].get("selection_scores") or {}).get(args.selection_policy) is not None
        else float("-inf"),
        reverse=True,
    )
    winning_record = next(
        (
            item
            for item in ranking
            if (item[1].get("selection_scores") or {}).get(args.selection_policy) is not None
        ),
        None,
    )
    winner = winning_record[0] if winning_record is not None else None
    run_id = _timestamp()
    audit = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "next_open_entry_gap_sensitivity_research_only_not_investment_advice",
        "candidate": {
            "name": candidate.name,
            "description": candidate.description,
            "weights": candidate.weights,
            "candidate_library": args.candidate_library,
        },
        "strategy": {
            "universe": "buyable_main_chinext",
            "holding_period_trading_days": args.hold_days,
            "rebalancing": "non_overlapping_every_holding_period",
            "topk": args.topk,
            "signal_time": "market close",
            "entry": "next local trading-session open",
            "scheduled_exit": "local close after holding_period_trading_days",
            "entry_gap_rule": (
                "at the next-session open, form the scheduled complete TopK basket only when every selected name has "
                "entry_open / signal_close - 1 at or below max_entry_gap; otherwise the entire cohort holds cash"
            ),
            "open_cost": args.open_cost,
            "close_cost": args.close_cost,
            "regime_filter": args.regime_filter,
            "regime_filter_description": REGIME_FILTERS[args.regime_filter],
        },
        "quality_gate": {
            "source": str(fundamental_path.resolve()),
            "sha256": file_sha256(fundamental_path),
            "effective_date": "strictly next local trading day after announcement_date",
            "max_quality_age_days": args.max_quality_age_days,
        },
        "data": {
            "provider_uri": str(provider_uri.resolve()),
            "calendar_start": market["datetime"].min().date().isoformat(),
            "calendar_end": market["datetime"].max().date().isoformat(),
            "market_rows": int(len(market)),
            "eligible_rows": int(market["quality_eligible"].sum()),
            "development_end": args.development_end,
            "test_period_used_for_entry_gap_selection": False,
        },
        "selection_policy": args.selection_policy,
        "selection_rule": f"{SELECTION_POLICIES[args.selection_policy]}; no test metrics are used for entry-gap ranking",
        "winner_max_entry_gap_selected_on_development_only": winner,
        "has_development_qualified_entry_gap": winning_record is not None,
        "ranking_by_development": [
            {
                "max_entry_gap": max_entry_gap,
                "development_selection_score": (summary.get("selection_scores") or {}).get(args.selection_policy),
                "development": summary["development"],
                "development_stability": summary.get("development_stability"),
                "test": summary["test"],
                "cash_cohorts": cash_cohorts,
            }
            for max_entry_gap, summary, cash_cohorts in ranking
        ],
        "limitations": [
            "This is an execution sensitivity audit, not authorization to apply an entry-gap ceiling to an existing forward candidate.",
            "The next-session opening price is observable only after the close-based signal; a rapid market move can make a real order unavailable or different from the adjusted open.",
            "The accepted restoration contract supports raw prices and lot sizing, but cannot simulate opening-auction priority, exact limit availability, suspensions, fills, or taxes.",
            "The current holding universe is derived from a current listing snapshot and can introduce survivorship bias in historical results.",
        ],
    }
    destination = experiment_root / f"{run_id}_entry_gap_audit.json"
    _atomic_write_text(destination, json.dumps(audit, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return {
        "status": "completed",
        "audit_path": str(destination.resolve()),
        "candidate": candidate.name,
        "winner_max_entry_gap_selected_on_development_only": winner,
        "has_development_qualified_entry_gap": winning_record is not None,
        "ranking_by_development": audit["ranking_by_development"],
    }


def run_walk_forward_selection_audit(args: argparse.Namespace) -> dict[str, Any]:
    """Audit a factor library with expanding, calendar-year training windows.

    Each fold selects exactly one candidate using only cohorts whose exits were
    known by that fold's training end.  The next calendar year's completed
    cohorts are then held out as a genuine historical validation slice.  This
    is an audit of a strategy family, never a new forward registration or an
    authorization to replace a current paper observation.
    """

    provider_uri = Path(args.provider_uri).expanduser()
    fundamental_path = Path(args.fundamentals).expanduser()
    experiment_root = Path(args.experiment_root).expanduser()
    candidates = candidate_library(args.candidate_library)
    if args.first_test_year > args.last_test_year:
        raise ValueError("first_test_year must not exceed last_test_year")

    fundamentals = load_fundamentals(fundamental_path)
    market = load_market_data(provider_uri, args.start, args.end, args.batch_size)
    calendar_start = pd.Timestamp(market["datetime"].min()).normalize()
    calendar_end = pd.Timestamp(market["datetime"].max()).normalize()
    if args.first_test_year - calendar_start.year < 2:
        raise ValueError("walk-forward audit requires at least two full prior calendar years of training data")
    if args.last_test_year > calendar_end.year:
        raise ValueError("last_test_year exceeds the locally available daily-data calendar")

    market = attach_quality_asof(market, fundamentals, max_age_days=args.max_quality_age_days)
    ranked = rank_factor_frame(market)
    candidate_rounds: dict[str, pd.DataFrame] = {}
    for candidate in candidates:
        scored = score_candidate(ranked, candidate)
        rounds, _ = evaluate_candidate(
            scored,
            candidate,
            hold_days=args.hold_days,
            topk=args.topk,
            open_cost=args.open_cost,
            close_cost=args.close_cost,
            development_end=calendar_end.date().isoformat(),
            regime_filter=args.regime_filter,
        )
        candidate_rounds[candidate.name] = rounds

    folds: list[dict[str, Any]] = []
    selected_test_rounds: list[pd.DataFrame] = []
    for test_year in range(args.first_test_year, args.last_test_year + 1):
        train_end = pd.Timestamp(f"{test_year - 1}-12-31")
        test_start = pd.Timestamp(f"{test_year}-01-01")
        test_end = min(pd.Timestamp(f"{test_year}-12-31"), calendar_end)
        fold, test_rounds = walk_forward_fold_result(
            candidate_rounds,
            train_start=calendar_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
            hold_days=args.hold_days,
            selection_policy=args.selection_policy,
        )
        folds.append(fold)
        if not test_rounds.empty:
            selected_test_rounds.append(test_rounds.assign(walk_forward_test_year=test_year))

    combined_test_rounds = (
        pd.concat(selected_test_rounds, ignore_index=True).sort_values("signal_date", kind="stable")
        if selected_test_rounds
        else pd.DataFrame()
    )
    run_id = _timestamp()
    aggregate = return_metrics(combined_test_rounds, args.hold_days)
    audit = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "expanding_window_candidate_selection_audit_research_only_not_investment_advice",
        "candidate_library": {
            "id": args.candidate_library,
            "count": len(candidates),
            "construction": CANDIDATE_LIBRARY_DESCRIPTIONS[args.candidate_library],
            "fingerprint_sha256": candidate_library_fingerprint(candidates),
        },
        "strategy": {
            "universe": "buyable_main_chinext",
            "holding_period_trading_days": args.hold_days,
            "rebalancing": "non_overlapping_every_holding_period",
            "topk": args.topk,
            "signal_time": "market close",
            "entry": "next local trading-session open",
            "exit": "local close after holding_period_trading_days",
            "open_cost": args.open_cost,
            "close_cost": args.close_cost,
            "regime_filter": args.regime_filter,
            "regime_filter_description": REGIME_FILTERS[args.regime_filter],
        },
        "selection_policy": args.selection_policy,
        "selection_rule": (
            f"{SELECTION_POLICIES[args.selection_policy]}; each fold selects only on completed training cohorts, "
            "and its following calendar-year test metrics are excluded from selection"
        ),
        "quality_gate": {
            "source": str(fundamental_path.resolve()),
            "sha256": file_sha256(fundamental_path),
            "effective_date": "strictly next local trading day after announcement_date",
            "max_quality_age_days": args.max_quality_age_days,
        },
        "data": {
            "provider_uri": str(provider_uri.resolve()),
            "calendar_start": calendar_start.date().isoformat(),
            "calendar_end": calendar_end.date().isoformat(),
            "market_rows": int(len(market)),
            "eligible_rows": int(market["quality_eligible"].sum()),
            "test_period_used_for_candidate_selection": False,
        },
        "protocol": {
            "first_test_year": args.first_test_year,
            "last_test_year": args.last_test_year,
            "training_window": "expanding from the requested calendar start through the prior calendar year",
            "fold_boundary_rule": "only cohorts with scheduled exits inside each train or test window are included",
        },
        "folds": folds,
        "aggregate_selected_out_of_sample": aggregate,
        "unique_fold_winners": sorted(
            {str(fold["winner_selected_on_training_only"]) for fold in folds if fold["winner_selected_on_training_only"]}
        ),
        "limitations": [
            "This audit checks historical candidate-selection stability; it does not promote a candidate or create a forward signal.",
            "The current holding universe is derived from a current listing snapshot and can introduce survivorship bias in historical results.",
            "Restoration factors support raw-price and lot-size reconstruction, but cannot prove limit queues, suspensions, fills, or exact-tax execution.",
        ],
    }
    destination = experiment_root / f"{run_id}_walk_forward_selection_audit.json"
    _atomic_write_text(destination, json.dumps(audit, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return {
        "status": "completed",
        "audit_path": str(destination.resolve()),
        "candidate_library": args.candidate_library,
        "fold_count": len(folds),
        "qualified_fold_count": sum(fold["winner_selected_on_training_only"] is not None for fold in folds),
        "unique_fold_winners": audit["unique_fold_winners"],
        "aggregate_selected_out_of_sample": aggregate,
    }


def run_research(args: argparse.Namespace) -> dict[str, Any]:
    """Run all candidate combinations and write a record for each one."""

    provider_uri = Path(args.provider_uri).expanduser()
    fundamental_path = Path(args.fundamentals).expanduser()
    experiment_root = Path(args.experiment_root).expanduser()
    candidates = candidate_library(args.candidate_library)
    fundamentals = load_fundamentals(fundamental_path)
    market = load_market_data(provider_uri, args.start, args.end, args.batch_size)
    price_basis_metadata = research_price_basis_metadata(provider_uri)
    market = attach_quality_asof(market, fundamentals, max_age_days=args.max_quality_age_days)
    ranked = rank_factor_frame(market)
    run_id = _timestamp()
    common = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "research_only_not_investment_advice",
        "candidate_library": {
            "id": args.candidate_library,
            "count": len(candidates),
            "construction": CANDIDATE_LIBRARY_DESCRIPTIONS[args.candidate_library],
            "fingerprint_sha256": candidate_library_fingerprint(candidates),
            "test_period_used_for_candidate_design": False,
        },
        "strategy": {
            "universe": "buyable_main_chinext",
            "holding_period_trading_days": args.hold_days,
            "rebalancing": "non_overlapping_every_holding_period",
            "topk": args.topk,
            "signal_time": "market close",
            "entry": "next local trading-session open",
            "exit": "local close after holding_period_trading_days",
            "open_cost": args.open_cost,
            "close_cost": args.close_cost,
            "regime_filter": args.regime_filter,
            "regime_filter_description": REGIME_FILTERS[args.regime_filter],
            "candidate_library": args.candidate_library,
            "selection_policy": args.selection_policy,
        },
        "quality_gate": {
            "source": str(fundamental_path.resolve()),
            "sha256": file_sha256(fundamental_path),
            "annual_report_only": True,
            "effective_date": "strictly next local trading day after announcement_date",
            "max_quality_age_days": args.max_quality_age_days,
            "requirements": {
                "weighted_average_roe_gte": 5.0,
                "parent_net_profit_gt": 0.0,
                "revenue_yoy_gt": 0.0,
                "profit_yoy_gt": 0.0,
            },
        },
        "data": {
            "provider_uri": str(provider_uri.resolve()),
            "calendar_start": market["datetime"].min().date().isoformat(),
            "calendar_end": market["datetime"].max().date().isoformat(),
            "market_rows": int(len(market)),
            "eligible_rows": int(market["quality_eligible"].sum()),
            "development_end": args.development_end,
            "test_window_is_newly_reserved": not args.research_only,
            **price_basis_metadata,
        },
        "limitations": [
            "The current holding universe is derived from a current listing snapshot and can introduce survivorship bias in historical results.",
            "Eastmoney public data are a present-day snapshot; retaining the earliest visible notice date reduces but does not eliminate accounting restatement bias.",
            "Restoration factors support raw-price and lot-size reconstruction, but this is not an exact tax, limit-queue, suspension, or fill simulation.",
            "The winner is selected only on development data. Its later test result is evidence for further research, never a promise of future return.",
        ],
    }
    summaries: list[dict[str, Any]] = []
    records: list[tuple[dict[str, Any], Path]] = []
    for candidate in candidates:
        scored = score_candidate(ranked, candidate)
        _, summary = evaluate_candidate(
            scored,
            candidate,
            hold_days=args.hold_days,
            topk=args.topk,
            open_cost=args.open_cost,
            close_cost=args.close_cost,
            development_end=args.development_end,
            regime_filter=args.regime_filter,
        )
        record = {**common, **summary, "candidate": candidate.name}
        destination = write_experiment_record(experiment_root, record)
        records.append((record, destination))
        summaries.append(summary)
        print(f"{candidate.name}: {destination}")
    winner = choose_winner(summaries, args.selection_policy)
    for record, destination in records:
        record["selected_by_development"] = record["candidate"] == winner
        _atomic_write_text(destination, json.dumps(record, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    ranking = sorted(
        records,
        key=lambda item: float((item[0].get("selection_scores") or {}).get(args.selection_policy))
        if (item[0].get("selection_scores") or {}).get(args.selection_policy) is not None
        else float("-inf"),
        reverse=True,
    )
    study = {
        "run_id": run_id,
        "status": "completed",
        "candidate_library": args.candidate_library,
        "candidate_count": len(candidates),
        "candidate_construction": CANDIDATE_LIBRARY_DESCRIPTIONS[args.candidate_library],
        "candidate_library_fingerprint_sha256": candidate_library_fingerprint(candidates),
        "selection_policy": args.selection_policy,
        "selection_rule": f"{SELECTION_POLICIES[args.selection_policy]}; no test metrics are used for selection",
        "data": dict(common["data"]),
        "winner_selected_on_development_only": winner,
        "ranking_by_development": [
            {
                "candidate": record["candidate"],
                "path": str(destination.resolve()),
                "development_selection_score": (record.get("selection_scores") or {}).get(args.selection_policy),
                "development": record["development"],
                "development_stability": record.get("development_stability"),
                "test": record["test"],
            }
            for record, destination in ranking
        ],
    }
    study_path = experiment_root / f"{run_id}_study.json"
    _atomic_write_text(study_path, json.dumps(study, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    study["study_path"] = str(study_path.resolve())
    if winner is None:
        study["status"] = "no_eligible_candidate"
        study["reason"] = (
            "No candidate satisfied the development-only selection policy; no strategy iteration was registered "
            "and no forward observation can be created from this sweep."
        )
        _atomic_write_text(study_path, json.dumps(study, ensure_ascii=False, indent=2, default=_json_default) + "\n")
        return study
    winner_record = next(record for record, _ in records if record["candidate"] == winner)
    label = args.iteration_label or f"hold_{args.hold_days}d_top_{args.topk}"
    iteration = build_iteration_record(
        run_id=run_id,
        label=label,
        strategy=common["strategy"],
        study_path=study_path,
        winner=winner_record,
        candidate_count=len(candidates),
        candidate_library_id=args.candidate_library,
        candidate_library_sha256=candidate_library_fingerprint(candidates),
        data=common["data"],
        promotion_eligible=not args.research_only,
        selection_policy=args.selection_policy,
    )
    registry_path = append_strategy_registry(Path(args.registry_path), iteration)
    study["iteration_id"] = iteration["iteration_id"]
    study["strategy_registry_path"] = str(registry_path.resolve())
    _atomic_write_text(study_path, json.dumps(study, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return study


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync = subparsers.add_parser("sync-fundamentals", help="download annual ROE/profit/revenue quality inputs")
    sync.add_argument("--start-year", type=int, default=2022)
    sync.add_argument("--end-year", type=int, default=2025)
    sync.add_argument("--output", default=str(DEFAULT_FUNDAMENTALS))
    sync.add_argument("--manifest", default=str(DEFAULT_FUNDAMENTAL_MANIFEST))

    sync_quarterly = subparsers.add_parser(
        "sync-quarterly-fundamentals", help="download quarterly ROE/profit/revenue inputs with announcement dates"
    )
    sync_quarterly.add_argument("--start-year", type=int, default=2019)
    sync_quarterly.add_argument("--end-year", type=int, default=2026)
    sync_quarterly.add_argument(
        "--through-report-date", help="latest already-public report period to request, such as 2026-03-31"
    )
    sync_quarterly.add_argument("--output", default=str(DEFAULT_QUARTERLY_FUNDAMENTALS))
    sync_quarterly.add_argument("--manifest", default=str(DEFAULT_QUARTERLY_FUNDAMENTAL_MANIFEST))

    merge_quarterly = subparsers.add_parser(
        "merge-quarterly-fundamentals", help="atomically merge independently downloaded quarterly snapshot chunks"
    )
    merge_quarterly.add_argument("--input", action="append", required=True, help="repeat one or more parquet inputs")
    merge_quarterly.add_argument("--output", default=str(DEFAULT_QUARTERLY_FUNDAMENTALS))
    merge_quarterly.add_argument("--manifest", default=str(DEFAULT_QUARTERLY_FUNDAMENTAL_MANIFEST))

    sync_forecasts = subparsers.add_parser(
        "sync-performance-forecasts",
        help="download dated public net-profit forecast notices for event-factor research",
    )
    sync_forecasts.add_argument("--start-year", type=int, default=2019)
    sync_forecasts.add_argument("--end-year", type=int, default=2026)
    sync_forecasts.add_argument(
        "--through-report-date", help="latest forecast accounting period already public, such as 2026-06-30"
    )
    sync_forecasts.add_argument("--output", default=str(DEFAULT_PERFORMANCE_FORECASTS))
    sync_forecasts.add_argument("--manifest", default=str(DEFAULT_PERFORMANCE_FORECAST_MANIFEST))

    sync_billboard = subparsers.add_parser(
        "sync-billboard-events",
        help="download public daily billboard event aggregates for short-horizon event research",
    )
    sync_billboard.add_argument("--start-year", type=int, default=2019)
    sync_billboard.add_argument("--end-year", type=int, default=2026)
    sync_billboard.add_argument("--output", default=str(DEFAULT_BILLBOARD_EVENTS))
    sync_billboard.add_argument("--manifest", default=str(DEFAULT_BILLBOARD_EVENT_MANIFEST))

    sync_major_holder = subparsers.add_parser(
        "sync-major-holder-events",
        help="download public major-holder increase/decrease notices for short-horizon event research",
    )
    sync_major_holder.add_argument("--start-year", type=int, default=2019)
    sync_major_holder.add_argument("--end-year", type=int, default=2026)
    sync_major_holder.add_argument("--output", default=str(DEFAULT_MAJOR_HOLDER_EVENTS))
    sync_major_holder.add_argument("--manifest", default=str(DEFAULT_MAJOR_HOLDER_EVENT_MANIFEST))

    sync_block_trade = subparsers.add_parser(
        "sync-block-trade-events",
        help="download public daily block-trade aggregates for short-horizon event research",
    )
    sync_block_trade.add_argument("--start-year", type=int, default=2019)
    sync_block_trade.add_argument("--end-year", type=int, default=2026)
    sync_block_trade.add_argument("--output", default=str(DEFAULT_BLOCK_TRADE_EVENTS))
    sync_block_trade.add_argument("--manifest", default=str(DEFAULT_BLOCK_TRADE_EVENT_MANIFEST))

    sync_margin_financing = subparsers.add_parser(
        "sync-margin-financing-events",
        help="download a fixed daily Top-N public financing-flow event snapshot for short-horizon research",
    )
    sync_margin_financing.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    sync_margin_financing.add_argument("--start", default="2019-01-01")
    sync_margin_financing.add_argument("--end", help="defaults to the latest local Qlib calendar session")
    sync_margin_financing.add_argument("--top-n", type=int, default=MARGIN_FINANCING_TOP_N)
    sync_margin_financing.add_argument("--output", default=str(DEFAULT_MARGIN_FINANCING_EVENTS))
    sync_margin_financing.add_argument("--manifest", default=str(DEFAULT_MARGIN_FINANCING_EVENT_MANIFEST))
    sync_margin_financing.add_argument(
        "--merge-existing",
        action="store_true",
        help="replace matching instrument/date rows in an existing snapshot while preserving earlier dates",
    )

    sync_institutional_survey = subparsers.add_parser(
        "sync-institutional-survey-events",
        help="experimental source probe; not eligible for research until a complete historical snapshot succeeds",
    )
    sync_institutional_survey.add_argument("--start-year", type=int, default=2019)
    sync_institutional_survey.add_argument("--end-year", type=int, default=2026)
    sync_institutional_survey.add_argument("--output", default=str(DEFAULT_INSTITUTIONAL_SURVEY_EVENTS))
    sync_institutional_survey.add_argument(
        "--manifest", default=str(DEFAULT_INSTITUTIONAL_SURVEY_EVENT_MANIFEST)
    )

    sync_repurchase = subparsers.add_parser(
        "sync-repurchase-plan-events",
        help="download dated public initial repurchase plans for short-horizon event research",
    )
    sync_repurchase.add_argument("--output", default=str(DEFAULT_REPURCHASE_EVENTS))
    sync_repurchase.add_argument("--manifest", default=str(DEFAULT_REPURCHASE_EVENT_MANIFEST))

    sync_holder_count = subparsers.add_parser(
        "sync-holder-count-events",
        help="download dated public shareholder-count changes for short-horizon event research",
    )
    sync_holder_count.add_argument("--start-year", type=int, default=2019)
    sync_holder_count.add_argument("--end-year", type=int, default=2026)
    sync_holder_count.add_argument("--output", default=str(DEFAULT_HOLDER_COUNT_EVENTS))
    sync_holder_count.add_argument("--manifest", default=str(DEFAULT_HOLDER_COUNT_EVENT_MANIFEST))

    sync_pledge = subparsers.add_parser(
        "sync-pledge-events",
        help="download dated public share-pledge notices for short-horizon event research",
    )
    sync_pledge.add_argument("--start-year", type=int, default=2019)
    sync_pledge.add_argument("--end-year", type=int, default=2026)
    sync_pledge.add_argument("--output", default=str(DEFAULT_PLEDGE_EVENTS))
    sync_pledge.add_argument("--manifest", default=str(DEFAULT_PLEDGE_EVENT_MANIFEST))

    sync_dividend_plan = subparsers.add_parser(
        "sync-dividend-plan-events",
        help="download dated public initial dividend-plan notices for short-horizon event research",
    )
    sync_dividend_plan.add_argument("--start-year", type=int, default=2019)
    sync_dividend_plan.add_argument("--end-year", type=int, default=2026)
    sync_dividend_plan.add_argument("--output", default=str(DEFAULT_DIVIDEND_PLAN_EVENTS))
    sync_dividend_plan.add_argument("--manifest", default=str(DEFAULT_DIVIDEND_PLAN_EVENT_MANIFEST))

    run = subparsers.add_parser("run", help="run the predeclared short-horizon factor sweep")
    run.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    run.add_argument("--fundamentals", default=str(DEFAULT_FUNDAMENTALS))
    run.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    run.add_argument("--start", default="2024-01-01")
    run.add_argument("--end", help="defaults to the local Qlib calendar end")
    run.add_argument("--development-end", default="2025-12-31")
    run.add_argument("--hold-days", type=int, default=3, help="holding period in local trading days; 3 is the short-term research default")
    run.add_argument("--topk", type=int, default=30)
    run.add_argument("--open-cost", type=float, default=0.0015)
    run.add_argument("--close-cost", type=float, default=0.0025)
    run.add_argument("--regime-filter", choices=sorted(REGIME_FILTERS), default="always")
    run.add_argument("--max-quality-age-days", type=int, default=550)
    run.add_argument("--batch-size", type=int, default=500)
    run.add_argument("--candidate-library", choices=sorted(CANDIDATE_LIBRARIES), default="v1")
    run.add_argument("--selection-policy", choices=sorted(SELECTION_POLICIES), default="pooled_return_drawdown")
    run.add_argument("--registry-path", default=str(DEFAULT_STRATEGY_REGISTRY))
    run.add_argument("--iteration-label", help="human-readable immutable label for this research cycle")
    run.add_argument(
        "--research-only",
        action="store_true",
        help="record a historical diagnostic without allowing promotion; use when the later window has already been reviewed",
    )

    factor_diagnostic = subparsers.add_parser(
        "factor-diagnostic", help="measure development-only three-day rank IC and TopK spread for every declared factor"
    )
    factor_diagnostic.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    factor_diagnostic.add_argument("--fundamentals", default=str(DEFAULT_FUNDAMENTALS))
    factor_diagnostic.add_argument(
        "--performance-forecasts",
        help="optional dated performance-forecast event snapshot; adds event factors to the development-only diagnostic",
    )
    factor_diagnostic.add_argument(
        "--billboard-events",
        help="optional daily-billboard event snapshot; adds same-close event factors to the development-only diagnostic",
    )
    factor_diagnostic.add_argument(
        "--major-holder-events",
        help="optional dated major-holder change notices; adds next-session event factors to the development-only diagnostic",
    )
    factor_diagnostic.add_argument(
        "--block-trade-events",
        help="optional daily block-trade snapshot; adds same-close event factors to the development-only diagnostic",
    )
    factor_diagnostic.add_argument(
        "--margin-financing-events",
        help="optional fixed Top-N daily financing-flow snapshot; adds same-close event factors to the development-only diagnostic",
    )
    factor_diagnostic.add_argument(
        "--institutional-survey-events",
        help="optional dated institutional-survey notice snapshot; adds next-session event factors to the development-only diagnostic",
    )
    factor_diagnostic.add_argument(
        "--repurchase-events",
        help="optional initial repurchase-plan snapshot; adds next-session plan factors to the development-only diagnostic",
    )
    factor_diagnostic.add_argument(
        "--holder-count-events",
        help="optional dated shareholder-count change snapshot; adds next-session event factors to the development-only diagnostic",
    )
    factor_diagnostic.add_argument(
        "--pledge-events",
        help="optional dated share-pledge notice snapshot; adds next-session event factors to the development-only diagnostic",
    )
    factor_diagnostic.add_argument(
        "--dividend-plan-events",
        help="optional dated initial dividend-plan notice snapshot; adds next-session event factors to the development-only diagnostic",
    )
    factor_diagnostic.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    factor_diagnostic.add_argument("--start", default="2019-01-01")
    factor_diagnostic.add_argument("--end", default="2025-12-31")
    factor_diagnostic.add_argument("--development-end", default="2025-12-31")
    factor_diagnostic.add_argument("--hold-days", type=int, default=3)
    factor_diagnostic.add_argument("--topk", type=int, default=3)
    factor_diagnostic.add_argument("--open-cost", type=float, default=0.0015)
    factor_diagnostic.add_argument("--close-cost", type=float, default=0.0025)
    factor_diagnostic.add_argument("--max-quality-age-days", type=int, default=550)
    factor_diagnostic.add_argument(
        "--max-forecast-age-days",
        type=int,
        default=30,
        help="maximum calendar age for a public forecast event; default targets the immediate post-announcement window",
    )
    factor_diagnostic.add_argument(
        "--max-billboard-age-days",
        type=int,
        default=3,
        help="maximum calendar age for a daily billboard event; default matches the three-day holding horizon",
    )
    factor_diagnostic.add_argument(
        "--max-major-holder-age-days",
        type=int,
        default=3,
        help="maximum calendar age for a major-holder notice; default matches the three-day holding horizon",
    )
    factor_diagnostic.add_argument(
        "--max-block-trade-age-days",
        type=int,
        default=3,
        help="maximum calendar age for a block trade; default matches the three-day holding horizon",
    )
    factor_diagnostic.add_argument(
        "--max-margin-financing-age-days",
        type=int,
        default=0,
        help="maximum calendar age for a daily financing-flow event; default keeps only its same-close signal",
    )
    factor_diagnostic.add_argument(
        "--max-institutional-survey-age-days",
        type=int,
        default=3,
        help="maximum calendar age for an institutional-survey notice; default matches the three-day holding horizon",
    )
    factor_diagnostic.add_argument(
        "--max-repurchase-age-days",
        type=int,
        default=3,
        help="maximum calendar age for an initial repurchase plan; default matches the three-day holding horizon",
    )
    factor_diagnostic.add_argument(
        "--max-holder-count-age-days",
        type=int,
        default=3,
        help="maximum calendar age for a shareholder-count notice; default matches the three-day holding horizon",
    )
    factor_diagnostic.add_argument(
        "--max-pledge-age-days",
        type=int,
        default=3,
        help="maximum calendar age for a share-pledge notice; default matches the three-day holding horizon",
    )
    factor_diagnostic.add_argument(
        "--max-dividend-plan-age-days",
        type=int,
        default=3,
        help="maximum calendar age for an initial dividend plan; default matches the three-day holding horizon",
    )
    factor_diagnostic.add_argument("--batch-size", type=int, default=500)
    factor_diagnostic.add_argument(
        "--factor",
        action="append",
        help="optional exact predeclared factor to diagnose; repeat to run an explicitly isolated factor set",
    )

    rolling_window_semantics = subparsers.add_parser(
        "rolling-window-semantics-audit",
        help="verify that declared rolling fields stay missing until their full history exists, without returns",
    )
    rolling_window_semantics.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    rolling_window_semantics.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    rolling_window_semantics.add_argument("--start", default="2015-01-01")
    rolling_window_semantics.add_argument("--end", help="defaults to the latest local Qlib calendar session")
    rolling_window_semantics.add_argument("--batch-size", type=int, default=500)

    factor_stability_audit = subparsers.add_parser(
        "factor-stability-audit",
        help="apply one fixed development-only cross-year stability screen to a saved factor diagnostic",
    )
    factor_stability_audit.add_argument("--diagnostic", required=True)
    factor_stability_audit.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    factor_stability_audit.add_argument(
        "--factor",
        action="append",
        help="optional exact factor name to audit; repeat to restrict the saved diagnostic",
    )
    factor_stability_audit.add_argument(
        "--minimum-calendar-years", type=int, default=FACTOR_STABILITY_MIN_CALENDAR_YEARS
    )
    factor_stability_audit.add_argument("--minimum-cohorts", type=int, default=FACTOR_STABILITY_MIN_COHORTS)

    factor_topk_viability_audit = subparsers.add_parser(
        "factor-topk-viability-audit",
        help="screen saved factor diagnostics as exact development-only TopK baskets after research costs",
    )
    factor_topk_viability_audit.add_argument("--diagnostic", required=True)
    factor_topk_viability_audit.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    factor_topk_viability_audit.add_argument(
        "--factor",
        action="append",
        help="optional exact factor name to audit; repeat to restrict the saved diagnostic",
    )

    selection_multiplicity_audit = subparsers.add_parser(
        "selection-multiplicity-audit",
        help="audit a stored development winner for candidate-library search multiplicity",
    )
    selection_multiplicity_audit.add_argument("--study", required=True)
    selection_multiplicity_audit.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    selection_multiplicity_audit.add_argument("--hold-days", type=int, default=3)
    selection_multiplicity_audit.add_argument(
        "--bootstrap-replicates", type=int, default=SELECTION_MULTIPLICITY_DEFAULT_BOOTSTRAP_REPLICATES
    )
    selection_multiplicity_audit.add_argument(
        "--block-cohorts", type=int, default=SELECTION_MULTIPLICITY_DEFAULT_BLOCK_COHORTS
    )
    selection_multiplicity_audit.add_argument("--seed", type=int, default=SELECTION_MULTIPLICITY_DEFAULT_SEED)

    limit_like_event_audit = subparsers.add_parser(
        "limit-like-event-audit",
        help="test the fixed development-only limit-like strong-close continuation event",
    )
    limit_like_event_audit.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    limit_like_event_audit.add_argument("--fundamentals", default=str(DEFAULT_FUNDAMENTALS))
    limit_like_event_audit.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    limit_like_event_audit.add_argument("--start", default="2019-01-01")
    limit_like_event_audit.add_argument("--end", default="2025-12-31")
    limit_like_event_audit.add_argument("--development-end", default="2025-12-31")
    limit_like_event_audit.add_argument("--hold-days", type=int, default=3)
    limit_like_event_audit.add_argument("--topk", type=int, default=3)
    limit_like_event_audit.add_argument("--open-cost", type=float, default=0.00012)
    limit_like_event_audit.add_argument("--close-cost", type=float, default=0.00062)
    limit_like_event_audit.add_argument("--max-quality-age-days", type=int, default=550)
    limit_like_event_audit.add_argument("--batch-size", type=int, default=500)

    quarterly_profit_acceleration_event_audit = subparsers.add_parser(
        "quarterly-profit-acceleration-event-audit",
        help="test the fixed development-only quarterly profit-acceleration drift event",
    )
    quarterly_profit_acceleration_event_audit.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    quarterly_profit_acceleration_event_audit.add_argument(
        "--fundamentals", default=str(DEFAULT_QUARTERLY_FUNDAMENTALS)
    )
    quarterly_profit_acceleration_event_audit.add_argument(
        "--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT)
    )
    quarterly_profit_acceleration_event_audit.add_argument("--start", default="2019-01-01")
    quarterly_profit_acceleration_event_audit.add_argument("--end", default="2025-12-31")
    quarterly_profit_acceleration_event_audit.add_argument("--development-end", default="2025-12-31")
    quarterly_profit_acceleration_event_audit.add_argument("--hold-days", type=int, default=3)
    quarterly_profit_acceleration_event_audit.add_argument("--topk", type=int, default=3)
    quarterly_profit_acceleration_event_audit.add_argument("--open-cost", type=float, default=0.00012)
    quarterly_profit_acceleration_event_audit.add_argument("--close-cost", type=float, default=0.00062)
    quarterly_profit_acceleration_event_audit.add_argument("--max-quality-age-days", type=int, default=550)
    quarterly_profit_acceleration_event_audit.add_argument("--batch-size", type=int, default=500)

    quarterly_event_capacity_audit = subparsers.add_parser(
        "quarterly-event-capacity-audit",
        help="count independent quarterly event cohorts without loading forward returns",
    )
    quarterly_event_capacity_audit.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    quarterly_event_capacity_audit.add_argument("--fundamentals", default=str(DEFAULT_QUARTERLY_FUNDAMENTALS))
    quarterly_event_capacity_audit.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    quarterly_event_capacity_audit.add_argument("--start", default="2019-01-01")
    quarterly_event_capacity_audit.add_argument("--end", default="2025-12-31")
    quarterly_event_capacity_audit.add_argument("--development-end", default="2025-12-31")
    quarterly_event_capacity_audit.add_argument(
        "--metric", choices=sorted(QUARTERLY_ACCELERATION_METRICS), required=True
    )
    quarterly_event_capacity_audit.add_argument("--hold-days", type=int, default=3)
    quarterly_event_capacity_audit.add_argument("--topk", type=int, default=3)
    quarterly_event_capacity_audit.add_argument(
        "--minimum-cohorts", type=int, default=QUARTERLY_EVENT_CAPACITY_MIN_COHORTS
    )

    billboard_holdout = subparsers.add_parser(
        "billboard-holdout",
        help="evaluate the one post-development inverse billboard event hypothesis on a strictly later interval",
    )
    billboard_holdout.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    billboard_holdout.add_argument("--fundamentals", default=str(DEFAULT_QUARTERLY_FUNDAMENTALS))
    billboard_holdout.add_argument("--billboard-events", default=str(DEFAULT_BILLBOARD_EVENTS))
    billboard_holdout.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    billboard_holdout.add_argument("--development-end", default="2025-12-31")
    billboard_holdout.add_argument("--holdout-start", default="2026-01-01")
    billboard_holdout.add_argument("--end", help="defaults to the latest local daily-data session")
    billboard_holdout.add_argument("--development-diagnostic-run-id", required=True)
    billboard_holdout.add_argument("--hold-days", type=int, default=3)
    billboard_holdout.add_argument("--topk", type=int, default=3)
    billboard_holdout.add_argument("--open-cost", type=float, default=0.00012)
    billboard_holdout.add_argument("--close-cost", type=float, default=0.00062)
    billboard_holdout.add_argument("--max-quality-age-days", type=int, default=550)
    billboard_holdout.add_argument("--max-billboard-age-days", type=int, default=3)
    billboard_holdout.add_argument("--batch-size", type=int, default=500)

    walk_forward_selection_audit = subparsers.add_parser(
        "walk-forward-selection-audit",
        help="select a candidate library on expanding historical windows and test each next calendar year",
    )
    walk_forward_selection_audit.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    walk_forward_selection_audit.add_argument("--fundamentals", default=str(DEFAULT_FUNDAMENTALS))
    walk_forward_selection_audit.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    walk_forward_selection_audit.add_argument("--start", default="2019-01-01")
    walk_forward_selection_audit.add_argument("--end", default="2025-12-31")
    walk_forward_selection_audit.add_argument("--first-test-year", type=int, default=2021)
    walk_forward_selection_audit.add_argument("--last-test-year", type=int, default=2025)
    walk_forward_selection_audit.add_argument("--hold-days", type=int, default=3)
    walk_forward_selection_audit.add_argument("--topk", type=int, default=3)
    walk_forward_selection_audit.add_argument("--regime-filter", choices=sorted(REGIME_FILTERS), default="breadth_5_above_20")
    walk_forward_selection_audit.add_argument("--open-cost", type=float, default=0.00012)
    walk_forward_selection_audit.add_argument("--close-cost", type=float, default=0.00062)
    walk_forward_selection_audit.add_argument("--max-quality-age-days", type=int, default=550)
    walk_forward_selection_audit.add_argument("--batch-size", type=int, default=500)
    walk_forward_selection_audit.add_argument("--candidate-library", choices=sorted(CANDIDATE_LIBRARIES), default="v2_microstructure")
    walk_forward_selection_audit.add_argument(
        "--selection-policy", choices=sorted(SELECTION_POLICIES), default="positive_year_stability_mdd20"
    )

    regime_audit = subparsers.add_parser(
        "regime-audit", help="compare all predeclared close-known market regimes for one recorded candidate"
    )
    regime_audit.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    regime_audit.add_argument("--fundamentals", default=str(DEFAULT_FUNDAMENTALS))
    regime_audit.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    regime_audit.add_argument("--candidate", required=True)
    regime_audit.add_argument("--candidate-library", choices=sorted(CANDIDATE_LIBRARIES), required=True)
    regime_audit.add_argument("--start", default="2024-01-01")
    regime_audit.add_argument("--end", help="defaults to the local Qlib calendar end")
    regime_audit.add_argument("--development-end", default="2025-12-31")
    regime_audit.add_argument("--hold-days", type=int, default=3)
    regime_audit.add_argument("--topk", type=int, default=3)
    regime_audit.add_argument("--open-cost", type=float, default=0.0015)
    regime_audit.add_argument("--close-cost", type=float, default=0.0025)
    regime_audit.add_argument("--max-quality-age-days", type=int, default=550)
    regime_audit.add_argument("--batch-size", type=int, default=500)
    regime_audit.add_argument("--selection-policy", choices=sorted(SELECTION_POLICIES), default="pooled_return_drawdown")

    loss_cap_audit = subparsers.add_parser(
        "loss-cap-audit", help="compare close-confirmed loss caps for one recorded factor candidate"
    )
    loss_cap_audit.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    loss_cap_audit.add_argument("--fundamentals", default=str(DEFAULT_FUNDAMENTALS))
    loss_cap_audit.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    loss_cap_audit.add_argument("--candidate", required=True)
    loss_cap_audit.add_argument("--candidate-library", choices=sorted(CANDIDATE_LIBRARIES), required=True)
    loss_cap_audit.add_argument("--start", default="2024-01-01")
    loss_cap_audit.add_argument("--end", help="defaults to the local Qlib calendar end")
    loss_cap_audit.add_argument("--development-end", default="2025-12-31")
    loss_cap_audit.add_argument("--hold-days", type=int, default=3)
    loss_cap_audit.add_argument("--topk", type=int, default=3)
    loss_cap_audit.add_argument("--regime-filter", choices=sorted(REGIME_FILTERS), default="always")
    loss_cap_audit.add_argument("--open-cost", type=float, default=0.0015)
    loss_cap_audit.add_argument("--close-cost", type=float, default=0.0025)
    loss_cap_audit.add_argument(
        "--close-loss-cap",
        type=float,
        action="append",
        help="repeat one or more daily-close loss caps; defaults to 0.05, 0.08, and 0.10 plus the uncapped baseline",
    )
    loss_cap_audit.add_argument("--max-quality-age-days", type=int, default=550)
    loss_cap_audit.add_argument("--batch-size", type=int, default=500)
    loss_cap_audit.add_argument("--selection-policy", choices=sorted(SELECTION_POLICIES), default="pooled_return_drawdown")

    entry_gap_audit = subparsers.add_parser(
        "entry-gap-audit", help="compare complete-TopK next-open entry-gap ceilings for one recorded factor candidate"
    )
    entry_gap_audit.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    entry_gap_audit.add_argument("--fundamentals", default=str(DEFAULT_FUNDAMENTALS))
    entry_gap_audit.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    entry_gap_audit.add_argument("--candidate", required=True)
    entry_gap_audit.add_argument("--candidate-library", choices=sorted(CANDIDATE_LIBRARIES), required=True)
    entry_gap_audit.add_argument("--start", default="2024-01-01")
    entry_gap_audit.add_argument("--end", help="defaults to the local Qlib calendar end")
    entry_gap_audit.add_argument("--development-end", default="2025-12-31")
    entry_gap_audit.add_argument("--hold-days", type=int, default=3)
    entry_gap_audit.add_argument("--topk", type=int, default=3)
    entry_gap_audit.add_argument("--regime-filter", choices=sorted(REGIME_FILTERS), default="always")
    entry_gap_audit.add_argument("--open-cost", type=float, default=0.0015)
    entry_gap_audit.add_argument("--close-cost", type=float, default=0.0025)
    entry_gap_audit.add_argument(
        "--max-entry-gap",
        type=float,
        action="append",
        help="repeat one or more next-open gap ceilings; defaults to 0.02, 0.04, and 0.06 plus the uncapped baseline",
    )
    entry_gap_audit.add_argument("--max-quality-age-days", type=int, default=550)
    entry_gap_audit.add_argument("--batch-size", type=int, default=500)
    entry_gap_audit.add_argument("--selection-policy", choices=sorted(SELECTION_POLICIES), default="pooled_return_drawdown")

    overlap_audit = subparsers.add_parser(
        "candidate-overlap-audit", help="measure basket and return-series overlap across recorded candidates"
    )
    overlap_audit.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    overlap_audit.add_argument("--fundamentals", default=str(DEFAULT_FUNDAMENTALS))
    overlap_audit.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    overlap_audit.add_argument(
        "--candidate", action="append", help="repeat for each candidate from one --candidate-library to compare"
    )
    overlap_audit.add_argument(
        "--candidate-spec", action="append", help="repeat library_id:candidate_name for a cross-library comparison"
    )
    overlap_audit.add_argument("--candidate-library", choices=sorted(CANDIDATE_LIBRARIES))
    overlap_audit.add_argument("--start", default="2024-01-01")
    overlap_audit.add_argument("--end", help="defaults to the local Qlib calendar end")
    overlap_audit.add_argument("--development-end", default="2025-12-31")
    overlap_audit.add_argument("--hold-days", type=int, default=3)
    overlap_audit.add_argument("--topk", type=int, default=3)
    overlap_audit.add_argument("--regime-filter", choices=sorted(REGIME_FILTERS), default="always")
    overlap_audit.add_argument("--open-cost", type=float, default=0.0015)
    overlap_audit.add_argument("--close-cost", type=float, default=0.0025)
    overlap_audit.add_argument("--max-quality-age-days", type=int, default=550)
    overlap_audit.add_argument("--batch-size", type=int, default=500)

    basket_correlation_audit = subparsers.add_parser(
        "basket-correlation-audit", help="measure within-basket return-correlation concentration for one candidate"
    )
    basket_correlation_audit.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    basket_correlation_audit.add_argument("--fundamentals", default=str(DEFAULT_FUNDAMENTALS))
    basket_correlation_audit.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    basket_correlation_audit.add_argument("--candidate", required=True)
    basket_correlation_audit.add_argument("--candidate-library", choices=sorted(CANDIDATE_LIBRARIES), required=True)
    basket_correlation_audit.add_argument("--start", default="2024-01-01")
    basket_correlation_audit.add_argument("--end", help="defaults to the local Qlib calendar end")
    basket_correlation_audit.add_argument("--development-end", default="2025-12-31")
    basket_correlation_audit.add_argument("--hold-days", type=int, default=3)
    basket_correlation_audit.add_argument("--topk", type=int, default=3)
    basket_correlation_audit.add_argument("--regime-filter", choices=sorted(REGIME_FILTERS), default="always")
    basket_correlation_audit.add_argument("--open-cost", type=float, default=0.0015)
    basket_correlation_audit.add_argument("--close-cost", type=float, default=0.0025)
    basket_correlation_audit.add_argument("--correlation-lookback", type=int, default=DEFAULT_BASKET_CORRELATION_LOOKBACK)
    basket_correlation_audit.add_argument("--max-quality-age-days", type=int, default=550)
    basket_correlation_audit.add_argument("--batch-size", type=int, default=500)

    cohort_risk_audit = subparsers.add_parser(
        "cohort-risk-audit", help="attribute the worst selected three-day cohorts to close-known stock characteristics"
    )
    cohort_risk_audit.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    cohort_risk_audit.add_argument("--fundamentals", default=str(DEFAULT_FUNDAMENTALS))
    cohort_risk_audit.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    cohort_risk_audit.add_argument("--candidate", required=True)
    cohort_risk_audit.add_argument("--candidate-library", choices=sorted(CANDIDATE_LIBRARIES), required=True)
    cohort_risk_audit.add_argument("--start", default="2024-01-01")
    cohort_risk_audit.add_argument("--end", help="defaults to the local Qlib calendar end")
    cohort_risk_audit.add_argument("--development-end", default="2025-12-31")
    cohort_risk_audit.add_argument("--hold-days", type=int, default=3)
    cohort_risk_audit.add_argument("--topk", type=int, default=3)
    cohort_risk_audit.add_argument("--regime-filter", choices=sorted(REGIME_FILTERS), default="always")
    cohort_risk_audit.add_argument("--open-cost", type=float, default=0.0015)
    cohort_risk_audit.add_argument("--close-cost", type=float, default=0.0025)
    cohort_risk_audit.add_argument("--worst-cohorts", type=int, default=10)
    cohort_risk_audit.add_argument("--max-quality-age-days", type=int, default=550)
    cohort_risk_audit.add_argument("--batch-size", type=int, default=500)

    risk_gate_audit = subparsers.add_parser(
        "risk-gate-audit", help="compare close-known low-volatility and low-range selection gate combinations"
    )
    risk_gate_audit.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    risk_gate_audit.add_argument("--fundamentals", default=str(DEFAULT_FUNDAMENTALS))
    risk_gate_audit.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    risk_gate_audit.add_argument("--candidate", required=True)
    risk_gate_audit.add_argument("--candidate-library", choices=sorted(CANDIDATE_LIBRARIES), required=True)
    risk_gate_audit.add_argument("--start", default="2024-01-01")
    risk_gate_audit.add_argument("--end", help="defaults to the local Qlib calendar end")
    risk_gate_audit.add_argument("--development-end", default="2025-12-31")
    risk_gate_audit.add_argument("--hold-days", type=int, default=3)
    risk_gate_audit.add_argument("--topk", type=int, default=3)
    risk_gate_audit.add_argument("--regime-filter", choices=sorted(REGIME_FILTERS), default="always")
    risk_gate_audit.add_argument("--open-cost", type=float, default=0.0015)
    risk_gate_audit.add_argument("--close-cost", type=float, default=0.0025)
    risk_gate_audit.add_argument(
        "--min-volatility-low-20",
        type=float,
        action="append",
        help="repeat volatility_low_20 rank floors; defaults to none, 0.20, and 0.40",
    )
    risk_gate_audit.add_argument(
        "--min-amplitude-low",
        type=float,
        action="append",
        help="repeat amplitude_low rank floors; defaults to none, 0.20, and 0.40",
    )
    risk_gate_audit.add_argument("--max-quality-age-days", type=int, default=550)
    risk_gate_audit.add_argument("--batch-size", type=int, default=500)
    risk_gate_audit.add_argument("--selection-policy", choices=sorted(SELECTION_POLICIES), default="pooled_return_drawdown")

    diversification_audit = subparsers.add_parser(
        "diversification-audit", help="compare complete-TopK trailing-correlation caps for one candidate"
    )
    diversification_audit.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    diversification_audit.add_argument("--fundamentals", default=str(DEFAULT_FUNDAMENTALS))
    diversification_audit.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    diversification_audit.add_argument("--candidate", required=True)
    diversification_audit.add_argument("--candidate-library", choices=sorted(CANDIDATE_LIBRARIES), required=True)
    diversification_audit.add_argument("--start", default="2024-01-01")
    diversification_audit.add_argument("--end", help="defaults to the local Qlib calendar end")
    diversification_audit.add_argument("--development-end", default="2025-12-31")
    diversification_audit.add_argument("--hold-days", type=int, default=3)
    diversification_audit.add_argument("--topk", type=int, default=3)
    diversification_audit.add_argument("--regime-filter", choices=sorted(REGIME_FILTERS), default="always")
    diversification_audit.add_argument("--open-cost", type=float, default=0.0015)
    diversification_audit.add_argument("--close-cost", type=float, default=0.0025)
    diversification_audit.add_argument(
        "--max-pairwise-correlation",
        type=float,
        action="append",
        help="repeat one or more correlation caps; defaults to 0.50, 0.60, and 0.70 plus uncapped baseline",
    )
    diversification_audit.add_argument("--correlation-lookback", type=int, default=DEFAULT_BASKET_CORRELATION_LOOKBACK)
    diversification_audit.add_argument(
        "--diversification-candidate-pool", type=int, default=DEFAULT_DIVERSIFICATION_CANDIDATE_POOL
    )
    diversification_audit.add_argument("--max-quality-age-days", type=int, default=550)
    diversification_audit.add_argument("--batch-size", type=int, default=500)
    diversification_audit.add_argument("--selection-policy", choices=sorted(SELECTION_POLICIES), default="pooled_return_drawdown")

    screen = subparsers.add_parser("screen", help="rank latest locally available candidates with a recorded factor mix")
    screen.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    screen.add_argument("--fundamentals", default=str(DEFAULT_FUNDAMENTALS))
    screen.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    screen.add_argument("--candidate", default="quality_trend_pullback")
    screen.add_argument("--candidate-library", choices=sorted(CANDIDATE_LIBRARIES), default="v1")
    screen.add_argument("--regime-filter", choices=sorted(REGIME_FILTERS), default="always")
    screen.add_argument("--as-of", help="latest local daily session by default")
    screen.add_argument("--start", help="optional feature-history start; defaults to a local rolling lookback")
    screen.add_argument("--lookback-calendar-days", type=int, default=100)
    screen.add_argument("--topk", type=int, default=20)
    screen.add_argument("--include-st", action="store_true", help="include current ST-tagged names; disabled by default")
    screen.add_argument("--max-quality-age-days", type=int, default=550)
    screen.add_argument("--batch-size", type=int, default=500)

    plan = subparsers.add_parser(
        "plan", help="turn a fresh screen into A-share board-lot plans for the configured pilot capital"
    )
    plan.add_argument("--screen-path", required=True, help="path emitted by the screen command")
    plan.add_argument("--topk", type=int, default=3, help="number of ranked candidates to size")
    plan.add_argument(
        "--capital",
        type=float,
        action="append",
        help="repeat for one or more account sizes; defaults to RMB 200k",
    )
    plan.add_argument("--lot-size", type=int, default=100)
    plan.add_argument("--commission-rate", type=float, default=0.0001, help="per-side broker commission; default is RMB 1 per RMB 10k")
    plan.add_argument("--commission-min", type=float, default=0.0, help="per-order commission minimum; default follows the supplied zero-minimum quote")
    plan.add_argument("--transfer-fee-rate", type=float, default=0.00002, help="per-side transfer/settlement fee")
    plan.add_argument("--stamp-duty-rate", type=float, default=0.0005, help="sell-side stamp duty rate")
    plan.add_argument("--max-gross-exposure", type=float, default=0.15)
    plan.add_argument("--target-weight", type=float, default=0.05)
    plan.add_argument("--output", help="optional JSON output path")

    monitor = subparsers.add_parser(
        "monitor", help="record eligible paper signals and settle completed three-day signals for the latest promoted strategy"
    )
    monitor.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    monitor.add_argument("--fundamentals", default=str(DEFAULT_FUNDAMENTALS))
    monitor.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    monitor.add_argument("--registry-path", default=str(DEFAULT_STRATEGY_REGISTRY))
    monitor.add_argument("--ledger-path", default=str(DEFAULT_PAPER_LEDGER))
    monitor.add_argument("--iteration-id", help="use a specific passed-initial-test iteration instead of the latest one")
    monitor.add_argument(
        "--not-before",
        required=True,
        help="first genuinely unseen signal-close date, in YYYY-MM-DD form; prevents historical paper-signal backfill",
    )
    monitor.add_argument("--as-of", help="local provider date by default")
    monitor.add_argument("--lookback-calendar-days", type=int, default=100)
    monitor.add_argument("--max-quality-age-days", type=int, default=550)
    monitor.add_argument("--batch-size", type=int, default=500)

    prospective_register = subparsers.add_parser(
        "prospective-register",
        help="pre-register the fixed close-below-VWAP hypothesis before its first unseen close",
    )
    prospective_register.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    prospective_register.add_argument(
        "--prospective-registry-path", default=str(DEFAULT_PROSPECTIVE_FACTOR_REGISTRY)
    )
    prospective_register.add_argument(
        "--source-diagnostic", default=str(PROSPECTIVE_VWAP_SOURCE_DIAGNOSTIC)
    )
    prospective_register.add_argument(
        "--not-before",
        default=PROSPECTIVE_VWAP_EARLIEST_NOT_BEFORE,
        help="first genuinely unseen signal close; must be later than the current local provider date",
    )

    prospective_monitor = subparsers.add_parser(
        "prospective-monitor",
        help="record current-close signals and three-day settlements for registered future-only factors",
    )
    prospective_monitor.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    prospective_monitor.add_argument("--fundamentals", default=str(DEFAULT_FUNDAMENTALS))
    prospective_monitor.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    prospective_monitor.add_argument(
        "--prospective-registry-path", default=str(DEFAULT_PROSPECTIVE_FACTOR_REGISTRY)
    )
    prospective_monitor.add_argument(
        "--prospective-ledger-path", default=str(DEFAULT_PROSPECTIVE_FACTOR_LEDGER)
    )
    prospective_monitor.add_argument("--registration-id", help="specific registration; latest by default")
    prospective_monitor.add_argument("--lookback-calendar-days", type=int, default=100)
    prospective_monitor.add_argument("--max-quality-age-days", type=int, default=550)
    prospective_monitor.add_argument("--batch-size", type=int, default=500)

    shadow_register = subparsers.add_parser(
        "shadow-register", help="register a development-only iteration for separate future paper observation"
    )
    shadow_register.add_argument("--registry-path", default=str(DEFAULT_STRATEGY_REGISTRY))
    shadow_register.add_argument("--shadow-registry-path", default=str(DEFAULT_SHADOW_OBSERVATION_REGISTRY))
    shadow_register.add_argument("--iteration-id", required=True)
    shadow_register.add_argument(
        "--not-before",
        required=True,
        help="first genuinely unseen signal-close date, in YYYY-MM-DD form",
    )

    shadow_suspend = subparsers.add_parser(
        "shadow-suspend", help="suspend a registered forward observation without deleting its audit trail"
    )
    shadow_suspend.add_argument("--registry-path", default=str(DEFAULT_STRATEGY_REGISTRY))
    shadow_suspend.add_argument("--shadow-registry-path", default=str(DEFAULT_SHADOW_OBSERVATION_REGISTRY))
    shadow_suspend.add_argument("--shadow-suspension-registry-path", default=str(DEFAULT_SHADOW_SUSPENSION_REGISTRY))
    shadow_suspend.add_argument("--iteration-id", required=True)
    shadow_suspend.add_argument("--reason", required=True)

    shadow_monitor = subparsers.add_parser(
        "shadow-monitor", help="record and settle registered development-only candidates in a separate paper ledger"
    )
    shadow_monitor.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    shadow_monitor.add_argument("--fundamentals", default=str(DEFAULT_FUNDAMENTALS))
    shadow_monitor.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    shadow_monitor.add_argument("--registry-path", default=str(DEFAULT_STRATEGY_REGISTRY))
    shadow_monitor.add_argument("--shadow-registry-path", default=str(DEFAULT_SHADOW_OBSERVATION_REGISTRY))
    shadow_monitor.add_argument("--shadow-suspension-registry-path", default=str(DEFAULT_SHADOW_SUSPENSION_REGISTRY))
    shadow_monitor.add_argument("--shadow-ledger-path", default=str(DEFAULT_SHADOW_PAPER_LEDGER))
    shadow_monitor.add_argument("--as-of", help="local provider date by default")
    shadow_monitor.add_argument("--lookback-calendar-days", type=int, default=100)
    shadow_monitor.add_argument("--max-quality-age-days", type=int, default=550)
    shadow_monitor.add_argument("--batch-size", type=int, default=500)

    report = subparsers.add_parser("report", help="render the three-day research registry and paper ledger as Markdown")
    report.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    report.add_argument("--registry-path", default=str(DEFAULT_STRATEGY_REGISTRY))
    report.add_argument("--ledger-path", default=str(DEFAULT_PAPER_LEDGER))
    report.add_argument("--shadow-ledger-path", default=str(DEFAULT_SHADOW_PAPER_LEDGER))
    report.add_argument("--shadow-observation-registry-path", default=str(DEFAULT_SHADOW_OBSERVATION_REGISTRY))
    report.add_argument("--shadow-suspension-registry-path", default=str(DEFAULT_SHADOW_SUSPENSION_REGISTRY))
    report.add_argument("--prospective-factor-registry-path", default=str(DEFAULT_PROSPECTIVE_FACTOR_REGISTRY))
    report.add_argument("--prospective-factor-ledger-path", default=str(DEFAULT_PROSPECTIVE_FACTOR_LEDGER))
    report.add_argument("--output", default=str(DEFAULT_RESEARCH_REPORT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "sync-fundamentals":
        report = sync_fundamentals(args.start_year, args.end_year, Path(args.output), Path(args.manifest))
    elif args.command == "sync-quarterly-fundamentals":
        report = sync_quarterly_fundamentals(
            args.start_year,
            args.end_year,
            Path(args.output),
            Path(args.manifest),
            args.through_report_date,
        )
    elif args.command == "merge-quarterly-fundamentals":
        report = merge_quarterly_fundamentals(
            [Path(path) for path in args.input], Path(args.output), Path(args.manifest)
        )
    elif args.command == "sync-performance-forecasts":
        report = sync_performance_forecasts(
            args.start_year,
            args.end_year,
            Path(args.output),
            Path(args.manifest),
            args.through_report_date,
        )
    elif args.command == "sync-billboard-events":
        report = sync_billboard_events(
            args.start_year,
            args.end_year,
            Path(args.output),
            Path(args.manifest),
        )
    elif args.command == "sync-major-holder-events":
        report = sync_major_holder_events(
            args.start_year,
            args.end_year,
            Path(args.output),
            Path(args.manifest),
        )
    elif args.command == "sync-block-trade-events":
        report = sync_block_trade_events(
            args.start_year,
            args.end_year,
            Path(args.output),
            Path(args.manifest),
        )
    elif args.command == "sync-margin-financing-events":
        report = sync_margin_financing_top_flow_events(
            Path(args.provider_uri),
            args.start,
            args.end,
            args.top_n,
            Path(args.output),
            Path(args.manifest),
            args.merge_existing,
        )
    elif args.command == "sync-institutional-survey-events":
        report = sync_institutional_survey_events(
            args.start_year,
            args.end_year,
            Path(args.output),
            Path(args.manifest),
        )
    elif args.command == "sync-repurchase-plan-events":
        report = sync_repurchase_plan_events(Path(args.output), Path(args.manifest))
    elif args.command == "sync-holder-count-events":
        report = sync_holder_count_events(args.start_year, args.end_year, Path(args.output), Path(args.manifest))
    elif args.command == "sync-pledge-events":
        report = sync_pledge_events(args.start_year, args.end_year, Path(args.output), Path(args.manifest))
    elif args.command == "sync-dividend-plan-events":
        report = sync_dividend_plan_events(args.start_year, args.end_year, Path(args.output), Path(args.manifest))
    elif args.command == "run":
        report = run_research(args)
    elif args.command == "factor-diagnostic":
        report = run_factor_diagnostic(args)
    elif args.command == "rolling-window-semantics-audit":
        report = run_rolling_window_semantics_audit(args)
    elif args.command == "factor-stability-audit":
        report = run_factor_stability_audit(args)
    elif args.command == "factor-topk-viability-audit":
        report = run_factor_topk_viability_audit(args)
    elif args.command == "selection-multiplicity-audit":
        report = run_selection_multiplicity_audit(args)
    elif args.command == "limit-like-event-audit":
        report = run_limit_like_event_audit(args)
    elif args.command == "quarterly-profit-acceleration-event-audit":
        report = run_quarterly_profit_acceleration_event_audit(args)
    elif args.command == "quarterly-event-capacity-audit":
        report = run_quarterly_event_capacity_audit(args)
    elif args.command == "billboard-holdout":
        report = run_billboard_holdout(args)
    elif args.command == "walk-forward-selection-audit":
        report = run_walk_forward_selection_audit(args)
    elif args.command == "regime-audit":
        report = run_regime_audit(args)
    elif args.command == "loss-cap-audit":
        report = run_loss_cap_audit(args)
    elif args.command == "entry-gap-audit":
        report = run_entry_gap_audit(args)
    elif args.command == "candidate-overlap-audit":
        report = run_candidate_overlap_audit(args)
    elif args.command == "basket-correlation-audit":
        report = run_basket_correlation_audit(args)
    elif args.command == "cohort-risk-audit":
        report = run_cohort_risk_audit(args)
    elif args.command == "risk-gate-audit":
        report = run_risk_gate_audit(args)
    elif args.command == "diversification-audit":
        report = run_diversification_audit(args)
    elif args.command == "plan":
        report = run_execution_plan(args)
    elif args.command == "monitor":
        report = run_paper_monitor(args)
    elif args.command == "prospective-register":
        report = register_prospective_vwap_factor(args)
    elif args.command == "prospective-monitor":
        report = run_prospective_vwap_monitor(args)
    elif args.command == "shadow-register":
        report = register_shadow_observation(args)
    elif args.command == "shadow-suspend":
        report = suspend_shadow_observation(args)
    elif args.command == "shadow-monitor":
        report = run_shadow_monitor(args)
    elif args.command == "report":
        report = run_research_report(args)
    else:
        report = run_latest_screen(args)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
