#!/usr/bin/env python3
"""Run Campaign058 no-return audit with its frozen finite-float range adapter."""

from __future__ import annotations

import gc
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.dataset as pa_dataset

from scripts import a_share_three_day_walkforward_campaign058_no_return_audit as audit


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign058_no_return_audit.py"
AUDIT_RUNNER_SHA256 = "84bf18ce4ccda2292235bd86cbc7be707560e04622ede15d0dfd2747ef79f8a0"
AUDIT_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_058_no_return_audit_implementation_freeze_20260804.json"
)
AUDIT_FREEZE_SHA256 = "ad4510111185aa37c43a12256f2b9801f4044a7c0e608369fb6ced87846fcccf"
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_058_no_return_audit_candidate_range_binding_failure_20260804.json"
)
FAILURE_RECORD_SHA256 = "4076ae740e68ef30b2256d96bd0acf59f1d1656f0f136b88a5cf3b34291d99fa"
SNAPSHOT_BINDING = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_058_feature_snapshot_binding_20260804.json"
)
SNAPSHOT_BINDING_SHA256 = "0cf92fd4c788a2250eb6b9359062e92908b7c17663b47732445d28c56cb9cf65"


class Campaign058NoReturnAuditRangeRepairError(RuntimeError):
    """Fail-closed additive candidate-loader repair error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected_sha256:
        raise Campaign058NoReturnAuditRangeRepairError(f"{label} changed: {path}")


def verify_repair_bindings() -> dict[str, str]:
    _require_file(AUDIT_RUNNER, AUDIT_RUNNER_SHA256, "frozen audit runner")
    _require_file(AUDIT_FREEZE, AUDIT_FREEZE_SHA256, "frozen audit record")
    _require_file(FAILURE_RECORD, FAILURE_RECORD_SHA256, "immutable failure record")
    _require_file(SNAPSHOT_BINDING, SNAPSHOT_BINDING_SHA256, "snapshot binding")
    if audit.FACTOR_NAME != "quarterly_profit_revenue_growth_spread_pp":
        raise Campaign058NoReturnAuditRangeRepairError("Campaign058 factor changed")
    return {
        "audit_runner_sha256": AUDIT_RUNNER_SHA256,
        "audit_freeze_sha256": AUDIT_FREEZE_SHA256,
        "failure_record_sha256": FAILURE_RECORD_SHA256,
        "snapshot_binding_sha256": SNAPSHOT_BINDING_SHA256,
    }


def validate_candidate_frame(
    frame: pd.DataFrame,
    *,
    expected_rows: int,
    expected_eligible_rows: int,
) -> pd.DataFrame:
    factor = audit.FACTOR_NAME
    eligibility = f"{factor}_eligible"
    expected_columns = ("trade_date", "symbol", factor, eligibility)
    if tuple(frame.columns) != expected_columns or len(frame) != expected_rows:
        raise Campaign058NoReturnAuditRangeRepairError(
            "Campaign058 repaired candidate frame schema or row count changed"
        )
    result = frame.copy()
    result["trade_date"] = pd.to_datetime(
        result["trade_date"], errors="coerce"
    ).dt.normalize()
    result["symbol"] = result["symbol"].astype(str).str.upper()
    result[eligibility] = (
        result[eligibility].astype("boolean").fillna(False).astype(bool)
    )
    result[factor] = pd.to_numeric(result[factor], errors="coerce")
    eligible = result[eligibility]
    values = result.loc[eligible, factor].to_numpy(dtype=float)
    if (
        result["trade_date"].isna().any()
        or result.duplicated(["trade_date", "symbol"]).any()
        or not np.isfinite(values).all()
        or result.loc[~eligible, factor].notna().any()
        or int(eligible.sum()) != expected_eligible_rows
    ):
        raise Campaign058NoReturnAuditRangeRepairError(
            "Campaign058 repaired candidate values or keys are invalid"
        )
    result["symbol"] = result["symbol"].astype("category")
    return result


def load_candidate_frame_compat(
    manifest_path: Path,
    manifest: dict[str, Any],
) -> pd.DataFrame:
    manifest_path = manifest_path.expanduser().resolve()
    records = list(manifest.get("files") or [])
    if (
        manifest_path != audit.SNAPSHOT_MANIFEST_PATH.resolve()
        or len(records) != audit.EXPECTED_PARTITIONS
        or manifest.get("partitions") != audit.EXPECTED_PARTITIONS
        or manifest.get("rows") != audit.EXPECTED_ROWS
        or manifest.get("dataset_sha256") != audit.SNAPSHOT_DATASET_SHA256
    ):
        raise Campaign058NoReturnAuditRangeRepairError(
            "Campaign058 repaired candidate-loader manifest identity changed"
        )
    root = (manifest_path.parent / "partitions").resolve()
    paths: list[str] = []
    for record in records:
        path = Path(str(record.get("path"))).expanduser().resolve()
        if path.parent.parent != root:
            raise Campaign058NoReturnAuditRangeRepairError(
                f"Campaign058 candidate partition escapes root: {path}"
            )
        paths.append(str(path))
    if len(paths) != len(set(paths)):
        raise Campaign058NoReturnAuditRangeRepairError(
            "Campaign058 candidate manifest contains duplicate paths"
        )
    factor = audit.FACTOR_NAME
    columns = ["trade_date", "symbol", factor, f"{factor}_eligible"]
    dataset = pa_dataset.dataset(paths, format="parquet")
    table = dataset.to_table(columns=columns, use_threads=True)
    frame = table.to_pandas(split_blocks=True, self_destruct=True)
    del table, dataset
    gc.collect()
    return validate_candidate_frame(
        frame,
        expected_rows=audit.EXPECTED_ROWS,
        expected_eligible_rows=audit.EXPECTED_ELIGIBLE_ROWS,
    )


def install_repair() -> dict[str, str]:
    result = verify_repair_bindings()
    current = audit._audit_engine.get("load_candidate_frame")
    if current not in (audit.load_candidate_frame, load_candidate_frame_compat):
        raise Campaign058NoReturnAuditRangeRepairError(
            "Campaign058 candidate loader was already changed by another caller"
        )
    audit._audit_engine["load_candidate_frame"] = load_candidate_frame_compat
    return result


def main() -> int:
    install_repair()
    return audit.main()


if __name__ == "__main__":
    raise SystemExit(main())
