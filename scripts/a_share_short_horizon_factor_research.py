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

CANDIDATE_LIBRARIES = {
    "v1": CANDIDATES,
    "v2_microstructure": V2_CANDIDATES,
    "v3_quality_grid": V3_CANDIDATES,
    "v4_freshness": V4_CANDIDATES,
    "v5_defensive": V5_CANDIDATES,
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
}

SELECTION_POLICIES = {
    "pooled_return_drawdown": "maximize development annualized_return - 0.5 * abs(development max_drawdown)",
    "positive_year_stability": (
        "maximize the worst development calendar-year net cumulative return - 0.5 * abs(full-development max_drawdown); "
        "requires at least two development years"
    ),
    "positive_year_stability_mdd20": (
        "require at least two positive development calendar years and development max_drawdown no worse than -20%; "
        "then maximize the worst development calendar-year net cumulative return - 0.5 * abs(full-development max_drawdown)"
    ),
}

# This cap matches the initial-test risk gate.  It is deliberately part of a
# separately named selection policy so a later research cycle cannot rewrite
# the winner of a prior, looser stability rule.
STRICT_DEVELOPMENT_MAX_DRAWDOWN = -0.20


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
    else:
        condition = frame["market_breadth_5"].gt(frame["market_breadth_20"]) & frame["market_breadth_20"].gt(0.0)
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
    events = fundamentals.copy()
    events["quality_effective_date"] = _first_trading_day_after(calendar, events["announcement_date"])
    events = events.dropna(subset=["quality_effective_date"])
    events = events.sort_values(
        ["instrument", "quality_effective_date", "report_date", "announcement_date"], kind="stable"
    ).drop_duplicates(["instrument", "quality_effective_date"], keep="last")

    quality_columns = ["report_date", "announcement_date", "roe", "net_profit", "revenue_yoy", "profit_yoy", "quality_effective_date"]
    daily = market[["instrument", "datetime"]].copy()
    daily["_kind"] = 1
    daily["_row"] = np.arange(len(daily))
    for column in ("report_date", "announcement_date", "quality_effective_date"):
        daily[column] = pd.NaT
    for column in ("roe", "net_profit", "revenue_yoy", "profit_yoy"):
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
    ]
    for column in raw_columns:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    eligible = result["quality_eligible"].fillna(False)
    breadth = (
        result.loc[eligible]
        .groupby("datetime", sort=False)
        .agg(market_breadth_5=("momentum_5", "mean"), market_breadth_20=("momentum_20", "mean"))
    )
    result = result.join(breadth, on="datetime")
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
    result["drawdown_20"] = 1.0 - result["rank_near_high_20"]
    result["quality_roe"] = result["rank_roe"]
    result["quality_revenue"] = result["rank_revenue_yoy"]
    result["quality_profit"] = result["rank_profit_yoy"]
    result["quality_freshness"] = 1.0 - result["rank_quality_age_days"]
    result["quality_growth"] = result[["rank_revenue_yoy", "rank_profit_yoy"]].mean(axis=1)
    result["quality_score"] = result[["rank_roe", "rank_revenue_yoy", "rank_profit_yoy"]].mean(axis=1)
    result["momentum_1"] = result["rank_momentum_1"]
    result["momentum_2"] = result["rank_momentum_2"]
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


def evaluate_candidate(
    scored: pd.DataFrame,
    candidate: Candidate,
    hold_days: int,
    topk: int,
    open_cost: float,
    close_cost: float,
    development_end: str,
    regime_filter: str = "always",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run non-overlapping cohorts from close signal to next-open entry.

    A signal is formed after the market close.  The portfolio buys on the next
    session's open and sells on the close after ``hold_days`` sessions.  This
    deliberately avoids using a future price in factor ranking.
    """

    if hold_days < 1 or topk < 1:
        raise ValueError("--hold-days and --topk must both be positive")
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

    pool = apply_regime_filter(base_pool, regime_filter)
    selected = pool.groupby("datetime", sort=False).head(topk).copy()
    selected["entry_date"] = selected["datetime"].map(lambda value: calendar[date_to_position[value] + 1])
    selected["exit_date"] = selected["datetime"].map(lambda value: calendar[date_to_position[value] + hold_days])

    quotes = scored[["datetime", "instrument", "open", "close"]].drop_duplicates(["datetime", "instrument"])
    entry = quotes.rename(columns={"datetime": "entry_date", "open": "entry_open"})[["entry_date", "instrument", "entry_open"]]
    exit_quote = quotes.rename(columns={"datetime": "exit_date", "close": "exit_close"})[["exit_date", "instrument", "exit_close"]]
    trades = selected.merge(entry, on=["entry_date", "instrument"], how="left")
    trades = trades.merge(exit_quote, on=["exit_date", "instrument"], how="left")
    trades = trades.dropna(subset=["entry_open", "exit_close"])
    trades = trades.loc[(trades["entry_open"] > 0) & (trades["exit_close"] > 0)].copy()
    trades["gross_return"] = trades["exit_close"] / trades["entry_open"] - 1.0
    trades["net_return"] = (1.0 - open_cost) * (1.0 + trades["gross_return"]) * (1.0 - close_cost) - 1.0
    traded_rounds = (
        trades.groupby(["datetime", "entry_date", "exit_date"], sort=True)
        .agg(net_return=("net_return", "mean"), gross_return=("gross_return", "mean"), holdings=("instrument", "nunique"))
        .reset_index()
        .rename(columns={"datetime": "signal_date"})
    )
    rounds = cohort_index.merge(traded_rounds, on=["signal_date", "entry_date", "exit_date"], how="left")
    active_dates = set(pool["datetime"].unique())
    rounds["regime_active"] = rounds["signal_date"].isin(active_dates)
    if regime_filter == "always":
        rounds = rounds.loc[rounds["holdings"].ge(minimum_holdings)].copy()
    else:
        active_but_untradable = rounds["regime_active"] & ~rounds["holdings"].ge(minimum_holdings)
        rounds = rounds.loc[~active_but_untradable].copy()
        rounds["net_return"] = rounds["net_return"].fillna(0.0)
        rounds["gross_return"] = rounds["gross_return"].fillna(0.0)
        rounds["holdings"] = rounds["holdings"].fillna(0).astype(int)
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
    stability_score = (
        min(year_returns) - 0.5 * abs(float(development["max_drawdown"]))
        if len(year_returns) >= 2 and min(year_returns) > 0.0 and development.get("max_drawdown") is not None
        else None
    )
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


def return_metrics(rounds: pd.DataFrame, hold_days: int) -> dict[str, float | int | None]:
    """Calculate net return, risk and drawdown from non-overlapping cohorts."""

    if rounds.empty:
        return {
            "rounds": 0,
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
    annualized_volatility = float(net.std(ddof=0) * math.sqrt(periods_per_year))
    return {
        "rounds": int(len(rounds)),
        "gross_cumulative_return": float((1.0 + gross).prod() - 1.0),
        "net_cumulative_return": float(equity.iloc[-1] - 1.0),
        "annualized_return": float(equity.iloc[-1] ** (periods_per_year / len(rounds)) - 1.0),
        "annualized_volatility": annualized_volatility,
        "sharpe_like": float(net.mean() / net.std(ddof=0) * math.sqrt(periods_per_year)) if net.std(ddof=0) else None,
        "max_drawdown": float(drawdown.min()),
        "win_rate": float((net > 0).mean()),
        "median_holdings": float(rounds["holdings"].median()),
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


def render_three_day_research_report(
    registry: dict[str, Any],
    ledger: dict[str, Any],
    shadow_ledger: dict[str, Any] | None = None,
    shadow_observation_registry: dict[str, Any] | None = None,
    no_eligible_studies: list[dict[str, Any]] | None = None,
    regime_audits: list[dict[str, Any]] | None = None,
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
    regime_audits = load_regime_audits(experiment_root)
    report = render_three_day_research_report(
        registry,
        ledger,
        shadow_ledger,
        shadow_observation_registry,
        no_eligible_studies,
        regime_audits,
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
        "regime_audits": len(regime_audits),
    }


def run_candidate_overlap_audit(args: argparse.Namespace) -> dict[str, Any]:
    """Measure whether several recorded candidates are genuinely distinct baskets."""

    names = list(dict.fromkeys(args.candidate))
    if len(names) < 2:
        raise ValueError("--candidate must be supplied at least twice")
    provider_uri = Path(args.provider_uri).expanduser()
    fundamental_path = Path(args.fundamentals).expanduser()
    experiment_root = Path(args.experiment_root).expanduser()
    candidates = [candidate_by_name(name, args.candidate_library) for name in names]
    fundamentals = load_fundamentals(fundamental_path)
    market = load_market_data(provider_uri, args.start, args.end, args.batch_size)
    market = attach_quality_asof(market, fundamentals, max_age_days=args.max_quality_age_days)
    ranked = rank_factor_frame(market)
    results: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
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
        results[candidate.name] = {
            "candidate": candidate,
            "baskets": baskets,
            "returns": returns,
            "summary": summary,
        }

    pairs: list[dict[str, Any]] = []
    for left_position, left_name in enumerate(names):
        for right_name in names[left_position + 1 :]:
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
                    "right_candidate": right_name,
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
        "candidate_library": args.candidate_library,
        "candidates": [
            {
                "name": candidate.name,
                "description": candidate.description,
                "weights": candidate.weights,
                "active_complete_baskets": len(results[candidate.name]["baskets"]),
                "return_cohorts": int(len(results[candidate.name]["returns"])),
                "development": results[candidate.name]["summary"]["development"],
                "development_stability": results[candidate.name]["summary"].get("development_stability"),
                "test": results[candidate.name]["summary"]["test"],
            }
            for candidate in candidates
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
            "test_period_used_for_pair_assessment": False,
        },
        "pairwise_overlap": pairs,
        "limitations": [
            "Basket overlap is a similarity diagnostic, not a strategy-selection or promotion rule.",
            "Only complete active TopK baskets are compared; inactive regimes are intentionally absent from basket overlap.",
            "The current holding universe is derived from a current listing snapshot and can introduce survivorship bias in historical results.",
        ],
    }
    destination = experiment_root / f"{run_id}_candidate_overlap_audit.json"
    _atomic_write_text(destination, json.dumps(audit, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return {
        "status": "completed",
        "audit_path": str(destination.resolve()),
        "candidate_count": len(candidates),
        "pairwise_overlap": pairs,
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

    overlap_audit = subparsers.add_parser(
        "candidate-overlap-audit", help="measure basket and return-series overlap across recorded candidates"
    )
    overlap_audit.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    overlap_audit.add_argument("--fundamentals", default=str(DEFAULT_FUNDAMENTALS))
    overlap_audit.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    overlap_audit.add_argument("--candidate", action="append", required=True, help="repeat for each candidate to compare")
    overlap_audit.add_argument("--candidate-library", choices=sorted(CANDIDATE_LIBRARIES), required=True)
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
    elif args.command == "regime-audit":
        report = run_regime_audit(args)
    elif args.command == "candidate-overlap-audit":
        report = run_candidate_overlap_audit(args)
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
