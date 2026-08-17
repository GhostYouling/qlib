#!/usr/bin/env python3
"""Resume Campaign060 while accepting only manifest-declared empty partitions.

The frozen Campaign060 implementation is unchanged.  This launcher replaces
one extractor boundary: an exact-column zero-row raw frame yields no profiles.
Every nonempty or wrong-column frame delegates to the original extractor.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from scripts import a_share_three_day_walkforward_campaign060_features as core


REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign060_features.py"
CORE_RUNNER_SHA256 = "6e9d51fbe18329e13e3f865c66597af56864313069d3d558ac46487347923e47"
CORE_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_060_feature_implementation_freeze_20260804.json"
)
CORE_IMPLEMENTATION_FREEZE_SHA256 = "ee6441831cf6ce1a61862fbef692a2540b9ef8f9b9e0bfff4436b4c6e8461f18"
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_060_empty_partition_build_failure_20260804.json"
)
FAILURE_RECORD_SHA256 = "4a0d8f98693700ea8504c852e1e035dbae991ee5ee89598b8584105a6e378f82"
ATTEMPT_LEDGER = (
    REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_060/research_attempt_ledger.json"
)
ATTEMPT_LEDGER_SHA256 = "8d250c52c24ab38f6089b25f20812ec56d73be229eeff813746af97b0d23aa1f"
EXPECTED_EMPTY_PARTITIONS = (
    ("SH600485", 2021),
    ("SH600677", 2021),
    ("SH600680", 2019),
    ("SZ000670", 2021),
    ("SZ002260", 2020),
    ("SZ002260", 2021),
)

_ORIGINAL_EXTRACT_PROFILES = core._runtime["extract_amount_profiles"]


class Campaign060EmptyPartitionRepairError(RuntimeError):
    """Fail-closed compatibility-repair error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected_sha256:
        raise Campaign060EmptyPartitionRepairError(f"{label} changed: {path}")


def verify_repair_bindings(
    data_root: Path = core.DEFAULT_DATA_ROOT,
) -> dict[str, Any]:
    """Verify frozen code and the exact manifest-declared empty set."""

    data_root = data_root.expanduser().resolve()
    if data_root != core.DEFAULT_DATA_ROOT.resolve():
        raise Campaign060EmptyPartitionRepairError("Campaign060 data root changed")
    _require_file(CORE_RUNNER, CORE_RUNNER_SHA256, "frozen core runner")
    _require_file(
        CORE_IMPLEMENTATION_FREEZE,
        CORE_IMPLEMENTATION_FREEZE_SHA256,
        "frozen core implementation record",
    )
    _require_file(FAILURE_RECORD, FAILURE_RECORD_SHA256, "immutable failure record")
    _require_file(ATTEMPT_LEDGER, ATTEMPT_LEDGER_SHA256, "append-only attempt ledger")
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
        raise Campaign060EmptyPartitionRepairError(
            "manifest-declared Campaign060 empty partitions changed"
        )
    return {
        "core_runner_sha256": CORE_RUNNER_SHA256,
        "core_implementation_freeze_sha256": CORE_IMPLEMENTATION_FREEZE_SHA256,
        "failure_record_sha256": FAILURE_RECORD_SHA256,
        "attempt_ledger_sha256": ATTEMPT_LEDGER_SHA256,
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
    """Accept exact-column emptiness; delegate every other frame."""

    if tuple(raw.columns) != core.RAW_COLUMNS:
        return _ORIGINAL_EXTRACT_PROFILES(raw, symbol=symbol)
    if raw.empty:
        return {}, {"source_sessions": 0}
    return _ORIGINAL_EXTRACT_PROFILES(raw, symbol=symbol)


def install_repair(data_root: Path = core.DEFAULT_DATA_ROOT) -> dict[str, Any]:
    """Install the one-boundary repair after every binding passes."""

    result = verify_repair_bindings(data_root)
    current = core._runtime["extract_amount_profiles"]
    if current not in (_ORIGINAL_EXTRACT_PROFILES, extract_profiles_compat):
        raise Campaign060EmptyPartitionRepairError(
            "Campaign060 extractor was already changed by another caller"
        )
    core._runtime["extract_amount_profiles"] = extract_profiles_compat
    core._engine["extract_amount_profiles"] = extract_profiles_compat
    return result


def main() -> int:
    install_repair(core.DEFAULT_DATA_ROOT)
    return core.main()


if __name__ == "__main__":
    raise SystemExit(main())
