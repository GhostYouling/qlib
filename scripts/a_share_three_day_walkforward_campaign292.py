#!/usr/bin/env python3
"""Run Campaign292's frozen Alpha158 peer-rank-extremity campaign."""

from __future__ import annotations

import argparse
import gc
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import rankdata

from scripts import a_share_three_day_walkforward_campaign290 as base


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_292_preregistration_20260825.json"
)
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_292_implementation_freeze_v4_20260825.json"
)
INFRASTRUCTURE_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_292_local_volume_enospc_failure_20260825.json"
)
METADATA_TEST_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_292_v2_plan_test_output_root_binding_failure_20260825.json"
)
DIRECT_SCRIPT_PLAN_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_292_direct_script_plan_import_failure_20260825.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign292.py"
)
CONCEPT_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_292_concept_scouting_20260825.json"
)
ALPHA158_MANIFEST_PATH = base.ALPHA158_MANIFEST_PATH
NUMERIC140_MANIFEST_PATH = base.NUMERIC140_MANIFEST_PATH
C136_MANIFEST_PATH = base.C136_MANIFEST_PATH
C146_MANIFEST_PATH = base.C146_MANIFEST_PATH
C263_MANIFEST_PATH = base.C263_MANIFEST_PATH
C290_MANIFEST_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_290/"
    "alpha158_session_median_state_persistence_v1/candidate_snapshot/"
    "snapshot_manifest.json"
)
C291_MANIFEST_PATH = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_291/"
    "alpha158_session_median_state_consensus_strength_v1/candidate_snapshot/"
    "snapshot_manifest.json"
)
SIGNAL_LEDGER_PATH = base.SIGNAL_LEDGER_PATH
EXECUTION_LEDGER_PATH = base.EXECUTION_LEDGER_PATH
FROZEN_OUTPUT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_292/"
    "alpha158_session_peer_rank_extremity_breadth_v2"
)
OUTPUT_ROOT = FROZEN_OUTPUT_ROOT
CANDIDATE_ROOT = OUTPUT_ROOT / "candidate_snapshot"
CANDIDATE_MANIFEST_PATH = CANDIDATE_ROOT / "snapshot_manifest.json"
NO_RETURN_PATH = OUTPUT_ROOT / "no_return_audit.json"
TERMINAL_RESULT_PATH = OUTPUT_ROOT / "terminal_result.json"
TRIAL_LEDGER_PATH = OUTPUT_ROOT / "terminal_trial_ledger.json"

FACTOR_NAME = "alpha158_session_peer_rank_extremity_breadth_1d"
TRIAL_ID = "wf292_alpha158_session_peer_rank_extremity_breadth_1d_single_higher"
CAMPAIGN290_FACTOR = "alpha158_session_median_state_persistence_1d"
CAMPAIGN291_FACTOR = "alpha158_session_median_state_consensus_strength_1d"
FEATURE_COUNT = 158
MINIMUM_FINITE_FEATURES = 119
MINIMUM_PAIRWISE_NAMES = 50
MINIMUM_PAIRWISE_SESSIONS = 100
MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION = 0.8
EXPECTED_COMPARATOR_COUNT = 145
EXPECTED_COMPARATOR_ORDER_SHA256 = (
    "d1dbf29b7143f837f7d1589e2f1f4622b1c64699b2b63a3ba940ea0258facf61"
)
YEARS = tuple(range(2019, 2024))
PURGE_SIGNAL_SESSIONS = 3
CHAIN_GENESIS = "0" * 64


class Campaign292Error(RuntimeError):
    """Fail closed when a frozen Campaign292 invariant changes."""


file_sha256 = base.file_sha256
canonical_sha256 = base.canonical_sha256
atomic_json = base.atomic_json
atomic_parquet = base.atomic_parquet
resolve_record = base.resolve_record
record_for_year = base.record_for_year


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Campaign292Error(f"JSON binding unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise Campaign292Error(f"JSON binding is not an object: {path}")
    return value


def require_file(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or file_sha256(path) != expected:
        raise Campaign292Error(f"{label} fingerprint changed")


def validate_protocol() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    protocol = load_json(PROTOCOL_PATH)
    factor = (protocol.get("factor_library") or [{}])[0]
    parameters = factor.get("parameters") or {}
    uniqueness = protocol.get("ordered_numeric_uniqueness") or {}
    development = protocol.get("development_trial") or {}
    boundary = protocol.get("research_boundary") or {}
    if not (
        protocol.get("kind")
        == "a_share_three_day_walkforward_campaign292_preregistration"
        and protocol.get("status")
        == "fully_frozen_before_candidate_comparator_daily_price_or_forward_return_values"
        and len(protocol.get("factor_library") or []) == 1
        and factor.get("name") == FACTOR_NAME
        and factor.get("direction") == "higher"
        and parameters
        == {
            "coordinate_count": FEATURE_COUNT,
            "minimum_finite_coordinates": MINIMUM_FINITE_FEATURES,
            "peer_rank_method": "ascending average ties",
            "empirical_percentile": "(rank - 0.5) / finite_peer_count",
            "coordinate_extremity": "2 * abs(percentile - 0.5)",
            "aggregation": "equal-weight mean over finite coordinates",
        }
        and uniqueness.get("comparator_count") == EXPECTED_COMPARATOR_COUNT
        and uniqueness.get("comparator_order_sha256")
        == EXPECTED_COMPARATOR_ORDER_SHA256
        and uniqueness.get("minimum_pair_names_per_session")
        == MINIMUM_PAIRWISE_NAMES
        and uniqueness.get("minimum_pair_sessions_per_comparator")
        == MINIMUM_PAIRWISE_SESSIONS
        and uniqueness.get("strict_absolute_median_maximum")
        == MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION
        and uniqueness.get("ordered_early_stop") is True
        and uniqueness.get("all_145_must_pass") is True
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
        and boundary.get("credential_loaded") is False
    ):
        raise Campaign292Error("Campaign292 protocol semantics changed")
    for label, binding in (protocol.get("authoritative_inputs") or {}).items():
        require_file(
            REPO_ROOT / str(binding["path"]), str(binding["sha256"]), label
        )
    for label, binding in (protocol.get("source_bindings") or {}).items():
        target = Path(str(binding["path"]))
        if not target.is_absolute():
            target = REPO_ROOT / target
        require_file(target, str(binding["sha256"]), label)
        if binding.get("verification_path"):
            require_file(
                REPO_ROOT / str(binding["verification_path"]),
                str(binding["verification_sha256"]),
                f"{label} verification",
            )
    candidate49 = protocol.get("candidate49_boundary") or {}
    require_file(
        SIGNAL_LEDGER_PATH,
        str(candidate49["signal_ledger_sha256"]),
        "Candidate49 signal ledger",
    )
    require_file(
        EXECUTION_LEDGER_PATH,
        str(candidate49["execution_ledger_sha256"]),
        "Candidate49 execution ledger",
    )
    alpha = load_json(ALPHA158_MANIFEST_PATH)
    numeric = load_json(NUMERIC140_MANIFEST_PATH)
    campaign290 = load_json(C290_MANIFEST_PATH)
    campaign291 = load_json(C291_MANIFEST_PATH)
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
        and campaign290.get("dataset_sha256")
        == protocol["source_bindings"]["campaign290_snapshot"]["dataset_sha256"]
        and campaign290.get("factor_name") == CAMPAIGN290_FACTOR
        and campaign290.get("direction") == "higher"
        and [int(item["year"]) for item in campaign290.get("files", [])]
        == list(YEARS)
        and campaign291.get("dataset_sha256")
        == protocol["source_bindings"]["campaign291_snapshot"]["dataset_sha256"]
        and campaign291.get("factor_name") == CAMPAIGN291_FACTOR
        and campaign291.get("direction") == "higher"
        and [int(item["year"]) for item in campaign291.get("files", [])]
        == list(YEARS)
    ):
        raise Campaign292Error("source manifest semantics changed")
    return protocol, alpha, numeric


def validate_implementation_freeze() -> dict[str, Any]:
    freeze = load_json(IMPLEMENTATION_FREEZE_PATH)
    frozen = freeze.get("frozen_implementation") or {}
    boundary = freeze.get("research_boundary") or {}
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign292_implementation_freeze"
        and freeze.get("status")
        == "exact_semantic_retry_with_module_invocation_frozen_after_recorded_infrastructure_failures"
        and frozen.get("protocol_sha256") == file_sha256(PROTOCOL_PATH)
        and frozen.get("runner_sha256") == file_sha256(Path(__file__).resolve())
        and frozen.get("test_sha256") == file_sha256(TEST_PATH)
        and frozen.get("runner_dependency_sha256")
        == file_sha256(Path(base.__file__).resolve())
        and frozen.get("predecessor_implementation_freeze_v3_sha256")
        == "c620123433eeaa2a26a467a1c07272f94c6b0ba3a1afed785adac207cf5122eb"
        and frozen.get("infrastructure_failure_sha256")
        == file_sha256(INFRASTRUCTURE_FAILURE_PATH)
        and frozen.get("metadata_test_failure_sha256")
        == file_sha256(METADATA_TEST_FAILURE_PATH)
        and frozen.get("direct_script_plan_failure_sha256")
        == file_sha256(DIRECT_SCRIPT_PLAN_FAILURE_PATH)
        and frozen.get("output_root")
        == str(FROZEN_OUTPUT_ROOT.relative_to(REPO_ROOT))
        and frozen.get("release_fold_memory_before_next_fold") is True
        and frozen.get("retry_batch_size") == 8192
        and frozen.get("comparator_count") == EXPECTED_COMPARATOR_COUNT
        and frozen.get("comparator_order_sha256")
        == EXPECTED_COMPARATOR_ORDER_SHA256
        and boundary.get("alpha158_candidate_values_read_before_retry_freeze") is True
        and boundary.get("comparator_values_read_before_retry_freeze") is True
        and boundary.get("validation_fold_return_values_read_before_retry_freeze")
        == 2
        and boundary.get("stress_2024_2025_opened") is False
        and boundary.get("post_failure_formula_direction_gate_or_trial_changed")
        is False
        and boundary.get("provider_credential_loaded") is False
    ):
        raise Campaign292Error("Campaign292 implementation freeze changed")
    return freeze


def verify_annual_source_files(
    alpha: Mapping[str, Any], numeric: Mapping[str, Any]
) -> None:
    base.verify_annual_source_files(alpha, numeric)
    for manifest_path, factor, label in (
        (C290_MANIFEST_PATH, CAMPAIGN290_FACTOR, "Campaign290"),
        (C291_MANIFEST_PATH, CAMPAIGN291_FACTOR, "Campaign291"),
    ):
        manifest = load_json(manifest_path)
        for year in YEARS:
            record = record_for_year(manifest, year)
            path = resolve_record(manifest_path, record)
            require_file(path, str(record["sha256"]), f"{label} partition {year}")
            required = {"stock_day_key", factor, f"{factor}_eligible"}
            if not required.issubset(pq.read_schema(path).names):
                raise Campaign292Error(f"{label} partition schema changed: {year}")


def session_peer_rank_extremity(
    *,
    keys: np.ndarray,
    matrix: np.ndarray,
    finite_count: np.ndarray,
    feature_support: np.ndarray,
    quality_listing: np.ndarray,
    model_support: np.ndarray,
) -> pd.DataFrame:
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
        and np.array_equal(feature_support, observed >= MINIMUM_FINITE_FEATURES)
        and np.all(~model_support | (feature_support & quality_listing))
        and len(np.unique(keys)) == len(keys)
    ):
        raise Campaign292Error("Alpha158 session support semantics changed")
    score_by_row = np.full(len(keys), np.nan, dtype=np.float64)
    supported = matrix[model_support]
    if len(supported):
        extremity = np.full(supported.shape, np.nan, dtype=np.float32)
        for column in range(FEATURE_COUNT):
            finite = np.isfinite(supported[:, column])
            count = int(finite.sum())
            if not count:
                continue
            ranks = rankdata(supported[finite, column], method="average")
            percentile = (ranks - 0.5) / count
            extremity[finite, column] = 2.0 * np.abs(percentile - 0.5)
        denominator = np.isfinite(extremity).sum(axis=1)
        valid = denominator >= MINIMUM_FINITE_FEATURES
        supported_scores = np.full(len(supported), np.nan, dtype=np.float64)
        supported_scores[valid] = (
            np.nansum(extremity[valid], axis=1) / denominator[valid]
        )
        score_by_row[model_support] = supported_scores
    selected = np.flatnonzero(quality_listing)
    scores = score_by_row[selected]
    counts = observed[selected]
    eligible = (
        model_support[selected]
        & (counts >= MINIMUM_FINITE_FEATURES)
        & np.isfinite(scores)
    )
    return pd.DataFrame(
        {
            "stock_day_key": keys[selected],
            FACTOR_NAME: scores,
            "finite_feature_count": counts,
            f"{FACTOR_NAME}_eligible": eligible,
            "quality_listing_eligible": np.ones(len(selected), dtype=bool),
            "model_support_eligible": model_support[selected],
        }
    )


def build_candidate_snapshot(
    alpha: Mapping[str, Any], *, output_root: Path = CANDIDATE_ROOT
) -> dict[str, Any]:
    if output_root.exists():
        raise Campaign292Error("candidate output root already exists; refuse overwrite")
    feature_names = list(alpha["feature_names"])
    columns = [
        "stock_day_key",
        *feature_names,
        "finite_feature_count",
        "feature_support_eligible",
        "quality_listing_eligible",
        "model_support_eligible",
    ]
    records: list[dict[str, Any]] = []
    totals = {
        "quality_listing_rows": 0,
        "candidate_eligible_rows": 0,
        "finite_feature_count_minimum_eligible": FEATURE_COUNT,
        "finite_feature_count_maximum_eligible": 0,
    }
    for year in YEARS:
        source_record = record_for_year(alpha, year)
        source_path = resolve_record(ALPHA158_MANIFEST_PATH, source_record)
        parts: list[pd.DataFrame] = []
        observed_sessions = 0
        for _, frame in base.iter_session_frames(source_path, columns):
            output = session_peer_rank_extremity(
                keys=frame["stock_day_key"].to_numpy(dtype=np.int64),
                matrix=frame[feature_names].to_numpy(dtype=np.float32, copy=True),
                finite_count=frame["finite_feature_count"].to_numpy(dtype=np.uint8),
                feature_support=frame["feature_support_eligible"].to_numpy(dtype=bool),
                quality_listing=frame["quality_listing_eligible"].to_numpy(dtype=bool),
                model_support=frame["model_support_eligible"].to_numpy(dtype=bool),
            )
            parts.append(output)
            observed_sessions += 1
        annual = pd.concat(parts, ignore_index=True)
        if len(np.unique(annual["stock_day_key"])) != len(annual):
            raise Campaign292Error(f"candidate annual keys duplicated: {year}")
        output_path = output_root / "partitions" / f"{year}.parquet"
        atomic_parquet(output_path, annual)
        eligible = annual[f"{FACTOR_NAME}_eligible"].to_numpy(dtype=bool)
        counts = annual["finite_feature_count"].to_numpy(dtype=np.uint8)
        totals["quality_listing_rows"] += len(annual)
        totals["candidate_eligible_rows"] += int(eligible.sum())
        if eligible.any():
            totals["finite_feature_count_minimum_eligible"] = min(
                totals["finite_feature_count_minimum_eligible"],
                int(counts[eligible].min()),
            )
            totals["finite_feature_count_maximum_eligible"] = max(
                totals["finite_feature_count_maximum_eligible"],
                int(counts[eligible].max()),
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
        raise Campaign292Error("candidate session counts changed")
    manifest = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign292_candidate_snapshot",
        "status": "immutable_candidate_ready_for_coverage_before_comparator_values",
        "created_at": base.utc_now(),
        "factor_name": FACTOR_NAME,
        "direction": "higher",
        "formula_parameters": {
            "coordinate_count": FEATURE_COUNT,
            "minimum_finite_coordinates": MINIMUM_FINITE_FEATURES,
            "peer_rank_method": "ascending average ties",
            "empirical_percentile": "(rank-0.5)/finite_peer_count",
            "coordinate_extremity": "2*abs(percentile-0.5)",
            "score": "equal-weight mean coordinate extremity over finite coordinates",
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
    manifest: Mapping[str, Any], *, manifest_path: Path = CANDIDATE_MANIFEST_PATH
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[int, tuple[np.ndarray, np.ndarray]]]:
    key_parts: list[np.ndarray] = []
    value_parts: list[np.ndarray] = []
    eligible_parts: list[np.ndarray] = []
    by_year: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    for record in manifest.get("files", []):
        path = resolve_record(manifest_path, record)
        require_file(path, str(record["sha256"]), f"candidate partition {record['year']}")
        frame = pd.read_parquet(
            path, columns=["stock_day_key", FACTOR_NAME, f"{FACTOR_NAME}_eligible"]
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
            raise Campaign292Error("candidate snapshot values changed")
        year = int(record["year"])
        by_year[year] = (keys, values)
        key_parts.append(keys)
        value_parts.append(values)
        eligible_parts.append(eligible)
    keys = np.concatenate(key_parts)
    values = np.concatenate(value_parts)
    eligible = np.concatenate(eligible_parts)
    if len(np.unique(keys)) != len(keys) or np.any(keys[1:] < keys[:-1]):
        raise Campaign292Error("candidate snapshot key order changed")
    return keys, values, eligible, by_year


def prior_campaign_comparison(
    *,
    manifest_path: Path,
    factor: str,
    source: str,
    candidate_by_year: Mapping[int, tuple[np.ndarray, np.ndarray]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = load_json(manifest_path)
    rows: list[list[Any]] = []
    source_rows = 0
    eligible_rows = 0
    for year in YEARS:
        record = record_for_year(manifest, year)
        path = resolve_record(manifest_path, record)
        frame = pd.read_parquet(
            path,
            columns=[
                "stock_day_key",
                factor,
                f"{factor}_eligible",
            ],
        )
        source_keys = frame["stock_day_key"].to_numpy(dtype=np.int64)
        values = pd.to_numeric(frame[factor], errors="coerce").to_numpy(
            dtype=np.float64
        )
        eligible = frame[f"{factor}_eligible"].to_numpy(dtype=bool)
        values[~eligible] = np.nan
        candidate_keys, candidate_values = candidate_by_year[year]
        if not np.array_equal(source_keys, candidate_keys):
            raise Campaign292Error(f"{factor} candidate alignment changed: {year}")
        finite = values[np.isfinite(values)]
        if finite.size and ((finite < 0.0).any() or (finite > 1.0).any()):
            raise Campaign292Error(f"{factor} comparator range changed")
        rows.extend(base.daily_rank_rows(candidate_keys, candidate_values, values))
        source_rows += len(frame)
        eligible_rows += int(eligible.sum())
    result = base.comparison_result(factor, rows, source)
    receipt = {
        "source_files_read": len(YEARS),
        "source_rows_read": source_rows,
        "eligible_2019_2023_source_rows": eligible_rows,
        "matched_candidate_rows": source_rows,
        "unmatched_candidate_rows": 0,
    }
    return result, receipt


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
            CAMPAIGN290_FACTOR,
            CAMPAIGN291_FACTOR,
        ]
    )
    if len(definitions) != EXPECTED_COMPARATOR_COUNT:
        raise Campaign292Error("comparator name order changed")
    results: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    failed_ordinal: int | None = None
    for ordinal, name in enumerate(definitions[:140], start=1):
        result = base.numeric140_comparison(
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
            aligned, receipt = base.fill_snapshot_aligned(
                manifest_path=path,
                manifest=manifest,
                factor=factor,
                candidate_keys=candidate_keys,
                minimum=minimum,
                maximum=maximum,
            )
            rows = base.daily_rank_rows(candidate_keys, candidate_values, aligned)
            result = base.comparison_result(factor, rows, source)
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
    if failed_ordinal is None:
        prior_specs = [
            (
                C290_MANIFEST_PATH,
                CAMPAIGN290_FACTOR,
                "campaign290_verified_candidate_snapshot",
            ),
            (
                C291_MANIFEST_PATH,
                CAMPAIGN291_FACTOR,
                "campaign291_verified_candidate_snapshot",
            ),
        ]
        for ordinal, (manifest_path, factor, source) in enumerate(
            prior_specs, start=144
        ):
            result, receipt = prior_campaign_comparison(
                manifest_path=manifest_path,
                factor=factor,
                source=source,
                candidate_by_year=candidate_by_year,
            )
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
    absolute = [
        float(item["absolute_median_daily_rank_correlation"])
        for item in results
        if item["absolute_median_daily_rank_correlation"] is not None
    ]
    all_passed = bool(
        failed_ordinal is None and len(results) == EXPECTED_COMPARATOR_COUNT
    )
    return {
        "status": (
            "all_145_uniqueness_gates_passed"
            if all_passed
            else "ordered_uniqueness_failed_closed"
        ),
        "comparator_order_sha256": EXPECTED_COMPARATOR_ORDER_SHA256,
        "comparators_evaluated": len(results),
        "comparators_passed": sum(item["gate_passed"] is True for item in results),
        "failed_ordinal": failed_ordinal,
        "failed_factor": (
            results[-1]["comparison_factor"] if failed_ordinal is not None else None
        ),
        "all_145_passed": all_passed,
        "maximum_observed_absolute_median_daily_rank_correlation": (
            max(absolute) if absolute else None
        ),
        "results": results,
        "source_receipts": receipts,
        "historical_daily_price_or_forward_return_values_read": False,
    }


def evaluate_validation(
    fold: Mapping[str, Any], keys: np.ndarray, scores: np.ndarray, *, batch_size: int
) -> dict[str, Any]:
    validation_start, validation_end = fold["validation"]
    dates, instruments = base.decode_keys(keys)
    identities = pd.DataFrame({"trade_date": dates, "instrument": instruments})
    market, calendar = base.engine.load_market_context(
        base.model_context(), validation_end, validation_start, batch_size
    )
    schedule = base.engine.global_signal_schedule(calendar)
    factors = identities.copy()
    factors[base.engine.factor_score_column(TRIAL_ID)] = scores
    panel = base.engine.build_signal_panel(market, factors, schedule)
    quotes = base.engine.quote_lookup(market)
    return base.engine.evaluate_trial_period(
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
    concept = load_json(CONCEPT_PATH)
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
    failure = load_json(INFRASTRUCTURE_FAILURE_PATH)
    entries.append(
        {
            "attempt_id": failure["attempt_id"],
            "phase": "infrastructure_failure",
            "name": "local_volume_enospc_before_fold_3_prevalidation_binding",
            "outcome": "preserved_partial_output_exact_semantic_retry_only",
            "reason": "The workspace volume exhausted while atomically creating the fold-3 prevalidation binding after two validation folds; no terminal artifact existed.",
            "failure_record_sha256": file_sha256(INFRASTRUCTURE_FAILURE_PATH),
            "historical_forward_return_values_read": True,
            "validation_folds_with_return_values_read": 2,
            "stress_2024_2025_opened": False,
        }
    )
    metadata_test_failure = load_json(METADATA_TEST_FAILURE_PATH)
    entries.append(
        {
            "attempt_id": metadata_test_failure["attempt_id"],
            "phase": "infrastructure_failure",
            "name": "v2_metadata_plan_test_output_root_binding",
            "outcome": "recorded_exact_semantic_v3_freeze_only",
            "reason": "The v2 freeze validator compared the production root against a metadata-only test seam; no historical values were read by the failed test.",
            "failure_record_sha256": file_sha256(METADATA_TEST_FAILURE_PATH),
            "historical_forward_return_values_read": False,
            "validation_folds_with_return_values_read": 0,
            "stress_2024_2025_opened": False,
        }
    )
    direct_script_failure = load_json(DIRECT_SCRIPT_PLAN_FAILURE_PATH)
    entries.append(
        {
            "attempt_id": direct_script_failure["attempt_id"],
            "phase": "infrastructure_failure",
            "name": "direct_script_plan_import_path",
            "outcome": "recorded_module_invocation_only",
            "reason": "Direct file execution could not import the scripts package; the authorized retry uses Python module execution and no historical values were read.",
            "failure_record_sha256": file_sha256(DIRECT_SCRIPT_PLAN_FAILURE_PATH),
            "historical_forward_return_values_read": False,
            "validation_folds_with_return_values_read": 0,
            "stress_2024_2025_opened": False,
        }
    )
    entries.append(
        {
            "attempt_id": "campaign292_factor_001",
            "phase": "coverage_uniqueness_and_development",
            "name": FACTOR_NAME,
            "formula": (
                "Mean centered empirical peer-percentile extremity across finite "
                "same-session Alpha158 coordinates."
            ),
            "direction": "higher",
            "parameters": {
                "coordinate_count": FEATURE_COUNT,
                "minimum_finite_coordinates": MINIMUM_FINITE_FEATURES,
                "peer_rank_method": "ascending average ties",
                "empirical_percentile": "(rank-0.5)/finite_peer_count",
                "coordinate_extremity": "2*abs(percentile-0.5)",
                "weights": "equal",
                "fit": "none",
                "exact_restart_after_infrastructure_failure": True,
                "batch_size": 8192,
            },
            "filters": "same-session quality/listing and model support; no temporal state or common coordinate sign",
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
        "kind": "a_share_three_day_walkforward_campaign292_terminal_trial_ledger",
        "status": "append_only_terminal_chain",
        "created_at": base.utc_now(),
        "entry_count": len(chained),
        "genesis_sha256": CHAIN_GENESIS,
        "entries": chained,
        "terminal_entry_sha256": chained[-1]["entry_sha256"],
        "record_every_formula_direction_parameter_filter_subset_model_and_failure": True,
    }
    atomic_json(TRIAL_LEDGER_PATH, ledger)
    return ledger


def run_campaign(*, batch_size: int) -> dict[str, Any]:
    if batch_size != 8192:
        raise Campaign292Error("Campaign292 exact infrastructure retry batch size changed")
    protocol, alpha, numeric = validate_protocol()
    validate_implementation_freeze()
    verify_annual_source_files(alpha, numeric)
    if OUTPUT_ROOT.exists():
        raise Campaign292Error("Campaign292 output root already exists; refuse overwrite")
    candidate_manifest = build_candidate_snapshot(alpha)
    keys, values, eligible, _ = load_candidate_snapshot(candidate_manifest)
    coverage = base.coverage_result(keys, values, eligible, protocol)
    uniqueness: dict[str, Any] | None = None
    if coverage["gate_passed"]:
        uniqueness = run_ordered_uniqueness(
            numeric_manifest=numeric, candidate_manifest=candidate_manifest
        )
    all_unique = bool(uniqueness and uniqueness["all_145_passed"])
    no_return = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign292_no_return_audit",
        "status": (
            "passed_ready_for_exact_one_no_fit_development_trial"
            if all_unique
            else "failed_closed_before_historical_daily_price_or_forward_return_values"
        ),
        "created_at": base.utc_now(),
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
    if all_unique:
        by_year = load_candidate_snapshot(candidate_manifest)[3]
        for fold in protocol["development_trial"]["walkforward_folds"]:
            year = int(str(fold["validation"][0])[:4])
            candidate_keys, candidate_scores = by_year[year]
            binding_path = OUTPUT_ROOT / f"fold_{fold['fold']}_prevalidation_scores.json"
            binding = {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign292_prevalidation_scores",
                "status": "frozen_before_fold_validation_daily_price_or_forward_return_values",
                "created_at": base.utc_now(),
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
            gc.collect()
    decision = base.survivor_decision(validation_metrics)
    survivor_count = int(decision.get("passed") is True)
    terminal = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign292_terminal_result",
        "status": (
            "development_survivor_frozen_lockbox_closed_pending_new_source_freeze"
            if survivor_count
            else "terminal_no_survivor_lockbox_closed"
        ),
        "created_at": base.utc_now(),
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "implementation_freeze_sha256": file_sha256(IMPLEMENTATION_FREEZE_PATH),
        "no_return_audit": {
            "path": str(NO_RETURN_PATH),
            "sha256": file_sha256(NO_RETURN_PATH),
        },
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
            else "zero development survivors or no-return gate failed"
        ),
        "definition_library_append_eligible": all_unique,
        "prior_definition_count": 164,
        "prior_numeric_comparator_count": 145,
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
            raise Campaign292Error("terminal trial ledger chain changed")
        previous = observed
    expected_no_return = terminal.get("no_return_audit") or {}
    expected_ledger = terminal.get("terminal_trial_ledger") or {}
    if not (
        terminal.get("kind")
        == "a_share_three_day_walkforward_campaign292_terminal_result"
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
        raise Campaign292Error("Campaign292 terminal semantics changed")
    return {
        "status": "verified_campaign292_terminal",
        "survivor_count": terminal["survivor_count"],
        "validation_fold_count": terminal["validation_fold_count"],
        "no_return_status": no_return["status"],
        "trial_ledger_entries": ledger["entry_count"],
        "lockbox_2024_2025_returns_open": False,
        "candidate49_ledgers_changed": False,
    }


def plan() -> dict[str, Any]:
    protocol, alpha, numeric = validate_protocol()
    validate_implementation_freeze()
    schemas: list[dict[str, Any]] = []
    for manifest_path, manifest, label in (
        (ALPHA158_MANIFEST_PATH, alpha, "alpha158"),
        (NUMERIC140_MANIFEST_PATH, numeric, "numeric140"),
    ):
        for year in YEARS:
            record = record_for_year(manifest, year)
            path = resolve_record(manifest_path, record)
            if not path.is_file():
                raise Campaign292Error(f"{label} annual partition missing: {year}")
            schemas.append(
                {
                    "source": label,
                    "year": year,
                    "columns": len(pq.read_schema(path).names),
                }
            )
    return {
        "ready": not OUTPUT_ROOT.exists(),
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
    run.add_argument("--batch-size", type=int, default=8192)
    subparsers.add_parser("verify")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "plan":
        print(json.dumps(plan(), ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    if args.command == "run":
        if not args.confirm_run:
            raise Campaign292Error("run requires --confirm-run")
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
