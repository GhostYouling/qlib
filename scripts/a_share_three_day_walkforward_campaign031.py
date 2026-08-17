#!/usr/bin/env python3
"""Run the single frozen Campaign031 three-session walk-forward trial.

Campaign031 reuses the byte-bound Campaign030 orchestration and unchanged
Campaign006 execution engine. Only deterministic campaign namespace and
admitted-factor substitutions are allowed; folds, execution assumptions,
survivor gates, and conditional exposed-stress rules remain inherited.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN030_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign030.py"
)
CAMPAIGN030_RUNNER_SHA256 = (
    "c72e48a51577399d9757ffe672b98d464c635d00e7aed9689e37be482f4859d9"
)
OLD_FACTOR = "intraday_market_correlation_resolution_119p"
ADMITTED_FACTOR = "intraday_market_dispersion_decoupling_238m"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN030_RUNNER) != CAMPAIGN030_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign030 orchestration fingerprint changed")

_source = CAMPAIGN030_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign030", "Campaign031"),
    ("campaign030", "campaign031"),
    ("campaign_030", "campaign_031"),
    ("wf030", "wf031"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign031_generated",
}
exec(compile(_source, str(CAMPAIGN030_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign031Error = _generated["Campaign031Error"]
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
