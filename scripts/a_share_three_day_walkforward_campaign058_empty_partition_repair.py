#!/usr/bin/env python3
"""Resume Campaign058 while accepting only manifest-declared empty raw partitions.

This additive compatibility launcher leaves the frozen Campaign058 feature
implementation unchanged.  It replaces one extractor boundary: an exact-column
zero-row raw frame yields no quarterly states and zero source-quality counters.
Every nonempty frame is delegated unchanged to the frozen extractor.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from scripts import a_share_three_day_walkforward_campaign058_features as core


REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_RUNNER = REPO_ROOT / "scripts/a_share_three_day_walkforward_campaign058_features.py"
CORE_RUNNER_SHA256 = "78ebccb0f8e62f0977dbd41e33aaeef62bf12fc8547bc09ff7d92e8eccb2224c"
CORE_IMPLEMENTATION_FREEZE = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_058_feature_implementation_freeze_20260804.json"
)
CORE_IMPLEMENTATION_FREEZE_SHA256 = "9539219b2a83beb58a3f701b6cae334051d18a2a37cb74778fa3e94c4110c38c"
FAILURE_RECORD = (
    REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_058_empty_partition_build_failure_20260804.json"
)
FAILURE_RECORD_SHA256 = "8d7555d79fa0b56762bf2ba8ed0176b8dfbb0eabf4a731e3f009c1398601fda2"
EXPECTED_EMPTY_PARTITIONS = (
    ("SH600485", 2021),
    ("SH600677", 2021),
    ("SH600680", 2019),
    ("SZ000670", 2021),
    ("SZ002260", 2020),
    ("SZ002260", 2021),
)

_ORIGINAL_EXTRACT_STATES = core.extract_quarterly_spread_states


class Campaign058EmptyPartitionRepairError(RuntimeError):
    """Fail-closed compatibility-repair error."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected_sha256:
        raise Campaign058EmptyPartitionRepairError(f"{label} changed: {path}")


def verify_repair_bindings(
    data_root: Path = core.DEFAULT_DATA_ROOT,
) -> dict[str, Any]:
    """Verify the original implementation and exact empty-partition set."""

    data_root = data_root.expanduser().resolve()
    if data_root != core.DEFAULT_DATA_ROOT.resolve():
        raise Campaign058EmptyPartitionRepairError("Campaign058 data root changed")
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
        raise Campaign058EmptyPartitionRepairError(
            "manifest-declared Campaign058 empty partitions changed"
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


def extract_states_compat(
    raw: pd.DataFrame,
    *,
    symbol: str,
) -> tuple[dict[pd.Timestamp, float], dict[str, int]]:
    """Accept an exact-column empty frame; delegate every nonempty frame."""

    if tuple(raw.columns) != core.RAW_COLUMNS:
        return _ORIGINAL_EXTRACT_STATES(raw, symbol=symbol)
    if raw.empty:
        return {}, {
            "source_sessions": 0,
            "source_identity_rows": 0,
            "sessions_without_prior_effective_quarterly_event": 0,
            "sessions_with_nonfinite_growth_spread_state": 0,
            "sessions_with_finite_growth_spread_state": 0,
        }
    return _ORIGINAL_EXTRACT_STATES(raw, symbol=symbol)


def install_repair(data_root: Path = core.DEFAULT_DATA_ROOT) -> dict[str, Any]:
    """Install the one-boundary repair after all immutable bindings pass."""

    result = verify_repair_bindings(data_root)
    current = core._engine.get("extract_amount_profiles")
    if current not in (_ORIGINAL_EXTRACT_STATES, extract_states_compat):
        raise Campaign058EmptyPartitionRepairError(
            "Campaign058 extractor was already changed by another caller"
        )
    core._engine["extract_amount_profiles"] = extract_states_compat
    return result


def main() -> int:
    install_repair(core.DEFAULT_DATA_ROOT)
    return core.main()


if __name__ == "__main__":
    raise SystemExit(main())
