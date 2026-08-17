#!/usr/bin/env python3
"""Read-only verifier for Campaign128's frozen feature snapshot."""

from __future__ import annotations

import argparse
import json
from typing import Any

from scripts import a_share_three_day_walkforward_campaign128_features as c128


MANIFEST_PATH = (
    c128.output_root(c128.DEFAULT_DATA_ROOT) / "snapshot_manifest.json"
).resolve()


class Campaign128SnapshotRecoveryError(RuntimeError):
    """Fail closed when a recovery binding or published byte changes."""


def validate_manifest_metadata(manifest: dict[str, Any]) -> None:
    """Validate only supplied metadata; do not open a candidate partition."""

    try:
        c128.validate_manifest_metadata(manifest)
    except c128.Campaign128FeatureError as exc:
        raise Campaign128SnapshotRecoveryError(str(exc)) from exc


def verify_snapshot(*, workers: int = 8) -> dict[str, Any]:
    """Verify every frozen output byte and semantic frame without returns."""

    try:
        result = c128.verify_snapshot_files(MANIFEST_PATH, workers=workers)
    except c128.Campaign128FeatureError as exc:
        raise Campaign128SnapshotRecoveryError(str(exc)) from exc
    return {
        **result,
        "recovery_verifier": "campaign128_frozen_read_only",
        "candidate_or_comparator_values_read_beyond_candidate_snapshot": False,
        "historical_daily_price_or_forward_return_values_read": False,
        "provider_request_issued": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    print(json.dumps(verify_snapshot(workers=args.workers), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
