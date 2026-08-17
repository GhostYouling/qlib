#!/usr/bin/env python3
"""Build and verify the frozen Campaign069 profit-growth/ROE rank-gap snapshot."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts import a_share_three_day_compact_comparator_cache_v4 as cache_v4


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign066_features.py"
BASE_RUNNER_SHA256 = "ff8bd4aef61f7eec00299d1b38e21c30e15a4e7b010d157b0ea60d0576adf614"
BASE_FACTOR = "quarterly_quality_rank_balance_3f"
FACTOR_NAME = "quarterly_profit_growth_roe_transition_gap_2r"
FACTOR_FORMULA = "r_profit_yoy-r_roe"
PROTOCOL_SHA256 = "c044776cff0031ac3e65a4a3de51c06b90e1c1c0c1ba94895f79e900628dffe1"
MECHANISM_AUDIT_SHA256 = "c3856cc3d89632cc502747ef44602247e2afe1bd526a62a53995aff91df782db"
FULL_DEFINITION_COUNT = 100
FULL_DEFINITION_ORDER_SHA256 = "ba1d04cb281f0ed64ae792cc68be6257e2e53716d2c294138d0336ca01d59e7d"
COMPARISON_COUNT = 99
COMPARISON_ORDER_SHA256 = "7f1ed85abfeb4688c0b07f892b497942a202f09ac8806ea095b6c9050f670538"
C68_FACTOR = "quarterly_profit_revenue_acceleration_rank_gap_2r"
C68_SNAPSHOT_MANIFEST_SHA256 = "9878e6c0249cb9e965dbfade2ce2b3a355bed5e6a46bf68667c82fc568672004"
C68_SNAPSHOT_DATASET_SHA256 = "bcd03a5e2122b64b072985b3a9a9ada880cad337dae4766a00cf52bf51f4f449"
C68_SNAPSHOT_BINDING_SHA256 = "4d2104915dafc025c6b64f8a76685a611418c019f39a31f181ebca42cf5bd956"
C68_RESEARCH_RECORD_SHA256 = "e8711163c8bce0136dc44b7fe42daa07655b43a37fb325798b75a8c351cafbfc"
CACHE_PUBLICATION_BINDING_SHA256 = "244f70b88be0396f7473c6664835cbb3cdad9135b6692b77c74018b1d53c925b"
CACHE_MANIFEST_SHA256 = "3d81068f07ac61fe4cd04bd1a893e58759c06d88213263135fec5244e309b57b"
CACHE_DATASET_SHA256 = "4a56dac48c14b667b6ee431519266f27bb8ff7cc25c51d8dce3bbc7aebe0376f"
EVENT_FIELDS = ("instrument", "report_date", "announcement_date", "roe", "profit_yoy")
STATE_FIELDS = ("profit_yoy", "roe")
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if not BASE_RUNNER.is_file() or _sha256(BASE_RUNNER) != BASE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign066 feature runner changed")


_source = BASE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign066", "Campaign069"),
    ("campaign066", "campaign069"),
    ("campaign_066", "campaign_069"),
    (BASE_FACTOR, FACTOR_NAME),
    (
        "1-(max(r_roe,r_profit,r_revenue)-min(r_roe,r_profit,r_revenue))",
        FACTOR_FORMULA,
    ),
    (
        "ab850ef8ff194c1172070e2ffd388eff2d7924354abf06a8b32c5bd43584a278",
        PROTOCOL_SHA256,
    ),
    (
        "1e5fe44c0cde5097646cf058ec8149c189cf65e2ce62093e221c0d5022b98b8b",
        MECHANISM_AUDIT_SHA256,
    ),
    ("FULL_DEFINITION_COUNT = 97", "FULL_DEFINITION_COUNT = 100"),
    (
        "bc66abb94f62bef5fe9912059ade232c6c86b16b82f162df577fa8d74afeca7d",
        FULL_DEFINITION_ORDER_SHA256,
    ),
    ("COMPARISON_COUNT = 96", "COMPARISON_COUNT = 99"),
    (
        "794dff48d649b8dec1fdf609583ad87260c3e71a681a48b9a0ce77726de4763b",
        COMPARISON_ORDER_SHA256,
    ),
    (
        'EVENT_FIELDS = ("instrument", "report_date", "announcement_date", "roe", "profit_yoy", "revenue_yoy")',
        'EVENT_FIELDS = ("instrument", "report_date", "announcement_date", "roe", "profit_yoy")',
    ),
    (
        'STATE_FIELDS = ("roe", "profit_yoy", "revenue_yoy")',
        'STATE_FIELDS = ("profit_yoy", "roe")',
    ),
    (
        "states = np.full((len(out), 3), np.nan, dtype=np.float64)",
        "states = np.full((len(out), 2), np.nan, dtype=np.float64)",
    ),
):
    _source = _source.replace(_old, _new)

_runtime: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign069_features_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _runtime)


Campaign069FeatureError = _runtime["Campaign069FeatureError"]
bindings = _runtime["bindings"]
DEFAULT_DATA_ROOT: Path = _runtime["DEFAULT_DATA_ROOT"]
DEFAULT_PROTOCOL = (
    REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_069_no_return_preregistration.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_069_feature_implementation_freeze_20260806.json"
)
DEFAULT_CALENDAR: Path = _runtime["DEFAULT_CALENDAR"]
CLEAN_MANIFEST_RELATIVE: Path = _runtime["CLEAN_MANIFEST_RELATIVE"]
QUARTERLY_PATH: Path = _runtime["QUARTERLY_PATH"]
QUARTERLY_MANIFEST_PATH: Path = _runtime["QUARTERLY_MANIFEST_PATH"]
EXPECTED_PARTITIONS = int(_runtime["EXPECTED_PARTITIONS"])
EXPECTED_ROWS = int(_runtime["EXPECTED_ROWS"])


def _require_link(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign069FeatureError(f"Campaign069 {label} changed")


def reconstruct_comparisons(
    spec: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    del spec
    definitions = cache_v4._library_layout()["definitions"]
    items = [
        {
            "name": str(item["name"]),
            "score_direction": str(item["score_direction"]),
        }
        for item in definitions
    ]
    items.append({"name": C68_FACTOR, "score_direction": "higher"})
    if (
        len(items) != COMPARISON_COUNT
        or _runtime["_comparison_order_digest"](items) != COMPARISON_ORDER_SHA256
        or items.count({"name": C68_FACTOR, "score_direction": "higher"}) != 1
    ):
        raise Campaign069FeatureError("Campaign069 comparison order changed")
    return items


def _validate_comparator_sources(spec: dict[str, Any]) -> None:
    chain = spec.get("source_chain") or {}
    cache = chain.get("compact_comparator_cache_v4") or {}
    c68 = chain.get("campaign068_terminal_comparator") or {}
    for raw_path, expected, label in (
        (
            cache.get("publication_binding_path"),
            CACHE_PUBLICATION_BINDING_SHA256,
            "compact-cache publication binding",
        ),
        (cache.get("manifest_path"), CACHE_MANIFEST_SHA256, "compact-cache manifest"),
        (
            c68.get("research_record_path"),
            C68_RESEARCH_RECORD_SHA256,
            "Campaign068 research record",
        ),
        (
            c68.get("snapshot_binding_path"),
            C68_SNAPSHOT_BINDING_SHA256,
            "Campaign068 snapshot binding",
        ),
        (
            c68.get("snapshot_manifest_path"),
            C68_SNAPSHOT_MANIFEST_SHA256,
            "Campaign068 snapshot manifest",
        ),
    ):
        path = Path(str(raw_path or "")).expanduser()
        if not path.is_absolute():
            path = REPO_ROOT / path
        _require_link(path.resolve(), expected, label)
    cache_manifest = json.loads(
        Path(str(cache["manifest_path"])).read_text(encoding="utf-8")
    )
    c68_manifest = json.loads(
        Path(str(c68["snapshot_manifest_path"])).read_text(encoding="utf-8")
    )
    if not (
        cache.get("dataset_sha256") == CACHE_DATASET_SHA256
        and cache_manifest.get("dataset_sha256") == CACHE_DATASET_SHA256
        and cache.get("logical_numeric_comparator_count") == 98
        and c68.get("dataset_sha256") == C68_SNAPSHOT_DATASET_SHA256
        and c68_manifest.get("dataset_sha256") == C68_SNAPSHOT_DATASET_SHA256
        and c68.get("factor") == C68_FACTOR
        and c68.get("score_direction") == "higher"
        and c68_manifest.get("factor_names") == [C68_FACTOR]
        and (c68_manifest.get("factor_directions") or {}).get(C68_FACTOR)
        == "higher"
    ):
        raise Campaign069FeatureError("Campaign069 comparator source semantics changed")


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    _require_link(path, PROTOCOL_SHA256, "protocol")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign069FeatureError("Campaign069 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    _validate_comparator_sources(spec)
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    unique = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    comparisons = reconstruct_comparisons(spec)
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign069_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign069_source_candidate_comparison_daily_price_or_return_values"
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and candidate.get("formula", "").startswith(FACTOR_FORMULA)
        and tuple(candidate.get("quarterly_source_projection") or ()) == EVENT_FIELDS
        and candidate.get("combination_rule", "").startswith(
            "Exactly r_profit_yoy-r_roe"
        )
        and candidate.get("valid_range")
        == {
            "lower": -1.0,
            "lower_inclusive": True,
            "upper": 1.0,
            "upper_inclusive": True,
        }
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("minimum_observed_calendar_years") == 5
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and unique.get("complete_definition_count") == FULL_DEFINITION_COUNT
        and unique.get("complete_definition_order_sha256")
        == FULL_DEFINITION_ORDER_SHA256
        and unique.get("numeric_comparator_count") == COMPARISON_COUNT
        and unique.get("numeric_comparator_order_sha256")
        == COMPARISON_ORDER_SHA256
        and unique.get("all_99_numeric_comparators_must_pass") is True
        and len(comparisons) == COMPARISON_COUNT
        and finite.get("trial_id")
        == "wf069_quarterly_profit_growth_roe_transition_gap_2r_single_higher"
        and finite.get("expected_trial_count") == 1
        and boundary.get("quarterly_or_minute_source_rows_read_before_this_freeze")
        is False
        and boundary.get("candidate_or_comparison_values_read_before_this_freeze")
        is False
        and boundary.get("historical_forward_return_fields_read") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign069FeatureError("Campaign069 protocol semantics changed")
    return spec


def compute_gap_values(ranks: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(ranks, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 2:
        raise Campaign069FeatureError("profit-growth/ROE rank gap requires n-by-2 ranks")
    eligible = np.isfinite(values).all(axis=1) & (
        ((values >= 0.0) & (values <= 1.0)).all(axis=1)
    )
    result = np.full(len(values), np.nan, dtype=np.float64)
    result[eligible] = values[eligible, 0] - values[eligible, 1]
    if ((result[eligible] < -1.0) | (result[eligible] > 1.0)).any():
        raise Campaign069FeatureError("profit-growth/ROE rank gap escaped [-1,1]")
    return result, eligible


def rank_and_gap_year_frame(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    common_finite = np.isfinite(
        work.loc[:, STATE_FIELDS].to_numpy(dtype=np.float64)
    ).all(axis=1)
    ranks = [
        work[column].where(common_finite).groupby(work["trade_date"], sort=False).rank(
            method="average", pct=True
        )
        for column in STATE_FIELDS
    ]
    rank_matrix = np.column_stack(
        [series.to_numpy(dtype=np.float64) for series in ranks]
    )
    values, eligible = compute_gap_values(rank_matrix)
    work[FACTOR_NAME] = values
    work[f"{FACTOR_NAME}_eligible"] = eligible
    work["provider"] = "eastmoney_quarterly_quality"
    return work


def validate_value_semantics(frame: pd.DataFrame) -> tuple[int, int]:
    if tuple(frame.columns) != OUTPUT_COLUMNS:
        raise Campaign069FeatureError("Campaign069 partition columns changed")
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"].astype(bool)
    if (
        values[eligible].isna().any()
        or ((values[eligible] < -1.0) | (values[eligible] > 1.0)).any()
        or values[~eligible].notna().any()
    ):
        raise Campaign069FeatureError("Campaign069 signed value semantics changed")
    return len(frame), int(eligible.sum())


def verify_snapshot_files(
    manifest_path: Path, *, workers: int = 4
) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    expected = (output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json").resolve()
    if manifest_path != expected:
        raise Campaign069FeatureError("Campaign069 manifest path changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _runtime["_validate_manifest"](manifest)
    partition_root = (manifest_path.parent / "partitions").resolve()

    def verify(item: dict[str, Any]) -> tuple[int, int]:
        path = Path(str(item["path"])).expanduser().resolve()
        try:
            path.relative_to(partition_root)
        except ValueError as exc:
            raise Campaign069FeatureError("Campaign069 partition escaped output root") from exc
        if _sha256(path) != item["output_byte_sha256"]:
            raise Campaign069FeatureError(f"partition byte hash changed: {path}")
        frame = pd.read_parquet(path)
        if (
            len(frame) != item["rows"]
            or _runtime["_frame_sha256"](frame) != item["output_frame_sha256"]
        ):
            raise Campaign069FeatureError(f"partition frame changed: {path}")
        return validate_value_semantics(frame)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        totals = list(pool.map(verify, manifest["files"]))
    digest_rows = [
        [
            item["relative_path"],
            item["output_byte_sha256"],
            item["output_frame_sha256"],
            item["rows"],
        ]
        for item in manifest["files"]
    ]
    if not (
        _runtime["_json_digest"](digest_rows) == manifest["dataset_sha256"]
        and sum(value[0] for value in totals) == EXPECTED_ROWS
        and len(totals) == EXPECTED_PARTITIONS
        and sum(value[1] for value in totals)
        == (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    ):
        raise Campaign069FeatureError("Campaign069 aggregate identity changed")
    return {
        "status": "verified",
        "partitions": len(totals),
        "rows": sum(value[0] for value in totals),
        "eligible_rows": sum(value[1] for value in totals),
        "dataset_sha256": manifest["dataset_sha256"],
        "eligible_value_range": [-1.0, 1.0],
        "comparison_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def status(data_root: Path = DEFAULT_DATA_ROOT) -> dict[str, Any]:
    load_protocol()
    path = output_root(data_root.expanduser().resolve()) / "snapshot_manifest.json"
    return {
        "status": "snapshot_present" if path.is_file() else "snapshot_absent_pre_build",
        "snapshot_manifest": str(path),
        "protocol_sha256": PROTOCOL_SHA256,
        "candidate_or_comparison_values_read_by_status": False,
        "daily_price_fields_read_by_status": [],
        "historical_forward_return_fields_read_by_status": False,
        "provider_request_issued_by_status": False,
    }


for _name, _value in {
    "FACTOR_NAME": FACTOR_NAME,
    "FACTOR_FORMULA": FACTOR_FORMULA,
    "PROTOCOL_SHA256": PROTOCOL_SHA256,
    "MECHANISM_AUDIT_SHA256": MECHANISM_AUDIT_SHA256,
    "FULL_DEFINITION_COUNT": FULL_DEFINITION_COUNT,
    "FULL_DEFINITION_ORDER_SHA256": FULL_DEFINITION_ORDER_SHA256,
    "COMPARISON_COUNT": COMPARISON_COUNT,
    "COMPARISON_ORDER_SHA256": COMPARISON_ORDER_SHA256,
    "EVENT_FIELDS": EVENT_FIELDS,
    "STATE_FIELDS": STATE_FIELDS,
    "OUTPUT_COLUMNS": OUTPUT_COLUMNS,
    "DEFAULT_PROTOCOL": DEFAULT_PROTOCOL,
    "DEFAULT_IMPLEMENTATION_FREEZE": DEFAULT_IMPLEMENTATION_FREEZE,
    "reconstruct_comparisons": reconstruct_comparisons,
    "load_protocol": load_protocol,
    "compute_balance_values": compute_gap_values,
    "rank_and_balance_year_frame": rank_and_gap_year_frame,
    "verify_snapshot_files": verify_snapshot_files,
    "status": status,
}.items():
    _runtime[_name] = _value


_runtime["FACTOR_RANGES"] = {FACTOR_NAME: (-1.0, 1.0)}
_runtime["FACTOR_FORMULAS"] = {FACTOR_NAME: FACTOR_FORMULA}

_comparison_order_digest = _runtime["_comparison_order_digest"]
prepare_events = _runtime["prepare_events"]
attach_states = _runtime["attach_states"]
output_root = _runtime["output_root"]
build_snapshot = _runtime["build_snapshot"]
main = _runtime["main"]


if __name__ == "__main__":
    raise SystemExit(main())
