#!/usr/bin/env python3
"""Build and no-return audit Campaign035 weak-order return entropy."""

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
    import scripts.a_share_three_day_walkforward_campaign034_features as campaign034
except ModuleNotFoundError:
    import a_share_three_day_preregistration_binding_validator as bindings
    import a_share_three_day_walkforward_campaign034_features as campaign034


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_FEATURE_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign034_features.py"
)
BASE_FEATURE_RUNNER_SHA256 = (
    "09d47d7cdf480cde9b60ad5be8e2b28fb0d31f7c041b68bcbd4278d5837f7c16"
)
OLD_FACTOR = "intraday_round_tenth_close_avoidance_240m"
FACTOR_NAME = "intraday_return_weak_order_entropy_234t"
MECHANISM_AUDIT_SHA256 = (
    "e4e8ca0f4228f123a749c549b1a4d7df4bf5cdeec7e544291612ae8b1b91d48e"
)
PROTOCOL_SHA256 = (
    "22ffd5a21b4104a8c1e0d110cc335a1a758649560ab2d10e9a9c16258f70d7c9"
)

# Bind these only after the immutable artifacts have been published.
SNAPSHOT_MANIFEST_SHA256 = (
    "33de221a37e0a19d3c1fffba3c8f0e64c20571581a7c72296b1a593c0acc91f4"
)
SNAPSHOT_DATASET_SHA256 = (
    "b557148b91a16dad9f028190723b2485f9eadd231c0aaded6b499d9dc1c68606"
)
NO_RETURN_AUDIT_SHA256 = (
    "ca40ca05991c8ea3c56fe3b3d85dc782c4e2d22f69b51bd12f192c3b9f289b0a"
)

COMPARISON_ORDER_SHA256 = (
    "c15a965426251d3c3e0d2bf9dae42cd8e231529cf6620871966513e13a09d4d0"
)
INHERITED_COMPARISON_ORDER_SHA256 = (
    "cf6f6867fd2309f965aa4780f32bd97dfc912caa2666c37fed37bde6080b45f3"
)
SELECTED_BAR_COUNT = 240
RETURN_COUNT_PER_HALF = 119
TUPLE_COUNT_PER_HALF = 117
POOLED_TUPLE_COUNT = 234
WEAK_ORDER_STATE_COUNT = 13
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign035_feature_library_v1"
)
FACTOR_FORMULA = (
    "For each half form 119 adjacent log-close returns and its 117 "
    "overlapping length-three return tuples. Classify all 234 tuples into "
    "the 13 exact weak orderings of three values; with p_k=count_k/234, "
    "return -sum_{p_k>0}(p_k*ln(p_k))/ln(13)."
)

C34_SNAPSHOT_PATH = Path(
    "/Volumes/DIsk/qlib-a-share-tushare-1m/derived/a_share/rich/tushare/"
    "minute_walkforward_campaign034_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign034_feature_library_v2/snapshot_manifest.json"
)
C34_SNAPSHOT_SHA256 = (
    "f9423db29dbe66856d79545dabb084f8b91f1409dc1835e3c0271bae8f25e3f2"
)
C34_DATASET_SHA256 = (
    "a828c1732cfd5149e3d54a9acfe8421251aadddce2b96f2be6bd9595d2de73d6"
)
C34_FACTOR_NAMES = ("intraday_round_tenth_close_avoidance_240m",)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_FEATURE_RUNNER) != BASE_FEATURE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign034 feature runner changed")

# Clone the frozen close-only build/publish machinery into a separate namespace.
# Candidate computation and the complete comparison audit are replaced below.
_source = BASE_FEATURE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign034", "Campaign035"),
    ("campaign034", "campaign035"),
    ("campaign_034", "campaign_035"),
    (OLD_FACTOR, FACTOR_NAME),
    (
        "19ab4e57d2ddaf3890374c4c2c50df718203f2de32c86f60ba44010d564b6d80",
        MECHANISM_AUDIT_SHA256,
    ),
    (
        "de5d6a4795cbe31bbb5b4cb74c4f663503c72c6301d144672916c22eaaab737c",
        PROTOCOL_SHA256,
    ),
    (
        "f9423db29dbe66856d79545dabb084f8b91f1409dc1835e3c0271bae8f25e3f2",
        SNAPSHOT_MANIFEST_SHA256,
    ),
    (
        "a828c1732cfd5149e3d54a9acfe8421251aadddce2b96f2be6bd9595d2de73d6",
        SNAPSHOT_DATASET_SHA256,
    ),
    (
        "44547f6b3cbbe76fcab383d6f8aa41f4a821e51f965d45f9a3532a474bf59713",
        NO_RETURN_AUDIT_SHA256,
    ),
    (
        "cf6f6867fd2309f965aa4780f32bd97dfc912caa2666c37fed37bde6080b45f3",
        COMPARISON_ORDER_SHA256,
    ),
):
    _source = _source.replace(_old, _new)

_namespace: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign035_features_cloned",
}
exec(compile(_source, str(BASE_FEATURE_RUNNER), "exec"), _namespace)
_generated = _namespace["_generated"]

DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_035_no_return_preregistration.json"
)
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_035/no_return"
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
Campaign035FeatureError = _namespace["Campaign035FeatureError"]

# Base-3 codes for the 13 transitive comparison triples
# (cmp(a,b), cmp(a,c), cmp(b,c)), with each cmp in {-1, 0, +1}.
WEAK_ORDER_CODES = np.asarray(
    sorted(
        {
            0,   # a < b < c
            1,   # a < b = c
            2,   # a < c < b
            5,   # a = c < b
            8,   # c < a < b
            9,   # a = b < c
            13,  # a = b = c
            17,  # a = b > c
            18,  # b < a < c
            21,  # a = c > b
            24,  # b < c < a
            25,  # b = c < a
            26,  # c < b < a
        }
    ),
    dtype=np.int8,
)


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
    """Validate Campaign035 and materialize its inherited complete spec."""

    path = path.expanduser().resolve()
    if _sha256(path) != PROTOCOL_SHA256:
        raise Campaign035FeatureError("Campaign035 no-return protocol changed")
    validation = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if not validation["all_bindings_passed"]:
        raise Campaign035FeatureError(
            "Campaign035 no-return protocol has a failed binding"
        )
    delta = json.loads(path.read_text(encoding="utf-8"))
    candidate = delta.get("candidate") or {}
    gates = delta.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    uniqueness = gates.get("uniqueness_after_coverage_only") or {}
    finite = delta.get("finite_development_catalog_if_admitted") or {}
    boundary = delta.get("research_boundary") or {}
    mechanism = (delta.get("source_chain") or {}).get(
        "mechanism_overlap_audit"
    ) or {}
    campaign_delta = delta.get(
        "campaign035_delta_from_effective_campaign034_protocol"
    ) or {}
    appended = uniqueness.get("appended_comparison") or {}
    if not (
        delta.get("version") == 1
        and delta.get("kind")
        == "a_share_three_day_walkforward_campaign035_no_return_preregistration"
        and delta.get("status")
        == (
            "frozen_before_campaign035_minute_candidate_comparison_daily_"
            "price_or_return_values"
        )
        and mechanism.get("sha256") == MECHANISM_AUDIT_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula") == FACTOR_FORMULA
        and tuple(candidate.get("source_projection") or ()) == RAW_COLUMNS
        and candidate.get("forbidden_source_columns")
        == ["open", "high", "low", "volume", "amount"]
        and candidate.get("selected_bar_count") == SELECTED_BAR_COUNT
        and candidate.get("within_half_return_count")
        == 2 * RETURN_COUNT_PER_HALF
        and candidate.get("tuple_length") == 3
        and candidate.get("within_half_tuple_count") == POOLED_TUPLE_COUNT
        and candidate.get("weak_order_state_count") == WEAK_ORDER_STATE_COUNT
        and candidate.get("exact_ties_retained") is True
        and candidate.get("comparison_tolerance") == 0.0
        and candidate.get("include_lunch_return_or_tuple") is False
        and candidate.get("overlapping_tuples_required") is True
        and candidate.get("support_denominator") == POOLED_TUPLE_COUNT
        and candidate.get("entropy_log_base") == "natural"
        and candidate.get("entropy_normalizer") == "ln(13)"
        and candidate.get("valid_range") == [0.0, 1.0]
        and candidate.get("transform_scale_clip_threshold_filter") == "none"
        and candidate.get(
            "strict_only_tie_drop_jitter_rounding_alternate_tuple_length_"
            "deoverlap_subwindow_board_or_year_search"
        )
        is False
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
        and uniqueness.get("inherited_comparison_count") == 55
        and uniqueness.get("inherited_comparison_order_sha256")
        == INHERITED_COMPARISON_ORDER_SHA256
        and appended
        == {"name": C34_FACTOR_NAMES[0], "score_direction": "higher"}
        and uniqueness.get("comparison_factor_count") == 56
        and uniqueness.get("comparison_factor_order_sha256")
        == COMPARISON_ORDER_SHA256
        and uniqueness.get("all_56_must_pass") is True
        and campaign_delta.get("candidate_factor_count") == 1
        and campaign_delta.get("comparison_factor_count") == 56
        and campaign_delta.get("development_trial_count_if_admitted") == 1
        and finite.get("trial_id")
        == "wf035_intraday_return_weak_order_entropy_234t_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("complexity") == 1
        and finite.get("expected_trial_count") == 1
        and finite.get("fold_count") == 3
        and finite.get("purge_local_signal_sessions") == 3
        and finite.get("t_plus_1_and_t_plus_3_must_remain_inside_partition")
        is True
        and boundary.get("external_campaign035_minute_partitions_read") is False
        and boundary.get("candidate_values_read") is False
        and boundary.get("comparison_values_read") is False
        and boundary.get("historical_daily_price_fields_read") is False
        and boundary.get("historical_forward_returns_read") is False
        and boundary.get("training_or_model_fitting_performed") is False
        and boundary.get("provider_request_issued") is False
        and boundary.get(
            "candidate49_historical_return_signal_or_execution_backfill_performed"
        )
        is False
        and boundary.get("candidate50_activation_created") is False
        and boundary.get(
            "current_scoring_selection_sizing_or_orders_performed"
        )
        is False
    ):
        raise Campaign035FeatureError("Campaign035 no-return semantics changed")

    base_spec = campaign034.load_protocol()
    base_gates = base_spec.get("ordered_no_return_gates") or {}
    base_coverage = base_gates.get(
        "coverage_and_capacity_before_comparison_values"
    ) or {}
    base_uniqueness = base_gates.get("uniqueness_after_coverage_only") or {}
    comparisons = copy.deepcopy(
        list(base_uniqueness.get("comparison_factors") or [])
    )
    if not (
        "holding_period_sessions" not in coverage
        and base_coverage.get("holding_period_sessions") == 3
        and len(comparisons) == 55
        and len({str(item.get("name")) for item in comparisons}) == 55
        and _comparison_order_digest(comparisons)
        == INHERITED_COMPARISON_ORDER_SHA256
    ):
        raise Campaign035FeatureError(
            "Campaign035 inherited comparison or holding-period context changed"
        )
    comparisons.append(copy.deepcopy(appended))
    if (
        len({str(item.get("name")) for item in comparisons}) != 56
        or _comparison_order_digest(comparisons) != COMPARISON_ORDER_SHA256
    ):
        raise Campaign035FeatureError(
            "Campaign035 complete comparison library changed"
        )

    runtime_coverage = copy.deepcopy(coverage)
    runtime_coverage["holding_period_sessions"] = 3
    runtime_uniqueness = copy.deepcopy(uniqueness)
    runtime_uniqueness["comparison_factors"] = comparisons
    runtime_gates = {
        "coverage_and_capacity_before_comparison_values": runtime_coverage,
        "uniqueness_after_coverage_only": runtime_uniqueness,
    }
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
    """Compute entropy across 13 exact weak orderings of return triples."""

    closes = np.asarray(closes, dtype=float)
    if closes.ndim != 2 or closes.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign035FeatureError("Campaign035 aligned close shape is invalid")
    finite_closes = np.isfinite(closes).all(axis=1)
    positive_closes = (closes > 0.0).all(axis=1)
    required_valid = finite_closes & positive_closes
    safe_closes = np.where(np.isfinite(closes) & (closes > 0.0), closes, 1.0)
    log_closes = np.log(safe_closes)
    morning = np.diff(log_closes[:, :120], axis=1)
    afternoon = np.diff(log_closes[:, 120:], axis=1)
    if (
        morning.shape[1] != RETURN_COUNT_PER_HALF
        or afternoon.shape != morning.shape
    ):
        raise Campaign035FeatureError("Campaign035 return-vector shape changed")
    finite_returns = np.isfinite(morning).all(axis=1) & np.isfinite(
        afternoon
    ).all(axis=1)
    tuples = np.concatenate(
        (
            np.stack(
                (morning[:, :-2], morning[:, 1:-1], morning[:, 2:]),
                axis=2,
            ),
            np.stack(
                (afternoon[:, :-2], afternoon[:, 1:-1], afternoon[:, 2:]),
                axis=2,
            ),
        ),
        axis=1,
    )
    if tuples.shape[1:] != (POOLED_TUPLE_COUNT, 3):
        raise Campaign035FeatureError("Campaign035 tuple support changed")
    first = tuples[:, :, 0]
    second = tuples[:, :, 1]
    third = tuples[:, :, 2]
    comparisons = np.stack(
        (
            np.sign(first - second),
            np.sign(first - third),
            np.sign(second - third),
        ),
        axis=2,
    ).astype(np.int8)
    codes = (
        (comparisons[:, :, 0] + 1) * 9
        + (comparisons[:, :, 1] + 1) * 3
        + comparisons[:, :, 2]
        + 1
    ).astype(np.int8)
    counts = np.stack(
        [(codes == code).sum(axis=1) for code in WEAK_ORDER_CODES],
        axis=1,
    )
    state_count = counts.sum(axis=1)
    state_count_valid = state_count == POOLED_TUPLE_COUNT
    probabilities = counts.astype(float) / float(POOLED_TUPLE_COUNT)
    with np.errstate(divide="ignore", invalid="ignore"):
        terms = np.where(
            probabilities > 0.0,
            probabilities * np.log(probabilities),
            0.0,
        )
    values = -np.sum(terms, axis=1) / np.log(WEAK_ORDER_STATE_COUNT)
    finite_values = np.isfinite(values)
    in_range = (values >= 0.0) & (values <= 1.0)
    eligible = (
        required_valid
        & finite_returns
        & state_count_valid
        & finite_values
        & in_range
    )
    tie_observations = (
        (comparisons == 0).any(axis=2) & np.isfinite(tuples).all(axis=2)
    ).sum()
    quality = {
        "base_rows": int(len(closes)),
        "invalid_required_close_rows": int((~finite_closes).sum()),
        f"{FACTOR_NAME}__nonpositive_close_rows": int(
            (finite_closes & ~positive_closes).sum()
        ),
        f"{FACTOR_NAME}__nonfinite_return_rows": int(
            (required_valid & ~finite_returns).sum()
        ),
        f"{FACTOR_NAME}__inadmissible_weak_order_rows": int(
            (required_valid & finite_returns & ~state_count_valid).sum()
        ),
        f"{FACTOR_NAME}__state_count_mismatch_rows": int(
            (required_valid & finite_returns & ~state_count_valid).sum()
        ),
        f"{FACTOR_NAME}__exact_tie_tuple_observations": int(tie_observations),
        f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
        f"{FACTOR_NAME}__range_or_nonfinite_rows": int(
            (
                required_valid
                & finite_returns
                & state_count_valid
                & (~finite_values | ~in_range)
            ).sum()
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
    manifest, verification = (
        campaign034.campaign033.campaign032.executor._verify_prior_snapshot(
            path=spec["path"],
            manifest_sha256=spec["sha256"],
            dataset_sha256=spec["dataset_sha256"],
            kind=spec["kind"],
            factor_names=spec["all_factors"],
            output_columns=spec["output_columns"],
            workers=workers,
        )
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
    """Apply coverage before the complete frozen 56-factor library."""

    if not SNAPSHOT_MANIFEST_SHA256 or not SNAPSHOT_DATASET_SHA256:
        raise Campaign035FeatureError(
            "bind Campaign035 snapshot fingerprints before audit"
        )
    _generated["_bind_executor"]()
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_protocol()
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    if _sha256(manifest_path) != SNAPSHOT_MANIFEST_SHA256:
        raise Campaign035FeatureError("Campaign035 snapshot manifest changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    existing = sorted(experiment_root.glob("*_campaign035_no_return_audit.json"))
    if existing:
        if len(existing) != 1 or not NO_RETURN_AUDIT_SHA256:
            raise Campaign035FeatureError(
                "existing Campaign035 audit is ambiguous or unbound"
            )
        if _sha256(existing[0]) != NO_RETURN_AUDIT_SHA256:
            raise Campaign035FeatureError("Campaign035 audit changed")
        return existing[0]
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    print("building Campaign035 no-price quality/listing eligibility", flush=True)
    foundation = campaign034.campaign033.campaign032.foundation
    engine = campaign034.campaign033.campaign032.engine
    eligible_keys = foundation.quality_listing_eligible_keys(
        campaign034.campaign033.campaign032.load_protocol()
    )
    candidate = engine.load_factor_frame(manifest_path, manifest, FACTOR_NAME)
    quality_frame, coverage = engine.coverage_and_capacity(
        candidate,
        eligible_keys,
        spec,
        FACTOR_NAME,
    )
    del candidate, eligible_keys
    gc.collect()
    if coverage["gate_passed_before_comparison_values"]:
        gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
        expected_order = [
            str(item["name"]) for item in gate["comparison_factors"]
        ]
        keys, values = engine._sorted_candidate_arrays(
            quality_frame,
            FACTOR_NAME,
        )
        chain, candidate49_manifest_path, candidate49_manifest = (
            engine._comparison_chain(data_root)
        )
        comparisons, frozen_verifications = (
            engine._uniqueness_against_frozen_library(
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
            campaign034.campaign033.campaign032._snapshot_specs_from_campaign031()
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
                    path=campaign034.campaign033.C32_SNAPSHOT_PATH,
                    manifest_sha256=campaign034.campaign033.C32_SNAPSHOT_SHA256,
                    dataset_sha256=campaign034.campaign033.C32_DATASET_SHA256,
                    factors=campaign034.campaign033.C32_FACTOR_NAMES,
                ),
                _snapshot_spec(
                    campaign=33,
                    path=campaign034.C33_SNAPSHOT_PATH,
                    manifest_sha256=campaign034.C33_SNAPSHOT_SHA256,
                    dataset_sha256=campaign034.C33_DATASET_SHA256,
                    factors=campaign034.C33_FACTOR_NAMES,
                ),
                _snapshot_spec(
                    campaign=34,
                    path=C34_SNAPSHOT_PATH,
                    manifest_sha256=C34_SNAPSHOT_SHA256,
                    dataset_sha256=C34_DATASET_SHA256,
                    factors=C34_FACTOR_NAMES,
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
                    campaign034.campaign033.campaign032.executor._prior_comparisons(
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
            and len(comparisons) == 56
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
    research = campaign034.campaign033.campaign032.research
    run_id = f"{research._timestamp()}_campaign035_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign035_no_return_audit",
        "status": (
            "completed_with_one_admissible_factor_pending_walkforward_preregistration"
            if admitted
            else "completed_zero_admissible_factors_stop_before_historical_returns"
        ),
        "run_id": run_id,
        "created_at": research._timestamp(),
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
            "freeze the exact one-trial Campaign035 walk-forward catalog before "
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
    foundation.atomic_write_json(record, destination)
    return destination


def status(data_root: Path, experiment_root: Path) -> dict[str, Any]:
    manifest_path = output_root(
        data_root.expanduser().resolve()
    ) / "snapshot_manifest.json"
    audits = sorted(
        experiment_root.expanduser().resolve().glob(
            "*_campaign035_no_return_audit.json"
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
_generated["OUTPUT_RUN_ID"] = OUTPUT_RUN_ID
_generated["PROTOCOL_SHA256"] = PROTOCOL_SHA256
_generated["SNAPSHOT_MANIFEST_SHA256"] = SNAPSHOT_MANIFEST_SHA256
_generated["SNAPSHOT_DATASET_SHA256"] = SNAPSHOT_DATASET_SHA256
_generated["NO_RETURN_AUDIT_SHA256"] = NO_RETURN_AUDIT_SHA256
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
