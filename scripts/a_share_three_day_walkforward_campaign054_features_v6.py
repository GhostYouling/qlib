#!/usr/bin/env python3
"""Fingerprint-bound Campaign054 ordered no-return audit entrypoint."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign054_features_v5 as audited
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign054_features_v5 as audited


runner = audited.runner
AUDIT_IMPLEMENTATION_FREEZE = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_054_no_return_audit_implementation_freeze_20260803.json"
)
EXPECTED_AUDIT_ENTRYPOINT_SHA256 = (
    "4f7b37d64666bea5a8c4d517bd6262a1f0b2ead03b20bb44bb08e963aa1188cc"
)
EXPECTED_AUDIT_IMPLEMENTATION_FREEZE_SHA256 = (
    "0d1653100e6eb4390a960a1c4f8a14a5e9dbc46aef440a6613c3c80bddf88ad9"
)

if (
    runner._sha256(runner.Path(audited.__file__).resolve())
    != EXPECTED_AUDIT_ENTRYPOINT_SHA256
):
    raise runner.Campaign054FeatureError(
        "Campaign054 frozen v5 audit entrypoint changed"
    )
runner._require_file(
    AUDIT_IMPLEMENTATION_FREEZE,
    EXPECTED_AUDIT_IMPLEMENTATION_FREEZE_SHA256,
    "Campaign054 no-return-audit implementation freeze",
)
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(audited.main())
