#!/usr/bin/env python3
"""Run the single frozen Campaign030 three-session walk-forward trial.

Campaign030 reuses the byte-bound Campaign029 orchestration and unchanged
Campaign006 execution engine. Only deterministic campaign namespace and
admitted-factor substitutions are allowed; folds, execution assumptions,
survivor gates, and conditional exposed-stress rules remain inherited.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN029_RUNNER = (
    REPO_ROOT / "scripts" / "a_share_three_day_walkforward_campaign029.py"
)
CAMPAIGN029_RUNNER_SHA256 = (
    "f6dff6062127a3cc6211a92963e337e78bcfdc4992c3bb470ff0d87beceffe48"
)
OLD_FACTOR = "intraday_market_shock_magnitude_decoupling_238m"
ADMITTED_FACTOR = "intraday_market_correlation_resolution_119p"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _sha256(CAMPAIGN029_RUNNER) != CAMPAIGN029_RUNNER_SHA256:
    raise RuntimeError("frozen Campaign029 orchestration fingerprint changed")

_source = CAMPAIGN029_RUNNER.read_text(encoding="utf-8")
for _old, _new in (
    ("Campaign029", "Campaign030"),
    ("campaign029", "campaign030"),
    ("campaign_029", "campaign_030"),
    ("wf029", "wf030"),
    (OLD_FACTOR, ADMITTED_FACTOR),
):
    _source = _source.replace(_old, _new)
_generated: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign030_generated",
}
exec(compile(_source, str(CAMPAIGN029_RUNNER), "exec"), _generated)

base = _generated["base"]
Campaign030Error = _generated["Campaign030Error"]
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
