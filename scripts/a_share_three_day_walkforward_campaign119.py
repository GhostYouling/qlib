#!/usr/bin/env python3
"""Run Campaign119's exact one-trial 2019-2023 historical walk-forward."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


_TEMPLATE_PATH = (
    Path(__file__).resolve().parent / "a_share_three_day_walkforward_campaign118.py"
)
_TEMPLATE_SHA256 = "6ed993342ed8d5be9c0cd8e4703981196f6e4734e0b6ed19ace4dc0d045cc93f"


def _template_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _template_sha256(_TEMPLATE_PATH) != _TEMPLATE_SHA256:
    raise RuntimeError("frozen Campaign118 development-runner template changed")


_source = _TEMPLATE_PATH.read_text(encoding="utf-8")
for _old, _new in (
    (
        "intraday_top_decile_amount_event_spacing_entropy_25g",
        "intraday_range_boundary_direction_state_entropy_238p",
    ),
    (
        "0cf2d60e8a2bbeb3fbbef2993207f8e52e72377a6a3d3acf7be11141fe8d06a4",
        "1b62ac7b1289f46f5c8d53971ec63835effaf7189e934b86789bfcefc84a8d45",
    ),
    (
        "194c2ef2f81c1906c3e94a85e26ce97d7d82dba567b54128cf6e9086e3a027bd",
        "30aaf36f807011891309c969359db26a342f0d87234fdca38df1d43e27d59188",
    ),
    (
        "19495eb562683e1e14fbe5e9a9730e6d614b481f7642c3da824ea36fdb4d5e2b",
        "66eb5902abf806005c2e938b4506d08c3106637b695ae99b2d4e322f55dfbbf2",
    ),
    (
        'audit.get("numeric_comparisons_passed") == 135',
        'audit.get("numeric_comparisons_passed") == 136',
    ),
    ("Campaign118", "Campaign119"),
    ("campaign118", "campaign119"),
    ("campaign_118", "campaign_119"),
    ("wf118", "wf119"),
):
    if _old not in _source:
        raise RuntimeError(
            f"Campaign119 development transformation token absent: {_old!r}"
        )
    _source = _source.replace(_old, _new)


_implementation: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign119_implementation",
}
exec(compile(_source, str(_TEMPLATE_PATH), "exec"), _implementation)
for _name, _value in _implementation.items():
    if _name not in {"__builtins__", "__file__", "__name__"}:
        globals()[_name] = _value


if __name__ == "__main__":
    raise SystemExit(_implementation["main"]())
