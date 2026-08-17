#!/usr/bin/env python3
"""Run the single frozen Campaign021 three-session walk-forward trial.

Campaign021 reuses the byte-bound Campaign018 orchestration and unchanged
Campaign006 execution engine. Only deterministic campaign namespace and
admitted-factor substitutions are allowed; folds, execution assumptions,
survivor gates, and conditional exposed-stress rules remain inherited.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN018_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign018.py"
)
CAMPAIGN018_RUNNER_SHA256 = (
    "393bbc40a98d746f285bfb60bde6bce419726078f27843b9e93609f2c8df4b63"
)
OLD_FACTOR = "intraday_range_share_volume_confirmation_240m"
ADMITTED_FACTOR = "intraday_market_response_delay_asymmetry_236p"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN018_RUNNER) != CAMPAIGN018_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign018 orchestration fingerprint changed")

_source = CAMPAIGN018_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign018", "Campaign021"),
    ("campaign018", "campaign021"),
    ("campaign_018", "campaign_021"),
    ("wf018", "wf021"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign021_generated",
}
exec(compile(_source, str(CAMPAIGN018_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign021Error = _generated["Campaign021Error"]
build_trial_catalog = _generated["build_trial_catalog"]
load_campaign = _generated["load_campaign"]
parser = _generated["parser"]
run_development = _generated["run_development"]
run_exposed_stress = _generated["run_exposed_stress"]
status = _generated["status"]
main = _generated["main"]
engine_namespace = run_exposed_stress.__globals__


if __name__ == "__main__":
    raise SystemExit(main())
