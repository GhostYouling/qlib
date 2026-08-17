#!/usr/bin/env python3
"""Build Campaign088's frozen bipower jump-variation-share snapshot."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterator

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from scripts import a_share_three_day_compact_comparator_cache as cache_v1
from scripts import a_share_three_day_preregistration_binding_validator as bindings
from scripts import a_share_three_day_walkforward_campaign085_features as c85
from scripts import a_share_three_day_walkforward_campaign086_features as c86
from scripts import a_share_three_day_walkforward_campaign086_features_v3 as c86_v3
from scripts import a_share_three_day_walkforward_campaign086_features_v4 as c86_v4
from scripts import a_share_three_day_walkforward_campaign087_features as c87

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = c86.DEFAULT_DATA_ROOT
DEFAULT_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_088_no_return_preregistration.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_088_feature_implementation_freeze_v3_20260807.json"
)
V1_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_088_feature_implementation_freeze_20260807.json"
)
V1_IMPLEMENTATION_FREEZE_SHA256 = (
    "53eda7ab435403620b6a5ee4750c176997dee6c29a575fd7f152ba9dfe637fb3"
)
CLI_IMPORT_REPAIR_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_088_feature_cli_import_repair_protocol_20260807.json"
)
CLI_IMPORT_REPAIR_PROTOCOL_SHA256 = (
    "a46ff6bbbed95f9e379b75e41c9cde4a887c29307c8f289d7965aa83d22c08e9"
)
V2_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_088_feature_implementation_freeze_v2_20260807.json"
)
V2_IMPLEMENTATION_FREEZE_SHA256 = (
    "645ad6dd1a1be7f0e5eb6fb24510ab806fb57d453811aa0a6f18277dd3fdd576"
)
ORDER_MONKEYPATCH_REPAIR_PROTOCOL = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_088_builder_order_monkeypatch_repair_protocol_20260807.json"
)
ORDER_MONKEYPATCH_REPAIR_PROTOCOL_SHA256 = (
    "da0fd6996a592efd529a10a3578117119f0572776295f1311bc33c453d159b68"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign088_features.py"
)

PROTOCOL_SHA256 = "903d8ea131d5e5d9c7d53447c03d715a2ef3eefc96482b6a3521f33a05171eab"
CORRECTION_SHA256 = "a45275c74c610ed846088a75828cb6068eabdf9ff742c89e85cc599c6faf71e2"
CURRENT_STATE_SHA256 = (
    "2268bf9e6c90ac5ac2cdc2098d883d0e80b6b2287836af985dbacc0374797a29"
)
NUMERIC_POLICY_SHA256 = (
    "f3f896ba4609699d1fa7bca5f613004b7e1dcc5eb4145268fc68f93f17479bc3"
)
C87_SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_087_feature_snapshot_binding_20260807.json"
)
C87_SNAPSHOT_BINDING_SHA256 = (
    "acaf2df7105b594e22f0daf697cb3e34db8d9233f32e585e26952c4678c188b0"
)
C87_SNAPSHOT_MANIFEST = c87.output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest_v5.json"
C87_SNAPSHOT_MANIFEST_SHA256 = (
    "3a44a828a5c95712471e2757fc24225607759860f236f10de674fc93927b7bfe"
)
C87_SNAPSHOT_DATASET_SHA256 = (
    "9f92cede97522203ace1dc3879a862cc55e58e4877f91fc407f275d418ba6428"
)

FACTOR_NAME = "intraday_bipower_jump_variation_share_238m"
FACTOR_FORMULA = (
    "on exactly 238 within-half adjacent log-close returns and 236 within-half "
    "adjacent return pairs, RV=sum(r^2), "
    "BV=(pi/2)*(238/236)*sum(abs(r_i)*abs(r_i+1)); return max(RV-BV,0)/RV"
)
OUTPUT_RUN_ID = (
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_walkforward_"
    "campaign088_feature_library_v1"
)
RAW_COLUMNS = ("datetime", "symbol", "provider", "close")
IDENTITY_COLUMNS = c86.IDENTITY_COLUMNS
SELECTED_BAR_COUNT = c86.SELECTED_BAR_COUNT
SOURCE_BAR_COUNT = c86.SOURCE_BAR_COUNT
RETURN_COUNT = 238
PAIR_COUNT = 236
ENDPOINT_TOLERANCE = 1e-12
OUTPUT_COLUMNS = ("stock_day_key", FACTOR_NAME, f"{FACTOR_NAME}_eligible")
EXPECTED_ROWS = c86.EXPECTED_ROWS
EXPECTED_PARTITIONS = c86.EXPECTED_PARTITIONS
EXPECTED_SESSIONS = c86.EXPECTED_SESSIONS
EXPECTED_RAW_PARTITIONS = c86.EXPECTED_RAW_PARTITIONS
EXPECTED_JOINT_CLEAN_ROWS = c86.EXPECTED_JOINT_CLEAN_ROWS
FULL_DEFINITION_COUNT = 119
FULL_DEFINITION_ORDER_SHA256 = (
    "0de791d223395722a74dfec4e4b2e469550c9a34e6f5ff64af4087287da0abb5"
)
COMPARISON_COUNT = 117
COMPARISON_ORDER_SHA256 = (
    "cc176eda08a1dc587a44fe9130dea4bd72db64b3d93a3646b53da593adb8cc1c"
)


class Campaign088FeatureError(RuntimeError):
    """Fail-closed Campaign088 feature error."""


def _sha256(path: Path) -> str:
    return c86._sha256(path)


def _json_digest(value: Any) -> str:
    return c86._json_digest(value)


def _comparison_order_digest(items: list[dict[str, str]]) -> str:
    return c86._comparison_order_digest(items)


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise Campaign088FeatureError(f"Campaign088 {label} changed: {path}")


def _freeze_v26_order(
    items: list[dict[str, str]], *, expected_count: int, expected_digest: str
) -> tuple[tuple[str, str], ...]:
    frozen = tuple((str(item["name"]), str(item["score_direction"])) for item in items)
    materialized = [
        {"name": name, "score_direction": direction} for name, direction in frozen
    ]
    if (
        len(materialized) != expected_count
        or _comparison_order_digest(materialized) != expected_digest
        or materialized[-1] != {"name": c87.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign088FeatureError("Campaign088 v26 frozen order changed")
    return frozen


_FROZEN_V26_COMPARISONS = _freeze_v26_order(
    [
        *c87.reconstruct_comparisons(),
        {"name": c87.FACTOR_NAME, "score_direction": "higher"},
    ],
    expected_count=COMPARISON_COUNT,
    expected_digest=COMPARISON_ORDER_SHA256,
)
_FROZEN_V26_DEFINITIONS = _freeze_v26_order(
    [
        *c87.reconstruct_complete_definitions(),
        {"name": c87.FACTOR_NAME, "score_direction": "higher"},
    ],
    expected_count=FULL_DEFINITION_COUNT,
    expected_digest=FULL_DEFINITION_ORDER_SHA256,
)


def reconstruct_comparisons() -> list[dict[str, str]]:
    items = [
        {"name": name, "score_direction": direction}
        for name, direction in _FROZEN_V26_COMPARISONS
    ]
    if (
        len(items) != COMPARISON_COUNT
        or _comparison_order_digest(items) != COMPARISON_ORDER_SHA256
        or items[-1] != {"name": c87.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign088FeatureError("Campaign088 numeric comparison order changed")
    return items


def reconstruct_complete_definitions() -> list[dict[str, str]]:
    items = [
        {"name": name, "score_direction": direction}
        for name, direction in _FROZEN_V26_DEFINITIONS
    ]
    if (
        len(items) != FULL_DEFINITION_COUNT
        or _comparison_order_digest(items) != FULL_DEFINITION_ORDER_SHA256
        or items[-1] != {"name": c87.FACTOR_NAME, "score_direction": "higher"}
    ):
        raise Campaign088FeatureError("Campaign088 complete definition order changed")
    return items


def load_protocol(path: Path = DEFAULT_PROTOCOL) -> dict[str, Any]:
    path = path.expanduser().resolve()
    _require(path, PROTOCOL_SHA256, "protocol")
    _require(C87_SNAPSHOT_BINDING, C87_SNAPSHOT_BINDING_SHA256, "Campaign087 binding")
    _require(
        C87_SNAPSHOT_MANIFEST, C87_SNAPSHOT_MANIFEST_SHA256, "Campaign087 manifest"
    )
    report = bindings.validate_record(path, data_root=DEFAULT_DATA_ROOT)
    if report.get("all_bindings_passed") is not True:
        raise Campaign088FeatureError("Campaign088 protocol binding failed")
    spec = json.loads(path.read_text(encoding="utf-8"))
    chain = spec.get("source_chain") or {}
    candidate = spec.get("candidate") or {}
    gates = spec.get("ordered_no_return_gates") or {}
    coverage = gates.get("coverage_and_capacity_before_comparison_values") or {}
    unique = gates.get("uniqueness_after_coverage_only") or {}
    finite = spec.get("finite_development_catalog_if_admitted") or {}
    boundary = spec.get("research_boundary") or {}
    previous = json.loads(C87_SNAPSHOT_MANIFEST.read_text(encoding="utf-8"))
    if not (
        spec.get("kind")
        == "a_share_three_day_walkforward_campaign088_no_return_preregistration"
        and spec.get("status")
        == "frozen_before_campaign088_minute_source_candidate_comparison_daily_price_or_return_values"
        and (chain.get("prevalue_authority_and_timestamp_correction") or {}).get(
            "sha256"
        )
        == CORRECTION_SHA256
        and (chain.get("authoritative_iteration_state") or {}).get("sha256")
        == CURRENT_STATE_SHA256
        and (chain.get("numeric_comparator_policy_v26") or {}).get("sha256")
        == NUMERIC_POLICY_SHA256
        and (chain.get("campaign087_terminal_numeric_comparator") or {}).get(
            "dataset_sha256"
        )
        == C87_SNAPSHOT_DATASET_SHA256
        and previous.get("dataset_sha256") == C87_SNAPSHOT_DATASET_SHA256
        and previous.get("factor_names") == [c87.FACTOR_NAME]
        and candidate.get("name") == FACTOR_NAME
        and candidate.get("direction") == "higher"
        and tuple(candidate.get("minute_source_projection") or ()) == RAW_COLUMNS
        and tuple(candidate.get("stock_day_identity_projection") or ())
        == IDENTITY_COLUMNS
        and candidate.get("selected_close_count") == SELECTED_BAR_COUNT
        and candidate.get("total_return_count") == RETURN_COUNT
        and candidate.get("total_adjacent_pair_count") == PAIR_COUNT
        and candidate.get("endpoint_canonicalization_tolerance") == ENDPOINT_TOLERANCE
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
        and unique.get("numeric_comparator_order_sha256") == COMPARISON_ORDER_SHA256
        and unique.get("all_117_numeric_comparators_must_pass") is True
        and len(reconstruct_comparisons()) == COMPARISON_COUNT
        and len(reconstruct_complete_definitions()) == FULL_DEFINITION_COUNT
        and finite.get("trial_id")
        == "wf088_intraday_bipower_jump_variation_share_238m_single_higher"
        and finite.get("feature_set") == [FACTOR_NAME]
        and finite.get("weights") == [1]
        and finite.get("expected_trial_count") == 1
        and boundary.get("comparison_values_read_before_coverage_pass") is False
        and boundary.get("daily_price_fields_read_before_admissibility") is False
        and boundary.get("forward_return_fields_read_before_admissibility") is False
        and boundary.get("candidate49_ledgers_may_change") is False
        and boundary.get("provider_request_issued") is False
    ):
        raise Campaign088FeatureError("Campaign088 protocol semantics changed")
    return spec


def compute_bipower_jump_share(
    closes: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return score, eligibility, realized variation, and bipower variation."""

    close = np.asarray(closes, dtype=np.float64)
    if close.ndim != 2 or close.shape[1] != SELECTED_BAR_COUNT:
        raise Campaign088FeatureError("bipower jump share requires an n-by-240 array")
    source_valid = np.isfinite(close).all(axis=1) & (close > 0.0).all(axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        logged = np.log(close)
        morning = np.diff(logged[:, :120], axis=1)
        afternoon = np.diff(logged[:, 120:], axis=1)
    returns = np.concatenate((morning, afternoon), axis=1)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        pair_products = np.concatenate(
            (
                np.abs(morning[:, :-1]) * np.abs(morning[:, 1:]),
                np.abs(afternoon[:, :-1]) * np.abs(afternoon[:, 1:]),
            ),
            axis=1,
        )
        rv = np.sum(returns * returns, axis=1, dtype=np.float64)
        bv = (
            (np.pi / 2.0)
            * (float(RETURN_COUNT) / float(PAIR_COUNT))
            * np.sum(pair_products, axis=1, dtype=np.float64)
        )
    support = source_valid & np.isfinite(rv) & (rv > 0.0) & np.isfinite(bv)
    result = np.full(len(close), np.nan, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        score = np.maximum(rv[support] - bv[support], 0.0) / rv[support]
    score[np.abs(score) <= ENDPOINT_TOLERANCE] = 0.0
    score[np.abs(score - 1.0) <= ENDPOINT_TOLERANCE] = 1.0
    valid_score = np.isfinite(score) & (score >= 0.0) & (score <= 1.0)
    positions = np.flatnonzero(support)
    result[positions[valid_score]] = score[valid_score]
    eligible = np.isfinite(result) & (result >= 0.0) & (result <= 1.0)
    result[~eligible] = np.nan
    return result, eligible, rv, bv


def extract_bipower_jump_share(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    if tuple(raw.columns) != RAW_COLUMNS:
        raise Campaign088FeatureError(
            f"unexpected raw columns for {symbol}: {tuple(raw.columns)}"
        )
    empty = pd.DataFrame(
        {
            "trade_date": pd.Series(dtype="datetime64[ns]"),
            FACTOR_NAME: pd.Series(dtype="float64"),
        }
    )
    if raw.empty:
        return empty, {
            "source_rows": 0,
            "source_sessions": 0,
            "valid_serial_persistence_sessions": 0,
            "invalid_selected_source_sessions": 0,
            "insufficient_pair_sessions": 0,
            "zero_range_selected_bars": 0,
            "retained_informative_pairs": 0,
        }
    work = raw.copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["symbol"] = work["symbol"].astype(str).str.upper()
    work["provider"] = work["provider"].astype(str).str.lower()
    work["close"] = pd.to_numeric(work["close"], errors="coerce")
    if (
        work["datetime"].isna().any()
        or set(work["symbol"].unique()) != {symbol.upper()}
        or set(work["provider"].unique()) != {"tushare"}
        or work.duplicated(["datetime"]).any()
    ):
        raise Campaign088FeatureError(f"raw minute identity changed for {symbol}")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    counts = work.groupby("trade_date", sort=True, observed=True).size()
    distinct = work.groupby("trade_date", sort=True, observed=True)[
        "minute_code"
    ].nunique()
    if (
        counts.empty
        or not counts.eq(SOURCE_BAR_COUNT).all()
        or not distinct.eq(SOURCE_BAR_COUNT).all()
        or not work["minute_code"].isin(c86.SOURCE_MINUTE_CODE_SET).all()
    ):
        raise Campaign088FeatureError(f"raw minute grid changed for {symbol}")
    continuous = work.loc[
        work["minute_code"].isin(c86.CONTINUOUS_MINUTE_CODE_SET),
        ["trade_date", "minute_code", "close"],
    ].copy()
    continuous["minute_code"] = pd.Categorical(
        continuous["minute_code"],
        categories=c86.CONTINUOUS_MINUTE_CODES,
        ordered=True,
    )
    continuous = continuous.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(counts.index).normalize()
    if len(continuous) != len(dates) * SELECTED_BAR_COUNT:
        raise Campaign088FeatureError(f"continuous minute grid changed for {symbol}")
    closes = (
        continuous["close"]
        .to_numpy(dtype=np.float64)
        .reshape(len(dates), SELECTED_BAR_COUNT)
    )
    values, eligible, rv, _bv = compute_bipower_jump_share(closes)
    source_valid = np.isfinite(closes).all(axis=1) & (closes > 0.0).all(axis=1)
    logged = np.full_like(closes, np.nan)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        logged[source_valid] = np.log(closes[source_valid])
    return_frame = np.concatenate(
        (np.diff(logged[:, :120], axis=1), np.diff(logged[:, 120:], axis=1)),
        axis=1,
    )
    return pd.DataFrame({"trade_date": dates, FACTOR_NAME: values}), {
        "source_rows": len(work),
        "source_sessions": len(dates),
        "valid_serial_persistence_sessions": int(eligible.sum()),
        "invalid_selected_source_sessions": int((~source_valid).sum()),
        "insufficient_pair_sessions": int(
            (source_valid & (~np.isfinite(rv) | (rv <= 0.0))).sum()
        ),
        "zero_range_selected_bars": int(
            ((return_frame == 0.0) & source_valid[:, None]).sum()
        ),
        "retained_informative_pairs": int(source_valid.sum()) * PAIR_COUNT,
    }


def output_root(data_root: Path) -> Path:
    return (
        data_root
        / "derived/a_share/rich/tushare/minute_walkforward_campaign088_feature_library"
        / OUTPUT_RUN_ID
    )


def _load_implementation_freeze() -> dict[str, Any]:
    _require(
        V1_IMPLEMENTATION_FREEZE,
        V1_IMPLEMENTATION_FREEZE_SHA256,
        "v1 implementation freeze",
    )
    _require(
        CLI_IMPORT_REPAIR_PROTOCOL,
        CLI_IMPORT_REPAIR_PROTOCOL_SHA256,
        "CLI import repair protocol",
    )
    _require(
        V2_IMPLEMENTATION_FREEZE,
        V2_IMPLEMENTATION_FREEZE_SHA256,
        "v2 implementation freeze",
    )
    _require(
        ORDER_MONKEYPATCH_REPAIR_PROTOCOL,
        ORDER_MONKEYPATCH_REPAIR_PROTOCOL_SHA256,
        "builder order monkeypatch repair protocol",
    )
    if not DEFAULT_IMPLEMENTATION_FREEZE.is_file():
        raise Campaign088FeatureError("Campaign088 v3 implementation freeze is absent")
    record = json.loads(DEFAULT_IMPLEMENTATION_FREEZE.read_text(encoding="utf-8"))
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign088_feature_implementation_freeze_v3"
        and record.get("status")
        == "builder_order_repair_frozen_before_campaign088_minute_source_rows_or_candidate_values"
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (record.get("v1_implementation_freeze") or {}).get("sha256")
        == V1_IMPLEMENTATION_FREEZE_SHA256
        and (record.get("cli_import_repair_protocol") or {}).get("sha256")
        == CLI_IMPORT_REPAIR_PROTOCOL_SHA256
        and (record.get("v2_implementation_freeze") or {}).get("sha256")
        == V2_IMPLEMENTATION_FREEZE_SHA256
        and (record.get("order_monkeypatch_repair_protocol") or {}).get("sha256")
        == ORDER_MONKEYPATCH_REPAIR_PROTOCOL_SHA256
        and (record.get("feature_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("candidate_source_rows_read_before_freeze") is False
        and record.get("candidate_values_computed_before_freeze") is False
        and record.get("comparison_values_read_before_freeze") is False
        and record.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
        and record.get("provider_request_issued_before_freeze") is False
    ):
        raise Campaign088FeatureError("Campaign088 v3 implementation freeze changed")
    return record


@contextlib.contextmanager
def _patched_campaign086_builder() -> Iterator[None]:
    replacements = {
        "__file__": str(Path(__file__).resolve()),
        "DEFAULT_PROTOCOL": DEFAULT_PROTOCOL,
        "DEFAULT_IMPLEMENTATION_FREEZE": DEFAULT_IMPLEMENTATION_FREEZE,
        "PROTOCOL_SHA256": PROTOCOL_SHA256,
        "FACTOR_NAME": FACTOR_NAME,
        "FACTOR_FORMULA": FACTOR_FORMULA,
        "OUTPUT_RUN_ID": OUTPUT_RUN_ID,
        "RAW_COLUMNS": RAW_COLUMNS,
        "OUTPUT_COLUMNS": OUTPUT_COLUMNS,
        "load_protocol": load_protocol,
        "_load_implementation_freeze": _load_implementation_freeze,
        "extract_serial_persistence": extract_bipower_jump_share,
        "attach_values": c86_v3.attach_values,
        "compact_stock_day_keys": c86_v4.compact_stock_day_keys,
        "output_root": output_root,
    }
    original = {name: getattr(c86, name) for name in replacements}
    try:
        for name, value in replacements.items():
            setattr(c86, name, value)
        yield
    finally:
        for name, value in original.items():
            setattr(c86, name, value)


def _dataset_material(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocol_sha256": manifest["protocol"]["sha256"],
        "implementation_freeze_sha256": manifest["implementation_freeze"]["sha256"],
        "raw_manifest_sha256": manifest["source"]["raw_manifest_sha256"],
        "joint_clean_manifest_sha256": manifest["source"][
            "joint_clean_manifest_sha256"
        ],
        "eligible_keys_sha256": manifest["eligible_universe"]["keys_sha256"],
        "factor_name": FACTOR_NAME,
        "factor_formula": FACTOR_FORMULA,
        "factor_eligible_rows": manifest["factor_eligible_rows"][FACTOR_NAME],
        "files": manifest["files"],
    }


def build_snapshot(
    *, data_root: Path, workers: int = 8, confirm_build: bool = False
) -> Path:
    if not confirm_build:
        raise Campaign088FeatureError("Campaign088 build requires --confirm-build")
    _load_implementation_freeze()
    if output_root(data_root.expanduser().resolve()).exists():
        raise Campaign088FeatureError("Campaign088 output already exists")
    with _patched_campaign086_builder():
        manifest_path = c86.build_snapshot(
            data_root=data_root,
            workers=workers,
            confirm_build=True,
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    old_quality = manifest.get("quality") or {}
    manifest["kind"] = "a_share_three_day_walkforward_campaign088_feature_snapshot"
    manifest["feature_runner"] = {
        "path": str(Path(__file__).resolve()),
        "sha256": _sha256(Path(__file__).resolve()),
    }
    manifest["quality"] = {
        "source_rows": int(old_quality.get("source_rows", 0)),
        "source_sessions": int(old_quality.get("source_sessions", 0)),
        "valid_bipower_jump_share_sessions": int(
            old_quality.get("valid_serial_persistence_sessions", 0)
        ),
        "invalid_selected_close_sessions": int(
            old_quality.get("invalid_selected_source_sessions", 0)
        ),
        "nonpositive_realized_variation_sessions": int(
            old_quality.get("insufficient_pair_sessions", 0)
        ),
        "zero_returns": int(old_quality.get("zero_range_selected_bars", 0)),
        "required_bipower_pairs": int(old_quality.get("retained_informative_pairs", 0)),
    }
    manifest["dataset_sha256"] = _json_digest(_dataset_material(manifest))
    c85._atomic_json(manifest, manifest_path)
    return manifest_path


def verify_snapshot_files(manifest_path: Path) -> dict[str, Any]:
    _load_implementation_freeze()
    path = manifest_path.expanduser().resolve()
    expected = output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
    if path != expected.resolve() or not path.is_file():
        raise Campaign088FeatureError("Campaign088 manifest path changed")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign088_feature_snapshot"
        and manifest.get("status") == "complete_no_return_candidate_snapshot"
        and (manifest.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (manifest.get("implementation_freeze") or {}).get("sha256")
        == _sha256(DEFAULT_IMPLEMENTATION_FREEZE)
        and (manifest.get("feature_runner") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and manifest.get("factor_names") == [FACTOR_NAME]
        and manifest.get("factor_directions") == {FACTOR_NAME: "higher"}
        and manifest.get("factor_ranges") == {FACTOR_NAME: [0.0, 1.0]}
        and manifest.get("rows") == EXPECTED_ROWS
        and manifest.get("partitions") == EXPECTED_PARTITIONS
        and manifest.get("calendar_sessions") == EXPECTED_SESSIONS
        and manifest.get("comparison_values_read") is False
        and manifest.get("historical_daily_price_fields_read") == []
        and manifest.get("historical_forward_returns_read") is False
        and manifest.get("provider_request_issued") is False
        and manifest.get("dataset_sha256") == _json_digest(_dataset_material(manifest))
    ):
        raise Campaign088FeatureError("Campaign088 manifest semantics changed")
    rows = 0
    eligible_count = 0
    all_keys: list[np.ndarray] = []
    for record in manifest.get("files") or []:
        partition = path.parent / str(record["path"])
        if _sha256(partition) != record.get("sha256"):
            raise Campaign088FeatureError("Campaign088 partition bytes changed")
        frame = pd.read_parquet(partition, columns=list(OUTPUT_COLUMNS))
        if c85._frame_sha256(frame) != record.get("frame_sha256"):
            raise Campaign088FeatureError("Campaign088 partition frame changed")
        values = frame[FACTOR_NAME].to_numpy(dtype=np.float64)
        flags = frame[f"{FACTOR_NAME}_eligible"].astype(bool).to_numpy()
        finite = np.isfinite(values)
        if not (
            np.array_equal(flags, finite)
            and ((values[finite] >= 0.0) & (values[finite] <= 1.0)).all()
            and int(flags.sum()) == int(record["eligible_rows"])
            and cache_v1.canonical_column_sha256(values)
            == record.get("factor_canonical_value_sha256")
        ):
            raise Campaign088FeatureError("Campaign088 values changed")
        rows += len(frame)
        eligible_count += int(flags.sum())
        all_keys.append(frame["stock_day_key"].to_numpy(dtype=np.int64))
    keys = np.concatenate(all_keys)
    key_sha = hashlib.sha256(keys.astype("<i8", copy=False).tobytes()).hexdigest()
    if not (
        rows == EXPECTED_ROWS
        and eligible_count
        == (manifest.get("factor_eligible_rows") or {}).get(FACTOR_NAME)
        and len(np.unique(keys)) == EXPECTED_ROWS
        and np.all(keys[1:] > keys[:-1])
        and key_sha == (manifest.get("eligible_universe") or {}).get("keys_sha256")
    ):
        raise Campaign088FeatureError("Campaign088 aggregate identity changed")
    return {
        "status": "verified",
        "dataset_sha256": manifest["dataset_sha256"],
        "partitions": len(manifest["files"]),
        "rows": rows,
        "eligible_rows": eligible_count,
        "comparison_values_read": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def status(data_root: Path = DEFAULT_DATA_ROOT) -> dict[str, Any]:
    load_protocol()
    path = output_root(data_root.expanduser().resolve()) / "snapshot_manifest.json"
    return {
        "status": "snapshot_present" if path.is_file() else "snapshot_absent_prebuild",
        "manifest_path": str(path),
        "comparison_values_read_by_status": False,
        "historical_daily_price_or_forward_return_values_read_by_status": False,
        "provider_request_issued_by_status": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    build.add_argument("--workers", type=int, default=8)
    build.add_argument("--confirm-build", action="store_true")
    inspect = sub.add_parser("status")
    inspect.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    verify = sub.add_parser("verify")
    verify.add_argument("--manifest", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    if args.command == "status":
        print(json.dumps(status(args.data_root), sort_keys=True))
        return 0
    if args.command == "build":
        print(
            build_snapshot(
                data_root=args.data_root,
                workers=args.workers,
                confirm_build=args.confirm_build,
            )
        )
        return 0
    manifest = args.manifest or (
        output_root(DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
    )
    print(json.dumps(verify_snapshot_files(manifest), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
