#!/usr/bin/env python3
"""Fingerprint-bound Campaign055 no-return audit entrypoint."""

from __future__ import annotations

from pathlib import Path

try:
    import scripts.a_share_three_day_walkforward_campaign055_features_v7 as audited
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign055_features_v7 as audited


runner = audited.runner
AUDIT_IMPLEMENTATION_FREEZE = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_055_no_return_audit_implementation_freeze_20260804.json"
)
EXPECTED_AUDITED_V7_SHA256 = (
    "75dd159bd7f88be5521506bbcad95ae1516a620fb7d84247563b0898cbbf5540"
)
EXPECTED_AUDIT_IMPLEMENTATION_FREEZE_SHA256 = (
    "9f7e30b6f29f4eddde4f70e9a1b26f2f652634dd69c39c4c946612533d58e634"
)

if runner._sha256(Path(audited.__file__).resolve()) != EXPECTED_AUDITED_V7_SHA256:
    raise runner.Campaign055FeatureError(
        "Campaign055 frozen v7 no-return audit implementation changed"
    )
runner._require_file(
    AUDIT_IMPLEMENTATION_FREEZE,
    EXPECTED_AUDIT_IMPLEMENTATION_FREEZE_SHA256,
    "Campaign055 no-return audit implementation freeze",
)
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(audited.main())
