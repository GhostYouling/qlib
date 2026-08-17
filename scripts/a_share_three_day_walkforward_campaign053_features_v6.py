#!/usr/bin/env python3
"""Fingerprint-bound terminal Campaign053 no-return audit entrypoint."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign053_features_v5 as completed
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign053_features_v5 as completed


runner = completed.runner
EXPECTED_V5_ENTRYPOINT_SHA256 = (
    "83c3816baa58917ce31a142fcb2dca82a20550de0209ccda8756c6865a007dcb"
)
EXPECTED_NO_RETURN_AUDIT_SHA256 = (
    "8228e32422686d020bdf7c6b00e54469d025884c23c234b48088428280bfd3ba"
)


if (
    runner._sha256(runner.Path(completed.__file__).resolve())
    != EXPECTED_V5_ENTRYPOINT_SHA256
):
    raise runner.Campaign053FeatureError("Campaign053 completed v5 entrypoint changed")

runner.NO_RETURN_AUDIT_SHA256 = EXPECTED_NO_RETURN_AUDIT_SHA256
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(runner.main())
