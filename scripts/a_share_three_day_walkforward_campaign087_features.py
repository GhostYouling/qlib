#!/usr/bin/env python3
"""Build Campaign087's frozen range/amount profile-alignment snapshot."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pandas as pd

from scripts import a_share_three_day_compact_comparator_cache as cache_v1
from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign085_features as c85
from scripts import a_share_three_day_walkforward_campaign086_features as c86
from scripts import a_share_three_day_walkforward_campaign086_features_v4 as c86_v4

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = c86.DEFAULT_DATA_ROOT
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_087_no_return_preregistration.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_087_feature_implementation_freeze_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign087_features.py"
)

PROTOCOL_SHA256 = "9adc09b52ec1b9844f3dd99b2cf815046c4143d9ae584fcf135552b32c17114c"
MECHANISM_AUDIT_SHA256 = (
    "183b65c5097937308d59c092a35979c370dc2a6dda384d3137020822a2d272ed"
)
CURRENT_STATE_SHA256 = (
    "124affacf9b3665589cfc08a72e6886c5d1baa2dd5fc721b7450f066755dc12b"
)
NUMERIC_POLICY_SHA256 = (
    "945b74a66688c1534a351fe8d8bc0eb2570070ae6379f12838386fabb450283b"
)
C86_SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_086_feature_snapshot_binding_20260807.json"
)
C86_SNAPSHOT_BINDING_SHA256 = (
    "61c29d28967f7ea37532f5e9f6eb440171237224261f60dad0db9be5bde7b563"
)
C86_SNAPSHOT_MANIFEST = (
    c86.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
)
C86_SNAPSHOT_MANIFEST_SHA256 = (
    "848ce713344f1ce805e3180344107d1d4bee5f8350bbcf52f8089e391fae3803"
)
C86_SNAPSHOT_DATASET_SHA256 = (
    "49cf11b5d69fa38a72f1a977975e290d4ed0bfd2205be6c50ba08dc64844b8e3"
)

FACTOR_NAME = "intraday_range_amount_profile_alignment_js_240m"
FACTOR_FORMULA = (
    "on exactly 240 bars r_i=ln(high_i/low_i), p_i=r_i/sum(r), "
    "q_i=amount_i/sum(amount), m_i=(p_i+q_i)/2; return "
    "1-[0.5*sum_{p_i>0}p_i*ln(p_i/m_i)+"
    "0.5*sum_{q_i>0}q_i*ln(q_i/m_i)]/ln(2)"
)
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_walkforward_"
    "campaign087_feature_library_v1"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "high", "low", "amount")
IDENTITY_COLUMNS = c86.IDENTITY_COLUMNS
SELECTED_BAR_COUNT = c86.SELECTED_BAR_COUNT
SOURCE_BAR_COUNT = c86.SOURCE_BAR_COUNT
ENDPOINT_TOLERANCE = 1e-12
OUTPUT_COLUMNS = ("stock_day_key", FACTOR_NAME, f"{FACTOR_NAME}_eligible")
EXPECTED_ROWS = c86.EXPECTED_ROWS
EXPECTED_PARTITIONS = c86.EXPECTED_PARTITIONS
EXPECTED_SESSIONS = c86.EXPECTED_SESSIONS
EXPECTED_RAW_PARTITIONS = c86.EXPECTED_RAW_PARTITIONS
EXPECTED_JOINT_CLEAN_ROWS = c86.EXPECTED_JOINT_CLEAN_ROWS
FULL_DEFINITION_COUNT = 118
FULL_DEFINITION_ORDER_SHA256 = (
    "261b5bac3512a91492d91e69fdbe8f6b571738e55a19553b5344f044697115f9"
)
COMPARISON_COUNT = 116
COMPARISON_ORDER_SHA256 = (
    "e84ad824a5b3044c45a541a6650b3e18af801b09a34871c3e6ab8c73c36891b2"
)


class Campaign087FeatureError(RuntimeError):
    """Fail-closed Campaign087 feature error."""


def _sha256(path: Path) -> str:
    return c86._sha256(path)


def _json_digest(value: Any) -> str:
    return c86._json_digest(value)


def _comparison_order_digest(items: list[dict[str, str]]) -> str:
    return c86._comparison_order_digest(items)


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign087FeatureError(f"Campaign087 {label} changed: {path}")


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = c86.reconstruct_comparisons()
    items.append({"name": c86.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != COMPARISON_COUNT
        or _comparison_order_digest(items) != COMPARISON_ORDER_SHA256
        or items[-1]
        != {"name": c86.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign087FeatureError("Campaign087 numeric comparison order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = c86.reconstruct_complete_definitions()
    items.append({"name": c86.FACTOR_NAME, "score_direction": "higher"})
    if (
        len(items) != FULL_DEFINITION_COUNT
        or _comparison_order_digest(items) != FULL_DEFINITION_ORDER_SHA256
    ):
        raise Campaign087FeatureError("Campaign087 complete definition order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    _require(path, PROTOCOL_SHA256, "protocol")
    _require(C86_SNAPSHOT_BINDING, C86_SNAPSHOT_BINDING_SHA256, "Campaign086 binding")
    _require(C86_SNAPSHOT_MANIFEST, C86_SNAPSHOT_MANIFEST_SHA256, "Campaign086 manifest")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign087FeatureError("Campaign087 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    chain = spec.get("source_chain") or {}
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    unique = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    previous = json.loads(C86_SNAPSHOT_MANIFEST.read_text(encoding="utf-8"))
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign087_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign087_minute_source_candidate_comparison_daily_price_or_return_values"
        and (chain.get("mechanism_overlap_audit") or {}).get("sha256")
        == MECHANISM_AUDIT_SHA256
        and (chain.get("authoritative_iteration_state") or {}).get("sha256")
        == CURRENT_STATE_SHA256
        and (chain.get("numeric_comparator_policy_v25") or {}).get("sha256")
        == NUMERIC_POLICY_SHA256
        and (chain.get("campaign086_terminal_numeric_comparator") or {}).get(
            "dataset_sha256"
        )
        == C86_SNAPSHOT_DATASET_SHA256
        and previous.get("dataset_sha256") == C86_SNAPSHOT_DATASET_SHA256
        and previous.get("factor_names") == [c86.FACTOR_NAME]
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("minute_source_projection") or ()) == RAW_COLUMNS
        and tuple(candidate.get("stock_day_identity_projection") or ())
        == IDENTITY_COLUMNS
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("endpoint_canonicalization_tolerance")
        == ENDPOINT_TOLERANCE
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and unique.get("complete_definition_count") == FULL_DEFINITION_COUNT
        and unique.get("complete_definition_order_sha256")
        == FULL_DEFINITION_ORDER_SHA256
        and unique.get("numeric_comparator_count") == COMPARISON_COUNT
        and unique.get("numeric_comparator_order_sha256") == COMPARISON_ORDER_SHA256
        and unique.get("all_116_numeric_comparators_must_pass") is True
        and len(reconstruct_comparisons()) == COMPARISON_COUNT
        and len(reconstruct_complete_definitions()) == FULL_DEFINITION_COUNT
        and finite.get("trial_id")
        == "wf087_intraday_range_amount_profile_alignment_js_240m_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1]
        and finite.get("expected_trial_count") == 1
        and boundary.get("comparison_values_read_before_coverage_pass") is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign087FeatureError("Campaign087 protocol semantics changed")
    return spec


def compute_profile_alignment(
    highs: np.ndarray, lows: np.ndarray, amounts: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return score, eligibility, total log range, and total amount by session."""

    high = np.asarray(highs, dtype=np.float64)
    low = np.asarray(lows, dtype=np.float64)
    amount = np.asarray(amounts, dtype=np.float64)
    expected = (len(high), SELECTED_BAR_COUNT) if high.ndim == 2 else None
    if expected is None or high.shape != expected or low.shape != expected or amount.shape != expected:
        raise Campaign087FeatureError("profile alignment requires aligned n-by-240 arrays")
    source_valid = (
        np.isfinite(high).all(axis=1)
        & np.isfinite(low).all(axis=1)
        & np.isfinite(amount).all(axis=1)
        & (high > 0.0).all(axis=1)
        & (low > 0.0).all(axis=1)
        & (low <= high).all(axis=1)
        & (amount >= 0.0).all(axis=1)
    )
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        ranges = np.log(high / low)
    ranges[~np.isfinite(ranges)] = np.nan
    total_range = np.sum(ranges, axis=1)
    total_amount = np.sum(amount, axis=1)
    support = (
        source_valid
        & np.isfinite(total_range)
        & (total_range > 0.0)
        & np.isfinite(total_amount)
        & (total_amount > 0.0)
    )
    result = np.full(len(high), np.nan, dtype=np.float64)
    if support.any():
        positions = np.flatnonzero(support)
        p = ranges[support] / total_range[support, None]
        q = amount[support] / total_amount[support, None]
        m = (p + q) / 2.0
        p_term = np.zeros_like(p)
        q_term = np.zeros_like(q)
        p_positive = p > 0.0
        q_positive = q > 0.0
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            p_term[p_positive] = p[p_positive] * np.log(
                p[p_positive] / m[p_positive]
            )
            q_term[q_positive] = q[q_positive] * np.log(
                q[q_positive] / m[q_positive]
            )
        jsd = 0.5 * (p_term.sum(axis=1) + q_term.sum(axis=1))
        score = 1.0 - jsd / np.log(2.0)
        score[np.abs(score) <= ENDPOINT_TOLERANCE] = 0.0
        score[np.abs(score - 1.0) <= ENDPOINT_TOLERANCE] = 1.0
        valid_score = np.isfinite(score) & (score >= 0.0) & (score <= 1.0)
        result[positions[valid_score]] = score[valid_score]
    eligible = np.isfinite(result) & (result >= 0.0) & (result <= 1.0)
    result[~eligible] = np.nan
    return result, eligible, total_range, total_amount


def extract_profile_alignment(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign087FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    empty = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            FACTOR_NAME: pd.Series(dtype="float64"),
        }
    )
    if raw.empty:
        return empty, {
            "source_rows": 0,
            "source_sessions": 0,
            "valid_serial_persistence_sessions": 0,
            "invalid_selected_source_sessions": 0,
            "insufficient_pair_sessions": 0,
            "zero_range_selected_bars": 0,
            "retained_informative_pairs": 0,
        }
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    for name in ("high", "low", "amount"):
        work[name] = pd.to_numeric(work[name], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign087FeatureError(f"raw minute identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    distinct = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].nunique()
    if (
        counts.empty
        or not counts.eq(SOURCE_BAR_COUNT).all()
        or not distinct.eq(SOURCE_BAR_COUNT).all()
        or not work["minute_code"].isin(c86.SOURCE_MINUTE_CODE_SET).all()
    ):
        raise Campaign087FeatureError(f"raw minute grid changed for {symbol}")
    continuous = work.loc[
        work["minute_code"].isin(c86.CONTINUOUS_MINUTE_CODE_SET),
        ["trade_date", "minute_code", "high", "low", "amount"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"],
        categories=c86.CONTINUOUS_MINUTE_CODES,
        ordered=True,
    )
    continuous = continuous.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(counts.index).normalize()
    if len(continuous) != len(dates) * SELECTED_BAR_COUNT:
        raise Campaign087FeatureError(f"continuous minute grid changed for {symbol}")
    arrays = {
        name: continuous[name]
        .to_numpy(dtype=np.float64)
        .reshape(len(dates), SELECTED_BAR_COUNT)
        for name in ("high", "low", "amount")
    }
    values, eligible, total_range, total_amount = compute_profile_alignment(
        arrays["high"], arrays["low"], arrays["amount"]
    )
    source_valid = (
        np.isfinite(arrays["high"]).all(axis=1)
        & np.isfinite(arrays["low"]).all(axis=1)
        & np.isfinite(arrays["amount"]).all(axis=1)
        & (arrays["high"] > 0.0).all(axis=1)
        & (arrays["low"] > 0.0).all(axis=1)
        & (arrays["low"] <= arrays["high"]).all(axis=1)
        & (arrays["amount"] >= 0.0).all(axis=1)
    )
    return pd.DataFrame({"trade_date": dates, FACTOR_NAME: values}), {
        "source_rows": len(work),
        "source_sessions": len(dates),
        "valid_serial_persistence_sessions": int(eligible.sum()),
        "invalid_selected_source_sessions": int((~source_valid).sum()),
        "insufficient_pair_sessions": int(
            (source_valid & (~np.isfinite(total_range) | (total_range <= 0.0))).sum()
        ),
        "zero_range_selected_bars": int(
            ((arrays["high"] == arrays["low"]) & source_valid[:, None]).sum()
        ),
        "retained_informative_pairs": int(
            (source_valid & (~np.isfinite(total_amount) | (total_amount <= 0.0))).sum()
        ),
    }


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/minute_walkforward_campaign087_feature_library"
        / OUTPUT_RUN_ID
    )


def _load_implementation_freeze() -> dict[str, Any]:
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign087FeatureError("Campaign087 implementation freeze is absent")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign087_feature_implementation_freeze"
        and record.get("status")
        == "frozen_before_campaign087_minute_source_rows_or_candidate_values"
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (record.get("feature_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("candidate_source_rows_read_before_freeze") is False
        and record.get("candidate_values_computed_before_freeze") is False
        and record.get("comparison_values_read_before_freeze") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and record.get("provider_request_issued_before_freeze") is False
    ):
        raise Campaign087FeatureError("Campaign087 implementation freeze changed")
    return record


@contextlib.contextmanager
def _patched_campaign086_builder() -> Iterator[None]:
    replacements = {
        "__file__": str(Path(__file__).resolve()),
        "DEFAULT_PROTOCOL": DEFAULT_PROTOCOL,
        "DEFAULT_IMPLEMENTATION_FREEZE": DEFAULT_IMPLEMENTATION_FREEZE,
        "FACTOR_NAME": FACTOR_NAME,
        "FACTOR_FORMULA": FACTOR_FORMULA,
        "OUTPUT_RUN_ID": OUTPUT_RUN_ID,
        "RAW_COLUMNS": RAW_COLUMNS,
        "OUTPUT_COLUMNS": OUTPUT_COLUMNS,
        "load_protocol": load_protocol,
        "_load_implementation_freeze": _load_implementation_freeze,
        "extract_serial_persistence": extract_profile_alignment,
        "compact_stock_day_keys": c86_v4.compact_stock_day_keys,
        "output_root": output_root,
    }
    original = {name: getattr(c86, name) for name in replacements}
    try:
        for name, value in replacements.items():
            setattr(c86, name, value)
        yield
    finally:
        for name, value in original.items():
            setattr(c86, name, value)


def _dataset_material(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocol_sha256": manifest["protocol"]["sha256"],
        "implementation_freeze_sha256": manifest["implementation_freeze"]["sha256"],
        "raw_manifest_sha256": manifest["source"]["raw_manifest_sha256"],
        "joint_clean_manifest_sha256": manifest["source"]["joint_clean_manifest_sha256"],
        "eligible_keys_sha256": manifest["eligible_universe"]["keys_sha256"],
        "factor_name": FACTOR_NAME,
        "factor_formula": FACTOR_FORMULA,
        "factor_eligible_rows": manifest["factor_eligible_rows"][FACTOR_NAME],
        "files": manifest["files"],
    }


def build_snapshot(
    *, data_root: Path, workers: int = 8, confirm_build: bool = False
) -> Path:
    if not confirm_build:
        raise Campaign087FeatureError("Campaign087 build requires --confirm-build")
    _load_implementation_freeze()
    if output_root(data_root.expanduser().resolve()).exists():
        raise Campaign087FeatureError("Campaign087 output already exists")
    with _patched_campaign086_builder():
        manifest_path = c86.build_snapshot(
            data_root=data_root,
            workers=workers,
            confirm_build=True,
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    old_quality = manifest.get("quality") or {}
    manifest["kind"] = "a_share_three_day_walkforward_campaign087_feature_snapshot"
    manifest["feature_runner"] = {
        "path": str(Path(__file__).resolve()),
        "sha256": _sha256(Path(__file__).resolve()),
    }
    manifest["quality"] = {
        "source_rows": int(old_quality.get("source_rows", 0)),
        "source_sessions": int(old_quality.get("source_sessions", 0)),
        "valid_profile_alignment_sessions": int(
            old_quality.get("valid_serial_persistence_sessions", 0)
        ),
        "invalid_selected_source_sessions": int(
            old_quality.get("invalid_selected_source_sessions", 0)
        ),
        "nonpositive_total_range_sessions": int(
            old_quality.get("insufficient_pair_sessions", 0)
        ),
        "zero_range_selected_bars": int(
            old_quality.get("zero_range_selected_bars", 0)
        ),
        "nonpositive_total_amount_sessions": int(
            old_quality.get("retained_informative_pairs", 0)
        ),
    }
    manifest["dataset_sha256"] = _json_digest(_dataset_material(manifest))
    c85._atomic_json(manifest, manifest_path)
    return manifest_path


def verify_snapshot_files(manifest_path: Path) -> dict[str, Any]:
    _load_implementation_freeze()
    path = manifest_path.expanduser().resolve()
    expected = output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
    if path != expected.resolve() or not path.is_file():
        raise Campaign087FeatureError("Campaign087 manifest path changed")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign087_feature_snapshot"
        and manifest.get("status") == "complete_no_return_candidate_snapshot"
        and (manifest.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (manifest.get("implementation_freeze") or {}).get("sha256")
        == _sha256(DEFAULT_IMPLEMENTATION_FREEZE)
        and (manifest.get("feature_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == {FACTOR_NAME: "higher"}
        and manifest.get("factor_ranges") == {FACTOR_NAME: [0.0, 1.0]}
        and manifest.get("rows") == EXPECTED_ROWS
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and manifest.get("calendar_sessions") == EXPECTED_SESSIONS
        and manifest.get("comparison_values_read") is False
        and manifest.get("historical_daily_price_fields_read") == []
        and manifest.get("historical_forward_returns_read") is False
        and manifest.get("provider_request_issued") is False
        and manifest.get("dataset_sha256") == _json_digest(_dataset_material(manifest))
    ):
        raise Campaign087FeatureError("Campaign087 manifest semantics changed")
    rows = 0
    eligible_count = 0
    all_keys: list[np.ndarray] = []
    for record in manifest.get("files") or []:
        partition = path.parent / str(record["path"])
        if _sha256(partition) != record.get("sha256"):
            raise Campaign087FeatureError("Campaign087 partition bytes changed")
        frame = pd.read_parquet(partition, columns=list(OUTPUT_COLUMNS))
        if c85._frame_sha256(frame) != record.get("frame_sha256"):
            raise Campaign087FeatureError("Campaign087 partition frame changed")
        values = frame[FACTOR_NAME].to_numpy(dtype=np.float64)
        flags = frame[f"{FACTOR_NAME}_eligible"].astype(bool).to_numpy()
        finite = np.isfinite(values)
        if not (
            np.array_equal(flags, finite)
            and ((values[finite] >= 0.0) & (values[finite] <= 1.0)).all()
            and int(flags.sum()) == int(record["eligible_rows"])
            and cache_v1.canonical_column_sha256(values)
            == record.get("factor_canonical_value_sha256")
        ):
            raise Campaign087FeatureError("Campaign087 values changed")
        rows += len(frame)
        eligible_count += int(flags.sum())
        all_keys.append(frame["stock_day_key"].to_numpy(dtype=np.int64))
    keys = np.concatenate(all_keys)
    key_sha = hashlib.sha256(keys.astype("<i8", copy=False).tobytes()).hexdigest()
    if not (
        rows == EXPECTED_ROWS
        and eligible_count == (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
        and len(np.unique(keys)) == EXPECTED_ROWS
        and np.all(keys[1:] > keys[:-1])
        and key_sha == (manifest.get("eligible_universe") or {}).get("keys_sha256")
    ):
        raise Campaign087FeatureError("Campaign087 aggregate identity changed")
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
    path = output_root(data_root.expanduser().resolve()) / "snapshot_manifest.json"
    return {
        "status": "snapshot_present" if path.is_file() else "snapshot_absent_prebuild",
        "manifest_path": str(path),
        "comparison_values_read_by_status": False,
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
