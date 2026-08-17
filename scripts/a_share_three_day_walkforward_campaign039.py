#!/usr/bin/env python3
"""Run the single frozen Campaign039 three-session walk-forward trial.

Campaign039 reuses the byte-bound Campaign034 orchestration and unchanged
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
CAMPAIGN034_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign034.py"
)
CAMPAIGN034_RUNNER_SHA256 = (
    "e2ef6c4af690aa4983804408a91a281bbd5772f7d5a72a726b4afab6c19804c6"
)
OLD_FACTOR = "intraday_round_tenth_close_avoidance_240m"
ADMITTED_FACTOR = "intraday_return_time_reversal_asymmetry_236p"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN034_RUNNER) != CAMPAIGN034_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign034 orchestration fingerprint changed")

_source = CAMPAIGN034_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign034", "Campaign039"),
    ("campaign034", "campaign039"),
    ("campaign_034", "campaign_039"),
    ("wf034", "wf039"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign039_generated",
}
exec(compile(_source, str(CAMPAIGN034_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign039Error = _generated["Campaign039Error"]
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
