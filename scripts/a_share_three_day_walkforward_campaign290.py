#!/usr/bin/env python3
"""Run Campaign290's frozen Alpha158 state-persistence research campaign."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import statistics
import tempfile
from collections.abc import Iterable, Iterator, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.stats import rankdata

from scripts import a_share_three_day_walkforward_campaign as engine


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REPO = Path("/Volumes/DIsk/Disk-Coding/qlib")
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_290_preregistration_20260825.json"
)
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_290_implementation_freeze_20260825.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign290.py"
)
FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_290_legacy_comparator_import_failure_20260825.json"
)
ALPHA158_MANIFEST_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_286/"
    "alpha158_development_design_recovery_v3/snapshot_manifest.json"
)
NUMERIC140_MANIFEST_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign132_design_matrix/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign132_numeric140_design_v1/snapshot_manifest.json"
)
C136_MANIFEST_PATH = (
    SOURCE_REPO
    / "data/experiments/short_horizon/historical_walkforward/campaign_136/"
    "source_snapshot_v1/snapshot_manifest.json"
)
C146_MANIFEST_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign146_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign146_feature_library_v1/snapshot_manifest.json"
)
C263_MANIFEST_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign263_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign263_feature_library_v1/snapshot_manifest.json"
)
CALENDAR_PATH = SOURCE_REPO / "data/qlib/cn_a_share/calendars/day.txt"
SOURCE_PROVIDER_URI = SOURCE_REPO / "data/qlib/cn_a_share"
SOURCE_QUALITY_PATH = SOURCE_REPO / "data/raw/a_share/fundamentals/quarterly_quality.parquet"
SIGNAL_LEDGER_PATH = (
    SOURCE_REPO / "data/experiments/short_horizon/candidate49_future_signal_ledger.json"
)
EXECUTION_LEDGER_PATH = (
    SOURCE_REPO
    / "data/experiments/short_horizon/candidate49_future_execution_ledger.json"
)
OUTPUT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_290/"
    "alpha158_session_median_state_persistence_v1"
)
CANDIDATE_ROOT = OUTPUT_ROOT / "candidate_snapshot"
CANDIDATE_MANIFEST_PATH = CANDIDATE_ROOT / "snapshot_manifest.json"
NO_RETURN_PATH = OUTPUT_ROOT / "no_return_audit.json"
TERMINAL_RESULT_PATH = OUTPUT_ROOT / "terminal_result.json"
TRIAL_LEDGER_PATH = OUTPUT_ROOT / "terminal_trial_ledger.json"

FACTOR_NAME = "alpha158_session_median_state_persistence_1d"
TRIAL_ID = "wf290_alpha158_session_median_state_persistence_1d_single_higher"
FEATURE_COUNT = 158
MINIMUM_PAIRED_FEATURES = 119
MINIMUM_PAIRWISE_NAMES = 50
MINIMUM_PAIRWISE_SESSIONS = 100
MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION = 0.8
EXPECTED_COMPARATOR_COUNT = 143
EXPECTED_COMPARATOR_ORDER_SHA256 = (
    "f4fbf3d578e2c80c29425716a30d60a3df01d67d04e37f1651236c4dff899588"
)
YEARS = tuple(range(2019, 2024))
PURGE_SIGNAL_SESSIONS = 3
FILE_MODE = 0o600
KEY_SCALE = 4_000_000
STATE_MISSING = np.int8(2)
CHAIN_GENESIS = "0" * 64


class Campaign290Error(RuntimeError):
    """Fail closed when a frozen Campaign290 invariant changes."""


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Campaign290Error(f"JSON binding unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise Campaign290Error(f"JSON binding is not an object: {path}")
    return value


def require_file(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or file_sha256(path) != expected:
        raise Campaign290Error(f"{label} fingerprint changed")


def atomic_json(path: Path, value: Any) -> None:
    payload = (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, FILE_MODE)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(name)
    try:
        pq.write_table(
            pa.Table.from_pandas(frame, preserve_index=False),
            temporary,
            compression="zstd",
            use_dictionary=False,
        )
        os.chmod(temporary, FILE_MODE)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def resolve_record(manifest_path: Path, record: Mapping[str, Any]) -> Path:
    raw = Path(str(record.get("path") or record.get("relative_path") or ""))
    return raw.resolve() if raw.is_absolute() else (manifest_path.parent / raw).resolve()


def record_for_year(manifest: Mapping[str, Any], year: int) -> dict[str, Any]:
    matches = [item for item in manifest.get("files", []) if int(item["year"]) == year]
    if len(matches) != 1:
        raise Campaign290Error(f"annual partition identity changed: {year}")
    return dict(matches[0])


def validate_protocol() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    protocol = load_json(PROTOCOL_PATH)
    if not (
        protocol.get("kind") == "a_share_three_day_walkforward_campaign290_preregistration"
        and protocol.get("status")
        == "fully_frozen_before_candidate_comparator_daily_price_or_forward_return_values"
        and len(protocol.get("factor_library") or []) == 1
        and protocol["factor_library"][0].get("name") == FACTOR_NAME
        and protocol["factor_library"][0].get("direction") == "higher"
        and protocol["factor_library"][0].get("parameters")
        == {
            "coordinate_count": FEATURE_COUNT,
            "minimum_paired_finite_coordinates": MINIMUM_PAIRED_FEATURES,
            "lag_accepted_sessions": 1,
            "state_cut": "exact finite session median",
            "coordinate_weight": 1.0,
        }
    ):
        raise Campaign290Error("Campaign290 protocol semantics changed")
    boundary = protocol.get("research_boundary") or {}
    uniqueness = protocol.get("ordered_numeric_uniqueness") or {}
    development = protocol.get("development_trial") or {}
    if not (
        uniqueness.get("comparator_count") == EXPECTED_COMPARATOR_COUNT
        and uniqueness.get("comparator_order_sha256")
        == EXPECTED_COMPARATOR_ORDER_SHA256
        and uniqueness.get("minimum_pair_names_per_session")
        == MINIMUM_PAIRWISE_NAMES
        and uniqueness.get("minimum_pair_sessions_per_comparator")
        == MINIMUM_PAIRWISE_SESSIONS
        and uniqueness.get("strict_absolute_median_maximum")
        == MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION
        and uniqueness.get("ordered_early_stop") is True
        and uniqueness.get("all_143_must_pass") is True
        and development.get("trial_id") == TRIAL_ID
        and development.get("model_fitting") is False
        and development.get("training_return_reads") == 0
        and development.get("purge_signal_sessions") == PURGE_SIGNAL_SESSIONS
        and len(development.get("walkforward_folds") or []) == 3
        and boundary.get("candidate_or_comparator_values_read_before_protocol")
        is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_protocol"
        )
        is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign290Error("Campaign290 gate or development semantics changed")
    for label, binding in (protocol.get("authoritative_inputs") or {}).items():
        target = REPO_ROOT / str(binding["path"])
        require_file(target, str(binding["sha256"]), label)
    for label, binding in (protocol.get("source_bindings") or {}).items():
        target = Path(str(binding["path"]))
        if not target.is_absolute():
            target = REPO_ROOT / target
        require_file(target, str(binding["sha256"]), label)
        verification = binding.get("verification_path")
        if verification:
            require_file(
                REPO_ROOT / str(verification),
                str(binding["verification_sha256"]),
                f"{label} verification",
            )
    candidate = protocol.get("candidate49_boundary") or {}
    require_file(
        SIGNAL_LEDGER_PATH, str(candidate["signal_ledger_sha256"]), "signal ledger"
    )
    require_file(
        EXECUTION_LEDGER_PATH,
        str(candidate["execution_ledger_sha256"]),
        "execution ledger",
    )
    alpha = load_json(ALPHA158_MANIFEST_PATH)
    numeric = load_json(NUMERIC140_MANIFEST_PATH)
    if not (
        alpha.get("dataset_sha256")
        == protocol["source_bindings"]["alpha158_design"]["dataset_sha256"]
        and alpha.get("feature_count") == FEATURE_COUNT
        and len(alpha.get("feature_names") or []) == FEATURE_COUNT
        and [int(item["year"]) for item in alpha.get("files", [])] == list(YEARS)
        and numeric.get("dataset_sha256")
        == protocol["source_bindings"]["numeric140_design"]["dataset_sha256"]
        and len(numeric.get("feature_names") or []) == 140
        and [int(item["year"]) for item in numeric.get("files", [])][:5]
        == list(YEARS)
    ):
        raise Campaign290Error("source manifest semantics changed")
    return protocol, alpha, numeric


def validate_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_PATH.is_file():
        raise Campaign290Error("Campaign290 implementation freeze is absent")
    freeze = load_json(IMPLEMENTATION_FREEZE_PATH)
    frozen = freeze.get("frozen_implementation") or {}
    boundary = freeze.get("research_boundary") or {}
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign290_implementation_freeze"
        and freeze.get("status")
        == "candidate_coverage_ordered_143_and_no_fit_development_runner_frozen_before_candidate_values"
        and frozen.get("protocol_sha256") == file_sha256(PROTOCOL_PATH)
        and frozen.get("runner_sha256") == file_sha256(Path(__file__).resolve())
        and frozen.get("test_sha256") == file_sha256(TEST_PATH)
        and frozen.get("comparator_count") == EXPECTED_COMPARATOR_COUNT
        and frozen.get("comparator_order_sha256")
        == EXPECTED_COMPARATOR_ORDER_SHA256
        and boundary.get("alpha158_candidate_values_read_before_freeze") is False
        and boundary.get("comparator_values_read_before_freeze") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
    ):
        raise Campaign290Error("Campaign290 implementation freeze changed")
    return freeze


def verify_annual_source_files(
    alpha: Mapping[str, Any], numeric: Mapping[str, Any]
) -> None:
    alpha_columns = [
        "stock_day_key",
        *list(alpha["feature_names"]),
        "finite_feature_count",
        "feature_support_eligible",
        "quality_listing_eligible",
        "model_support_eligible",
    ]
    numeric_columns = [
        "stock_day_key",
        *list(numeric["feature_names"]),
        "finite_component_count",
        "model_support_eligible",
    ]
    for manifest_path, manifest, columns, label in (
        (ALPHA158_MANIFEST_PATH, alpha, alpha_columns, "Alpha158"),
        (NUMERIC140_MANIFEST_PATH, numeric, numeric_columns, "Numeric140"),
    ):
        for year in YEARS:
            record = record_for_year(manifest, year)
            path = resolve_record(manifest_path, record)
            require_file(path, str(record["sha256"]), f"{label} partition {year}")
            if pq.read_schema(path).names != columns:
                raise Campaign290Error(f"{label} partition schema changed: {year}")


def accepted_days() -> tuple[np.ndarray, dict[int, int]]:
    values = [
        line.strip()
        for line in CALENDAR_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    selected = [value for value in values if "2019-01-01" <= value <= "2023-12-31"]
    days = (
        pd.DatetimeIndex(selected)
        .to_numpy(dtype="datetime64[D]")
        .astype(np.int64)
    )
    if len(days) != 1214 or np.any(days[1:] <= days[:-1]):
        raise Campaign290Error("accepted 2019-2023 calendar changed")
    return days, {int(day): index for index, day in enumerate(days)}


def iter_session_frames(
    path: Path, columns: Sequence[str], *, batch_size: int = 65_536
) -> Iterator[tuple[int, pd.DataFrame]]:
    carry: pd.DataFrame | None = None
    for batch in pq.ParquetFile(path).iter_batches(batch_size=batch_size, columns=columns):
        frame = batch.to_pandas()
        if carry is not None:
            frame = pd.concat([carry, frame], ignore_index=True)
            carry = None
        days = frame["stock_day_key"].to_numpy(dtype=np.int64) // KEY_SCALE
        if len(frame) == 0:
            continue
        last_day = int(days[-1])
        last_start = int(np.searchsorted(days, last_day, side="left"))
        complete = frame.iloc[:last_start]
        carry = frame.iloc[last_start:].copy()
        if not complete.empty:
            complete_days = (
                complete["stock_day_key"].to_numpy(dtype=np.int64) // KEY_SCALE
            )
            boundaries = np.flatnonzero(
                np.r_[True, complete_days[1:] != complete_days[:-1], True]
            )
            for start, stop in zip(boundaries[:-1], boundaries[1:], strict=True):
                yield int(complete_days[start]), complete.iloc[start:stop]
    if carry is not None and not carry.empty:
        day = int(carry["stock_day_key"].iloc[0]) // KEY_SCALE
        if not np.all(carry["stock_day_key"].to_numpy(dtype=np.int64) // KEY_SCALE == day):
            raise Campaign290Error("session carry spans multiple dates")
        yield day, carry


def session_state_persistence(
    *,
    keys: np.ndarray,
    matrix: np.ndarray,
    finite_count: np.ndarray,
    feature_support: np.ndarray,
    quality_listing: np.ndarray,
    model_support: np.ndarray,
    previous_states: Mapping[int, np.ndarray] | None,
    exact_previous_session: bool,
) -> tuple[pd.DataFrame, dict[int, np.ndarray]]:
    keys = np.asarray(keys, dtype=np.int64)
    matrix = np.asarray(matrix, dtype=np.float32)
    finite_count = np.asarray(finite_count, dtype=np.uint8)
    feature_support = np.asarray(feature_support, dtype=bool)
    quality_listing = np.asarray(quality_listing, dtype=bool)
    model_support = np.asarray(model_support, dtype=bool)
    observed = np.isfinite(matrix).sum(axis=1).astype(np.uint8)
    if not (
        matrix.shape == (len(keys), FEATURE_COUNT)
        and np.array_equal(observed, finite_count)
        and np.array_equal(feature_support, observed >= MINIMUM_PAIRED_FEATURES)
        and np.all(~model_support | (feature_support & quality_listing))
        and len(np.unique(keys)) == len(keys)
    ):
        raise Campaign290Error("Alpha158 session support semantics changed")
    supported_matrix = matrix[model_support]
    if len(supported_matrix):
        with np.errstate(all="ignore"):
            medians = np.nanmedian(supported_matrix, axis=0)
        states = np.full(supported_matrix.shape, STATE_MISSING, dtype=np.int8)
        finite = np.isfinite(supported_matrix) & np.isfinite(medians)[None, :]
        states[finite & (supported_matrix < medians)] = -1
        states[finite & (supported_matrix == medians)] = 0
        states[finite & (supported_matrix > medians)] = 1
    else:
        states = np.empty((0, FEATURE_COUNT), dtype=np.int8)
    securities = keys % KEY_SCALE
    current_states = {
        int(security): state.copy()
        for security, state in zip(securities[model_support], states, strict=True)
    }
    selected = np.flatnonzero(quality_listing)
    scores = np.full(len(selected), np.nan, dtype=np.float64)
    paired_counts = np.zeros(len(selected), dtype=np.uint8)
    eligible = np.zeros(len(selected), dtype=bool)
    if exact_previous_session and previous_states is not None:
        supported_lookup = {
            int(index): state
            for index, state in zip(
                np.flatnonzero(model_support), states, strict=True
            )
        }
        for out_index, row_index in enumerate(selected):
            current = supported_lookup.get(int(row_index))
            previous = previous_states.get(int(securities[row_index]))
            if current is None or previous is None:
                continue
            paired = (current != STATE_MISSING) & (previous != STATE_MISSING)
            count = int(paired.sum())
            paired_counts[out_index] = count
            if count < MINIMUM_PAIRED_FEATURES:
                continue
            scores[out_index] = float(np.equal(current[paired], previous[paired]).mean())
            eligible[out_index] = True
    output = pd.DataFrame(
        {
            "stock_day_key": keys[selected],
            FACTOR_NAME: scores,
            "paired_feature_count": paired_counts,
            f"{FACTOR_NAME}_eligible": eligible,
            "quality_listing_eligible": np.ones(len(selected), dtype=bool),
            "model_support_eligible": model_support[selected],
        }
    )
    return output, current_states


def build_candidate_snapshot(
    alpha: Mapping[str, Any], *, output_root: Path = CANDIDATE_ROOT
) -> dict[str, Any]:
    if output_root.exists():
        raise Campaign290Error("candidate output root already exists; refuse overwrite")
    feature_names = list(alpha["feature_names"])
    columns = [
        "stock_day_key",
        *feature_names,
        "finite_feature_count",
        "feature_support_eligible",
        "quality_listing_eligible",
        "model_support_eligible",
    ]
    calendar, calendar_order = accepted_days()
    del calendar
    previous_day: int | None = None
    previous_states: dict[int, np.ndarray] | None = None
    records: list[dict[str, Any]] = []
    totals = {
        "quality_listing_rows": 0,
        "candidate_eligible_rows": 0,
        "paired_feature_count_minimum_eligible": FEATURE_COUNT,
        "paired_feature_count_maximum_eligible": 0,
    }
    for year in YEARS:
        source_record = record_for_year(alpha, year)
        source_path = resolve_record(ALPHA158_MANIFEST_PATH, source_record)
        parts: list[pd.DataFrame] = []
        observed_sessions = 0
        for day, frame in iter_session_frames(source_path, columns):
            current_order = calendar_order.get(day)
            if current_order is None:
                raise Campaign290Error("Alpha158 design contains a non-calendar session")
            exact_previous = bool(
                previous_day is not None
                and calendar_order.get(previous_day) == current_order - 1
            )
            matrix = frame[feature_names].to_numpy(dtype=np.float32, copy=True)
            output, current_states = session_state_persistence(
                keys=frame["stock_day_key"].to_numpy(dtype=np.int64),
                matrix=matrix,
                finite_count=frame["finite_feature_count"].to_numpy(dtype=np.uint8),
                feature_support=frame["feature_support_eligible"].to_numpy(dtype=bool),
                quality_listing=frame["quality_listing_eligible"].to_numpy(dtype=bool),
                model_support=frame["model_support_eligible"].to_numpy(dtype=bool),
                previous_states=previous_states,
                exact_previous_session=exact_previous,
            )
            parts.append(output)
            previous_day = day
            previous_states = current_states
            observed_sessions += 1
        annual = pd.concat(parts, ignore_index=True)
        if len(np.unique(annual["stock_day_key"])) != len(annual):
            raise Campaign290Error(f"candidate annual keys duplicated: {year}")
        output_path = output_root / "partitions" / f"{year}.parquet"
        atomic_parquet(output_path, annual)
        eligible = annual[f"{FACTOR_NAME}_eligible"].to_numpy(dtype=bool)
        paired = annual["paired_feature_count"].to_numpy(dtype=np.uint8)
        totals["quality_listing_rows"] += len(annual)
        totals["candidate_eligible_rows"] += int(eligible.sum())
        if eligible.any():
            totals["paired_feature_count_minimum_eligible"] = min(
                totals["paired_feature_count_minimum_eligible"],
                int(paired[eligible].min()),
            )
            totals["paired_feature_count_maximum_eligible"] = max(
                totals["paired_feature_count_maximum_eligible"],
                int(paired[eligible].max()),
            )
        records.append(
            {
                "year": year,
                "path": str(output_path.relative_to(output_root)),
                "rows": len(annual),
                "eligible_rows": int(eligible.sum()),
                "sessions": observed_sessions,
                "sha256": file_sha256(output_path),
            }
        )
        del annual, parts
        gc.collect()
    if [item["sessions"] for item in records] != [244, 243, 243, 242, 242]:
        raise Campaign290Error("candidate session counts changed")
    manifest = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign290_candidate_snapshot",
        "status": "immutable_candidate_ready_for_coverage_before_comparator_values",
        "created_at": utc_now(),
        "factor_name": FACTOR_NAME,
        "direction": "higher",
        "formula_parameters": {
            "coordinate_count": FEATURE_COUNT,
            "minimum_paired_finite_coordinates": MINIMUM_PAIRED_FEATURES,
            "lag_accepted_sessions": 1,
            "state_cut": "exact finite model-support-peer session median",
        },
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "implementation_freeze_sha256": file_sha256(IMPLEMENTATION_FREEZE_PATH),
        "source_manifest_sha256": file_sha256(ALPHA158_MANIFEST_PATH),
        "source_dataset_sha256": alpha["dataset_sha256"],
        "files": records,
        "totals": totals,
        "dataset_sha256": canonical_sha256(
            [[item["year"], item["sha256"], item["rows"]] for item in records]
        ),
        "alpha158_values_read": True,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
        "candidate49_ledgers_changed": False,
    }
    atomic_json(output_root / "snapshot_manifest.json", manifest)
    return manifest


def load_candidate_snapshot(
    manifest: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[int, tuple[np.ndarray, np.ndarray]]]:
    keys_parts: list[np.ndarray] = []
    values_parts: list[np.ndarray] = []
    eligible_parts: list[np.ndarray] = []
    by_year: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    for record in manifest.get("files", []):
        path = resolve_record(CANDIDATE_MANIFEST_PATH, record)
        require_file(path, str(record["sha256"]), f"candidate partition {record['year']}")
        frame = pd.read_parquet(
            path,
            columns=["stock_day_key", FACTOR_NAME, f"{FACTOR_NAME}_eligible"],
        )
        keys = frame["stock_day_key"].to_numpy(dtype=np.int64)
        values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce").to_numpy(
            dtype=np.float64
        )
        eligible = frame[f"{FACTOR_NAME}_eligible"].to_numpy(dtype=bool)
        if not (
            np.all(np.diff(keys) >= 0)
            and np.all(np.isfinite(values[eligible]))
            and np.all((values[eligible] >= 0.0) & (values[eligible] <= 1.0))
            and np.all(~eligible | np.isfinite(values))
        ):
            raise Campaign290Error("candidate snapshot values changed")
        year = int(record["year"])
        by_year[year] = (keys, values)
        keys_parts.append(keys)
        values_parts.append(values)
        eligible_parts.append(eligible)
    keys = np.concatenate(keys_parts)
    values = np.concatenate(values_parts)
    eligible = np.concatenate(eligible_parts)
    if len(np.unique(keys)) != len(keys) or np.any(keys[1:] < keys[:-1]):
        raise Campaign290Error("candidate snapshot key order changed")
    return keys, values, eligible, by_year


def coverage_result(
    keys: np.ndarray, values: np.ndarray, eligible: np.ndarray, protocol: Mapping[str, Any]
) -> dict[str, Any]:
    days = keys // KEY_SCALE
    boundaries = np.flatnonzero(np.r_[True, days[1:] != days[:-1], True])
    rows: list[list[Any]] = []
    for start, stop in zip(boundaries[:-1], boundaries[1:], strict=True):
        selected = eligible[start:stop] & np.isfinite(values[start:stop])
        rows.append(
            [int(days[start]), int(stop - start), int(selected.sum()), float(selected.mean())]
        )
    frame = pd.DataFrame(rows, columns=["day", "denominator", "numerator", "coverage"])
    gate = protocol["coverage_first_gate"]
    indices = np.arange(0, max(len(frame) - 3, 0), 3)
    possible = frame["numerator"].to_numpy(dtype=np.int64)[indices] >= int(
        gate["p05_eligible_equity_count_minimum"]
    )
    years = sorted(
        set(
            pd.to_datetime(
                frame["day"].to_numpy(dtype=np.int64)[indices][possible],
                unit="D",
                origin="unix",
            ).year
        )
    )
    median = float(frame["coverage"].median())
    p05 = float(frame["coverage"].quantile(0.05))
    names_p05 = float(frame["numerator"].quantile(0.05))
    potential = int(possible.sum())
    passed = bool(
        median >= float(gate["median_daily_coverage_minimum"])
        and p05 >= float(gate["p05_daily_coverage_minimum"])
        and names_p05 >= int(gate["p05_eligible_equity_count_minimum"])
        and potential >= int(gate["non_overlapping_three_signal_session_cohorts_minimum"])
        and len(years) >= int(gate["observed_calendar_years_minimum"])
    )
    return {
        "gate_passed": passed,
        "quality_listing_rows": len(keys),
        "candidate_eligible_rows": int(eligible.sum()),
        "calendar_sessions": len(frame),
        "median_daily_coverage": median,
        "p05_daily_coverage": p05,
        "eligible_names_minimum": int(frame["numerator"].min()),
        "eligible_names_p05": names_p05,
        "eligible_names_median": float(frame["numerator"].median()),
        "potential_non_overlapping_three_session_cohorts": potential,
        "observed_cohort_years": years,
        "daily_coverage_frame_sha256": canonical_sha256(rows),
        "thresholds": gate,
        "worst_ten_sessions": [
            {
                "trade_date": pd.Timestamp(row.day, unit="D").date().isoformat(),
                "quality_listing_eligible_names": int(row.denominator),
                "candidate_eligible_names": int(row.numerator),
                "coverage": float(row.coverage),
            }
            for row in frame.sort_values(["coverage", "day"], kind="stable")
            .head(10)
            .itertuples(index=False)
        ],
    }


def daily_rank_rows(
    keys: np.ndarray,
    candidate_values: np.ndarray,
    comparison_values: np.ndarray,
    *,
    minimum_names: int = MINIMUM_PAIRWISE_NAMES,
) -> list[list[Any]]:
    keys = np.asarray(keys, dtype=np.int64)
    candidate_values = np.asarray(candidate_values, dtype=np.float64)
    comparison_values = np.asarray(comparison_values, dtype=np.float64)
    if not (
        keys.ndim == candidate_values.ndim == comparison_values.ndim == 1
        and len(keys) == len(candidate_values) == len(comparison_values)
        and np.all(keys[1:] >= keys[:-1])
    ):
        raise Campaign290Error("daily rank arrays changed")
    days = keys // KEY_SCALE
    boundaries = np.flatnonzero(np.r_[True, days[1:] != days[:-1], True])
    rows: list[list[Any]] = []
    for start, stop in zip(boundaries[:-1], boundaries[1:], strict=True):
        candidate = candidate_values[start:stop]
        comparison = comparison_values[start:stop]
        finite = np.isfinite(candidate) & np.isfinite(comparison)
        count = int(finite.sum())
        if count < minimum_names:
            continue
        left = candidate[finite]
        right = comparison[finite]
        if np.unique(left).size < 2 or np.unique(right).size < 2:
            continue
        correlation = float(
            np.corrcoef(
                rankdata(left, method="average") / count,
                rankdata(right, method="average") / count,
            )[0, 1]
        )
        if math.isfinite(correlation):
            rows.append([int(days[start]), count, correlation])
    return rows


def comparison_result(name: str, daily_rows_value: list[list[Any]], source: str) -> dict[str, Any]:
    correlations = np.asarray([row[2] for row in daily_rows_value], dtype=np.float64)
    sessions = len(correlations)
    median = float(np.median(correlations)) if sessions else math.nan
    passed = bool(
        sessions >= MINIMUM_PAIRWISE_SESSIONS
        and math.isfinite(median)
        and abs(median) < MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION
    )
    return {
        "comparison_factor": name,
        "source": source,
        "comparison_value_semantics": "frozen direction-normalized average-tie percentile rank",
        "pairwise_sessions": sessions,
        "minimum_pairwise_names_observed": (
            min(int(row[1]) for row in daily_rows_value) if daily_rows_value else 0
        ),
        "median_daily_rank_correlation": median if math.isfinite(median) else None,
        "absolute_median_daily_rank_correlation": (
            abs(median) if math.isfinite(median) else None
        ),
        "daily_rank_correlation_p05": (
            float(np.quantile(correlations, 0.05)) if sessions else None
        ),
        "daily_rank_correlation_p95": (
            float(np.quantile(correlations, 0.95)) if sessions else None
        ),
        "daily_correlation_frame_sha256": (
            canonical_sha256(daily_rows_value) if sessions else None
        ),
        "gate_passed": passed,
    }


def compact_stock_day_keys(dates: pd.Series, symbols: pd.Series) -> np.ndarray:
    days = (
        pd.DatetimeIndex(pd.to_datetime(dates).dt.normalize())
        .to_numpy(dtype="datetime64[D]")
        .astype(np.int64)
    )
    text = symbols.astype("string").str.upper()
    prefix = text.str[:2]
    exchange = prefix.map({"SH": 1, "SZ": 2, "BJ": 3})
    code = pd.to_numeric(text.str[2:], errors="coerce")
    if exchange.isna().any() or code.isna().any():
        raise Campaign290Error("snapshot symbol identity changed")
    return (
        days * KEY_SCALE
        + exchange.to_numpy(dtype=np.int64) * 1_000_000
        + code.to_numpy(dtype=np.int64)
    )


def numeric140_comparison(
    *,
    name: str,
    numeric_manifest: Mapping[str, Any],
    candidate_by_year: Mapping[int, tuple[np.ndarray, np.ndarray]],
) -> dict[str, Any]:
    rows: list[list[Any]] = []
    source_rows = 0
    for year in YEARS:
        record = record_for_year(numeric_manifest, year)
        path = resolve_record(NUMERIC140_MANIFEST_PATH, record)
        frame = pd.read_parquet(path, columns=["stock_day_key", name])
        source_keys = frame["stock_day_key"].to_numpy(dtype=np.int64)
        source_values = pd.to_numeric(frame[name], errors="coerce").to_numpy(
            dtype=np.float64
        )
        candidate_keys, candidate_values = candidate_by_year[year]
        if not np.array_equal(source_keys, candidate_keys):
            raise Campaign290Error(f"Numeric140 candidate alignment changed: {year}")
        finite = source_values[np.isfinite(source_values)]
        if finite.size and ((finite <= 0.0).any() or (finite > 1.0).any()):
            raise Campaign290Error(f"Numeric140 comparator range changed: {name}")
        rows.extend(daily_rank_rows(candidate_keys, candidate_values, source_values))
        source_rows += len(frame)
        del frame, source_values
        gc.collect()
    return comparison_result(name, rows, f"campaign132_numeric140_design:{source_rows}")


def fill_snapshot_aligned(
    *,
    manifest_path: Path,
    manifest: Mapping[str, Any],
    factor: str,
    candidate_keys: np.ndarray,
    minimum: float | None,
    maximum: float | None,
) -> tuple[np.ndarray, dict[str, Any]]:
    aligned = np.full(len(candidate_keys), np.nan, dtype=np.float64)
    filled = np.zeros(len(candidate_keys), dtype=bool)
    records = list(manifest.get("files") or manifest.get("partitions") or [])
    if manifest.get("files") is not None:
        records = [item for item in records if int(item.get("year", 0)) in YEARS]
    files_read = 0
    rows_read = 0
    eligible_rows = 0
    matched_rows = 0
    eligible_column = f"{factor}_eligible"
    for record in records:
        path = resolve_record(manifest_path, record)
        frame = pd.read_parquet(
            path, columns=["trade_date", "symbol", factor, eligible_column]
        )
        rows_read += len(frame)
        dates = pd.to_datetime(frame["trade_date"]).dt.normalize()
        in_years = dates.dt.year.isin(YEARS).to_numpy(dtype=bool)
        eligible = (
            frame[eligible_column].astype("boolean").fillna(False).to_numpy(dtype=bool)
            & in_years
        )
        numeric = pd.to_numeric(frame[factor], errors="coerce").to_numpy(
            dtype=np.float64
        )
        eligible &= np.isfinite(numeric)
        if eligible.any():
            values = numeric[eligible]
            if (
                (minimum is not None and (values < minimum).any())
                or (maximum is not None and (values > maximum).any())
            ):
                raise Campaign290Error(f"snapshot comparator range changed: {factor}")
            source_keys = compact_stock_day_keys(
                frame.loc[eligible, "trade_date"], frame.loc[eligible, "symbol"]
            )
            positions = np.searchsorted(candidate_keys, source_keys)
            matched = positions < len(candidate_keys)
            matched[matched] &= candidate_keys[positions[matched]] == source_keys[matched]
            target = positions[matched]
            if filled[target].any():
                raise Campaign290Error(f"snapshot comparator keys duplicated: {factor}")
            aligned[target] = values[matched]
            filled[target] = True
            eligible_rows += len(values)
            matched_rows += int(matched.sum())
        files_read += 1
        if files_read % 5000 == 0:
            print(json.dumps({"factor": factor, "files_read": files_read}), flush=True)
        del frame
    return aligned, {
        "source_files_read": files_read,
        "source_rows_read": rows_read,
        "eligible_2019_2023_source_rows": eligible_rows,
        "matched_candidate_rows": matched_rows,
        "unmatched_candidate_rows": len(candidate_keys) - matched_rows,
    }


def run_ordered_uniqueness(
    *,
    numeric_manifest: Mapping[str, Any],
    candidate_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_keys, candidate_values, _, candidate_by_year = load_candidate_snapshot(
        candidate_manifest
    )
    definitions = list(numeric_manifest["feature_names"])
    definitions.extend(
        [
            "daily_realized_price_basis_adjustment_magnitude_1d",
            "intraday_return_amount_cross_spectral_phase_lead_59f",
            "intraday_amount_profile_spectral_entropy_60f",
        ]
    )
    if len(definitions) != EXPECTED_COMPARATOR_COUNT:
        raise Campaign290Error("comparator name order changed")
    results: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    failed_ordinal: int | None = None
    for ordinal, name in enumerate(definitions[:140], start=1):
        result = numeric140_comparison(
            name=name,
            numeric_manifest=numeric_manifest,
            candidate_by_year=candidate_by_year,
        )
        results.append(result)
        receipts.append({"ordinal": ordinal, "source": "numeric140_annual_partitions"})
        print(
            json.dumps(
                {
                    "ordinal": ordinal,
                    "factor": name,
                    "absolute_median": result["absolute_median_daily_rank_correlation"],
                    "passed": result["gate_passed"],
                }
            ),
            flush=True,
        )
        if result["gate_passed"] is not True:
            failed_ordinal = ordinal
            break
    snapshot_specs = [
        (
            C136_MANIFEST_PATH,
            load_json(C136_MANIFEST_PATH),
            definitions[140],
            0.0,
            None,
            "campaign136_verified_snapshot",
        ),
        (
            C146_MANIFEST_PATH,
            load_json(C146_MANIFEST_PATH),
            definitions[141],
            -1.0,
            1.0,
            "campaign146_verified_snapshot",
        ),
        (
            C263_MANIFEST_PATH,
            load_json(C263_MANIFEST_PATH),
            definitions[142],
            0.0,
            1.0,
            "campaign263_verified_snapshot",
        ),
    ]
    if failed_ordinal is None:
        for ordinal, (path, manifest, factor, minimum, maximum, source) in enumerate(
            snapshot_specs, start=141
        ):
            aligned, receipt = fill_snapshot_aligned(
                manifest_path=path,
                manifest=manifest,
                factor=factor,
                candidate_keys=candidate_keys,
                minimum=minimum,
                maximum=maximum,
            )
            rows = daily_rank_rows(candidate_keys, candidate_values, aligned)
            result = comparison_result(factor, rows, source)
            results.append(result)
            receipts.append({"ordinal": ordinal, **receipt, "source": source})
            print(
                json.dumps(
                    {
                        "ordinal": ordinal,
                        "factor": factor,
                        "absolute_median": result[
                            "absolute_median_daily_rank_correlation"
                        ],
                        "passed": result["gate_passed"],
                    }
                ),
                flush=True,
            )
            if result["gate_passed"] is not True:
                failed_ordinal = ordinal
                break
            del aligned
            gc.collect()
    absolute = [
        float(item["absolute_median_daily_rank_correlation"])
        for item in results
        if item["absolute_median_daily_rank_correlation"] is not None
    ]
    return {
        "status": (
            "all_143_uniqueness_gates_passed"
            if failed_ordinal is None and len(results) == EXPECTED_COMPARATOR_COUNT
            else "ordered_uniqueness_failed_closed"
        ),
        "comparator_order_sha256": EXPECTED_COMPARATOR_ORDER_SHA256,
        "comparators_evaluated": len(results),
        "comparators_passed": sum(item["gate_passed"] is True for item in results),
        "failed_ordinal": failed_ordinal,
        "failed_factor": (
            results[-1]["comparison_factor"] if failed_ordinal is not None else None
        ),
        "all_143_passed": bool(
            failed_ordinal is None and len(results) == EXPECTED_COMPARATOR_COUNT
        ),
        "maximum_observed_absolute_median_daily_rank_correlation": (
            max(absolute) if absolute else None
        ),
        "results": results,
        "source_receipts": receipts,
        "historical_daily_price_or_forward_return_values_read": False,
    }


def model_context() -> dict[str, Any]:
    return {
        "daily_data_bindings": {
            "provider_uri": {"kind": "directory", "path": str(SOURCE_PROVIDER_URI)},
            "quarterly_quality": {"path": str(SOURCE_QUALITY_PATH)},
        }
    }


def decode_keys(keys: np.ndarray) -> tuple[pd.DatetimeIndex, np.ndarray]:
    keys = np.asarray(keys, dtype=np.int64)
    days = keys // KEY_SCALE
    security = keys % KEY_SCALE
    exchange = security // 1_000_000
    codes = security % 1_000_000
    prefix = np.empty(len(keys), dtype=object)
    for value, name in ((1, "SH"), (2, "SZ"), (3, "BJ")):
        prefix[exchange == value] = name
    if np.any(~np.isin(exchange, [1, 2, 3])):
        raise Campaign290Error("candidate key exchange changed")
    instruments = np.asarray(
        [f"{p}{int(code):06d}" for p, code in zip(prefix, codes, strict=True)],
        dtype=object,
    )
    dates = pd.DatetimeIndex(pd.to_datetime(days, unit="D", origin="unix"))
    return dates, instruments


def evaluate_validation(
    fold: Mapping[str, Any], keys: np.ndarray, scores: np.ndarray, *, batch_size: int
) -> dict[str, Any]:
    validation_start, validation_end = fold["validation"]
    dates, instruments = decode_keys(keys)
    identities = pd.DataFrame({"trade_date": dates, "instrument": instruments})
    market, calendar = engine.load_market_context(
        model_context(), validation_end, validation_start, batch_size
    )
    schedule = engine.global_signal_schedule(calendar)
    factors = identities.copy()
    factors[engine.factor_score_column(TRIAL_ID)] = scores
    panel = engine.build_signal_panel(market, factors, schedule)
    quotes = engine.quote_lookup(market)
    return engine.evaluate_trial_period(
        panel,
        quotes,
        calendar,
        schedule,
        {"feature_set": [TRIAL_ID], "weights": [1.0]},
        validation_start,
        validation_end,
        PURGE_SIGNAL_SESSIONS,
        include_sensitivity=True,
    )


def compound(values: Iterable[float]) -> float:
    result = 1.0
    for value in values:
        result *= 1.0 + float(value)
    return float(result - 1.0)


def survivor_decision(validation_metrics: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    validations = list(validation_metrics)
    reasons: list[str] = []
    if len(validations) != 3:
        reasons.append("incomplete_validation_fold_count")
    for index, result in enumerate(validations, start=1):
        association = result.get("association") or {}
        normalized = result.get("normalized_execution") or {}
        pilot = result.get("pilot_execution_primary_10bp") or {}
        if int(association.get("cohorts") or 0) < 60:
            reasons.append(f"fold_{index}_insufficient_association_cohorts")
        if int(normalized.get("terminal_unresolved_position_count") or 0) != 0:
            reasons.append(f"fold_{index}_normalized_unresolved_positions")
        if int(pilot.get("terminal_unresolved_position_count") or 0) != 0:
            reasons.append(f"fold_{index}_pilot_unresolved_positions")
        affordability = pilot.get("board_lot_affordability_rate")
        if affordability is None or float(affordability) < 0.9:
            reasons.append(f"fold_{index}_board_lot_affordability")
        participation = pilot.get("maximum_filled_trade_daily_amount_participation")
        if participation is None or float(participation) > 0.01:
            reasons.append(f"fold_{index}_amount_participation")
    if len(validations) != 3:
        return {
            "passed": False,
            "rejection_reasons": reasons,
            "operationally_admissible": False,
        }
    mean_ics = [float(item["association"]["mean_rank_ic"]) for item in validations]
    spreads = [
        float(item["association"]["mean_top3_minus_bottom3_gross_return"])
        for item in validations
    ]
    normalized_returns = [
        float(item["normalized_execution"]["net_cumulative_return"])
        for item in validations
    ]
    pilot10 = [
        float(item["pilot_execution_primary_10bp"]["net_cumulative_return"])
        for item in validations
    ]
    pilot20 = [
        float(item["pilot_slippage_sensitivity"]["0.0020"]["net_cumulative_return"])
        for item in validations
    ]
    drawdowns = [
        float(item["normalized_execution"]["maximum_drawdown"])
        for item in validations
    ]
    positive_ic = sum(value > 0.0 for value in mean_ics)
    positive_normalized = sum(value > 0.0 for value in normalized_returns)
    positive_pilot = sum(value > 0.0 for value in pilot10)
    aggregate = {
        "normalized_return": compound(normalized_returns),
        "pilot_10bp_return": compound(pilot10),
        "pilot_20bp_return": compound(pilot20),
    }
    quality = bool(
        positive_ic >= 2
        and statistics.median(mean_ics) > 0.0
        and statistics.median(spreads) > 0.0
        and positive_normalized >= 2
        and positive_pilot >= 2
        and statistics.median(pilot10) > 0.0
        and min(drawdowns) >= -0.25
        and aggregate["pilot_20bp_return"] > 0.0
    )
    if not quality:
        reasons.append("development_quality_or_aggregate_gate_failed")
    operational = not any(
        reason for reason in reasons if reason != "development_quality_or_aggregate_gate_failed"
    )
    return {
        "passed": bool(operational and quality),
        "operationally_admissible": operational,
        "validation_quality_and_aggregate_passed": quality,
        "rejection_reasons": reasons,
        "positive_mean_rank_ic_fold_count": positive_ic,
        "positive_normalized_return_fold_count": positive_normalized,
        "positive_pilot_10bp_return_fold_count": positive_pilot,
        "median_validation_mean_rank_ic": float(statistics.median(mean_ics)),
        "median_validation_spread": float(statistics.median(spreads)),
        "median_validation_pilot_10bp_return": float(statistics.median(pilot10)),
        "worst_validation_normalized_drawdown": min(drawdowns),
        "development_aggregate": aggregate,
    }


def chain_entries(entries: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    previous = CHAIN_GENESIS
    output: list[dict[str, Any]] = []
    for ordinal, raw in enumerate(entries, start=1):
        entry = {"ordinal": ordinal, "previous_entry_sha256": previous, **dict(raw)}
        digest = canonical_sha256(entry)
        entry["entry_sha256"] = digest
        output.append(entry)
        previous = digest
    return output


def write_trial_ledger(
    *, no_return: Mapping[str, Any], terminal: Mapping[str, Any]
) -> dict[str, Any]:
    concept = load_json(
        REPO_ROOT
        / "docs/a_share_three_day_walkforward_campaign_290_concept_scouting_20260825.json"
    )
    entries: list[dict[str, Any]] = []
    for item in concept["finite_prevalue_concept_catalog"]:
        entries.append(
            {
                "attempt_id": item["catalog_id"],
                "phase": "prevalue_concept_scouting",
                "name": item["name"],
                "outcome": item["decision"],
                "reason": item["reason"],
                "historical_forward_return_values_read": False,
            }
        )
    entries.append(
        {
            "attempt_id": "campaign290_infrastructure_001",
            "phase": "prevalue_infrastructure",
            "name": "legacy_campaign265_comparator_import",
            "outcome": "failed_before_candidate_comparator_or_return_values",
            "reason": "Campaign054FeatureError: Campaign054 completed no-return audit changed",
            "evidence": {"path": str(FAILURE_PATH.relative_to(REPO_ROOT)), "sha256": file_sha256(FAILURE_PATH)},
            "historical_forward_return_values_read": False,
        }
    )
    entries.append(
        {
            "attempt_id": "campaign290_factor_001",
            "phase": "coverage_uniqueness_and_development",
            "name": FACTOR_NAME,
            "formula": (
                "Fraction of identical below/equal/above session-median Alpha158 states "
                "versus the exact prior accepted session, requiring 119 paired finite coordinates."
            ),
            "direction": "higher",
            "parameters": {
                "coordinate_count": FEATURE_COUNT,
                "minimum_paired_finite_coordinates": MINIMUM_PAIRED_FEATURES,
                "lag_accepted_sessions": 1,
                "weights": "equal",
                "fit": "none",
            },
            "filters": "current and exact-prior model support; no gap bridge",
            "subset": "frozen 2019-2023 quality/listing development domain",
            "model": "none; direct single factor",
            "no_return_status": no_return["status"],
            "development_status": terminal["status"],
            "outcome": (
                "survived" if terminal.get("survivor_count") == 1 else "terminated"
            ),
            "historical_forward_return_values_read": bool(
                terminal.get("development_return_values_read")
            ),
        }
    )
    chained = chain_entries(entries)
    ledger = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign290_terminal_trial_ledger",
        "status": "append_only_terminal_chain",
        "created_at": utc_now(),
        "entry_count": len(chained),
        "genesis_sha256": CHAIN_GENESIS,
        "entries": chained,
        "terminal_entry_sha256": chained[-1]["entry_sha256"],
        "record_every_formula_direction_parameter_filter_subset_model_and_failure": True,
    }
    atomic_json(TRIAL_LEDGER_PATH, ledger)
    return ledger


def run_campaign(*, batch_size: int) -> dict[str, Any]:
    protocol, alpha, numeric = validate_protocol()
    validate_implementation_freeze()
    verify_annual_source_files(alpha, numeric)
    if OUTPUT_ROOT.exists():
        raise Campaign290Error("Campaign290 output root already exists; refuse overwrite")
    candidate_manifest = build_candidate_snapshot(alpha)
    keys, values, eligible, _ = load_candidate_snapshot(candidate_manifest)
    coverage = coverage_result(keys, values, eligible, protocol)
    uniqueness: dict[str, Any] | None = None
    if coverage["gate_passed"]:
        uniqueness = run_ordered_uniqueness(
            numeric_manifest=numeric, candidate_manifest=candidate_manifest
        )
    no_return = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign290_no_return_audit",
        "status": (
            "passed_ready_for_exact_one_no_fit_development_trial"
            if uniqueness and uniqueness["all_143_passed"]
            else "failed_closed_before_historical_daily_price_or_forward_return_values"
        ),
        "created_at": utc_now(),
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "candidate_manifest": {
            "path": str(CANDIDATE_MANIFEST_PATH),
            "sha256": file_sha256(CANDIDATE_MANIFEST_PATH),
            "dataset_sha256": candidate_manifest["dataset_sha256"],
        },
        "coverage": coverage,
        "ordered_uniqueness": uniqueness,
        "candidate_values_read": True,
        "comparator_values_read": uniqueness is not None,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
        "candidate49_ledgers_changed": False,
    }
    atomic_json(NO_RETURN_PATH, no_return)
    validation_metrics: list[dict[str, Any]] = []
    prevalidation_bindings: list[dict[str, Any]] = []
    if no_return["status"] == "passed_ready_for_exact_one_no_fit_development_trial":
        for fold in protocol["development_trial"]["walkforward_folds"]:
            year = int(str(fold["validation"][0])[:4])
            candidate_keys, candidate_scores = load_candidate_snapshot(
                candidate_manifest
            )[3][year]
            binding_path = OUTPUT_ROOT / f"fold_{fold['fold']}_prevalidation_scores.json"
            binding = {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign290_prevalidation_scores",
                "status": "frozen_before_fold_validation_daily_price_or_forward_return_values",
                "created_at": utc_now(),
                "fold": fold,
                "trial_id": TRIAL_ID,
                "candidate_manifest_sha256": file_sha256(CANDIDATE_MANIFEST_PATH),
                "candidate_partition_sha256": next(
                    item["sha256"]
                    for item in candidate_manifest["files"]
                    if int(item["year"]) == year
                ),
                "row_count": len(candidate_keys),
                "finite_score_count": int(np.isfinite(candidate_scores).sum()),
                "training_return_reads": 0,
                "validation_daily_price_or_forward_return_values_read": False,
                "lockbox_2024_2025_returns_open": False,
            }
            atomic_json(binding_path, binding)
            prevalidation_bindings.append(
                {"path": str(binding_path), "sha256": file_sha256(binding_path)}
            )
            validation_metrics.append(
                evaluate_validation(
                    fold, candidate_keys, candidate_scores, batch_size=batch_size
                )
            )
    decision = survivor_decision(validation_metrics)
    survivor_count = int(decision.get("passed") is True)
    terminal = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign290_terminal_result",
        "status": (
            "development_survivor_frozen_lockbox_closed_pending_new_source_freeze"
            if survivor_count
            else "terminal_no_survivor_lockbox_closed"
        ),
        "created_at": utc_now(),
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "implementation_freeze_sha256": file_sha256(IMPLEMENTATION_FREEZE_PATH),
        "no_return_audit": {"path": str(NO_RETURN_PATH), "sha256": file_sha256(NO_RETURN_PATH)},
        "trial_id": TRIAL_ID,
        "factor_name": FACTOR_NAME,
        "training_return_reads": 0,
        "validation_fold_count": len(validation_metrics),
        "validation_metrics": validation_metrics,
        "prevalidation_score_bindings": prevalidation_bindings,
        "decision": decision,
        "survivor_count": survivor_count,
        "development_return_values_read": bool(validation_metrics),
        "lockbox_2024_2025_returns_open": False,
        "lockbox_reason": (
            "Alpha158 2024-2025 source is absent and must be separately completed and frozen"
            if survivor_count
            else "zero development survivors"
        ),
        "definition_library_append_eligible": bool(
            uniqueness and uniqueness["all_143_passed"]
        ),
        "prior_definition_count": 162,
        "prior_numeric_comparator_count": 143,
        "candidate49_signal_ledger_sha256": file_sha256(SIGNAL_LEDGER_PATH),
        "candidate49_execution_ledger_sha256": file_sha256(EXECUTION_LEDGER_PATH),
        "candidate49_ledgers_changed": False,
        "provider_request_issued": False,
        "current_scoring_selection_sizing_positions_or_orders_performed": False,
        "investment_advice": False,
    }
    atomic_json(TERMINAL_RESULT_PATH, terminal)
    ledger = write_trial_ledger(no_return=no_return, terminal=terminal)
    terminal["terminal_trial_ledger"] = {
        "path": str(TRIAL_LEDGER_PATH),
        "sha256": file_sha256(TRIAL_LEDGER_PATH),
        "entry_count": ledger["entry_count"],
        "terminal_entry_sha256": ledger["terminal_entry_sha256"],
    }
    atomic_json(TERMINAL_RESULT_PATH, terminal)
    return terminal


def verify_terminal() -> dict[str, Any]:
    validate_protocol()
    validate_implementation_freeze()
    terminal = load_json(TERMINAL_RESULT_PATH)
    no_return = load_json(NO_RETURN_PATH)
    ledger = load_json(TRIAL_LEDGER_PATH)
    manifest = load_json(CANDIDATE_MANIFEST_PATH)
    for record in manifest.get("files", []):
        require_file(
            resolve_record(CANDIDATE_MANIFEST_PATH, record),
            str(record["sha256"]),
            f"candidate output {record['year']}",
        )
    previous = CHAIN_GENESIS
    for ordinal, entry in enumerate(ledger.get("entries", []), start=1):
        body = dict(entry)
        observed = str(body.pop("entry_sha256"))
        if not (
            int(body.get("ordinal", 0)) == ordinal
            and body.get("previous_entry_sha256") == previous
            and canonical_sha256(body) == observed
        ):
            raise Campaign290Error("terminal trial ledger chain changed")
        previous = observed
    expected_no_return = terminal.get("no_return_audit") or {}
    expected_ledger = terminal.get("terminal_trial_ledger") or {}
    if not (
        terminal.get("kind")
        == "a_share_three_day_walkforward_campaign290_terminal_result"
        and terminal.get("lockbox_2024_2025_returns_open") is False
        and terminal.get("candidate49_ledgers_changed") is False
        and expected_no_return.get("sha256") == file_sha256(NO_RETURN_PATH)
        and expected_ledger.get("sha256") == file_sha256(TRIAL_LEDGER_PATH)
        and ledger.get("terminal_entry_sha256") == previous
        and no_return.get("historical_daily_price_or_forward_return_values_read")
        is False
        and file_sha256(SIGNAL_LEDGER_PATH)
        == terminal.get("candidate49_signal_ledger_sha256")
        and file_sha256(EXECUTION_LEDGER_PATH)
        == terminal.get("candidate49_execution_ledger_sha256")
    ):
        raise Campaign290Error("Campaign290 terminal semantics changed")
    return {
        "status": "verified_campaign290_terminal",
        "survivor_count": terminal["survivor_count"],
        "validation_fold_count": terminal["validation_fold_count"],
        "no_return_status": no_return["status"],
        "trial_ledger_entries": ledger["entry_count"],
        "lockbox_2024_2025_returns_open": False,
        "candidate49_ledgers_changed": False,
    }


def plan() -> dict[str, Any]:
    protocol, alpha, numeric = validate_protocol()
    schemas: list[dict[str, Any]] = []
    for manifest_path, manifest, label in (
        (ALPHA158_MANIFEST_PATH, alpha, "alpha158"),
        (NUMERIC140_MANIFEST_PATH, numeric, "numeric140"),
    ):
        for year in YEARS:
            record = record_for_year(manifest, year)
            path = resolve_record(manifest_path, record)
            if not path.is_file():
                raise Campaign290Error(f"{label} annual partition missing: {year}")
            schemas.append(
                {"source": label, "year": year, "columns": len(pq.read_schema(path).names)}
            )
    return {
        "ready": IMPLEMENTATION_FREEZE_PATH.is_file() and not OUTPUT_ROOT.exists(),
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "implementation_freeze_present": IMPLEMENTATION_FREEZE_PATH.is_file(),
        "output_root_absent": not OUTPUT_ROOT.exists(),
        "source_schema_records": schemas,
        "candidate_values_read": False,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
        "credential_loaded": False,
        "candidate49_ledgers_changed": False,
        "trial_id": protocol["development_trial"]["trial_id"],
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    run = subparsers.add_parser("run")
    run.add_argument("--confirm-run", action="store_true")
    run.add_argument("--batch-size", type=int, default=65_536)
    subparsers.add_parser("verify")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "plan":
        print(json.dumps(plan(), ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    if args.command == "run":
        if not args.confirm_run:
            raise Campaign290Error("run requires --confirm-run")
        print(
            json.dumps(
                run_campaign(batch_size=args.batch_size),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
        )
        return 0
    print(json.dumps(verify_terminal(), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
