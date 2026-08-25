#!/usr/bin/env python3
"""Build Campaign286's frozen 2019-2023 Alpha158 development design."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from qlib.contrib.data.loader import Alpha158DL
from scripts import a_share_short_horizon_factor_research as research


REPO_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_286_preregistration_20260825.json"
)
PROTOCOL_SHA256 = "62bc6eccb6d1240f5f08ce895c05fca4ca2231cf9deca7fda0cf7f1af6ca91af"
CONCEPT_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_286_concept_scouting_20260825.json"
)
CONCEPT_SHA256 = "5214937fdb377d8887179131083428d1f862fd40d87d6a7ea2e9b1a0544dda78"
POLICY_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_historical_walkforward_research_policy_20260727.json"
)
POLICY_SHA256 = "38426d6161b9bfed323c58caba18feca668b8c9d53e294951a8ba90c01a798bb"
LOADER_PATH = REPO_ROOT / "qlib/contrib/data/loader.py"
LOADER_SHA256 = "814b7f7ab3d418ae3c87ce352220080b239eba2670eac9e38376b794be4075cb"
HANDLER_PATH = REPO_ROOT / "qlib/contrib/data/handler.py"
HANDLER_SHA256 = "b621481c6009c39066c67c71390fd2bea635f56daf9f2c4e38817eff268e3232"
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign286_design.py"
)
IMPLEMENTATION_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_286_design_implementation_freeze_20260825.json"
)
PROVIDER_URI = REPO_ROOT / "data/qlib/cn_a_share"
QUALITY_PATH = REPO_ROOT / "data/raw/a_share/fundamentals/quarterly_quality.parquet"
QUALITY_SHA256 = "3ac901a97928d2ed81ac72e3eaac9bdc148d36cf67b6abe70223699235ef059f"
QUALITY_MANIFEST_PATH = REPO_ROOT / "data/metadata/quarterly_quality_manifest.json"
QUALITY_MANIFEST_SHA256 = (
    "e3cf654babe37a82393c5530696bc1cc242b736cb88e1947b8444b638125ba8c"
)
PRICE_BASIS_PATH = PROVIDER_URI / "price_basis.json"
PRICE_BASIS_SHA256 = "68e9dbb83749779b34d5cf3b116195074c154ff74cb6de95ba67695bedc1f14f"
CALENDAR_PATH = PROVIDER_URI / "calendars/day.txt"
CALENDAR_SHA256 = "fda506597d26bcec953cdc0882042a5046ec1587db60490e16a01627fd43f53a"
UNIVERSE_PATH = PROVIDER_URI / "instruments/buyable_main_chinext.txt"
UNIVERSE_SHA256 = "77ccf8de2ed1e447e73b5d5ff1703fc2a8656d6adab34ef44017481730249db1"
OUTPUT_ROOT = (
    REPO_ROOT / "data/experiments/short_horizon/historical_walkforward/campaign_286/"
    "alpha158_development_design_v1"
)

FEATURE_COUNT = 158
FEATURE_LIBRARY_SHA256 = (
    "b1154a5b310ec5f8ead6ca064c06ae4a1121dc1c9a0d4ff7dcd00efcf20704e5"
)
MINIMUM_FINITE_FEATURES = 119
DEVELOPMENT_YEARS = tuple(range(2019, 2024))
QUALITY_MAX_AGE_DAYS = 550
MINIMUM_LISTING_SESSIONS = 20
COVERAGE_THRESHOLDS = {
    "median_daily_feature_row_coverage_minimum": 0.95,
    "p05_daily_feature_row_coverage_minimum": 0.90,
    "p05_eligible_names_minimum": 50.0,
    "non_overlapping_three_session_cohorts_minimum": 200,
    "cohort_years_minimum": 5,
}


class Campaign286DesignError(RuntimeError):
    """Fail closed when a frozen Campaign286 design invariant changes."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def value_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Campaign286DesignError(f"JSON object required: {path}")
    return value


def require_file(path: Path, expected: str, label: str) -> None:
    if len(expected) != 64 or not path.is_file() or file_sha256(path) != expected:
        raise Campaign286DesignError(f"{label} changed: {path}")


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                payload,
                handle,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def atomic_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(name)
    try:
        table = pa.Table.from_pandas(frame, preserve_index=False)
        pq.write_table(
            table,
            temporary,
            compression="zstd",
            use_dictionary=False,
            row_group_size=65_536,
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def feature_config() -> tuple[list[str], list[str]]:
    expressions, names = Alpha158DL.get_feature_config()
    pairs = list(zip(names, expressions, strict=True))
    if not (
        len(expressions) == len(names) == FEATURE_COUNT
        and len(set(expressions)) == len(set(names)) == FEATURE_COUNT
        and value_sha256(pairs) == FEATURE_LIBRARY_SHA256
    ):
        raise Campaign286DesignError("Alpha158 complete feature library changed")
    return list(expressions), list(names)


def validate_protocol() -> dict[str, Any]:
    bindings = (
        (PROTOCOL_PATH, PROTOCOL_SHA256, "Campaign286 protocol"),
        (CONCEPT_PATH, CONCEPT_SHA256, "Campaign286 concept catalog"),
        (POLICY_PATH, POLICY_SHA256, "historical research policy"),
        (LOADER_PATH, LOADER_SHA256, "Alpha158 loader"),
        (HANDLER_PATH, HANDLER_SHA256, "Alpha158 handler"),
        (QUALITY_PATH, QUALITY_SHA256, "quarterly quality snapshot"),
        (
            QUALITY_MANIFEST_PATH,
            QUALITY_MANIFEST_SHA256,
            "quarterly quality manifest",
        ),
        (PRICE_BASIS_PATH, PRICE_BASIS_SHA256, "price-basis manifest"),
        (CALENDAR_PATH, CALENDAR_SHA256, "provider calendar"),
        (UNIVERSE_PATH, UNIVERSE_SHA256, "buyable universe"),
    )
    for path, expected, label in bindings:
        require_file(path, expected, label)
    protocol = load_json(PROTOCOL_PATH)
    library = protocol.get("complete_feature_library") or {}
    support = library.get("design_support") or {}
    universe = protocol.get("research_universe") or {}
    coverage = protocol.get("coverage_gate_before_labels") or {}
    if not (
        protocol.get("kind")
        == "a_share_three_day_walkforward_campaign286_preregistration"
        and protocol.get("status")
        == "complete_campaign_frozen_before_alpha158_feature_or_label_values"
        and library.get("feature_count") == FEATURE_COUNT
        and library.get("canonical_name_expression_pairs_sha256")
        == FEATURE_LIBRARY_SHA256
        and library.get("all_features_required") is True
        and support.get("minimum_finite_features") == MINIMUM_FINITE_FEATURES
        and support.get("neutral_fill") is False
        and universe.get("minimum_listing_sessions") == MINIMUM_LISTING_SESSIONS
        and coverage.get("development_years") == list(DEVELOPMENT_YEARS)
        and all(
            coverage.get(name) == value for name, value in COVERAGE_THRESHOLDS.items()
        )
    ):
        raise Campaign286DesignError("Campaign286 protocol semantics changed")
    feature_config()
    return protocol


def validate_implementation_freeze() -> dict[str, Any]:
    if not IMPLEMENTATION_FREEZE_PATH.is_file():
        raise Campaign286DesignError("Campaign286 design implementation freeze absent")
    record = load_json(IMPLEMENTATION_FREEZE_PATH)
    runner = record.get("design_runner") or {}
    tests = record.get("tests") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign286_design_implementation_freeze"
        and record.get("status")
        == "frozen_before_first_alpha158_feature_or_label_value_read"
        and (record.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and runner.get("path") == str(Path(__file__).resolve().relative_to(REPO_ROOT))
        and runner.get("sha256") == file_sha256(Path(__file__).resolve())
        and tests.get("path") == str(TEST_PATH.relative_to(REPO_ROOT))
        and tests.get("sha256") == file_sha256(TEST_PATH)
        and boundary.get("alpha158_feature_values_read_before_freeze") is False
        and boundary.get("historical_label_or_forward_return_values_read_before_freeze")
        is False
        and boundary.get("provider_request_issued_before_freeze") is False
        and boundary.get("candidate49_ledgers_changed_before_freeze") is False
    ):
        raise Campaign286DesignError("Campaign286 design implementation freeze changed")
    return record


def support_state(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(matrix)
    if values.ndim != 2 or values.shape[1] != FEATURE_COUNT:
        raise Campaign286DesignError("Alpha158 design matrix shape changed")
    finite_count = np.isfinite(values).sum(axis=1).astype(np.uint8)
    eligible = finite_count >= MINIMUM_FINITE_FEATURES
    return finite_count, eligible


def compact_stock_day_keys(
    trade_dates: pd.Series, instruments: pd.Series
) -> np.ndarray:
    """Encode the unchanged date/exchange/security identity without legacy imports."""

    dates = pd.to_datetime(trade_dates, errors="coerce").dt.normalize()
    text = instruments.astype("string").str.upper()
    exchange = text.str.slice(0, 2).map({"SH": 1, "SZ": 2, "BJ": 3})
    codes = pd.to_numeric(text.str.slice(2), errors="coerce")
    if dates.isna().any() or exchange.isna().any() or codes.isna().any():
        raise Campaign286DesignError("stock-day identity cannot be compacted")
    days = dates.to_numpy(dtype="datetime64[D]").astype(np.int64, copy=False)
    security = exchange.to_numpy(dtype=np.int64) * 1_000_000 + codes.to_numpy(
        dtype=np.int64
    )
    return days * 4_000_000 + security


def coverage_summary(daily: pd.DataFrame) -> dict[str, Any]:
    required = {"session", "quality_listing_names", "eligible_names"}
    if set(daily) != required:
        raise Campaign286DesignError("daily coverage columns changed")
    ordered = daily.sort_values("session", kind="stable").reset_index(drop=True)
    if (
        len(ordered) == 0
        or ordered["session"].duplicated().any()
        or (ordered[["quality_listing_names", "eligible_names"]] < 0).any().any()
        or (ordered["eligible_names"] > ordered["quality_listing_names"]).any()
        or (ordered["quality_listing_names"] == 0).any()
    ):
        raise Campaign286DesignError("daily coverage identity changed")
    ratios = ordered["eligible_names"] / ordered["quality_listing_names"]
    indices = np.arange(0, max(len(ordered) - 3, 0), 3)
    potential_mask = ordered.iloc[indices]["eligible_names"].ge(50)
    potential = int(potential_mask.sum())
    cohort_dates = pd.to_datetime(
        ordered.iloc[indices].loc[potential_mask, "session"], errors="raise"
    )
    years = sorted(int(value) for value in cohort_dates.dt.year.unique())
    median = float(ratios.median())
    p05 = float(ratios.quantile(0.05))
    p05_names = float(ordered["eligible_names"].quantile(0.05))
    passed = bool(
        median >= COVERAGE_THRESHOLDS["median_daily_feature_row_coverage_minimum"]
        and p05 >= COVERAGE_THRESHOLDS["p05_daily_feature_row_coverage_minimum"]
        and p05_names >= COVERAGE_THRESHOLDS["p05_eligible_names_minimum"]
        and potential
        >= COVERAGE_THRESHOLDS["non_overlapping_three_session_cohorts_minimum"]
        and len(years) >= COVERAGE_THRESHOLDS["cohort_years_minimum"]
    )
    return {
        "quality_listing_rows": int(ordered["quality_listing_names"].sum()),
        "model_support_eligible_rows": int(ordered["eligible_names"].sum()),
        "calendar_sessions": len(ordered),
        "median_daily_feature_row_coverage": median,
        "p05_daily_feature_row_coverage": p05,
        "eligible_names_minimum": int(ordered["eligible_names"].min()),
        "eligible_names_p05": p05_names,
        "eligible_names_median": float(ordered["eligible_names"].median()),
        "potential_non_overlapping_three_session_cohorts": potential,
        "observed_cohort_years": years,
        "daily_coverage_frame_sha256": hashlib.sha256(
            ordered.to_csv(index=False, lineterminator="\n").encode("utf-8")
        ).hexdigest(),
        "thresholds": COVERAGE_THRESHOLDS,
        "gate_passed_before_historical_label_or_forward_return_read": passed,
    }


def _load_year_features(
    year: int,
    *,
    instruments: list[str],
    expressions: list[str],
    names: list[str],
    batch_size: int,
) -> pd.DataFrame:
    from qlib.data import D

    pieces: list[pd.DataFrame] = []
    for offset in range(0, len(instruments), batch_size):
        batch = instruments[offset : offset + batch_size]
        frame = D.features(
            batch,
            expressions,
            start_time=f"{year}-01-01",
            end_time=f"{year}-12-31",
            freq="day",
        ).rename(columns=dict(zip(expressions, names, strict=True)))
        pieces.append(frame.reset_index())
        print(
            f"Campaign286 Alpha158 {year}: loaded "
            f"{min(offset + len(batch), len(instruments))}/{len(instruments)} instruments",
            flush=True,
        )
    result = pd.concat(pieces, ignore_index=True)
    result["datetime"] = pd.to_datetime(result["datetime"]).dt.normalize()
    result["instrument"] = result["instrument"].astype(str)
    if result.duplicated(["datetime", "instrument"]).any():
        raise Campaign286DesignError(f"Alpha158 identities duplicate in {year}")
    matrix = result[names].to_numpy(dtype=np.float64, copy=True)
    matrix[~np.isfinite(matrix)] = np.nan
    result[names] = matrix.astype(np.float32)
    return result.sort_values(["datetime", "instrument"], kind="stable").reset_index(
        drop=True
    )


def build_design(*, batch_size: int = 128, output_root: Path = OUTPUT_ROOT) -> Path:
    plan_payload = plan(output_root=output_root)
    if plan_payload["ready"] is not True:
        raise Campaign286DesignError("Campaign286 design output already exists")
    if batch_size < 1:
        raise Campaign286DesignError("batch size must be positive")
    validate_protocol()
    validate_implementation_freeze()

    import qlib
    from qlib.data import D

    research.require_research_price_basis(PROVIDER_URI)
    qlib.init(provider_uri=str(PROVIDER_URI), region="cn", kernels=1)
    universe = D.instruments(market="buyable_main_chinext")
    listing_spans = D.list_instruments(universe, as_list=False)
    provider_calendar = pd.DatetimeIndex(D.calendar(freq="day")).normalize()
    instruments = D.list_instruments(
        universe, start_time="2019-01-01", end_time="2023-12-31", as_list=True
    )
    if not instruments:
        raise Campaign286DesignError("Campaign286 universe is empty")
    fundamentals = research.load_fundamentals(QUALITY_PATH)
    expressions, names = feature_config()

    output_root = output_root.expanduser().resolve()
    partial = output_root.parent / f".{output_root.name}.partial"
    if partial.exists():
        raise Campaign286DesignError(f"preserve existing partial output: {partial}")
    partial.mkdir(parents=True)
    records: list[dict[str, Any]] = []
    daily_parts: list[pd.DataFrame] = []
    try:
        for year in DEVELOPMENT_YEARS:
            features = _load_year_features(
                year,
                instruments=instruments,
                expressions=expressions,
                names=names,
                batch_size=batch_size,
            )
            identity = research.attach_listing_age_sessions(
                features[["instrument", "datetime"]], listing_spans, provider_calendar
            )
            eligibility = research.attach_quality_asof(
                identity,
                fundamentals,
                max_age_days=QUALITY_MAX_AGE_DAYS,
                availability_calendar=provider_calendar,
            )
            quality = eligibility["quality_eligible"].fillna(False).to_numpy(bool)
            matrix = features[names].to_numpy(dtype=np.float32, copy=False)
            finite_count, feature_support = support_state(matrix)
            model_support = quality & feature_support
            keys = compact_stock_day_keys(features["datetime"], features["instrument"])
            output = features[names].copy()
            output.insert(0, "stock_day_key", keys)
            output["finite_feature_count"] = finite_count
            output["feature_support_eligible"] = feature_support
            output["quality_listing_eligible"] = quality
            output["model_support_eligible"] = model_support
            output = output.sort_values("stock_day_key", kind="stable").reset_index(
                drop=True
            )
            relative = Path("partitions") / f"{year}.parquet"
            path = partial / relative
            atomic_parquet(output, path)
            records.append(
                {
                    "year": year,
                    "path": str(relative),
                    "rows": len(output),
                    "quality_listing_rows": int(quality.sum()),
                    "feature_support_rows": int(feature_support.sum()),
                    "model_support_eligible_rows": int(model_support.sum()),
                    "finite_feature_count_minimum": int(finite_count.min()),
                    "finite_feature_count_maximum": int(finite_count.max()),
                    "sha256": file_sha256(path),
                }
            )
            daily = (
                pd.DataFrame(
                    {
                        "session": features["datetime"],
                        "quality": quality,
                        "eligible": model_support,
                    }
                )
                .groupby("session", sort=True, observed=True)[["quality", "eligible"]]
                .sum()
            )
            daily_parts.append(
                daily.rename(
                    columns={
                        "quality": "quality_listing_names",
                        "eligible": "eligible_names",
                    }
                ).reset_index()
            )
        daily_coverage = pd.concat(daily_parts, ignore_index=True)
        coverage = coverage_summary(daily_coverage)
        audit = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign286_alpha158_structural_audit",
            "status": (
                "passed_ready_for_frozen_model_implementation"
                if coverage[
                    "gate_passed_before_historical_label_or_forward_return_read"
                ]
                else "failed_terminal_before_historical_label_or_forward_return_read"
            ),
            "created_at": datetime.now(UTC).isoformat(),
            "coverage": coverage,
            "alpha158_feature_values_read": True,
            "historical_label_or_forward_return_values_read": False,
            "model_fitting_performed": False,
            "provider_request_issued": False,
            "credential_loaded": False,
            "candidate49_ledgers_changed": False,
        }
        atomic_json(partial / "structural_audit.json", audit)
        digest_rows = [
            [
                item["year"],
                item["rows"],
                item["model_support_eligible_rows"],
                item["sha256"],
            ]
            for item in records
        ]
        manifest = {
            "schema_version": 1,
            "kind": "a_share_three_day_walkforward_campaign286_alpha158_development_design",
            "status": (
                "immutable_design_ready_for_model_implementation"
                if audit["status"] == "passed_ready_for_frozen_model_implementation"
                else "immutable_design_failed_structural_gate"
            ),
            "created_at": datetime.now(UTC).isoformat(),
            "protocol": {"path": str(PROTOCOL_PATH), "sha256": PROTOCOL_SHA256},
            "feature_count": FEATURE_COUNT,
            "feature_names": names,
            "feature_library_sha256": FEATURE_LIBRARY_SHA256,
            "minimum_finite_features": MINIMUM_FINITE_FEATURES,
            "development_years": list(DEVELOPMENT_YEARS),
            "rows": int(sum(item["rows"] for item in records)),
            "model_support_eligible_rows": int(
                sum(item["model_support_eligible_rows"] for item in records)
            ),
            "partitions": len(records),
            "files": records,
            "dataset_sha256": value_sha256(digest_rows),
            "structural_audit": {
                "path": "structural_audit.json",
                "sha256": file_sha256(partial / "structural_audit.json"),
                "gate_passed": coverage[
                    "gate_passed_before_historical_label_or_forward_return_read"
                ],
            },
            "alpha158_feature_values_read": True,
            "historical_label_or_forward_return_values_read": False,
            "model_fitting_performed": False,
            "lockbox_2024_2025_feature_or_return_values_read": False,
            "provider_request_issued": False,
            "credential_loaded": False,
            "candidate49_historical_backfill_performed": False,
            "candidate49_ledgers_changed": False,
            "current_scoring_selection_sizing_or_orders_performed": False,
        }
        atomic_json(partial / "snapshot_manifest.json", manifest)
        os.replace(partial, output_root)
        return output_root / "snapshot_manifest.json"
    except BaseException as error:
        atomic_json(
            partial / "build_failure.json",
            {
                "schema_version": 1,
                "kind": "a_share_three_day_walkforward_campaign286_design_failure",
                "status": "failed_partial_preserved",
                "created_at": datetime.now(UTC).isoformat(),
                "error_type": type(error).__name__,
                "error": str(error),
                "historical_label_or_forward_return_values_read": False,
                "provider_request_issued": False,
                "candidate49_ledgers_changed": False,
            },
        )
        raise


def _record_path(manifest_path: Path, record: dict[str, Any]) -> Path:
    return (manifest_path.parent / str(record["path"])).resolve()


def verify_snapshot(manifest_path: Path) -> dict[str, Any]:
    validate_protocol()
    validate_implementation_freeze()
    manifest_path = manifest_path.expanduser().resolve()
    manifest = load_json(manifest_path)
    _, names = feature_config()
    if not (
        manifest.get("kind")
        == "a_share_three_day_walkforward_campaign286_alpha158_development_design"
        and manifest.get("status") == "immutable_design_ready_for_model_implementation"
        and manifest.get("feature_names") == names
        and manifest.get("feature_count") == FEATURE_COUNT
        and manifest.get("feature_library_sha256") == FEATURE_LIBRARY_SHA256
        and manifest.get("minimum_finite_features") == MINIMUM_FINITE_FEATURES
        and manifest.get("development_years") == list(DEVELOPMENT_YEARS)
        and manifest.get("partitions") == len(manifest.get("files") or []) == 5
        and manifest.get("historical_label_or_forward_return_values_read") is False
        and manifest.get("lockbox_2024_2025_feature_or_return_values_read") is False
    ):
        raise Campaign286DesignError("Campaign286 design manifest semantics changed")
    digest_rows: list[list[Any]] = []
    for record in manifest["files"]:
        path = _record_path(manifest_path, record)
        require_file(path, str(record["sha256"]), "Campaign286 design partition")
        frame = pd.read_parquet(
            path,
            columns=[
                "stock_day_key",
                *names,
                "finite_feature_count",
                "feature_support_eligible",
                "quality_listing_eligible",
                "model_support_eligible",
            ],
        )
        finite_count, support = support_state(
            frame[names].to_numpy(dtype=np.float32, copy=False)
        )
        quality = frame["quality_listing_eligible"].to_numpy(dtype=bool)
        model_support = frame["model_support_eligible"].to_numpy(dtype=bool)
        if not (
            len(frame) == int(record["rows"])
            and not frame["stock_day_key"].duplicated().any()
            and np.array_equal(
                finite_count, frame["finite_feature_count"].to_numpy(dtype=np.uint8)
            )
            and np.array_equal(
                support, frame["feature_support_eligible"].to_numpy(dtype=bool)
            )
            and np.array_equal(model_support, quality & support)
            and int(model_support.sum()) == int(record["model_support_eligible_rows"])
        ):
            raise Campaign286DesignError(
                "Campaign286 design partition semantics changed"
            )
        digest_rows.append(
            [
                int(record["year"]),
                len(frame),
                int(model_support.sum()),
                str(record["sha256"]),
            ]
        )
    if value_sha256(digest_rows) != manifest.get("dataset_sha256"):
        raise Campaign286DesignError("Campaign286 design dataset digest changed")
    audit_binding = manifest.get("structural_audit") or {}
    audit_path = (manifest_path.parent / str(audit_binding.get("path"))).resolve()
    require_file(audit_path, str(audit_binding.get("sha256")), "structural audit")
    audit = load_json(audit_path)
    if not (
        audit.get("status") == "passed_ready_for_frozen_model_implementation"
        and (audit.get("coverage") or {}).get(
            "gate_passed_before_historical_label_or_forward_return_read"
        )
        is True
        and audit.get("historical_label_or_forward_return_values_read") is False
    ):
        raise Campaign286DesignError("Campaign286 structural audit changed")
    return {
        "status": "verified",
        "manifest_path": str(manifest_path),
        "manifest_sha256": file_sha256(manifest_path),
        "dataset_sha256": manifest["dataset_sha256"],
        "rows": manifest["rows"],
        "model_support_eligible_rows": manifest["model_support_eligible_rows"],
        "feature_count": manifest["feature_count"],
        "historical_label_or_forward_return_values_read": False,
    }


def plan(*, output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    validate_protocol()
    validate_implementation_freeze()
    root = output_root.expanduser().resolve()
    ready = not root.exists() and not (root.parent / f".{root.name}.partial").exists()
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign286_design_plan",
        "status": (
            "ready_to_build_alpha158_development_design_without_labels"
            if ready
            else "not_ready_preserve_existing_output_or_partial"
        ),
        "ready": ready,
        "output_root": str(root),
        "feature_count": FEATURE_COUNT,
        "minimum_finite_features": MINIMUM_FINITE_FEATURES,
        "development_years": list(DEVELOPMENT_YEARS),
        "alpha158_feature_values_read_by_plan": False,
        "historical_label_or_forward_return_values_read_by_plan": False,
        "lockbox_2024_2025_feature_or_return_values_read_by_plan": False,
        "provider_request_issued": False,
        "credential_loaded": False,
        "candidate49_ledgers_changed": False,
    }


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    subcommands = command.add_subparsers(dest="command", required=True)
    subcommands.add_parser("plan")
    build = subcommands.add_parser("build")
    build.add_argument("--confirm-build", action="store_true")
    build.add_argument("--batch-size", type=int, default=128)
    verify = subcommands.add_parser("verify")
    verify.add_argument("--manifest", type=Path, required=True)
    return command


def main() -> int:
    args = parser().parse_args()
    if args.command == "plan":
        payload = plan()
    elif args.command == "build":
        if not args.confirm_build:
            raise Campaign286DesignError("build requires --confirm-build")
        manifest = build_design(batch_size=args.batch_size)
        payload = verify_snapshot(manifest)
    elif args.command == "verify":
        payload = verify_snapshot(args.manifest)
    else:  # pragma: no cover
        raise AssertionError(args.command)
    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
