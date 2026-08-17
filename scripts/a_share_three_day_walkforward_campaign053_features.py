#!/usr/bin/env python3
"""Build and audit Campaign053 amount/price-discovery alignment."""

from __future__ import annotations

import argparse
import copy
import gc
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import scripts.a_share_three_day_preregistration_binding_validator as bindings
    import scripts.a_share_three_day_walkforward_campaign052_features_v3 as previous_entry
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_three_day_walkforward_campaign052_features_v3 as previous_entry


REPO_ROOT = Path(__file__).resolve().parents[1]
previous = previous_entry.runner
FACTOR_NAME = "intraday_amount_price_discovery_alignment_js_238p"
FACTOR_FORMULA = (
    "On the exact 240-bar grid, form 119 adjacent log-close returns within each "
    "half, excluding 09:30 and the lunch transition. For each of the 238 return "
    "endpoints use its nonnegative amount a_i. Let p_i=a_i/sum(a), "
    "q_i=abs(r_i)/sum(abs(r)), and m_i=(p_i+q_i)/2. Let "
    "JSD=0.5*sum(p_i*ln(p_i/m_i))+0.5*sum(q_i*ln(q_i/m_i)), with every zero "
    "contribution defined as zero. Return 1-JSD/ln(2)."
)
MECHANISM_AUDIT_SHA256 = "7cf02ae931c97427bc93339ef1fdf8c7a9547ebccb666a4a649e0b13f9467dd4"
PROTOCOL_SHA256 = "829f9781ed6d7bbf2d6c5d318abf03838c5916bdf944fc46f28da13cf2a8b02c"
IMPLEMENTATION_FREEZE_SHA256 = ""
SNAPSHOT_MANIFEST_SHA256 = ""
SNAPSHOT_DATASET_SHA256 = ""
SNAPSHOT_PUBLICATION_BINDING_SHA256 = ""
NO_RETURN_AUDIT_SHA256 = ""

TERMINAL_LIBRARY_COUNT = 66
INHERITED_COMPARISON_COUNT = 75
COMPARISON_COUNT = 76
INHERITED_COMPARISON_ORDER_SHA256 = "8c30647dde2f246dce84222ba7b4b18e61424f784cf522f97c95a6ee7dd802ec"
COMPARISON_ORDER_SHA256 = "e0740ee631eabfd281b5819379829feaabcd18910ab76a94623d3098d1e0b62e"
LOWER_BOUND = 0.0
UPPER_BOUND = 1.0
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign053_feature_library_v1"
)
DEFAULT_PROTOCOL = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_053_no_return_preregistration.json"
DEFAULT_IMPLEMENTATION_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_053_feature_implementation_freeze_20260803.json"
DEFAULT_SNAPSHOT_BINDING = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_053_snapshot_publication_binding_20260803.json"
DEFAULT_EXPERIMENT_ROOT = REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_053/no_return"
DEFAULT_DATA_ROOT = previous.DEFAULT_DATA_ROOT
RAW_COLUMNS = ("datetime", "symbol", "provider", "close", "amount")
BASE_COLUMNS = previous.BASE_COLUMNS
OUTPUT_COLUMNS = (
    "trade_date", "symbol", "provider", FACTOR_NAME, f"{FACTOR_NAME}_eligible",
)
FACTOR_NAMES = (FACTOR_NAME,)
FACTOR_DIRECTIONS = {FACTOR_NAME: "higher"}
FACTOR_RANGES = {FACTOR_NAME: (LOWER_BOUND, UPPER_BOUND)}
FACTOR_FORMULAS = {FACTOR_NAME: FACTOR_FORMULA}
C52_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign052_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign052_feature_library_v1/snapshot_manifest.json"
)
C52_SNAPSHOT_SHA256 = "04547981bed8a78438d7988296f1b3887a7d67b6604df555b207fac0b85a26c4"
C52_DATASET_SHA256 = "f9a6f08060c60c2183c587d6008ffa20f76735bdef46a989f02dff6ecba1a30e"
C52_FACTOR_NAME = "quarterly_announcement_delay_consistency_4q"

_generated = previous._generated
_engine_globals = previous._engine_globals
market = previous.market
campaign044 = previous.campaign044


class Campaign053FeatureError(RuntimeError):
    """Fail-closed Campaign053 feature boundary error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected_sha256:
        raise Campaign053FeatureError(f"{label} changed")


def _comparison_order_digest(comparisons: list[dict[str, Any]]) -> str:
    payload = json.dumps(
        [(str(item["name"]), str(item["score_direction"])) for item in comparisons],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def output_root(data_root: Path) -> Path:
    return (
        data_root.expanduser().resolve()
        / "derived/a_share/rich/tushare/minute_walkforward_campaign053_feature_library"
        / OUTPUT_RUN_ID
    )


def _load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_SHA256:
        raise Campaign053FeatureError("Campaign053 implementation freeze is not bound")
    _require_file(DEFAULT_IMPLEMENTATION_FREEZE, IMPLEMENTATION_FREEZE_SHA256, "Campaign053 implementation freeze")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    runner = record.get("feature_runner") or {}
    protocol = record.get("no_return_protocol") or {}
    if not (
        record.get("kind") == "a_share_three_day_walkforward_campaign053_feature_implementation_freeze"
        and record.get("status") == "frozen_before_campaign053_candidate_values"
        and Path(str(runner.get("path"))).resolve() == Path(__file__).resolve()
        and runner.get("sha256") == _sha256(Path(__file__).resolve())
        and protocol.get("sha256") == PROTOCOL_SHA256
        and record.get("candidate_values_read_before_freeze") is False
        and record.get("comparison_values_read_before_freeze") is False
        and record.get("historical_forward_returns_read_before_freeze") is False
    ):
        raise Campaign053FeatureError("Campaign053 implementation freeze semantics changed")
    return record


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    _require_file(path, PROTOCOL_SHA256, "Campaign053 no-return protocol")
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if validation.get("all_bindings_passed") is not True:
        raise Campaign053FeatureError("Campaign053 protocol has a failed binding")
    spec = json.loads(path.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    inherited = previous.load_protocol()
    inherited_comparisons = copy.deepcopy(
        inherited["ordered_no_return_gates"]["uniqueness_after_coverage_only"]["comparison_factors"]
    )
    comparisons = inherited_comparisons + [copy.deepcopy(uniqueness.get("final_comparison_factor") or {})]
    if not (
        spec.get("version") == 1
        and spec.get("kind") == "a_share_three_day_walkforward_campaign053_no_return_preregistration"
        and spec.get("status") == "frozen_before_campaign053_candidate_comparison_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and candidate.get("forbidden_source_columns") == ["open", "high", "low", "volume"]
        and candidate.get("accepted_minute_grid") == "09:31--11:30 and 13:01--15:00 exactly 240 bars; source 09:30 identity row is excluded"
        and candidate.get("return_pair_rule") == "119 adjacent log-close returns independently within each half; no 09:30 return and no lunch transition"
        and candidate.get("amount_alignment") == "nonnegative amount at each return endpoint, exactly 238 values"
        and candidate.get("normalization") == "one minus Jensen-Shannon divergence divided by natural-log two"
        and candidate.get("alternate_field_pairing_window_direction_scale_board_year_cost_regime_fit_combination_or_model_search") is False
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and uniqueness.get("maximum_allowed_absolute_median_daily_rank_correlation") == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and uniqueness.get("inherited_campaign052_comparison_factor_count") == INHERITED_COMPARISON_COUNT
        and uniqueness.get("inherited_campaign052_comparison_factor_order_sha256") == INHERITED_COMPARISON_ORDER_SHA256
        and uniqueness.get("comparison_factor_count") == COMPARISON_COUNT
        and uniqueness.get("comparison_factor_order_sha256") == COMPARISON_ORDER_SHA256
        and len(inherited_comparisons) == INHERITED_COMPARISON_COUNT
        and len(comparisons) == COMPARISON_COUNT
        and _comparison_order_digest(comparisons) == COMPARISON_ORDER_SHA256
        and finite.get("trial_id") == f"wf053_{FACTOR_NAME}_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("expected_trial_count") == 1
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_historical_return_read") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign053FeatureError("Campaign053 protocol semantics changed")
    result = copy.deepcopy(spec)
    result["ordered_no_return_gates"]["uniqueness_after_coverage_only"]["comparison_factors"] = comparisons
    return result


def compute_factor_values(
    closes: np.ndarray, endpoint_amounts: np.ndarray
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the exact frozen Jensen-Shannon alignment for stock-days."""
    closes = np.asarray(closes, dtype=float)
    endpoint_amounts = np.asarray(endpoint_amounts, dtype=float)
    if closes.ndim != 2 or closes.shape[1] != 240:
        raise Campaign053FeatureError("closes must have shape (n, 240)")
    if endpoint_amounts.shape != (closes.shape[0], 238):
        raise Campaign053FeatureError("endpoint amounts must have shape (n, 238)")
    valid_close = np.isfinite(closes).all(axis=1) & (closes > 0.0).all(axis=1)
    valid_amount = np.isfinite(endpoint_amounts).all(axis=1) & (endpoint_amounts >= 0.0).all(axis=1)
    returns = np.full((len(closes), 238), np.nan, dtype=float)
    if len(closes):
        logged = np.full_like(closes, np.nan, dtype=float)
        logged[valid_close] = np.log(closes[valid_close])
        returns[:, :119] = np.diff(logged[:, :120], axis=1)
        returns[:, 119:] = np.diff(logged[:, 120:], axis=1)
    amount_total = np.where(valid_amount, endpoint_amounts.sum(axis=1), np.nan)
    absolute = np.abs(returns)
    return_total = np.where(valid_close, absolute.sum(axis=1), np.nan)
    eligible = valid_close & valid_amount & (amount_total > 0.0) & (return_total > 0.0)
    score = np.full(len(closes), np.nan, dtype=float)
    if eligible.any():
        p = endpoint_amounts[eligible] / amount_total[eligible, None]
        q = absolute[eligible] / return_total[eligible, None]
        m = 0.5 * (p + q)
        with np.errstate(divide="ignore", invalid="ignore"):
            p_term = np.where(p > 0.0, p * np.log(p / m), 0.0)
            q_term = np.where(q > 0.0, q * np.log(q / m), 0.0)
        jsd = 0.5 * (p_term.sum(axis=1) + q_term.sum(axis=1))
        score[eligible] = 1.0 - jsd / np.log(2.0)
    in_range = np.isfinite(score) & (score >= LOWER_BOUND - 1e-12) & (score <= UPPER_BOUND + 1e-12)
    score[np.isfinite(score)] = np.clip(score[np.isfinite(score)], LOWER_BOUND, UPPER_BOUND)
    eligible &= in_range
    score[~eligible] = np.nan
    quality = {
        f"{FACTOR_NAME}__invalid_close_rows": int((~valid_close).sum()),
        f"{FACTOR_NAME}__invalid_amount_rows": int((~valid_amount).sum()),
        f"{FACTOR_NAME}__zero_total_endpoint_amount_rows": int((valid_amount & ~(amount_total > 0.0)).sum()),
        f"{FACTOR_NAME}__zero_total_absolute_return_rows": int((valid_close & ~(return_total > 0.0)).sum()),
        f"{FACTOR_NAME}__range_or_nonfinite_score_rows": int(((valid_close & valid_amount & (amount_total > 0.0) & (return_total > 0.0)) & ~in_range).sum()),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
    }
    return {FACTOR_NAME: score}, {FACTOR_NAME: eligible}, quality


def compute_partition_frame(
    raw: pd.DataFrame,
    base_frame: pd.DataFrame,
    _unused_benchmark: Any,
    *,
    symbol: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign053FeatureError(f"unexpected raw columns for {symbol}: {tuple(raw.columns)}")
    if tuple(base_frame.columns) != BASE_COLUMNS:
        raise Campaign053FeatureError(f"unexpected joint-base columns for {symbol}: {tuple(base_frame.columns)}")
    base_work = base_frame.copy()
    base_work["trade_date"] = pd.to_datetime(base_work["trade_date"], errors="coerce").dt.normalize()
    base_work["symbol"] = base_work["symbol"].astype(str).str.upper()
    if (
        base_work["trade_date"].isna().any()
        or (not base_work.empty and set(base_work["symbol"].unique()) != {symbol.upper()})
        or base_work.duplicated(["trade_date", "symbol"]).any()
    ):
        raise Campaign053FeatureError(f"joint-base identity changed for {symbol}")
    base_work = base_work.sort_values("trade_date", kind="stable").reset_index(drop=True)
    if base_work.empty:
        return empty_output_frame(), {"base_rows": 0}
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign053FeatureError(f"raw identity changed for {symbol}")
    work["close"] = pd.to_numeric(work["close"], errors="coerce")
    work["amount"] = pd.to_numeric(work["amount"], errors="coerce")
    work["trade_date"] = work["datetime"].dt.normalize()
    work = work.loc[work["trade_date"].isin(base_work["trade_date"])].copy()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    source_counts = work.groupby("trade_date", sort=True, observed=True).size()
    if not source_counts.eq(241).all():
        raise Campaign053FeatureError(f"every source stock-day must retain 241 rows for {symbol}")
    source_codes = work.groupby("trade_date", sort=True, observed=True)["minute_code"].agg(lambda values: frozenset(int(value) for value in values))
    if not source_codes.eq(market.SOURCE_MINUTE_CODE_SET).all():
        raise Campaign053FeatureError(f"source minute grid changed for {symbol}")
    expected_dates = pd.Series(pd.Index(source_counts.index)).reset_index(drop=True)
    if not base_work["trade_date"].reset_index(drop=True).equals(expected_dates):
        raise Campaign053FeatureError(f"source and joint-base dates changed for {symbol}")
    continuous = work.loc[work["minute_code"].isin(set(int(x) for x in market.CONTINUOUS_MINUTE_CODES))].sort_values(["trade_date", "datetime"], kind="stable")
    if len(continuous) != len(base_work) * 240:
        raise Campaign053FeatureError(f"continuous grid row count changed for {symbol}")
    closes = continuous["close"].to_numpy(dtype=float).reshape(len(base_work), 240)
    amounts = continuous["amount"].to_numpy(dtype=float).reshape(len(base_work), 240)
    endpoint_amounts = np.concatenate((amounts[:, 1:120], amounts[:, 121:240]), axis=1)
    values, eligible, quality = compute_factor_values(closes, endpoint_amounts)
    quality["base_rows"] = len(base_work)
    frame = pd.DataFrame({
        "trade_date": base_work["trade_date"],
        "symbol": symbol.upper(),
        "provider": "tushare",
        FACTOR_NAME: values[FACTOR_NAME],
        f"{FACTOR_NAME}_eligible": eligible[FACTOR_NAME],
    })
    return frame.loc[:, OUTPUT_COLUMNS], quality


def _validate_snapshot_manifest(manifest: dict[str, Any], *, require_fingerprint_constants: bool) -> None:
    if not require_fingerprint_constants:
        manifest["kind"] = "a_share_three_day_walkforward_campaign053_feature_snapshot"
        manifest["source_open_high_low_read"] = False
        manifest["source_close_read"] = True
        manifest["source_volume_read"] = False
        manifest["source_amount_read"] = True
        evidence = {k: v for k, v in (manifest.get("protocol_evidence") or {}).items() if not k.startswith("campaign052_") and not k.startswith("campaign053_")}
        evidence["campaign053_mechanism_overlap_audit_sha256"] = MECHANISM_AUDIT_SHA256
        evidence["campaign053_no_return_preregistration_sha256"] = PROTOCOL_SHA256
        evidence["campaign053_implementation_freeze_sha256"] = IMPLEMENTATION_FREEZE_SHA256
        manifest["protocol_evidence"] = evidence
    evidence = manifest.get("protocol_evidence") or {}
    quality = manifest.get("quality") or {}
    files = list(manifest.get("files") or [])
    eligible_rows = (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    if not (
        manifest.get("schema_version") == 1
        and manifest.get("kind") == "a_share_three_day_walkforward_campaign053_feature_snapshot"
        and manifest.get("status") == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("source_fields_read") == list(RAW_COLUMNS)
        and manifest.get("source_open_high_low_read") is False
        and manifest.get("source_close_read") is True
        and manifest.get("source_volume_read") is False
        and manifest.get("source_amount_read") is True
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == FACTOR_DIRECTIONS
        and manifest.get("factor_formulas") == FACTOR_FORMULAS
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and evidence.get("campaign053_mechanism_overlap_audit_sha256") == MECHANISM_AUDIT_SHA256
        and evidence.get("campaign053_no_return_preregistration_sha256") == PROTOCOL_SHA256
        and evidence.get("campaign053_implementation_freeze_sha256") == IMPLEMENTATION_FREEZE_SHA256
        and isinstance(manifest.get("rows"), int) and manifest["rows"] > 0
        and manifest.get("partitions") == len(files)
        and quality.get("base_rows") == manifest.get("rows")
        and quality.get(f"{FACTOR_NAME}__eligible_rows") == eligible_rows
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("comparison_factor_values_read") is False
        and manifest.get("candidate49_historical_return_read") is False
        and manifest.get("training_or_model_fitting_performed") is False
        and manifest.get("current_scoring_selection_sizing_or_orders_performed") is False
        and manifest.get("prospective_candidate_activation_created") is False
    ):
        raise Campaign053FeatureError("Campaign053 snapshot semantics changed")
    if require_fingerprint_constants and not (
        SNAPSHOT_MANIFEST_SHA256 and SNAPSHOT_DATASET_SHA256 and manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
    ):
        raise Campaign053FeatureError("Campaign053 snapshot fingerprint is not bound")


def _install_engine_globals() -> None:
    values = {
        "DEFAULT_PROTOCOL": DEFAULT_PROTOCOL,
        "DEFAULT_EXPERIMENT_ROOT": DEFAULT_EXPERIMENT_ROOT,
        "RAW_COLUMNS": RAW_COLUMNS,
        "FACTOR_NAME": FACTOR_NAME,
        "FACTOR_NAMES": FACTOR_NAMES,
        "FACTOR_DIRECTIONS": FACTOR_DIRECTIONS,
        "FACTOR_RANGES": FACTOR_RANGES,
        "FACTOR_FORMULA": FACTOR_FORMULA,
        "FACTOR_FORMULAS": FACTOR_FORMULAS,
        "OUTPUT_COLUMNS": OUTPUT_COLUMNS,
        "OUTPUT_RUN_ID": OUTPUT_RUN_ID,
        "PROTOCOL_SHA256": PROTOCOL_SHA256,
        "SNAPSHOT_MANIFEST_SHA256": SNAPSHOT_MANIFEST_SHA256,
        "SNAPSHOT_DATASET_SHA256": SNAPSHOT_DATASET_SHA256,
        "NO_RETURN_AUDIT_SHA256": NO_RETURN_AUDIT_SHA256,
        "load_protocol": load_protocol,
        "compute_factor_values": compute_factor_values,
        "compute_partition_frame": compute_partition_frame,
        "_validate_snapshot_manifest": _validate_snapshot_manifest,
        "output_root": output_root,
    }
    _generated.update(values)
    _engine_globals.update(values)


_install_engine_globals()
empty_output_frame = _generated["empty_output_frame"]
verify_snapshot_files = _generated["verify_snapshot_files"]


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    _load_implementation_freeze()
    _install_engine_globals()
    inherited = _generated["_inherited_build_snapshot"]
    inherited_writer = inherited.__globals__["_inherited_build_snapshot"]
    publication_foundation = inherited_writer.__globals__["foundation"]
    original = publication_foundation.atomic_write_json

    def write_with_truth(value: dict[str, Any], path: Path) -> None:
        if value.get("kind") == "a_share_three_day_walkforward_campaign053_feature_snapshot" and value.get("output_run_id") == OUTPUT_RUN_ID:
            value = dict(value)
            value.update({
                "source_open_high_low_read": False,
                "source_close_read": True,
                "source_volume_read": False,
                "source_amount_read": True,
                "quarterly_disclosure_fields_read": [],
                "quarterly_value_fields_read": [],
            })
        original(value, path)

    publication_foundation.atomic_write_json = write_with_truth
    try:
        return inherited(data_root=data_root, workers=workers)
    finally:
        publication_foundation.atomic_write_json = original


def _load_candidate_frame(manifest_path: Path, manifest: dict[str, Any]) -> pd.DataFrame:
    _, _, engine, _, _, _ = campaign044._context()
    return engine.load_factor_frame(manifest_path, manifest, FACTOR_NAME)


def run_no_return_audit(*, data_root: Path, experiment_root: Path, workers: int) -> Path:
    _load_implementation_freeze()
    if not (SNAPSHOT_MANIFEST_SHA256 and SNAPSHOT_DATASET_SHA256 and SNAPSHOT_PUBLICATION_BINDING_SHA256):
        raise Campaign053FeatureError("bind Campaign053 snapshot and publication record before audit")
    _require_file(DEFAULT_SNAPSHOT_BINDING, SNAPSHOT_PUBLICATION_BINDING_SHA256, "Campaign053 snapshot publication binding")
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_protocol()

    _require_file(C52_SNAPSHOT_PATH, C52_SNAPSHOT_SHA256, "Campaign052 snapshot manifest")
    c52_manifest = json.loads(C52_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    if c52_manifest.get("dataset_sha256") != C52_DATASET_SHA256:
        raise Campaign053FeatureError("Campaign052 snapshot dataset changed")
    previous._install_engine_globals()
    c52_verification = previous.verify_snapshot_files(c52_manifest, C52_SNAPSHOT_PATH, workers)

    _install_engine_globals()
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    _require_file(manifest_path, SNAPSHOT_MANIFEST_SHA256, "Campaign053 snapshot manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    existing = sorted(experiment_root.glob("*_campaign053_no_return_audit.json"))
    if existing:
        if len(existing) != 1 or not NO_RETURN_AUDIT_SHA256 or _sha256(existing[0]) != NO_RETURN_AUDIT_SHA256:
            raise Campaign053FeatureError("existing Campaign053 audit is ambiguous or unbound")
        return existing[0]
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    prior, foundation, engine, _, candidate49, comparison_engine = campaign044._context()
    eligible_keys = foundation.quality_listing_eligible_keys(prior.load_protocol())
    candidate = _load_candidate_frame(manifest_path, manifest)
    quality_frame, coverage = engine.coverage_and_capacity(candidate, eligible_keys, spec, FACTOR_NAME)
    del candidate, eligible_keys
    gc.collect()
    if coverage["gate_passed_before_comparison_values"]:
        gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
        expected_order = [str(item["name"]) for item in gate["comparison_factors"]]
        directions = {str(item["name"]): str(item["score_direction"]) for item in gate["comparison_factors"]}
        keys, values = engine._sorted_candidate_arrays(quality_frame, FACTOR_NAME)
        catalog, source_verifications = campaign044._build_source_catalog(data_root=data_root, workers=workers, verify_files=True)
        comparisons: list[dict[str, Any]] = []
        for source in catalog:
            aligned = campaign044._load_aligned_source_values(source, keys)
            for factor in source["factors"]:
                comparisons.append(comparison_engine._aligned_comparison_result(
                    candidate_keys=keys, candidate_values=values,
                    comparison_values=aligned.pop(factor), comparison=factor,
                    direction=directions[factor], gate=gate,
                ))
            del aligned
            gc.collect()
        if len(comparisons) != TERMINAL_LIBRARY_COUNT:
            raise Campaign053FeatureError("complete 66-factor catalog changed")
        _, candidate49_path, candidate49_manifest = engine._comparison_chain(data_root)
        candidate49_verification = candidate49.verify_snapshot_files(candidate49_manifest, candidate49_path, workers)
        candidate49_values = engine._load_filtered_comparison_values_explicit(candidate49_manifest, [candidate49.FACTOR_NAME], keys)[candidate49.FACTOR_NAME]
        comparisons.append(comparison_engine._aligned_comparison_result(
            candidate_keys=keys, candidate_values=values,
            comparison_values=candidate49_values, comparison=candidate49.FACTOR_NAME,
            direction="higher", gate=gate,
        ))
        del candidate49_values
        gc.collect()
        extra_verifications: dict[str, Any] = {}
        for label, source_path, expected_sha, expected_dataset, factor, module in previous._extra_comparison_sources():
            _require_file(source_path, expected_sha, f"{label} snapshot manifest")
            source_manifest = json.loads(source_path.read_text(encoding="utf-8"))
            if expected_dataset is not None and source_manifest.get("dataset_sha256") != expected_dataset:
                raise Campaign053FeatureError(f"{label} snapshot dataset changed")
            extra_verifications[label] = module.verify_snapshot_files(source_manifest, source_path, workers)
            comparison_values = engine._load_filtered_comparison_values_explicit(source_manifest, [factor], keys)[factor]
            comparisons.append(comparison_engine._aligned_comparison_result(
                candidate_keys=keys, candidate_values=values,
                comparison_values=comparison_values, comparison=factor,
                direction="higher", gate=gate,
            ))
            del comparison_values
            gc.collect()
        c52_values = engine._load_filtered_comparison_values_explicit(c52_manifest, [C52_FACTOR_NAME], keys)[C52_FACTOR_NAME]
        comparisons.append(comparison_engine._aligned_comparison_result(
            candidate_keys=keys, candidate_values=values,
            comparison_values=c52_values, comparison=C52_FACTOR_NAME,
            direction="higher", gate=gate,
        ))
        del c52_values
        gc.collect()
        observed_order = [str(item["comparison_factor"]) for item in comparisons]
        observed_correlations = [float(item["absolute_median_daily_rank_correlation"]) for item in comparisons if item["absolute_median_daily_rank_correlation"] is not None]
        passed = observed_order == expected_order and len(comparisons) == COMPARISON_COUNT and all(item["gate_passed"] for item in comparisons)
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": True,
            "comparison_factor_count": len(comparisons),
            "comparison_order_matches_preregistration": observed_order == expected_order,
            "terminal_66_source_snapshot_verification": source_verifications,
            "candidate49_snapshot_file_verification": candidate49_verification,
            **{f"{key}_snapshot_file_verification": value for key, value in extra_verifications.items()},
            "campaign052_snapshot_file_verification": c52_verification,
            "comparisons": comparisons,
            "maximum_observed_absolute_median_daily_rank_correlation": max(observed_correlations) if observed_correlations else None,
            "all_required_comparisons_passed": passed,
        }
        del keys, values
        gc.collect()
    else:
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": False,
            "comparisons": [],
            "all_required_comparisons_passed": False,
            "failure_reason": "coverage_gate_failed",
        }
    admitted = bool(coverage["gate_passed_before_comparison_values"] and uniqueness["all_required_comparisons_passed"])
    research = prior.research
    run_id = f"{research._timestamp()}_campaign053_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign053_no_return_audit",
        "status": "completed_with_one_admissible_factor_pending_walkforward_preregistration" if admitted else "completed_zero_admissible_factors_stop_before_historical_returns",
        "run_id": run_id,
        "created_at": research._timestamp(),
        "protocol": {"path": str(DEFAULT_PROTOCOL.resolve()), "sha256": PROTOCOL_SHA256},
        "candidate_snapshot": {"path": str(manifest_path), "sha256": SNAPSHOT_MANIFEST_SHA256, "dataset_sha256": SNAPSHOT_DATASET_SHA256},
        "snapshot_publication_binding": {"path": str(DEFAULT_SNAPSHOT_BINDING.resolve()), "sha256": SNAPSHOT_PUBLICATION_BINDING_SHA256},
        "snapshot_file_verification": verification,
        "coverage_and_capacity": {FACTOR_NAME: coverage},
        "uniqueness": {FACTOR_NAME: uniqueness},
        "admissible_factor_names": [FACTOR_NAME] if admitted else [],
        "admissible_factor_count": 1 if admitted else 0,
        "failed_factor_names": [] if admitted else [FACTOR_NAME],
        "next_action": "freeze the exact one-trial Campaign053 walk-forward catalog before reading 2019-2023 returns" if admitted else "record the no-return rejection and design a genuinely new campaign",
        "source_fields_read": list(RAW_COLUMNS),
        "minute_open_high_low_volume_fields_read": [],
        "minute_close_and_amount_fields_read": ["close", "amount"],
        "quarterly_disclosure_fields_read": [],
        "quarterly_value_fields_read": [],
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "candidate49_prospective_ledgers_changed": False,
        "second_prospective_candidate_created": False,
        "training_or_model_fitting_performed": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    destination = experiment_root / f"{run_id}.json"
    foundation.atomic_write_json(record, destination)
    return destination


def status(data_root: Path, experiment_root: Path) -> dict[str, Any]:
    _install_engine_globals()
    manifest_path = output_root(data_root.expanduser().resolve()) / "snapshot_manifest.json"
    audits = sorted(experiment_root.expanduser().resolve().glob("*_campaign053_no_return_audit.json"))
    result = {
        "protocol_path": str(DEFAULT_PROTOCOL.resolve()),
        "protocol_sha256_bound": True,
        "implementation_freeze_sha256_bound": bool(IMPLEMENTATION_FREEZE_SHA256),
        "snapshot_manifest_path": str(manifest_path),
        "snapshot_exists": manifest_path.is_file(),
        "snapshot_sha256_bound": bool(SNAPSHOT_MANIFEST_SHA256),
        "audit_count": len(audits),
        "no_return_audit_sha256_bound": bool(NO_RETURN_AUDIT_SHA256),
        "source_fields_read_by_status": list(RAW_COLUMNS),
        "daily_price_fields_read_by_status": False,
        "forward_return_fields_read_by_status": False,
        "candidate49_historical_return_read": False,
        "second_prospective_candidate_created": False,
    }
    if manifest_path.is_file():
        result["snapshot_observed_sha256"] = _sha256(manifest_path)
    if audits:
        result["latest_audit"] = str(audits[-1])
        result["latest_audit_observed_sha256"] = _sha256(audits[-1])
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "build", "no-return-audit"):
        command = subparsers.add_parser(name)
        command.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
        command.add_argument("--workers", type=int, default=4)
        if name in {"status", "no-return-audit"}:
            command.add_argument("--experiment-root", type=Path, default=DEFAULT_EXPERIMENT_ROOT)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "status":
        payload = status(args.data_root, args.experiment_root)
    elif args.command == "build":
        payload = {"manifest": str(build_snapshot(data_root=args.data_root, workers=args.workers))}
    else:
        payload = {"audit": str(run_no_return_audit(data_root=args.data_root, experiment_root=args.experiment_root, workers=args.workers))}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
