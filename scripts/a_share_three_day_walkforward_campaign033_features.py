#!/usr/bin/env python3
"""Build and no-return audit Campaign033 signed-return spectral entropy."""

from __future__ import annotations

import copy
import gc
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

try:
    import scripts.a_share_three_day_preregistration_binding_validator as bindings
    import scripts.a_share_three_day_walkforward_campaign028_features as campaign028
    import scripts.a_share_three_day_walkforward_campaign032_features as campaign032
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_three_day_walkforward_campaign028_features as campaign028
    import a_share_three_day_walkforward_campaign032_features as campaign032


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign028_features.py"
)
BASE_FEATURE_RUNNER_SHA256 = (
    "eb0eeb690c07fd28ccae71c6125021535edb9aa18a0c669110b18dc52457f317"
)
COMPARISON_ORCHESTRATOR = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign032_features.py"
)
COMPARISON_ORCHESTRATOR_SHA256 = (
    "2f7490fbdf298101ab6cd7ce9bdaeab235a8c00351c5d3626ad761d07c9f23ee"
)
OLD_FACTOR = "intraday_absolute_return_serial_persistence_236p"
FACTOR_NAME = "intraday_return_spectral_entropy_59f"
MECHANISM_AUDIT_SHA256 = (
    "fc932c2f9172d81bccb503f94d03e6407e2b807044eaab13d167f4a817289c1c"
)
PROTOCOL_SHA256 = (
    "3e5546941b5954f96fc5a2d7dc7fbcf03b48d063ea1414133c2c17ae191fad4f"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "bbd2b064885e90576712610a5b11426c3f3048fd10ff1d0590ea02861e423bd6"
)
SNAPSHOT_DATASET_SHA256 = (
    "ef76f920ab1b88dcbec40b640de240db308e60fc9711f42bb9cffbfe002e27cf"
)
NO_RETURN_AUDIT_SHA256 = (
    "f92d564c0a8f8bd32ae0a29f3879cb7c4bee85e61f9030f6ee8b635f4f5c1b35"
)
COMPARISON_ORDER_SHA256 = (
    "6176a8b4a0b190b31ae106591226625f140c970d3cc64ba8e3a889bee870f898"
)
SELECTED_BAR_COUNT = 240
RETURN_COUNT_PER_HALF = 119
POSITIVE_FREQUENCY_BIN_COUNT = 59
ENDPOINT_TOLERANCE = 1e-12
FACTOR_FORMULA = (
    "-sum(p_k * log(p_k)) / log(59) for k=1..59, where p_k is pooled "
    "morning-plus-afternoon demeaned signed-return DFT power at positive "
    "frequency k divided by total pooled positive-frequency power"
)

C32_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign032_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign032_feature_library_v1/snapshot_manifest.json"
)
C32_SNAPSHOT_SHA256 = (
    "8e64ad897fe725ab4ed800b0203ddd88a6c1431e2386744e1d2b13867d848c65"
)
C32_DATASET_SHA256 = (
    "c72008162f6655e7ce34da114641f451aa04d32df61ac4c77222f7f8ad1d787f"
)
C32_FACTOR_NAMES = ("quarterly_announcement_timeliness_days",)


class Campaign033FeatureError(RuntimeError):
    """Raised when a frozen Campaign033 boundary no longer holds."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_FEATURE_RUNNER) != BASE_FEATURE_RUNNER_SHA256:
    raise Campaign033FeatureError("frozen Campaign028 feature runner changed")
if _sha256(COMPARISON_ORCHESTRATOR) != COMPARISON_ORCHESTRATOR_SHA256:
    raise Campaign033FeatureError("frozen Campaign032 comparison runner changed")

# Reuse the frozen close-only partition builder and publication machinery.
# Candidate computation and the complete comparison audit are replaced below.
_source = BASE_FEATURE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign028", "Campaign033"),
    ("campaign028", "campaign033"),
    ("campaign_028", "campaign_033"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "f41e33bb607e7adf6a7ba3c731bae40fbaa85fdc9e5ee054831607bbcd518a2a",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "704dbe2f21624a5b97ac597c9e79b1ca6e7611903eef39624a701a1e0acc10bc",
        PROTOCOL_SHA256,
    ),
    (
        "b08065c1cb7dbdbf06e4285a0c686338e121d27546fce97bb92dc9251f8366d0",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "8d3a3368ed85c0215751bf86b7d491bf9ad049762a810cce2e50b1a3b4badadf",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "9f077d989d0456cbfaf23fbcce4d3737ac3da25380c50435cfddbc7f31fe0963",
        NO_RETURN_AUDIT_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_namespace: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign033_features_cloned",
}
exec(compile(_source, str(BASE_FEATURE_RUNNER), "exec"), _namespace)
_generated = _namespace["_generated"]

DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_033_no_return_preregistration.json"
)
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_033/no_return"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "close")
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
FACTOR_NAMES = (FACTOR_NAME,)
FACTOR_DIRECTIONS = {FACTOR_NAME: "higher"}
FACTOR_RANGES = {FACTOR_NAME: (0.0, 1.0)}
FACTOR_FORMULAS = {FACTOR_NAME: FACTOR_FORMULA}


def _comparison_order_digest(comparisons: list[dict[str, Any]]) -> str:
    values = [
        (str(item["name"]), str(item["score_direction"]))
        for item in comparisons
    ]
    payload = json.dumps(
        values,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    """Validate Campaign033 and materialize its inherited complete spec."""

    path = path.expanduser().resolve()
    if _sha256(path) != PROTOCOL_SHA256:
        raise Campaign033FeatureError("Campaign033 no-return protocol changed")
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if not validation["all_bindings_passed"]:
        raise Campaign033FeatureError(
            "Campaign033 no-return protocol has a failed binding"
        )
    delta = json.loads(path.read_text(encoding="utf-8"))
    candidate = delta.get("candidate") or {}
    gates = delta.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    comparisons = list(uniqueness.get("comparison_factors") or [])
    finite = delta.get("finite_development_catalog_if_admitted") or {}
    boundary = delta.get("research_boundary") or {}
    if not (
        delta.get("version") == 1
        and delta.get("kind")
        == "a_share_three_day_walkforward_campaign033_no_return_preregistration"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("return_count_per_half") == RETURN_COUNT_PER_HALF
        and candidate.get("positive_frequency_bins") == [1, 59]
        and candidate.get("half_session_demeaning") is True
        and candidate.get("valid_range") == [0.0, 1.0]
        and candidate.get("endpoint_canonicalization_tolerance")
        == ENDPOINT_TOLERANCE
        and candidate.get("transform_scale_clip_threshold_filter") == "none"
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.90
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and uniqueness.get(
            "maximum_allowed_absolute_median_daily_rank_correlation"
        )
        == 0.8
        and uniqueness.get("minimum_pairwise_names_per_session") == 50
        and uniqueness.get("minimum_pairwise_sessions_per_comparison") == 100
        and len(comparisons) == 54
        and len({str(item.get("name")) for item in comparisons}) == 54
        and comparisons[-1].get("name") == C32_FACTOR_NAMES[0]
        and _comparison_order_digest(comparisons) == COMPARISON_ORDER_SHA256
        and finite.get("expected_trial_count") == 1
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("complexity") == 1
        and finite.get("purge_local_signal_sessions") == 3
        and boundary.get("external_campaign033_minute_partitions_read") is False
        and boundary.get("candidate_values_read") is False
        and boundary.get("comparison_values_read") is False
        and boundary.get("historical_daily_price_fields_read") is False
        and boundary.get("historical_forward_returns_read") is False
        and boundary.get("candidate49_historical_return_signal_or_execution_backfill_performed")
        is False
        and boundary.get("current_scoring_selection_sizing_or_orders_performed")
        is False
    ):
        raise Campaign033FeatureError("Campaign033 no-return semantics changed")

    base_spec = campaign032.load_protocol()
    base_coverage = (
        (base_spec.get("ordered_no_return_gates") or {}).get(
            "coverage_and_capacity_before_comparison_values"
        )
        or {}
    )
    if (
        "holding_period_sessions" in coverage
        or base_coverage.get("holding_period_sessions") != 3
    ):
        raise Campaign033FeatureError(
            "Campaign033 inherited holding-period context changed"
        )
    runtime_gates = copy.deepcopy(gates)
    runtime_gates[
        "coverage_and_capacity_before_comparison_values"
    ]["holding_period_sessions"] = 3

    spec = copy.deepcopy(base_spec)
    spec["version"] = 1
    spec["kind"] = delta["kind"]
    spec["status"] = delta["status"]
    spec["candidates"] = [
        {
            "name": FACTOR_NAME,
            "direction": "higher",
            "formula": FACTOR_FORMULA,
            "source_fields_allowed": list(RAW_COLUMNS),
            "source_fields_used_by_formula": list(RAW_COLUMNS),
            "selected_bar_count": SELECTED_BAR_COUNT,
            "valid_range": [0.0, 1.0],
        }
    ]
    spec["ordered_no_return_gates"] = runtime_gates
    spec["finite_post_admissibility_search"] = {
        "candidate_factor_count": 1,
        "development_trial_count": 1,
        "trial": {
            "trial_id": finite["trial_id"],
            "factor": FACTOR_NAME,
            "direction": "higher",
            "transform": "none",
            "threshold": "none",
            "filter": "none",
            "combination": "none",
        },
        "development_interval": {
            "start": finite["development_interval"][0],
            "end": finite["development_interval"][1],
            "folds": copy.deepcopy(
                (base_spec.get("finite_post_admissibility_search") or {})
                .get("development_interval", {})
                .get("folds", [])
            ),
            "purge_local_signal_sessions": 3,
        },
    }
    return spec


def compute_factor_values(
    *,
    closes: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Compute the frozen pooled two-half 59-bin spectral entropy."""

    closes = np.asarray(closes, dtype=float)
    if closes.ndim != 2 or closes.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign033FeatureError("Campaign033 aligned close shape is invalid")
    finite_closes = np.isfinite(closes).all(axis=1)
    positive_closes = (closes > 0.0).all(axis=1)
    required_valid = finite_closes & positive_closes
    safe_closes = np.where(closes > 0.0, closes, 1.0)
    log_closes = np.log(safe_closes)
    morning = np.diff(log_closes[:, :120], axis=1)
    afternoon = np.diff(log_closes[:, 120:], axis=1)
    if (
        morning.shape[1] != RETURN_COUNT_PER_HALF
        or afternoon.shape != morning.shape
    ):
        raise Campaign033FeatureError("Campaign033 return-vector shape changed")
    finite_returns = np.isfinite(morning).all(axis=1) & np.isfinite(
        afternoon
    ).all(axis=1)
    morning = morning - morning.mean(axis=1, keepdims=True)
    afternoon = afternoon - afternoon.mean(axis=1, keepdims=True)
    morning_coefficients = np.fft.rfft(morning, n=RETURN_COUNT_PER_HALF, axis=1)[
        :, 1:
    ]
    afternoon_coefficients = np.fft.rfft(
        afternoon, n=RETURN_COUNT_PER_HALF, axis=1
    )[:, 1:]
    if (
        morning_coefficients.shape[1] != POSITIVE_FREQUENCY_BIN_COUNT
        or afternoon_coefficients.shape != morning_coefficients.shape
    ):
        raise Campaign033FeatureError("Campaign033 frequency-bin shape changed")
    power = (
        np.abs(morning_coefficients) ** 2
        + np.abs(afternoon_coefficients) ** 2
    )
    finite_power = np.isfinite(power).all(axis=1)
    total_power = np.sum(power, axis=1)
    positive_power = total_power > 0.0
    probabilities = np.divide(
        power,
        total_power[:, None],
        out=np.zeros_like(power, dtype=float),
        where=positive_power[:, None],
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        entropy_terms = np.where(
            probabilities > 0.0,
            probabilities * np.log(probabilities),
            0.0,
        )
    values = -np.sum(entropy_terms, axis=1) / np.log(
        POSITIVE_FREQUENCY_BIN_COUNT
    )
    low = 0.0
    high = 1.0
    canonicalized = (
        ((values < low) & (values >= low - ENDPOINT_TOLERANCE))
        | ((values > high) & (values <= high + ENDPOINT_TOLERANCE))
    )
    values = np.where(
        (values < low) & (values >= low - ENDPOINT_TOLERANCE),
        low,
        values,
    )
    values = np.where(
        (values > high) & (values <= high + ENDPOINT_TOLERANCE),
        high,
        values,
    )
    finite_values = np.isfinite(values)
    in_range = (values >= low) & (values <= high)
    eligible = (
        required_valid
        & finite_returns
        & finite_power
        & positive_power
        & finite_values
        & in_range
    )
    quality = {
        "base_rows": int(len(closes)),
        "invalid_required_close_rows": int((~finite_closes).sum()),
        f"{FACTOR_NAME}__nonpositive_close_rows": int(
            (finite_closes & ~positive_closes).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_return_rows": int(
            (required_valid & ~finite_returns).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_power_rows": int(
            (required_valid & finite_returns & ~finite_power).sum()
        ),
        f"{FACTOR_NAME}__nonpositive_total_power_rows": int(
            (required_valid & finite_returns & finite_power & ~positive_power).sum()
        ),
        f"{FACTOR_NAME}__endpoint_canonicalized_rows": int(
            (required_valid & finite_returns & finite_power & canonicalized).sum()
        ),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (
                required_valid
                & finite_returns
                & finite_power
                & positive_power
                & (~finite_values | ~in_range)
            ).sum()
        ),
    }
    return (
        {FACTOR_NAME: np.where(eligible, values, np.nan)},
        {FACTOR_NAME: eligible},
        quality,
    )


def _verify_post_campaign003_snapshot(
    spec: dict[str, Any], workers: int
) -> tuple[dict[str, Any], dict[str, Any], tuple[str, ...]]:
    manifest, verification = campaign032.executor._verify_prior_snapshot(
        path=spec["path"],
        manifest_sha256=spec["sha256"],
        dataset_sha256=spec["dataset_sha256"],
        kind=spec["kind"],
        factor_names=spec["all_factors"],
        output_columns=spec["output_columns"],
        workers=workers,
    )
    selected = tuple(spec["selected"])
    return manifest, verification, selected


def run_no_return_audit(
    *,
    data_root: Path,
    experiment_root: Path,
    workers: int,
) -> Path:
    """Apply coverage before the complete frozen 54-factor library."""

    if not SNAPSHOT_MANIFEST_SHA256 or not SNAPSHOT_DATASET_SHA256:
        raise Campaign033FeatureError(
            "bind Campaign033 snapshot fingerprints before audit"
        )
    _generated["_bind_executor"]()
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_protocol()
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    if _sha256(manifest_path) != SNAPSHOT_MANIFEST_SHA256:
        raise Campaign033FeatureError("Campaign033 snapshot manifest changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    existing = sorted(experiment_root.glob("*_campaign033_no_return_audit.json"))
    if existing:
        if len(existing) != 1 or not NO_RETURN_AUDIT_SHA256:
            raise Campaign033FeatureError(
                "existing Campaign033 audit is ambiguous or unbound"
            )
        if _sha256(existing[0]) != NO_RETURN_AUDIT_SHA256:
            raise Campaign033FeatureError("Campaign033 audit changed")
        return existing[0]
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    print("building Campaign033 no-price quality/listing eligibility", flush=True)
    base_spec = campaign032.load_protocol()
    eligible_keys = campaign032.foundation.quality_listing_eligible_keys(base_spec)
    candidate = campaign032.engine.load_factor_frame(
        manifest_path, manifest, FACTOR_NAME
    )
    quality_frame, coverage = campaign032.engine.coverage_and_capacity(
        candidate,
        eligible_keys,
        spec,
        FACTOR_NAME,
    )
    del candidate, eligible_keys
    gc.collect()
    if coverage["gate_passed_before_comparison_values"]:
        gate = spec["ordered_no_return_gates"][
            "uniqueness_after_coverage_only"
        ]
        expected_order = [
            str(item["name"]) for item in gate["comparison_factors"]
        ]
        keys, values = campaign032.engine._sorted_candidate_arrays(
            quality_frame,
            FACTOR_NAME,
        )
        chain, candidate49_manifest_path, candidate49_manifest = (
            campaign032.engine._comparison_chain(data_root)
        )
        comparisons, frozen_verifications = (
            campaign032.engine._uniqueness_against_frozen_library(
                candidate_keys=keys,
                candidate_values=values,
                chain=chain,
                candidate49_manifest_path=candidate49_manifest_path,
                candidate49_manifest=candidate49_manifest,
                gate=gate,
                workers=workers,
                frozen_verifications=None,
            )
        )
        snapshot_specs = []
        for snapshot_spec in campaign032._snapshot_specs_from_campaign031():
            selected = tuple(
                factor
                for factor in snapshot_spec["all_factors"]
                if factor in expected_order
            )
            snapshot_specs.append({**snapshot_spec, "selected": selected})
        c32_manifest = json.loads(C32_SNAPSHOT_PATH.read_text(encoding="utf-8"))
        c32_output_columns = ["trade_date", "symbol", "provider"]
        for factor in C32_FACTOR_NAMES:
            c32_output_columns.extend([factor, f"{factor}_eligible"])
        snapshot_specs.append(
            {
                "campaign": 32,
                "path": C32_SNAPSHOT_PATH,
                "sha256": C32_SNAPSHOT_SHA256,
                "dataset_sha256": C32_DATASET_SHA256,
                "kind": str(c32_manifest.get("kind") or ""),
                "all_factors": C32_FACTOR_NAMES,
                "output_columns": tuple(c32_output_columns),
                "selected": C32_FACTOR_NAMES,
            }
        )
        snapshot_verifications: dict[str, Any] = {}
        for snapshot_spec in snapshot_specs:
            campaign = int(snapshot_spec["campaign"])
            prior_manifest, prior_verification, selected = (
                _verify_post_campaign003_snapshot(snapshot_spec, workers)
            )
            if selected:
                comparisons.extend(
                    campaign032.executor._prior_comparisons(
                        candidate_keys=keys,
                        candidate_values=values,
                        manifest=prior_manifest,
                        factors=selected,
                        gate=gate,
                    )
                )
            snapshot_verifications[f"campaign{campaign:03d}"] = prior_verification
        observed_order = [
            str(item["comparison_factor"]) for item in comparisons
        ]
        observed = [
            float(item["absolute_median_daily_rank_correlation"])
            for item in comparisons
            if item["absolute_median_daily_rank_correlation"] is not None
        ]
        passed = bool(
            observed_order == expected_order
            and len(comparisons) == 54
            and all(item["gate_passed"] for item in comparisons)
        )
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": True,
            "comparison_factor_count": len(comparisons),
            "comparison_order_matches_preregistration": (
                observed_order == expected_order
            ),
            "pre_campaign004_comparison_count": 25,
            "post_campaign003_snapshot_verification": snapshot_verifications,
            "prior_snapshot_file_verification": frozen_verifications,
            "comparisons": comparisons,
            "maximum_observed_absolute_median_daily_rank_correlation": (
                max(observed) if observed else None
            ),
            "all_required_comparisons_passed": passed,
        }
    else:
        uniqueness = {
            "comparison_values_loaded_after_coverage_pass": False,
            "comparisons": [],
            "all_required_comparisons_passed": False,
            "failure_reason": "coverage_gate_failed",
        }
    admitted = bool(
        coverage["gate_passed_before_comparison_values"]
        and uniqueness["all_required_comparisons_passed"]
    )
    run_id = (
        f"{campaign032.research._timestamp()}_campaign033_no_return_audit"
    )
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign033_no_return_audit",
        "status": (
            "completed_with_one_admissible_factor_pending_walkforward_preregistration"
            if admitted
            else "completed_zero_admissible_factors_stop_before_historical_returns"
        ),
        "run_id": run_id,
        "created_at": campaign032.research._timestamp(),
        "protocol": {
            "path": str(DEFAULT_PROTOCOL.resolve()),
            "sha256": PROTOCOL_SHA256,
        },
        "candidate_snapshot": {
            "path": str(manifest_path),
            "sha256": SNAPSHOT_MANIFEST_SHA256,
            "dataset_sha256": SNAPSHOT_DATASET_SHA256,
        },
        "snapshot_file_verification": verification,
        "coverage_and_capacity": {FACTOR_NAME: coverage},
        "uniqueness": {FACTOR_NAME: uniqueness},
        "admissible_factor_names": [FACTOR_NAME] if admitted else [],
        "admissible_factor_count": 1 if admitted else 0,
        "failed_factor_names": [] if admitted else [FACTOR_NAME],
        "next_action": (
            "freeze the exact one-trial Campaign033 walk-forward catalog before "
            "reading 2019-2023 returns"
            if admitted
            else "record the no-return rejection and design a new campaign"
        ),
        "source_fields_read": list(RAW_COLUMNS),
        "minute_open_high_low_volume_amount_fields_read": [],
        "market_quarterly_or_event_fields_read": [],
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "candidate49_historical_return_read": False,
        "candidate49_prospective_ledgers_changed": False,
        "candidate50_prospective_activation_created": False,
        "training_or_model_fitting_performed": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }
    experiment_root.mkdir(parents=True, exist_ok=True)
    destination = experiment_root / f"{run_id}.json"
    campaign032.foundation.atomic_write_json(record, destination)
    return destination


def status(data_root: Path, experiment_root: Path) -> dict[str, Any]:
    manifest_path = output_root(
        data_root.expanduser().resolve()
    ) / "snapshot_manifest.json"
    audits = sorted(
        experiment_root.expanduser().resolve().glob(
            "*_campaign033_no_return_audit.json"
        )
    )
    result: dict[str, Any] = {
        "protocol_path": str(DEFAULT_PROTOCOL.resolve()),
        "protocol_sha256_bound": True,
        "snapshot_manifest_path": str(manifest_path),
        "snapshot_exists": manifest_path.is_file(),
        "snapshot_sha256_bound": bool(SNAPSHOT_MANIFEST_SHA256),
        "audit_count": len(audits),
        "no_return_audit_sha256_bound": bool(NO_RETURN_AUDIT_SHA256),
        "source_fields_read_by_status": list(RAW_COLUMNS),
        "minute_open_high_low_volume_amount_fields_read_by_status": [],
        "market_quarterly_or_event_fields_read_by_status": [],
        "daily_price_fields_read_by_status": False,
        "forward_return_fields_read_by_status": False,
        "candidate49_historical_return_read": False,
    }
    if manifest_path.is_file():
        result["snapshot_observed_sha256"] = _sha256(manifest_path)
    if audits:
        result["latest_audit"] = str(audits[-1])
        result["latest_audit_observed_sha256"] = _sha256(audits[-1])
    return result


_namespace["compute_factor_values"] = compute_factor_values
_generated["DEFAULT_PROTOCOL"] = DEFAULT_PROTOCOL
_generated["DEFAULT_EXPERIMENT_ROOT"] = DEFAULT_EXPERIMENT_ROOT
_generated["FACTOR_NAME"] = FACTOR_NAME
_generated["FACTOR_NAMES"] = FACTOR_NAMES
_generated["FACTOR_DIRECTIONS"] = FACTOR_DIRECTIONS
_generated["FACTOR_RANGES"] = FACTOR_RANGES
_generated["FACTOR_FORMULA"] = FACTOR_FORMULA
_generated["FACTOR_FORMULAS"] = FACTOR_FORMULAS
_generated["OUTPUT_COLUMNS"] = OUTPUT_COLUMNS
_generated["load_protocol"] = load_protocol
_generated["compute_factor_values"] = compute_factor_values
_generated["run_no_return_audit"] = run_no_return_audit
_generated["status"] = status

empty_output_frame = _generated["empty_output_frame"]
output_root = _generated["output_root"]
build_snapshot = _generated["build_snapshot"]
verify_snapshot_files = _generated["verify_snapshot_files"]
_validate_snapshot_manifest = _generated["_validate_snapshot_manifest"]
parser = _generated["parser"]
main = _generated["main"]
engine_namespace = run_no_return_audit.__globals__


if __name__ == "__main__":
    raise SystemExit(main())
