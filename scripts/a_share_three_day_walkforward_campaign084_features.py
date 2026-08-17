#!/usr/bin/env python3
"""Build Campaign084's profit-growth level/acceleration floor without returns."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign083_features as c83


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_RUNNER = (
    REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign066_features.py"
)
BASE_RUNNER_SHA256 = "ff8bd4aef61f7eec00299d1b38e21c30e15a4e7b010d157b0ea60d0576adf614"
BASE_FACTOR = "quarterly_quality_rank_balance_3f"
FACTOR_NAME = "quarterly_profit_growth_level_acceleration_floor_2r"
FACTOR_FORMULA = "min(r_profit_level,r_profit_acceleration)"
PROTOCOL_SHA256 = "c396f141c811978004c04b62f09caceef343a9860e43f48de1fe44419c9bcf70"
MECHANISM_AUDIT_SHA256 = (
    "3b661b09a1f7fa4b3489027f4cbed5d5e5c524fecba9a3bd0ce1ed16a732c039"
)
NUMERIC_POLICY_SHA256 = (
    "dacfbcd9bfdb2b764bd52c71e09e50154a7ab8b4e7b2e183afdf52ddd96e32fa"
)
CURRENT_STATE_SHA256 = (
    "3702683aeab45a7917fdedd918fe0ccc3076e36dc98c613e09fe383b6932405d"
)
FULL_DEFINITION_COUNT = 115
FULL_DEFINITION_ORDER_SHA256 = (
    "c42c662c17bbeec105ef85f0d9ba63edabae32601d0b9701209057961f72adec"
)
COMPARISON_COUNT = 113
COMPARISON_ORDER_SHA256 = (
    "04e8161152715277f4ebdfc63e5cd19db60a8dcd204d3f05dd38ab8313a03078"
)
C83_FACTOR = c83.FACTOR_NAME
C83_BINDING_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_083_feature_snapshot_binding_20260806.json"
)
C83_BINDING_SHA256 = "6a37b02574f506e4f2043b91788bef9c8a93e3535985867293531bde22be5b2c"
C83_MANIFEST_PATH = c83.output_root(c83.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
C83_MANIFEST_SHA256 = "e462a154f2da5374be671955b04d0e70b2bc02821a397e978e346dca75bf0618"
C83_DATASET_SHA256 = "b9b9a54d1a1a040d22cae0dbabe1cdb556312a97f604efe1da38e437478cde52"
EVENT_FIELDS = (
    "instrument",
    "report_date",
    "announcement_date",
    "profit_yoy",
)
STATE_FIELDS = (
    "profit_yoy",
    "profit_yoy_acceleration",
)
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
    ("Campaign066", "Campaign084"),
    ("campaign066", "campaign084"),
    ("campaign_066", "campaign_084"),
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
    ("FULL_DEFINITION_COUNT = 97", "FULL_DEFINITION_COUNT = 115"),
    (
        "bc66abb94f62bef5fe9912059ade232c6c86b16b82f162df577fa8d74afeca7d",
        FULL_DEFINITION_ORDER_SHA256,
    ),
    ("COMPARISON_COUNT = 96", "COMPARISON_COUNT = 113"),
    (
        "794dff48d649b8dec1fdf609583ad87260c3e71a681a48b9a0ce77726de4763b",
        COMPARISON_ORDER_SHA256,
    ),
    ("C65_FACTOR", "C83_FACTOR"),
    ("intraday_range_weak_order_time_reversal_divergence_236t", C83_FACTOR),
    ("campaign065", "campaign083"),
    (
        'EVENT_FIELDS = ("instrument", "report_date", "announcement_date", "roe", "profit_yoy", "revenue_yoy")',
        'EVENT_FIELDS = ("instrument", "report_date", "announcement_date", "profit_yoy")',
    ),
    (
        'STATE_FIELDS = ("roe", "profit_yoy", "revenue_yoy")',
        'STATE_FIELDS = ("profit_yoy", "profit_yoy_acceleration")',
    ),
    (
        "states = np.full((len(out), 3), np.nan, dtype=np.float64)",
        "states = np.full((len(out), 2), np.nan, dtype=np.float64)",
    ),
):
    _source = _source.replace(_old, _new)

_runtime: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign084_features_generated",
}
exec(compile(_source, str(BASE_RUNNER), "exec"), _runtime)


Campaign084FeatureError = _runtime["Campaign084FeatureError"]
bindings = _runtime["bindings"]
DEFAULT_DATA_ROOT: Path = _runtime["DEFAULT_DATA_ROOT"]
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_084_no_return_preregistration.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_084_feature_implementation_freeze_20260806.json"
)
DEFAULT_CALENDAR: Path = _runtime["DEFAULT_CALENDAR"]
CLEAN_MANIFEST_RELATIVE: Path = _runtime["CLEAN_MANIFEST_RELATIVE"]
QUARTERLY_PATH: Path = _runtime["QUARTERLY_PATH"]
QUARTERLY_MANIFEST_PATH: Path = _runtime["QUARTERLY_MANIFEST_PATH"]
EXPECTED_PARTITIONS = int(_runtime["EXPECTED_PARTITIONS"])
EXPECTED_ROWS = int(_runtime["EXPECTED_ROWS"])


def reconstruct_comparisons(
    spec: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    del spec
    items = c83.reconstruct_comparisons()
    items.append({"name": C83_FACTOR, "score_direction": "higher"})
    if (
        len(items) != COMPARISON_COUNT
        or _runtime["_comparison_order_digest"](items) != COMPARISON_ORDER_SHA256
        or items[-1] != {"name": C83_FACTOR, "score_direction": "higher"}
    ):
        raise Campaign084FeatureError("Campaign084 comparison order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = c83.reconstruct_complete_definitions()
    items.append({"name": C83_FACTOR, "score_direction": "higher"})
    if (
        len(items) != FULL_DEFINITION_COUNT
        or _runtime["_comparison_order_digest"](items) != FULL_DEFINITION_ORDER_SHA256
    ):
        raise Campaign084FeatureError("Campaign084 complete definition order changed")
    return items


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign084FeatureError(f"Campaign084 {label} changed: {path}")


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    _require(path, PROTOCOL_SHA256, "protocol")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign084FeatureError("Campaign084 protocol binding failed")
    _require(C83_BINDING_PATH, C83_BINDING_SHA256, "Campaign083 snapshot binding")
    _require(C83_MANIFEST_PATH, C83_MANIFEST_SHA256, "Campaign083 snapshot manifest")
    previous = json.loads(C83_MANIFEST_PATH.read_text(encoding="utf-8"))
    spec = json.loads(path.read_text(encoding="utf-8"))
    chain = spec.get("source_chain") or {}
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    unique = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    comparisons = reconstruct_comparisons(spec)
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign084_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign084_quarterly_source_candidate_comparison_daily_price_or_return_values"
        and (chain.get("numeric_comparator_policy_v19") or {}).get("sha256")
        == NUMERIC_POLICY_SHA256
        and (chain.get("authoritative_iteration_state") or {}).get("sha256")
        == CURRENT_STATE_SHA256
        and (chain.get("campaign083_terminal_numeric_comparator") or {}).get(
            "dataset_sha256"
        )
        == C83_DATASET_SHA256
        and previous.get("dataset_sha256") == C83_DATASET_SHA256
        and previous.get("factor_names") == [C83_FACTOR]
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("stock_day_identity_projection") or ())
        == ("trade_date", "symbol", "provider")
        and tuple(candidate.get("quarterly_source_projection") or ()) == EVENT_FIELDS
        and candidate.get("event_identity") == ["instrument", "report_date"]
        and candidate.get("event_identity_must_be_unique") is True
        and candidate.get("combination_rule", "").startswith(
            "Exactly min(r_profit_level,r_profit_acceleration)"
        )
        and candidate.get("frozen_old_definition_inputs")
        == ["quality_profit", "profit_yoy_acceleration"]
        and candidate.get("campaign083_factor_used_or_combined") is False
        and candidate.get("valid_range")
        == {
            "lower": 0.0,
            "lower_inclusive": False,
            "upper": 1.0,
            "upper_inclusive": True,
        }
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and unique.get("complete_definition_count") == FULL_DEFINITION_COUNT
        and unique.get("complete_definition_order_sha256")
        == FULL_DEFINITION_ORDER_SHA256
        and unique.get("numeric_comparator_count") == COMPARISON_COUNT
        and unique.get("numeric_comparator_order_sha256") == COMPARISON_ORDER_SHA256
        and unique.get("all_113_numeric_comparators_must_pass") is True
        and len(comparisons) == COMPARISON_COUNT
        and len(reconstruct_complete_definitions()) == FULL_DEFINITION_COUNT
        and finite.get("trial_id")
        == "wf084_quarterly_profit_growth_level_acceleration_floor_2r_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("complexity") == 1
        and finite.get("expected_trial_count") == 1
        and boundary.get("comparison_values_read_before_coverage_pass") is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign084FeatureError("Campaign084 protocol semantics changed")
    return spec


def compute_floor_values(ranks: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(ranks, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != 2:
        raise Campaign084FeatureError("profit floor requires an n-by-2 rank array")
    eligible = np.isfinite(values).all(axis=1) & (
        ((values > 0.0) & (values <= 1.0)).all(axis=1)
    )
    result = np.full(len(values), np.nan, dtype=np.float64)
    result[eligible] = values[eligible].min(axis=1)
    if ((result[eligible] <= 0.0) | (result[eligible] > 1.0)).any():
        raise Campaign084FeatureError("profit floor escaped (0,1]")
    return result, eligible


def prepare_events(
    events: pd.DataFrame, calendar: pd.DatetimeIndex
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Compute same-quarter accelerations before strict-next-session activation."""

    if tuple(events.columns) != EVENT_FIELDS:
        raise Campaign084FeatureError("quarterly source projection changed")
    work = events.copy()
    work["instrument"] = work["instrument"].astype(str).str.upper()
    for column in ("report_date", "announcement_date"):
        work[column] = pd.to_datetime(work[column], errors="coerce").dt.normalize()
    work["profit_yoy"] = pd.to_numeric(work["profit_yoy"], errors="coerce")
    work.loc[~np.isfinite(work["profit_yoy"]), "profit_yoy"] = np.nan
    if (
        work.empty
        or work[["instrument", "report_date", "announcement_date"]].isna().any().any()
        or work.duplicated(["instrument", "report_date"]).any()
    ):
        raise Campaign084FeatureError("quarterly event identities changed")
    work = work.sort_values(
        ["instrument", "report_date", "announcement_date"], kind="stable"
    )
    work["_report_month"] = work["report_date"].dt.month
    work["profit_yoy_acceleration"] = work.groupby(
        ["instrument", "_report_month"], sort=False
    )["profit_yoy"].diff()
    calendar_values = calendar.to_numpy(dtype="datetime64[ns]")
    positions = np.searchsorted(
        calendar_values,
        work["announcement_date"].to_numpy(dtype="datetime64[ns]"),
        side="right",
    )
    valid = positions < len(calendar_values)
    work = work.loc[valid].copy()
    work["effective_position"] = positions[valid]
    work = (
        work.sort_values(
            [
                "instrument",
                "effective_position",
                "report_date",
                "announcement_date",
            ],
            kind="stable",
        )
        .drop_duplicates(["instrument", "effective_position"], keep="last")
        .reset_index(drop=True)
    )
    result: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for symbol, group in work.groupby("instrument", sort=False):
        states = group.loc[:, STATE_FIELDS].ffill().to_numpy(dtype=np.float64)
        result[str(symbol)] = (
            group["effective_position"].to_numpy(dtype=np.int64),
            states,
        )
    return result


def rank_and_floor_year_frame(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    common_finite = np.isfinite(
        work.loc[:, STATE_FIELDS]
        .apply(pd.to_numeric, errors="coerce")
        .to_numpy(dtype=np.float64)
    ).all(axis=1)
    rank_source = work.loc[common_finite].copy()
    ranks = [
        rank_source.groupby("trade_date", sort=False)[column].rank(
            method="average", pct=True
        )
        for column in STATE_FIELDS
    ]
    rank_matrix = np.column_stack([item.to_numpy(dtype=np.float64) for item in ranks])
    selected_values, selected_eligible = compute_floor_values(rank_matrix)
    values = np.full(len(work), np.nan, dtype=np.float64)
    eligible = np.zeros(len(work), dtype=bool)
    selected_positions = np.flatnonzero(common_finite)
    values[selected_positions] = selected_values
    eligible[selected_positions] = selected_eligible
    work[FACTOR_NAME] = values
    work[f"{FACTOR_NAME}_eligible"] = eligible
    work["provider"] = "eastmoney_quarterly_quality"
    return work


def validate_value_semantics(frame: pd.DataFrame) -> tuple[int, int]:
    if tuple(frame.columns) != OUTPUT_COLUMNS:
        raise Campaign084FeatureError("Campaign084 partition columns changed")
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"].astype(bool)
    if (
        values[eligible].isna().any()
        or ((values[eligible] <= 0.0) | (values[eligible] > 1.0)).any()
        or values[~eligible].notna().any()
    ):
        raise Campaign084FeatureError("Campaign084 value semantics changed")
    return len(frame), int(eligible.sum())


def verify_snapshot_files(manifest_path: Path, *, workers: int = 4) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    expected = (output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json").resolve()
    if manifest_path != expected:
        raise Campaign084FeatureError("Campaign084 manifest path changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _runtime["_validate_manifest"](manifest)
    partition_root = (manifest_path.parent / "partitions").resolve()

    def verify(item: dict[str, Any]) -> tuple[int, int]:
        path = Path(str(item["path"])).expanduser().resolve()
        path.relative_to(partition_root)
        if _sha256(path) != item["output_byte_sha256"]:
            raise Campaign084FeatureError(f"partition byte hash changed: {path}")
        frame = pd.read_parquet(path)
        if (
            len(frame) != item["rows"]
            or _runtime["_frame_sha256"](frame) != item["output_frame_sha256"]
        ):
            raise Campaign084FeatureError(f"partition frame changed: {path}")
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
        raise Campaign084FeatureError("Campaign084 aggregate identity changed")
    return {
        "status": "verified",
        "partitions": len(totals),
        "rows": sum(value[0] for value in totals),
        "eligible_rows": sum(value[1] for value in totals),
        "dataset_sha256": manifest["dataset_sha256"],
        "comparison_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


for _name, _value in {
    "Campaign084FeatureError": Campaign084FeatureError,
    "FACTOR_NAME": FACTOR_NAME,
    "FACTOR_FORMULA": FACTOR_FORMULA,
    "PROTOCOL_SHA256": PROTOCOL_SHA256,
    "MECHANISM_AUDIT_SHA256": MECHANISM_AUDIT_SHA256,
    "FULL_DEFINITION_COUNT": FULL_DEFINITION_COUNT,
    "FULL_DEFINITION_ORDER_SHA256": FULL_DEFINITION_ORDER_SHA256,
    "COMPARISON_COUNT": COMPARISON_COUNT,
    "COMPARISON_ORDER_SHA256": COMPARISON_ORDER_SHA256,
    "C83_FACTOR": C83_FACTOR,
    "EVENT_FIELDS": EVENT_FIELDS,
    "STATE_FIELDS": STATE_FIELDS,
    "OUTPUT_COLUMNS": OUTPUT_COLUMNS,
    "DEFAULT_PROTOCOL": DEFAULT_PROTOCOL,
    "DEFAULT_IMPLEMENTATION_FREEZE": DEFAULT_IMPLEMENTATION_FREEZE,
    "reconstruct_comparisons": reconstruct_comparisons,
    "reconstruct_complete_definitions": reconstruct_complete_definitions,
    "load_protocol": load_protocol,
    "compute_balance_values": compute_floor_values,
    "prepare_events": prepare_events,
    "rank_and_balance_year_frame": rank_and_floor_year_frame,
    "validate_value_semantics": validate_value_semantics,
    "verify_snapshot_files": verify_snapshot_files,
}.items():
    _runtime[_name] = _value


_runtime["FACTOR_RANGES"] = {FACTOR_NAME: (0.0, 1.0)}
_runtime["FACTOR_FORMULAS"] = {FACTOR_NAME: FACTOR_FORMULA}

_comparison_order_digest = _runtime["_comparison_order_digest"]
attach_states = _runtime["attach_states"]
output_root = _runtime["output_root"]
build_snapshot = _runtime["build_snapshot"]
status = _runtime["status"]
main = _runtime["main"]


if __name__ == "__main__":
    raise SystemExit(main())
