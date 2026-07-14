"""Audit time-safe nonlinear three-day A-share factor models.

This deliberately small model family is a research diagnostic after repeated
fixed-weight factor grids failed the three-day stability gate.  It uses the
same close-known features, next-session-open entry and three-session-close
exit as ``a_share_short_horizon_factor_research.py``.  Each evaluation year is
predicted by a separately fitted model using only earlier signal dates; 2026
is never used to choose a configuration.

The generated audit is research-only.  It neither registers a strategy nor
emits a trading signal.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import a_share_short_horizon_factor_research as research


DEFAULT_PROVIDER_URI = REPO_ROOT / "data" / "qlib" / "cn_a_share"
DEFAULT_FUNDAMENTALS = research.DEFAULT_FUNDAMENTALS
DEFAULT_EXPERIMENT_ROOT = REPO_ROOT / "data" / "experiments" / "short_horizon"
# Keep the model family immutable when the broader exploratory diagnostic
# catalog grows.  A new model feature set needs its own explicitly named audit.
DEFAULT_FEATURES = tuple(sorted({factor for candidate in research.V7_CANDIDATES for factor in candidate.weights}))
DEFAULT_FEATURE_SET = "v1_full"
STABLE_PRICE_VOLUME_FEATURES = (
    "amplitude_low",
    "amplitude_low_1",
    "volatility_low_20",
    "volume_dry_up",
)
MODEL_CONFIGURATIONS = ("ridge", "lgbm_shallow", "lgbm_ranker_shallow")
# These are existing close-known market states from the factor-research
# harness.  The compact set deliberately tests only: no gate, a broad positive
# medium-term market state, and that same state with a pre-existing risk
# filter.  It is not an unrestricted post-hoc regime sweep.
MODEL_REGIME_FILTERS = (
    "always",
    "breadth_20_positive",
    "breadth_20_positive_and_volatility_below_trailing_p75",
)


@dataclass(frozen=True)
class ModelConfiguration:
    """One deliberately fixed, low-complexity model hypothesis."""

    name: str
    description: str


@dataclass(frozen=True)
class ModelFeatureSet:
    """One immutable, auditable set of score-time model inputs."""

    name: str
    description: str
    columns: tuple[str, ...]
    formation_rule: str


MODEL_SPECS = {
    "ridge": ModelConfiguration(
        name="ridge",
        description="Regularized linear regression over the existing close-known factor directions.",
    ),
    "lgbm_shallow": ModelConfiguration(
        name="lgbm_shallow",
        description="Shallow regularized gradient boosting over the same factor set to test limited interactions.",
    ),
    "lgbm_ranker_shallow": ModelConfiguration(
        name="lgbm_ranker_shallow",
        description=(
            "Shallow LambdaRank boosting over within-signal-date forward-return quintiles, aligned to TopK ordering."
        ),
    ),
}

MODEL_FEATURE_SETS = {
    DEFAULT_FEATURE_SET: ModelFeatureSet(
        name=DEFAULT_FEATURE_SET,
        description="All fixed V7 close-known factor directions, frozen before the model audit family was added.",
        columns=DEFAULT_FEATURES,
        formation_rule="Predeclared full technical-and-quality model input set.",
    ),
    "v2_stable_price_volume": ModelFeatureSet(
        name="v2_stable_price_volume",
        description=(
            "Only the four close-known price-volume factors that passed the fixed 2019--2025 cross-year "
            "single-factor stability audit."
        ),
        columns=STABLE_PRICE_VOLUME_FEATURES,
        formation_rule=(
            "Diagnostic-driven historical sensitivity set; it may be audited only and can never be registered, "
            "promoted, or turned into a trading signal from this historical run."
        ),
    ),
}


def _timestamp() -> str:
    return pd.Timestamp.now(tz="UTC").strftime("%Y%m%dT%H%M%SZ")


def _json_default(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    raise TypeError(f"not JSON serializable: {type(value).__name__}")


def validate_model_configuration(name: str) -> ModelConfiguration:
    """Return a fixed model specification and reject unrecorded configurations."""

    try:
        return MODEL_SPECS[name]
    except KeyError as exc:
        choices = ", ".join(sorted(MODEL_SPECS))
        raise ValueError(f"unknown model configuration {name!r}; choose one of: {choices}") from exc


def model_feature_set(name: str) -> ModelFeatureSet:
    """Return an immutable model input set and reject unrecorded feature changes."""

    try:
        return MODEL_FEATURE_SETS[name]
    except KeyError as exc:
        choices = ", ".join(sorted(MODEL_FEATURE_SETS))
        raise ValueError(f"unknown model feature_set {name!r}; choose one of: {choices}") from exc


def annual_evaluation_segments(
    signal_dates: Iterable[pd.Timestamp], development_start: str, development_end: str
) -> list[tuple[str, pd.DatetimeIndex]]:
    """Split signals into annual development folds plus one later test segment.

    All signals before ``development_start`` are reserved for the first model
    fit.  Development years are evaluated independently, so the selection
    metrics cannot be dominated by one unusually favorable calendar year.
    """

    dates = pd.DatetimeIndex(sorted(pd.to_datetime(list(signal_dates)).unique()))
    development_start_ts = pd.Timestamp(development_start)
    development_end_ts = pd.Timestamp(development_end)
    if development_start_ts > development_end_ts:
        raise ValueError("development_start must not be after development_end")
    if not len(dates):
        raise ValueError("no signal dates are available for model research")
    segments: list[tuple[str, pd.DatetimeIndex]] = []
    for year in range(development_start_ts.year, development_end_ts.year + 1):
        segment = dates[(dates.year == year) & (dates >= development_start_ts) & (dates <= development_end_ts)]
        if len(segment):
            segments.append((f"development_{year}", segment))
    test = dates[dates > development_end_ts]
    if len(test):
        segments.append(("test", test))
    if not segments or not any(name.startswith("development_") for name, _ in segments):
        raise ValueError("no development-year signals match the requested model research window")
    first_development = next(segment for name, segment in segments if name.startswith("development_"))
    if not (dates < first_development.min()).any():
        raise ValueError("model research needs at least one earlier signal date before the first development year")
    return segments


def deterministic_daily_sample(frame: pd.DataFrame, maximum_per_signal: int) -> pd.DataFrame:
    """Cap training rows per signal date without using labels or random state."""

    if maximum_per_signal < 1:
        raise ValueError("maximum_per_signal must be positive")
    required = {"signal_date", "instrument"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"training frame is missing columns: {', '.join(missing)}")
    if frame.empty:
        return frame.copy()
    sampled = frame.copy()
    sampled["_sample_hash"] = pd.util.hash_pandas_object(
        sampled[["signal_date", "instrument"]].astype(str), index=False
    )
    sampled = sampled.sort_values(["signal_date", "_sample_hash", "instrument"], kind="stable")
    sampled = sampled.groupby("signal_date", sort=False).head(maximum_per_signal).copy()
    return sampled.drop(columns="_sample_hash")


def build_training_frame(
    features: pd.DataFrame, labels: pd.DataFrame, feature_columns: Iterable[str]
) -> pd.DataFrame:
    """Join outcomes only for fitting; score-time universes remain unfiltered by future quotes."""

    columns = tuple(feature_columns)
    required_features = {"signal_date", "instrument", *columns}
    missing_features = sorted(required_features - set(features.columns))
    if missing_features:
        raise ValueError(f"model features are missing columns: {', '.join(missing_features)}")
    required_labels = {"signal_date", "instrument", "forward_gross_return"}
    missing_labels = sorted(required_labels - set(labels.columns))
    if missing_labels:
        raise ValueError(f"model labels are missing columns: {', '.join(missing_labels)}")
    joined = features[["signal_date", "instrument", *columns]].merge(
        labels[["signal_date", "instrument", "forward_gross_return"]],
        on=["signal_date", "instrument"],
        how="inner",
        validate="one_to_one",
    )
    joined = joined.loc[np.isfinite(joined["forward_gross_return"].to_numpy(dtype=float, copy=False))].copy()
    return joined.sort_values(["signal_date", "instrument"], kind="stable")


def cross_sectional_relevance(frame: pd.DataFrame, buckets: int = 5) -> pd.DataFrame:
    """Add deterministic within-date return buckets for the ranking-only model.

    The feature sample is chosen before this function and does not depend on
    labels.  Relevance is then calculated only from realized historical
    returns within each training signal date; score-time rows never receive or
    require this label.  ``method='first'`` makes ties deterministic by the
    pre-existing signal-date/instrument ordering.
    """

    if buckets < 2:
        raise ValueError("ranking relevance buckets must be at least two")
    required = {"signal_date", "instrument", "forward_gross_return"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"training frame is missing ranking-label columns: {', '.join(missing)}")
    result = frame.sort_values(["signal_date", "instrument"], kind="stable").copy()
    ranks = result.groupby("signal_date", sort=False)["forward_gross_return"].rank(method="first", pct=True)
    result["ranking_relevance"] = np.minimum(
        buckets - 1, np.ceil(ranks.to_numpy(dtype=float, copy=False) * buckets).astype(int) - 1
    )
    return result


def make_estimator(configuration: str):
    """Instantiate only one of the predeclared low-resource estimators."""

    validate_model_configuration(configuration)
    if configuration == "ridge":
        from sklearn.linear_model import Ridge

        return Ridge(alpha=10.0)
    from lightgbm import LGBMRanker, LGBMRegressor

    if configuration == "lgbm_ranker_shallow":
        return LGBMRanker(
            objective="lambdarank",
            metric="ndcg",
            n_estimators=100,
            learning_rate=0.04,
            num_leaves=15,
            max_depth=4,
            min_child_samples=400,
            colsample_bytree=0.8,
            subsample=0.8,
            subsample_freq=1,
            reg_lambda=5.0,
            random_state=17,
            n_jobs=1,
            verbosity=-1,
        )

    return LGBMRegressor(
        objective="regression",
        n_estimators=100,
        learning_rate=0.04,
        num_leaves=15,
        max_depth=4,
        min_child_samples=400,
        colsample_bytree=0.8,
        subsample=0.8,
        subsample_freq=1,
        reg_lambda=5.0,
        random_state=17,
        n_jobs=1,
        verbosity=-1,
    )


def fit_model(configuration: str, estimator: Any, train_features: pd.DataFrame, train: pd.DataFrame) -> None:
    """Fit one fixed model while keeping rank labels confined to training dates."""

    if configuration != "lgbm_ranker_shallow":
        estimator.fit(train_features, train["forward_gross_return"].astype(float))
        return
    required = {"signal_date", "ranking_relevance"}
    missing = sorted(required - set(train.columns))
    if missing:
        raise ValueError(f"ranker training frame is missing columns: {', '.join(missing)}")
    groups = train.groupby("signal_date", sort=False).size().tolist()
    if not groups or min(groups) < 2:
        raise ValueError("ranker training needs at least two sampled stocks in every signal-date group")
    estimator.fit(train_features, train["ranking_relevance"].astype(int), group=groups)


def factor_feature_frame(ranked: pd.DataFrame, signal_dates: pd.DatetimeIndex, feature_columns: Iterable[str]) -> pd.DataFrame:
    """Return all score-time eligible names without filtering by future execution data."""

    columns = tuple(feature_columns)
    required = {"datetime", "instrument", "quality_eligible", *columns}
    missing = sorted(required - set(ranked.columns))
    if missing:
        raise ValueError(f"ranked market frame is missing model features: {', '.join(missing)}")
    frame = ranked.loc[
        ranked["quality_eligible"].fillna(False) & ranked["datetime"].isin(signal_dates),
        ["datetime", "instrument", *columns],
    ].copy()
    frame = frame.rename(columns={"datetime": "signal_date"})
    return frame.sort_values(["signal_date", "instrument"], kind="stable")


def active_regime_dates(ranked: pd.DataFrame, signal_dates: pd.DatetimeIndex, regime_filter: str) -> pd.DatetimeIndex:
    """Return close-known signal dates allowed by one predeclared market gate."""

    if regime_filter not in research.REGIME_FILTERS:
        choices = ", ".join(sorted(research.REGIME_FILTERS))
        raise ValueError(f"unknown model regime_filter {regime_filter!r}; choose one of: {choices}")
    required = {"datetime", "quality_eligible"}
    missing = sorted(required - set(ranked.columns))
    if missing:
        raise ValueError(f"ranked market frame is missing regime fields: {', '.join(missing)}")
    signal_rows = ranked.loc[
        ranked["quality_eligible"].fillna(False) & ranked["datetime"].isin(signal_dates)
    ].copy()
    active = research.apply_regime_filter(signal_rows, regime_filter)
    return pd.DatetimeIndex(sorted(pd.to_datetime(active["datetime"]).unique()))


def score_topk_rounds(
    predictions: pd.DataFrame,
    labels: pd.DataFrame,
    signal_dates: pd.DatetimeIndex,
    topk: int,
    open_cost: float,
    close_cost: float,
    active_signal_dates: pd.DatetimeIndex | None = None,
) -> tuple[pd.DataFrame, dict[str, float | int | None]]:
    """Score complete TopK baskets; incomplete future-quote baskets remain cash.

    Predictions are ranked before future returns are joined.  Consequently a
    missing entry or exit quote cannot cause a model to substitute a
    hindsight-selected fourth name.
    """

    if topk < 1:
        raise ValueError("topk must be positive")
    required_predictions = {"signal_date", "instrument", "score"}
    missing_predictions = sorted(required_predictions - set(predictions.columns))
    if missing_predictions:
        raise ValueError(f"predictions are missing columns: {', '.join(missing_predictions)}")
    active_dates = (
        pd.DatetimeIndex(signal_dates)
        if active_signal_dates is None
        else pd.DatetimeIndex(sorted(pd.to_datetime(active_signal_dates).unique()))
    )
    active_dates = active_dates.intersection(pd.DatetimeIndex(signal_dates))
    selected = (
        predictions.loc[predictions["signal_date"].isin(active_dates)]
        .sort_values(["signal_date", "score", "instrument"], ascending=[True, False, True], kind="stable")
        .groupby("signal_date", sort=False)
        .head(topk)
        .copy()
    )
    joined = selected.merge(
        labels[["signal_date", "instrument", "forward_gross_return"]],
        on=["signal_date", "instrument"],
        how="left",
        validate="one_to_one",
    )
    basket = (
        joined.groupby("signal_date", sort=True)
        .agg(
            selected_holdings=("instrument", "nunique"),
            complete_returns=("forward_gross_return", "count"),
            gross_return=("forward_gross_return", "mean"),
        )
        .reindex(signal_dates)
    )
    basket["regime_active"] = basket.index.isin(active_dates)
    complete = (
        basket["regime_active"]
        & basket["selected_holdings"].eq(topk)
        & basket["complete_returns"].eq(topk)
    )
    basket["holdings"] = np.where(complete, topk, 0)
    basket["gross_return"] = basket["gross_return"].where(complete, 0.0).fillna(0.0)
    basket["net_return"] = (1.0 - open_cost) * (1.0 + basket["gross_return"]) * (1.0 - close_cost) - 1.0
    basket.loc[~complete, "net_return"] = 0.0
    rounds = basket.reset_index(names="signal_date")
    return rounds, research.return_metrics(rounds, hold_days=3)


def score_diagnostics(predictions: pd.DataFrame, labels: pd.DataFrame) -> dict[str, float | int | None]:
    """Calculate daily cross-sectional IC only where realized labels exist."""

    merged = predictions.merge(
        labels[["signal_date", "instrument", "forward_gross_return"]],
        on=["signal_date", "instrument"],
        how="inner",
        validate="one_to_one",
    )
    values: list[float] = []
    rank_values: list[float] = []
    for _, group in merged.groupby("signal_date", sort=True):
        valid = group[["score", "forward_gross_return"]].dropna()
        if len(valid) < 3 or valid["score"].nunique() < 2 or valid["forward_gross_return"].nunique() < 2:
            continue
        pearson = valid["score"].corr(valid["forward_gross_return"], method="pearson")
        spearman = valid["score"].corr(valid["forward_gross_return"], method="spearman")
        if pd.notna(pearson) and pd.notna(spearman):
            values.append(float(pearson))
            rank_values.append(float(spearman))
    def _summary(items: list[float], prefix: str) -> dict[str, float | int | None]:
        if not items:
            return {f"{prefix}_mean": None, f"{prefix}_std": None, f"{prefix}ir": None}
        array = np.asarray(items, dtype=float)
        standard_deviation = float(array.std(ddof=0))
        mean = float(array.mean())
        return {
            f"{prefix}_mean": mean,
            f"{prefix}_std": standard_deviation,
            f"{prefix}ir": float(mean / standard_deviation) if standard_deviation else None,
        }
    return {
        "days_with_ic": len(values),
        **_summary(values, "ic"),
        **_summary(rank_values, "rank_ic"),
    }


def configuration_selection_score(development_years: list[dict[str, Any]], development: dict[str, Any]) -> float | None:
    """Apply the same every-year-positive and -20% drawdown rule to model outputs."""

    returns = [item.get("topk", {}).get("net_cumulative_return") for item in development_years]
    if len(returns) < 2 or any(value is None or float(value) <= 0.0 for value in returns):
        return None
    drawdown = development.get("max_drawdown")
    if drawdown is None or float(drawdown) < research.STRICT_DEVELOPMENT_MAX_DRAWDOWN:
        return None
    return float(min(float(value) for value in returns) - 0.5 * abs(float(drawdown)))


def run_model_audit(args: argparse.Namespace) -> dict[str, Any]:
    """Fit predeclared annual walk-forward models and preserve an untouched test period."""

    if args.hold_days != 3:
        raise ValueError("this model audit is intentionally defined only for the three-session holding period")
    if args.topk < 1:
        raise ValueError("topk must be positive")
    if args.train_window_rounds < 20 or args.maximum_train_rows_per_signal < args.topk:
        raise ValueError("training window and daily sample cap are too small for model research")
    provider_uri = Path(args.provider_uri).expanduser()
    fundamental_path = Path(args.fundamentals).expanduser()
    experiment_root = Path(args.experiment_root).expanduser()
    configurations = tuple(args.configuration or MODEL_CONFIGURATIONS)
    for configuration in configurations:
        validate_model_configuration(configuration)
    if len(set(configurations)) != len(configurations):
        raise ValueError("each model configuration may be supplied only once")
    regime_filters = tuple(args.regime_filter or MODEL_REGIME_FILTERS)
    for regime_filter in regime_filters:
        if regime_filter not in research.REGIME_FILTERS:
            choices = ", ".join(sorted(research.REGIME_FILTERS))
            raise ValueError(f"unknown model regime_filter {regime_filter!r}; choose one of: {choices}")
    if len(set(regime_filters)) != len(regime_filters):
        raise ValueError("each model regime_filter may be supplied only once")
    feature_set = model_feature_set(getattr(args, "feature_set", DEFAULT_FEATURE_SET))

    fundamentals = research.load_fundamentals(fundamental_path)
    market = research.load_market_data(provider_uri, args.start, args.end, args.batch_size)
    market = research.attach_quality_asof(market, fundamentals, max_age_days=args.max_quality_age_days)
    ranked = research.rank_factor_frame(market)
    calendar = pd.DatetimeIndex(sorted(ranked["datetime"].unique()))
    signal_dates = calendar[: -(args.hold_days + 1) : args.hold_days]
    feature_columns = feature_set.columns
    features = factor_feature_frame(ranked, signal_dates, feature_columns)
    labels = research.forward_factor_return_frame(ranked, args.hold_days)
    training = build_training_frame(features, labels, feature_columns)
    segments = annual_evaluation_segments(signal_dates, args.development_start, args.development_end)
    active_dates_by_regime = {
        regime_filter: active_regime_dates(ranked, signal_dates, regime_filter)
        for regime_filter in regime_filters
    }
    records: list[dict[str, Any]] = []
    for configuration in configurations:
        fold_records_by_regime: dict[str, list[dict[str, Any]]] = {regime_filter: [] for regime_filter in regime_filters}
        fold_rounds_by_regime: dict[str, list[pd.DataFrame]] = {regime_filter: [] for regime_filter in regime_filters}
        for segment_name, evaluation_dates in segments:
            training_dates = signal_dates[signal_dates < evaluation_dates.min()][-args.train_window_rounds :]
            train = training.loc[training["signal_date"].isin(training_dates)].copy()
            train = deterministic_daily_sample(train, args.maximum_train_rows_per_signal)
            if configuration == "lgbm_ranker_shallow":
                train = cross_sectional_relevance(train)
            evaluation = features.loc[features["signal_date"].isin(evaluation_dates)].copy()
            if train.empty or evaluation.empty:
                raise ValueError(f"{configuration} has no rows for {segment_name}")
            estimator = make_estimator(configuration)
            train_features = train[list(feature_columns)].astype(float).fillna(0.5)
            fit_model(configuration, estimator, train_features, train)
            prediction = evaluation[["signal_date", "instrument"]].copy()
            prediction["score"] = estimator.predict(evaluation[list(feature_columns)].astype(float).fillna(0.5))
            prediction_diagnostics = score_diagnostics(prediction, labels)
            for regime_filter in regime_filters:
                active_dates = active_dates_by_regime[regime_filter].intersection(evaluation_dates)
                rounds, topk = score_topk_rounds(
                    prediction,
                    labels,
                    evaluation_dates,
                    args.topk,
                    args.open_cost,
                    args.close_cost,
                    active_signal_dates=active_dates,
                )
                rounds["segment"] = segment_name
                fold_rounds_by_regime[regime_filter].append(rounds)
                fold_records_by_regime[regime_filter].append(
                    {
                        "segment": segment_name,
                        "signal_start": evaluation_dates.min().date().isoformat(),
                        "signal_end": evaluation_dates.max().date().isoformat(),
                        "training_signal_start": training_dates.min().date().isoformat(),
                        "training_signal_end": training_dates.max().date().isoformat(),
                        "training_rows": int(len(train)),
                        "evaluation_rows": int(len(evaluation)),
                        "regime_active_rounds": int(len(active_dates)),
                        "topk": topk,
                        "prediction": prediction_diagnostics,
                    }
                )
        for regime_filter in regime_filters:
            fold_records = fold_records_by_regime[regime_filter]
            development_folds = [record for record in fold_records if record["segment"].startswith("development_")]
            all_rounds = pd.concat(fold_rounds_by_regime[regime_filter], ignore_index=True)
            development_rounds = all_rounds.loc[all_rounds["segment"].str.startswith("development_")].copy()
            test_rounds = all_rounds.loc[all_rounds["segment"].eq("test")].copy()
            development = research.return_metrics(development_rounds, args.hold_days)
            test = research.return_metrics(test_rounds, args.hold_days)
            selection_score = configuration_selection_score(development_folds, development)
            records.append(
                {
                    "configuration": configuration,
                    "regime_filter": regime_filter,
                    "regime_filter_description": research.REGIME_FILTERS[regime_filter],
                    "model_key": f"{configuration}__{regime_filter}",
                    "configuration_description": validate_model_configuration(configuration).description,
                    "development_selection_score": selection_score,
                    "development": development,
                    "test": test,
                    "development_stability": {
                        "calendar_year_count": len(development_folds),
                        "positive_calendar_year_count": sum(
                            float(record["topk"]["net_cumulative_return"] or 0.0) > 0.0
                            for record in development_folds
                        ),
                        "worst_calendar_year_net_cumulative_return": min(
                            (record["topk"]["net_cumulative_return"] for record in development_folds),
                            default=None,
                        ),
                        "max_drawdown_cap": research.STRICT_DEVELOPMENT_MAX_DRAWDOWN,
                        "passes_max_drawdown_cap": (
                            development.get("max_drawdown") is not None
                            and float(development["max_drawdown"]) >= research.STRICT_DEVELOPMENT_MAX_DRAWDOWN
                        ),
                    },
                    "folds": fold_records,
                }
            )

    ranking = sorted(
        records,
        key=lambda record: (
            float(record["development_selection_score"])
            if record["development_selection_score"] is not None
            else float("-inf")
        ),
        reverse=True,
    )
    winner = next(
        (record["model_key"] for record in ranking if record["development_selection_score"] is not None),
        None,
    )
    run_id = _timestamp()
    audit = {
        "run_id": run_id,
        "status": "completed",
        "purpose": "three_day_walk_forward_model_research_only_not_investment_advice",
        "model_family": "predeclared_ridge_shallow_lightgbm_and_shallow_lambdarank_with_compact_existing_market_gates",
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
        "features": {
            "feature_set": feature_set.name,
            "description": feature_set.description,
            "formation_rule": feature_set.formation_rule,
            "count": len(feature_columns),
            "names": list(feature_columns),
            "missing_value_fill": 0.5,
            "ranker_target": "within-signal-date forward-gross-return quintiles" if "lgbm_ranker_shallow" in configurations else None,
        },
        "protocol": {
            "development_start": args.development_start,
            "development_end": args.development_end,
            "yearly_refit": True,
            "train_window_rounds": args.train_window_rounds,
            "maximum_train_rows_per_signal": args.maximum_train_rows_per_signal,
            "training_sample": "deterministic per-signal hash sample independent of labels",
            "regime_filters": list(regime_filters),
            "regime_filter_selection": "three predeclared close-known states; test period does not select a gate",
            "test_period_used_for_configuration_selection": False,
        },
        "quality_gate": {
            "source": str(fundamental_path.resolve()),
            "sha256": research.file_sha256(fundamental_path),
            "effective_date": "strictly next local trading day after announcement_date",
            "max_quality_age_days": args.max_quality_age_days,
        },
        "data": {
            "provider_uri": str(provider_uri.resolve()),
            "calendar_start": market["datetime"].min().date().isoformat(),
            "calendar_end": market["datetime"].max().date().isoformat(),
            "market_rows": int(len(market)),
            "eligible_rows": int(market["quality_eligible"].sum()),
            "labeled_training_rows": int(len(training)),
        },
        "selection_rule": (
            "Require every development calendar year to have positive TopK net cumulative return and pooled "
            "development max_drawdown no worse than -20%; then maximize the worst development-year return minus "
            "0.5 * absolute pooled development max_drawdown.  Test metrics are not used for selection."
        ),
        "winner_configuration_selected_on_development_only": winner,
        "ranking_by_development": ranking,
        "limitations": [
            "This audit is historical research only; no configuration is registered, promoted, or converted into a trading signal.",
            "The holding universe is derived from a current listing snapshot and can introduce survivorship bias in historical results.",
            "Prices require the accepted point-in-time restoration-factor contract; exact limit queues, suspensions, market impact, and fill priority remain unsimulated.",
            "The post-development period is already historical evidence and remains a diagnostic check, not new forward proof.",
        ],
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    destination = experiment_root / f"{run_id}_model_audit.json"
    research._atomic_write_text(
        destination, json.dumps(audit, ensure_ascii=False, indent=2, default=_json_default) + "\n"
    )
    return {
        "status": "completed",
        "audit_path": str(destination.resolve()),
        "winner_configuration_selected_on_development_only": winner,
        "ranking_by_development": [
            {
                "model_key": record["model_key"],
                "configuration": record["configuration"],
                "regime_filter": record["regime_filter"],
                "development_selection_score": record["development_selection_score"],
                "development": record["development"],
                "test": record["test"],
            }
            for record in ranking
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider-uri", default=str(DEFAULT_PROVIDER_URI))
    parser.add_argument("--fundamentals", default=str(DEFAULT_FUNDAMENTALS))
    parser.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    parser.add_argument("--start", default="2019-01-01")
    parser.add_argument("--end", help="defaults to the local Qlib calendar end")
    parser.add_argument("--development-start", default="2023-01-01")
    parser.add_argument("--development-end", default="2025-12-31")
    parser.add_argument("--hold-days", type=int, default=3)
    parser.add_argument("--topk", type=int, default=3)
    parser.add_argument("--open-cost", type=float, default=0.00012)
    parser.add_argument("--close-cost", type=float, default=0.00062)
    parser.add_argument("--max-quality-age-days", type=int, default=550)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--train-window-rounds", type=int, default=336)
    parser.add_argument("--maximum-train-rows-per-signal", type=int, default=384)
    parser.add_argument(
        "--feature-set",
        default=DEFAULT_FEATURE_SET,
        choices=sorted(MODEL_FEATURE_SETS),
        help="immutable score-time feature set; a non-default diagnostic-driven set remains research-only",
    )
    parser.add_argument("--configuration", action="append", choices=sorted(MODEL_SPECS))
    parser.add_argument(
        "--regime-filter",
        action="append",
        choices=sorted(research.REGIME_FILTERS),
        help="repeat a predeclared close-known market gate; defaults to the compact model-gate audit set",
    )
    return parser.parse_args()


def main() -> int:
    report = run_model_audit(parse_args())
    print(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
