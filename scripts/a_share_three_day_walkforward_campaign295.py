#!/usr/bin/env python3
"""Run Campaign295's frozen Alpha158 price-volume confirmation campaign."""

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

from scripts import a_share_three_day_walkforward_campaign294 as prior


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_295_preregistration_20260825.json"
)
ORIGINAL_IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_295_implementation_freeze_20260825.json"
)
IMPLEMENTATION_FREEZE_V2_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_295_implementation_freeze_v2_20260825.json"
)
PREVIOUS_IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_295_implementation_freeze_v3_20260825.json"
)
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_295_implementation_freeze_v4_20260825.json"
)
CONCEPT_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_295_concept_scouting_20260825.json"
)
IMPORT_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_295_direct_script_import_context_failure_20260825.json"
)
PYTEST_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_295_pytest_import_context_failure_20260825.json"
)
COMPARATOR_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_295_prior_comparator_function_reference_failure_20260825.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign295.py"
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
SIGNAL_LEDGER_PATH = prior.SIGNAL_LEDGER_PATH
EXECUTION_LEDGER_PATH = prior.EXECUTION_LEDGER_PATH

OUTPUT_ROOT = (
    REPO_ROOT
    / ".local-research/campaign_295/"
    "alpha158_price_volume_directional_confirmation_20d_v2"
)
CANDIDATE_ROOT = OUTPUT_ROOT / "candidate_snapshot"
CANDIDATE_MANIFEST_PATH = CANDIDATE_ROOT / "snapshot_manifest.json"
NO_RETURN_PATH = OUTPUT_ROOT / "no_return_audit.json"
TERMINAL_RESULT_PATH = OUTPUT_ROOT / "terminal_result.json"
TRIAL_LEDGER_PATH = OUTPUT_ROOT / "terminal_trial_ledger.json"

FACTOR_NAME = "alpha158_price_volume_directional_confirmation_20d"
TRIAL_ID = "wf295_alpha158_price_volume_directional_confirmation_20d_single_higher"
PRICE_DIRECTION_FEATURE = "SUMD20"
CONFIRMATION_FEATURE = "CORD20"
INPUT_TOLERANCE = 1e-6
FEATURE_COUNT = 158
MINIMUM_ALPHA158_FINITE_FEATURES = 119
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

CAMPAIGN290_FACTOR = prior.CAMPAIGN290_FACTOR
CAMPAIGN291_FACTOR = prior.CAMPAIGN291_FACTOR
CAMPAIGN292_FACTOR = prior.CAMPAIGN292_FACTOR
CAMPAIGN293_FACTOR = prior.CAMPAIGN293_FACTOR

base = prior.base
file_sha256 = prior.file_sha256
canonical_sha256 = prior.canonical_sha256
atomic_json = prior.atomic_json
atomic_parquet = prior.atomic_parquet
resolve_record = prior.resolve_record
record_for_year = prior.record_for_year


class Campaign295Error(RuntimeError):
    """Fail closed when a frozen Campaign295 invariant changes."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Campaign295Error(f"JSON binding unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise Campaign295Error(f"JSON binding is not an object: {path}")
    return value


def require_file(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or file_sha256(path) != expected:
        raise Campaign295Error(f"{label} fingerprint changed")


def validate_protocol() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    _, alpha, numeric = prior.validate_protocol()
    prior.validate_implementation_freeze()
    protocol = load_json(PROTOCOL_PATH)
    factor = (protocol.get("factor_library") or [{}])[0]
    parameters = factor.get("parameters") or {}
    uniqueness = protocol.get("ordered_numeric_uniqueness") or {}
    development = protocol.get("development_trial") or {}
    boundary = protocol.get("research_boundary") or {}
    append_rule = protocol.get("append_rule") or {}
    if not (
        protocol.get("kind")
        == "a_share_three_day_walkforward_campaign295_preregistration"
        and protocol.get("status")
        == "fully_frozen_before_campaign295_candidate_comparator_daily_price_or_forward_return_values"
        and len(protocol.get("factor_library") or []) == 1
        and factor.get("name") == FACTOR_NAME
        and factor.get("direction") == "higher"
        and parameters.get("price_direction_feature") == PRICE_DIRECTION_FEATURE
        and parameters.get("price_volume_confirmation_feature")
        == CONFIRMATION_FEATURE
        and parameters.get("fixed_horizon_sessions") == 20
        and parameters.get("score") == "SUMD20 * (1 + CORD20) / 2"
        and float(parameters.get("input_numerical_tolerance")) == INPUT_TOLERANCE
        and parameters.get("fit") == "none"
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
        and append_rule.get("prior_library_counts")
        == {"complete_definitions": 166, "numeric_comparators": 147}
        and boundary.get("campaign295_candidate_or_comparator_values_read_before_protocol")
        is False
        and boundary.get("historical_daily_price_or_forward_return_values_read_before_protocol")
        is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("credential_loaded") is False
    ):
        raise Campaign295Error("Campaign295 protocol semantics changed")
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
    if not (
        candidate49.get("same_day_20260825_retry_allowed") is False
        and alpha.get("dataset_sha256")
        == protocol["source_bindings"]["alpha158_design"]["dataset_sha256"]
        and alpha.get("feature_count") == FEATURE_COUNT
        and len(alpha.get("feature_names") or []) == FEATURE_COUNT
        and PRICE_DIRECTION_FEATURE in alpha["feature_names"]
        and CONFIRMATION_FEATURE in alpha["feature_names"]
        and [int(item["year"]) for item in alpha.get("files", [])]
        == list(YEARS)
        and numeric.get("dataset_sha256")
        == protocol["source_bindings"]["numeric140_design"]["dataset_sha256"]
        and len(numeric.get("feature_names") or []) == 140
    ):
        raise Campaign295Error("Campaign295 source or Candidate49 semantics changed")
    return protocol, alpha, numeric


def validate_implementation_freeze() -> dict[str, Any]:
    freeze = load_json(IMPLEMENTATION_FREEZE_PATH)
    frozen = freeze.get("frozen_implementation") or {}
    boundary = freeze.get("research_boundary") or {}
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign295_implementation_freeze_v4"
        and freeze.get("status")
        == "scientifically_identical_comparator_helper_correction_refrozen_before_return_values"
        and frozen.get("protocol_sha256") == file_sha256(PROTOCOL_PATH)
        and frozen.get("runner_sha256") == file_sha256(Path(__file__).resolve())
        and frozen.get("test_sha256") == file_sha256(TEST_PATH)
        and frozen.get("runner_dependency_sha256")
        == file_sha256(Path(prior.__file__).resolve())
        and frozen.get("original_implementation_freeze_sha256")
        == file_sha256(ORIGINAL_IMPLEMENTATION_FREEZE_PATH)
        and frozen.get("implementation_freeze_v2_sha256")
        == file_sha256(IMPLEMENTATION_FREEZE_V2_PATH)
        and frozen.get("previous_implementation_freeze_sha256")
        == file_sha256(PREVIOUS_IMPLEMENTATION_FREEZE_PATH)
        and frozen.get("import_context_failure_sha256")
        == file_sha256(IMPORT_FAILURE_PATH)
        and frozen.get("pytest_import_context_failure_sha256")
        == file_sha256(PYTEST_FAILURE_PATH)
        and frozen.get("comparator_function_reference_failure_sha256")
        == file_sha256(COMPARATOR_FAILURE_PATH)
        and frozen.get("scientific_semantics_changed") is False
        and frozen.get("factor_name") == FACTOR_NAME
        and frozen.get("formula") == "SUMD20 * (1 + CORD20) / 2"
        and frozen.get("input_numerical_tolerance") == INPUT_TOLERANCE
        and frozen.get("comparator_count") == EXPECTED_COMPARATOR_COUNT
        and frozen.get("comparator_order_sha256")
        == EXPECTED_COMPARATOR_ORDER_SHA256
        and boundary.get("campaign295_candidate_values_read_before_freeze") is True
        and boundary.get("comparator_values_read_before_freeze") is True
        and boundary.get("historical_daily_price_or_forward_return_values_read_before_freeze")
        is False
        and boundary.get("provider_credential_loaded") is False
    ):
        raise Campaign295Error("Campaign295 implementation freeze changed")
    return freeze


def price_volume_directional_confirmation(
    *,
    keys: np.ndarray,
    sumd: np.ndarray,
    cord: np.ndarray,
    finite_count: np.ndarray,
    feature_support: np.ndarray,
    quality_listing: np.ndarray,
    model_support: np.ndarray,
) -> pd.DataFrame:
    keys = np.asarray(keys, dtype=np.int64)
    sumd = np.asarray(sumd, dtype=np.float64)
    cord = np.asarray(cord, dtype=np.float64)
    finite_count = np.asarray(finite_count, dtype=np.uint8)
    feature_support = np.asarray(feature_support, dtype=bool)
    quality_listing = np.asarray(quality_listing, dtype=bool)
    model_support = np.asarray(model_support, dtype=bool)
    if not (
        len(keys)
        == len(sumd)
        == len(cord)
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
        raise Campaign295Error("Alpha158 row support semantics changed")
    finite_inputs = np.isfinite(sumd) & np.isfinite(cord)
    bounded_inputs = (
        finite_inputs
        & (sumd >= -1.0 - INPUT_TOLERANCE)
        & (sumd <= 1.0 + INPUT_TOLERANCE)
        & (cord >= -1.0 - INPUT_TOLERANCE)
        & (cord <= 1.0 + INPUT_TOLERANCE)
    )
    score = np.full(len(keys), np.nan, dtype=np.float64)
    calculable = model_support & bounded_inputs
    score[calculable] = sumd[calculable] * (1.0 + cord[calculable]) / 2.0
    selected = np.flatnonzero(quality_listing)
    selected_scores = score[selected]
    input_counts = (
        np.isfinite(sumd[selected]).astype(np.uint8)
        + np.isfinite(cord[selected]).astype(np.uint8)
    )
    eligible = (
        model_support[selected]
        & bounded_inputs[selected]
        & np.isfinite(selected_scores)
        & (selected_scores >= -1.0 - INPUT_TOLERANCE)
        & (selected_scores <= 1.0 + INPUT_TOLERANCE)
    )
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
        raise Campaign295Error("candidate output root already exists; refuse overwrite")
    columns = [
        "stock_day_key",
        PRICE_DIRECTION_FEATURE,
        CONFIRMATION_FEATURE,
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
                price_volume_directional_confirmation(
                    keys=frame["stock_day_key"].to_numpy(dtype=np.int64),
                    sumd=frame[PRICE_DIRECTION_FEATURE].to_numpy(dtype=np.float64),
                    cord=frame[CONFIRMATION_FEATURE].to_numpy(dtype=np.float64),
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
            raise Campaign295Error(f"candidate annual keys duplicated: {year}")
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
        raise Campaign295Error("candidate session counts changed")
    manifest = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign295_candidate_snapshot",
        "status": "immutable_candidate_ready_for_coverage_before_comparator_values",
        "created_at": base.utc_now(),
        "factor_name": FACTOR_NAME,
        "direction": "higher",
        "formula_parameters": {
            "price_direction_feature": PRICE_DIRECTION_FEATURE,
            "price_volume_confirmation_feature": CONFIRMATION_FEATURE,
            "fixed_horizon_sessions": 20,
            "score": "SUMD20 * (1 + CORD20) / 2",
            "input_numerical_tolerance": INPUT_TOLERANCE,
            "fit": "none",
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
        "alpha158_feature_values_read": True,
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
            and np.all(values[eligible] >= -1.0 - INPUT_TOLERANCE)
            and np.all(values[eligible] <= 1.0 + INPUT_TOLERANCE)
        ):
            raise Campaign295Error("candidate snapshot values changed")
        year = int(record["year"])
        by_year[year] = (keys, values)
        key_parts.append(keys)
        value_parts.append(values)
        eligible_parts.append(eligible)
    keys = np.concatenate(key_parts)
    values = np.concatenate(value_parts)
    eligible = np.concatenate(eligible_parts)
    if len(np.unique(keys)) != len(keys) or np.any(keys[1:] < keys[:-1]):
        raise Campaign295Error("candidate snapshot key order changed")
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
        raise Campaign295Error("comparator name order changed")
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
            (C290_MANIFEST_PATH, CAMPAIGN290_FACTOR, "campaign290_verified_candidate_snapshot"),
            (C291_MANIFEST_PATH, CAMPAIGN291_FACTOR, "campaign291_verified_candidate_snapshot"),
            (C292_MANIFEST_PATH, CAMPAIGN292_FACTOR, "campaign292_verified_candidate_snapshot"),
            (C293_MANIFEST_PATH, CAMPAIGN293_FACTOR, "campaign293_verified_candidate_snapshot"),
        ]
        for ordinal, (manifest_path, factor, source) in enumerate(
            prior_specs, start=144
        ):
            result, receipt = prior.prior.prior.prior_campaign_comparison(
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
        (IMPORT_FAILURE_PATH, "direct_script_import_context"),
        (PYTEST_FAILURE_PATH, "pytest_console_import_context"),
        (COMPARATOR_FAILURE_PATH, "prior_comparator_function_reference"),
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
            "attempt_id": "campaign295_factor_001",
            "phase": "coverage_uniqueness_and_conditional_development",
            "name": FACTOR_NAME,
            "formula": "SUMD20 * (1 + CORD20) / 2",
            "direction": "higher",
            "parameters": {
                "fixed_horizon_sessions": 20,
                "input_numerical_tolerance": INPUT_TOLERANCE,
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
        "kind": "a_share_three_day_walkforward_campaign295_terminal_trial_ledger",
        "status": "append_only_terminal_chain",
        "created_at": base.utc_now(),
        "entry_count": len(chained),
        "genesis_sha256": CHAIN_GENESIS,
        "entries": chained,
        "terminal_entry_sha256": chained[-1]["entry_sha256"],
        "infrastructure_failure_count": 3,
        "record_every_formula_direction_parameter_filter_subset_model_and_failure": True,
    }
    atomic_json(TRIAL_LEDGER_PATH, ledger)
    return ledger


def verify_source_files(alpha: Mapping[str, Any], numeric: Mapping[str, Any]) -> None:
    prior.verify_source_files(alpha, numeric)
    for year in YEARS:
        record = record_for_year(alpha, year)
        path = resolve_record(ALPHA158_MANIFEST_PATH, record)
        required = {
            "stock_day_key",
            PRICE_DIRECTION_FEATURE,
            CONFIRMATION_FEATURE,
            "finite_feature_count",
            "feature_support_eligible",
            "quality_listing_eligible",
            "model_support_eligible",
        }
        if not required.issubset(pq.read_schema(path).names):
            raise Campaign295Error(f"Alpha158 required partition schema changed: {year}")


def run_campaign(*, batch_size: int) -> dict[str, Any]:
    if batch_size != 8192:
        raise Campaign295Error("Campaign295 batch size changed")
    protocol, alpha, numeric = validate_protocol()
    validate_implementation_freeze()
    verify_source_files(alpha, numeric)
    if OUTPUT_ROOT.exists():
        raise Campaign295Error("Campaign295 output root already exists; refuse overwrite")
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
        "kind": "a_share_three_day_walkforward_campaign295_no_return_audit",
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
            binding_path = OUTPUT_ROOT / f"fold_{fold['fold']}_prevalidation_scores.json"
            binding = {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign295_prevalidation_scores",
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
        "kind": "a_share_three_day_walkforward_campaign295_terminal_result",
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
            raise Campaign295Error("terminal trial ledger chain changed")
        previous = observed
    if not (
        terminal.get("kind")
        == "a_share_three_day_walkforward_campaign295_terminal_result"
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
        raise Campaign295Error("Campaign295 terminal semantics changed")
    return {
        "status": "verified_campaign295_terminal",
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
                raise Campaign295Error(f"{label} annual partition missing: {year}")
            schemas.append(
                {"source": label, "year": year, "columns": len(pq.read_schema(path).names)}
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
            raise Campaign295Error("run requires --confirm-run")
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
