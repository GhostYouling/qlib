#!/usr/bin/env python3
"""Fingerprint-bound completed Campaign054 no-return audit entrypoint."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign054_features_v8 as completed
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign054_features_v8 as completed


audited = completed.audited
runner = completed.runner
NO_RETURN_AUDIT = (
    runner.REPO_ROOT
    / "data/experiments/short_horizon/historical_walkforward/campaign_054/no_return/20260803T153026Z_campaign054_no_return_audit.json"
)
NO_RETURN_AUDIT_FREEZE = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_054_no_return_audit_freeze_20260803.json"
)
EXPECTED_V8_ENTRYPOINT_SHA256 = (
    "2487183025bdadfd1ef3f95431d06d491ade960f0aa89b2b88199c9526899699"
)
EXPECTED_NO_RETURN_AUDIT_SHA256 = (
    "866006cbe319afeca3b055bef2a1754b954e4511b953a3e8a2337d3aa575ee87"
)
EXPECTED_NO_RETURN_AUDIT_FREEZE_SHA256 = (
    "5903bc7d5dbf6eb5a8fd0b1eb0b4c0bf5a42f220aae206ba1493a86509bc4ad1"
)

if (
    runner._sha256(runner.Path(completed.__file__).resolve())
    != EXPECTED_V8_ENTRYPOINT_SHA256
):
    raise runner.Campaign054FeatureError(
        "Campaign054 completed v8 entrypoint changed"
    )
runner._require_file(
    NO_RETURN_AUDIT,
    EXPECTED_NO_RETURN_AUDIT_SHA256,
    "Campaign054 completed no-return audit",
)
runner._require_file(
    NO_RETURN_AUDIT_FREEZE,
    EXPECTED_NO_RETURN_AUDIT_FREEZE_SHA256,
    "Campaign054 no-return audit freeze",
)
runner.NO_RETURN_AUDIT_SHA256 = EXPECTED_NO_RETURN_AUDIT_SHA256
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(audited.main())
