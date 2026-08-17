#!/usr/bin/env python3
"""Run the single frozen Campaign034 three-session walk-forward trial.

Campaign034 reuses the byte-bound Campaign033 orchestration and unchanged
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
CAMPAIGN033_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign033.py"
)
CAMPAIGN033_RUNNER_SHA256 = (
    "2e27892205b626b5d7a5e804cb17f4385d29d6a544c5c3670e6f1ed0d42d957d"
)
OLD_FACTOR = "intraday_return_spectral_entropy_59f"
ADMITTED_FACTOR = "intraday_round_tenth_close_avoidance_240m"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN033_RUNNER) != CAMPAIGN033_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign033 orchestration fingerprint changed")

_source = CAMPAIGN033_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign033", "Campaign034"),
    ("campaign033", "campaign034"),
    ("campaign_033", "campaign_034"),
    ("wf033", "wf034"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign034_generated",
}
exec(compile(_source, str(CAMPAIGN033_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign034Error = _generated["Campaign034Error"]
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
