#!/usr/bin/env python3
"""Recover Campaign260's snapshot build by adding two manifest-only counters."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts import a_share_three_day_walkforward_campaign260_features as base


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_BUILDER_PATH = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign260_features.py"
BASE_BUILDER_SHA256 = "9c13373796d2023acbacc786ea74dd4d1cf63cc60cd5f1152a5b4c52a375d77b"
FAILURE_RECORD_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_260_initial_snapshot_build_failure_20260816.json"
)
RECOVERY_FREEZE_PATH = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_260_snapshot_build_recovery_freeze_20260816.json"
)
RECOVERY_TEST_PATH = (
    REPO_ROOT
    / "tests/data_collector_tests/test_a_share_three_day_walkforward_campaign260_features_recovery.py"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(BASE_BUILDER_PATH) != BASE_BUILDER_SHA256:
    raise RuntimeError("frozen Campaign260 base builder changed")


_original_extract = base.extract_amount_clock_third_central_moment


def extract_amount_clock_third_central_moment(
    raw: pd.DataFrame, *, symbol: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Preserve candidate values and add exact inherited support counters."""

    values, quality = _original_extract(raw, symbol=symbol)
    work = raw.loc[:, ["datetime", "amount"]].copy()
    work["datetime"] = pd.to_datetime(work["datetime"], errors="coerce")
    work["amount"] = pd.to_numeric(work["amount"], errors="coerce")
    work["trade_date"] = work["datetime"].dt.normalize()
    work["minute_code"] = work["datetime"].dt.hour * 60 + work["datetime"].dt.minute
    selected = work.loc[
        work["minute_code"].isin(base.CONTINUOUS_MINUTE_CODE_SET),
        ["trade_date", "minute_code", "amount"],
    ].copy()
    selected["minute_code"] = pd.Categorical(
        selected["minute_code"],
        categories=base.CONTINUOUS_MINUTE_CODES,
        ordered=True,
    )
    selected = selected.sort_values(["trade_date", "minute_code"], kind="stable")
    dates = pd.DatetimeIndex(values["trade_date"]).normalize()
    amounts = selected["amount"].to_numpy(dtype=np.float64).reshape(
        len(dates), base.formula.PROFILE_POSITIONS
    )
    eligible = np.isfinite(
        pd.to_numeric(values[base.FACTOR_SHORT_NAME], errors="coerce").to_numpy()
    )
    quality = dict(quality)
    quality["positive_amount_bars"] = int((amounts[eligible] > 0.0).sum())
    quality["zero_amount_bars"] = int((amounts[eligible] == 0.0).sum())
    return values, quality


def _validate_recovery_freeze() -> dict[str, Any]:
    if not RECOVERY_FREEZE_PATH.is_file():
        raise base.Campaign260FeatureError("Campaign260 recovery freeze missing")
    record = json.loads(RECOVERY_FREEZE_PATH.read_text(encoding="utf-8"))
    code = record.get("code") or {}
    tests = record.get("tests") or {}
    boundary = record.get("research_boundary") or {}
    if not (
        record.get("kind")
        == "a_share_three_day_walkforward_campaign260_snapshot_build_recovery_freeze"
        and record.get("status")
        == "counter_schema_only_recovery_frozen_before_retry"
        and code.get("base_builder_sha256") == BASE_BUILDER_SHA256
        and code.get("recovery_runner_sha256") == _sha256(Path(__file__).resolve())
        and tests.get("recovery_test_sha256") == _sha256(RECOVERY_TEST_PATH)
        and tests.get("exit_code") == 0
        and tests.get("passed") >= 3
        and record.get("candidate_formula_or_value_semantics_changed") is False
        and record.get("output_run_id") == base.OUTPUT_RUN_ID
        and boundary.get("comparator_values_read_before_retry") is False
        and boundary.get("historical_daily_price_or_forward_return_values_read")
        is False
        and boundary.get("provider_request_issued") is False
        and boundary.get("candidate49_ledgers_changed") is False
    ):
        raise base.Campaign260FeatureError("Campaign260 recovery freeze changed")
    return record


base._engine["extract_amount_clock_third_central_moment"] = (
    extract_amount_clock_third_central_moment
)
base._engine["_validate_implementation_freeze"] = _validate_recovery_freeze

FACTOR_NAME = base.FACTOR_NAME
OUTPUT_RUN_ID = base.OUTPUT_RUN_ID
DEFAULT_DATA_ROOT = base.DEFAULT_DATA_ROOT
output_root = base.output_root
build_snapshot = base.build_snapshot
verify_snapshot_files = base.verify_snapshot_files
status = base.status
main = base.main


if __name__ == "__main__":
    raise SystemExit(main())
