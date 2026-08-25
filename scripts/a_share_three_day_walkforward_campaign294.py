#!/usr/bin/env python3
"""Run Campaign294's frozen Alpha158 cross-family consensus campaign."""

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

from scripts import a_share_three_day_walkforward_campaign293 as prior


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_V1_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_294_preregistration_20260825.json"
)
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_294_preregistration_v2_20260825.json"
)
ORIGINAL_IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_294_implementation_freeze_20260825.json"
)
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_294_implementation_freeze_v2_20260825.json"
)
CONCEPT_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_294_concept_scouting_20260825.json"
)
IMPORT_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_294_source_repository_import_context_failure_20260825.json"
)
PROTOCOL_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_294_preregistration_source_hash_failure_20260825.json"
)
UNIQUENESS_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_294_prior_comparator_function_reference_failure_20260825.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign294.py"
)

ALPHA158_MANIFEST_PATH = prior.ALPHA158_MANIFEST_PATH
NUMERIC140_MANIFEST_PATH = prior.NUMERIC140_MANIFEST_PATH
C136_MANIFEST_PATH = prior.C136_MANIFEST_PATH
C146_MANIFEST_PATH = prior.C146_MANIFEST_PATH
C263_MANIFEST_PATH = prior.C263_MANIFEST_PATH
C290_MANIFEST_PATH = prior.C290_MANIFEST_PATH
C291_MANIFEST_PATH = prior.C291_MANIFEST_PATH
C292_MANIFEST_PATH = prior.C292_MANIFEST_PATH
C293_MANIFEST_PATH = prior.CANDIDATE_MANIFEST_PATH
SIGNAL_LEDGER_PATH = prior.SIGNAL_LEDGER_PATH
EXECUTION_LEDGER_PATH = prior.EXECUTION_LEDGER_PATH

OUTPUT_ROOT = (
    REPO_ROOT
    / ".local-research/campaign_294/"
    "alpha158_same_horizon_cross_family_peer_rank_consensus_v2"
)
CANDIDATE_ROOT = OUTPUT_ROOT / "candidate_snapshot"
CANDIDATE_MANIFEST_PATH = CANDIDATE_ROOT / "snapshot_manifest.json"
NO_RETURN_PATH = OUTPUT_ROOT / "no_return_audit.json"
TERMINAL_RESULT_PATH = OUTPUT_ROOT / "terminal_result.json"
TRIAL_LEDGER_PATH = OUTPUT_ROOT / "terminal_trial_ledger.json"

FACTOR_NAME = "alpha158_same_horizon_cross_family_peer_rank_consensus_5h"
TRIAL_ID = (
    "wf294_alpha158_same_horizon_cross_family_peer_rank_consensus_5h_single_higher"
)
CAMPAIGN290_FACTOR = prior.CAMPAIGN290_FACTOR
CAMPAIGN291_FACTOR = prior.CAMPAIGN291_FACTOR
CAMPAIGN292_FACTOR = prior.CAMPAIGN292_FACTOR
CAMPAIGN293_FACTOR = prior.FACTOR_NAME
FEATURE_COUNT = 158
MINIMUM_ALPHA158_FINITE_FEATURES = 119
FAMILY_PREFIXES = prior.FAMILY_PREFIXES
HORIZONS = prior.HORIZONS
MINIMUM_FINITE_FAMILIES_PER_HORIZON = 22
EXPECTED_COMPARATOR_COUNT = 147
EXPECTED_COMPARATOR_ORDER_SHA256 = (
    "5a771c4f9bd028b352194ec4779acb15b38ab6ab23a935458660b2024c7914c1"
)
MINIMUM_PAIRWISE_NAMES = 50
MINIMUM_PAIRWISE_SESSIONS = 100
MAXIMUM_ABSOLUTE_MEDIAN_CORRELATION = 0.8
YEARS = tuple(range(2019, 2024))
PURGE_SIGNAL_SESSIONS = 3
CHAIN_GENESIS = "0" * 64

base = prior.prior.base
file_sha256 = prior.file_sha256
canonical_sha256 = prior.canonical_sha256
atomic_json = prior.atomic_json
atomic_parquet = prior.atomic_parquet
resolve_record = prior.resolve_record
record_for_year = prior.record_for_year


class Campaign294Error(RuntimeError):
    """Fail closed when a frozen Campaign294 invariant changes."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Campaign294Error(f"JSON binding unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise Campaign294Error(f"JSON binding is not an object: {path}")
    return value


def require_file(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or file_sha256(path) != expected:
        raise Campaign294Error(f"{label} fingerprint changed")


def horizon_indices(feature_names: Sequence[str]) -> np.ndarray:
    positions = {name: index for index, name in enumerate(feature_names)}
    groups = [
        [f"{prefix}{horizon}" for prefix in FAMILY_PREFIXES]
        for horizon in HORIZONS
    ]
    if any(name not in positions for group in groups for name in group):
        raise Campaign294Error("Alpha158 cross-family horizon inventory changed")
    indices = np.asarray([[positions[name] for name in group] for group in groups])
    if indices.shape != (5, 29) or len(np.unique(indices)) != 145:
        raise Campaign294Error("Alpha158 horizon-family coordinates changed")
    return indices


def effective_protocol() -> dict[str, Any]:
    correction = load_json(PROTOCOL_PATH)
    base_binding = correction.get("base_protocol") or {}
    failure_binding = correction.get("failure_record") or {}
    override = correction.get("exact_override") or {}
    if not (
        correction.get("kind")
        == "a_share_three_day_walkforward_campaign294_preregistration_v2_correction"
        and correction.get("status")
        == "fully_frozen_exact_single_source_hash_correction_before_campaign294_values"
        and base_binding.get("path") == str(PROTOCOL_V1_PATH.relative_to(REPO_ROOT))
        and base_binding.get("sha256") == file_sha256(PROTOCOL_V1_PATH)
        and base_binding.get("preserved_without_rewriting") is True
        and failure_binding.get("path")
        == str(PROTOCOL_FAILURE_PATH.relative_to(REPO_ROOT))
        and failure_binding.get("sha256") == file_sha256(PROTOCOL_FAILURE_PATH)
        and override.get("json_pointer")
        == "/source_bindings/campaign292_snapshot/dataset_sha256"
        and override.get("invalid_v1_value")
        == "f5e57256d4b794b6ef899844048a09cc522a085008d0f0370"
        and override.get("correct_value")
        == "f5e57256d4b794b6efeee9a56ea86d4ef399844048a09cc522a085008d0f0370"
        and correction.get("all_other_base_protocol_fields_and_order_preserved")
        is True
    ):
        raise Campaign294Error("Campaign294 protocol correction changed")
    protocol = load_json(PROTOCOL_V1_PATH)
    observed = protocol["source_bindings"]["campaign292_snapshot"][
        "dataset_sha256"
    ]
    if observed != override["invalid_v1_value"]:
        raise Campaign294Error("Campaign294 invalid v1 protocol evidence changed")
    protocol["source_bindings"]["campaign292_snapshot"]["dataset_sha256"] = (
        override["correct_value"]
    )
    return protocol


def validate_protocol() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    protocol = effective_protocol()
    factor = (protocol.get("factor_library") or [{}])[0]
    parameters = factor.get("parameters") or {}
    uniqueness = protocol.get("ordered_numeric_uniqueness") or {}
    development = protocol.get("development_trial") or {}
    boundary = protocol.get("research_boundary") or {}
    if not (
        protocol.get("kind") == "a_share_three_day_walkforward_campaign294_preregistration"
        and protocol.get("status")
        == "fully_frozen_before_campaign294_candidate_comparator_daily_price_or_forward_return_values"
        and len(protocol.get("factor_library") or []) == 1
        and factor.get("name") == FACTOR_NAME
        and factor.get("direction") == "higher"
        and parameters.get("family_count") == len(FAMILY_PREFIXES)
        and parameters.get("ordered_family_prefixes") == list(FAMILY_PREFIXES)
        and parameters.get("ordered_horizons") == list(HORIZONS)
        and parameters.get("minimum_finite_families_per_horizon")
        == MINIMUM_FINITE_FAMILIES_PER_HORIZON
        and parameters.get("required_supported_horizons") == len(HORIZONS)
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
        and uniqueness.get("all_147_must_pass") is True
        and development.get("trial_id") == TRIAL_ID
        and development.get("model_fitting") is False
        and development.get("training_return_reads") == 0
        and development.get("purge_signal_sessions") == PURGE_SIGNAL_SESSIONS
        and len(development.get("walkforward_folds") or []) == 3
        and boundary.get("campaign294_candidate_or_comparator_values_read_before_protocol")
        is False
        and boundary.get("historical_daily_price_or_forward_return_values_read_before_protocol")
        is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("credential_loaded") is False
    ):
        raise Campaign294Error("Campaign294 protocol semantics changed")
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
    ):
        raise Campaign294Error("Campaign294 source manifest semantics changed")
    horizon_indices(list(alpha["feature_names"]))
    for label, path, factor_name in (
        ("Campaign290", C290_MANIFEST_PATH, CAMPAIGN290_FACTOR),
        ("Campaign291", C291_MANIFEST_PATH, CAMPAIGN291_FACTOR),
        ("Campaign292", C292_MANIFEST_PATH, CAMPAIGN292_FACTOR),
        ("Campaign293", C293_MANIFEST_PATH, CAMPAIGN293_FACTOR),
    ):
        manifest = load_json(path)
        if not (
            manifest.get("factor_name") == factor_name
            and manifest.get("direction") == "higher"
            and [int(item["year"]) for item in manifest.get("files", [])]
            == list(YEARS)
            and manifest.get("dataset_sha256")
            == protocol["source_bindings"][f"campaign{label[-3:]}_snapshot"][
                "dataset_sha256"
            ]
        ):
            raise Campaign294Error(f"{label} comparator semantics changed")
    return protocol, alpha, numeric


def validate_implementation_freeze() -> dict[str, Any]:
    freeze = load_json(IMPLEMENTATION_FREEZE_PATH)
    frozen = freeze.get("frozen_implementation") or {}
    boundary = freeze.get("research_boundary") or {}
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign294_implementation_freeze_v2"
        and freeze.get("status")
        == "scientifically_identical_helper_reference_refrozen_before_v2_return_values"
        and frozen.get("protocol_v1_sha256") == file_sha256(PROTOCOL_V1_PATH)
        and frozen.get("protocol_v2_sha256") == file_sha256(PROTOCOL_PATH)
        and frozen.get("runner_sha256") == file_sha256(Path(__file__).resolve())
        and frozen.get("test_sha256") == file_sha256(TEST_PATH)
        and frozen.get("runner_dependency_sha256")
        == file_sha256(Path(prior.__file__).resolve())
        and frozen.get("original_implementation_freeze_sha256")
        == file_sha256(ORIGINAL_IMPLEMENTATION_FREEZE_PATH)
        and frozen.get("uniqueness_failure_sha256")
        == file_sha256(UNIQUENESS_FAILURE_PATH)
        and frozen.get("scientific_semantics_changed") is False
        and frozen.get("factor_name") == FACTOR_NAME
        and frozen.get("minimum_finite_families_per_horizon")
        == MINIMUM_FINITE_FAMILIES_PER_HORIZON
        and frozen.get("comparator_count") == EXPECTED_COMPARATOR_COUNT
        and frozen.get("comparator_order_sha256")
        == EXPECTED_COMPARATOR_ORDER_SHA256
        and boundary.get("v1_candidate_values_read_before_v2_freeze") is True
        and boundary.get("v1_comparator_values_read_before_v2_freeze") is True
        and boundary.get("historical_daily_price_or_forward_return_values_read_before_v2_freeze")
        is False
        and boundary.get("provider_credential_loaded") is False
    ):
        raise Campaign294Error("Campaign294 implementation freeze changed")
    return freeze


def session_cross_family_consensus(
    *,
    keys: np.ndarray,
    matrix: np.ndarray,
    finite_count: np.ndarray,
    feature_support: np.ndarray,
    quality_listing: np.ndarray,
    model_support: np.ndarray,
    groups: np.ndarray,
) -> pd.DataFrame:
    keys = np.asarray(keys, dtype=np.int64)
    matrix = np.asarray(matrix, dtype=np.float32)
    finite_count = np.asarray(finite_count, dtype=np.uint8)
    feature_support = np.asarray(feature_support, dtype=bool)
    quality_listing = np.asarray(quality_listing, dtype=bool)
    model_support = np.asarray(model_support, dtype=bool)
    groups = np.asarray(groups, dtype=np.int64)
    observed = np.isfinite(matrix).sum(axis=1).astype(np.uint8)
    if not (
        matrix.shape == (len(keys), FEATURE_COUNT)
        and groups.shape == (len(HORIZONS), len(FAMILY_PREFIXES))
        and np.array_equal(observed, finite_count)
        and np.array_equal(
            feature_support, observed >= MINIMUM_ALPHA158_FINITE_FEATURES
        )
        and np.all(~model_support | (feature_support & quality_listing))
        and len(np.unique(keys)) == len(keys)
    ):
        raise Campaign294Error("Alpha158 session support semantics changed")
    score_by_row = np.full(len(keys), np.nan, dtype=np.float64)
    minimum_count_by_row = np.zeros(len(keys), dtype=np.uint8)
    supported = matrix[model_support]
    if len(supported):
        percentiles = np.full(supported.shape, np.nan, dtype=np.float32)
        for column in np.unique(groups):
            finite = np.isfinite(supported[:, column])
            count = int(finite.sum())
            if count:
                ranks = rankdata(supported[finite, column], method="average")
                percentiles[finite, column] = (ranks - 0.5) / count
        values = percentiles[:, groups]
        counts = np.isfinite(values).sum(axis=2)
        variances = np.full((len(supported), len(HORIZONS)), np.nan)
        for horizon_index in range(len(HORIZONS)):
            horizon_values = values[:, horizon_index, :]
            finite = np.isfinite(horizon_values)
            count = counts[:, horizon_index]
            sums = np.nansum(horizon_values, axis=1)
            means = np.divide(
                sums,
                count,
                out=np.zeros(len(supported), dtype=np.float64),
                where=count > 0,
            )
            centered = np.where(finite, horizon_values - means[:, None], 0.0)
            variances[:, horizon_index] = np.divide(
                np.sum(centered * centered, axis=1),
                count,
                out=np.full(len(supported), np.nan),
                where=count > 0,
            )
        valid = np.all(counts >= MINIMUM_FINITE_FAMILIES_PER_HORIZON, axis=1)
        supported_scores = np.full(len(supported), np.nan, dtype=np.float64)
        supported_scores[valid] = 1.0 - 4.0 * np.mean(variances[valid], axis=1)
        score_by_row[model_support] = supported_scores
        minimum_count_by_row[model_support] = counts.min(axis=1).astype(np.uint8)
    selected = np.flatnonzero(quality_listing)
    scores = score_by_row[selected]
    minimum_counts = minimum_count_by_row[selected]
    eligible = (
        model_support[selected]
        & (minimum_counts >= MINIMUM_FINITE_FAMILIES_PER_HORIZON)
        & np.isfinite(scores)
        & (scores >= 0.0)
        & (scores <= 1.0)
    )
    return pd.DataFrame(
        {
            "stock_day_key": keys[selected],
            FACTOR_NAME: scores,
            "minimum_finite_family_count_across_horizons": minimum_counts,
            f"{FACTOR_NAME}_eligible": eligible,
            "quality_listing_eligible": np.ones(len(selected), dtype=bool),
            "model_support_eligible": model_support[selected],
        }
    )


def build_candidate_snapshot(alpha: Mapping[str, Any]) -> dict[str, Any]:
    if CANDIDATE_ROOT.exists():
        raise Campaign294Error("candidate output root already exists; refuse overwrite")
    feature_names = list(alpha["feature_names"])
    groups = horizon_indices(feature_names)
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
        "minimum_family_count_minimum_eligible": len(FAMILY_PREFIXES),
        "minimum_family_count_maximum_eligible": 0,
    }
    for year in YEARS:
        source_record = record_for_year(alpha, year)
        source_path = resolve_record(ALPHA158_MANIFEST_PATH, source_record)
        parts: list[pd.DataFrame] = []
        observed_sessions = 0
        for _, frame in base.iter_session_frames(source_path, columns):
            parts.append(
                session_cross_family_consensus(
                    keys=frame["stock_day_key"].to_numpy(dtype=np.int64),
                    matrix=frame[feature_names].to_numpy(dtype=np.float32, copy=True),
                    finite_count=frame["finite_feature_count"].to_numpy(dtype=np.uint8),
                    feature_support=frame["feature_support_eligible"].to_numpy(dtype=bool),
                    quality_listing=frame["quality_listing_eligible"].to_numpy(dtype=bool),
                    model_support=frame["model_support_eligible"].to_numpy(dtype=bool),
                    groups=groups,
                )
            )
            observed_sessions += 1
        annual = pd.concat(parts, ignore_index=True)
        if len(np.unique(annual["stock_day_key"])) != len(annual):
            raise Campaign294Error(f"candidate annual keys duplicated: {year}")
        output_path = CANDIDATE_ROOT / "partitions" / f"{year}.parquet"
        atomic_parquet(output_path, annual)
        eligible = annual[f"{FACTOR_NAME}_eligible"].to_numpy(dtype=bool)
        counts = annual["minimum_finite_family_count_across_horizons"].to_numpy(
            dtype=np.uint8
        )
        totals["quality_listing_rows"] += len(annual)
        totals["candidate_eligible_rows"] += int(eligible.sum())
        if eligible.any():
            totals["minimum_family_count_minimum_eligible"] = min(
                totals["minimum_family_count_minimum_eligible"],
                int(counts[eligible].min()),
            )
            totals["minimum_family_count_maximum_eligible"] = max(
                totals["minimum_family_count_maximum_eligible"],
                int(counts[eligible].max()),
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
        raise Campaign294Error("candidate session counts changed")
    manifest = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign294_candidate_snapshot",
        "status": "immutable_candidate_ready_for_coverage_before_comparator_values",
        "created_at": base.utc_now(),
        "factor_name": FACTOR_NAME,
        "direction": "higher",
        "formula_parameters": {
            "family_count": len(FAMILY_PREFIXES),
            "ordered_horizons": list(HORIZONS),
            "minimum_finite_families_per_horizon": MINIMUM_FINITE_FAMILIES_PER_HORIZON,
            "required_supported_horizons": len(HORIZONS),
            "score": "1-4*mean per-horizon population variance across family peer percentiles",
        },
        "protocol_v1_sha256": file_sha256(PROTOCOL_V1_PATH),
        "protocol_v2_sha256": file_sha256(PROTOCOL_PATH),
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
    atomic_json(CANDIDATE_MANIFEST_PATH, manifest)
    return manifest


def load_candidate_snapshot(
    manifest: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[int, tuple[np.ndarray, np.ndarray]]]:
    key_parts: list[np.ndarray] = []
    value_parts: list[np.ndarray] = []
    eligible_parts: list[np.ndarray] = []
    by_year: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    for record in manifest.get("files", []):
        path = resolve_record(CANDIDATE_MANIFEST_PATH, record)
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
        ):
            raise Campaign294Error("candidate snapshot values changed")
        year = int(record["year"])
        by_year[year] = (keys, values)
        key_parts.append(keys)
        value_parts.append(values)
        eligible_parts.append(eligible)
    keys = np.concatenate(key_parts)
    values = np.concatenate(value_parts)
    eligible = np.concatenate(eligible_parts)
    if len(np.unique(keys)) != len(keys) or np.any(keys[1:] < keys[:-1]):
        raise Campaign294Error("candidate snapshot key order changed")
    return keys, values, eligible, by_year


def run_ordered_uniqueness(
    *, numeric_manifest: Mapping[str, Any], candidate_manifest: Mapping[str, Any]
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
            CAMPAIGN292_FACTOR,
            CAMPAIGN293_FACTOR,
        ]
    )
    if len(definitions) != EXPECTED_COMPARATOR_COUNT:
        raise Campaign294Error("comparator name order changed")
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
        (C136_MANIFEST_PATH, definitions[140], 0.0, None, "campaign136_verified_snapshot"),
        (C146_MANIFEST_PATH, definitions[141], -1.0, 1.0, "campaign146_verified_snapshot"),
        (C263_MANIFEST_PATH, definitions[142], 0.0, 1.0, "campaign263_verified_snapshot"),
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
                        "absolute_median": result["absolute_median_daily_rank_correlation"],
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
            (C290_MANIFEST_PATH, CAMPAIGN290_FACTOR, "campaign290_verified_candidate_snapshot"),
            (C291_MANIFEST_PATH, CAMPAIGN291_FACTOR, "campaign291_verified_candidate_snapshot"),
            (C292_MANIFEST_PATH, CAMPAIGN292_FACTOR, "campaign292_verified_candidate_snapshot"),
            (C293_MANIFEST_PATH, CAMPAIGN293_FACTOR, "campaign293_verified_candidate_snapshot"),
        ]
        for ordinal, (manifest_path, factor, source) in enumerate(
            prior_specs, start=144
        ):
            result, receipt = prior.prior.prior_campaign_comparison(
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
                        "absolute_median": result["absolute_median_daily_rank_correlation"],
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
            "all_147_uniqueness_gates_passed"
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
        "all_147_passed": all_passed,
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
    entries = [
        {
            "attempt_id": item["catalog_id"],
            "phase": "prevalue_concept_scouting",
            "name": item["name"],
            "outcome": item["decision"],
            "reason": item["reason"],
            "historical_forward_return_values_read": False,
        }
        for item in concept["finite_prevalue_concept_catalog"]
    ]
    for failure_path, name in (
        (IMPORT_FAILURE_PATH, "source_repository_import_context"),
        (PROTOCOL_FAILURE_PATH, "preregistration_source_hash_transcription"),
        (UNIQUENESS_FAILURE_PATH, "prior_comparator_function_reference"),
    ):
        failure = load_json(failure_path)
        entries.append(
            {
                "attempt_id": failure["attempt_id"],
                "phase": "infrastructure_failure",
                "name": name,
                "outcome": failure["status"],
                "failure_record_sha256": file_sha256(failure_path),
                "historical_forward_return_values_read": False,
            }
        )
    entries.append(
        {
            "attempt_id": "campaign294_factor_001",
            "phase": "coverage_uniqueness_and_development",
            "name": FACTOR_NAME,
            "formula": "One minus four times mean same-horizon cross-family peer-percentile population variance.",
            "direction": "higher",
            "parameters": {
                "family_count": len(FAMILY_PREFIXES),
                "ordered_horizons": list(HORIZONS),
                "minimum_finite_families_per_horizon": MINIMUM_FINITE_FAMILIES_PER_HORIZON,
                "fit": "none",
            },
            "coverage_gate_passed": no_return["coverage"]["gate_passed"],
            "uniqueness_status": (
                (no_return.get("ordered_uniqueness") or {}).get("status")
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
        "kind": "a_share_three_day_walkforward_campaign294_terminal_trial_ledger",
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


def verify_source_files(alpha: Mapping[str, Any], numeric: Mapping[str, Any]) -> None:
    prior.verify_source_files(alpha, numeric)
    manifest = load_json(C293_MANIFEST_PATH)
    for year in YEARS:
        record = record_for_year(manifest, year)
        path = resolve_record(C293_MANIFEST_PATH, record)
        require_file(path, str(record["sha256"]), f"Campaign293 partition {year}")
        required = {"stock_day_key", CAMPAIGN293_FACTOR, f"{CAMPAIGN293_FACTOR}_eligible"}
        if not required.issubset(pq.read_schema(path).names):
            raise Campaign294Error(f"Campaign293 partition schema changed: {year}")


def run_campaign(*, batch_size: int) -> dict[str, Any]:
    if batch_size != 8192:
        raise Campaign294Error("Campaign294 batch size changed")
    protocol, alpha, numeric = validate_protocol()
    validate_implementation_freeze()
    verify_source_files(alpha, numeric)
    if OUTPUT_ROOT.exists():
        raise Campaign294Error("Campaign294 output root already exists; refuse overwrite")
    candidate_manifest = build_candidate_snapshot(alpha)
    keys, values, eligible, _ = load_candidate_snapshot(candidate_manifest)
    coverage = base.coverage_result(keys, values, eligible, protocol)
    uniqueness = None
    if coverage["gate_passed"]:
        uniqueness = run_ordered_uniqueness(
            numeric_manifest=numeric, candidate_manifest=candidate_manifest
        )
    all_unique = bool(uniqueness and uniqueness["all_147_passed"])
    no_return = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign294_no_return_audit",
        "status": (
            "passed_ready_for_exact_one_no_fit_development_trial"
            if all_unique
            else "failed_closed_before_historical_daily_price_or_forward_return_values"
        ),
        "created_at": base.utc_now(),
        "protocol_v1_sha256": file_sha256(PROTOCOL_V1_PATH),
        "protocol_v2_sha256": file_sha256(PROTOCOL_PATH),
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
                "kind": "a_share_three_day_walkforward_campaign294_prevalidation_scores",
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
        "kind": "a_share_three_day_walkforward_campaign294_terminal_result",
        "status": (
            "development_survivor_frozen_lockbox_closed_pending_new_source_freeze"
            if survivor_count
            else "terminal_no_survivor_lockbox_closed"
        ),
        "created_at": base.utc_now(),
        "protocol_v1_sha256": file_sha256(PROTOCOL_V1_PATH),
        "protocol_v2_sha256": file_sha256(PROTOCOL_PATH),
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
        "prior_definition_count": 166,
        "prior_numeric_comparator_count": 147,
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
            raise Campaign294Error("terminal trial ledger chain changed")
        previous = observed
    if not (
        terminal.get("kind")
        == "a_share_three_day_walkforward_campaign294_terminal_result"
        and terminal.get("lockbox_2024_2025_returns_open") is False
        and terminal.get("candidate49_ledgers_changed") is False
        and (terminal.get("no_return_audit") or {}).get("sha256")
        == file_sha256(NO_RETURN_PATH)
        and (terminal.get("terminal_trial_ledger") or {}).get("sha256")
        == file_sha256(TRIAL_LEDGER_PATH)
        and ledger.get("terminal_entry_sha256") == previous
        and no_return.get("historical_daily_price_or_forward_return_values_read")
        is False
        and file_sha256(SIGNAL_LEDGER_PATH)
        == terminal.get("candidate49_signal_ledger_sha256")
        and file_sha256(EXECUTION_LEDGER_PATH)
        == terminal.get("candidate49_execution_ledger_sha256")
    ):
        raise Campaign294Error("Campaign294 terminal semantics changed")
    return {
        "status": "verified_campaign294_terminal",
        "survivor_count": terminal["survivor_count"],
        "validation_fold_count": terminal["validation_fold_count"],
        "no_return_status": no_return["status"],
        "trial_ledger_entries": ledger["entry_count"],
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
                raise Campaign294Error(f"{label} annual partition missing: {year}")
            schemas.append(
                {"source": label, "year": year, "columns": len(pq.read_schema(path).names)}
            )
    return {
        "ready": not OUTPUT_ROOT.exists(),
        "protocol_v1_sha256": file_sha256(PROTOCOL_V1_PATH),
        "protocol_v2_sha256": file_sha256(PROTOCOL_PATH),
        "implementation_freeze_present": IMPLEMENTATION_FREEZE_PATH.is_file(),
        "output_root_absent": not OUTPUT_ROOT.exists(),
        "source_schema_records": schemas,
        "candidate_values_read": False,
        "comparator_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
        "credential_loaded": False,
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
            raise Campaign294Error("run requires --confirm-run")
        print(
            json.dumps(
                run_campaign(batch_size=args.batch_size),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
        )
        return 0
    print(
        json.dumps(
            verify_terminal(), ensure_ascii=False, sort_keys=True, indent=2
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
