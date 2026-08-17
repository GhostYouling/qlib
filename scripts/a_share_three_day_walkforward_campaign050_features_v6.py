#!/usr/bin/env python3
"""No-return-audit-freeze-bound Campaign050 entrypoint."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign050_features_v5 as audit
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign050_features_v5 as audit


runner = audit.runner
AUDIT_ENTRYPOINT_FREEZE = (
    runner.REPO_ROOT
    / "docs/a_share_three_day_walkforward_campaign_050_no_return_audit_entrypoint_freeze_20260801.json"
)
EXPECTED_AUDIT_ENTRYPOINT_SHA256 = (
    "49829302753addf02efe66caaf5e9bf391ffd605da9a1f056705c6dca034b35b"
)
EXPECTED_AUDIT_ENTRYPOINT_FREEZE_SHA256 = (
    "ba77a6ed20cd6bfdf21ab708e3763b6e42922357a2d3d3c506e49a45f44851dd"
)

if (
    runner._sha256(runner.Path(audit.__file__).resolve())
    != EXPECTED_AUDIT_ENTRYPOINT_SHA256
):
    raise runner.Campaign050FeatureError(
        "Campaign050 snapshot-bound v5 entrypoint changed"
    )
if (
    runner._sha256(AUDIT_ENTRYPOINT_FREEZE)
    != EXPECTED_AUDIT_ENTRYPOINT_FREEZE_SHA256
):
    raise runner.Campaign050FeatureError(
        "Campaign050 no-return audit entrypoint freeze changed"
    )


if __name__ == "__main__":
    raise SystemExit(runner.main())
