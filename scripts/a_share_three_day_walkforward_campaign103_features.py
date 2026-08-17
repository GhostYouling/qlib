#!/usr/bin/env python3
"""Build and no-return-audit Campaign103's temporal 130-factor breadth.

The only input is Campaign102's immutable directional-rank matrix.  This
module never loads a price, forward return, training target, or Candidate49
state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from scripts import a_share_three_day_walkforward_campaign102_design as c102

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_103_no_return_preregistration.json"
)
DEFAULT_SOURCE_CATALOG = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_103_source_catalog.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_103_feature_implementation_freeze_v2_20260807.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign103_features.py"
)
C102_MANIFEST_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign102_design_matrix/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign102_design_matrix_v1/snapshot_manifest.json"
)

PROTOCOL_SHA256 = "ea7aae7dcae02629cb00e39e6bff903b7ce2afe14aeb1e29b3b612d381297245"
SOURCE_CATALOG_SHA256 = "6cfa9e7a1a050037fac15a6822a06fc2fab3ac4b6959a41433f81213b6532a76"
C102_MANIFEST_SHA256 = "fc9ab498462439731785a0eabbde370c1fd883c8d771eba312c85aa912d3cebe"
C102_DATASET_SHA256 = "cceec2b790d134a89914e83e0697c1e6abff605a85fd85be74de68067faddb92"
NUMERIC_POLICY_SHA256 = "4e6c7aea0be521773cda56ceea33d1665a82e9254b1e9198fa13b65e22d826b0"
NUMERIC_COUNT = 130
NUMERIC_ORDER_SHA256 = "c80d9b929536dd509d6c1a904f790831050e68200393de381f92ad9293ef69e7"
EXPECTED_ROWS = 1_331_759
EXPECTED_SESSIONS = 1_632
EXPECTED_PARTITIONS = 7
EXPECTED_YEARS = tuple(range(2019, 2026))
MINIMUM_COMPONENTS_EACH_SESSION = 98
MINIMUM_PAIRED_COMPONENTS = 66
MINIMUM_PAIRWISE_NAMES = 50
MINIMUM_PAIRWISE_SESSIONS = 100
MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION = 0.8
FACTOR_NAME = "full_numeric_library_directional_rank_improvement_breadth_130f"
PAIRED_COUNT_NAME = f"{FACTOR_NAME}_paired_component_count"
ELIGIBLE_NAME = f"{FACTOR_NAME}_eligible"
OUTPUT_COLUMNS = ("stock_day_key", FACTOR_NAME, PAIRED_COUNT_NAME, ELIGIBLE_NAME)
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign103_feature_library_v1"
)


class Campaign103FeatureError(RuntimeError):
    """Fail closed when a frozen Campaign103 invariant changes."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    resolved = path.expanduser().resolve()
    if not resolved.is_file() or _sha256(resolved) != expected:
        raise Campaign103FeatureError(f"{label} changed: {resolved}")


def _record_path(manifest_path: Path, record: dict[str, Any]) -> Path:
    raw = Path(str(record["path"]))
    return raw.resolve() if raw.is_absolute() else (manifest_path.parent / raw).resolve()


def load_frozen_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    _require(DEFAULT_PROTOCOL, PROTOCOL_SHA256, "Campaign103 protocol")
    _require(DEFAULT_SOURCE_CATALOG, SOURCE_CATALOG_SHA256, "Campaign103 catalog")
    _require(C102_MANIFEST_PATH, C102_MANIFEST_SHA256, "Campaign102 design manifest")
    protocol = json.loads(DEFAULT_PROTOCOL.read_text(encoding="utf-8"))
    catalog = json.loads(DEFAULT_SOURCE_CATALOG.read_text(encoding="utf-8"))
    manifest = json.loads(C102_MANIFEST_PATH.read_text(encoding="utf-8"))
    candidate = protocol.get("candidate") or {}
    source = catalog.get("source") or {}
    source_manifest = source.get("manifest") or {}
    receipts = list(catalog.get("partition_receipts") or [])
    observed_receipts = [
        {
            "year": int(item["year"]),
            "rows": int(item["rows"]),
            "sha256": str(item["sha256"]),
        }
        for item in manifest.get("files") or []
    ]
    if not (
        protocol.get("status")
        == "frozen_before_campaign103_candidate_paired_support_comparison_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("source_factor_count") == NUMERIC_COUNT
        and candidate.get("source_factor_order_sha256") == NUMERIC_ORDER_SHA256
        and candidate.get("minimum_paired_components") == MINIMUM_PAIRED_COMPONENTS
        and source_manifest.get("sha256") == C102_MANIFEST_SHA256
        and source_manifest.get("dataset_sha256") == C102_DATASET_SHA256
        and source.get("component_count") == NUMERIC_COUNT
        and source.get("component_order_sha256") == NUMERIC_ORDER_SHA256
        and receipts == observed_receipts
        and manifest.get("dataset_sha256") == C102_DATASET_SHA256
        and manifest.get("component_count") == NUMERIC_COUNT
        and manifest.get("component_order_sha256") == NUMERIC_ORDER_SHA256
        and manifest.get("minimum_finite_components")
        == MINIMUM_COMPONENTS_EACH_SESSION
        and manifest.get("rows") == EXPECTED_ROWS
        and manifest.get("calendar_sessions") == EXPECTED_SESSIONS
        and len(manifest.get("files") or []) == EXPECTED_PARTITIONS
        and tuple(int(item["year"]) for item in manifest["files"])
        == EXPECTED_YEARS
    ):
        raise Campaign103FeatureError("Campaign103 frozen input semantics changed")
    return protocol, catalog, manifest


def _load_implementation_freeze() -> dict[str, Any]:
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign103FeatureError("Campaign103 implementation freeze is absent")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign103_feature_implementation_freeze"
        and record.get("status") == "frozen_before_campaign103_values"
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (record.get("source_catalog") or {}).get("sha256")
        == SOURCE_CATALOG_SHA256
        and (record.get("source_manifest") or {}).get("sha256")
        == C102_MANIFEST_SHA256
        and (record.get("feature_builder") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("synthetic_tests") or {}).get("sha256")
        == _sha256(TEST_PATH)
        and boundary.get("campaign103_candidate_or_paired_support_values_read_before_freeze")
        is False
        and boundary.get("campaign103_comparison_values_read_before_freeze") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read_before_freeze")
        is False
        and boundary.get("provider_request_issued_before_freeze") is False
        and boundary.get("candidate49_ledgers_changed_before_freeze") is False
    ):
        raise Campaign103FeatureError("Campaign103 implementation freeze changed")
    return record


def improvement_breadth(
    current: np.ndarray,
    prior: np.ndarray,
    current_support: np.ndarray,
    prior_support: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return the exact equal-vote temporal breadth and frozen support state."""

    now = np.asarray(current, dtype=np.float32)
    before = np.asarray(prior, dtype=np.float32)
    current_ok = np.asarray(current_support, dtype=bool)
    prior_ok = np.asarray(prior_support, dtype=bool)
    if (
        now.ndim != 2
        or now.shape != before.shape
        or now.shape[1] != NUMERIC_COUNT
        or current_ok.shape != (len(now),)
        or prior_ok.shape != (len(now),)
    ):
        raise Campaign103FeatureError("Campaign103 breadth input shape changed")
    for values in (now, before):
        finite = np.isfinite(values)
        if np.any((values[finite] <= 0.0) | (values[finite] > 1.0)):
            raise Campaign103FeatureError("directional component escaped (0,1]")
    paired = np.isfinite(now) & np.isfinite(before)
    paired_count = paired.sum(axis=1).astype(np.uint8)
    eligible = (
        current_ok
        & prior_ok
        & (paired_count >= np.uint8(MINIMUM_PAIRED_COMPONENTS))
    )
    votes = np.where(now > before, 1.0, np.where(now == before, 0.5, 0.0))
    numerator = np.where(paired, votes, 0.0).sum(axis=1, dtype=np.float64)
    result = np.full(len(now), np.nan, dtype=np.float64)
    result[eligible] = numerator[eligible] / paired_count[eligible]
    if np.any(~np.isfinite(result[eligible])) or np.any(
        (result[eligible] < 0.0) | (result[eligible] > 1.0)
    ):
        raise Campaign103FeatureError("Campaign103 breadth escaped [0,1]")
    return result, paired_count, eligible


def _canonical_partition_sha256(
    keys: np.ndarray,
    values: np.ndarray,
    paired_count: np.ndarray,
    eligible: np.ndarray,
) -> str:
    digest = hashlib.sha256()
    digest.update(np.asarray(keys, dtype="<i8").tobytes())
    canonical = np.asarray(values, dtype="<f4").copy()
    canonical[~np.isfinite(canonical)] = np.float32(np.nan)
    digest.update(canonical.tobytes())
    digest.update(np.asarray(paired_count, dtype=np.uint8).tobytes())
    digest.update(np.asarray(eligible, dtype=np.uint8).tobytes())
    return digest.hexdigest()


def _write_partition(
    path: Path,
    keys: np.ndarray,
    values: np.ndarray,
    paired_count: np.ndarray,
    eligible: np.ndarray,
) -> None:
    table = pa.Table.from_pydict(
        {
            "stock_day_key": pa.array(keys, type=pa.int64()),
            FACTOR_NAME: pa.array(values, type=pa.float32(), from_pandas=True),
            PAIRED_COUNT_NAME: pa.array(paired_count, type=pa.uint8()),
            ELIGIBLE_NAME: pa.array(eligible, type=pa.bool_()),
        }
    )
    pq.write_table(
        table,
        path,
        compression="zstd",
        compression_level=6,
        use_dictionary=False,
        write_statistics=True,
        row_group_size=65_536,
        data_page_version="2.0",
    )


def output_root(data_root: Path) -> Path:
    return (
        data_root.expanduser().resolve()
        / "derived/a_share/rich/tushare/minute_walkforward_campaign103_feature_library"
        / OUTPUT_RUN_ID
    )


def _calendar_sessions(source_manifest: dict[str, Any]) -> np.ndarray:
    seen: set[int] = set()
    for record in source_manifest["files"]:
        path = _record_path(C102_MANIFEST_PATH, record)
        _require(path, str(record["sha256"]), f"Campaign102 {record['year']} partition")
        keys = pd.read_parquet(path, columns=["stock_day_key"])[
            "stock_day_key"
        ].to_numpy(dtype=np.int64)
        seen.update((keys // 4_000_000).tolist())
    result = np.asarray(sorted(seen), dtype=np.int64)
    if len(result) != EXPECTED_SESSIONS or np.any(result[1:] <= result[:-1]):
        raise Campaign103FeatureError("Campaign103 accepted calendar changed")
    return result


def _candidate_year(
    *,
    keys: np.ndarray,
    matrix: np.ndarray,
    source_support: np.ndarray,
    calendar: np.ndarray,
    prior_state: tuple[int, np.ndarray, np.ndarray, np.ndarray] | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, tuple[int, np.ndarray, np.ndarray, np.ndarray]]:
    sessions = keys // 4_000_000
    boundaries = np.flatnonzero(np.r_[True, sessions[1:] != sessions[:-1], True])
    values = np.full(len(keys), np.nan, dtype=np.float64)
    paired_count = np.zeros(len(keys), dtype=np.uint8)
    eligible = np.zeros(len(keys), dtype=bool)
    calendar_position = {int(value): index for index, value in enumerate(calendar)}
    state = prior_state
    for start, stop in zip(boundaries[:-1], boundaries[1:], strict=True):
        session = int(sessions[start])
        position = calendar_position.get(session)
        if position is None:
            raise Campaign103FeatureError("Campaign103 session absent from calendar")
        current_codes = keys[start:stop] % 4_000_000
        current_matrix = matrix[start:stop]
        current_support = source_support[start:stop]
        prior_matrix = np.full(current_matrix.shape, np.nan, dtype=np.float32)
        prior_support = np.zeros(stop - start, dtype=bool)
        if position > 0:
            expected_prior = int(calendar[position - 1])
            if state is None or int(state[0]) != expected_prior:
                raise Campaign103FeatureError("Campaign103 exact-prior session state changed")
            _, prior_codes, prior_values, prior_flags = state
            locations = np.searchsorted(prior_codes, current_codes)
            matched = locations < len(prior_codes)
            if matched.any():
                matched_indices = np.flatnonzero(matched)
                matched[matched_indices] = (
                    prior_codes[locations[matched_indices]]
                    == current_codes[matched_indices]
                )
            if matched.any():
                prior_matrix[matched] = prior_values[locations[matched]]
                prior_support[matched] = prior_flags[locations[matched]]
        local_values, local_count, local_eligible = improvement_breadth(
            current_matrix,
            prior_matrix,
            current_support,
            prior_support,
        )
        values[start:stop] = local_values
        paired_count[start:stop] = local_count
        eligible[start:stop] = local_eligible
        order = np.argsort(current_codes, kind="stable")
        state = (
            session,
            current_codes[order].copy(),
            current_matrix[order].copy(),
            current_support[order].copy(),
        )
    if state is None:
        raise Campaign103FeatureError("Campaign103 year contained no session")
    return values, paired_count, eligible, state


def build_snapshot(*, data_root: Path) -> Path:
    freeze = _load_implementation_freeze()
    _, _, source_manifest = load_frozen_inputs()
    if data_root.expanduser().resolve() != DEFAULT_DATA_ROOT.resolve():
        raise Campaign103FeatureError("Campaign103 data root changed")
    c102.verify_snapshot(C102_MANIFEST_PATH)
    calendar = _calendar_sessions(source_manifest)
    final_root = output_root(data_root)
    if final_root.exists():
        raise Campaign103FeatureError("Campaign103 feature output already exists")
    if shutil.disk_usage(data_root).free < 2 * 1024**3:
        raise Campaign103FeatureError("data root has less than 2 GiB free")
    final_root.parent.mkdir(parents=True, exist_ok=True)
    partial_root = Path(tempfile.mkdtemp(prefix=f".{OUTPUT_RUN_ID}.", dir=final_root.parent))
    partition_root = partial_root / "partitions"
    partition_root.mkdir()
    records: list[dict[str, Any]] = []
    total_rows = total_eligible = 0
    state: tuple[int, np.ndarray, np.ndarray, np.ndarray] | None = None
    try:
        for record in source_manifest["files"]:
            year = int(record["year"])
            print(f"building Campaign103 year={year}", flush=True)
            keys, matrix, finite_count, source_support = c102._read_partition(
                C102_MANIFEST_PATH, record
            )
            if not np.array_equal(source_support, finite_count >= 98):
                raise Campaign103FeatureError("Campaign102 support flag changed")
            values, paired_count, eligible, state = _candidate_year(
                keys=keys,
                matrix=matrix,
                source_support=source_support,
                calendar=calendar,
                prior_state=state,
            )
            path = partition_root / f"{year}.parquet"
            _write_partition(path, keys, values, paired_count, eligible)
            eligible_rows = int(eligible.sum())
            records.append(
                {
                    "year": year,
                    "path": f"partitions/{year}.parquet",
                    "rows": len(keys),
                    "eligible_rows": eligible_rows,
                    "sha256": _sha256(path),
                    "candidate_matrix_sha256": _canonical_partition_sha256(
                        keys, values, paired_count, eligible
                    ),
                    "minimum_paired_components_observed": int(paired_count.min()),
                    "maximum_paired_components_observed": int(paired_count.max()),
                    "source_partition_sha256": str(record["sha256"]),
                }
            )
            total_rows += len(keys)
            total_eligible += eligible_rows
        if total_rows != EXPECTED_ROWS or len(records) != EXPECTED_PARTITIONS:
            raise Campaign103FeatureError("Campaign103 aggregate identity changed")
        manifest = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign103_feature_snapshot",
            "status": "immutable_candidate_ready_for_coverage_first_no_return_audit",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "output_run_id": OUTPUT_RUN_ID,
            "protocol": {"path": str(DEFAULT_PROTOCOL), "sha256": PROTOCOL_SHA256},
            "source_catalog": {
                "path": str(DEFAULT_SOURCE_CATALOG),
                "sha256": SOURCE_CATALOG_SHA256,
            },
            "source_manifest": {
                "path": str(C102_MANIFEST_PATH),
                "sha256": C102_MANIFEST_SHA256,
                "dataset_sha256": C102_DATASET_SHA256,
            },
            "implementation_freeze": {
                "path": str(DEFAULT_IMPLEMENTATION_FREEZE),
                "sha256": _sha256(DEFAULT_IMPLEMENTATION_FREEZE),
                "feature_builder_sha256": freeze["feature_builder"]["sha256"],
                "synthetic_tests_sha256": freeze["synthetic_tests"]["sha256"],
            },
            "factor": FACTOR_NAME,
            "direction": "higher",
            "component_count": NUMERIC_COUNT,
            "component_order_sha256": NUMERIC_ORDER_SHA256,
            "minimum_components_each_session": MINIMUM_COMPONENTS_EACH_SESSION,
            "minimum_paired_components": MINIMUM_PAIRED_COMPONENTS,
            "prior_session_rule": "exact_previous_accepted_calendar_session_no_bridge",
            "tie_vote": 0.5,
            "files": records,
            "partitions": len(records),
            "rows": total_rows,
            "eligible_rows": total_eligible,
            "calendar_sessions": len(calendar),
            "dataset_sha256": _json_sha256(records),
            "campaign103_candidate_and_paired_support_values_read": True,
            "campaign103_comparison_values_read": False,
            "historical_daily_price_fields_read": [],
            "historical_forward_return_fields_read": False,
            "training_or_model_fitting_performed": False,
            "provider_request_issued": False,
            "candidate49_historical_backfill_performed": False,
            "candidate49_ledgers_changed": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
        }
        manifest_path = partial_root / "snapshot_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(partial_root, final_root)
        return final_root / "snapshot_manifest.json"
    except BaseException:
        shutil.rmtree(partial_root, ignore_errors=True)
        raise


def _read_candidate_partition(
    manifest_path: Path, record: dict[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    path = _record_path(manifest_path, record)
    _require(path, str(record["sha256"]), f"Campaign103 {record['year']} partition")
    frame = pd.read_parquet(path, columns=list(OUTPUT_COLUMNS))
    return (
        frame["stock_day_key"].to_numpy(dtype=np.int64),
        frame[FACTOR_NAME].to_numpy(dtype=np.float64),
        frame[PAIRED_COUNT_NAME].to_numpy(dtype=np.uint8),
        frame[ELIGIBLE_NAME].to_numpy(dtype=bool),
    )


def verify_snapshot(manifest_path: Path) -> dict[str, Any]:
    _load_implementation_freeze()
    _, _, source_manifest = load_frozen_inputs()
    c102.verify_snapshot(C102_MANIFEST_PATH)
    manifest_path = manifest_path.expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = list(manifest.get("files") or [])
    rows = eligible_rows = 0
    sessions: set[int] = set()
    for output_record, source_record in zip(
        records, source_manifest["files"], strict=True
    ):
        keys, values, paired_count, eligible = _read_candidate_partition(
            manifest_path, output_record
        )
        source_path = _record_path(C102_MANIFEST_PATH, source_record)
        source_keys = pd.read_parquet(source_path, columns=["stock_day_key"])[
            "stock_day_key"
        ].to_numpy(dtype=np.int64)
        if not (
            np.array_equal(keys, source_keys)
            and np.array_equal(np.isfinite(values), eligible)
            and np.all(paired_count[eligible] >= MINIMUM_PAIRED_COMPONENTS)
            and np.all((values[eligible] >= 0.0) & (values[eligible] <= 1.0))
            and _canonical_partition_sha256(keys, values, paired_count, eligible)
            == output_record["candidate_matrix_sha256"]
            and output_record["source_partition_sha256"] == source_record["sha256"]
        ):
            raise Campaign103FeatureError(
                f"Campaign103 partition semantics changed: {output_record.get('year')}"
            )
        rows += len(keys)
        eligible_rows += int(eligible.sum())
        sessions.update((keys // 4_000_000).tolist())
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign103_feature_snapshot"
        and manifest.get("factor") == FACTOR_NAME
        and manifest.get("component_count") == NUMERIC_COUNT
        and manifest.get("component_order_sha256") == NUMERIC_ORDER_SHA256
        and manifest.get("minimum_paired_components") == MINIMUM_PAIRED_COMPONENTS
        and len(records) == manifest.get("partitions") == EXPECTED_PARTITIONS
        and rows == manifest.get("rows") == EXPECTED_ROWS
        and eligible_rows == manifest.get("eligible_rows")
        and len(sessions) == manifest.get("calendar_sessions") == EXPECTED_SESSIONS
        and manifest.get("dataset_sha256") == _json_sha256(records)
        and manifest.get("campaign103_comparison_values_read") is False
        and manifest.get("historical_forward_return_fields_read") is False
        and manifest.get("training_or_model_fitting_performed") is False
        and manifest.get("provider_request_issued") is False
        and manifest.get("candidate49_ledgers_changed") is False
    ):
        raise Campaign103FeatureError("Campaign103 snapshot verification changed")
    return {
        "status": "verified",
        "manifest_sha256": _sha256(manifest_path),
        "dataset_sha256": manifest["dataset_sha256"],
        "partitions": len(records),
        "rows": rows,
        "eligible_rows": eligible_rows,
        "calendar_sessions": len(sessions),
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def coverage_and_capacity(
    keys: np.ndarray, values: np.ndarray
) -> dict[str, Any]:
    sessions = keys // 4_000_000
    frame = pd.DataFrame(
        {"session": sessions, "eligible": np.isfinite(values)}
    )
    daily = frame.groupby("session", sort=True, observed=True)["eligible"].agg(
        ["size", "sum"]
    )
    ratios = daily["sum"] / daily["size"]
    indices = np.arange(0, max(len(daily) - 3, 0), 3)
    potential_mask = daily.iloc[indices]["sum"].ge(MINIMUM_PAIRWISE_NAMES)
    potential = int(potential_mask.sum())
    cohort_sessions = daily.iloc[indices].loc[potential_mask].index.to_numpy(
        dtype=np.int64
    )
    cohort_years = sorted(
        pd.to_datetime(cohort_sessions, unit="D", origin="unix").year.unique().tolist()
    )
    median = float(ratios.median())
    p05 = float(ratios.quantile(0.05))
    p05_names = float(daily["sum"].quantile(0.05))
    passed = bool(
        median >= 0.95
        and p05 >= 0.90
        and p05_names >= MINIMUM_PAIRWISE_NAMES
        and potential >= 200
        and len(cohort_years) >= 5
    )
    return {
        "quality_listing_rows": int(len(keys)),
        "candidate_eligible_rows": int(np.isfinite(values).sum()),
        "calendar_sessions": int(len(daily)),
        "median_coverage": median,
        "p05_coverage": p05,
        "eligible_names_minimum": int(daily["sum"].min()),
        "eligible_names_p05": p05_names,
        "eligible_names_median": float(daily["sum"].median()),
        "potential_non_overlapping_three_session_cohorts": potential,
        "observed_cohort_years": [int(value) for value in cohort_years],
        "gate_passed_before_comparison_values": passed,
    }


def _daily_frame_sha256(rows: list[dict[str, Any]]) -> str | None:
    if not rows:
        return None
    payload = "".join(
        f"{item['session']},{item['pairwise_names']},{item['rank_correlation']:.17g}\n"
        for item in rows
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _comparison_result(
    *, name: str, source_direction: str, rows: list[dict[str, Any]]
) -> dict[str, Any]:
    correlations = np.asarray(
        [item["rank_correlation"] for item in rows], dtype=np.float64
    )
    median = float(np.median(correlations)) if len(correlations) else math.nan
    passed = bool(
        len(correlations) >= MINIMUM_PAIRWISE_SESSIONS
        and math.isfinite(median)
        and abs(median) < MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION
    )
    return {
        "comparison_factor": name,
        "source_score_direction": source_direction,
        "stored_directional_score_comparison_direction": "higher",
        "pairwise_sessions": int(len(correlations)),
        "minimum_pairwise_names_observed": (
            min(int(item["pairwise_names"]) for item in rows) if rows else 0
        ),
        "median_daily_rank_correlation": median if math.isfinite(median) else None,
        "absolute_median_daily_rank_correlation": (
            abs(median) if math.isfinite(median) else None
        ),
        "daily_rank_correlation_p05": (
            float(np.quantile(correlations, 0.05)) if len(correlations) else None
        ),
        "daily_rank_correlation_p95": (
            float(np.quantile(correlations, 0.95)) if len(correlations) else None
        ),
        "daily_correlation_frame_sha256": _daily_frame_sha256(rows),
        "gate_passed": passed,
    }


def uniqueness_after_coverage(
    *, candidate_manifest_path: Path, coverage: dict[str, Any]
) -> list[dict[str, Any]]:
    if coverage.get("gate_passed_before_comparison_values") is not True:
        raise Campaign103FeatureError("comparisons requested before coverage pass")
    _, _, source_manifest = load_frozen_inputs()
    candidate_manifest = json.loads(
        candidate_manifest_path.read_text(encoding="utf-8")
    )
    definitions = list(source_manifest["components"])
    daily_rows: list[list[dict[str, Any]]] = [[] for _ in range(NUMERIC_COUNT)]
    for output_record, source_record in zip(
        candidate_manifest["files"], source_manifest["files"], strict=True
    ):
        print(f"auditing Campaign103 uniqueness year={source_record['year']}", flush=True)
        keys, candidate_values, _, candidate_eligible = _read_candidate_partition(
            candidate_manifest_path, output_record
        )
        source_keys, matrix, _, _ = c102._read_partition(
            C102_MANIFEST_PATH, source_record
        )
        if not np.array_equal(keys, source_keys):
            raise Campaign103FeatureError("Campaign103 comparison identity changed")
        sessions = keys // 4_000_000
        boundaries = np.flatnonzero(np.r_[True, sessions[1:] != sessions[:-1], True])
        for start, stop in zip(boundaries[:-1], boundaries[1:], strict=True):
            session = int(sessions[start])
            candidate = candidate_values[start:stop]
            current_matrix = matrix[start:stop]
            base_eligible = candidate_eligible[start:stop]
            for index in range(NUMERIC_COUNT):
                comparison = current_matrix[:, index].astype(np.float64, copy=False)
                finite = base_eligible & np.isfinite(comparison)
                names = int(finite.sum())
                if names < MINIMUM_PAIRWISE_NAMES:
                    continue
                left = candidate[finite]
                right = comparison[finite]
                if np.unique(left).size < 2 or np.unique(right).size < 2:
                    continue
                left_rank = pd.Series(left).rank(method="average", pct=True)
                right_rank = pd.Series(right).rank(method="average", pct=True)
                correlation = left_rank.corr(right_rank, method="pearson")
                if math.isfinite(float(correlation)):
                    daily_rows[index].append(
                        {
                            "session": session,
                            "pairwise_names": names,
                            "rank_correlation": float(correlation),
                        }
                    )
    results = [
        _comparison_result(
            name=str(definition["name"]),
            source_direction=str(definition["score_direction"]),
            rows=daily_rows[index],
        )
        for index, definition in enumerate(definitions)
    ]
    if [item["comparison_factor"] for item in results] != [
        item["name"] for item in definitions
    ]:
        raise Campaign103FeatureError("Campaign103 comparison order changed")
    return results


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def no_return_audit(*, manifest_path: Path, output: Path) -> Path:
    verification = verify_snapshot(manifest_path)
    manifest_path = manifest_path.expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    keys_parts: list[np.ndarray] = []
    value_parts: list[np.ndarray] = []
    for record in manifest["files"]:
        keys, values, _, _ = _read_candidate_partition(manifest_path, record)
        keys_parts.append(keys)
        value_parts.append(values)
    keys = np.concatenate(keys_parts)
    values = np.concatenate(value_parts)
    coverage = coverage_and_capacity(keys, values)
    comparisons: list[dict[str, Any]] = []
    if coverage["gate_passed_before_comparison_values"]:
        comparisons = uniqueness_after_coverage(
            candidate_manifest_path=manifest_path, coverage=coverage
        )
    all_passed = bool(comparisons) and len(comparisons) == NUMERIC_COUNT and all(
        item["gate_passed"] is True for item in comparisons
    )
    maximum = max(
        (
            float(item["absolute_median_daily_rank_correlation"])
            for item in comparisons
            if item["absolute_median_daily_rank_correlation"] is not None
        ),
        default=None,
    )
    admissible = bool(
        coverage["gate_passed_before_comparison_values"] and all_passed
    )
    payload = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign103_no_return_audit",
        "status": (
            "completed_one_admissible_factor_ready_for_frozen_development_trial"
            if admissible
            else "completed_zero_admissible_factors_stop_before_historical_daily_prices_or_returns"
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "protocol": {"path": str(DEFAULT_PROTOCOL), "sha256": PROTOCOL_SHA256},
        "candidate_snapshot": {
            "path": str(manifest_path),
            "sha256": _sha256(manifest_path),
            "dataset_sha256": manifest["dataset_sha256"],
        },
        "snapshot_verification": verification,
        "coverage_and_capacity": coverage,
        "uniqueness": {
            "comparison_values_loaded_after_coverage_pass": bool(comparisons),
            "comparison_factor_count": len(comparisons),
            "comparison_order_sha256": NUMERIC_ORDER_SHA256,
            "all_130_required_numeric_comparisons_passed": all_passed,
            "maximum_observed_absolute_median_daily_rank_correlation": maximum,
            "comparisons": comparisons,
        },
        "admissible_factor_count": 1 if admissible else 0,
        "admissible_factor_names": [FACTOR_NAME] if admissible else [],
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "training_or_model_fitting_performed": False,
        "provider_request_issued": False,
        "candidate49_historical_backfill_performed": False,
        "candidate49_ledgers_changed": False,
        "second_prospective_candidate_created": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
        "investment_advice": False,
        "next_action": (
            "freeze and run the sole 2019-2023 Campaign103 development trial"
            if admissible
            else "record terminal no-return rejection and begin only a genuinely new offline campaign"
        ),
    }
    _atomic_json(output.expanduser().resolve(), payload)
    return output.expanduser().resolve()


def status(*, data_root: Path) -> dict[str, Any]:
    root = output_root(data_root)
    return {
        "output_root": str(root),
        "published": (root / "snapshot_manifest.json").is_file(),
        "implementation_freeze_exists": DEFAULT_IMPLEMENTATION_FREEZE.is_file(),
        "campaign103_candidate_or_paired_support_values_read_by_status": False,
        "campaign103_comparison_values_read_by_status": False,
        "historical_daily_price_or_forward_return_values_read_by_status": False,
        "provider_request_issued_by_status": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("status", "build", "verify", "audit"))
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "status":
        payload: Any = status(data_root=args.data_root)
    elif args.command == "build":
        payload = {"manifest": str(build_snapshot(data_root=args.data_root))}
    elif args.command == "verify":
        if args.manifest is None:
            raise Campaign103FeatureError("--manifest is required")
        payload = verify_snapshot(args.manifest)
    else:
        if args.manifest is None or args.output is None:
            raise Campaign103FeatureError("audit requires --manifest and --output")
        path = no_return_audit(manifest_path=args.manifest, output=args.output)
        payload = {"audit": str(path)}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
