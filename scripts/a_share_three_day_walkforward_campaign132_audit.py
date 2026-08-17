#!/usr/bin/env python3
"""Audit Campaign132's immutable numeric140 design without reading returns."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign132_design as design

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    design.output_root(design.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_132/no_return/"
    "design_structural_audit.json"
)
DEFAULT_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_132_structural_audit_implementation_freeze_20260814.json"
)
TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign132_audit.py"
)
LEGACY_GATE_SOURCE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_102_no_return_preregistration.json"
)

PROTOCOL_SHA256 = "b4c3f6b3a69506c8a8f5ee71ffe05e487af0f71ae2b104adb3a79b2efc4ac0be"
MANIFEST_SHA256 = "043c17fea89f3b0956d643a7c6e3f4d73a11403b967213d2d57539a6a8316a49"
DATASET_SHA256 = "12ce3a64b5e13581392ded9890e2064db4ccca3945da3eb8ad7752c95366a9fc"
LEGACY_GATE_SOURCE_SHA256 = (
    "5def1f153c4cca94f2d646598f09b810108688488b8aab0b2be345366364b8f9"
)
EXPECTED_ROWS = 1_331_759
EXPECTED_SESSIONS = 1_632
THRESHOLDS = {
    "minimum_median_coverage": 0.95,
    "minimum_p05_coverage": 0.90,
    "minimum_p05_eligible_names": 50.0,
    "minimum_potential_non_overlapping_three_session_cohorts": 200,
    "minimum_observed_cohort_years": 5,
}


class Campaign132AuditError(RuntimeError):
    """Fail closed when a structural-audit binding changes."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise Campaign132AuditError(f"JSON object required: {path}")
    return value


def require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or file_sha256(path) != expected_sha256:
        raise Campaign132AuditError(f"{label} changed: {path}")


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def validate_implementation_freeze() -> dict[str, Any]:
    freeze = load_json(DEFAULT_IMPLEMENTATION_FREEZE)
    if not (
        freeze.get("kind")
        == "a_share_three_day_walkforward_campaign132_structural_audit_implementation_freeze"
        and freeze.get("status")
        == "frozen_before_campaign132_daily_structural_coverage_read"
        and (freeze.get("protocol") or {}).get("sha256") == PROTOCOL_SHA256
        and (freeze.get("design_manifest") or {}).get("sha256") == MANIFEST_SHA256
        and (freeze.get("audit_runner") or {}).get("sha256")
        == file_sha256(Path(__file__).resolve())
        and (freeze.get("tests") or {}).get("sha256") == file_sha256(TEST_PATH)
        and freeze.get("daily_structural_coverage_read_before_freeze") is False
        and freeze.get(
            "historical_daily_price_or_forward_return_values_read_before_freeze"
        )
        is False
    ):
        raise Campaign132AuditError("Campaign132 structural-audit freeze changed")
    return freeze


def coverage_summary(
    daily: pd.DataFrame,
    *,
    expected_rows: int,
    expected_sessions: int,
    thresholds: dict[str, float | int] | None = None,
) -> dict[str, Any]:
    gate = dict(THRESHOLDS if thresholds is None else thresholds)
    required = {"session", "quality_listing_names", "eligible_names"}
    if set(daily) != required:
        raise Campaign132AuditError("daily coverage columns changed")
    ordered = daily.sort_values("session", kind="stable").reset_index(drop=True)
    if (
        len(ordered) != expected_sessions
        or ordered["session"].duplicated().any()
        or int(ordered["quality_listing_names"].sum()) != expected_rows
        or (ordered["eligible_names"] > ordered["quality_listing_names"]).any()
        or (ordered[["quality_listing_names", "eligible_names"]] < 0).any().any()
    ):
        raise Campaign132AuditError("daily coverage identity changed")
    ratios = ordered["eligible_names"] / ordered["quality_listing_names"]
    indices = np.arange(0, max(len(ordered) - 3, 0), 3)
    potential_mask = ordered.iloc[indices]["eligible_names"].ge(50)
    potential = int(potential_mask.sum())
    cohort_sessions = (
        ordered.iloc[indices].loc[potential_mask, "session"].to_numpy(dtype=np.int64)
    )
    cohort_years = sorted(
        pd.to_datetime(cohort_sessions, unit="D", origin="unix").year.unique().tolist()
    )
    median_coverage = float(ratios.median())
    p05_coverage = float(ratios.quantile(0.05))
    p05_names = float(ordered["eligible_names"].quantile(0.05))
    passed = bool(
        median_coverage >= float(gate["minimum_median_coverage"])
        and p05_coverage >= float(gate["minimum_p05_coverage"])
        and p05_names >= float(gate["minimum_p05_eligible_names"])
        and potential
        >= int(gate["minimum_potential_non_overlapping_three_session_cohorts"])
        and len(cohort_years) >= int(gate["minimum_observed_cohort_years"])
    )
    daily_digest = hashlib.sha256(
        ordered.to_csv(index=False, lineterminator="\n").encode("utf-8")
    ).hexdigest()
    return {
        "quality_listing_rows": int(ordered["quality_listing_names"].sum()),
        "eligible_rows": int(ordered["eligible_names"].sum()),
        "calendar_sessions": len(ordered),
        "median_coverage": median_coverage,
        "p05_coverage": p05_coverage,
        "eligible_names_min": int(ordered["eligible_names"].min()),
        "eligible_names_p05": p05_names,
        "eligible_names_median": float(ordered["eligible_names"].median()),
        "potential_non_overlapping_three_session_cohorts": potential,
        "observed_cohort_years": [int(value) for value in cohort_years],
        "daily_coverage_frame_sha256": daily_digest,
        "gate": gate,
        "gate_passed_before_model_fit_or_returns": passed,
    }


def structural_audit(manifest_path: Path) -> dict[str, Any]:
    validate_implementation_freeze()
    manifest_path = manifest_path.expanduser().resolve()
    require_file(Path(design.DEFAULT_PROTOCOL), PROTOCOL_SHA256, "Campaign132 protocol")
    require_file(manifest_path, MANIFEST_SHA256, "Campaign132 design manifest")
    require_file(
        LEGACY_GATE_SOURCE,
        LEGACY_GATE_SOURCE_SHA256,
        "pre-existing Campaign102 structural gate source",
    )
    verification = design.verify_snapshot(manifest_path)
    manifest = load_json(manifest_path)
    if manifest.get("dataset_sha256") != DATASET_SHA256:
        raise Campaign132AuditError("Campaign132 design dataset digest changed")
    daily_rows: list[dict[str, Any]] = []
    for record in manifest["files"]:
        path = (manifest_path.parent / str(record["path"])).resolve()
        frame = pd.read_parquet(path, columns=["stock_day_key", design.ELIGIBLE_NAME])
        sessions = frame["stock_day_key"].to_numpy(dtype=np.int64) // 4_000_000
        eligible = frame[design.ELIGIBLE_NAME].to_numpy(dtype=bool)
        grouped = (
            pd.DataFrame({"session": sessions, "eligible": eligible})
            .groupby("session", sort=True, observed=True)["eligible"]
            .agg(["size", "sum"])
        )
        for row in grouped.itertuples():
            daily_rows.append(
                {
                    "session": int(row.Index),
                    "quality_listing_names": int(row.size),
                    "eligible_names": int(row.sum),
                }
            )
    coverage = coverage_summary(
        pd.DataFrame(daily_rows),
        expected_rows=EXPECTED_ROWS,
        expected_sessions=EXPECTED_SESSIONS,
    )
    passed = bool(coverage["gate_passed_before_model_fit_or_returns"])
    return {
        "schema_version": 1,
        "kind": "a_share_three_day_walkforward_campaign132_design_structural_audit",
        "status": (
            "passed_ready_for_frozen_model_implementation"
            if passed
            else "failed_terminal_before_model_fit_or_returns"
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "protocol": {"path": str(design.DEFAULT_PROTOCOL), "sha256": PROTOCOL_SHA256},
        "snapshot": {
            "path": str(manifest_path),
            "sha256": MANIFEST_SHA256,
            "dataset_sha256": DATASET_SHA256,
        },
        "inherited_structural_gate_source": {
            "path": str(LEGACY_GATE_SOURCE),
            "sha256": LEGACY_GATE_SOURCE_SHA256,
            "thresholds_copied_without_change": True,
            "thresholds_selected_from_campaign132_observations": False,
        },
        "verification": verification,
        "coverage": coverage,
        "campaign132_design_matrix_values_read": True,
        "model_fitting_performed": False,
        "historical_daily_price_fields_read": [],
        "historical_forward_return_fields_read": False,
        "provider_request_issued": False,
        "credential_loaded": False,
        "candidate49_historical_backfill_performed": False,
        "candidate49_ledgers_changed": False,
        "current_scoring_selection_sizing_or_orders_performed": False,
    }


def plan() -> dict[str, Any]:
    validate_implementation_freeze()
    require_file(Path(design.DEFAULT_PROTOCOL), PROTOCOL_SHA256, "Campaign132 protocol")
    require_file(DEFAULT_MANIFEST, MANIFEST_SHA256, "Campaign132 design manifest")
    require_file(
        LEGACY_GATE_SOURCE,
        LEGACY_GATE_SOURCE_SHA256,
        "pre-existing Campaign102 structural gate source",
    )
    return {
        "status": "ready_to_audit_daily_design_coverage_without_prices_or_returns",
        "ready": True,
        "manifest_sha256": MANIFEST_SHA256,
        "dataset_sha256": DATASET_SHA256,
        "inherited_thresholds": THRESHOLDS,
        "design_values_read_by_plan": False,
        "historical_daily_price_or_forward_return_values_read_by_plan": False,
        "provider_request_issued": False,
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    subcommands = value.add_subparsers(dest="command", required=True)
    subcommands.add_parser("plan")
    audit = subcommands.add_parser("audit")
    audit.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    audit.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    audit.add_argument("--confirm-audit", action="store_true")
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "plan":
            payload = plan()
        else:
            if not args.confirm_audit:
                raise Campaign132AuditError("audit requires --confirm-audit")
            result = structural_audit(args.manifest)
            output = args.output.expanduser().resolve()
            atomic_json(output, result)
            payload = {
                "status": result["status"],
                "audit": str(output),
                "audit_sha256": file_sha256(output),
                "coverage": result["coverage"],
            }
    except (Campaign132AuditError, ValueError, FileNotFoundError) as error:
        print(
            json.dumps(
                {"status": "failed", "error": str(error)}, ensure_ascii=False, indent=2
            )
        )
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
