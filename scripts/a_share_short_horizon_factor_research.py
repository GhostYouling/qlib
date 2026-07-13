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
DEFAULT_EXPERIMENT_ROOT = DATA_ROOT / "experiments" / "short_horizon"
DEFAULT_STRATEGY_REGISTRY = DEFAULT_EXPERIMENT_ROOT / "strategy_registry.json"
DEFAULT_PAPER_LEDGER = DEFAULT_EXPERIMENT_ROOT / "three_day_paper_ledger.json"
DEFAULT_SHADOW_OBSERVATION_REGISTRY = DEFAULT_EXPERIMENT_ROOT / "shadow_observation_registry.json"
DEFAULT_SHADOW_PAPER_LEDGER = DEFAULT_EXPERIMENT_ROOT / "three_day_shadow_paper_ledger.json"
DEFAULT_RESEARCH_REPORT = DEFAULT_EXPERIMENT_ROOT / "three_day_research_report.md"
DEFAULT_PILOT_CAPITALS = (200_000.0,)

EASTMONEY_DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
EASTMONEY_REPORT = "RPT_LICO_FN_CPD"
FUNDAMENTAL_COLUMNS = (
    "instrument",
    "report_date",
    "announcement_date",
    "roe",
    "net_profit",
    "revenue_yoy",
    "profit_yoy",
)


@dataclass(frozen=True)
class Candidate:
    """One predeclared factor combination used in the first research sweep."""

    name: str
    description: str
    weights: dict[str, float]


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
)

# This diagnostic catalog is fixed before a new candidate library exists.  It
# combines prior-library factors with unused, close-known technical fields.
# It is evidence for forming a future library; it never selects or promotes an
# existing candidate.
FACTOR_DIAGNOSTIC_COLUMNS = tuple(
    sorted({factor for candidate in V7_CANDIDATES for factor in candidate.weights} | set(EXPLORATORY_DIAGNOSTIC_FACTORS))
)
FACTOR_DIAGNOSTIC_BUCKET_COUNT = 5


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


def sync_fundamentals(start_year: int, end_year: int, output: Path, manifest: Path) -> dict[str, Any]:
    """Download annual quality inputs and write an auditable local snapshot."""

    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://data.eastmoney.com/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        }
    )
    frames: list[pd.DataFrame] = []
    counts: dict[str, int] = {}
    for report_date in annual_report_dates(start_year, end_year):
        rows = fetch_annual_report_rows(session, report_date)
        normalized = normalize_fundamental_rows(rows, report_date)
        frames.append(normalized)
        counts[report_date] = len(normalized)
        print(f"{report_date}: {len(normalized)} normalized annual-report rows")

    merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=FUNDAMENTAL_COLUMNS)
    merged = merged.sort_values(["instrument", "report_date", "announcement_date"], kind="stable")
    merged = merged.drop_duplicates(["instrument", "report_date"], keep="first").reset_index(drop=True)
    if merged.empty:
        raise RuntimeError("annual-report sync produced no usable rows")
    _atomic_write_parquet(output, merged)
    result = {
        "status": "completed",
        "source": {
            "provider": "Eastmoney public datacenter",
            "endpoint": EASTMONEY_DATACENTER_URL,
            "report": EASTMONEY_REPORT,
            "retrieved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        },
        "report_dates": annual_report_dates(start_year, end_year),
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
    """Add year-over-year changes using only earlier annual reports per stock.

    These values belong to the newer report and therefore become usable only
    when that report itself is made effective after its announcement date in
    ``attach_quality_asof``.  No later report is used to backfill an earlier
    disclosure.
    """

    required = {"instrument", "report_date", "announcement_date", "roe", "revenue_yoy", "profit_yoy"}
    if missing := sorted(required - set(events.columns)):
        raise ValueError(f"fundamental events are missing columns: {', '.join(missing)}")
    result = events.sort_values(["instrument", "report_date", "announcement_date"], kind="stable").copy()
    for field, acceleration in (
        ("roe", "roe_change"),
        ("revenue_yoy", "revenue_yoy_acceleration"),
        ("profit_yoy", "profit_yoy_acceleration"),
    ):
        result[acceleration] = result.groupby("instrument", sort=False)[field].diff()
    return result


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


def load_market_data(provider_uri: Path, start: str, end: str | None, batch_size: int) -> pd.DataFrame:
    """Load the local buyable universe and precompute only non-forward factors."""

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    import qlib
    from qlib.data import D

    if batch_size < 1:
        raise ValueError("--batch-size must be positive")
    provider_uri = provider_uri.expanduser().resolve()
    if not provider_uri.exists():
        raise FileNotFoundError(f"Qlib provider directory does not exist: {provider_uri}")
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
        "momentum_10": "$close/Ref($close, 10) - 1",
        "momentum_20": "$close/Ref($close, 20) - 1",
        "momentum_60": "$close/Ref($close, 60) - 1",
        "trend_ma_5": "$close/Mean($close, 5) - 1",
        "trend_ma_20": "$close/Mean($close, 20) - 1",
        "trend_ma_60": "$close/Mean($close, 60) - 1",
        "volume_surge_1": "$volume/Mean($volume, 20) - 1",
        "volume_surge": "Mean($volume, 5)/Mean($volume, 20) - 1",
        "volume_surge_3": "Mean($volume, 3)/Mean($volume, 10) - 1",
        "turnover_surge": "Mean($turnover, 5)/Mean($turnover, 20) - 1",
        "turnover_surge_3": "Mean($turnover, 3)/Mean($turnover, 10) - 1",
        "turnover_surge_1": "$turnover/Mean($turnover, 20) - 1",
        "liquidity_5": "Mean($turnover, 5)",
        "volatility_5": "Std($close/Ref($close, 1) - 1, 5)",
        "volatility_10": "Std($close/Ref($close, 1) - 1, 10)",
        "volatility_20": "Std($close/Ref($close, 1) - 1, 20)",
        "amplitude_1": "$high/$low - 1",
        "amplitude_5": "Mean($high/$low - 1, 5)",
        "gap_1": "$open/Ref($close, 1) - 1",
        "near_high_10": "$close/Max($high, 10) - 1",
        "near_high_20": "$close/Max($high, 20) - 1",
        "intraday_strength": "$close/$open - 1",
        "close_to_high": "$close/$high",
    }
    frames: list[pd.DataFrame] = []
    expressions = list(fields.values())
    for offset in range(0, len(instruments), batch_size):
        batch = instruments[offset : offset + batch_size]
        frame = D.features(batch, expressions, start_time=start, end_time=end, freq="day")
        frame = frame.rename(columns={expression: name for name, expression in fields.items()}).reset_index()
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


def rank_factor_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Turn raw factors into daily comparable [0, 1] scores without look-ahead."""

    result = frame.copy()
    raw_columns = [
        "momentum_1",
        "momentum_2",
        "momentum_3",
        "momentum_5",
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
        "roe",
        "revenue_yoy",
        "profit_yoy",
        "quality_age_days",
        "roe_change",
        "revenue_yoy_acceleration",
        "profit_yoy_acceleration",
    ]
    for column in raw_columns:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    eligible = result["quality_eligible"].fillna(False)
    result = result.join(market_state_frame(result, eligible), on="datetime")
    for column in raw_columns:
        ranked = result.loc[eligible].groupby("datetime", sort=False)[column].rank(pct=True)
        result.loc[eligible, f"rank_{column}"] = ranked
    result["reversal_1"] = 1.0 - result["rank_momentum_1"]
    result["reversal_2"] = 1.0 - result["rank_momentum_2"]
    result["reversal_3"] = 1.0 - result["rank_momentum_3"]
    result["reversal_5"] = 1.0 - result["rank_momentum_5"]
    result["reversal_10"] = 1.0 - result["rank_momentum_10"]
    result["volume_dry_up"] = 1.0 - result["rank_volume_surge"]
    result["volatility_target_5"] = 1.0 - (result["rank_volatility_5"] - 0.50).abs()
    result["volatility_target"] = 1.0 - (result["rank_volatility_10"] - 0.65).abs()
    result["volatility_target_20"] = 1.0 - (result["rank_volatility_20"] - 0.50).abs()
    result["volatility_low_20"] = 1.0 - result["rank_volatility_20"]
    result["amplitude_low_1"] = 1.0 - result["rank_amplitude_1"]
    result["amplitude_low"] = 1.0 - result["rank_amplitude_5"]
    result["gap_reversal"] = 1.0 - result["rank_gap_1"]
    result["gap_strength"] = result["rank_gap_1"]
    result["close_pullback"] = 1.0 - result["rank_close_to_high"]
    result["drawdown_20"] = 1.0 - result["rank_near_high_20"]
    result["quality_roe"] = result["rank_roe"]
    result["quality_revenue"] = result["rank_revenue_yoy"]
    result["quality_profit"] = result["rank_profit_yoy"]
    result["quality_freshness"] = 1.0 - result["rank_quality_age_days"]
    result["quality_growth"] = result[["rank_revenue_yoy", "rank_profit_yoy"]].mean(axis=1)
    result["quality_score"] = result[["rank_roe", "rank_revenue_yoy", "rank_profit_yoy"]].mean(axis=1)
    result["roe_change"] = result["rank_roe_change"]
    result["revenue_yoy_acceleration"] = result["rank_revenue_yoy_acceleration"]
    result["profit_yoy_acceleration"] = result["rank_profit_yoy_acceleration"]
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
    drawdown = equity / equity.cummax() - 1.0
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
    summaries: list[dict[str, Any]] = []
    for factor in factor_columns:
        if factor not in forward_returns.columns:
            continue
        cohorts: list[dict[str, Any]] = []
        quintile_means: list[dict[str, Any]] = []
        for signal_date, group in forward_returns.groupby("signal_date", sort=True):
            valid = group[[factor, "forward_gross_return"]].dropna()
            if len(valid) < max(2, 2 * topk) or valid[factor].nunique() < 2:
                continue
            rank_ic = valid[factor].corr(valid["forward_gross_return"], method="spearman")
            if pd.isna(rank_ic):
                continue
            ordered = valid.sort_values(factor, ascending=False, kind="stable")
            top = ordered.head(topk)["forward_gross_return"]
            bottom = ordered.tail(topk)["forward_gross_return"]
            top_gross_return = float(top.mean())
            top_net_return = float((1.0 - open_cost) * (1.0 + top_gross_return) * (1.0 - close_cost) - 1.0)
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
                "by_signal_year": by_year,
            }
        )
    return sorted(
        summaries,
        key=lambda item: (float(item["mean_rank_ic"]), float(item["mean_top_minus_bottom_gross_return"])),
        reverse=True,
    )


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
        if iteration.get("promotion", {}).get("status") == "passed_initial_test":
            return iteration
    detail = f" {iteration_id}" if iteration_id else ""
    raise ValueError(f"no passed_initial_test strategy found in registry{detail}")


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
            "rule": "Forward paper observation only; the date must be the first genuinely unseen signal close.",
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
    not_before = getattr(args, "not_before", None)
    if not_before is not None and latest_date.normalize() < pd.Timestamp(not_before).normalize():
        return {
            "status": "not_started",
            "as_of": latest_date.date().isoformat(),
            "iteration_id": iteration["iteration_id"],
            "not_before": pd.Timestamp(not_before).date().isoformat(),
            "reason": "forward observation begins only on the registered unseen signal date",
        }
    calendar = local_trading_calendar(provider_uri, end=latest_date.date().isoformat())
    ledger = load_paper_ledger(ledger_path)
    settled_ids = {str(item.get("signal_id")) for item in ledger["settlements"]}
    new_settlements: list[dict[str, Any]] = []
    for signal in ledger["signals"]:
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


def run_shadow_monitor(args: argparse.Namespace) -> dict[str, Any]:
    """Collect forward paper evidence for every explicitly registered research candidate."""

    plan_path = Path(args.shadow_registry_path)
    plan = load_shadow_observation_registry(plan_path)
    if not plan["observations"]:
        return {
            "status": "completed",
            "observations": [],
            "message": "no forward shadow observations are registered",
            "shadow_registry_path": str(plan_path.expanduser().resolve()),
        }
    reports: list[dict[str, Any]] = []
    for observation in plan["observations"]:
        monitor_args = argparse.Namespace(**vars(args))
        monitor_args.iteration_id = str(observation["iteration_id"])
        monitor_args.ledger_path = args.shadow_ledger_path
        monitor_args.allow_research_only = True
        monitor_args.not_before = str(observation["not_before"])
        reports.append(run_paper_monitor(monitor_args))
    return {
        "status": "completed",
        "observation_count": len(reports),
        "observations": reports,
        "shadow_registry_path": str(plan_path.expanduser().resolve()),
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


def _shadow_observation_rows(plan: dict[str, Any], ledger: dict[str, Any]) -> list[dict[str, Any]]:
    """Summarize separate forward evidence for each explicitly registered candidate."""

    signals = list(ledger.get("signals") or [])
    settlements = list(ledger.get("settlements") or [])
    rows: list[dict[str, Any]] = []
    for observation in plan.get("observations") or []:
        iteration_id = str(observation.get("iteration_id", ""))
        candidate_signals = [item for item in signals if str(item.get("iteration_id")) == iteration_id]
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
                "signals": len(candidate_signals),
                "settlements": len(candidate_settlements),
                "pending": len(pending),
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


def load_factor_diagnostics(experiment_root: Path) -> list[dict[str, Any]]:
    """Read development-only single-factor diagnostics for the research log."""

    diagnostics: list[dict[str, Any]] = []
    for path in sorted(experiment_root.expanduser().glob("*_factor_diagnostic.json")):
        try:
            diagnostic = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if diagnostic.get("status") != "completed":
            continue
        ranking = list(diagnostic.get("ranking_by_development_rank_ic") or [])
        data = diagnostic.get("data") or {}
        top = ranking[0] if ranking else {}
        diagnostics.append(
            {
                "run_id": str(diagnostic.get("run_id", path.stem)),
                "calendar_start": str(data.get("calendar_start", "—")),
                "calendar_end": str(data.get("calendar_end", "—")),
                "factor_count": len(ranking),
                "top_factor": str(top.get("factor", "—")),
                "top_factor_mean_rank_ic": top.get("mean_rank_ic"),
                "path": str(path.resolve()),
            }
        )
    return diagnostics


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
) -> str:
    """Render the append-only machine records into a concise human research log."""

    iterations = list(registry.get("iterations") or [])
    signals, settlements, pending, paper_equity = _paper_ledger_summary(ledger)
    lines = [
        "# 三日短线研究日志",
        "",
        "本报告由策略注册表和纸面台账生成。它记录研究证据，不构成买卖建议或收益承诺。",
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
    if factor_diagnostics:
        lines.extend(
            [
                "",
                "## 开发期单因子三日预测诊断",
                "",
                "诊断只描述每个已声明因子与其后完整三日收益的横截面秩相关；它不选择策略，不能替代组合的独立测试或前瞻观察。",
                "",
                "| 诊断 | 历史范围 | 因子数 | 开发期最高平均 Rank IC 因子 | 平均 Rank IC |",
                "| --- | --- | ---: | --- | ---: |",
            ]
        )
        for diagnostic in factor_diagnostics:
            mean_ic = diagnostic["top_factor_mean_rank_ic"]
            formatted_ic = "—" if mean_ic is None else f"{float(mean_ic):.4f}"
            lines.append(
                "| {run_id} | {start} 至 {end} | {count} | {factor} | {mean_ic} |".format(
                    run_id=diagnostic["run_id"],
                    start=diagnostic["calendar_start"],
                    end=diagnostic["calendar_end"],
                    count=diagnostic["factor_count"],
                    factor=diagnostic["top_factor"],
                    mean_ic=formatted_ic,
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
        shadow_signals, shadow_settlements, shadow_pending, shadow_equity = _paper_ledger_summary(shadow_ledger)
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
        observation_rows = _shadow_observation_rows(shadow_observation_registry or {}, shadow_ledger)
        if observation_rows:
            lines.extend(
                [
                    "| 候选 | 候选库 | 首个可用收盘日 | 信号 | 已结算 | 待结算 | 已结算累计净收益 |",
                    "| --- | --- | --- | ---: | ---: | ---: | ---: |",
                ]
            )
            for row in observation_rows:
                lines.append(
                    "| {candidate} | {library} | {not_before} | {signals} | {settlements} | {pending} | {net_return} |".format(
                        candidate=row["candidate"],
                        library=row["candidate_library"],
                        not_before=row["not_before"],
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
            "1. 每次本地收盘数据更新后运行 `monitor`，只追加新的样本外信号或结算。",
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
    experiment_root = Path(args.experiment_root).expanduser()
    no_eligible_studies = load_no_eligible_studies(experiment_root)
    factor_diagnostics = load_factor_diagnostics(experiment_root)
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
    )
    output = Path(args.output).expanduser()
    _atomic_write_text(output, report)
    return {
        "status": "completed",
        "registry_path": str(registry_path.resolve()),
        "ledger_path": str(ledger_path.resolve()),
        "shadow_ledger_path": str(shadow_ledger_path.resolve()),
        "shadow_observation_registry_path": str(shadow_observation_registry_path.resolve()),
        "report_path": str(output.resolve()),
        "iterations": len(registry.get("iterations") or []),
        "signals": len(ledger["signals"]),
        "settlements": len(ledger["settlements"]),
        "shadow_signals": len(shadow_ledger["signals"]),
        "shadow_settlements": len(shadow_ledger["settlements"]),
        "no_eligible_studies": len(no_eligible_studies),
        "factor_diagnostics": len(factor_diagnostics),
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


def run_factor_diagnostic(args: argparse.Namespace) -> dict[str, Any]:
    """Measure development-only forward association for the declared factor catalog."""

    provider_uri = Path(args.provider_uri).expanduser()
    fundamental_path = Path(args.fundamentals).expanduser()
    experiment_root = Path(args.experiment_root).expanduser()
    fundamentals = load_fundamentals(fundamental_path)
    market = load_market_data(provider_uri, args.start, args.end, args.batch_size)
    market_end = market["datetime"].max()
    if market_end > pd.Timestamp(args.development_end):
        raise ValueError(
            "factor-diagnostic is development-only; pass --end no later than --development-end so reserved test data cannot guide factor design"
        )
    market = attach_quality_asof(market, fundamentals, max_age_days=args.max_quality_age_days)
    ranked = rank_factor_frame(market)
    forward_returns = forward_factor_return_frame(ranked, args.hold_days)
    summaries = summarize_factor_diagnostics(
        forward_returns,
        FACTOR_DIAGNOSTIC_COLUMNS,
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
        "factor_catalog": list(FACTOR_DIAGNOSTIC_COLUMNS),
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
        "data": {
            "provider_uri": str(provider_uri.resolve()),
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
            "Prices are qfq-adjusted and do not provide exact executable or limit-up/limit-down simulation.",
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
            "Prices are qfq-adjusted and do not provide an exact executable or limit-up/limit-down simulation.",
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
            "Prices are qfq-adjusted and do not provide exact executable or limit-up/limit-down simulation.",
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
            "Prices are qfq-adjusted and do not provide exact executable or limit-up/limit-down simulation.",
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
            "Prices are qfq-adjusted and do not provide exact executable or limit-up/limit-down simulation.",
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
            "Prices are qfq-adjusted and do not provide exact lot-size, dividend, tax, or limit-up/limit-down execution simulation.",
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
            "The qfq price data cannot simulate limit-up/limit-down availability, restoration factors, dividends, lot sizing, or exact taxes.",
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
            "The qfq price data cannot simulate opening-auction fill priority, limit-up/limit-down availability, restoration factors, dividends, lot sizing, or exact taxes.",
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


def run_research(args: argparse.Namespace) -> dict[str, Any]:
    """Run all candidate combinations and write a record for each one."""

    provider_uri = Path(args.provider_uri).expanduser()
    fundamental_path = Path(args.fundamentals).expanduser()
    experiment_root = Path(args.experiment_root).expanduser()
    candidates = candidate_library(args.candidate_library)
    fundamentals = load_fundamentals(fundamental_path)
    market = load_market_data(provider_uri, args.start, args.end, args.batch_size)
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
        },
        "limitations": [
            "The current holding universe is derived from a current listing snapshot and can introduce survivorship bias in historical results.",
            "Eastmoney public data are a present-day snapshot; retaining the earliest visible notice date reduces but does not eliminate accounting restatement bias.",
            "Prices are qfq-adjusted and the provider lacks Qlib restoration factors; this is not an exact lot-size, dividend, tax, or limit-up/limit-down execution simulation.",
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
    factor_diagnostic.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    factor_diagnostic.add_argument("--start", default="2019-01-01")
    factor_diagnostic.add_argument("--end", default="2025-12-31")
    factor_diagnostic.add_argument("--development-end", default="2025-12-31")
    factor_diagnostic.add_argument("--hold-days", type=int, default=3)
    factor_diagnostic.add_argument("--topk", type=int, default=3)
    factor_diagnostic.add_argument("--open-cost", type=float, default=0.0015)
    factor_diagnostic.add_argument("--close-cost", type=float, default=0.0025)
    factor_diagnostic.add_argument("--max-quality-age-days", type=int, default=550)
    factor_diagnostic.add_argument("--batch-size", type=int, default=500)

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
    monitor.add_argument("--as-of", help="local provider date by default")
    monitor.add_argument("--lookback-calendar-days", type=int, default=100)
    monitor.add_argument("--max-quality-age-days", type=int, default=550)
    monitor.add_argument("--batch-size", type=int, default=500)

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

    shadow_monitor = subparsers.add_parser(
        "shadow-monitor", help="record and settle registered development-only candidates in a separate paper ledger"
    )
    shadow_monitor.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    shadow_monitor.add_argument("--fundamentals", default=str(DEFAULT_FUNDAMENTALS))
    shadow_monitor.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    shadow_monitor.add_argument("--registry-path", default=str(DEFAULT_STRATEGY_REGISTRY))
    shadow_monitor.add_argument("--shadow-registry-path", default=str(DEFAULT_SHADOW_OBSERVATION_REGISTRY))
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
    report.add_argument("--output", default=str(DEFAULT_RESEARCH_REPORT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "sync-fundamentals":
        report = sync_fundamentals(args.start_year, args.end_year, Path(args.output), Path(args.manifest))
    elif args.command == "run":
        report = run_research(args)
    elif args.command == "factor-diagnostic":
        report = run_factor_diagnostic(args)
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
    elif args.command == "shadow-register":
        report = register_shadow_observation(args)
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
