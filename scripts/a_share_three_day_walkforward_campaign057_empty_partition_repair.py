#!/usr/bin/env python3
"""Resume Campaign057 while accepting only manifest-declared empty raw partitions.

This additive compatibility launcher leaves the frozen Campaign057 feature
implementation unchanged.  It replaces one extractor boundary: an exact-column
zero-row raw frame yields no profiles and ``source_sessions=0``.  Every nonempty
frame is delegated unchanged to the original frozen extractor.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from scripts import a_share_three_day_walkforward_campaign057_features as core


REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign057_features.py"
CORE_RUNNER_SHA256 = "3706ac11c551dd02c8d6d8cf30c95a6f076d6a6e6c5dbba4beb07dde10aca66a"
CORE_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_057_feature_implementation_freeze_20260804.json"
)
CORE_IMPLEMENTATION_FREEZE_SHA256 = "44b889f9deb49b7fc3bbe1293a42e77dd5844502cba723d32d6eb7d46c118a7e"
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_057_empty_partition_build_failure_20260804.json"
)
FAILURE_RECORD_SHA256 = "32b7814c51a13d8bbd38e2c6692e3c98dba08cdc8a78b3f710ed1b2bb4a23c08"
EXPECTED_EMPTY_PARTITIONS = (
    ("SH600485", 2021),
    ("SH600677", 2021),
    ("SH600680", 2019),
    ("SZ000670", 2021),
    ("SZ002260", 2020),
    ("SZ002260", 2021),
)

_ORIGINAL_EXTRACT_PROFILES = core.extract_amount_profiles


class Campaign057EmptyPartitionRepairError(RuntimeError):
    """Fail-closed compatibility-repair error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if expected_sha256.startswith("__"):
        raise Campaign057EmptyPartitionRepairError(
            "Campaign057 failure identity is not frozen"
        )
    if not path.is_file() or _sha256(path) != expected_sha256:
        raise Campaign057EmptyPartitionRepairError(f"{label} changed: {path}")


def verify_repair_bindings(
    data_root: Path = core.DEFAULT_DATA_ROOT,
) -> dict[str, Any]:
    """Verify the original implementation and exact empty-partition set."""

    data_root = data_root.expanduser().resolve()
    if data_root != core.DEFAULT_DATA_ROOT.resolve():
        raise Campaign057EmptyPartitionRepairError("Campaign057 data root changed")
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
        raise Campaign057EmptyPartitionRepairError(
            "manifest-declared Campaign057 empty partitions changed"
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
    """Accept an exact-column empty frame; delegate every nonempty frame."""

    if tuple(raw.columns) != core.RAW_COLUMNS:
        return _ORIGINAL_EXTRACT_PROFILES(raw, symbol=symbol)
    if raw.empty:
        return {}, {"source_sessions": 0}
    return _ORIGINAL_EXTRACT_PROFILES(raw, symbol=symbol)


def install_repair(data_root: Path = core.DEFAULT_DATA_ROOT) -> dict[str, Any]:
    """Install the one-boundary repair after all immutable bindings pass."""

    result = verify_repair_bindings(data_root)
    if core.extract_amount_profiles not in (
        _ORIGINAL_EXTRACT_PROFILES,
        extract_profiles_compat,
    ):
        raise Campaign057EmptyPartitionRepairError(
            "Campaign057 extractor was already changed by another caller"
        )
    core.extract_amount_profiles = extract_profiles_compat
    core._generated["extract_amount_profiles"] = extract_profiles_compat
    return result


def main() -> int:
    install_repair(core.DEFAULT_DATA_ROOT)
    return core.main()


if __name__ == "__main__":
    raise SystemExit(main())
