#!/usr/bin/env python3
"""Resume Campaign059 while accepting only manifest-declared empty raw partitions.

This additive launcher leaves the frozen Campaign059 implementation unchanged.
An exact-column zero-row frame yields no return profiles and zero source-quality
counters; every nonempty frame delegates unchanged to the original extractor.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from scripts import a_share_three_day_walkforward_campaign059_features as core


REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign059_features.py"
CORE_RUNNER_SHA256 = "d96954a319caf6b7dd45eafd46fae7db2a6176abc292529d00480b4a9ad10cc0"
CORE_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_059_feature_implementation_freeze_20260804.json"
)
CORE_IMPLEMENTATION_FREEZE_SHA256 = "e4902e4487396fc58ffd8aa74a49c831ac83f732a79d61a63606276262f06d9d"
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_059_empty_partition_build_failure_20260804.json"
)
FAILURE_RECORD_SHA256 = "a01fe92707bfd16795f37dc7c140bb88b8d217c77a87ab0676a88ee33eb90f3c"
EXPECTED_EMPTY_PARTITIONS = (
    ("SH600485", 2021),
    ("SH600677", 2021),
    ("SH600680", 2019),
    ("SZ000670", 2021),
    ("SZ002260", 2020),
    ("SZ002260", 2021),
)

_ORIGINAL_EXTRACT_PROFILES = core.extract_signed_return_profiles


class Campaign059EmptyPartitionRepairError(RuntimeError):
    """Fail-closed Campaign059 compatibility-repair error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected_sha256:
        raise Campaign059EmptyPartitionRepairError(f"{label} changed: {path}")


def verify_repair_bindings(
    data_root: Path = core.DEFAULT_DATA_ROOT,
) -> dict[str, Any]:
    data_root = data_root.expanduser().resolve()
    if data_root != core.DEFAULT_DATA_ROOT.resolve():
        raise Campaign059EmptyPartitionRepairError("Campaign059 data root changed")
    _require_file(CORE_RUNNER, CORE_RUNNER_SHA256, "frozen core runner")
    _require_file(
        CORE_IMPLEMENTATION_FREEZE,
        CORE_IMPLEMENTATION_FREEZE_SHA256,
        "frozen core implementation record",
    )
    _require_file(FAILURE_RECORD, FAILURE_RECORD_SHA256, "immutable failure record")
    raw_manifest_path = data_root / core.RAW_MANIFEST_RELATIVE
    _require_file(raw_manifest_path, core.RAW_MANIFEST_SHA256, "raw source manifest")
    manifest = json.loads(raw_manifest_path.read_text(encoding="utf-8"))
    empty = tuple(
        sorted(
            (str(item["symbol"]).upper(), int(item["year"]))
            for item in manifest.get("files", [])
            if int(item.get("rows", -1)) == 0
        )
    )
    if empty != EXPECTED_EMPTY_PARTITIONS:
        raise Campaign059EmptyPartitionRepairError(
            "manifest-declared Campaign059 empty partitions changed"
        )
    return {
        "core_runner_sha256": CORE_RUNNER_SHA256,
        "core_implementation_freeze_sha256": CORE_IMPLEMENTATION_FREEZE_SHA256,
        "failure_record_sha256": FAILURE_RECORD_SHA256,
        "raw_manifest_sha256": core.RAW_MANIFEST_SHA256,
        "manifest_declared_empty_partitions": [
            f"{symbol}/{year}" for symbol, year in empty
        ],
    }


def extract_profiles_compat(
    raw: pd.DataFrame,
    *,
    symbol: str,
) -> tuple[dict[pd.Timestamp, Any], dict[str, int]]:
    if tuple(raw.columns) != core.RAW_COLUMNS:
        return _ORIGINAL_EXTRACT_PROFILES(raw, symbol=symbol)
    if raw.empty:
        return {}, {
            "source_sessions": 0,
            "source_rows": 0,
            "source_nonfinite_close_grid_rows": 0,
            "source_nonpositive_close_grid_rows": 0,
            "source_valid_close_grid_rows": 0,
            "source_exact_zero_return_positions": 0,
        }
    return _ORIGINAL_EXTRACT_PROFILES(raw, symbol=symbol)


def install_repair(data_root: Path = core.DEFAULT_DATA_ROOT) -> dict[str, Any]:
    result = verify_repair_bindings(data_root)
    current = core._engine.get("extract_amount_profiles")
    if current not in (_ORIGINAL_EXTRACT_PROFILES, extract_profiles_compat):
        raise Campaign059EmptyPartitionRepairError(
            "Campaign059 extractor was already changed by another caller"
        )
    core._engine["extract_amount_profiles"] = extract_profiles_compat
    return result


def main() -> int:
    install_repair(core.DEFAULT_DATA_ROOT)
    return core.main()


if __name__ == "__main__":
    raise SystemExit(main())
