#!/usr/bin/env python3
"""Build and verify Campaign071's point-in-time net-profit scale rank."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts import a_share_three_day_compact_comparator_cache_v4 as cache_v4


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign070_features.py"
TEMPLATE_RUNNER_SHA256 = "c05335e002b8766c4591bf8be3a987888d807923ff6846ee1312ce50c5de168e"
FACTOR_NAME = "quarterly_net_profit_scale_rank"
FACTOR_FORMULA = (
    "strict-next-session finite positive net_profit state, forward-filled only "
    "after availability, then same-stock-day average-tie percentile rank"
)
PROTOCOL_SHA256 = "1d61fc0f0943f512304a722bcf3017e6867fd00ec9a41e1ed310022a526c161f"
MECHANISM_AUDIT_SHA256 = "e32457e148b3a4c774fdd5d1f7b6445a47ae8b5767c00f067c952a61a4f530a4"
NUMERIC_POLICY_SHA256 = "afe9f33f1b8accdcbb1481604313fcc55e9e84ecbc02098730f0b41adf60c68f"
FULL_DEFINITION_COUNT = 102
FULL_DEFINITION_ORDER_SHA256 = "5509c7801521a81c259892ad8637bdcdf5440eb11a1e99872091de251d282f08"
COMPARISON_COUNT = 101
COMPARISON_ORDER_SHA256 = "8ab835ebc9a5cc4f1b0e8e80a7db027dc7b64837859b43975d544dcf9294eca3"
C68_FACTOR = "quarterly_profit_revenue_acceleration_rank_gap_2r"
C69_FACTOR = "quarterly_profit_growth_roe_transition_gap_2r"
C70_FACTOR = "quarterly_announcement_delay_improvement_yoy_rank_1y"
C70_SNAPSHOT_MANIFEST_SHA256 = "f828ee06ac609580880eb0bfcd2d1fbcaba590e872f57fe5639a468c67edcbd7"
C70_SNAPSHOT_DATASET_SHA256 = "35ea87d9e183b77a382a88789cedf96d79f6a102c5006e156bbde2ff87fd6efe"
C70_SNAPSHOT_BINDING_SHA256 = "4c573c47ce247cac96c492ae37f93c39356303db18f05c093f1446a765e8aa34"
C70_RESEARCH_RECORD_SHA256 = "9f8450e791c7afafbb6fe971eebe3815c8ab5c9c28b4907a75840058c1402900"
CACHE_PUBLICATION_BINDING_SHA256 = "244f70b88be0396f7473c6664835cbb3cdad9135b6692b77c74018b1d53c925b"
CACHE_MANIFEST_SHA256 = "3d81068f07ac61fe4cd04bd1a893e58759c06d88213263135fec5244e309b57b"
C68_SNAPSHOT_MANIFEST_SHA256 = "9878e6c0249cb9e965dbfade2ce2b3a355bed5e6a46bf68667c82fc568672004"
C69_SNAPSHOT_MANIFEST_SHA256 = "6023becea579d0f6ed6ac27316421294f13fd6759d6d51790a31940526e363b7"
EVENT_FIELDS = ("instrument", "report_date", "announcement_date", "net_profit")
STATE_FIELDS = ("net_profit",)
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)


class Campaign071FeatureError(RuntimeError):
    """Fail-closed Campaign071 feature error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if not TEMPLATE_RUNNER.is_file() or _sha256(TEMPLATE_RUNNER) != TEMPLATE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign070 feature runner changed")


_source = TEMPLATE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign070", "Campaign071"),
    ("campaign070", "campaign071"),
    ("campaign_070", "campaign_071"),
    ("quarterly_announcement_delay_improvement_yoy_rank_1y", FACTOR_NAME),
    (
        "prior-year same-quarter announcement delay minus current announcement delay, strict-next-session activation, finite-state forward fill, then same-stock-day average-tie percentile rank",
        FACTOR_FORMULA,
    ),
    ("5474879454fbc3113fb386b4ebc4a1e1e0643a168511ebfe39d8bd9fc9a96952", PROTOCOL_SHA256),
    ("b561bd2b53051d25caeaf987345d87829623d7ca8c57481eb982158e86dfc9ec", MECHANISM_AUDIT_SHA256),
    ("afdb235a9aac5d6cde01b5e4edf57cdd3da15fd3adac035c69f284408bead913", NUMERIC_POLICY_SHA256),
    ("FULL_DEFINITION_COUNT = 101", "FULL_DEFINITION_COUNT = 102"),
    ("0bc65c0bcae2dd089ceb8c67ea606be483673caac5cbce4ce9dc9e89b04fd124", FULL_DEFINITION_ORDER_SHA256),
    ("COMPARISON_COUNT = 100", "COMPARISON_COUNT = 101"),
    ("d1c58576dcdef7980c279426f135440d05f8484d2f42d4b4866539b963a0b7ee", COMPARISON_ORDER_SHA256),
    ('EVENT_FIELDS = ("instrument", "report_date", "announcement_date")', 'EVENT_FIELDS = ("instrument", "report_date", "announcement_date", "net_profit")'),
    ('STATE_FIELDS = ("improvement_days",)', 'STATE_FIELDS = ("net_profit",)'),
    ("all_100_numeric_comparators_must_pass", "all_101_numeric_comparators_must_pass"),
    ("wf070_", "wf071_"),
):
    _source = _source.replace(_old, _new)

_namespace: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign071_features_generated",
}
exec(compile(_source, str(TEMPLATE_RUNNER), "exec"), _namespace)
_runtime: dict[str, Any] = _namespace["_runtime"]

DEFAULT_DATA_ROOT: Path = _runtime["DEFAULT_DATA_ROOT"]
DEFAULT_CALENDAR: Path = _runtime["DEFAULT_CALENDAR"]
QUARTERLY_PATH: Path = _runtime["QUARTERLY_PATH"]
QUARTERLY_MANIFEST_PATH: Path = _runtime["QUARTERLY_MANIFEST_PATH"]
EXPECTED_PARTITIONS = int(_runtime["EXPECTED_PARTITIONS"])
EXPECTED_ROWS = int(_runtime["EXPECTED_ROWS"])
DEFAULT_PROTOCOL = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_071_no_return_preregistration.json"
DEFAULT_IMPLEMENTATION_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_071_feature_implementation_freeze_20260806.json"
bindings = _runtime["bindings"]


def _require_link(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign071FeatureError(f"Campaign071 {label} changed")


def reconstruct_comparisons(spec: dict[str, Any] | None = None) -> list[dict[str, str]]:
    del spec
    items = [
        {"name": str(item["name"]), "score_direction": str(item["score_direction"])}
        for item in cache_v4._library_layout()["definitions"]
    ]
    items.extend(
        [
            {"name": C68_FACTOR, "score_direction": "higher"},
            {"name": C69_FACTOR, "score_direction": "higher"},
            {"name": C70_FACTOR, "score_direction": "higher"},
        ]
    )
    if (
        len(items) != COMPARISON_COUNT
        or _runtime["_comparison_order_digest"](items) != COMPARISON_ORDER_SHA256
        or items[-1] != {"name": C70_FACTOR, "score_direction": "higher"}
    ):
        raise Campaign071FeatureError("Campaign071 comparison order changed")
    return items


def _validate_comparator_sources(spec: dict[str, Any]) -> None:
    chain = spec.get("source_chain") or {}
    cache = chain.get("compact_comparator_cache_v4") or {}
    c68 = chain.get("campaign068_terminal_comparator") or {}
    c69 = chain.get("campaign069_terminal_comparator") or {}
    c70 = chain.get("campaign070_terminal_comparator") or {}
    required = (
        (cache.get("publication_binding_path"), CACHE_PUBLICATION_BINDING_SHA256, "cache publication"),
        (cache.get("manifest_path"), CACHE_MANIFEST_SHA256, "cache manifest"),
        (c68.get("snapshot_manifest_path"), C68_SNAPSHOT_MANIFEST_SHA256, "Campaign068 manifest"),
        (c69.get("snapshot_manifest_path"), C69_SNAPSHOT_MANIFEST_SHA256, "Campaign069 manifest"),
        (c70.get("research_record_path"), C70_RESEARCH_RECORD_SHA256, "Campaign070 record"),
        (c70.get("snapshot_binding_path"), C70_SNAPSHOT_BINDING_SHA256, "Campaign070 snapshot binding"),
        (c70.get("snapshot_manifest_path"), C70_SNAPSHOT_MANIFEST_SHA256, "Campaign070 manifest"),
    )
    for raw_path, expected, label in required:
        path = Path(str(raw_path or "")).expanduser()
        if not path.is_absolute():
            path = REPO_ROOT / path
        _require_link(path.resolve(), str(expected), label)
    c70_manifest = json.loads(Path(str(c70["snapshot_manifest_path"])).read_text(encoding="utf-8"))
    if not (
        c70.get("dataset_sha256") == C70_SNAPSHOT_DATASET_SHA256
        and c70.get("factor") == C70_FACTOR
        and c70.get("score_direction") == "higher"
        and c70_manifest.get("dataset_sha256") == C70_SNAPSHOT_DATASET_SHA256
        and c70_manifest.get("factor_names") == [C70_FACTOR]
    ):
        raise Campaign071FeatureError("Campaign071 Campaign070 comparator semantics changed")


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    _require_link(path, PROTOCOL_SHA256, "protocol")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign071FeatureError("Campaign071 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    _validate_comparator_sources(spec)
    chain = spec.get("source_chain") or {}
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    unique = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("kind") == "a_share_three_day_walkforward_campaign071_no_return_preregistration"
        and spec.get("status") == "frozen_before_campaign071_source_candidate_comparison_daily_price_or_return_values"
        and (chain.get("numeric_comparison_policy") or {}).get("sha256") == NUMERIC_POLICY_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("stock_day_identity_projection") or ()) == ("trade_date", "symbol", "provider")
        and tuple(candidate.get("quarterly_source_projection") or ()) == EVENT_FIELDS
        and candidate.get("event_identity") == ["instrument", "report_date"]
        and candidate.get("event_identity_must_be_unique") is True
        and candidate.get("valid_range") == {"lower": 0.0, "lower_inclusive": False, "upper": 1.0, "upper_inclusive": True}
        and coverage.get("minimum_median_coverage") == 0.95
        and coverage.get("minimum_p05_coverage") == 0.9
        and coverage.get("minimum_p05_eligible_names") == 50
        and coverage.get("minimum_non_overlapping_three_session_cohorts") == 200
        and coverage.get("comparison_values_read_before_coverage_pass") is False
        and unique.get("complete_definition_count") == FULL_DEFINITION_COUNT
        and unique.get("complete_definition_order_sha256") == FULL_DEFINITION_ORDER_SHA256
        and unique.get("numeric_comparator_count") == COMPARISON_COUNT
        and unique.get("numeric_comparator_order_sha256") == COMPARISON_ORDER_SHA256
        and unique.get("all_101_numeric_comparators_must_pass") is True
        and len(reconstruct_comparisons(spec)) == COMPARISON_COUNT
        and finite.get("trial_id") == "wf071_quarterly_net_profit_scale_rank_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("complexity") == 1
        and finite.get("expected_trial_count") == 1
        and boundary.get("quarterly_or_stock_day_source_rows_read_before_this_freeze") is False
        and boundary.get("candidate_or_comparison_values_read_before_this_freeze") is False
        and boundary.get("historical_forward_return_fields_read") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign071FeatureError("Campaign071 protocol semantics changed")
    return spec


def prepare_events(events: pd.DataFrame, calendar: pd.DatetimeIndex) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    if tuple(events.columns) != EVENT_FIELDS:
        raise Campaign071FeatureError("quarterly source projection changed")
    work = events.copy()
    work["instrument"] = work["instrument"].astype(str).str.upper()
    for column in ("report_date", "announcement_date"):
        work[column] = pd.to_datetime(work[column], errors="coerce").dt.normalize()
    work["net_profit"] = pd.to_numeric(work["net_profit"], errors="coerce")
    if (
        work.empty
        or work[["instrument", "report_date", "announcement_date"]].isna().any().any()
        or work.duplicated(["instrument", "report_date"]).any()
    ):
        raise Campaign071FeatureError("quarterly event identities changed")
    work.loc[~(np.isfinite(work["net_profit"]) & work["net_profit"].gt(0.0)), "net_profit"] = np.nan
    calendar_values = calendar.to_numpy(dtype="datetime64[ns]")
    positions = np.searchsorted(calendar_values, work["announcement_date"].to_numpy(dtype="datetime64[ns]"), side="right")
    in_range = positions < len(calendar_values)
    work = work.loc[in_range].copy()
    work["effective_position"] = positions[in_range]
    work = (
        work.sort_values(["instrument", "effective_position", "report_date", "announcement_date"], kind="stable")
        .drop_duplicates(["instrument", "effective_position"], keep="last")
        .reset_index(drop=True)
    )
    result: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for symbol, group in work.groupby("instrument", sort=False):
        finite = group.loc[np.isfinite(group["net_profit"]) & group["net_profit"].gt(0.0)]
        if not finite.empty:
            result[str(symbol)] = (
                finite["effective_position"].to_numpy(dtype=np.int64),
                finite[["net_profit"]].to_numpy(dtype=np.float64),
            )
    return result


def attach_states(
    frame: pd.DataFrame,
    *,
    symbol: str,
    calendar: pd.DatetimeIndex,
    events_by_symbol: dict[str, tuple[np.ndarray, np.ndarray]],
) -> pd.DataFrame:
    if tuple(frame.columns) != ("trade_date", "symbol", "provider"):
        raise Campaign071FeatureError("joint-clean identity projection changed")
    out = frame.copy()
    out["trade_date"] = pd.to_datetime(out["trade_date"], errors="coerce").dt.normalize()
    out["symbol"] = out["symbol"].astype(str).str.upper()
    out["provider"] = out["provider"].astype(str).str.lower()
    if out.empty:
        out["net_profit"] = pd.Series(dtype="float64")
        return out
    if out["trade_date"].isna().any() or set(out["symbol"].unique()) != {symbol.upper()} or out.duplicated(["trade_date", "symbol"]).any():
        raise Campaign071FeatureError(f"joint-clean identity changed for {symbol}")
    calendar_values = calendar.to_numpy(dtype="datetime64[ns]")
    dates = out["trade_date"].to_numpy(dtype="datetime64[ns]")
    positions = np.searchsorted(calendar_values, dates, side="left")
    if (positions >= len(calendar_values)).any() or not np.array_equal(calendar_values[positions], dates):
        raise Campaign071FeatureError(f"joint-clean dates escaped calendar for {symbol}")
    states = np.full(len(out), np.nan, dtype=np.float64)
    event_state = events_by_symbol.get(symbol.upper())
    if event_state is not None:
        event_positions, event_values = event_state
        chosen = np.searchsorted(event_positions, positions, side="right") - 1
        valid = chosen >= 0
        states[valid] = event_values[chosen[valid], 0]
    out["net_profit"] = states
    return out


def rank_year_frame(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    raw = pd.to_numeric(work["net_profit"], errors="coerce")
    raw = raw.where(np.isfinite(raw) & raw.gt(0.0))
    ranks = raw.groupby(work["trade_date"], sort=False).rank(method="average", pct=True)
    values = ranks.to_numpy(dtype=np.float64)
    eligible = np.isfinite(values) & (values > 0.0) & (values <= 1.0)
    work[FACTOR_NAME] = np.where(eligible, values, np.nan)
    work[f"{FACTOR_NAME}_eligible"] = eligible
    work["provider"] = "quarterly_quality_pit"
    return work


def validate_value_semantics(frame: pd.DataFrame) -> tuple[int, int]:
    if tuple(frame.columns) != OUTPUT_COLUMNS:
        raise Campaign071FeatureError("Campaign071 partition columns changed")
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"].astype(bool)
    if values[eligible].isna().any() or ((values[eligible] <= 0.0) | (values[eligible] > 1.0)).any() or values[~eligible].notna().any():
        raise Campaign071FeatureError("Campaign071 value semantics changed")
    return len(frame), int(eligible.sum())


def verify_snapshot_files(manifest_path: Path, *, workers: int = 4) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    expected = (output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json").resolve()
    if manifest_path != expected:
        raise Campaign071FeatureError("Campaign071 manifest path changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _runtime["_validate_manifest"](manifest)
    partition_root = (manifest_path.parent / "partitions").resolve()

    def verify(item: dict[str, Any]) -> tuple[int, int]:
        path = Path(str(item["path"])).expanduser().resolve()
        path.relative_to(partition_root)
        if _sha256(path) != item["output_byte_sha256"]:
            raise Campaign071FeatureError(f"partition byte hash changed: {path}")
        frame = pd.read_parquet(path)
        if len(frame) != item["rows"] or _runtime["_frame_sha256"](frame) != item["output_frame_sha256"]:
            raise Campaign071FeatureError(f"partition frame changed: {path}")
        return validate_value_semantics(frame)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        totals = list(pool.map(verify, manifest["files"]))
    digest_rows = [[item["relative_path"], item["output_byte_sha256"], item["output_frame_sha256"], item["rows"]] for item in manifest["files"]]
    if not (
        _runtime["_json_digest"](digest_rows) == manifest["dataset_sha256"]
        and sum(value[0] for value in totals) == EXPECTED_ROWS
        and len(totals) == EXPECTED_PARTITIONS
        and sum(value[1] for value in totals) == (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
    ):
        raise Campaign071FeatureError("Campaign071 aggregate identity changed")
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
    "Campaign071FeatureError": Campaign071FeatureError,
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
    "prepare_events": prepare_events,
    "attach_states": attach_states,
    "rank_and_balance_year_frame": rank_year_frame,
    "verify_snapshot_files": verify_snapshot_files,
}.items():
    _runtime[_name] = _value

_runtime["FACTOR_RANGES"] = {FACTOR_NAME: (0.0, 1.0)}
_runtime["FACTOR_FORMULAS"] = {FACTOR_NAME: FACTOR_FORMULA}

output_root = _runtime["output_root"]
build_snapshot = _runtime["build_snapshot"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    build.add_argument("--workers", type=int, default=4)
    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.command == "build":
        payload = {"snapshot_manifest": str(build_snapshot(data_root=args.data_root, workers=args.workers))}
    elif args.command == "verify":
        payload = verify_snapshot_files(args.manifest, workers=args.workers)
    else:
        load_protocol()
        path = output_root(args.data_root.expanduser().resolve()) / "snapshot_manifest.json"
        payload = {
            "status": "snapshot_present" if path.is_file() else "snapshot_absent_pre_build",
            "snapshot_manifest": str(path),
            "candidate_or_comparison_values_read_by_status": False,
            "historical_daily_price_or_forward_return_values_read_by_status": False,
            "provider_request_issued_by_status": False,
        }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
