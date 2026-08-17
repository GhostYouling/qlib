#!/usr/bin/env python3
"""Run Campaign121's exact one-trial 2019-2023 historical walk-forward."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


_TEMPLATE_PATH = (
    Path(__file__).resolve().parent / "a_share_three_day_walkforward_campaign119.py"
)
_TEMPLATE_SHA256 = "8277eac7daec2e478aa4b170401ac9a02bb69736f5c92cab77f5629750210c3b"


def _template_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _template_sha256(_TEMPLATE_PATH) != _TEMPLATE_SHA256:
    raise RuntimeError("frozen Campaign119 development-runner template changed")


_source = _TEMPLATE_PATH.read_text(encoding="utf-8")
for _old, _new in (
    (
        "intraday_range_boundary_direction_state_entropy_238p",
        "intraday_terminal_close_direction_first_attainment_240m",
    ),
    (
        "1b62ac7b1289f46f5c8d53971ec63835effaf7189e934b86789bfcefc84a8d45",
        "5dde9c750cc792e74c1e1750703f9c17426acb9e211ae8fdd0d0376365029dcd",
    ),
    (
        "30aaf36f807011891309c969359db26a342f0d87234fdca38df1d43e27d59188",
        "e5789da9896535d8d67e0f0f3a7b2704f41292e4694b127a27999224abfad724",
    ),
    (
        "66eb5902abf806005c2e938b4506d08c3106637b695ae99b2d4e322f55dfbbf2",
        "cb476bcc93e7c88df6e2666af9d60d470c90f8a7670ea4553d2e9b877ab8a5b2",
    ),
    (
        'audit.get("numeric_comparisons_passed") == 136',
        'audit.get("numeric_comparisons_passed") == 138',
    ),
    ("Campaign119", "Campaign121"),
    ("campaign119", "campaign121"),
    ("campaign_119", "campaign_121"),
    ("wf119", "wf121"),
):
    if _old not in _source:
        raise RuntimeError(
            f"Campaign121 development transformation token absent: {_old!r}"
        )
    _source = _source.replace(_old, _new)


_implementation: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign121_implementation",
}
exec(compile(_source, str(_TEMPLATE_PATH), "exec"), _implementation)
for _name, _value in _implementation.items():
    if _name not in {"__builtins__", "__file__", "__name__"}:
        globals()[_name] = _value


if __name__ == "__main__":
    raise SystemExit(_implementation["main"]())
