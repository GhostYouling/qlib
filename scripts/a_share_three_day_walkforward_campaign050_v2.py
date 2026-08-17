#!/usr/bin/env python3
"""Exact-schema Campaign050 development runner entrypoint."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign050 as runner
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign050 as runner


EXPECTED_RUNNER_V1_SHA256 = (
    "1840d5723e215522e9f92c3e08642a4b0f52e23112f429d772821ca054271a49"
)
DEFAULT_PREREGISTRATION_V2 = (
    runner.REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_050_preregistration_v2.json"
)

if runner._sha256(runner.Path(runner.__file__).resolve()) != EXPECTED_RUNNER_V1_SHA256:
    raise RuntimeError("frozen Campaign050 v1 development runner changed")

runner.engine_namespace["DEFAULT_CAMPAIGN"] = DEFAULT_PREREGISTRATION_V2

Campaign050Error = runner.Campaign050Error
build_trial_catalog = runner.build_trial_catalog
load_campaign = runner.load_campaign
run_development = runner.run_development
run_exposed_stress = runner.run_exposed_stress
status = runner.status
main = runner.main


if __name__ == "__main__":
    raise SystemExit(main())
