#!/usr/bin/env python3
"""Run Campaign128's exact one-trial 2019-2023 historical walk-forward."""

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
        "intraday_transaction_price_dispersion_resolution_2h",
    ),
    (
        "1b62ac7b1289f46f5c8d53971ec63835effaf7189e934b86789bfcefc84a8d45",
        "7661112a503f8930cba5fd79c03815b8c830d39f98703746362b85b37fa14cef",
    ),
    (
        "30aaf36f807011891309c969359db26a342f0d87234fdca38df1d43e27d59188",
        "6ddc6358bffbfd6ae412744e96479b7bc6bc179ee0ae20cff9b3cb3e85b86e2f",
    ),
    (
        "66eb5902abf806005c2e938b4506d08c3106637b695ae99b2d4e322f55dfbbf2",
        "4644fdbf8ddbd046def730c9eaf848fdc56874f617ea2aefb50dedcffbc9bb4f",
    ),
    (
        'audit.get("numeric_comparisons_passed") == 136',
        'audit.get("numeric_comparisons_passed") == 139',
    ),
    ("Campaign119", "Campaign128"),
    ("campaign119", "campaign128"),
    ("campaign_119", "campaign_128"),
    ("wf119", "wf128"),
):
    if _old not in _source:
        raise RuntimeError(
            f"Campaign128 development transformation token absent: {_old!r}"
        )
    _source = _source.replace(_old, _new)


_implementation: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign128_implementation",
}
exec(compile(_source, str(_TEMPLATE_PATH), "exec"), _implementation)  # noqa: S102
for _name, _value in _implementation.items():
    if _name not in {"__builtins__", "__file__", "__name__"}:
        globals()[_name] = _value


if __name__ == "__main__":
    raise SystemExit(_implementation["main"]())
