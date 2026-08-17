#!/usr/bin/env python3
"""Build Campaign098's frozen normalized range-clock-variance snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pandas as pd

from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign090_features as c90
from scripts import a_share_three_day_walkforward_campaign097_features as c97


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_098_no_return_preregistration.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_098_feature_implementation_freeze_v3_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign098_features.py"
)

PROTOCOL_SHA256 = "31dcecebeea81adab163acd76e21616e6b35726a2798bb4ca72cee4252ca78bd"
MECHANISM_AUDIT_SHA256 = (
    "b9844d51524781ba96cb00d217601e904fc25e08cc6350d5032953f7c11eb69f"
)
CURRENT_STATE_SHA256 = (
    "86db8a03d3ea0cb93edfd81bcaed96bd05016146cb7b84e38787db8068a24ef2"
)
NUMERIC_POLICY_SHA256 = (
    "5f13ed6f376cd428195b9e5783f30651bad761dbec7feb77b86eb7274dcf034a"
)

FACTOR_NAME = "intraday_range_clock_variance_240m"
FACTOR_FORMULA = (
    "for q_i=log(high_i/low_i), p_i=q_i/sum(q), u_i=i/239, and "
    "mu=sum(p_i*u_i), return 4*sum(p_i*(u_i-mu)^2) over exactly 240 bars"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low")
OUTPUT_COLUMNS = ("stock_day_key", FACTOR_NAME, f"{FACTOR_NAME}_eligible")
SELECTED_BAR_COUNT = 240
CLOCK_DENOMINATOR = 239
ENDPOINT_TOLERANCE = 1e-12
FULL_DEFINITION_COUNT = 129
FULL_DEFINITION_ORDER_SHA256 = (
    "2eaf839992ebfd09aed3e64cc8998c0d7e808e5678c10665442c1bc09ff0a875"
)
COMPARISON_COUNT = 126
COMPARISON_ORDER_SHA256 = (
    "1fdad7b688f9d66255aae59b30137e2e539adb24ed0bafddf8ccda1dded0a36c"
)
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign098_feature_library_v1"
)
PUBLICATION_RUNNER_SHA256 = (
    "c37124971238368ca233b38e9b3532fb52cf8e613e70d490afc15478e5107355"
)
PUBLICATION_IMPLEMENTATION_FREEZE_SHA256 = (
    "b232128e4c30e011e68ee47cd29c46f19a685cb2f51815f28427dfaf3996143e"
)


class Campaign098FeatureError(RuntimeError):
    """Fail closed when a frozen Campaign098 invariant changes."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _order_digest(items: list[dict[str, str]]) -> str:
    return c97._order_digest(items)


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = [dict(item) for item in c97.reconstruct_complete_definitions()]
    items.append({"name": c97.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != FULL_DEFINITION_COUNT
        or _order_digest(items) != FULL_DEFINITION_ORDER_SHA256
    ):
        raise Campaign098FeatureError("Campaign098 complete definition order changed")
    return items


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = [dict(item) for item in c97.reconstruct_comparisons()]
    items.append({"name": c97.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != COMPARISON_COUNT
        or _order_digest(items) != COMPARISON_ORDER_SHA256
    ):
        raise Campaign098FeatureError("Campaign098 comparator order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    if not path.is_file() or _sha256(path) != PROTOCOL_SHA256:
        raise Campaign098FeatureError(f"Campaign098 protocol changed: {path}")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign098FeatureError("Campaign098 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    chain = spec.get("source_chain") or {}
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    support = gates.get("support_predicate_before_source_rows") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign098_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign098_minute_source_candidate_comparator_daily_price_or_return_values"
        and (chain.get("mechanism_overlap_and_support_predicate_audit") or {}).get(
            "sha256"
        )
        == MECHANISM_AUDIT_SHA256
        and (chain.get("authoritative_iteration_state") or {}).get("sha256")
        == CURRENT_STATE_SHA256
        and (chain.get("numeric_comparator_policy_v43") or {}).get("sha256")
        == NUMERIC_POLICY_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("minute_source_projection") or ()) == RAW_COLUMNS
        and tuple(candidate.get("stock_day_identity_projection") or ())
        == tuple(c90.c86.IDENTITY_COLUMNS)
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("clock_coordinate_denominator") == CLOCK_DENOMINATOR
        and candidate.get("endpoint_tolerance") == ENDPOINT_TOLERANCE
        and candidate.get("valid_range")
        == {
            "lower": 0,
            "lower_inclusive": True,
            "upper": 1,
            "upper_inclusive": True,
        }
        and candidate.get("exact_support_predicate_gate_passed_before_source_rows")
        is True
        and support.get("required") is True
        and support.get("known_terminal_coverage_failure_inventory_reviewed") is True
        and support.get(
            "candidate_identical_to_or_provably_narrower_than_known_failure"
        )
        is False
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and uniqueness.get("complete_definition_count") == FULL_DEFINITION_COUNT
        and uniqueness.get("complete_definition_order_sha256")
        == FULL_DEFINITION_ORDER_SHA256
        and uniqueness.get("numeric_comparator_count") == COMPARISON_COUNT
        and uniqueness.get("numeric_comparator_order_sha256") == COMPARISON_ORDER_SHA256
        and uniqueness.get("all_126_numeric_comparators_must_pass") is True
        and uniqueness.get("candidate_specific_comparator_drop_allowed") is False
        and len(reconstruct_complete_definitions()) == FULL_DEFINITION_COUNT
        and len(reconstruct_comparisons()) == COMPARISON_COUNT
        and finite.get("trial_id")
        == "wf098_intraday_range_clock_variance_240m_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("expected_trial_count") == 1
        and finite.get("purge_local_signal_sessions_before_each_partition_boundary")
        == 3
        and finite.get("t_plus_1_and_t_plus_3_must_remain_inside_partition") is True
        and boundary.get("candidate_source_rows_read_before_freeze") is False
        and boundary.get("candidate_values_read_before_freeze") is False
        and boundary.get("comparison_values_read_before_coverage_pass") is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign098FeatureError("Campaign098 protocol semantics changed")
    return spec


def compute_range_clock_variance(
    highs: np.ndarray, lows: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return normalized variance, eligibility, total mass, ranges, and centers."""

    high = np.asarray(highs, dtype=np.float64)
    low = np.asarray(lows, dtype=np.float64)
    if high.ndim != 2 or high.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign098FeatureError("Campaign098 requires an n-by-240 high array")
    if low.ndim != 2 or low.shape != high.shape:
        raise Campaign098FeatureError("Campaign098 requires matching n-by-240 lows")
    source_valid = (
        np.isfinite(high).all(axis=1)
        & np.isfinite(low).all(axis=1)
        & (high > 0.0).all(axis=1)
        & (low > 0.0).all(axis=1)
        & (high >= low).all(axis=1)
    )
    clock = np.arange(SELECTED_BAR_COUNT, dtype=np.float64) / float(CLOCK_DENOMINATOR)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        ranges = np.log(high / low)
        totals = np.sum(ranges, axis=1, dtype=np.float64)
        weights = ranges / totals[:, None]
        centers = np.sum(weights * clock, axis=1, dtype=np.float64)
        raw_score = 4.0 * np.sum(
            weights * np.square(clock - centers[:, None]),
            axis=1,
            dtype=np.float64,
        )
    support = (
        source_valid
        & np.isfinite(ranges).all(axis=1)
        & (ranges >= 0.0).all(axis=1)
        & np.isfinite(totals)
        & (totals > 0.0)
        & np.isfinite(weights).all(axis=1)
        & np.isfinite(centers)
        & np.isfinite(raw_score)
    )
    result = np.full(len(high), np.nan, dtype=np.float64)
    candidate = raw_score[support].copy()
    candidate[np.abs(candidate) <= ENDPOINT_TOLERANCE] = 0.0
    candidate[np.abs(candidate - 1.0) <= ENDPOINT_TOLERANCE] = 1.0
    valid_score = np.isfinite(candidate) & (candidate >= 0.0) & (candidate <= 1.0)
    positions = np.flatnonzero(support)
    result[positions[valid_score]] = candidate[valid_score]
    eligible = np.isfinite(result) & (result >= 0.0) & (result <= 1.0)
    result[~eligible] = np.nan
    return result, eligible, totals, ranges, centers


def extract_range_clock_variance(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign098FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    empty = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            FACTOR_NAME: pd.Series(dtype="float64"),
        }
    )
    quality = {
        "source_rows": 0,
        "source_sessions": 0,
        "valid_range_clock_center_sessions": 0,
        "invalid_selected_source_sessions": 0,
        "nonpositive_total_range_sessions": 0,
        "invalid_ordered_range_sessions": 0,
        "zero_range_bars": 0,
        "endpoint_canonicalized_sessions": 0,
    }
    if raw.empty:
        return empty, quality
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["high"] = pd.to_numeric(work["high"], errors="coerce")
    work["low"] = pd.to_numeric(work["low"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign098FeatureError(f"raw minute identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    distinct = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].nunique()
    if (
        counts.empty
        or not counts.eq(c90.c86.SOURCE_BAR_COUNT).all()
        or not distinct.eq(c90.c86.SOURCE_BAR_COUNT).all()
        or not work["minute_code"].isin(c90.c86.SOURCE_MINUTE_CODE_SET).all()
    ):
        raise Campaign098FeatureError(f"raw minute grid changed for {symbol}")
    continuous = work.loc[
        work["minute_code"].isin(c90.c86.CONTINUOUS_MINUTE_CODE_SET),
        ["trade_date", "minute_code", "high", "low"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"],
        categories=c90.c86.CONTINUOUS_MINUTE_CODES,
        ordered=True,
    )
    continuous = continuous.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(counts.index).normalize()
    if len(continuous) != len(dates) * SELECTED_BAR_COUNT:
        raise Campaign098FeatureError(f"continuous minute grid changed for {symbol}")
    highs = (
        continuous["high"]
        .to_numpy(dtype=np.float64)
        .reshape(len(dates), SELECTED_BAR_COUNT)
    )
    lows = (
        continuous["low"]
        .to_numpy(dtype=np.float64)
        .reshape(len(dates), SELECTED_BAR_COUNT)
    )
    values, eligible, totals, ranges, _centers = compute_range_clock_variance(
        highs, lows
    )
    finite_positive = (
        np.isfinite(highs).all(axis=1)
        & np.isfinite(lows).all(axis=1)
        & (highs > 0.0).all(axis=1)
        & (lows > 0.0).all(axis=1)
    )
    ordered = finite_positive & (highs >= lows).all(axis=1)
    return pd.DataFrame({"trade_date": dates, FACTOR_NAME: values}), {
        "source_rows": int(len(work)),
        "source_sessions": int(len(dates)),
        "valid_range_clock_center_sessions": int(eligible.sum()),
        "invalid_selected_source_sessions": int((~finite_positive).sum()),
        "nonpositive_total_range_sessions": int(
            (ordered & (~np.isfinite(totals) | (totals <= 0.0))).sum()
        ),
        "invalid_ordered_range_sessions": int((finite_positive & ~ordered).sum()),
        "zero_range_bars": int(((ranges == 0.0) & ordered[:, None]).sum()),
        "endpoint_canonicalized_sessions": int(
            (eligible & ((values == 0.0) | (values == 1.0))).sum()
        ),
    }


def output_root(data_root: Path) -> Path:
    return (
        data_root.expanduser().resolve()
        / "derived/a_share/rich/tushare/minute_walkforward_campaign098_feature_library"
        / OUTPUT_RUN_ID
    )


def _load_implementation_freeze() -> dict[str, Any]:
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign098FeatureError("Campaign098 implementation freeze is absent")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign098_feature_implementation_freeze"
        and record.get("status")
        == "frozen_after_snapshot_publication_before_successful_independent_verification"
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (record.get("feature_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("candidate_source_rows_read_before_freeze") is True
        and record.get("candidate_values_computed_before_freeze") is True
        and record.get("comparator_values_read_before_freeze") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and record.get("provider_request_issued_before_freeze") is False
    ):
        raise Campaign098FeatureError("Campaign098 implementation freeze changed")
    return record


_ENGINE = c90._generated


@contextmanager
def _campaign098_binding() -> Iterator[None]:
    names: dict[str, Any] = {
        "__file__": str(Path(__file__).resolve()),
        "Campaign090FeatureError": Campaign098FeatureError,
        "DEFAULT_DATA_ROOT": DEFAULT_DATA_ROOT,
        "DEFAULT_PROTOCOL": DEFAULT_PROTOCOL,
        "DEFAULT_IMPLEMENTATION_FREEZE": DEFAULT_IMPLEMENTATION_FREEZE,
        "TEST_PATH": TEST_PATH,
        "PROTOCOL_SHA256": PROTOCOL_SHA256,
        "MECHANISM_AUDIT_SHA256": MECHANISM_AUDIT_SHA256,
        "CURRENT_STATE_SHA256": CURRENT_STATE_SHA256,
        "NUMERIC_POLICY_SHA256": NUMERIC_POLICY_SHA256,
        "FACTOR_NAME": FACTOR_NAME,
        "FACTOR_FORMULA": FACTOR_FORMULA,
        "OUTPUT_RUN_ID": OUTPUT_RUN_ID,
        "RAW_COLUMNS": RAW_COLUMNS,
        "OUTPUT_COLUMNS": OUTPUT_COLUMNS,
        "FULL_DEFINITION_COUNT": FULL_DEFINITION_COUNT,
        "FULL_DEFINITION_ORDER_SHA256": FULL_DEFINITION_ORDER_SHA256,
        "COMPARISON_COUNT": COMPARISON_COUNT,
        "COMPARISON_ORDER_SHA256": COMPARISON_ORDER_SHA256,
        "reconstruct_complete_definitions": reconstruct_complete_definitions,
        "reconstruct_comparisons": reconstruct_comparisons,
        "load_protocol": load_protocol,
        "compute_directional_amount_timing_spread": compute_range_clock_variance,
        "extract_directional_amount_timing_spread": extract_range_clock_variance,
        "output_root": output_root,
        "_load_implementation_freeze": _load_implementation_freeze,
    }
    previous = {name: _ENGINE.get(name) for name in names}
    _ENGINE.update(names)
    try:
        yield
    finally:
        _ENGINE.update(previous)


def _finalize_manifest(path: Path) -> None:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign098_feature_snapshot"
    ):
        return
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign090_feature_snapshot"
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == {FACTOR_NAME: "higher"}
        and manifest.get("factor_ranges") == {FACTOR_NAME: [0.0, 1.0]}
        and (manifest.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and manifest.get("comparison_values_read") is False
        and manifest.get("historical_forward_returns_read") is False
    ):
        raise Campaign098FeatureError("unexpected inherited snapshot semantics")
    quality = dict(manifest.get("quality") or {})
    quality["valid_range_clock_variance_sessions"] = int(
        quality.pop("valid_range_clock_center_sessions")
    )
    manifest["quality"] = quality
    manifest["kind"] = "a_share_three_day_walkforward_campaign098_feature_snapshot"
    manifest["status"] = "complete_no_return_candidate_snapshot"
    manifest["support_predicate"] = (
        "all 240 high-low pairs finite positive ordered, zero ranges retained, "
        "finite positive total log range, and normalized variance inside [0,1]"
    )
    manifest["clock_coordinate"] = "u_i=i/239 for i=0,...,239"
    manifest["population_variance_multiplier"] = 4.0
    manifest["source_open_close_volume_amount_or_peer_values_read"] = False
    manifest["candidate49_historical_backfill_performed"] = False
    manifest["prospective_candidate_created"] = False
    c90.c85._atomic_json(manifest, path)


def build_snapshot(
    *, data_root: Path, workers: int = 8, confirm_build: bool = False
) -> Path:
    load_protocol()
    _load_implementation_freeze()
    with _campaign098_binding():
        path = c90.build_snapshot(
            data_root=data_root, workers=workers, confirm_build=confirm_build
        )
        _finalize_manifest(path)
        return path


def _dataset_material(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocol_sha256": manifest["protocol"]["sha256"],
        "implementation_freeze_sha256": manifest["implementation_freeze"]["sha256"],
        "raw_manifest_sha256": manifest["source"]["raw_manifest_sha256"],
        "joint_clean_manifest_sha256": manifest["source"][
            "joint_clean_manifest_sha256"
        ],
        "eligible_keys_sha256": manifest["eligible_universe"]["keys_sha256"],
        "factor_name": FACTOR_NAME,
        "factor_formula": FACTOR_FORMULA,
        "factor_eligible_rows": manifest["factor_eligible_rows"][FACTOR_NAME],
        "files": manifest["files"],
    }


def verify_snapshot_files(manifest_path: Path) -> dict[str, Any]:
    _load_implementation_freeze()
    path = manifest_path.expanduser().resolve()
    expected = output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
    if path != expected.resolve() or not path.is_file():
        raise Campaign098FeatureError("Campaign098 manifest path changed")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign098_feature_snapshot"
        and manifest.get("status") == "complete_no_return_candidate_snapshot"
        and (manifest.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (manifest.get("implementation_freeze") or {}).get("sha256")
        == PUBLICATION_IMPLEMENTATION_FREEZE_SHA256
        and (manifest.get("feature_runner") or {}).get("sha256")
        == PUBLICATION_RUNNER_SHA256
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == {FACTOR_NAME: "higher"}
        and manifest.get("factor_ranges") == {FACTOR_NAME: [0.0, 1.0]}
        and manifest.get("rows") == c90.c86.EXPECTED_ROWS
        and manifest.get("partitions") == c90.c86.EXPECTED_PARTITIONS
        and manifest.get("calendar_sessions") == c90.c86.EXPECTED_SESSIONS
        and manifest.get("comparison_values_read") is False
        and manifest.get("historical_daily_price_fields_read") == []
        and manifest.get("historical_forward_returns_read") is False
        and manifest.get("provider_request_issued") is False
        and manifest.get("dataset_sha256")
        == c90._json_digest(_dataset_material(manifest))
    ):
        raise Campaign098FeatureError("Campaign098 manifest semantics changed")
    rows = eligible_count = 0
    all_keys: list[np.ndarray] = []
    for record in manifest.get("files") or []:
        partition = path.parent / str(record["path"])
        if _sha256(partition) != record.get("sha256"):
            raise Campaign098FeatureError("Campaign098 partition bytes changed")
        frame = pd.read_parquet(partition, columns=list(OUTPUT_COLUMNS))
        if c90.c85._frame_sha256(frame) != record.get("frame_sha256"):
            raise Campaign098FeatureError("Campaign098 partition frame changed")
        values = frame[FACTOR_NAME].to_numpy(dtype=np.float64)
        flags = frame[f"{FACTOR_NAME}_eligible"].astype(bool).to_numpy()
        finite = np.isfinite(values)
        if not (
            np.array_equal(flags, finite)
            and ((values[finite] >= 0.0) & (values[finite] <= 1.0)).all()
            and int(flags.sum()) == int(record["eligible_rows"])
            and _ENGINE["cache_v1"].canonical_column_sha256(values)
            == record.get("factor_canonical_value_sha256")
        ):
            raise Campaign098FeatureError("Campaign098 partition values changed")
        rows += len(frame)
        eligible_count += int(flags.sum())
        all_keys.append(frame["stock_day_key"].to_numpy(dtype=np.int64))
    keys = np.concatenate(all_keys)
    key_sha = hashlib.sha256(keys.astype("<i8", copy=False).tobytes()).hexdigest()
    if not (
        rows == c90.c86.EXPECTED_ROWS
        and eligible_count
        == (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
        and len(np.unique(keys)) == c90.c86.EXPECTED_ROWS
        and np.all(keys[1:] > keys[:-1])
        and key_sha == (manifest.get("eligible_universe") or {}).get("keys_sha256")
    ):
        raise Campaign098FeatureError("Campaign098 aggregate identity changed")
    return {
        "status": "verified",
        "dataset_sha256": manifest["dataset_sha256"],
        "partitions": len(manifest["files"]),
        "rows": rows,
        "eligible_rows": eligible_count,
        "comparison_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def status(data_root: Path = DEFAULT_DATA_ROOT) -> dict[str, Any]:
    load_protocol()
    path = output_root(data_root) / "snapshot_manifest.json"
    return {
        "status": "snapshot_present" if path.is_file() else "snapshot_absent_prebuild",
        "manifest_path": str(path),
        "implementation_freeze_present": DEFAULT_IMPLEMENTATION_FREEZE.is_file(),
        "source_rows_read_by_status": False,
        "candidate_values_computed_by_status": False,
        "comparator_values_read_by_status": False,
        "historical_daily_price_or_forward_return_values_read_by_status": False,
        "provider_request_issued_by_status": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    build.add_argument("--workers", type=int, default=8)
    build.add_argument("--confirm-build", action="store_true")
    inspect = sub.add_parser("status")
    inspect.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    verify = sub.add_parser("verify")
    verify.add_argument("--manifest", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "status":
        print(json.dumps(status(args.data_root), sort_keys=True))
        return 0
    if args.command == "build":
        print(
            build_snapshot(
                data_root=args.data_root,
                workers=args.workers,
                confirm_build=args.confirm_build,
            )
        )
        return 0
    manifest = args.manifest or (
        output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
    )
    print(json.dumps(verify_snapshot_files(manifest), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
