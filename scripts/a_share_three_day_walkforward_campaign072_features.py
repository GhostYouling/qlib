#!/usr/bin/env python3
"""Build and verify Campaign072's joint profit/revenue growth-floor rank."""

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
TEMPLATE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign071_features.py"
TEMPLATE_RUNNER_SHA256 = "bc67ea1ebe7bc66faf18d2b5d443ec4b739a83d097646c600b13c30ed0996fec"
FACTOR_NAME = "quarterly_joint_profit_revenue_growth_floor_rank"
FACTOR_FORMULA = (
    "strict-next-session independently forward-filled finite profit_yoy and "
    "revenue_yoy states, raw min(profit_yoy,revenue_yoy), then same-stock-day "
    "average-tie percentile rank"
)
PROTOCOL_SHA256 = "32f16b1e8e07b0d60aa6646f66c52740e330fa02ef631803fb68b55a7e79cc98"
MECHANISM_AUDIT_SHA256 = "b02f240a66ed271fdd05cf75eb325c8c69a6f996749db8e708edc65aba1280ae"
NUMERIC_POLICY_SHA256 = "b24c643d086a73e66844a0e988d65a46aff2f82986c544515422119dd19d7242"
FULL_DEFINITION_COUNT = 103
FULL_DEFINITION_ORDER_SHA256 = "eaef28a5c755176045dfe09ef73e1030bc35b16cf92738f691c450c3af02db0f"
COMPARISON_COUNT = 102
COMPARISON_ORDER_SHA256 = "b473b8e32852dbbd1ca6beeb567805af55b77ec2e91222ec3e75e4bd64a64226"
C68_FACTOR = "quarterly_profit_revenue_acceleration_rank_gap_2r"
C69_FACTOR = "quarterly_profit_growth_roe_transition_gap_2r"
C70_FACTOR = "quarterly_announcement_delay_improvement_yoy_rank_1y"
C71_FACTOR = "quarterly_net_profit_scale_rank"
C68_SNAPSHOT_MANIFEST_SHA256 = "9878e6c0249cb9e965dbfade2ce2b3a355bed5e6a46bf68667c82fc568672004"
C69_SNAPSHOT_MANIFEST_SHA256 = "6023becea579d0f6ed6ac27316421294f13fd6759d6d51790a31940526e363b7"
C70_SNAPSHOT_MANIFEST_SHA256 = "f828ee06ac609580880eb0bfcd2d1fbcaba590e872f57fe5639a468c67edcbd7"
C71_SNAPSHOT_MANIFEST_SHA256 = "438db2c72a0e5a166f87e680109024be7b28ed710edbd6b4d5ce6968e4a3f7fd"
C71_SNAPSHOT_DATASET_SHA256 = "8c6f1eff1b2238132f429eaeae13d9a7fbd9956e89f3499fa1cf68d54435528d"
C71_SNAPSHOT_BINDING_SHA256 = "8b6cb0bbab838bc72977ce0b8c59e4b1894633cfe78c903de01a2fcc65749a71"
C71_RESEARCH_RECORD_SHA256 = "414ea6ae1083e3b5e21c91de9719c0c2b201ba11e6b8af0fe77889da46d1ce56"
CACHE_PUBLICATION_BINDING_SHA256 = "244f70b88be0396f7473c6664835cbb3cdad9135b6692b77c74018b1d53c925b"
CACHE_MANIFEST_SHA256 = "3d81068f07ac61fe4cd04bd1a893e58759c06d88213263135fec5244e309b57b"
EVENT_FIELDS = (
    "instrument",
    "report_date",
    "announcement_date",
    "profit_yoy",
    "revenue_yoy",
)
STATE_FIELDS = ("profit_yoy", "revenue_yoy")
OUTPUT_COLUMNS = (
    "trade_date",
    "symbol",
    "provider",
    FACTOR_NAME,
    f"{FACTOR_NAME}_eligible",
)


class Campaign072FeatureError(RuntimeError):
    """Fail-closed Campaign072 feature error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if not TEMPLATE_RUNNER.is_file() or _sha256(TEMPLATE_RUNNER) != TEMPLATE_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign071 feature runner changed")


_source = TEMPLATE_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign071", "Campaign072"),
    ("campaign071", "campaign072"),
    ("campaign_071", "campaign_072"),
    ("quarterly_net_profit_scale_rank", FACTOR_NAME),
    (
        "strict-next-session finite positive net_profit state, forward-filled only after availability, then same-stock-day average-tie percentile rank",
        FACTOR_FORMULA,
    ),
    ("1d61fc0f0943f512304a722bcf3017e6867fd00ec9a41e1ed310022a526c161f", PROTOCOL_SHA256),
    ("e32457e148b3a4c774fdd5d1f7b6445a47ae8b5767c00f067c952a61a4f530a4", MECHANISM_AUDIT_SHA256),
    ("afe9f33f1b8accdcbb1481604313fcc55e9e84ecbc02098730f0b41adf60c68f", NUMERIC_POLICY_SHA256),
    ("FULL_DEFINITION_COUNT = 102", "FULL_DEFINITION_COUNT = 103"),
    ("5509c7801521a81c259892ad8637bdcdf5440eb11a1e99872091de251d282f08", FULL_DEFINITION_ORDER_SHA256),
    ("COMPARISON_COUNT = 101", "COMPARISON_COUNT = 102"),
    ("8ab835ebc9a5cc4f1b0e8e80a7db027dc7b64837859b43975d544dcf9294eca3", COMPARISON_ORDER_SHA256),
    (
        'EVENT_FIELDS = ("instrument", "report_date", "announcement_date", "net_profit")',
        'EVENT_FIELDS = ("instrument", "report_date", "announcement_date", "profit_yoy", "revenue_yoy")',
    ),
    ('STATE_FIELDS = ("net_profit",)', 'STATE_FIELDS = ("profit_yoy", "revenue_yoy")'),
    ("all_101_numeric_comparators_must_pass", "all_102_numeric_comparators_must_pass"),
    ("wf071_", "wf072_"),
):
    _source = _source.replace(_old, _new)

_namespace: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign072_features_generated",
}
exec(compile(_source, str(TEMPLATE_RUNNER), "exec"), _namespace)
_runtime: dict[str, Any] = _namespace["_runtime"]

DEFAULT_DATA_ROOT: Path = _runtime["DEFAULT_DATA_ROOT"]
DEFAULT_CALENDAR: Path = _runtime["DEFAULT_CALENDAR"]
QUARTERLY_PATH: Path = _runtime["QUARTERLY_PATH"]
QUARTERLY_MANIFEST_PATH: Path = _runtime["QUARTERLY_MANIFEST_PATH"]
EXPECTED_PARTITIONS = int(_runtime["EXPECTED_PARTITIONS"])
EXPECTED_ROWS = int(_runtime["EXPECTED_ROWS"])
DEFAULT_PROTOCOL = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_072_no_return_preregistration.json"
DEFAULT_IMPLEMENTATION_FREEZE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_072_feature_implementation_freeze_20260806.json"
bindings = _runtime["bindings"]


def _require_link(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign072FeatureError(f"Campaign072 {label} changed")


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
            {"name": C71_FACTOR, "score_direction": "higher"},
        ]
    )
    if (
        len(items) != COMPARISON_COUNT
        or _runtime["_comparison_order_digest"](items) != COMPARISON_ORDER_SHA256
        or items[-1] != {"name": C71_FACTOR, "score_direction": "higher"}
    ):
        raise Campaign072FeatureError("Campaign072 comparison order changed")
    return items


def _validate_comparator_sources(spec: dict[str, Any]) -> None:
    chain = spec.get("source_chain") or {}
    cache = chain.get("compact_comparator_cache_v4") or {}
    c68 = chain.get("campaign068_terminal_comparator") or {}
    c69 = chain.get("campaign069_terminal_comparator") or {}
    c70 = chain.get("campaign070_terminal_comparator") or {}
    c71 = chain.get("campaign071_terminal_comparator") or {}
    required = (
        (cache.get("publication_binding_path"), CACHE_PUBLICATION_BINDING_SHA256, "cache publication"),
        (cache.get("manifest_path"), CACHE_MANIFEST_SHA256, "cache manifest"),
        (c68.get("snapshot_manifest_path"), C68_SNAPSHOT_MANIFEST_SHA256, "Campaign068 manifest"),
        (c69.get("snapshot_manifest_path"), C69_SNAPSHOT_MANIFEST_SHA256, "Campaign069 manifest"),
        (c70.get("snapshot_manifest_path"), C70_SNAPSHOT_MANIFEST_SHA256, "Campaign070 manifest"),
        (c71.get("research_record_path"), C71_RESEARCH_RECORD_SHA256, "Campaign071 record"),
        (c71.get("snapshot_binding_path"), C71_SNAPSHOT_BINDING_SHA256, "Campaign071 snapshot binding"),
        (c71.get("snapshot_manifest_path"), C71_SNAPSHOT_MANIFEST_SHA256, "Campaign071 manifest"),
    )
    for raw_path, expected, label in required:
        path = Path(str(raw_path or "")).expanduser()
        if not path.is_absolute():
            path = REPO_ROOT / path
        _require_link(path.resolve(), str(expected), label)
    c71_manifest = json.loads(Path(str(c71["snapshot_manifest_path"])).read_text(encoding="utf-8"))
    if not (
        c71.get("dataset_sha256") == C71_SNAPSHOT_DATASET_SHA256
        and c71.get("factor") == C71_FACTOR
        and c71.get("score_direction") == "higher"
        and c71_manifest.get("dataset_sha256") == C71_SNAPSHOT_DATASET_SHA256
        and c71_manifest.get("factor_names") == [C71_FACTOR]
    ):
        raise Campaign072FeatureError("Campaign072 Campaign071 comparator semantics changed")


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    _require_link(path, PROTOCOL_SHA256, "protocol")
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign072FeatureError("Campaign072 protocol binding failed")
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
        spec.get("kind") == "a_share_three_day_walkforward_campaign072_no_return_preregistration"
        and spec.get("status") == "frozen_before_campaign072_source_candidate_comparison_daily_price_or_return_values"
        and (chain.get("numeric_comparison_policy") or {}).get("sha256") == NUMERIC_POLICY_SHA256
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("stock_day_identity_projection") or ()) == ("trade_date", "symbol", "provider")
        and tuple(candidate.get("quarterly_source_projection") or ()) == EVENT_FIELDS
        and candidate.get("event_identity") == ["instrument", "report_date"]
        and candidate.get("event_identity_must_be_unique") is True
        and candidate.get("raw_combination_rule") == "Exactly min(profit_yoy,revenue_yoy) on the common finite two-field universe."
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
        and unique.get("all_102_numeric_comparators_must_pass") is True
        and len(reconstruct_comparisons(spec)) == COMPARISON_COUNT
        and finite.get("trial_id") == "wf072_quarterly_joint_profit_revenue_growth_floor_rank_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1.0]
        and finite.get("complexity") == 1
        and finite.get("expected_trial_count") == 1
        and boundary.get("quarterly_or_stock_day_source_rows_read_before_this_freeze") is False
        and boundary.get("candidate_or_comparison_values_read_before_this_freeze") is False
        and boundary.get("historical_forward_return_fields_read") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign072FeatureError("Campaign072 protocol semantics changed")
    return spec


def prepare_events(
    events: pd.DataFrame, calendar: pd.DatetimeIndex
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    if tuple(events.columns) != EVENT_FIELDS:
        raise Campaign072FeatureError("quarterly source projection changed")
    work = events.copy()
    work["instrument"] = work["instrument"].astype(str).str.upper()
    for column in ("report_date", "announcement_date"):
        work[column] = pd.to_datetime(work[column], errors="coerce").dt.normalize()
    for column in STATE_FIELDS:
        work[column] = pd.to_numeric(work[column], errors="coerce")
        work.loc[~np.isfinite(work[column]), column] = np.nan
    if (
        work.empty
        or work[["instrument", "report_date", "announcement_date"]].isna().any().any()
        or work.duplicated(["instrument", "report_date"]).any()
    ):
        raise Campaign072FeatureError("quarterly event identities changed")
    calendar_values = calendar.to_numpy(dtype="datetime64[ns]")
    positions = np.searchsorted(
        calendar_values,
        work["announcement_date"].to_numpy(dtype="datetime64[ns]"),
        side="right",
    )
    in_range = positions < len(calendar_values)
    work = work.loc[in_range].copy()
    work["effective_position"] = positions[in_range]
    work = (
        work.sort_values(
            ["instrument", "effective_position", "report_date", "announcement_date"],
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


def attach_states(
    frame: pd.DataFrame,
    *,
    symbol: str,
    calendar: pd.DatetimeIndex,
    events_by_symbol: dict[str, tuple[np.ndarray, np.ndarray]],
) -> pd.DataFrame:
    if tuple(frame.columns) != ("trade_date", "symbol", "provider"):
        raise Campaign072FeatureError("joint-clean identity projection changed")
    out = frame.copy()
    out["trade_date"] = pd.to_datetime(out["trade_date"], errors="coerce").dt.normalize()
    out["symbol"] = out["symbol"].astype(str).str.upper()
    out["provider"] = out["provider"].astype(str).str.lower()
    if out.empty:
        for column in STATE_FIELDS:
            out[column] = pd.Series(dtype="float64")
        return out
    if (
        out["trade_date"].isna().any()
        or set(out["symbol"].unique()) != {symbol.upper()}
        or out.duplicated(["trade_date", "symbol"]).any()
    ):
        raise Campaign072FeatureError(f"joint-clean identity changed for {symbol}")
    calendar_values = calendar.to_numpy(dtype="datetime64[ns]")
    dates = out["trade_date"].to_numpy(dtype="datetime64[ns]")
    positions = np.searchsorted(calendar_values, dates, side="left")
    if (positions >= len(calendar_values)).any() or not np.array_equal(
        calendar_values[positions], dates
    ):
        raise Campaign072FeatureError(f"joint-clean dates escaped calendar for {symbol}")
    states = np.full((len(out), len(STATE_FIELDS)), np.nan, dtype=np.float64)
    event_state = events_by_symbol.get(symbol.upper())
    if event_state is not None:
        event_positions, event_values = event_state
        chosen = np.searchsorted(event_positions, positions, side="right") - 1
        valid = chosen >= 0
        states[valid] = event_values[chosen[valid]]
    for index, column in enumerate(STATE_FIELDS):
        out[column] = states[:, index]
    return out


def rank_year_frame(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    states = work.loc[:, STATE_FIELDS].apply(pd.to_numeric, errors="coerce")
    finite = np.isfinite(states.to_numpy(dtype=np.float64)).all(axis=1)
    raw_floor = states.min(axis=1, skipna=False).where(finite)
    ranks = raw_floor.groupby(work["trade_date"], sort=False).rank(
        method="average", pct=True
    )
    values = ranks.to_numpy(dtype=np.float64)
    eligible = np.isfinite(values) & (values > 0.0) & (values <= 1.0)
    work[FACTOR_NAME] = np.where(eligible, values, np.nan)
    work[f"{FACTOR_NAME}_eligible"] = eligible
    work["provider"] = "quarterly_quality_pit"
    return work


def validate_value_semantics(frame: pd.DataFrame) -> tuple[int, int]:
    if tuple(frame.columns) != OUTPUT_COLUMNS:
        raise Campaign072FeatureError("Campaign072 partition columns changed")
    values = pd.to_numeric(frame[FACTOR_NAME], errors="coerce")
    eligible = frame[f"{FACTOR_NAME}_eligible"].astype(bool)
    if (
        values[eligible].isna().any()
        or ((values[eligible] <= 0.0) | (values[eligible] > 1.0)).any()
        or values[~eligible].notna().any()
    ):
        raise Campaign072FeatureError("Campaign072 value semantics changed")
    return len(frame), int(eligible.sum())


def verify_snapshot_files(manifest_path: Path, *, workers: int = 4) -> dict[str, Any]:
    manifest_path = manifest_path.expanduser().resolve()
    expected = (output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json").resolve()
    if manifest_path != expected:
        raise Campaign072FeatureError("Campaign072 manifest path changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _runtime["_validate_manifest"](manifest)
    partition_root = (manifest_path.parent / "partitions").resolve()

    def verify(item: dict[str, Any]) -> tuple[int, int]:
        path = Path(str(item["path"])).expanduser().resolve()
        path.relative_to(partition_root)
        if _sha256(path) != item["output_byte_sha256"]:
            raise Campaign072FeatureError(f"partition byte hash changed: {path}")
        frame = pd.read_parquet(path)
        if (
            len(frame) != item["rows"]
            or _runtime["_frame_sha256"](frame) != item["output_frame_sha256"]
        ):
            raise Campaign072FeatureError(f"partition frame changed: {path}")
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
        raise Campaign072FeatureError("Campaign072 aggregate identity changed")
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
    "Campaign072FeatureError": Campaign072FeatureError,
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
        payload = {
            "snapshot_manifest": str(
                build_snapshot(data_root=args.data_root, workers=args.workers)
            )
        }
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
