#!/usr/bin/env python3
"""Run the single frozen Campaign042 three-session walk-forward trial.

Campaign042 reuses the byte-bound Campaign039 orchestration and unchanged
Campaign006 execution engine. Only deterministic campaign namespace and
admitted-factor substitutions are allowed; folds, execution assumptions,
survivor gates, and conditional exposed-stress rules remain inherited. The
shared reporting repair keeps displayed complexity equal to the feature set.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN039_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign039.py"
)
CAMPAIGN039_RUNNER_SHA256 = (
    "1d4c2977432f4d4fa9b0f7d9d47b09308511b5021bfbb8ab73e9d73d2631f59c"
)
OLD_FACTOR = "intraday_return_time_reversal_asymmetry_236p"
ADMITTED_FACTOR = "intraday_lunch_repricing_persistence_2r"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN039_RUNNER) != CAMPAIGN039_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign039 orchestration fingerprint changed")

_source = CAMPAIGN039_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign039", "Campaign042"),
    ("campaign039", "campaign042"),
    ("campaign_039", "campaign_042"),
    ("wf039", "wf042"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign042_generated",
}
exec(compile(_source, str(CAMPAIGN039_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign042Error = _generated["Campaign042Error"]
build_trial_catalog = _generated["build_trial_catalog"]
load_campaign = _generated["load_campaign"]
parser = _generated["parser"]
run_development = _generated["run_development"]
run_exposed_stress = _generated["run_exposed_stress"]
status = _generated["status"]
main = _generated["main"]
engine_namespace = _generated["engine_namespace"]
_inherited_survivor_decision = _generated[
    "_inherited_survivor_decision"
]
_survivor_decision_with_canonical_complexity = _generated[
    "_survivor_decision_with_canonical_complexity"
]


if __name__ == "__main__":
    raise SystemExit(main())
