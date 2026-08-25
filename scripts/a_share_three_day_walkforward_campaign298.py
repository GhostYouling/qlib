#!/usr/bin/env python3
"""Run Campaign298's frozen Alpha158 volume-CV campaign."""

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

from scripts import a_share_three_day_walkforward_campaign297 as prior


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_298_preregistration_20260825.json"
)
ORIGINAL_IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_298_implementation_freeze_20260825.json"
)
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_298_implementation_freeze_v2_20260825.json"
)
CONCEPT_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_298_concept_scouting_20260825.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign298.py"
)
PREFREEZE_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_298_prefreeze_black_failure_20260825.json"
)
PREPLAN_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_298_preplan_recursive_value_read_failure_20260825.json"
)

ALPHA158_MANIFEST_PATH = prior.ALPHA158_MANIFEST_PATH
NUMERIC140_MANIFEST_PATH = prior.NUMERIC140_MANIFEST_PATH
C136_MANIFEST_PATH = prior.C136_MANIFEST_PATH
C146_MANIFEST_PATH = prior.C146_MANIFEST_PATH
C263_MANIFEST_PATH = prior.C263_MANIFEST_PATH
C290_MANIFEST_PATH = prior.C290_MANIFEST_PATH
C291_MANIFEST_PATH = prior.C291_MANIFEST_PATH
C292_MANIFEST_PATH = prior.C292_MANIFEST_PATH
C293_MANIFEST_PATH = prior.C293_MANIFEST_PATH
C295_MANIFEST_PATH = prior.C295_MANIFEST_PATH
C296_MANIFEST_PATH = prior.C296_MANIFEST_PATH
C297_MANIFEST_PATH = prior.CANDIDATE_MANIFEST_PATH
SIGNAL_LEDGER_PATH = prior.SIGNAL_LEDGER_PATH
EXECUTION_LEDGER_PATH = prior.EXECUTION_LEDGER_PATH

OUTPUT_ROOT = (
    REPO_ROOT
    / ".local-research/campaign_298/alpha158_volume_coefficient_of_variation_20d_v1"
)
CANDIDATE_ROOT = OUTPUT_ROOT / "candidate_snapshot"
CANDIDATE_MANIFEST_PATH = CANDIDATE_ROOT / "snapshot_manifest.json"
NO_RETURN_PATH = OUTPUT_ROOT / "no_return_audit.json"
TERMINAL_RESULT_PATH = OUTPUT_ROOT / "terminal_result.json"
TRIAL_LEDGER_PATH = OUTPUT_ROOT / "terminal_trial_ledger.json"

FACTOR_NAME = "alpha158_volume_coefficient_of_variation_20d"
TRIAL_ID = "wf298_alpha158_volume_coefficient_of_variation_20d_single_higher"
VOLUME_STD_FEATURE = "VSTD20"
VOLUME_MEAN_FEATURE = "VMA20"
FEATURE_COUNT = 158
MINIMUM_ALPHA158_FINITE_FEATURES = 119
EXPECTED_COMPARATOR_COUNT = 150
EXPECTED_COMPARATOR_ORDER_SHA256 = (
    "135dec87e00f39a78913e8b678c0c5e809f516c952575a9e406c360086a6508e"
)
LOWER_DIRECTION_COMPARATOR = "intraday_realized_volatility"
MINIMUM_PAIRWISE_NAMES = 50
MINIMUM_PAIRWISE_SESSIONS = 100
MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION = 0.8
YEARS = tuple(range(2019, 2024))
PURGE_SIGNAL_SESSIONS = 3
CHAIN_GENESIS = "0" * 64

CAMPAIGN290_FACTOR = prior.CAMPAIGN290_FACTOR
CAMPAIGN291_FACTOR = prior.CAMPAIGN291_FACTOR
CAMPAIGN292_FACTOR = prior.CAMPAIGN292_FACTOR
CAMPAIGN293_FACTOR = prior.CAMPAIGN293_FACTOR
CAMPAIGN295_FACTOR = prior.CAMPAIGN295_FACTOR
CAMPAIGN296_FACTOR = prior.CAMPAIGN296_FACTOR
CAMPAIGN297_FACTOR = prior.FACTOR_NAME

base = prior.base
file_sha256 = prior.file_sha256
canonical_sha256 = prior.canonical_sha256
atomic_json = prior.atomic_json
atomic_parquet = prior.atomic_parquet
resolve_record = prior.resolve_record
record_for_year = prior.record_for_year


class Campaign298Error(RuntimeError):
    """Fail closed when a frozen Campaign298 invariant changes."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Campaign298Error(f"JSON binding unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise Campaign298Error(f"JSON binding is not an object: {path}")
    return value


def require_file(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or file_sha256(path) != expected:
        raise Campaign298Error(f"{label} fingerprint changed")


def validate_protocol() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    alpha = load_json(ALPHA158_MANIFEST_PATH)
    numeric = load_json(NUMERIC140_MANIFEST_PATH)
    protocol = load_json(PROTOCOL_PATH)
    factor = (protocol.get("factor_library") or [{}])[0]
    parameters = factor.get("parameters") or {}
    coverage = protocol.get("coverage_and_capacity_gates") or {}
    uniqueness = protocol.get("ordered_numeric_uniqueness") or {}
    development = protocol.get("development_trial") or {}
    append_rule = protocol.get("append_rule") or {}
    boundary = protocol.get("research_boundary") or {}
    if not (
        protocol.get("kind")
        == "a_share_three_day_walkforward_campaign298_preregistration"
        and protocol.get("status")
        == "fully_frozen_before_campaign298_candidate_comparator_daily_price_or_forward_return_values"
        and len(protocol.get("factor_library") or []) == 1
        and factor.get("name") == FACTOR_NAME
        and factor.get("direction") == "higher"
        and parameters.get("volume_standard_deviation_feature") == VOLUME_STD_FEATURE
        and parameters.get("volume_moving_average_feature") == VOLUME_MEAN_FEATURE
        and parameters.get("fixed_horizon_sessions") == 20
        and parameters.get("score") == "VSTD20 / VMA20"
        and parameters.get("fit") == "none"
        and coverage.get("median_daily_coverage_minimum") == 0.95
        and coverage.get("p05_daily_coverage_minimum") == 0.9
        and coverage.get("p05_eligible_names_minimum") == 50
        and coverage.get("non_overlapping_three_signal_session_cohorts_minimum") == 200
        and coverage.get("cohort_years_minimum") == 5
        and coverage.get("coverage_failure_stops_before_every_comparator_value") is True
        and uniqueness.get("comparator_count") == EXPECTED_COMPARATOR_COUNT
        and uniqueness.get("comparator_order_sha256")
        == EXPECTED_COMPARATOR_ORDER_SHA256
        and uniqueness.get("minimum_pair_names_per_session") == MINIMUM_PAIRWISE_NAMES
        and uniqueness.get("minimum_pair_sessions_per_comparator")
        == MINIMUM_PAIRWISE_SESSIONS
        and uniqueness.get("strict_absolute_median_maximum")
        == MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION
        and uniqueness.get("ordered_early_stop") is True
        and uniqueness.get("all_150_must_pass") is True
        and development.get("trial_id") == TRIAL_ID
        and development.get("model_fitting") is False
        and development.get("training_return_reads") == 0
        and development.get("purge_signal_sessions") == PURGE_SIGNAL_SESSIONS
        and len(development.get("walkforward_folds") or []) == 3
        and append_rule.get("prior_library_counts")
        == {"complete_definitions": 169, "numeric_comparators": 150}
        and boundary.get(
            "campaign298_candidate_or_comparator_values_read_before_protocol"
        )
        is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_protocol"
        )
        is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("credential_value_or_digest_read") is False
    ):
        raise Campaign298Error("Campaign298 protocol semantics changed")
    for label, binding in (protocol.get("authoritative_inputs") or {}).items():
        require_file(REPO_ROOT / str(binding["path"]), str(binding["sha256"]), label)
    for label, binding in (protocol.get("source_bindings") or {}).items():
        target = Path(str(binding["path"]))
        if not target.is_absolute():
            target = REPO_ROOT / target
        require_file(target, str(binding["sha256"]), label)
    candidate49 = protocol.get("candidate49_boundary") or {}
    require_file(
        SIGNAL_LEDGER_PATH, str(candidate49["signal_ledger_sha256"]), "signal ledger"
    )
    require_file(
        EXECUTION_LEDGER_PATH,
        str(candidate49["execution_ledger_sha256"]),
        "execution ledger",
    )
    required_features = {VOLUME_STD_FEATURE, VOLUME_MEAN_FEATURE}
    if not (
        candidate49.get("same_day_20260825_retry_allowed") is False
        and alpha.get("dataset_sha256")
        == protocol["source_bindings"]["alpha158_design"]["dataset_sha256"]
        and alpha.get("feature_count") == FEATURE_COUNT
        and len(alpha.get("feature_names") or []) == FEATURE_COUNT
        and required_features.issubset(alpha["feature_names"])
        and [int(item["year"]) for item in alpha.get("files", [])] == list(YEARS)
        and numeric.get("dataset_sha256")
        == protocol["source_bindings"]["numeric140_design"]["dataset_sha256"]
        and len(numeric.get("feature_names") or []) == 140
    ):
        raise Campaign298Error("Campaign298 source or Candidate49 semantics changed")
    return protocol, alpha, numeric


def validate_implementation_freeze() -> dict[str, Any]:
    freeze = load_json(IMPLEMENTATION_FREEZE_PATH)
    frozen = freeze.get("frozen_implementation") or {}
    boundary = freeze.get("research_boundary") or {}
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign298_implementation_freeze_v2"
        and freeze.get("status")
        == "metadata_only_plan_repair_frozen_before_campaign298_candidate_comparator_or_return_values"
        and frozen.get("protocol_sha256") == file_sha256(PROTOCOL_PATH)
        and frozen.get("concept_sha256") == file_sha256(CONCEPT_PATH)
        and frozen.get("runner_sha256") == file_sha256(Path(__file__).resolve())
        and frozen.get("test_sha256") == file_sha256(TEST_PATH)
        and frozen.get("runner_dependency_sha256")
        == file_sha256(Path(prior.__file__).resolve())
        and frozen.get("prefreeze_failure_sha256")
        == file_sha256(PREFREEZE_FAILURE_PATH)
        and frozen.get("preplan_failure_sha256") == file_sha256(PREPLAN_FAILURE_PATH)
        and frozen.get("original_implementation_freeze_sha256")
        == file_sha256(ORIGINAL_IMPLEMENTATION_FREEZE_PATH)
        and frozen.get("factor_name") == FACTOR_NAME
        and frozen.get("formula") == "VSTD20 / VMA20"
        and frozen.get("fixed_horizon_sessions") == 20
        and frozen.get("comparator_count") == EXPECTED_COMPARATOR_COUNT
        and frozen.get("comparator_order_sha256") == EXPECTED_COMPARATOR_ORDER_SHA256
        and boundary.get("candidate_values_read_before_freeze") is False
        and boundary.get("comparator_values_read_before_freeze") is False
        and boundary.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and boundary.get("provider_credential_value_or_digest_read") is False
    ):
        raise Campaign298Error("Campaign298 implementation freeze changed")
    return freeze


def volume_coefficient_of_variation(
    *,
    keys: np.ndarray,
    volume_std: np.ndarray,
    volume_mean: np.ndarray,
    finite_count: np.ndarray,
    feature_support: np.ndarray,
    quality_listing: np.ndarray,
    model_support: np.ndarray,
) -> pd.DataFrame:
    keys = np.asarray(keys, dtype=np.int64)
    volume_std = np.asarray(volume_std, dtype=np.float64)
    volume_mean = np.asarray(volume_mean, dtype=np.float64)
    finite_count = np.asarray(finite_count, dtype=np.uint8)
    feature_support = np.asarray(feature_support, dtype=bool)
    quality_listing = np.asarray(quality_listing, dtype=bool)
    model_support = np.asarray(model_support, dtype=bool)
    if not (
        len(keys)
        == len(volume_std)
        == len(volume_mean)
        == len(finite_count)
        == len(feature_support)
        == len(quality_listing)
        == len(model_support)
        and np.array_equal(
            feature_support, finite_count >= MINIMUM_ALPHA158_FINITE_FEATURES
        )
        and np.all(~model_support | (feature_support & quality_listing))
        and len(np.unique(keys)) == len(keys)
    ):
        raise Campaign298Error("Alpha158 row support semantics changed")
    finite_inputs = np.isfinite(volume_std) & np.isfinite(volume_mean)
    valid_inputs = finite_inputs & (volume_std >= 0.0) & (volume_mean > 0.0)
    score = np.full(len(keys), np.nan, dtype=np.float64)
    calculable = model_support & valid_inputs
    score[calculable] = volume_std[calculable] / volume_mean[calculable]
    valid_score = np.isfinite(score) & (score >= 0.0)
    score[~valid_score] = np.nan
    selected = np.flatnonzero(quality_listing)
    selected_scores = score[selected]
    input_counts = np.isfinite(volume_std[selected]).astype(np.uint8) + np.isfinite(
        volume_mean[selected]
    ).astype(np.uint8)
    eligible = model_support[selected] & valid_inputs[selected] & valid_score[selected]
    return pd.DataFrame(
        {
            "stock_day_key": keys[selected],
            FACTOR_NAME: selected_scores,
            "finite_required_input_count": input_counts,
            f"{FACTOR_NAME}_eligible": eligible,
            "quality_listing_eligible": np.ones(len(selected), dtype=bool),
            "model_support_eligible": model_support[selected],
        }
    )


def build_candidate_snapshot(alpha: Mapping[str, Any]) -> dict[str, Any]:
    if CANDIDATE_ROOT.exists():
        raise Campaign298Error("candidate output root already exists; refuse overwrite")
    columns = [
        "stock_day_key",
        VOLUME_STD_FEATURE,
        VOLUME_MEAN_FEATURE,
        "finite_feature_count",
        "feature_support_eligible",
        "quality_listing_eligible",
        "model_support_eligible",
    ]
    records: list[dict[str, Any]] = []
    totals: dict[str, Any] = {
        "quality_listing_rows": 0,
        "candidate_eligible_rows": 0,
        "score_minimum_eligible": None,
        "score_maximum_eligible": None,
    }
    for year in YEARS:
        source_record = record_for_year(alpha, year)
        source_path = resolve_record(ALPHA158_MANIFEST_PATH, source_record)
        parts: list[pd.DataFrame] = []
        observed_sessions = 0
        for _, frame in base.iter_session_frames(source_path, columns):
            parts.append(
                volume_coefficient_of_variation(
                    keys=frame["stock_day_key"].to_numpy(dtype=np.int64),
                    volume_std=frame[VOLUME_STD_FEATURE].to_numpy(dtype=np.float64),
                    volume_mean=frame[VOLUME_MEAN_FEATURE].to_numpy(dtype=np.float64),
                    finite_count=frame["finite_feature_count"].to_numpy(dtype=np.uint8),
                    feature_support=frame["feature_support_eligible"].to_numpy(
                        dtype=bool
                    ),
                    quality_listing=frame["quality_listing_eligible"].to_numpy(
                        dtype=bool
                    ),
                    model_support=frame["model_support_eligible"].to_numpy(dtype=bool),
                )
            )
            observed_sessions += 1
        annual = pd.concat(parts, ignore_index=True)
        if len(np.unique(annual["stock_day_key"])) != len(annual):
            raise Campaign298Error(f"candidate annual keys duplicated: {year}")
        output_path = CANDIDATE_ROOT / "partitions" / f"{year}.parquet"
        atomic_parquet(output_path, annual)
        eligible = annual[f"{FACTOR_NAME}_eligible"].to_numpy(dtype=bool)
        scores = annual[FACTOR_NAME].to_numpy(dtype=np.float64)
        totals["quality_listing_rows"] += len(annual)
        totals["candidate_eligible_rows"] += int(eligible.sum())
        if eligible.any():
            annual_minimum = float(scores[eligible].min())
            annual_maximum = float(scores[eligible].max())
            totals["score_minimum_eligible"] = (
                annual_minimum
                if totals["score_minimum_eligible"] is None
                else min(float(totals["score_minimum_eligible"]), annual_minimum)
            )
            totals["score_maximum_eligible"] = (
                annual_maximum
                if totals["score_maximum_eligible"] is None
                else max(float(totals["score_maximum_eligible"]), annual_maximum)
            )
        records.append(
            {
                "year": year,
                "path": str(output_path.relative_to(CANDIDATE_ROOT)),
                "rows": len(annual),
                "eligible_rows": int(eligible.sum()),
                "sessions": observed_sessions,
                "sha256": file_sha256(output_path),
            }
        )
        del annual, parts
        gc.collect()
    if [item["sessions"] for item in records] != [244, 243, 243, 242, 242]:
        raise Campaign298Error("candidate session counts changed")
    manifest = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign298_candidate_snapshot",
        "status": "immutable_candidate_ready_for_coverage_before_comparator_values",
        "created_at": base.utc_now(),
        "factor_name": FACTOR_NAME,
        "direction": "higher",
        "formula_parameters": {
            "volume_standard_deviation_feature": VOLUME_STD_FEATURE,
            "volume_moving_average_feature": VOLUME_MEAN_FEATURE,
            "fixed_horizon_sessions": 20,
            "score": "VSTD20 / VMA20",
            "new_denominator_epsilon": None,
            "fit": "none",
        },
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "implementation_freeze_sha256": file_sha256(IMPLEMENTATION_FREEZE_PATH),
        "source_manifest_sha256": file_sha256(ALPHA158_MANIFEST_PATH),
        "source_dataset_sha256": alpha["dataset_sha256"],
        "files": records,
        "totals": totals,
        "dataset_sha256": canonical_sha256(
            [
                [
                    item["year"],
                    item["sha256"],
                    item["rows"],
                    item["eligible_rows"],
                ]
                for item in records
            ]
        ),
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
        "candidate49_ledgers_changed": False,
    }
    atomic_json(CANDIDATE_MANIFEST_PATH, manifest)
    return manifest


def load_candidate_snapshot(
    manifest: Mapping[str, Any],
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    dict[int, tuple[np.ndarray, np.ndarray]],
]:
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign298_candidate_snapshot"
        and manifest.get("factor_name") == FACTOR_NAME
        and manifest.get("direction") == "higher"
        and manifest.get("protocol_sha256") == file_sha256(PROTOCOL_PATH)
        and manifest.get("implementation_freeze_sha256")
        == file_sha256(IMPLEMENTATION_FREEZE_PATH)
    ):
        raise Campaign298Error("candidate manifest semantics changed")
    key_parts: list[np.ndarray] = []
    value_parts: list[np.ndarray] = []
    eligible_parts: list[np.ndarray] = []
    by_year: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    digest_rows: list[list[Any]] = []
    for year in YEARS:
        record = record_for_year(manifest, year)
        path = resolve_record(CANDIDATE_MANIFEST_PATH, record)
        require_file(path, str(record["sha256"]), f"candidate partition {year}")
        frame = pd.read_parquet(
            path,
            columns=["stock_day_key", FACTOR_NAME, f"{FACTOR_NAME}_eligible"],
        )
        keys = frame["stock_day_key"].to_numpy(dtype=np.int64)
        values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce").to_numpy(
            dtype=np.float64
        )
        eligible = frame[f"{FACTOR_NAME}_eligible"].to_numpy(dtype=bool)
        values[~eligible] = np.nan
        key_parts.append(keys)
        value_parts.append(values)
        eligible_parts.append(eligible)
        by_year[year] = (keys, values)
        digest_rows.append([year, record["sha256"], len(frame), int(eligible.sum())])
    if canonical_sha256(digest_rows) != manifest.get("dataset_sha256"):
        raise Campaign298Error("candidate dataset digest changed")
    keys = np.concatenate(key_parts)
    values = np.concatenate(value_parts)
    eligible = np.concatenate(eligible_parts)
    if len(np.unique(keys)) != len(keys) or np.any(keys[1:] < keys[:-1]):
        raise Campaign298Error("candidate snapshot key order changed")
    return keys, values, eligible, by_year


def comparison_definitions(numeric_manifest: Mapping[str, Any]) -> list[str]:
    definitions = prior.comparison_definitions(numeric_manifest)
    definitions.append(CAMPAIGN297_FACTOR)
    if len(definitions) != EXPECTED_COMPARATOR_COUNT:
        raise Campaign298Error("comparator name order changed")
    observed = canonical_sha256(
        [
            [
                name,
                "lower" if name == LOWER_DIRECTION_COMPARATOR else "higher",
            ]
            for name in definitions
        ]
    )
    if observed != EXPECTED_COMPARATOR_ORDER_SHA256:
        raise Campaign298Error("comparator order digest changed")
    return definitions


def candidate_snapshot_comparison(
    *,
    manifest_path: Path,
    factor: str,
    source: str,
    candidate_by_year: Mapping[int, tuple[np.ndarray, np.ndarray]],
    minimum: float | None,
    maximum: float | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = load_json(manifest_path)
    rows: list[list[Any]] = []
    source_rows = 0
    eligible_rows = 0
    for year in YEARS:
        record = record_for_year(manifest, year)
        path = resolve_record(manifest_path, record)
        require_file(path, str(record["sha256"]), f"{factor} source {year}")
        frame = pd.read_parquet(
            path, columns=["stock_day_key", factor, f"{factor}_eligible"]
        )
        source_keys = frame["stock_day_key"].to_numpy(dtype=np.int64)
        values = pd.to_numeric(frame[factor], errors="coerce").to_numpy(
            dtype=np.float64
        )
        eligible = frame[f"{factor}_eligible"].to_numpy(dtype=bool)
        values[~eligible] = np.nan
        candidate_keys, candidate_values = candidate_by_year[year]
        if not np.array_equal(source_keys, candidate_keys):
            raise Campaign298Error(f"{factor} candidate alignment changed: {year}")
        finite = values[np.isfinite(values)]
        if finite.size and minimum is not None and (finite < minimum).any():
            raise Campaign298Error(f"{factor} comparator minimum changed")
        if finite.size and maximum is not None and (finite > maximum).any():
            raise Campaign298Error(f"{factor} comparator maximum changed")
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
        "frozen_minimum": minimum,
        "frozen_maximum": maximum,
    }
    return result, receipt


def run_ordered_uniqueness(
    *, numeric_manifest: Mapping[str, Any], candidate_manifest: Mapping[str, Any]
) -> dict[str, Any]:
    candidate_keys, candidate_values, _, candidate_by_year = load_candidate_snapshot(
        candidate_manifest
    )
    definitions = comparison_definitions(numeric_manifest)
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
            definitions[140],
            0.0,
            None,
            "campaign136_verified_snapshot",
        ),
        (
            C146_MANIFEST_PATH,
            definitions[141],
            -1.0,
            1.0,
            "campaign146_verified_snapshot",
        ),
        (
            C263_MANIFEST_PATH,
            definitions[142],
            0.0,
            1.0,
            "campaign263_verified_snapshot",
        ),
    ]
    if failed_ordinal is None:
        for ordinal, (path, factor, minimum, maximum, source) in enumerate(
            snapshot_specs, start=141
        ):
            aligned, receipt = base.fill_snapshot_aligned(
                manifest_path=path,
                manifest=load_json(path),
                factor=factor,
                candidate_keys=candidate_keys,
                minimum=minimum,
                maximum=maximum,
            )
            result = base.comparison_result(
                factor,
                base.daily_rank_rows(candidate_keys, candidate_values, aligned),
                source,
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
            del aligned
            gc.collect()
    prior_specs = [
        (
            C290_MANIFEST_PATH,
            CAMPAIGN290_FACTOR,
            "campaign290_verified_candidate_snapshot",
            0.0,
            1.0,
        ),
        (
            C291_MANIFEST_PATH,
            CAMPAIGN291_FACTOR,
            "campaign291_verified_candidate_snapshot",
            0.0,
            1.0,
        ),
        (
            C292_MANIFEST_PATH,
            CAMPAIGN292_FACTOR,
            "campaign292_verified_candidate_snapshot",
            0.0,
            1.0,
        ),
        (
            C293_MANIFEST_PATH,
            CAMPAIGN293_FACTOR,
            "campaign293_verified_candidate_snapshot",
            0.0,
            1.0,
        ),
        (
            C295_MANIFEST_PATH,
            CAMPAIGN295_FACTOR,
            "campaign295_verified_candidate_snapshot",
            -1.0,
            1.0,
        ),
        (
            C296_MANIFEST_PATH,
            CAMPAIGN296_FACTOR,
            "campaign296_verified_candidate_snapshot",
            None,
            None,
        ),
        (
            C297_MANIFEST_PATH,
            CAMPAIGN297_FACTOR,
            "campaign297_verified_candidate_snapshot",
            0.0,
            1.000001,
        ),
    ]
    if failed_ordinal is None:
        for ordinal, (manifest_path, factor, source, minimum, maximum) in enumerate(
            prior_specs, start=144
        ):
            result, receipt = candidate_snapshot_comparison(
                manifest_path=manifest_path,
                factor=factor,
                source=source,
                candidate_by_year=candidate_by_year,
                minimum=minimum,
                maximum=maximum,
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
    all_passed = failed_ordinal is None and len(results) == EXPECTED_COMPARATOR_COUNT
    return {
        "status": (
            "all_150_uniqueness_gates_passed"
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
        "all_150_passed": all_passed,
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
                "decision": item["decision"],
                "parameters": item.get("parameters"),
                "reason": item["reason"],
                "candidate_values_read": False,
                "comparator_values_read": False,
                "historical_daily_price_or_forward_return_values_read": False,
            }
        )
    failure = load_json(PREFREEZE_FAILURE_PATH)
    entries.append(
        {
            "attempt_id": failure["attempt_id"],
            "phase": failure["phase"],
            "name": "prefreeze_black_format_check",
            "decision": failure["status"],
            "error_type": failure["error_type"],
            "error_summary": failure["error_summary"],
            "failure_record_sha256": file_sha256(PREFREEZE_FAILURE_PATH),
            "candidate_values_read": False,
            "comparator_values_read": False,
            "historical_daily_price_or_forward_return_values_read": False,
        }
    )
    preplan_failure = load_json(PREPLAN_FAILURE_PATH)
    entries.append(
        {
            "attempt_id": preplan_failure["attempt_id"],
            "phase": preplan_failure["phase"],
            "name": "preplan_recursive_value_read_risk",
            "decision": preplan_failure["status"],
            "error_type": preplan_failure["error_type"],
            "error_summary": preplan_failure["error_summary"],
            "failure_record_sha256": file_sha256(PREPLAN_FAILURE_PATH),
            "candidate_values_read": False,
            "comparator_values_read": False,
            "historical_daily_price_or_forward_return_values_read": False,
        }
    )
    entries.append(
        {
            "attempt_id": "campaign298_factor_001",
            "phase": "coverage_uniqueness_and_conditional_development",
            "name": FACTOR_NAME,
            "formula": "VSTD20 / VMA20",
            "direction": "higher",
            "parameters": {
                "fixed_horizon_sessions": 20,
                "fit": "none",
            },
            "coverage_gate_passed": no_return["coverage"]["gate_passed"],
            "uniqueness_status": (no_return.get("ordered_uniqueness") or {}).get(
                "status"
            ),
            "historical_forward_return_values_read": terminal[
                "development_return_values_read"
            ],
            "outcome": terminal["status"],
        }
    )
    chained = chain_entries(entries)
    ledger = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign298_terminal_trial_ledger",
        "status": "append_only_terminal_chain",
        "created_at": base.utc_now(),
        "entry_count": len(chained),
        "genesis_sha256": CHAIN_GENESIS,
        "entries": chained,
        "terminal_entry_sha256": chained[-1]["entry_sha256"],
        "prevalue_concept_attempt_count": len(
            concept["finite_prevalue_concept_catalog"]
        ),
        "infrastructure_failure_count": 2,
        "complete_factor_attempt_count": 1,
        "record_every_formula_direction_parameter_filter_subset_model_combination_and_failure": True,
    }
    atomic_json(TRIAL_LEDGER_PATH, ledger)
    return ledger


def verify_source_files(alpha: Mapping[str, Any], numeric: Mapping[str, Any]) -> None:
    prior.verify_source_files(alpha, numeric)
    comparison_definitions(numeric)
    required = {
        "stock_day_key",
        VOLUME_STD_FEATURE,
        VOLUME_MEAN_FEATURE,
        "finite_feature_count",
        "feature_support_eligible",
        "quality_listing_eligible",
        "model_support_eligible",
    }
    for year in YEARS:
        record = record_for_year(alpha, year)
        path = resolve_record(ALPHA158_MANIFEST_PATH, record)
        if not required.issubset(pq.read_schema(path).names):
            raise Campaign298Error(
                f"Alpha158 required partition schema changed: {year}"
            )


def coverage_result(
    keys: np.ndarray,
    values: np.ndarray,
    eligible: np.ndarray,
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    source = protocol.get("coverage_and_capacity_gates") or {}
    gate = {
        "domain": source.get("domain"),
        "holding_period_sessions": 3,
        "median_daily_coverage_minimum": source.get("median_daily_coverage_minimum"),
        "p05_daily_coverage_minimum": source.get("p05_daily_coverage_minimum"),
        "p05_eligible_equity_count_minimum": source.get("p05_eligible_names_minimum"),
        "non_overlapping_three_signal_session_cohorts_minimum": source.get(
            "non_overlapping_three_signal_session_cohorts_minimum"
        ),
        "observed_calendar_years_minimum": source.get("cohort_years_minimum"),
        "must_pass_before_comparator_values": source.get(
            "coverage_failure_stops_before_every_comparator_value"
        ),
    }
    expected = {
        "domain": source.get("domain"),
        "holding_period_sessions": 3,
        "median_daily_coverage_minimum": 0.95,
        "p05_daily_coverage_minimum": 0.9,
        "p05_eligible_equity_count_minimum": 50,
        "non_overlapping_three_signal_session_cohorts_minimum": 200,
        "observed_calendar_years_minimum": 5,
        "must_pass_before_comparator_values": True,
    }
    if gate != expected:
        raise Campaign298Error("coverage key mapping or threshold changed")
    return base.coverage_result(keys, values, eligible, {"coverage_first_gate": gate})


def run_campaign(*, batch_size: int) -> dict[str, Any]:
    if batch_size != 8192:
        raise Campaign298Error("Campaign298 batch size changed")
    protocol, alpha, numeric = validate_protocol()
    validate_implementation_freeze()
    verify_source_files(alpha, numeric)
    if OUTPUT_ROOT.exists():
        raise Campaign298Error(
            "Campaign298 output root already exists; refuse overwrite"
        )
    candidate_manifest = build_candidate_snapshot(alpha)
    keys, values, eligible, _ = load_candidate_snapshot(candidate_manifest)
    coverage = coverage_result(keys, values, eligible, protocol)
    uniqueness = None
    if coverage["gate_passed"]:
        uniqueness = run_ordered_uniqueness(
            numeric_manifest=numeric, candidate_manifest=candidate_manifest
        )
    all_unique = bool(uniqueness and uniqueness["all_150_passed"])
    no_return = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign298_no_return_audit",
        "status": (
            "passed_ready_for_exact_one_no_fit_development_trial"
            if all_unique
            else "failed_closed_before_historical_daily_price_or_forward_return_values"
        ),
        "created_at": base.utc_now(),
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "implementation_freeze_sha256": file_sha256(IMPLEMENTATION_FREEZE_PATH),
        "candidate_manifest": {
            "path": str(CANDIDATE_MANIFEST_PATH),
            "sha256": file_sha256(CANDIDATE_MANIFEST_PATH),
            "dataset_sha256": candidate_manifest["dataset_sha256"],
        },
        "coverage": coverage,
        "ordered_uniqueness": uniqueness,
        "alpha158_feature_values_read": True,
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
            binding_path = (
                OUTPUT_ROOT / f"fold_{fold['fold']}_prevalidation_scores.json"
            )
            binding = {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign298_prevalidation_scores",
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
        "kind": "a_share_three_day_walkforward_campaign298_terminal_result",
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
        "prior_definition_count": 169,
        "prior_numeric_comparator_count": 150,
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
    load_candidate_snapshot(manifest)
    previous = CHAIN_GENESIS
    for ordinal, entry in enumerate(ledger.get("entries", []), start=1):
        body = dict(entry)
        observed = str(body.pop("entry_sha256"))
        if not (
            int(body.get("ordinal", 0)) == ordinal
            and body.get("previous_entry_sha256") == previous
            and canonical_sha256(body) == observed
        ):
            raise Campaign298Error("terminal trial ledger chain changed")
        previous = observed
    if not (
        terminal.get("kind")
        == "a_share_three_day_walkforward_campaign298_terminal_result"
        and terminal.get("lockbox_2024_2025_returns_open") is False
        and terminal.get("candidate49_ledgers_changed") is False
        and (terminal.get("no_return_audit") or {}).get("sha256")
        == file_sha256(NO_RETURN_PATH)
        and (terminal.get("terminal_trial_ledger") or {}).get("sha256")
        == file_sha256(TRIAL_LEDGER_PATH)
        and ledger.get("terminal_entry_sha256") == previous
        and ledger.get("infrastructure_failure_count") == 2
        and no_return.get("historical_daily_price_or_forward_return_values_read")
        is False
        and file_sha256(SIGNAL_LEDGER_PATH)
        == terminal.get("candidate49_signal_ledger_sha256")
        and file_sha256(EXECUTION_LEDGER_PATH)
        == terminal.get("candidate49_execution_ledger_sha256")
    ):
        raise Campaign298Error("Campaign298 terminal semantics changed")
    return {
        "status": "verified_campaign298_terminal",
        "survivor_count": terminal["survivor_count"],
        "validation_fold_count": terminal["validation_fold_count"],
        "no_return_status": no_return["status"],
        "trial_ledger_entries": ledger["entry_count"],
        "definition_library_append_eligible": terminal[
            "definition_library_append_eligible"
        ],
        "lockbox_2024_2025_returns_open": False,
        "candidate49_ledgers_changed": False,
    }


def plan() -> dict[str, Any]:
    _, alpha, numeric = validate_protocol()
    validate_implementation_freeze()
    schemas = []
    for manifest_path, manifest, label in (
        (ALPHA158_MANIFEST_PATH, alpha, "alpha158"),
        (NUMERIC140_MANIFEST_PATH, numeric, "numeric140"),
    ):
        for year in YEARS:
            record = record_for_year(manifest, year)
            path = resolve_record(manifest_path, record)
            if not path.is_file():
                raise Campaign298Error(f"{label} annual partition missing: {year}")
            schemas.append(
                {
                    "source": label,
                    "year": year,
                    "columns": len(pq.read_schema(path).names),
                }
            )
    comparison_definitions(numeric)
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
        "credential_value_or_digest_read": False,
        "candidate49_ledgers_changed": False,
        "trial_id": TRIAL_ID,
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
            raise Campaign298Error("run requires --confirm-run")
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
