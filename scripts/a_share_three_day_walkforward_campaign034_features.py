#!/usr/bin/env python3
"""Build and no-return audit Campaign034 round-tenth close avoidance."""

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
    import scripts.a_share_three_day_walkforward_campaign033_features as campaign033
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_three_day_walkforward_campaign033_features as campaign033


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign033_features.py"
)
BASE_FEATURE_RUNNER_SHA256 = (
    "ae3a523b3fdf0de128a878346b4b0368744ddc61e32e89bc94c0abe3426f70d1"
)
OLD_FACTOR = "intraday_return_spectral_entropy_59f"
FACTOR_NAME = "intraday_round_tenth_close_avoidance_240m"
MECHANISM_AUDIT_SHA256 = (
    "19ab4e57d2ddaf3890374c4c2c50df718203f2de32c86f60ba44010d564b6d80"
)
PROTOCOL_SHA256 = (
    "de5d6a4795cbe31bbb5b4cb74c4f663503c72c6301d144672916c22eaaab737c"
)
SNAPSHOT_MANIFEST_SHA256 = (
    "f9423db29dbe66856d79545dabb084f8b91f1409dc1835e3c0271bae8f25e3f2"
)
SNAPSHOT_DATASET_SHA256 = (
    "a828c1732cfd5149e3d54a9acfe8421251aadddce2b96f2be6bd9595d2de73d6"
)
NO_RETURN_AUDIT_SHA256 = (
    "44547f6b3cbbe76fcab383d6f8aa41f4a821e51f965d45f9a3532a474bf59713"
)
COMPARISON_ORDER_SHA256 = (
    "cf6f6867fd2309f965aa4780f32bd97dfc912caa2666c37fed37bde6080b45f3"
)
SELECTED_BAR_COUNT = 240
BASE_TICK_CNY = 0.01
ROUND_PRICE_GRID_CNY = 0.10
TICK_INTEGER_TOLERANCE_FEN = 1e-6
OUTPUT_RUN_ID_V2 = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign034_feature_library_v2"
)
FACTOR_FORMULA = (
    "1 - count(q_i mod 10 = 0) / 240, where q_i = "
    "nearest_integer(100 * close_i) after exact CNY 0.01 tick validation"
)

C33_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign033_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign033_feature_library_v1/snapshot_manifest.json"
)
C33_SNAPSHOT_SHA256 = (
    "bbd2b064885e90576712610a5b11426c3f3048fd10ff1d0590ea02861e423bd6"
)
C33_DATASET_SHA256 = (
    "ef76f920ab1b88dcbec40b640de240db308e60fc9711f42bb9cffbfe002e27cf"
)
C33_FACTOR_NAMES = ("intraday_return_spectral_entropy_59f",)


class Campaign034FeatureError(RuntimeError):
    """Raised when a frozen Campaign034 boundary no longer holds."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_FEATURE_RUNNER) != BASE_FEATURE_RUNNER_SHA256:
    raise Campaign034FeatureError("frozen Campaign033 feature runner changed")

# Reuse the frozen close-only partition builder and publication machinery.
# Candidate computation and the complete comparison audit are replaced below.
_source = BASE_FEATURE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign033", "Campaign034"),
    ("campaign033", "campaign034"),
    ("campaign_033", "campaign_034"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "fc932c2f9172d81bccb503f94d03e6407e2b807044eaab13d167f4a817289c1c",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "3e5546941b5954f96fc5a2d7dc7fbcf03b48d063ea1414133c2c17ae191fad4f",
        PROTOCOL_SHA256,
    ),
    (
        "bbd2b064885e90576712610a5b11426c3f3048fd10ff1d0590ea02861e423bd6",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "ef76f920ab1b88dcbec40b640de240db308e60fc9711f42bb9cffbfe002e27cf",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "f92d564c0a8f8bd32ae0a29f3879cb7c4bee85e61f9030f6ee8b635f4f5c1b35",
        NO_RETURN_AUDIT_SHA256,
    ),
    (
        "6176a8b4a0b190b31ae106591226625f140c970d3cc64ba8e3a889bee870f898",
        COMPARISON_ORDER_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_namespace: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign034_features_cloned",
}
exec(compile(_source, str(BASE_FEATURE_RUNNER), "exec"), _namespace)
_generated = _namespace["_generated"]

DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_034_no_return_preregistration.json"
)
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_034/no_return"
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
    """Validate Campaign034 and materialize its inherited complete spec."""

    path = path.expanduser().resolve()
    if _sha256(path) != PROTOCOL_SHA256:
        raise Campaign034FeatureError("Campaign034 no-return protocol changed")
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if not validation["all_bindings_passed"]:
        raise Campaign034FeatureError(
            "Campaign034 no-return protocol has a failed binding"
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
        == "a_share_three_day_walkforward_campaign034_no_return_preregistration"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("raw_unadjusted_price_required") is True
        and candidate.get("base_tick_cny") == BASE_TICK_CNY
        and candidate.get("round_price_grid_cny") == ROUND_PRICE_GRID_CNY
        and candidate.get("tick_integer_tolerance_fen")
        == TICK_INTEGER_TOLERANCE_FEN
        and candidate.get("support_denominator") == SELECTED_BAR_COUNT
        and candidate.get("valid_range") == [0.0, 1.0]
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
        and len(comparisons) == 55
        and len({str(item.get("name")) for item in comparisons}) == 55
        and comparisons[-1].get("name") == C33_FACTOR_NAMES[0]
        and _comparison_order_digest(comparisons) == COMPARISON_ORDER_SHA256
        and finite.get("expected_trial_count") == 1
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("complexity") == 1
        and finite.get("purge_local_signal_sessions") == 3
        and boundary.get("external_campaign034_minute_partitions_read") is False
        and boundary.get("candidate_values_read") is False
        and boundary.get("comparison_values_read") is False
        and boundary.get("historical_daily_price_fields_read") is False
        and boundary.get("historical_forward_returns_read") is False
        and boundary.get(
            "candidate49_historical_return_signal_or_execution_backfill_performed"
        )
        is False
        and boundary.get(
            "current_scoring_selection_sizing_or_orders_performed"
        )
        is False
    ):
        raise Campaign034FeatureError("Campaign034 no-return semantics changed")

    base_spec = campaign033.load_protocol()
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
        raise Campaign034FeatureError(
            "Campaign034 inherited holding-period context changed"
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
    """Compute fixed-support avoidance of exact CNY 0.10 close points."""

    closes = np.asarray(closes, dtype=float)
    if closes.ndim != 2 or closes.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign034FeatureError("Campaign034 aligned close shape is invalid")
    finite_by_position = np.isfinite(closes)
    positive_by_position = closes > 0.0
    finite_closes = finite_by_position.all(axis=1)
    positive_closes = positive_by_position.all(axis=1)
    required_valid = finite_closes & positive_closes

    safe_closes = np.where(
        finite_by_position & positive_by_position,
        closes,
        0.0,
    )
    close_fen = 100.0 * safe_closes
    nearest_fen = np.rint(close_fen)
    tick_error_fen = np.abs(close_fen - nearest_fen)
    tick_valid_by_position = (
        np.isfinite(tick_error_fen)
        & (tick_error_fen <= TICK_INTEGER_TOLERANCE_FEN)
    )
    tick_valid = tick_valid_by_position.all(axis=1)
    integer_fen = nearest_fen.astype(np.int64)
    round_tenth_count = (np.remainder(integer_fen, 10) == 0).sum(axis=1)
    values = 1.0 - (
        round_tenth_count.astype(float) / float(SELECTED_BAR_COUNT)
    )
    finite_values = np.isfinite(values)
    in_range = (values >= 0.0) & (values <= 1.0)
    eligible = required_valid & tick_valid & finite_values & in_range
    quality = {
        "base_rows": int(len(closes)),
        "invalid_required_close_rows": int((~finite_closes).sum()),
        f"{FACTOR_NAME}__nonpositive_close_rows": int(
            (finite_closes & ~positive_closes).sum()
        ),
        f"{FACTOR_NAME}__non_tick_grid_close_rows": int(
            (required_valid & ~tick_valid).sum()
        ),
        f"{FACTOR_NAME}__round_tenth_close_observations": int(
            (
                (np.remainder(integer_fen, 10) == 0)
                & finite_by_position
                & positive_by_position
                & tick_valid_by_position
            ).sum()
        ),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (required_valid & tick_valid & (~finite_values | ~in_range)).sum()
        ),
    }
    return (
        {FACTOR_NAME: np.where(eligible, values, np.nan)},
        {FACTOR_NAME: eligible},
        quality,
    )


def _verify_snapshot_spec(
    spec: dict[str, Any], workers: int
) -> tuple[dict[str, Any], dict[str, Any], tuple[str, ...]]:
    manifest, verification = campaign033.campaign032.executor._verify_prior_snapshot(
        path=spec["path"],
        manifest_sha256=spec["sha256"],
        dataset_sha256=spec["dataset_sha256"],
        kind=spec["kind"],
        factor_names=spec["all_factors"],
        output_columns=spec["output_columns"],
        workers=workers,
    )
    return manifest, verification, tuple(spec["selected"])


def _snapshot_spec(
    *,
    campaign: int,
    path: Path,
    manifest_sha256: str,
    dataset_sha256: str,
    factors: tuple[str, ...],
) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    output_columns = ["trade_date", "symbol", "provider"]
    for factor in factors:
        output_columns.extend([factor, f"{factor}_eligible"])
    return {
        "campaign": campaign,
        "path": path,
        "sha256": manifest_sha256,
        "dataset_sha256": dataset_sha256,
        "kind": str(manifest.get("kind") or ""),
        "all_factors": factors,
        "output_columns": tuple(output_columns),
        "selected": factors,
    }


def run_no_return_audit(
    *,
    data_root: Path,
    experiment_root: Path,
    workers: int,
) -> Path:
    """Apply coverage before the complete frozen 55-factor library."""

    if not SNAPSHOT_MANIFEST_SHA256 or not SNAPSHOT_DATASET_SHA256:
        raise Campaign034FeatureError(
            "bind Campaign034 snapshot fingerprints before audit"
        )
    _generated["_bind_executor"]()
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_protocol()
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    if _sha256(manifest_path) != SNAPSHOT_MANIFEST_SHA256:
        raise Campaign034FeatureError("Campaign034 snapshot manifest changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    existing = sorted(experiment_root.glob("*_campaign034_no_return_audit.json"))
    if existing:
        if len(existing) != 1 or not NO_RETURN_AUDIT_SHA256:
            raise Campaign034FeatureError(
                "existing Campaign034 audit is ambiguous or unbound"
            )
        if _sha256(existing[0]) != NO_RETURN_AUDIT_SHA256:
            raise Campaign034FeatureError("Campaign034 audit changed")
        return existing[0]
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    print("building Campaign034 no-price quality/listing eligibility", flush=True)
    eligible_keys = campaign033.campaign032.foundation.quality_listing_eligible_keys(
        campaign033.campaign032.load_protocol()
    )
    candidate = campaign033.campaign032.engine.load_factor_frame(
        manifest_path, manifest, FACTOR_NAME
    )
    quality_frame, coverage = (
        campaign033.campaign032.engine.coverage_and_capacity(
            candidate,
            eligible_keys,
            spec,
            FACTOR_NAME,
        )
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
        keys, values = campaign033.campaign032.engine._sorted_candidate_arrays(
            quality_frame,
            FACTOR_NAME,
        )
        chain, candidate49_manifest_path, candidate49_manifest = (
            campaign033.campaign032.engine._comparison_chain(data_root)
        )
        comparisons, frozen_verifications = (
            campaign033.campaign032.engine._uniqueness_against_frozen_library(
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
        for prior_spec in (
            campaign033.campaign032._snapshot_specs_from_campaign031()
        ):
            selected = tuple(
                factor
                for factor in prior_spec["all_factors"]
                if factor in expected_order
            )
            snapshot_specs.append({**prior_spec, "selected": selected})
        snapshot_specs.extend(
            [
                _snapshot_spec(
                    campaign=32,
                    path=campaign033.C32_SNAPSHOT_PATH,
                    manifest_sha256=campaign033.C32_SNAPSHOT_SHA256,
                    dataset_sha256=campaign033.C32_DATASET_SHA256,
                    factors=campaign033.C32_FACTOR_NAMES,
                ),
                _snapshot_spec(
                    campaign=33,
                    path=C33_SNAPSHOT_PATH,
                    manifest_sha256=C33_SNAPSHOT_SHA256,
                    dataset_sha256=C33_DATASET_SHA256,
                    factors=C33_FACTOR_NAMES,
                ),
            ]
        )
        snapshot_verifications: dict[str, Any] = {}
        for prior_spec in snapshot_specs:
            campaign_number = int(prior_spec["campaign"])
            prior_manifest, prior_verification, selected = _verify_snapshot_spec(
                prior_spec, workers
            )
            if selected:
                comparisons.extend(
                    campaign033.campaign032.executor._prior_comparisons(
                        candidate_keys=keys,
                        candidate_values=values,
                        manifest=prior_manifest,
                        factors=selected,
                        gate=gate,
                    )
                )
            snapshot_verifications[
                f"campaign{campaign_number:03d}"
            ] = prior_verification
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
            and len(comparisons) == 55
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
        f"{campaign033.campaign032.research._timestamp()}_"
        "campaign034_no_return_audit"
    )
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign034_no_return_audit",
        "status": (
            "completed_with_one_admissible_factor_pending_walkforward_preregistration"
            if admitted
            else "completed_zero_admissible_factors_stop_before_historical_returns"
        ),
        "run_id": run_id,
        "created_at": campaign033.campaign032.research._timestamp(),
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
            "freeze the exact one-trial Campaign034 walk-forward catalog before "
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
    campaign033.campaign032.foundation.atomic_write_json(record, destination)
    return destination


def status(data_root: Path, experiment_root: Path) -> dict[str, Any]:
    manifest_path = output_root(
        data_root.expanduser().resolve()
    ) / "snapshot_manifest.json"
    audits = sorted(
        experiment_root.expanduser().resolve().glob(
            "*_campaign034_no_return_audit.json"
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
_generated["OUTPUT_RUN_ID"] = OUTPUT_RUN_ID_V2
_generated["load_protocol"] = load_protocol
_generated["compute_factor_values"] = compute_factor_values
_generated["compute_partition_frame"].__globals__[
    "compute_factor_values"
] = compute_factor_values
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
