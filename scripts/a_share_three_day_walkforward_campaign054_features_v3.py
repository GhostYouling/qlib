#!/usr/bin/env python3
"""Authorized Campaign054 numerical and publication-evidence repair."""

from __future__ import annotations

import re

import numpy as np

try:
    import scripts.a_share_three_day_walkforward_campaign054_features_v2 as frozen
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign054_features_v2 as frozen


runner = frozen.runner
EXPECTED_V2_ENTRYPOINT_SHA256 = (
    "8fa465b07e7b056c0f038bbfe4c43684a44dea415f7534e78af55951406430a7"
)
REPAIR_AUTHORIZATION = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_054_snapshot_v1_prebinding_failure_repair_20260803.json"
)
EXPECTED_REPAIR_AUTHORIZATION_SHA256 = (
    "e5df12f500470243f232c1ccb3265eb5df517e82199efd2afb7ddb2bbca99e87"
)
FAILED_V1_SNAPSHOT = (
    runner.DEFAULT_DATA_ROOT
    / "derived/a_share/rich/tushare/minute_walkforward_campaign054_feature_library"
    / runner.OUTPUT_RUN_ID
    / "snapshot_manifest.json"
)
EXPECTED_FAILED_V1_SNAPSHOT_SHA256 = (
    "dd893a54fe04e336bcff3730c96e1181e7c429ccb9b25a7a768c0d96a07d93ed"
)
REPAIRED_OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign054_feature_library_v2"
)

if (
    runner._sha256(runner.Path(frozen.__file__).resolve())
    != EXPECTED_V2_ENTRYPOINT_SHA256
):
    raise runner.Campaign054FeatureError("Campaign054 frozen v2 entrypoint changed")
runner._require_file(
    REPAIR_AUTHORIZATION,
    EXPECTED_REPAIR_AUTHORIZATION_SHA256,
    "Campaign054 v1 prebinding failure-repair authorization",
)
runner._require_file(
    FAILED_V1_SNAPSHOT,
    EXPECTED_FAILED_V1_SNAPSHOT_SHA256,
    "Campaign054 failed unbound v1 snapshot",
)


def compute_factor_values(
    volumes: np.ndarray,
    amounts: np.ndarray,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray], dict[str, int]]:
    """Use algebraically identical differences to avoid common-offset loss."""

    volumes = np.asarray(volumes, dtype=float)
    amounts = np.asarray(amounts, dtype=float)
    if volumes.ndim != 2 or volumes.shape[1] != 240:
        raise runner.Campaign054FeatureError("volumes must have shape (n, 240)")
    if amounts.shape != volumes.shape:
        raise runner.Campaign054FeatureError("amounts must match volumes shape")

    raw_valid = (
        np.isfinite(volumes).all(axis=1)
        & np.isfinite(amounts).all(axis=1)
        & (volumes >= 0.0).all(axis=1)
        & (amounts >= 0.0).all(axis=1)
    )
    volume_positive = volumes > 0.0
    amount_positive = amounts > 0.0
    one_sided_zero = np.logical_xor(volume_positive, amount_positive).any(axis=1)
    active = volume_positive & amount_positive
    active_count = active.sum(axis=1)
    total_weight = np.where(
        raw_valid, np.where(active, volumes, 0.0).sum(axis=1), np.nan
    )
    eligible_input = (
        raw_valid
        & ~one_sided_zero
        & (active_count >= runner.MINIMUM_ACTIVE_BARS)
        & np.isfinite(total_weight)
        & (total_weight > 0.0)
    )

    log_prices = np.full(volumes.shape, np.inf, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        log_prices[active] = np.log(amounts[active]) - np.log(volumes[active])
    finite_active_prices = np.where(
        active, np.isfinite(log_prices), True
    ).all(axis=1)
    eligible_input &= finite_active_prices

    order = np.argsort(log_prices, axis=1, kind="stable")
    sorted_prices = np.take_along_axis(log_prices, order, axis=1)
    sorted_weights = np.take_along_axis(
        np.where(active, volumes, 0.0), order, axis=1
    )
    cumulative = np.cumsum(sorted_weights, axis=1)
    quantiles: list[np.ndarray] = []
    for probability in (0.25, 0.5, 0.75):
        reached = cumulative >= (probability * total_weight)[:, None]
        index = reached.argmax(axis=1)
        quantiles.append(sorted_prices[np.arange(len(volumes)), index])
    q25, q50, q75 = quantiles
    lower_half = q50 - q25
    upper_half = q75 - q50
    spread = lower_half + upper_half
    eligible = (
        eligible_input
        & np.isfinite(q25)
        & np.isfinite(q50)
        & np.isfinite(q75)
        & (lower_half >= 0.0)
        & (upper_half >= 0.0)
        & (spread > 0.0)
    )
    score = np.full(len(volumes), np.nan, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        score[eligible] = (
            upper_half[eligible] - lower_half[eligible]
        ) / spread[eligible]
    in_range = (
        np.isfinite(score)
        & (score >= runner.LOWER_BOUND - runner.ENDPOINT_TOLERANCE)
        & (score <= runner.UPPER_BOUND + runner.ENDPOINT_TOLERANCE)
    )
    score[np.isfinite(score)] = np.clip(
        score[np.isfinite(score)], runner.LOWER_BOUND, runner.UPPER_BOUND
    )
    eligible &= in_range
    score[~eligible] = np.nan
    quality = {
        f"{runner.FACTOR_NAME}__invalid_raw_rows": int((~raw_valid).sum()),
        f"{runner.FACTOR_NAME}__one_sided_zero_rows": int(
            (raw_valid & one_sided_zero).sum()
        ),
        f"{runner.FACTOR_NAME}__insufficient_active_bar_rows": int(
            (
                raw_valid
                & ~one_sided_zero
                & (active_count < runner.MINIMUM_ACTIVE_BARS)
            ).sum()
        ),
        f"{runner.FACTOR_NAME}__invalid_active_price_rows": int(
            (raw_valid & ~one_sided_zero & ~finite_active_prices).sum()
        ),
        f"{runner.FACTOR_NAME}__nonpositive_quantile_spread_rows": int(
            (eligible_input & ~(spread > 0.0)).sum()
        ),
        f"{runner.FACTOR_NAME}__range_or_nonfinite_score_rows": int(
            ((eligible_input & (spread > 0.0)) & ~in_range).sum()
        ),
        f"{runner.FACTOR_NAME}__eligible_rows": int(eligible.sum()),
    }
    return {runner.FACTOR_NAME: score}, {runner.FACTOR_NAME: eligible}, quality


def output_root(data_root: runner.Path) -> runner.Path:
    return (
        data_root.expanduser().resolve()
        / "derived/a_share/rich/tushare/minute_walkforward_campaign054_feature_library"
        / REPAIRED_OUTPUT_RUN_ID
    )


_base_validate_snapshot_manifest = runner._validate_snapshot_manifest


def clean_protocol_evidence(evidence: dict[str, object]) -> dict[str, object]:
    """Drop misleading evidence inherited from a numbered prior campaign."""

    return {
        key: value
        for key, value in evidence.items()
        if not re.match(r"^campaign\d{3}_", key)
        or key.startswith("campaign054_")
    }


def validate_snapshot_manifest(
    manifest: dict[str, object], *, require_fingerprint_constants: bool
) -> None:
    _base_validate_snapshot_manifest(
        manifest,
        require_fingerprint_constants=require_fingerprint_constants,
    )
    evidence = dict(manifest.get("protocol_evidence") or {})
    if not require_fingerprint_constants:
        evidence = clean_protocol_evidence(evidence)
        manifest["protocol_evidence"] = evidence
    stale = [
        key
        for key in evidence
        if re.match(r"^campaign\d{3}_", key)
        and not key.startswith("campaign054_")
    ]
    if stale:
        raise runner.Campaign054FeatureError(
            "Campaign054 snapshot retained stale campaign evidence"
        )


runner.OUTPUT_RUN_ID = REPAIRED_OUTPUT_RUN_ID
runner.compute_factor_values = compute_factor_values
runner.output_root = output_root
runner._validate_snapshot_manifest = validate_snapshot_manifest
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(runner.main())
