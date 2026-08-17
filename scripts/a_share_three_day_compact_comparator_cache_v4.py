#!/usr/bin/env python3
"""Build and verify the v4 dynamic-quality compact comparator cache."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from scripts import a_share_three_day_compact_comparator_cache as v1
from scripts import a_share_three_day_compact_comparator_cache_v2 as v2
from scripts import a_share_three_day_compact_comparator_cache_v3 as v3
from scripts import a_share_three_day_walkforward_campaign058_no_return_audit as quality_audit


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_compact_comparator_cache_protocol_v4_20260806.json"
)
PROTOCOL_SHA256 = "19f2086ec4e19b25f69800ee750cef0dc51cc3150e29808f2d9e2585b055d533"
V3_BUILDER_SHA256 = "cf39aa8293990ef00c1d429a96157cbd33c6fb41c5a630ddb8c9c9420a2fd200"
V3_FAILURE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_compact_comparator_cache_v3_build_failure_20260806.json"
)
V3_FAILURE_SHA256 = "00e7c051cf70518195d9d9ce23d234fe7673b46f1a145d1b96c0dd0175b9294c"
V3_DIAGNOSIS_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_compact_comparator_cache_v3_equivalence_diagnosis_20260806.json"
)
V3_DIAGNOSIS_SHA256 = "7f90fe174da2bf7f5fb6b347d6c296a8bc399d2723039617e2dde9062e2a99da"
QUALITY_AUDIT_SHA256 = "84bf18ce4ccda2292235bd86cbc7be707560e04622ede15d0dfd2747ef79f8a0"
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_compact_comparator_cache_implementation_freeze_v4_20260806.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_compact_comparator_cache_v4.py"
)
DEFAULT_DATA_ROOT = v1.DEFAULT_DATA_ROOT
DEFAULT_OUTPUT_ROOT = (
    DEFAULT_DATA_ROOT
    / "derived/a_share/rich/tushare/compact_comparator_cache/"
    "campaign067_terminal_numeric98_v4"
)
FAILED_FORMAL_OUTPUT_ROOTS = (
    v1.DEFAULT_OUTPUT_ROOT,
    v2.DEFAULT_OUTPUT_ROOT,
    v3.DEFAULT_OUTPUT_ROOT,
)
DYNAMIC_COMPARATORS = ("quality_growth", "quality_score")
AUXILIARY_COLUMNS = (
    "quality_raw_roe",
    "quality_raw_profit_yoy",
    "quality_raw_revenue_yoy",
)
RAW_SOURCE_FIELDS = {
    "quality_raw_roe": "roe",
    "quality_raw_profit_yoy": "profit_yoy",
    "quality_raw_revenue_yoy": "revenue_yoy",
}
EXPECTED_LOGICAL_NAME_LIST_SHA256 = (
    "7e53d979ab48191118ba75e4255ee0fabc3dadb72797b19e06490595022a1a76"
)
EXPECTED_FIXED_NAME_LIST_SHA256 = (
    "8db0a2f5631840812d3d31bc3466b9a379177c39fe9a2763fde8bcc8a9314a3d"
)
EXPECTED_DYNAMIC_NAME_LIST_SHA256 = (
    "f6bf55b0a0710a719bacf11b72dd591f03fb8b4336856294038d6a387eb730fc"
)
EXPECTED_AUXILIARY_NAME_LIST_SHA256 = (
    "812bd69eb9c2cbce6ba24cf973fdbab7f6f03f89acfafdd95e28fe2924962f00"
)
EXPECTED_PHYSICAL_NAME_LIST_SHA256 = (
    "e21409c868bdea2d4941ccc4c8e3681625693cae3850307bb17cfa9955781848"
)


class CompactComparatorCacheV4Error(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _require(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise CompactComparatorCacheV4Error(f"{label} changed")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _library_layout() -> dict[str, Any]:
    definitions, complete = v1.numeric_definitions()
    logical_names = [str(item["name"]) for item in definitions]
    fixed_indices = [
        index
        for index, name in enumerate(logical_names)
        if name not in DYNAMIC_COMPARATORS
    ]
    fixed_definitions = [definitions[index] for index in fixed_indices]
    fixed_names = [str(item["name"]) for item in fixed_definitions]
    physical_names = [*fixed_names, *AUXILIARY_COLUMNS]
    if not (
        len(definitions) == 98
        and len(complete) == 99
        and len(fixed_definitions) == 96
        and len(physical_names) == 99
        and _json_sha256(logical_names) == EXPECTED_LOGICAL_NAME_LIST_SHA256
        and _json_sha256(fixed_names) == EXPECTED_FIXED_NAME_LIST_SHA256
        and _json_sha256(list(DYNAMIC_COMPARATORS))
        == EXPECTED_DYNAMIC_NAME_LIST_SHA256
        and _json_sha256(list(AUXILIARY_COLUMNS))
        == EXPECTED_AUXILIARY_NAME_LIST_SHA256
        and _json_sha256(physical_names) == EXPECTED_PHYSICAL_NAME_LIST_SHA256
    ):
        raise CompactComparatorCacheV4Error("compact-cache v4 library layout changed")
    return {
        "definitions": definitions,
        "complete_definitions": complete,
        "logical_names": logical_names,
        "fixed_indices": fixed_indices,
        "fixed_definitions": fixed_definitions,
        "fixed_names": fixed_names,
        "physical_names": physical_names,
    }


def load_protocol() -> dict[str, Any]:
    _require(PROTOCOL_PATH, PROTOCOL_SHA256, "compact-cache v4 protocol")
    _require(V3_FAILURE_PATH, V3_FAILURE_SHA256, "compact-cache v3 failure")
    _require(V3_DIAGNOSIS_PATH, V3_DIAGNOSIS_SHA256, "compact-cache v3 diagnosis")
    _require(Path(v3.__file__).resolve(), V3_BUILDER_SHA256, "compact-cache v3 builder")
    _require(
        Path(quality_audit.__file__).resolve(),
        QUALITY_AUDIT_SHA256,
        "Campaign058 quality semantics",
    )
    inherited = v3.load_protocol()
    layout = _library_layout()
    spec = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    chain = spec.get("authoritative_protocol_chain") or []
    failure = spec.get("recorded_v3_failure") or {}
    diagnosis = spec.get("bound_v3_diagnosis") or {}
    output = spec.get("frozen_output") or {}
    library = spec.get("frozen_library_and_keys") or {}
    recipe = spec.get("dynamic_quality_recipe_contract") or {}
    capture = spec.get("capture_and_alignment_contract") or {}
    equivalence = spec.get("semantic_equivalence_contract") or {}
    boundary = spec.get("research_boundary") or {}
    if not (
        spec.get("version") == 4
        and spec.get("kind")
        == "a_share_three_day_candidate_independent_compact_comparator_cache_protocol"
        and spec.get("status")
        == "frozen_dynamic_quality_composite_repair_before_v4_values"
        and [item.get("sha256") for item in chain]
        == [v1.PROTOCOL_SHA256, v2.PROTOCOL_SHA256, v3.PROTOCOL_SHA256]
        and failure.get("sha256") == V3_FAILURE_SHA256
        and failure.get("v3_formal_output_published") is False
        and failure.get("v3_temporary_values_reusable_for_v4_publication") is False
        and diagnosis.get("sha256") == V3_DIAGNOSIS_SHA256
        and diagnosis.get("mismatch_names") == list(DYNAMIC_COMPARATORS)
        and output.get("output_root") == str(DEFAULT_OUTPUT_ROOT)
        and output.get(
            "failed_v1_v2_or_v3_temporary_values_may_be_reused_for_publication"
        )
        is False
        and library.get("eligibility_rows") == v1.EXPECTED_ROWS
        and library.get("eligibility_keys_sha256") == v1.EXPECTED_KEYS_SHA256
        and library.get("logical_numeric_comparator_count") == 98
        and library.get("logical_numeric_order_sha256")
        == v1.EXPECTED_NUMERIC_ORDER_SHA256
        and library.get("fixed_materialized_comparator_count") == 96
        and library.get("physical_float64_column_count") == 99
        and library.get("physical_name_list_json_sha256")
        == EXPECTED_PHYSICAL_NAME_LIST_SHA256
        and recipe.get("dynamic_comparators") == list(DYNAMIC_COMPARATORS)
        and recipe.get("raw_auxiliary_columns") == list(AUXILIARY_COLUMNS)
        and recipe.get("candidate_intersection_precedes_ranking") is True
        and recipe.get("rank_method") == "average"
        and recipe.get("rank_pct") is True
        and recipe.get("global_materialized_quality_growth_or_quality_score_may_be_stored")
        is False
        and capture.get(
            "v3_global_values_for_quality_growth_and_quality_score_must_be_discarded_before_physical_partition_write"
        )
        is True
        and equivalence.get("campaign067_comparison_count") == 97
        and equivalence.get(
            "campaign067_comparison_result_objects_exact_equality_required"
        )
        is True
        and boundary.get("v4_comparator_or_raw_auxiliary_values_read_before_protocol_freeze")
        is False
        and boundary.get("historical_daily_price_fields_read") == []
        and boundary.get("historical_forward_returns_read") is False
        and boundary.get("provider_request_issued") is False
        and isinstance(inherited, dict)
        and len(layout["physical_names"]) == 99
    ):
        raise CompactComparatorCacheV4Error("compact-cache v4 protocol changed")
    return spec


def _load_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_PATH.is_file():
        raise CompactComparatorCacheV4Error(
            "compact-cache v4 implementation freeze is absent"
        )
    record = json.loads(IMPLEMENTATION_FREEZE_PATH.read_text(encoding="utf-8"))
    if not (
        record.get("version") == 4
        and record.get("kind")
        == "a_share_three_day_compact_comparator_cache_implementation_freeze"
        and record.get("status")
        == "frozen_before_v4_comparator_raw_auxiliary_or_cache_values_materialized"
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (record.get("builder") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and (record.get("tests") or {}).get("sha256") == _sha256(TEST_PATH)
        and record.get("v4_cache_output_existed_before_freeze") is False
        and record.get("v4_comparison_or_raw_auxiliary_values_read_before_freeze")
        is False
        and record.get("historical_daily_price_or_forward_return_values_read_before_freeze")
        is False
        and record.get("provider_request_issued_before_freeze") is False
    ):
        raise CompactComparatorCacheV4Error(
            "compact-cache v4 implementation freeze changed"
        )
    return record


def reconstruct_dynamic_quality_values(
    *, candidate_keys: np.ndarray, raw_auxiliary_values: dict[str, np.ndarray]
) -> dict[str, np.ndarray]:
    """Recreate the two frozen composites after candidate-key intersection."""

    keys = np.asarray(candidate_keys, dtype=np.int64)
    if (
        len(np.unique(keys)) != len(keys)
        or (len(keys) > 1 and not np.all(keys[1:] > keys[:-1]))
        or set(raw_auxiliary_values) != set(AUXILIARY_COLUMNS)
    ):
        raise CompactComparatorCacheV4Error("dynamic quality inputs changed")
    frame = pd.DataFrame({"session": keys // 4_000_000})
    for name in AUXILIARY_COLUMNS:
        values = np.asarray(raw_auxiliary_values[name], dtype=np.float64)
        if values.shape != (len(keys),):
            raise CompactComparatorCacheV4Error(
                f"dynamic quality auxiliary shape changed for {name}"
            )
        frame[name] = values
    ranks = pd.DataFrame(index=frame.index)
    for name in AUXILIARY_COLUMNS:
        ranks[name] = frame.groupby("session", sort=False)[name].rank(
            method="average", pct=True
        )
    growth = ranks[
        ["quality_raw_profit_yoy", "quality_raw_revenue_yoy"]
    ].mean(axis=1, skipna=False)
    score = ranks[list(AUXILIARY_COLUMNS)].mean(axis=1, skipna=False)
    return {
        "quality_growth": growth.to_numpy(dtype=np.float64),
        "quality_score": score.to_numpy(dtype=np.float64),
    }


def _quality_auxiliary_values(
    *, keys: np.ndarray, comparison_engine: Any
) -> tuple[np.ndarray, dict[str, Any]]:
    """Attach the three frozen raw PIT fields to the global eligible keys."""

    static = quality_audit.verify_static_bindings()
    prior, foundation, _, _, _, _ = quality_audit.prior_audit.terminal.campaign044._context()
    eligible = foundation.quality_listing_eligible_keys(prior.load_protocol()).copy()
    eligible["symbol"] = eligible["symbol"].astype(str).str.upper()
    eligible_keys = comparison_engine._compact_stock_day_keys(
        eligible["trade_date"], eligible["symbol"]
    )
    order = np.argsort(eligible_keys, kind="stable")
    eligible_keys = eligible_keys[order]
    if not (
        len(eligible_keys) == len(keys)
        and len(np.unique(eligible_keys)) == len(eligible_keys)
        and np.array_equal(eligible_keys, keys)
    ):
        raise CompactComparatorCacheV4Error(
            "v4 quality auxiliary eligibility keys changed"
        )
    selected = eligible.iloc[order].copy().reset_index(drop=True)
    market = selected.rename(
        columns={"trade_date": "datetime", "symbol": "instrument"}
    )[["instrument", "datetime"]]
    fundamentals = quality_audit.research.load_fundamentals(
        quality_audit.candidate.QUARTERLY_PATH
    )
    fundamentals["instrument"] = fundamentals["instrument"].astype(str).str.upper()
    calendar = pd.DatetimeIndex(
        pd.to_datetime(
            quality_audit.candidate.DEFAULT_CALENDAR.read_text(
                encoding="utf-8"
            ).splitlines(),
            errors="coerce",
        )
    ).normalize().unique().sort_values()
    if calendar.empty or pd.isna(calendar).any():
        raise CompactComparatorCacheV4Error("accepted calendar values changed")
    attached = quality_audit.research.attach_quality_asof(
        market,
        fundamentals,
        max_age_days=550,
        availability_calendar=calendar,
    )
    observed_keys = comparison_engine._compact_stock_day_keys(
        attached["datetime"], attached["instrument"]
    )
    if not (
        np.array_equal(observed_keys, keys)
        and attached["quality_eligible"].astype("boolean").fillna(False).all()
    ):
        raise CompactComparatorCacheV4Error(
            "v4 quality auxiliary PIT alignment changed"
        )
    matrix = np.column_stack(
        [
            pd.to_numeric(attached[RAW_SOURCE_FIELDS[name]], errors="coerce").to_numpy(
                dtype=np.float64
            )
            for name in AUXILIARY_COLUMNS
        ]
    )
    receipt = {
        "quality_semantics_source_path": str(Path(quality_audit.__file__).resolve()),
        "quality_semantics_source_sha256": QUALITY_AUDIT_SHA256,
        "quarterly_source_path": str(quality_audit.candidate.QUARTERLY_PATH.resolve()),
        "quarterly_source_sha256": quality_audit.candidate.QUARTERLY_SHA256,
        "quarterly_manifest_path": str(
            quality_audit.candidate.QUARTERLY_MANIFEST_PATH.resolve()
        ),
        "quarterly_manifest_sha256": quality_audit.candidate.QUARTERLY_MANIFEST_SHA256,
        "accepted_calendar_path": str(quality_audit.candidate.DEFAULT_CALENDAR.resolve()),
        "accepted_calendar_sha256": quality_audit.candidate.CALENDAR_SHA256,
        "static_binding_receipt": static,
        "rows": len(keys),
        "columns": [
            {
                "name": name,
                "source_field": RAW_SOURCE_FIELDS[name],
                "finite_rows": int(np.isfinite(matrix[:, index]).sum()),
                "nonfinite_rows": int((~np.isfinite(matrix[:, index])).sum()),
                "canonical_value_sha256": v1.canonical_column_sha256(
                    matrix[:, index]
                ),
            }
            for index, name in enumerate(AUXILIARY_COLUMNS)
        ],
        "point_in_time_max_age_days": 550,
        "candidate_intersection_ranking_performed": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }
    del eligible, selected, market, fundamentals, attached
    gc.collect()
    return matrix, receipt


def _write_partitions(
    *,
    root: Path,
    keys: np.ndarray,
    logical_matrix: np.ndarray,
    auxiliary_matrix: np.ndarray,
    fixed_indices: list[int],
    physical_names: list[str],
) -> list[dict[str, Any]]:
    partition_root = root / "partitions"
    partition_root.mkdir(parents=True, exist_ok=False)
    days = keys // 4_000_000
    records: list[dict[str, Any]] = []
    for year in range(2019, 2026):
        start_day = np.datetime64(f"{year}-01-01", "D").astype(np.int64)
        stop_day = np.datetime64(f"{year + 1}-01-01", "D").astype(np.int64)
        start = int(np.searchsorted(days, start_day, side="left"))
        stop = int(np.searchsorted(days, stop_day, side="left"))
        year_keys = np.asarray(keys[start:stop], dtype=np.int64)
        year_matrix = np.column_stack(
            [
                np.asarray(logical_matrix[start:stop, fixed_indices], dtype=np.float64),
                np.asarray(auxiliary_matrix[start:stop, :], dtype=np.float64),
            ]
        )
        arrays: list[pa.Array] = [pa.array(year_keys, type=pa.int64())]
        arrays.extend(
            pa.array(year_matrix[:, index], type=pa.float64(), from_pandas=False)
            for index in range(len(physical_names))
        )
        table = pa.Table.from_arrays(
            arrays, names=["stock_day_key", *physical_names]
        )
        path = partition_root / f"{year}.parquet"
        pq.write_table(
            table,
            path,
            compression="zstd",
            use_dictionary=False,
            write_statistics=True,
            row_group_size=65_536,
            data_page_version="2.0",
        )
        records.append(
            {
                "year": year,
                "path": f"partitions/{year}.parquet",
                "rows": len(year_keys),
                "sha256": _sha256(path),
                "frame_sha256": v1.partition_frame_sha256(
                    year_keys, year_matrix, physical_names
                ),
            }
        )
        del table, arrays, year_keys, year_matrix
        gc.collect()
    if sum(int(item["rows"]) for item in records) != v1.EXPECTED_ROWS:
        raise CompactComparatorCacheV4Error("v4 partition rows changed")
    return records


def _logical_values_from_physical(
    *,
    candidate_keys: np.ndarray,
    candidate_positions: np.ndarray,
    physical_matrix: np.ndarray,
    layout: dict[str, Any],
) -> dict[str, np.ndarray]:
    physical_index = {
        name: index for index, name in enumerate(layout["physical_names"])
    }
    values = {
        name: np.asarray(
            physical_matrix[candidate_positions, physical_index[name]],
            dtype=np.float64,
        )
        for name in layout["fixed_names"]
    }
    raw = {
        name: np.asarray(
            physical_matrix[candidate_positions, physical_index[name]],
            dtype=np.float64,
        )
        for name in AUXILIARY_COLUMNS
    }
    values.update(
        reconstruct_dynamic_quality_values(
            candidate_keys=candidate_keys,
            raw_auxiliary_values=raw,
        )
    )
    if set(values) != set(layout["logical_names"]):
        raise CompactComparatorCacheV4Error("v4 logical reconstruction changed")
    return values


def _actual_equivalence(
    *,
    keys: np.ndarray,
    physical_matrix: np.ndarray,
    layout: dict[str, Any],
    completed: dict[str, Any],
) -> dict[str, Any]:
    prior, foundation, engine, _, _, comparison_engine = (
        v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    )
    v1.audit._install_frozen_candidate_range(engine)
    eligible = foundation.quality_listing_eligible_keys(prior.load_protocol())
    manifest = json.loads(v1.audit.SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))
    candidate_frame = engine.load_factor_frame(
        v1.audit.SNAPSHOT_MANIFEST_PATH, manifest, v1.FACTOR_NAME
    )
    quality_frame, coverage = engine.coverage_and_capacity(
        candidate_frame,
        eligible,
        v1.audit.load_protocol(),
        v1.FACTOR_NAME,
    )
    del candidate_frame, eligible
    if coverage != completed["coverage_and_capacity"][v1.FACTOR_NAME]:
        raise CompactComparatorCacheV4Error(
            "Campaign067 candidate coverage changed during v4 equivalence"
        )
    candidate_keys, candidate_values = engine._sorted_candidate_arrays(
        quality_frame, v1.FACTOR_NAME
    )
    del quality_frame
    positions = np.searchsorted(keys, candidate_keys, side="left")
    if not (
        np.all(positions < len(keys))
        and np.array_equal(keys[positions], candidate_keys)
    ):
        raise CompactComparatorCacheV4Error(
            "v4 cache does not cover Campaign067 candidate keys"
        )
    logical_values = _logical_values_from_physical(
        candidate_keys=candidate_keys,
        candidate_positions=positions,
        physical_matrix=physical_matrix,
        layout=layout,
    )
    gate = v1.audit.load_protocol()["ordered_no_return_gates"][
        "uniqueness_after_coverage_only"
    ]
    observed: list[dict[str, Any]] = []
    for definition in layout["definitions"][:-1]:
        name = str(definition["name"])
        observed.append(
            comparison_engine._aligned_comparison_result(
                candidate_keys=candidate_keys,
                candidate_values=candidate_values,
                comparison_values=logical_values[name],
                comparison=name,
                direction=str(definition["score_direction"]),
                gate=gate,
            )
        )
    expected = completed["uniqueness"][v1.FACTOR_NAME]["comparisons"]
    if observed != expected:
        mismatches = [
            index
            for index, (left, right) in enumerate(zip(observed, expected, strict=True))
            if left != right
        ]
        raise CompactComparatorCacheV4Error(
            f"v4 semantic equivalence failed at comparisons {mismatches[:5]}"
        )
    candidate_name = layout["logical_names"][-1]
    receipt = {
        "candidate_factor": v1.FACTOR_NAME,
        "candidate_coverage_exactly_equal_to_completed_audit": True,
        "comparison_count": len(observed),
        "all_comparison_result_objects_exactly_equal": True,
        "comparison_results_sha256": _json_sha256(observed),
        "bound_completed_audit_sha256": v1.COMPLETED_AUDIT_SHA256,
        "dynamic_recipe_comparators": list(DYNAMIC_COMPARATORS),
        "dynamic_candidate_value_sha256": {
            name: v1.canonical_column_sha256(logical_values[name])
            for name in DYNAMIC_COMPARATORS
        },
        "campaign067_cache_column_sha256": v1.canonical_column_sha256(
            logical_values[candidate_name]
        ),
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }
    del logical_values, candidate_keys, candidate_values
    gc.collect()
    return receipt


def _physical_column_records(
    physical_matrix: np.ndarray, layout: dict[str, Any]
) -> list[dict[str, Any]]:
    directions = {
        str(item["name"]): str(item["score_direction"])
        for item in layout["definitions"]
    }
    records = []
    for index, name in enumerate(layout["physical_names"]):
        values = np.asarray(physical_matrix[:, index], dtype=np.float64)
        records.append(
            {
                "name": name,
                "role": (
                    "fixed_materialized_comparator"
                    if name in directions
                    else "raw_dynamic_recipe_auxiliary"
                ),
                "score_direction": directions.get(name),
                "finite_rows": int(np.isfinite(values).sum()),
                "nonfinite_rows": int((~np.isfinite(values)).sum()),
                "canonical_value_sha256": v1.canonical_column_sha256(values),
            }
        )
    return records


def _dataset_material(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocol_sha256": PROTOCOL_SHA256,
        "implementation_freeze_sha256": manifest["implementation_freeze"]["sha256"],
        "builder_sha256": manifest["builder"]["sha256"],
        "eligibility_keys_sha256": v1.EXPECTED_KEYS_SHA256,
        "logical_numeric_order_sha256": v1.EXPECTED_NUMERIC_ORDER_SHA256,
        "physical_name_list_json_sha256": EXPECTED_PHYSICAL_NAME_LIST_SHA256,
        "dynamic_recipes": manifest["dynamic_recipes"],
        "physical_columns": manifest["physical_columns"],
        "files": manifest["files"],
        "source_snapshot_verifications_sha256": manifest[
            "source_snapshot_verifications_sha256"
        ],
        "campaign067_snapshot_file_verification_sha256": manifest[
            "campaign067_snapshot_file_verification_sha256"
        ],
        "quality_auxiliary_receipt_sha256": manifest[
            "quality_auxiliary_receipt_sha256"
        ],
        "source_key_alignment_receipts_sha256": manifest[
            "source_key_alignment_receipts_sha256"
        ],
        "semantic_equivalence_sha256": _json_sha256(
            manifest["semantic_equivalence"]
        ),
    }


def _manifest(
    *,
    keys: np.ndarray,
    physical_matrix: np.ndarray,
    layout: dict[str, Any],
    files: list[dict[str, Any]],
    receipts: dict[str, Any],
    candidate_receipt: dict[str, Any],
    quality_auxiliary_receipt: dict[str, Any],
    alignment_receipts: list[dict[str, Any]],
    equivalence: dict[str, Any],
    freeze_sha256: str,
) -> dict[str, Any]:
    manifest = {
        "schema_version": 4,
        "kind": "a_share_three_day_candidate_independent_compact_comparator_cache_v4",
        "status": "complete_verified_semantically_equivalent_no_return_cache",
        "created_at": _utc_now(),
        "protocol": {
            "path": str(PROTOCOL_PATH.resolve()),
            "sha256": PROTOCOL_SHA256,
        },
        "authoritative_protocol_chain": [
            {"path": str(v1.PROTOCOL_PATH.resolve()), "sha256": v1.PROTOCOL_SHA256},
            {"path": str(v2.PROTOCOL_PATH.resolve()), "sha256": v2.PROTOCOL_SHA256},
            {"path": str(v3.PROTOCOL_PATH.resolve()), "sha256": v3.PROTOCOL_SHA256},
        ],
        "recorded_v3_failure": {
            "path": str(V3_FAILURE_PATH.resolve()),
            "sha256": V3_FAILURE_SHA256,
        },
        "bound_v3_diagnosis": {
            "path": str(V3_DIAGNOSIS_PATH.resolve()),
            "sha256": V3_DIAGNOSIS_SHA256,
        },
        "implementation_freeze": {
            "path": str(IMPLEMENTATION_FREEZE_PATH.resolve()),
            "sha256": freeze_sha256,
        },
        "builder": {
            "path": str(Path(__file__).resolve()),
            "sha256": _sha256(Path(__file__).resolve()),
        },
        "eligibility": {
            "rows": len(keys),
            "calendar_sessions": int(len(np.unique(keys // 4_000_000))),
            "sorted_little_endian_int64_sha256": hashlib.sha256(
                keys.astype("<i8", copy=False).tobytes()
            ).hexdigest(),
        },
        "logical_numeric_comparator_count": len(layout["logical_names"]),
        "logical_numeric_comparator_order_sha256": v1.EXPECTED_NUMERIC_ORDER_SHA256,
        "logical_name_list_json_sha256": _json_sha256(layout["logical_names"]),
        "fixed_materialized_comparator_count": len(layout["fixed_names"]),
        "fixed_materialized_name_list_json_sha256": _json_sha256(
            layout["fixed_names"]
        ),
        "dynamic_recipe_comparator_count": len(DYNAMIC_COMPARATORS),
        "physical_float64_column_count": len(layout["physical_names"]),
        "physical_name_list_json_sha256": _json_sha256(layout["physical_names"]),
        "dynamic_recipes": {
            "quality_growth": {
                "raw_auxiliaries": [
                    "quality_raw_profit_yoy",
                    "quality_raw_revenue_yoy",
                ],
                "candidate_intersection_precedes_session_rank": True,
                "rank_method": "average",
                "rank_pct": True,
                "mean_skipna": False,
            },
            "quality_score": {
                "raw_auxiliaries": list(AUXILIARY_COLUMNS),
                "candidate_intersection_precedes_session_rank": True,
                "rank_method": "average",
                "rank_pct": True,
                "mean_skipna": False,
            },
        },
        "physical_columns": _physical_column_records(physical_matrix, layout),
        "files": files,
        "source_snapshot_verifications": receipts,
        "source_snapshot_verifications_sha256": _json_sha256(receipts),
        "campaign067_snapshot_file_verification": candidate_receipt,
        "campaign067_snapshot_file_verification_sha256": _json_sha256(
            candidate_receipt
        ),
        "quality_auxiliary_receipt": quality_auxiliary_receipt,
        "quality_auxiliary_receipt_sha256": _json_sha256(
            quality_auxiliary_receipt
        ),
        "source_key_alignment_receipts": alignment_receipts,
        "source_key_alignment_receipts_sha256": _json_sha256(alignment_receipts),
        "semantic_equivalence": equivalence,
        "failed_v1_v2_or_v3_temporary_values_reused": False,
        "global_materialized_dynamic_quality_values_stored": False,
        "historical_daily_price_fields_read": [],
        "historical_forward_returns_read": False,
        "candidate49_history_signal_or_execution_backfilled": False,
        "provider_request_issued": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }
    manifest["dataset_sha256"] = _json_sha256(_dataset_material(manifest))
    return manifest


def build_cache(
    *, data_root: Path, output_root: Path, workers: int, confirm_build: bool
) -> Path:
    if not confirm_build:
        raise CompactComparatorCacheV4Error("v4 build requires --confirm-build")
    load_protocol()
    _load_implementation_freeze()
    data_root = data_root.expanduser().resolve()
    output_root = output_root.expanduser().resolve()
    if data_root != DEFAULT_DATA_ROOT.resolve():
        raise CompactComparatorCacheV4Error("compact-cache v4 data root changed")
    if output_root != DEFAULT_OUTPUT_ROOT.resolve():
        raise CompactComparatorCacheV4Error("compact-cache v4 output root changed")
    if output_root.exists():
        raise CompactComparatorCacheV4Error("compact-cache v4 output already exists")
    if any(path.exists() for path in FAILED_FORMAL_OUTPUT_ROOTS):
        raise CompactComparatorCacheV4Error(
            "a failed v1/v2/v3 formal root was published"
        )
    layout = _library_layout()
    keys = v1.eligible_keys()
    output_root.parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(
        tempfile.mkdtemp(prefix=f".{output_root.name}.", dir=output_root.parent)
    )
    logical_working_path = temporary_root / "working_logical_matrix.npy"
    auxiliary_working_path = temporary_root / "working_quality_auxiliary_matrix.npy"
    logical_matrix = np.lib.format.open_memmap(
        logical_working_path,
        mode="w+",
        dtype=np.float64,
        shape=(len(keys), len(layout["logical_names"])),
    )
    alignment_receipts: list[dict[str, Any]] = []
    engine, previous_loader = v2._install_global_alignment_loader(
        keys=keys,
        alignment_receipts=alignment_receipts,
    )
    try:
        receipts, candidate_receipt, completed = v3._capture_matrix(
            data_root=data_root,
            workers=workers,
            keys=keys,
            matrix=logical_matrix,
            definitions=layout["definitions"],
        )
    finally:
        engine._load_filtered_comparison_values_explicit = previous_loader
    _, _, _, _, _, comparison_engine = (
        v1.audit.c66_audit.c62_audit.c61_audit.prior_audit.terminal.campaign044._context()
    )
    auxiliary_values, quality_auxiliary_receipt = _quality_auxiliary_values(
        keys=keys, comparison_engine=comparison_engine
    )
    auxiliary_matrix = np.lib.format.open_memmap(
        auxiliary_working_path,
        mode="w+",
        dtype=np.float64,
        shape=auxiliary_values.shape,
    )
    auxiliary_matrix[:, :] = auxiliary_values
    auxiliary_matrix.flush()
    del auxiliary_values
    gc.collect()
    files = _write_partitions(
        root=temporary_root,
        keys=keys,
        logical_matrix=logical_matrix,
        auxiliary_matrix=auxiliary_matrix,
        fixed_indices=layout["fixed_indices"],
        physical_names=layout["physical_names"],
    )
    loaded_keys, physical_matrix = v1._load_cache_matrix(
        root=temporary_root,
        records=files,
        names=layout["physical_names"],
    )
    if not np.array_equal(loaded_keys, keys):
        raise CompactComparatorCacheV4Error("v4 Parquet key round trip changed")
    for physical_index, logical_index in enumerate(layout["fixed_indices"]):
        name = layout["logical_names"][logical_index]
        if v1.canonical_column_sha256(
            physical_matrix[:, physical_index]
        ) != v1.canonical_column_sha256(logical_matrix[:, logical_index]):
            raise CompactComparatorCacheV4Error(
                f"v4 fixed Parquet value round trip changed for {name}"
            )
    auxiliary_offset = len(layout["fixed_names"])
    for index, name in enumerate(AUXILIARY_COLUMNS):
        if v1.canonical_column_sha256(
            physical_matrix[:, auxiliary_offset + index]
        ) != v1.canonical_column_sha256(auxiliary_matrix[:, index]):
            raise CompactComparatorCacheV4Error(
                f"v4 auxiliary Parquet value round trip changed for {name}"
            )
    equivalence = _actual_equivalence(
        keys=loaded_keys,
        physical_matrix=physical_matrix,
        layout=layout,
        completed=completed,
    )
    freeze_sha256 = _sha256(IMPLEMENTATION_FREEZE_PATH)
    manifest = _manifest(
        keys=loaded_keys,
        physical_matrix=physical_matrix,
        layout=layout,
        files=files,
        receipts=receipts,
        candidate_receipt=candidate_receipt,
        quality_auxiliary_receipt=quality_auxiliary_receipt,
        alignment_receipts=alignment_receipts,
        equivalence=equivalence,
        freeze_sha256=freeze_sha256,
    )
    manifest_path = temporary_root / "snapshot_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    del physical_matrix, loaded_keys, logical_matrix, auxiliary_matrix
    gc.collect()
    logical_working_path.unlink()
    auxiliary_working_path.unlink()
    os.replace(temporary_root, output_root)
    return output_root / "snapshot_manifest.json"


def _validate_manifest(manifest: dict[str, Any], layout: dict[str, Any]) -> None:
    alignments = manifest.get("source_key_alignment_receipts") or []
    if not (
        manifest.get("schema_version") == 4
        and manifest.get("kind")
        == "a_share_three_day_candidate_independent_compact_comparator_cache_v4"
        and manifest.get("status")
        == "complete_verified_semantically_equivalent_no_return_cache"
        and (manifest.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (manifest.get("recorded_v3_failure") or {}).get("sha256")
        == V3_FAILURE_SHA256
        and (manifest.get("bound_v3_diagnosis") or {}).get("sha256")
        == V3_DIAGNOSIS_SHA256
        and (manifest.get("builder") or {}).get("sha256")
        == _sha256(Path(__file__).resolve())
        and manifest.get("logical_numeric_comparator_count") == 98
        and manifest.get("logical_numeric_comparator_order_sha256")
        == v1.EXPECTED_NUMERIC_ORDER_SHA256
        and manifest.get("fixed_materialized_comparator_count") == 96
        and manifest.get("dynamic_recipe_comparator_count") == 2
        and manifest.get("physical_float64_column_count") == 99
        and manifest.get("physical_name_list_json_sha256")
        == EXPECTED_PHYSICAL_NAME_LIST_SHA256
        and list((manifest.get("dynamic_recipes") or {}).keys())
        == list(DYNAMIC_COMPARATORS)
        and manifest.get("failed_v1_v2_or_v3_temporary_values_reused") is False
        and manifest.get("global_materialized_dynamic_quality_values_stored") is False
        and manifest.get("historical_daily_price_fields_read") == []
        and manifest.get("historical_forward_returns_read") is False
        and manifest.get("provider_request_issued") is False
        and alignments
        and manifest.get("source_key_alignment_receipts_sha256")
        == _json_sha256(alignments)
        and all(
            item.get("requested_global_keys") == v1.EXPECTED_ROWS
            and item.get("matched_global_keys", -1) >= 0
            and item.get("absent_global_keys", -1) >= 0
            and item.get("matched_global_keys") + item.get("absent_global_keys")
            == v1.EXPECTED_ROWS
            for item in alignments
        )
        and [item.get("name") for item in manifest.get("physical_columns") or []]
        == layout["physical_names"]
        and manifest.get("dataset_sha256")
        == _json_sha256(_dataset_material(manifest))
    ):
        raise CompactComparatorCacheV4Error("compact-cache v4 manifest changed")


def verify_cache(
    manifest_path: Path = DEFAULT_OUTPUT_ROOT / "snapshot_manifest.json",
    *,
    full_equivalence: bool = False,
) -> dict[str, Any]:
    load_protocol()
    _load_implementation_freeze()
    manifest_path = manifest_path.expanduser().resolve()
    if manifest_path != (DEFAULT_OUTPUT_ROOT / "snapshot_manifest.json").resolve():
        raise CompactComparatorCacheV4Error("compact-cache v4 manifest path changed")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    layout = _library_layout()
    _validate_manifest(manifest, layout)
    completed = v1._completed_audit()
    expected_receipts = completed["uniqueness"][v1.FACTOR_NAME][
        "source_snapshot_verifications"
    ]
    if not (
        manifest.get("source_snapshot_verifications") == expected_receipts
        and manifest.get("source_snapshot_verifications_sha256")
        == _json_sha256(expected_receipts)
        and manifest.get("campaign067_snapshot_file_verification")
        == completed["snapshot_file_verification"]
    ):
        raise CompactComparatorCacheV4Error("compact-cache v4 source receipts changed")
    keys, physical_matrix = v1._load_cache_matrix(
        root=manifest_path.parent,
        records=list(manifest["files"]),
        names=layout["physical_names"],
    )
    if hashlib.sha256(keys.astype("<i8", copy=False).tobytes()).hexdigest() != (
        v1.EXPECTED_KEYS_SHA256
    ):
        raise CompactComparatorCacheV4Error("compact-cache v4 keys changed")
    for index, record in enumerate(manifest["physical_columns"]):
        values = physical_matrix[:, index]
        if not (
            record.get("name") == layout["physical_names"][index]
            and record.get("finite_rows") == int(np.isfinite(values).sum())
            and record.get("nonfinite_rows") == int((~np.isfinite(values)).sum())
            and record.get("canonical_value_sha256")
            == v1.canonical_column_sha256(values)
        ):
            raise CompactComparatorCacheV4Error(
                f"compact-cache v4 column changed at {record.get('name')}"
            )
    if full_equivalence:
        recomputed = _actual_equivalence(
            keys=keys,
            physical_matrix=physical_matrix,
            layout=layout,
            completed=completed,
        )
        if recomputed != manifest["semantic_equivalence"]:
            raise CompactComparatorCacheV4Error(
                "compact-cache v4 full semantic equivalence changed"
            )
    result = {
        "status": "verified",
        "manifest_path": str(manifest_path),
        "manifest_sha256": _sha256(manifest_path),
        "dataset_sha256": manifest["dataset_sha256"],
        "rows": len(keys),
        "logical_numeric_comparator_count": 98,
        "fixed_materialized_comparator_count": 96,
        "dynamic_recipe_comparator_count": 2,
        "physical_float64_column_count": 99,
        "alignment_receipt_count": len(
            manifest["source_key_alignment_receipts"]
        ),
        "full_equivalence_recomputed": bool(full_equivalence),
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }
    del physical_matrix, keys
    gc.collect()
    return result


def status() -> dict[str, Any]:
    load_protocol()
    manifest = DEFAULT_OUTPUT_ROOT / "snapshot_manifest.json"
    return {
        "protocol_sha256": PROTOCOL_SHA256,
        "implementation_freeze_exists": IMPLEMENTATION_FREEZE_PATH.is_file(),
        "failed_formal_outputs_exist": any(
            path.exists() for path in FAILED_FORMAL_OUTPUT_ROOTS
        ),
        "v4_output_exists": DEFAULT_OUTPUT_ROOT.exists(),
        "v4_manifest_exists": manifest.is_file(),
        "comparison_or_raw_auxiliary_values_read_by_status": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    build = sub.add_parser("build")
    build.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    build.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    build.add_argument("--workers", type=int, default=4)
    build.add_argument("--confirm-build", action="store_true")
    verify = sub.add_parser("verify")
    verify.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT / "snapshot_manifest.json",
    )
    verify.add_argument("--full-equivalence", action="store_true")
    args = parser.parse_args()
    if args.command == "status":
        payload = status()
    elif args.command == "build":
        payload = {
            "manifest": str(
                build_cache(
                    data_root=args.data_root,
                    output_root=args.output_root,
                    workers=args.workers,
                    confirm_build=args.confirm_build,
                )
            )
        }
    else:
        payload = verify_cache(
            args.manifest,
            full_equivalence=args.full_equivalence,
        )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
