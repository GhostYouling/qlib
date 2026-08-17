#!/usr/bin/env python3
"""Snapshot-bound Campaign058 ordered no-return audit implementation."""

from __future__ import annotations

import gc
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_AUDIT = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign057_no_return_audit.py"
BASE_AUDIT_SHA256 = "d60f8bb19e953a75e6dcc47745399a08cab71deb61134783fc3a043613e6ed59"
BASE_FACTOR = "intraday_day_over_day_absolute_return_profile_similarity_238b"
FACTOR_NAME = "quarterly_profit_revenue_growth_spread_pp"
EXPECTED_COMPARISON_COUNT = 89
EXPECTED_COMPARISON_ORDER_SHA256 = "c4100bc923fad2ea5fb8898ccb102afe44307c8ab03ee2df8b0972d9b71bbbc1"
SNAPSHOT_BINDING_SHA256 = "0cf92fd4c788a2250eb6b9359062e92908b7c17663b47732445d28c56cb9cf65"
SNAPSHOT_MANIFEST_SHA256 = "c5bf57a70a2af71f30be87eec254710db65550f5dd7e041f219e862b4d97c00f"
SNAPSHOT_DATASET_SHA256 = "59fb5ed46c76a4737bbc60de9707f7f3b10223b692de4f4a88fec4143891cd4c"
EXPECTED_ELIGIBLE_ROWS = 7_231_483
QUALITY_COMPARISON_FACTORS = (
    "quality_roe",
    "quality_profit",
    "quality_revenue",
    "quality_growth",
    "quality_score",
    "roe_change",
    "revenue_yoy_acceleration",
    "profit_yoy_acceleration",
)
QUALITY_SOURCE_FIELDS = (
    "instrument",
    "report_date",
    "announcement_date",
    "roe",
    "net_profit",
    "revenue_yoy",
    "profit_yoy",
)


def _local_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _local_sha256(BASE_AUDIT) != BASE_AUDIT_SHA256:
    raise RuntimeError("frozen Campaign057 no-return audit changed")

_source = BASE_AUDIT.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign057", "Campaign058"),
    ("campaign057", "campaign058"),
    ("campaign_057", "campaign_058"),
    (BASE_FACTOR, FACTOR_NAME),
    ("a48d754e8b64201e35fd324e5f894957f0347932915ba3aaca85b7c873903e62", SNAPSHOT_BINDING_SHA256),
    ("7aba63621b2c6bd2b9d511d11ab56fc5331ae1dcf7a3c6055dbe6455d437d0ed", SNAPSHOT_MANIFEST_SHA256),
    ("b24d183b15feb98015d7353160740273ffb5acc14dcf0031a984d9eb3003f19d", SNAPSHOT_DATASET_SHA256),
    ("EXPECTED_ELIGIBLE_ROWS = 7_671_540", "EXPECTED_ELIGIBLE_ROWS = 7_231_483"),
    ("EXPECTED_COMPARISON_COUNT = 80", "EXPECTED_COMPARISON_COUNT = 89"),
    ("67e70655596658de91c8285ff998c17e8d2a7d83d0f571d416182e635e8180ae", EXPECTED_COMPARISON_ORDER_SHA256),
    ('"minute_open_high_low_close_volume_fields_read": ["close"],', '"minute_open_high_low_close_volume_fields_read": [],'),
):
    _source = _source.replace(_old, _new)

_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign058_no_return_audit_generated",
}
exec(compile(_source, str(BASE_AUDIT), "exec"), _generated)
_audit_engine: dict[str, Any] = _generated["_generated"]

from scripts import a_share_short_horizon_factor_research as research
from scripts import a_share_three_day_walkforward_campaign057_no_return_audit as c57_audit

Campaign058NoReturnAuditError = _generated["Campaign058NoReturnAuditError"]
candidate = _generated["candidate"]
prior_audit = _generated["prior_audit"]
DEFAULT_DATA_ROOT = _generated["DEFAULT_DATA_ROOT"]
DEFAULT_EXPERIMENT_ROOT = _generated["DEFAULT_EXPERIMENT_ROOT"]
SNAPSHOT_BINDING = _generated["SNAPSHOT_BINDING"]
SNAPSHOT_MANIFEST_PATH = _generated["SNAPSHOT_MANIFEST_PATH"]
EXPECTED_ROWS = _generated["EXPECTED_ROWS"]
EXPECTED_PARTITIONS = _generated["EXPECTED_PARTITIONS"]
C57_SNAPSHOT_PATH = c57_audit.SNAPSHOT_MANIFEST_PATH

for _name, _value in {
    "SNAPSHOT_BINDING_SHA256": SNAPSHOT_BINDING_SHA256,
    "SNAPSHOT_MANIFEST_SHA256": SNAPSHOT_MANIFEST_SHA256,
    "SNAPSHOT_DATASET_SHA256": SNAPSHOT_DATASET_SHA256,
    "EXPECTED_ELIGIBLE_ROWS": EXPECTED_ELIGIBLE_ROWS,
    "EXPECTED_COMPARISON_COUNT": EXPECTED_COMPARISON_COUNT,
    "EXPECTED_COMPARISON_ORDER_SHA256": EXPECTED_COMPARISON_ORDER_SHA256,
}.items():
    _generated[_name] = _value
    _audit_engine[_name] = _value


def _audit_require_file(path: Path, expected_sha256: str, label: str) -> None:
    path = path.expanduser().resolve()
    if not path.is_file() or _local_sha256(path) != expected_sha256:
        raise Campaign058NoReturnAuditError(f"{label} changed: {path}")


def _load_protocol() -> dict[str, Any]:
    spec = json.loads(json.dumps(candidate.load_protocol()))
    gate = spec["ordered_no_return_gates"]["uniqueness_after_coverage_only"]
    comparisons = candidate._reconstruct_comparisons(spec)
    if (
        len(comparisons) != EXPECTED_COMPARISON_COUNT
        or candidate._comparison_order_digest(comparisons)
        != EXPECTED_COMPARISON_ORDER_SHA256
    ):
        raise Campaign058NoReturnAuditError("Campaign058 comparison order changed")
    gate["comparison_factors"] = comparisons
    return spec


_generated["_require_file"] = _audit_require_file
_generated["_load_protocol"] = _load_protocol
_audit_engine["_require_file"] = _audit_require_file
_audit_engine["_load_protocol"] = _load_protocol


def _require_finalized_identities() -> None:
    values = (
        SNAPSHOT_BINDING_SHA256,
        SNAPSHOT_MANIFEST_SHA256,
        SNAPSHOT_DATASET_SHA256,
    )
    if EXPECTED_ELIGIBLE_ROWS < 0 or any(value.startswith("__") for value in values):
        raise Campaign058NoReturnAuditError(
            "Campaign058 audit identities are not frozen"
        )


_base_verify_static_bindings = _generated["verify_static_bindings"]


def verify_static_bindings() -> dict[str, Any]:
    _require_finalized_identities()
    result = _base_verify_static_bindings()
    for path, expected, label in (
        (candidate.QUARTERLY_PATH, candidate.QUARTERLY_SHA256, "quarterly source"),
        (
            candidate.QUARTERLY_MANIFEST_PATH,
            candidate.QUARTERLY_MANIFEST_SHA256,
            "quarterly manifest",
        ),
        (candidate.DEFAULT_CALENDAR, candidate.CALENDAR_SHA256, "accepted calendar"),
    ):
        if not path.is_file() or _local_sha256(path) != expected:
            raise Campaign058NoReturnAuditError(f"Campaign058 {label} changed: {path}")
    return {
        **result,
        "quarterly_source_sha256": candidate.QUARTERLY_SHA256,
        "quarterly_manifest_sha256": candidate.QUARTERLY_MANIFEST_SHA256,
        "calendar_sha256": candidate.CALENDAR_SHA256,
        "quality_comparison_factors": list(QUALITY_COMPARISON_FACTORS),
    }


def _load_bound_prior_snapshots(workers: int) -> dict[str, Any]:
    snapshots = c57_audit._load_bound_prior_snapshots(workers)
    c57_path = C57_SNAPSHOT_PATH.resolve()
    if not c57_path.is_file() or _local_sha256(c57_path) != c57_audit.SNAPSHOT_MANIFEST_SHA256:
        raise Campaign058NoReturnAuditError("Campaign057 terminal snapshot changed")
    manifest = json.loads(c57_path.read_text(encoding="utf-8"))
    if manifest.get("dataset_sha256") != c57_audit.SNAPSHOT_DATASET_SHA256:
        raise Campaign058NoReturnAuditError("Campaign057 snapshot dataset changed")
    verification = c57_audit.candidate.verify_snapshot_files(c57_path, workers=workers)
    return {
        **snapshots,
        "c57_manifest": manifest,
        "c57_verification": verification,
    }


def materialize_quality_comparison_frame(attached: pd.DataFrame) -> pd.DataFrame:
    """Materialize the eight frozen older quality semantics on one key frame."""

    required = {
        "datetime",
        "roe",
        "revenue_yoy",
        "profit_yoy",
        "roe_change",
        "revenue_yoy_acceleration",
        "profit_yoy_acceleration",
        "quality_eligible",
    }
    if missing := sorted(required - set(attached.columns)):
        raise Campaign058NoReturnAuditError(
            "Campaign058 attached quality frame is missing: " + ", ".join(missing)
        )
    if not attached["quality_eligible"].astype("boolean").fillna(False).all():
        raise Campaign058NoReturnAuditError(
            "Campaign058 quality comparison mask diverged from frozen eligible keys"
        )
    result = pd.DataFrame(index=attached.index)
    result["quality_roe"] = attached.groupby("datetime", sort=False)["roe"].rank(
        method="average", pct=True
    )
    result["quality_profit"] = attached.groupby("datetime", sort=False)[
        "profit_yoy"
    ].rank(method="average", pct=True)
    result["quality_revenue"] = attached.groupby("datetime", sort=False)[
        "revenue_yoy"
    ].rank(method="average", pct=True)
    result["quality_growth"] = result[["quality_profit", "quality_revenue"]].mean(
        axis=1, skipna=False
    )
    result["quality_score"] = result[
        ["quality_roe", "quality_profit", "quality_revenue"]
    ].mean(axis=1, skipna=False)
    for factor in (
        "roe_change",
        "revenue_yoy_acceleration",
        "profit_yoy_acceleration",
    ):
        result[factor] = attached.groupby("datetime", sort=False)[factor].rank(
            method="average", pct=True
        )
    return result.loc[:, list(QUALITY_COMPARISON_FACTORS)]


def _quality_comparison_values(
    *,
    keys: np.ndarray,
    comparison_engine: Any,
) -> dict[str, np.ndarray]:
    """Load quality values only after coverage and align them to candidate keys."""

    prior, foundation, _, _, _, _ = prior_audit.terminal.campaign044._context()
    eligible = foundation.quality_listing_eligible_keys(prior.load_protocol()).copy()
    eligible["symbol"] = eligible["symbol"].astype(str).str.upper()
    eligible_keys = comparison_engine._compact_stock_day_keys(
        eligible["trade_date"], eligible["symbol"]
    )
    order = np.argsort(eligible_keys, kind="stable")
    eligible_keys = eligible_keys[order]
    if len(np.unique(eligible_keys)) != len(eligible_keys):
        raise Campaign058NoReturnAuditError("quality/listing eligible keys changed")
    positions = np.searchsorted(eligible_keys, keys)
    if (
        (positions >= len(eligible_keys)).any()
        or not np.array_equal(eligible_keys[positions], keys)
    ):
        raise Campaign058NoReturnAuditError(
            "Campaign058 candidate keys escape the frozen quality/listing mask"
        )
    selected = eligible.iloc[order[positions]].copy().reset_index(drop=True)
    market = selected.rename(
        columns={"trade_date": "datetime", "symbol": "instrument"}
    )[["instrument", "datetime"]]
    fundamentals = research.load_fundamentals(candidate.QUARTERLY_PATH)
    fundamentals["instrument"] = fundamentals["instrument"].astype(str).str.upper()
    calendar = pd.DatetimeIndex(
        pd.to_datetime(
            candidate.DEFAULT_CALENDAR.read_text(encoding="utf-8").splitlines(),
            errors="coerce",
        )
    ).normalize().unique().sort_values()
    if calendar.empty or pd.isna(calendar).any():
        raise Campaign058NoReturnAuditError("accepted calendar values changed")
    attached = research.attach_quality_asof(
        market,
        fundamentals,
        max_age_days=550,
        availability_calendar=calendar,
    )
    observed_keys = comparison_engine._compact_stock_day_keys(
        attached["datetime"], attached["instrument"]
    )
    if not np.array_equal(observed_keys, keys):
        raise Campaign058NoReturnAuditError(
            "Campaign058 quality comparison alignment changed"
        )
    values = materialize_quality_comparison_frame(attached)
    result = {
        factor: pd.to_numeric(values[factor], errors="coerce").to_numpy(dtype=float)
        for factor in QUALITY_COMPARISON_FACTORS
    }
    del eligible, selected, market, fundamentals, attached, values
    gc.collect()
    return result


def _append_all_prior_comparisons(
    *,
    data_root: Path,
    workers: int,
    keys: Any,
    values: Any,
    gate: dict[str, Any],
    directions: dict[str, str],
    snapshots: dict[str, Any],
    engine: Any,
    candidate49: Any,
    comparison_engine: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Reconstruct the exact order: prior 80, C57, then eight quality factors."""

    comparisons, verifications = c57_audit._append_all_prior_comparisons(
        data_root=data_root,
        workers=workers,
        keys=keys,
        values=values,
        gate=gate,
        directions=directions,
        snapshots=snapshots,
        engine=engine,
        candidate49=candidate49,
        comparison_engine=comparison_engine,
    )
    c57_factor = c57_audit.candidate.FACTOR_NAME
    c57_values = engine._load_filtered_comparison_values_explicit(
        snapshots["c57_manifest"], [c57_factor], keys
    )[c57_factor]
    comparisons.append(
        comparison_engine._aligned_comparison_result(
            candidate_keys=keys,
            candidate_values=values,
            comparison_values=c57_values,
            comparison=c57_factor,
            direction=directions[c57_factor],
            gate=gate,
        )
    )
    del c57_values
    gc.collect()
    quality_values = _quality_comparison_values(
        keys=keys,
        comparison_engine=comparison_engine,
    )
    for factor in QUALITY_COMPARISON_FACTORS:
        comparisons.append(
            comparison_engine._aligned_comparison_result(
                candidate_keys=keys,
                candidate_values=values,
                comparison_values=quality_values[factor],
                comparison=factor,
                direction=directions[factor],
                gate=gate,
            )
        )
    del quality_values
    gc.collect()
    return comparisons, {
        **verifications,
        "campaign057_snapshot_file_verification": snapshots["c57_verification"],
        "quality_source_sha256": candidate.QUARTERLY_SHA256,
        "quality_manifest_sha256": candidate.QUARTERLY_MANIFEST_SHA256,
        "quality_comparison_factors": list(QUALITY_COMPARISON_FACTORS),
        "quality_comparison_semantics": (
            "strict_next_accepted_session_then_same_session_average_tie_percentile_ranks"
        ),
    }


for _name, _value in {
    "verify_static_bindings": verify_static_bindings,
    "_load_bound_prior_snapshots": _load_bound_prior_snapshots,
    "_append_all_prior_comparisons": _append_all_prior_comparisons,
}.items():
    _generated[_name] = _value
    _audit_engine[_name] = _value

_base_run_no_return_audit = _generated["run_no_return_audit"]


def run_no_return_audit(
    *,
    data_root: Path,
    experiment_root: Path,
    workers: int,
) -> Path:
    destination = _base_run_no_return_audit(
        data_root=data_root,
        experiment_root=experiment_root,
        workers=workers,
    )
    record = json.loads(destination.read_text(encoding="utf-8"))
    factor_result = (record.get("uniqueness") or {}).get(FACTOR_NAME) or {}
    comparisons_loaded = bool(
        factor_result.get("comparison_values_loaded_after_coverage_pass")
    )
    record.update(
        {
            "quarterly_candidate_fields_in_bound_snapshot": [
                "revenue_yoy",
                "profit_yoy",
            ],
            "quarterly_comparison_fields_read": (
                list(QUALITY_SOURCE_FIELDS) if comparisons_loaded else []
            ),
            "minute_price_or_activity_fields_read": [],
            "quality_comparison_values_loaded_after_coverage_pass": comparisons_loaded,
            "candidate49_historical_return_read": False,
            "historical_daily_price_fields_read": [],
            "historical_forward_return_fields_read": False,
            "provider_request_issued_by_campaign058_audit": False,
        }
    )
    prior, foundation, _, _, _, _ = prior_audit.terminal.campaign044._context()
    foundation.atomic_write_json(record, destination)
    return destination


_generated["run_no_return_audit"] = run_no_return_audit
_audit_engine["run_no_return_audit"] = run_no_return_audit
load_candidate_frame = _generated["load_candidate_frame"]
status = _generated["status"]
main = _generated["main"]


if __name__ == "__main__":
    raise SystemExit(main())
