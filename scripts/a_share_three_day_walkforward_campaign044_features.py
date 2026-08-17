#!/usr/bin/env python3
"""Build and audit the Campaign044 complete-terminal-library consensus.

Campaign044 is a historical-research meta factor.  It reads every one of the
66 terminal factor snapshots, explicitly excludes active prospective
Candidate49, and computes one equal-weight average of same-session directional
percentile ranks on all-component common support.  This module never reads a
daily price or forward return.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import datetime as dt
import gc
import hashlib
import json
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow.dataset as pa_dataset


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a_share_three_day_preregistration_binding_validator as bindings  # noqa: E402
import a_share_three_day_walkforward_campaign043_features as campaign043  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs"
    / "a_share_three_day_walkforward_campaign_044_no_return_preregistration.json"
)
DEFAULT_DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
DEFAULT_EXPERIMENT_ROOT = (
    REPO_ROOT
    / "data"
    / "experiments"
    / "short_horizon"
    / "historical_walkforward"
    / "campaign_044"
    / "no_return"
)

FACTOR_NAME = "full_terminal_library_directional_percentile_consensus_66f"
FACTOR_NAMES = (FACTOR_NAME,)
FACTOR_DIRECTIONS = {FACTOR_NAME: "higher"}
FACTOR_RANGES = {FACTOR_NAME: (0.0, 1.0)}
FACTOR_FORMULA = (
    "On each signal session, require common finite eligible support across all "
    "66 terminal factors and at least 50 names; compute every frozen-direction "
    "average-tie empirical percentile rank and take their arithmetic mean with "
    "weight 1/66."
)
FACTOR_FORMULAS = {FACTOR_NAME: FACTOR_FORMULA}
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)
ACTIVE_CANDIDATE49_FACTOR = "intraday_cumulative_vwap_crossing_rate_240m"
SOURCE_FACTOR_COUNT = 66
SOURCE_FACTOR_ORDER_SHA256 = (
    "71a34e7decf7ba4a456cff4e08b0ea034a3919ee62edf5eb3bec603eb50a5bed"
)
MINIMUM_COMMON_SUPPORT_NAMES = 50
EXPECTED_PARTITIONS = 33_015
EXPECTED_ROWS = 7_724_498
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_"
    "walkforward_campaign044_feature_library_v1"
)
PROTOCOL_SHA256 = (
    "1037d27b173f4fb63c75672c4da50c6616f1f1eb3ae1917ecf291fc2d2644f69"
)

# Bind after immutable publication and its ordered no-return audit.
SNAPSHOT_MANIFEST_SHA256 = (
    "ab5d08bf5c9ca8737c32b13e8a6fcc68d9cfb26fc8cdb43377d34bde5d724964"
)
SNAPSHOT_DATASET_SHA256 = (
    "295c023b3f6a76605ab0413f6ab9410e2dabcb4cb2d262de7a62618818a55487"
)
NO_RETURN_AUDIT_SHA256 = (
    "5bf91fae0ab73f04680e840d8a5280250e0e3091f80fe47684d1656fbde10776"
)


class Campaign044FeatureError(RuntimeError):
    """Fail-closed Campaign044 feature or no-return error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _value_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _comparison_order_digest(items: list[dict[str, Any]]) -> str:
    return _value_sha256(
        [[str(item["name"]), str(item["score_direction"])] for item in items]
    )


def _require_file(path: Path, sha256: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != sha256:
        raise Campaign044FeatureError(f"{label} changed: {path}")


def _context() -> tuple[Any, Any, Any, Any, Any, Any]:
    prior = (
        campaign043.campaign042.campaign041.campaign040.campaign039
        .campaign038.campaign037.campaign036.campaign035.campaign034
        .campaign033.campaign032
    )
    foundation = prior.foundation
    engine = prior.engine
    executor = prior.executor
    candidate49 = engine.candidate49
    comparison_engine = engine.comparison_engine
    return prior, foundation, engine, executor, candidate49, comparison_engine


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    _require_file(path, PROTOCOL_SHA256, "Campaign044 no-return protocol")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign044FeatureError("Campaign044 protocol bindings changed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    candidate = spec.get("candidate") or {}
    source_factors = list(candidate.get("source_factors") or [])
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get(
        "coverage_and_capacity_before_component_correlation_calculation"
    ) or {}
    dominance = gates.get("single_component_dominance_after_coverage_only") or {}
    attempts = list(spec.get("append_only_attempt_catalog") or [])
    if not (
        spec.get("version") == 1
        and spec.get("kind")
        == "a_share_three_day_walkforward_campaign044_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign044_source_factor_candidate_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and int(candidate.get("source_factor_count", -1)) == SOURCE_FACTOR_COUNT
        and len(source_factors) == SOURCE_FACTOR_COUNT
        and len({str(item.get("name") or "") for item in source_factors})
        == SOURCE_FACTOR_COUNT
        and ACTIVE_CANDIDATE49_FACTOR
        not in {str(item.get("name") or "") for item in source_factors}
        and _comparison_order_digest(source_factors)
        == SOURCE_FACTOR_ORDER_SHA256
        and candidate.get("source_factor_order_sha256")
        == SOURCE_FACTOR_ORDER_SHA256
        and int(candidate.get("minimum_common_support_names", -1))
        == MINIMUM_COMMON_SUPPORT_NAMES
        and candidate.get("all_components_required") is True
        and float(coverage.get("minimum_median_coverage", -1)) == 0.95
        and float(coverage.get("minimum_p05_coverage", -1)) == 0.9
        and int(coverage.get("minimum_p05_eligible_names", -1)) == 50
        and int(
            coverage.get("minimum_non_overlapping_three_session_cohorts", -1)
        )
        == 200
        and int(coverage.get("minimum_observed_calendar_years", -1)) == 5
        and int(dominance.get("comparison_factor_count", -1))
        == SOURCE_FACTOR_COUNT
        and dominance.get("comparison_factor_order_sha256")
        == SOURCE_FACTOR_ORDER_SHA256
        and dominance.get("all_66_must_pass") is True
        and float(
            dominance.get(
                "maximum_allowed_absolute_median_daily_rank_correlation", -1
            )
        )
        == 0.8
        and len(attempts) == 3
        and attempts[0].get("kind") == "pre_value_design_rejection"
        and attempts[0].get("source_factor_values_read") is False
        and attempts[1].get("kind") == "pre_value_design_rejection"
        and attempts[1].get("source_factor_values_read") is False
        and attempts[2].get("trial_id")
        == "wf044_full_terminal_library_directional_percentile_consensus_66f_single_higher"
    ):
        raise Campaign044FeatureError("Campaign044 protocol semantics changed")
    return spec


def source_factor_specs(
    spec: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    protocol = spec or load_protocol()
    return [
        {
            "name": str(item["name"]),
            "score_direction": str(item["score_direction"]),
        }
        for item in protocol["candidate"]["source_factors"]
    ]


def _directional_percentile(
    values: np.ndarray,
    date_codes: np.ndarray,
    *,
    direction: str,
) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    date_codes = np.asarray(date_codes)
    if (
        values.ndim != 1
        or date_codes.ndim != 1
        or len(values) != len(date_codes)
        or not np.isfinite(values).all()
        or direction not in {"higher", "lower"}
    ):
        raise Campaign044FeatureError("invalid directional-percentile input")
    if len(values) == 0:
        return np.empty(0, dtype=float)
    ranked = pd.Series(values).groupby(
        pd.Series(date_codes), sort=False, observed=True
    ).rank(
        method="average",
        pct=True,
        ascending=direction == "higher",
    )
    result = ranked.to_numpy(dtype=float)
    if not np.isfinite(result).all() or (result <= 0.0).any() or (result > 1.0).any():
        raise Campaign044FeatureError("directional percentile escaped (0,1]")
    return result


def compute_consensus_frame(
    panel: pd.DataFrame,
    *,
    factors: list[dict[str, str]] | None = None,
    minimum_common_support_names: int = MINIMUM_COMMON_SUPPORT_NAMES,
) -> pd.DataFrame:
    """Compute the frozen consensus on a synthetic or already aligned panel."""

    specs = factors or source_factor_specs()
    names = [item["name"] for item in specs]
    required = ["trade_date", "symbol", *names]
    if (
        len(specs) < 1
        or len(names) != len(set(names))
        or minimum_common_support_names < 1
        or any(column not in panel.columns for column in required)
    ):
        raise Campaign044FeatureError("consensus panel schema is invalid")
    work = panel.loc[:, required].copy()
    work["trade_date"] = pd.to_datetime(work["trade_date"], errors="coerce").dt.normalize()
    work["symbol"] = work["symbol"].astype(str).str.upper()
    if work["trade_date"].isna().any() or work.duplicated(
        ["trade_date", "symbol"]
    ).any():
        raise Campaign044FeatureError("consensus panel keys are invalid")
    finite = np.ones(len(work), dtype=bool)
    for name in names:
        work[name] = pd.to_numeric(work[name], errors="coerce")
        finite &= np.isfinite(work[name].to_numpy(dtype=float))
    counts = (
        work.loc[finite]
        .groupby("trade_date", observed=True, sort=False)
        .size()
    )
    accepted_dates = set(counts[counts >= minimum_common_support_names].index)
    eligible = finite & work["trade_date"].isin(accepted_dates).to_numpy(dtype=bool)
    score = np.full(len(work), np.nan, dtype=float)
    if eligible.any():
        date_codes = pd.factorize(work.loc[eligible, "trade_date"], sort=True)[0]
        total = np.zeros(int(eligible.sum()), dtype=float)
        for item in specs:
            total += _directional_percentile(
                work.loc[eligible, item["name"]].to_numpy(dtype=float),
                date_codes,
                direction=item["score_direction"],
            )
        score[eligible] = total / len(specs)
    if (
        not np.isfinite(score[eligible]).all()
        or (score[eligible] < 0.0).any()
        or (score[eligible] > 1.0).any()
    ):
        raise Campaign044FeatureError("consensus score escaped [0,1]")
    return pd.DataFrame(
        {
            "trade_date": work["trade_date"],
            "symbol": work["symbol"],
            FACTOR_NAME: score,
            f"{FACTOR_NAME}_eligible": eligible,
        }
    )


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived"
        / "a_share"
        / "rich"
        / "tushare"
        / "minute_walkforward_campaign044_feature_library"
        / OUTPUT_RUN_ID
    )


def _snapshot_spec(
    *,
    campaign: int,
    path: Path,
    manifest_sha256: str,
    dataset_sha256: str,
    factors: tuple[str, ...],
) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    columns = ["trade_date", "symbol", "provider"]
    for factor in factors:
        columns.extend([factor, f"{factor}_eligible"])
    return {
        "family": "walkforward_campaign_snapshot",
        "campaign": campaign,
        "path": path,
        "sha256": manifest_sha256,
        "dataset_sha256": dataset_sha256,
        "kind": str(manifest.get("kind") or ""),
        "factors": factors,
        "all_factors": factors,
        "output_columns": tuple(columns),
        "manifest": manifest,
    }


def _build_source_catalog(
    *,
    data_root: Path,
    workers: int,
    verify_files: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Resolve all 66 terminal sources without loading Candidate49's snapshot."""

    spec = load_protocol()
    expected_specs = source_factor_specs(spec)
    expected_names = [item["name"] for item in expected_specs]
    prior, _, engine, executor, candidate49, comparison_engine = _context()
    candidate49_spec = candidate49.load_preregistration()
    chain = candidate49.validate_external_chain(candidate49_spec, data_root)
    joint_manifest = chain[1]
    joint_path = Path(chain[3]).resolve()
    base_factors = tuple(candidate49.COMPARISON_FACTORS[:4])
    catalog: list[dict[str, Any]] = [
        {
            "family": "pre_campaign004_terminal_snapshot",
            "path": joint_path,
            "manifest": joint_manifest,
            "factors": base_factors,
        }
    ]
    comparison_pairs = list(zip(chain[4::2], chain[5::2], strict=True))
    remaining = tuple(candidate49.COMPARISON_FACTORS[4:])
    if (
        len(comparison_pairs) != len(remaining)
        or tuple(str(item[0].get("factor_name") or "") for item in comparison_pairs)
        != remaining
    ):
        raise Campaign044FeatureError("pre-Campaign004 terminal source order changed")
    for (manifest, path), factor in zip(comparison_pairs, remaining, strict=True):
        catalog.append(
            {
                "family": "pre_campaign004_terminal_snapshot",
                "path": Path(path).resolve(),
                "manifest": manifest,
                "factors": (factor,),
            }
        )

    prior_specs = list(prior._snapshot_specs_from_campaign031())
    post_specs = list(campaign043._post_campaign031_snapshot_specs())
    c43_binding = spec["source_chain"]["campaign043_terminal_snapshot"]
    c43_path = Path(str(c43_binding["path"])).resolve()
    post_specs.append(
        _snapshot_spec(
            campaign=43,
            path=c43_path,
            manifest_sha256=str(c43_binding["sha256"]),
            dataset_sha256=str(c43_binding["dataset_sha256"]),
            factors=(campaign043.FACTOR_NAME,),
        )
    )
    for item in [*prior_specs, *post_specs]:
        catalog.append(
            {
                "family": "walkforward_campaign_snapshot",
                "campaign": int(item["campaign"]),
                "path": Path(item["path"]).resolve(),
                "sha256": str(item["sha256"]),
                "dataset_sha256": str(item["dataset_sha256"]),
                "kind": str(item["kind"]),
                "manifest": json.loads(Path(item["path"]).read_text(encoding="utf-8")),
                "factors": tuple(item["all_factors"]),
                "all_factors": tuple(item["all_factors"]),
                "output_columns": tuple(item["output_columns"]),
            }
        )
    observed_names = [factor for item in catalog for factor in item["factors"]]
    if (
        observed_names != expected_names
        or len(observed_names) != SOURCE_FACTOR_COUNT
        or ACTIVE_CANDIDATE49_FACTOR in observed_names
    ):
        raise Campaign044FeatureError("complete terminal source catalog changed")

    verifications: dict[str, Any] = {}
    for index, item in enumerate(catalog):
        path = Path(item["path"])
        manifest = item["manifest"]
        key = f"source_{index:02d}_{'_'.join(item['factors'])}"
        observed_manifest_sha = _sha256(path)
        if item["family"] == "walkforward_campaign_snapshot":
            if observed_manifest_sha != item["sha256"]:
                raise Campaign044FeatureError(f"terminal source manifest changed: {path}")
            if verify_files:
                verified_manifest, verification = executor._verify_prior_snapshot(
                    path=path,
                    manifest_sha256=item["sha256"],
                    dataset_sha256=item["dataset_sha256"],
                    kind=item["kind"],
                    factor_names=item["all_factors"],
                    output_columns=item["output_columns"],
                    workers=workers,
                )
                item["manifest"] = verified_manifest
            else:
                verification = {"file_verification_deferred": True}
        else:
            if verify_files:
                verification = comparison_engine._verify_comparison_snapshot_outputs(
                    manifest,
                    path,
                    workers,
                )
            else:
                verification = {"file_verification_deferred": True}
        verifications[key] = {
            "path": str(path),
            "sha256": observed_manifest_sha,
            "dataset_sha256": str(manifest.get("dataset_sha256") or ""),
            "factors": list(item["factors"]),
            **verification,
        }
    return catalog, verifications


def _load_aligned_source_values(
    source: dict[str, Any],
    candidate_keys: np.ndarray,
) -> dict[str, np.ndarray]:
    _, _, engine, _, _, _ = _context()
    return engine._load_filtered_comparison_values_explicit(
        source["manifest"],
        source["factors"],
        candidate_keys,
    )


def _intersect_sorted_master_keys(
    master_keys: np.ndarray,
    master_dates: np.ndarray,
    anchor_keys: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    master_keys = np.asarray(master_keys, dtype=np.int64)
    master_dates = np.asarray(master_dates, dtype="datetime64[ns]")
    anchor_keys = np.asarray(anchor_keys, dtype=np.int64)
    if (
        master_keys.ndim != 1
        or master_dates.ndim != 1
        or anchor_keys.ndim != 1
        or len(master_keys) != len(master_dates)
        or len(master_keys) == 0
        or len(anchor_keys) == 0
        or not np.all(master_keys[:-1] < master_keys[1:])
        or not np.all(anchor_keys[:-1] < anchor_keys[1:])
    ):
        raise Campaign044FeatureError("master or anchor identity keys are invalid")
    positions = np.searchsorted(anchor_keys, master_keys, side="left")
    bounded = positions < len(anchor_keys)
    matched = np.zeros(len(master_keys), dtype=bool)
    matched[bounded] = anchor_keys[positions[bounded]] == master_keys[bounded]
    if not matched.any():
        raise Campaign044FeatureError("quality/listing and minute identities do not overlap")
    return master_keys[matched], master_dates[matched]


def _quality_listing_master_keys() -> tuple[np.ndarray, np.ndarray]:
    prior, foundation, _, _, _, comparison_engine = _context()
    eligible = foundation.quality_listing_eligible_keys(prior.load_protocol())
    work = eligible.loc[:, ["trade_date", "symbol"]].copy()
    work["trade_date"] = pd.to_datetime(work["trade_date"], errors="coerce").dt.normalize()
    work["symbol"] = work["symbol"].astype(str).str.upper()
    if work["trade_date"].isna().any() or work.duplicated(
        ["trade_date", "symbol"]
    ).any():
        raise Campaign044FeatureError("quality/listing master keys changed")
    keys = comparison_engine._compact_stock_day_keys(
        work["trade_date"], work["symbol"]
    )
    order = np.argsort(keys, kind="stable")
    keys = keys[order]
    dates = work["trade_date"].to_numpy(dtype="datetime64[ns]")[order]
    if len(np.unique(keys)) != len(keys):
        raise Campaign044FeatureError("quality/listing master keys are not unique")
    protocol = load_protocol()
    anchor_binding = protocol["source_chain"]["campaign043_terminal_snapshot"]
    anchor_manifest_path = Path(str(anchor_binding["path"])).resolve()
    _require_file(
        anchor_manifest_path,
        str(anchor_binding["sha256"]),
        "Campaign043 identity anchor manifest",
    )
    anchor_manifest = json.loads(anchor_manifest_path.read_text(encoding="utf-8"))
    records = list(anchor_manifest.get("files") or [])
    if len(records) != EXPECTED_PARTITIONS:
        raise Campaign044FeatureError("Campaign043 identity anchor count changed")
    dataset = pa_dataset.dataset(
        [str(Path(record["path"]).resolve()) for record in records],
        format="parquet",
    )
    table = dataset.to_table(columns=["trade_date", "symbol"], use_threads=True)
    anchor = table.to_pandas(split_blocks=True, self_destruct=True)
    del table, dataset
    gc.collect()
    if len(anchor) != EXPECTED_ROWS:
        raise Campaign044FeatureError("Campaign043 identity anchor rows changed")
    anchor["trade_date"] = pd.to_datetime(
        anchor["trade_date"], errors="coerce"
    ).dt.normalize()
    anchor["symbol"] = anchor["symbol"].astype(str).str.upper()
    if anchor["trade_date"].isna().any() or anchor.duplicated(
        ["trade_date", "symbol"]
    ).any():
        raise Campaign044FeatureError("Campaign043 identity anchor keys changed")
    anchor_keys = comparison_engine._compact_stock_day_keys(
        anchor["trade_date"], anchor["symbol"]
    )
    anchor_keys.sort(kind="stable")
    del anchor
    gc.collect()
    return _intersect_sorted_master_keys(keys, dates, anchor_keys)


def _build_score_cache(
    *,
    partial_root: Path,
    final_root: Path,
    data_root: Path,
    workers: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Two-pass bounded-memory common-support and percentile construction."""

    _, foundation, _, _, _, _ = _context()
    cache_path = partial_root / "score_cache.parquet"
    cache_meta_path = partial_root / "score_cache_manifest.json"
    if cache_path.exists() or cache_meta_path.exists():
        if not cache_path.is_file() or not cache_meta_path.is_file():
            raise Campaign044FeatureError("Campaign044 score cache is incomplete")
        meta = json.loads(cache_meta_path.read_text(encoding="utf-8"))
        frame = pd.read_parquet(cache_path, columns=["stock_day_key", FACTOR_NAME])
        if not (
            meta.get("protocol_sha256") == PROTOCOL_SHA256
            and meta.get("source_factor_order_sha256") == SOURCE_FACTOR_ORDER_SHA256
            and meta.get("candidate49_factor_values_read") is False
            and meta.get("historical_forward_return_fields_read") is False
            and meta.get("byte_sha256") == _sha256(cache_path)
            and int(meta.get("rows", -1)) == len(frame)
            and meta.get("frame_sha256") == foundation.frame_digest(frame)
        ):
            raise Campaign044FeatureError("Campaign044 score cache changed")
        keys = frame["stock_day_key"].to_numpy(dtype=np.int64)
        scores = frame[FACTOR_NAME].to_numpy(dtype=float)
        if (
            len(np.unique(keys)) != len(keys)
            or not np.all(keys[:-1] < keys[1:])
            or not np.isfinite(scores).all()
            or (scores < 0.0).any()
            or (scores > 1.0).any()
        ):
            raise Campaign044FeatureError("Campaign044 score cache values changed")
        return keys, scores, meta

    catalog, verifications = _build_source_catalog(
        data_root=data_root,
        workers=workers,
        verify_files=True,
    )
    master_keys, master_dates = _quality_listing_master_keys()
    valid = np.ones(len(master_keys), dtype=bool)
    print(
        f"Campaign044 pass 1/2: intersecting {SOURCE_FACTOR_COUNT} terminal factors",
        flush=True,
    )
    observed = 0
    for source in catalog:
        values = _load_aligned_source_values(source, master_keys)
        for factor in source["factors"]:
            valid &= np.isfinite(values.pop(factor))
            observed += 1
            print(
                f"Campaign044 common-support factors={observed}/{SOURCE_FACTOR_COUNT} "
                f"rows={int(valid.sum()):,}",
                flush=True,
            )
        del values
        gc.collect()
    candidate_indices = np.flatnonzero(valid)
    candidate_dates = master_dates[candidate_indices]
    unique_dates, inverse, counts = np.unique(
        candidate_dates,
        return_inverse=True,
        return_counts=True,
    )
    keep = counts[inverse] >= MINIMUM_COMMON_SUPPORT_NAMES
    common_indices = candidate_indices[keep]
    common_keys = master_keys[common_indices]
    common_dates = master_dates[common_indices]
    _, date_codes = np.unique(common_dates, return_inverse=True)
    if len(common_keys) == 0 or len(unique_dates) == 0:
        raise Campaign044FeatureError("Campaign044 common support is empty")
    total = np.zeros(len(common_keys), dtype=float)
    directions = {
        item["name"]: item["score_direction"] for item in source_factor_specs()
    }
    print(
        f"Campaign044 pass 2/2: ranking {SOURCE_FACTOR_COUNT} terminal factors "
        f"on {len(common_keys):,} common rows",
        flush=True,
    )
    observed = 0
    for source in catalog:
        values = _load_aligned_source_values(source, common_keys)
        for factor in source["factors"]:
            factor_values = values.pop(factor)
            if not np.isfinite(factor_values).all():
                raise Campaign044FeatureError(
                    f"terminal source eligibility changed between passes: {factor}"
                )
            total += _directional_percentile(
                factor_values,
                date_codes,
                direction=directions[factor],
            )
            observed += 1
            print(
                f"Campaign044 ranked factors={observed}/{SOURCE_FACTOR_COUNT}",
                flush=True,
            )
        del values
        gc.collect()
    scores = total / SOURCE_FACTOR_COUNT
    if (
        not np.isfinite(scores).all()
        or (scores < 0.0).any()
        or (scores > 1.0).any()
        or len(np.unique(common_keys)) != len(common_keys)
        or not np.all(common_keys[:-1] < common_keys[1:])
    ):
        raise Campaign044FeatureError("Campaign044 composite score is invalid")
    cache = pd.DataFrame(
        {"stock_day_key": common_keys, FACTOR_NAME: scores}
    )
    foundation.atomic_write_frame(cache, cache_path)
    session_counts = pd.Series(common_dates).value_counts(sort=False)
    meta = {
        "version": 1,
        "kind": "a_share_three_day_walkforward_campaign044_score_cache",
        "status": "complete_before_daily_price_or_return_read",
        "path": str(final_root / cache_path.name),
        "protocol_sha256": PROTOCOL_SHA256,
        "source_factor_count": SOURCE_FACTOR_COUNT,
        "source_factor_order_sha256": SOURCE_FACTOR_ORDER_SHA256,
        "source_snapshot_verifications": verifications,
        "quality_listing_master_rows": int(len(master_keys)),
        "all_component_common_rows_before_session_minimum": int(valid.sum()),
        "eligible_rows": int(len(cache)),
        "eligible_sessions": int(len(session_counts)),
        "minimum_common_support_names": MINIMUM_COMMON_SUPPORT_NAMES,
        "eligible_names_min": int(session_counts.min()),
        "eligible_names_median": float(session_counts.median()),
        "rows": int(len(cache)),
        "byte_sha256": _sha256(cache_path),
        "frame_sha256": foundation.frame_digest(cache),
        "source_terminal_factor_values_read": True,
        "candidate49_factor_values_read": False,
        "daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "training_or_model_fitting_performed": False,
    }
    foundation.atomic_write_json(meta, cache_meta_path)
    return common_keys, scores, meta


def _checkpoint_paths(
    partial_root: Path,
    symbol: str,
    year: int,
) -> tuple[Path, Path]:
    return (
        partial_root / "partitions" / symbol / f"{year}.parquet",
        partial_root / ".metadata" / symbol / f"{year}.json",
    )


def _process_partition(
    *,
    partial_root: Path,
    final_root: Path,
    anchor_record: dict[str, Any],
    common_keys: np.ndarray,
    scores: np.ndarray,
    cache_sha256: str,
) -> tuple[dict[str, Any], Counter[str], bool]:
    _, foundation, _, _, _, comparison_engine = _context()
    symbol = str(anchor_record["symbol"])
    year = int(anchor_record["year"])
    data_path, sidecar_path = _checkpoint_paths(partial_root, symbol, year)
    final_data = final_root / "partitions" / symbol / f"{year}.parquet"
    if data_path.exists() or sidecar_path.exists():
        if not data_path.is_file() or not sidecar_path.is_file():
            raise Campaign044FeatureError(
                f"incomplete Campaign044 checkpoint for {symbol}/{year}"
            )
        record = json.loads(sidecar_path.read_text(encoding="utf-8"))
        frame = pd.read_parquet(data_path, columns=list(OUTPUT_COLUMNS))
        if not (
            record.get("protocol_sha256") == PROTOCOL_SHA256
            and record.get("score_cache_sha256") == cache_sha256
            and record.get("anchor_source_sha256")
            == anchor_record.get("output_byte_sha256")
            and record.get("output_byte_sha256") == _sha256(data_path)
            and int(record.get("rows", -1)) == len(frame)
            and record.get("output_frame_sha256") == foundation.frame_digest(frame)
        ):
            raise Campaign044FeatureError(
                f"Campaign044 checkpoint changed for {symbol}/{year}"
            )
        record["path"] = str(final_data)
        dates = Counter(
            pd.to_datetime(
                frame.loc[frame[f"{FACTOR_NAME}_eligible"], "trade_date"]
            ).dt.date.astype(str)
        )
        return record, dates, True

    anchor_path = Path(str(anchor_record["path"]))
    if _sha256(anchor_path) != anchor_record.get("output_byte_sha256"):
        raise Campaign044FeatureError(
            f"Campaign043 anchor partition changed for {symbol}/{year}"
        )
    anchor = pd.read_parquet(
        anchor_path,
        columns=["trade_date", "symbol", "provider"],
    )
    trade_date = pd.to_datetime(anchor["trade_date"], errors="coerce").dt.normalize()
    symbols = anchor["symbol"].astype(str).str.upper()
    keys = comparison_engine._compact_stock_day_keys(trade_date, symbols)
    positions = np.searchsorted(common_keys, keys, side="left")
    bounded = positions < len(common_keys)
    eligible = np.zeros(len(keys), dtype=bool)
    eligible[bounded] = common_keys[positions[bounded]] == keys[bounded]
    values = np.full(len(keys), np.nan, dtype=float)
    values[eligible] = scores[positions[eligible]]
    frame = pd.DataFrame(
        {
            "trade_date": trade_date,
            "symbol": symbols,
            "provider": anchor["provider"].astype(str),
            FACTOR_NAME: values,
            f"{FACTOR_NAME}_eligible": eligible,
        },
        columns=OUTPUT_COLUMNS,
    )
    if (
        frame["trade_date"].isna().any()
        or frame.duplicated(["trade_date", "symbol"]).any()
        or frame.loc[~frame[f"{FACTOR_NAME}_eligible"], FACTOR_NAME].notna().any()
    ):
        raise Campaign044FeatureError(
            f"Campaign044 output keys changed for {symbol}/{year}"
        )
    foundation.atomic_write_frame(frame, data_path)
    record = {
        "symbol": symbol,
        "year": year,
        "path": str(final_data),
        "protocol_sha256": PROTOCOL_SHA256,
        "output_run_id": OUTPUT_RUN_ID,
        "factor_names": [FACTOR_NAME],
        "anchor_source_path": str(anchor_path),
        "anchor_source_sha256": str(anchor_record["output_byte_sha256"]),
        "score_cache_sha256": cache_sha256,
        "rows": int(len(frame)),
        "factor_eligible_rows": {FACTOR_NAME: int(eligible.sum())},
        "quality": {
            "base_rows": int(len(frame)),
            f"{FACTOR_NAME}__eligible_rows": int(eligible.sum()),
            f"{FACTOR_NAME}__ineligible_rows": int((~eligible).sum()),
        },
        "source_terminal_factor_values_read": True,
        "candidate49_factor_values_read": False,
        "daily_price_fields_read": [],
        "forward_return_fields_read": False,
        "output_byte_sha256": _sha256(data_path),
        "output_frame_sha256": foundation.frame_digest(frame),
    }
    foundation.atomic_write_json(record, sidecar_path)
    dates = Counter(trade_date[eligible].dt.date.astype(str))
    return record, dates, False


def _process_symbol(
    records: list[dict[str, Any]],
    *,
    partial_root: Path,
    final_root: Path,
    common_keys: np.ndarray,
    scores: np.ndarray,
    cache_sha256: str,
) -> tuple[list[dict[str, Any]], Counter[str], int]:
    output: list[dict[str, Any]] = []
    dates: Counter[str] = Counter()
    resumed = 0
    for record in sorted(records, key=lambda item: int(item["year"])):
        item, item_dates, was_resumed = _process_partition(
            partial_root=partial_root,
            final_root=final_root,
            anchor_record=record,
            common_keys=common_keys,
            scores=scores,
            cache_sha256=cache_sha256,
        )
        output.append(item)
        dates.update(item_dates)
        resumed += int(was_resumed)
    return output, dates, resumed


def _validate_snapshot_manifest(
    manifest: dict[str, Any],
    *,
    require_fingerprint_constants: bool,
) -> None:
    eligible = manifest.get("factor_eligible_rows") or {}
    if not (
        manifest.get("schema_version") == 1
        and manifest.get("kind")
        == "a_share_three_day_walkforward_campaign044_feature_snapshot"
        and manifest.get("status")
        == "feature_library_complete_pending_ordered_no_return_gates"
        and manifest.get("protocol_sha256") == PROTOCOL_SHA256
        and manifest.get("output_run_id") == OUTPUT_RUN_ID
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == FACTOR_DIRECTIONS
        and manifest.get("factor_formulas") == FACTOR_FORMULAS
        and manifest.get("source_factor_count") == SOURCE_FACTOR_COUNT
        and manifest.get("source_factor_order_sha256")
        == SOURCE_FACTOR_ORDER_SHA256
        and ACTIVE_CANDIDATE49_FACTOR
        not in set(manifest.get("source_factor_names") or [])
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and manifest.get("rows") == EXPECTED_ROWS
        and len(manifest.get("files") or []) == EXPECTED_PARTITIONS
        and isinstance(eligible.get(FACTOR_NAME), int)
        and manifest.get("source_terminal_factor_values_read") is True
        and manifest.get("candidate49_factor_values_read") is False
        and manifest.get("daily_price_fields_read") == []
        and manifest.get("forward_return_fields_read") is False
        and manifest.get("candidate49_historical_return_read") is False
        and manifest.get("training_or_model_fitting_performed") is False
        and manifest.get("current_scoring_selection_sizing_or_orders_performed")
        is False
    ):
        raise Campaign044FeatureError("Campaign044 snapshot semantics changed")
    if require_fingerprint_constants and not (
        SNAPSHOT_MANIFEST_SHA256
        and SNAPSHOT_DATASET_SHA256
        and manifest.get("dataset_sha256") == SNAPSHOT_DATASET_SHA256
    ):
        raise Campaign044FeatureError(
            "Campaign044 snapshot fingerprint constants are not bound"
        )


def build_snapshot(*, data_root: Path, workers: int) -> Path:
    if workers < 1 or workers > 8:
        raise ValueError("--workers must be between 1 and 8")
    data_root = data_root.expanduser().resolve()
    spec = load_protocol()
    final_root = output_root(data_root)
    final_manifest = final_root / "snapshot_manifest.json"
    partial_root = final_root.parent / f".{OUTPUT_RUN_ID}.partial"
    if final_root.exists():
        if not final_manifest.is_file() or not SNAPSHOT_MANIFEST_SHA256:
            raise Campaign044FeatureError(
                "published Campaign044 snapshot exists but is not fingerprint-bound"
            )
        _require_file(
            final_manifest,
            SNAPSHOT_MANIFEST_SHA256,
            "Campaign044 snapshot manifest",
        )
        _validate_snapshot_manifest(
            json.loads(final_manifest.read_text(encoding="utf-8")),
            require_fingerprint_constants=True,
        )
        return final_manifest
    if shutil.disk_usage(data_root).free < 10 * 1024**3:
        raise Campaign044FeatureError("external data root has less than 10 GiB free")

    _, foundation, _, _, _, _ = _context()
    c43_binding = spec["source_chain"]["campaign043_terminal_snapshot"]
    c43_path = Path(str(c43_binding["path"])).resolve()
    _require_file(c43_path, str(c43_binding["sha256"]), "Campaign043 anchor manifest")
    anchor_manifest = json.loads(c43_path.read_text(encoding="utf-8"))
    anchor_records = list(anchor_manifest.get("files") or [])
    if len(anchor_records) != EXPECTED_PARTITIONS:
        raise Campaign044FeatureError("Campaign043 anchor partition count changed")
    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in anchor_records:
        by_symbol[str(record["symbol"])].append(record)
    lock_path = data_root / ".a_share_walkforward_campaign044_features.lock"
    with foundation.ProcessLock(lock_path):
        partial_root.mkdir(parents=True, exist_ok=True)
        common_keys, scores, cache_meta = _build_score_cache(
            partial_root=partial_root,
            final_root=final_root,
            data_root=data_root,
            workers=workers,
        )
        all_records: list[dict[str, Any]] = []
        eligible_dates: Counter[str] = Counter()
        resumed = 0
        completed_symbols = 0
        print(
            f"building {EXPECTED_PARTITIONS:,} Campaign044 partitions across "
            f"{len(by_symbol):,} symbols with {workers} workers",
            flush=True,
        )
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    _process_symbol,
                    records,
                    partial_root=partial_root,
                    final_root=final_root,
                    common_keys=common_keys,
                    scores=scores,
                    cache_sha256=str(cache_meta["byte_sha256"]),
                ): symbol
                for symbol, records in sorted(by_symbol.items())
            }
            try:
                for future in concurrent.futures.as_completed(futures):
                    futures.pop(future)
                    records, dates, resumed_count = future.result()
                    all_records.extend(records)
                    eligible_dates.update(dates)
                    resumed += resumed_count
                    completed_symbols += 1
                    if completed_symbols % 25 == 0 or completed_symbols == len(
                        by_symbol
                    ):
                        print(
                            f"Campaign044 progress symbols={completed_symbols:,}/"
                            f"{len(by_symbol):,} partitions={len(all_records):,}/"
                            f"{EXPECTED_PARTITIONS:,} resumed={resumed:,}",
                            flush=True,
                        )
            except BaseException:
                for future in futures:
                    future.cancel()
                raise
        if len(all_records) != EXPECTED_PARTITIONS:
            raise Campaign044FeatureError(
                "not every anchor partition produced a Campaign044 checkpoint"
            )
        all_records.sort(key=lambda item: (str(item["symbol"]), int(item["year"])))
        rows = sum(int(item["rows"]) for item in all_records)
        eligible_rows = sum(
            int(item["factor_eligible_rows"][FACTOR_NAME]) for item in all_records
        )
        if rows != EXPECTED_ROWS or eligible_rows != len(common_keys):
            raise Campaign044FeatureError("Campaign044 aggregate row counts changed")
        dataset_payload = "\n".join(
            f"{item['symbol']}|{item['year']}|{item['output_byte_sha256']}"
            for item in all_records
        ).encode("utf-8")
        manifest = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign044_feature_snapshot",
            "status": "feature_library_complete_pending_ordered_no_return_gates",
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "output_run_id": OUTPUT_RUN_ID,
            "protocol_path": str(DEFAULT_PROTOCOL.resolve()),
            "protocol_sha256": PROTOCOL_SHA256,
            "anchor_manifest_path": str(c43_path),
            "anchor_manifest_sha256": str(c43_binding["sha256"]),
            "anchor_dataset_sha256": str(c43_binding["dataset_sha256"]),
            "score_cache": cache_meta,
            "source_snapshot_verifications": cache_meta[
                "source_snapshot_verifications"
            ],
            "dataset_sha256": hashlib.sha256(dataset_payload).hexdigest(),
            "factor_names": [FACTOR_NAME],
            "factor_directions": FACTOR_DIRECTIONS,
            "factor_formulas": FACTOR_FORMULAS,
            "factor_eligible_rows": {FACTOR_NAME: eligible_rows},
            "eligible_names_by_date": {
                FACTOR_NAME: {
                    date: int(count) for date, count in sorted(eligible_dates.items())
                }
            },
            "source_factor_count": SOURCE_FACTOR_COUNT,
            "source_factor_names": [
                item["name"] for item in source_factor_specs(spec)
            ],
            "source_factor_directions": {
                item["name"]: item["score_direction"]
                for item in source_factor_specs(spec)
            },
            "source_factor_order_sha256": SOURCE_FACTOR_ORDER_SHA256,
            "active_candidate49_factor_excluded": ACTIVE_CANDIDATE49_FACTOR,
            "files": all_records,
            "partitions": len(all_records),
            "rows": rows,
            "quality": {
                "base_rows": rows,
                f"{FACTOR_NAME}__eligible_rows": eligible_rows,
                f"{FACTOR_NAME}__ineligible_rows": rows - eligible_rows,
                "quality_listing_master_rows": int(
                    cache_meta["quality_listing_master_rows"]
                ),
                "all_component_common_rows_before_session_minimum": int(
                    cache_meta["all_component_common_rows_before_session_minimum"]
                ),
                "minimum_common_support_names": MINIMUM_COMMON_SUPPORT_NAMES,
            },
            "source_terminal_factor_values_read": True,
            "candidate49_factor_values_read": False,
            "daily_price_fields_read": [],
            "forward_return_fields_read": False,
            "candidate49_historical_return_read": False,
            "training_or_model_fitting_performed": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
            "prospective_candidate_activation_created": False,
            "resumed_partitions": resumed,
            "protocol_evidence": {
                "campaign044_no_return_preregistration_sha256": PROTOCOL_SHA256,
                "campaign044_mechanism_overlap_audit_sha256": spec[
                    "source_chain"
                ]["mechanism_overlap_audit"]["sha256"],
                "candidate49_no_return_protocol_sha256": spec["source_chain"][
                    "candidate49_no_return_protocol"
                ]["sha256"],
            },
        }
        _validate_snapshot_manifest(manifest, require_fingerprint_constants=False)
        foundation.atomic_write_json(manifest, partial_root / "snapshot_manifest.json")
        final_root.parent.mkdir(parents=True, exist_ok=True)
        partial_root.replace(final_root)
        return final_manifest


def verify_snapshot_files(
    manifest: dict[str, Any],
    manifest_path: Path,
    workers: int,
) -> dict[str, Any]:
    _, foundation, _, _, _, _ = _context()
    records = list(manifest.get("files") or [])
    root = (manifest_path.parent / "partitions").resolve()

    def verify(record: dict[str, Any]) -> int:
        path = Path(str(record["path"])).resolve()
        if path.parent.parent != root:
            raise Campaign044FeatureError(f"snapshot partition escapes root: {path}")
        _require_file(
            path,
            str(record["output_byte_sha256"]),
            "Campaign044 snapshot partition",
        )
        frame = pd.read_parquet(path, columns=list(OUTPUT_COLUMNS))
        if (
            len(frame) != int(record["rows"])
            or foundation.frame_digest(frame) != record["output_frame_sha256"]
        ):
            raise Campaign044FeatureError(f"snapshot partition frame changed: {path}")
        return len(frame)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        counts = list(pool.map(verify, records))
    if len(counts) != EXPECTED_PARTITIONS or sum(counts) != EXPECTED_ROWS:
        raise Campaign044FeatureError("Campaign044 snapshot aggregate changed")
    return {
        "verified_partitions": len(counts),
        "verified_rows": sum(counts),
        "all_partition_byte_and_frame_hashes_valid": True,
    }


def _load_candidate_frame(
    manifest: dict[str, Any],
) -> pd.DataFrame:
    paths = [str(Path(record["path"]).resolve()) for record in manifest["files"]]
    dataset = pa_dataset.dataset(paths, format="parquet")
    table = dataset.to_table(
        columns=["trade_date", "symbol", FACTOR_NAME, f"{FACTOR_NAME}_eligible"],
        use_threads=True,
    )
    frame = table.to_pandas(split_blocks=True, self_destruct=True)
    del table, dataset
    gc.collect()
    frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce").dt.normalize()
    frame["symbol"] = frame["symbol"].astype(str).str.upper().astype("category")
    frame[FACTOR_NAME] = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    frame[f"{FACTOR_NAME}_eligible"] = (
        frame[f"{FACTOR_NAME}_eligible"]
        .astype("boolean")
        .fillna(False)
        .astype(bool)
    )
    eligible = frame[f"{FACTOR_NAME}_eligible"]
    values = frame.loc[eligible, FACTOR_NAME].to_numpy(dtype=float)
    if (
        len(frame) != EXPECTED_ROWS
        or frame["trade_date"].isna().any()
        or frame.duplicated(["trade_date", "symbol"]).any()
        or not np.isfinite(values).all()
        or (values < 0.0).any()
        or (values > 1.0).any()
        or frame.loc[~eligible, FACTOR_NAME].notna().any()
    ):
        raise Campaign044FeatureError("Campaign044 candidate frame changed")
    return frame


def run_no_return_audit(
    *,
    data_root: Path,
    experiment_root: Path,
    workers: int,
) -> Path:
    if not SNAPSHOT_MANIFEST_SHA256 or not SNAPSHOT_DATASET_SHA256:
        raise Campaign044FeatureError(
            "bind Campaign044 snapshot fingerprints before audit"
        )
    data_root = data_root.expanduser().resolve()
    experiment_root = experiment_root.expanduser().resolve()
    spec = load_protocol()
    manifest_path = output_root(data_root) / "snapshot_manifest.json"
    _require_file(
        manifest_path,
        SNAPSHOT_MANIFEST_SHA256,
        "Campaign044 snapshot manifest",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _validate_snapshot_manifest(manifest, require_fingerprint_constants=True)
    existing = sorted(experiment_root.glob("*_campaign044_no_return_audit.json"))
    if existing:
        if len(existing) != 1 or not NO_RETURN_AUDIT_SHA256:
            raise Campaign044FeatureError(
                "existing Campaign044 audit is ambiguous or unbound"
            )
        _require_file(existing[0], NO_RETURN_AUDIT_SHA256, "Campaign044 audit")
        return existing[0]
    verification = verify_snapshot_files(manifest, manifest_path, workers)
    prior, foundation, engine, _, _, comparison_engine = _context()
    eligible_keys = foundation.quality_listing_eligible_keys(prior.load_protocol())
    candidate = _load_candidate_frame(manifest)
    coverage_spec = copy.deepcopy(spec)
    coverage_gate = spec["ordered_no_return_gates"][
        "coverage_and_capacity_before_component_correlation_calculation"
    ]
    coverage_spec["ordered_no_return_gates"][
        "coverage_and_capacity_before_comparison_values"
    ] = {
        **coverage_gate,
        "holding_period_sessions": 3,
    }
    quality_frame, coverage = engine.coverage_and_capacity(
        candidate,
        eligible_keys,
        coverage_spec,
        FACTOR_NAME,
    )
    del candidate, eligible_keys
    gc.collect()
    if coverage["gate_passed_before_comparison_values"]:
        raw_gate = spec["ordered_no_return_gates"][
            "single_component_dominance_after_coverage_only"
        ]
        gate = {
            "maximum_allowed_absolute_median_daily_rank_correlation": raw_gate[
                "maximum_allowed_absolute_median_daily_rank_correlation"
            ],
            "minimum_pairwise_names_per_session": raw_gate[
                "minimum_pairwise_names_per_session"
            ],
            "minimum_pairwise_sessions_per_comparison": raw_gate[
                "minimum_pairwise_sessions_per_component"
            ],
        }
        keys = comparison_engine._compact_stock_day_keys(
            quality_frame["trade_date"], quality_frame["symbol"]
        )
        candidate_values = quality_frame[FACTOR_NAME].to_numpy(dtype=float)
        order = np.argsort(keys, kind="stable")
        keys = keys[order]
        candidate_values = candidate_values[order]
        catalog, source_verifications = _build_source_catalog(
            data_root=data_root,
            workers=workers,
            verify_files=True,
        )
        directions = {
            item["name"]: item["score_direction"] for item in source_factor_specs(spec)
        }
        comparisons: list[dict[str, Any]] = []
        for source in catalog:
            values = _load_aligned_source_values(source, keys)
            for factor in source["factors"]:
                comparisons.append(
                    comparison_engine._aligned_comparison_result(
                        candidate_keys=keys,
                        candidate_values=candidate_values,
                        comparison_values=values.pop(factor),
                        comparison=factor,
                        direction=directions[factor],
                        gate=gate,
                    )
                )
            del values
            gc.collect()
        expected_order = [item["name"] for item in source_factor_specs(spec)]
        observed_order = [item["comparison_factor"] for item in comparisons]
        observed = [
            float(item["absolute_median_daily_rank_correlation"])
            for item in comparisons
            if item["absolute_median_daily_rank_correlation"] is not None
        ]
        passed = bool(
            observed_order == expected_order
            and len(comparisons) == SOURCE_FACTOR_COUNT
            and all(item["gate_passed"] for item in comparisons)
        )
        dominance = {
            "source_component_values_reloaded_after_coverage_pass": True,
            "source_component_count": len(comparisons),
            "source_component_order_matches_preregistration": observed_order
            == expected_order,
            "source_snapshot_file_verification": source_verifications,
            "comparisons": comparisons,
            "maximum_observed_absolute_median_daily_rank_correlation": (
                max(observed) if observed else None
            ),
            "all_required_source_components_passed": passed,
        }
    else:
        dominance = {
            "source_component_values_reloaded_after_coverage_pass": False,
            "comparisons": [],
            "all_required_source_components_passed": False,
            "failure_reason": "coverage_gate_failed",
        }
    admitted = bool(
        coverage["gate_passed_before_comparison_values"]
        and dominance["all_required_source_components_passed"]
    )
    research = prior.research
    run_id = f"{research._timestamp()}_campaign044_no_return_audit"
    record = {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign044_no_return_audit",
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
        "single_component_dominance": {FACTOR_NAME: dominance},
        "admissible_factor_names": [FACTOR_NAME] if admitted else [],
        "admissible_factor_count": 1 if admitted else 0,
        "failed_factor_names": [] if admitted else [FACTOR_NAME],
        "pre_value_rejected_design_attempts": spec[
            "append_only_attempt_catalog"
        ][:2],
        "next_action": (
            "freeze the exact one-return-trial Campaign044 walk-forward catalog"
            if admitted
            else "record both attempts and design a genuinely new campaign"
        ),
        "source_terminal_factor_values_read": True,
        "candidate49_factor_values_read": False,
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
    manifest_path = output_root(data_root.expanduser().resolve()) / "snapshot_manifest.json"
    audits = sorted(
        experiment_root.expanduser().resolve().glob(
            "*_campaign044_no_return_audit.json"
        )
    )
    result: dict[str, Any] = {
        "protocol_path": str(DEFAULT_PROTOCOL.resolve()),
        "protocol_sha256_bound": True,
        "source_factor_count": SOURCE_FACTOR_COUNT,
        "source_factor_order_sha256": SOURCE_FACTOR_ORDER_SHA256,
        "active_candidate49_factor_excluded": ACTIVE_CANDIDATE49_FACTOR,
        "snapshot_manifest_path": str(manifest_path),
        "snapshot_exists": manifest_path.is_file(),
        "snapshot_sha256_bound": bool(SNAPSHOT_MANIFEST_SHA256),
        "audit_count": len(audits),
        "no_return_audit_sha256_bound": bool(NO_RETURN_AUDIT_SHA256),
        "source_factor_values_read_by_status": False,
        "daily_price_fields_read_by_status": False,
        "forward_return_fields_read_by_status": False,
        "candidate49_factor_values_read_by_status": False,
        "candidate49_historical_return_read": False,
    }
    if manifest_path.is_file():
        result["snapshot_observed_sha256"] = _sha256(manifest_path)
    if audits:
        result["latest_audit"] = str(audits[-1])
        result["latest_audit_observed_sha256"] = _sha256(audits[-1])
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("status", "build-snapshot", "no-return-audit"),
    )
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--experiment-root", default=str(DEFAULT_EXPERIMENT_ROOT))
    parser.add_argument("--workers", type=int, default=8)
    return parser


def main() -> int:
    args = _parser().parse_args()
    data_root = Path(args.data_root)
    experiment_root = Path(args.experiment_root)
    if args.command == "status":
        print(
            json.dumps(
                status(data_root, experiment_root),
                sort_keys=True,
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "build-snapshot":
        print(build_snapshot(data_root=data_root, workers=args.workers))
        return 0
    print(
        run_no_return_audit(
            data_root=data_root,
            experiment_root=experiment_root,
            workers=args.workers,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
