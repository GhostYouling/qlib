#!/usr/bin/env python3
"""Run Campaign118's exact one-trial 2019-2023 historical walk-forward."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


_TEMPLATE_PATH = (
    Path(__file__).resolve().parent / "a_share_three_day_walkforward_campaign117.py"
)
_TEMPLATE_SHA256 = "5d80f88d673ea452793332d5ecedbba259b3fa01dff331386b0a648e78ffed5b"


def _template_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _template_sha256(_TEMPLATE_PATH) != _TEMPLATE_SHA256:
    raise RuntimeError("frozen Campaign117 development-runner template changed")


_source = _TEMPLATE_PATH.read_text(encoding="utf-8")
for _old, _new in (
    (
        "intraday_amount_weak_order_entropy_236t",
        "intraday_top_decile_amount_event_spacing_entropy_25g",
    ),
    (
        "cb5d77b8fe81fce0464b1c3fe7d93ab345d9b7b1a78f045447e0bf2b6197f084",
        "0cf2d60e8a2bbeb3fbbef2993207f8e52e72377a6a3d3acf7be11141fe8d06a4",
    ),
    (
        "114bb5dd2ac28d8e51e6a35c234cfe06f7d3810b4d7c46303e38af33d4566879",
        "194c2ef2f81c1906c3e94a85e26ce97d7d82dba567b54128cf6e9086e3a027bd",
    ),
    (
        "4f5bf6ee2c26f6956178d6954aae92821530c90a6334375e8cf0e9938fa71c18",
        "19495eb562683e1e14fbe5e9a9730e6d614b481f7642c3da824ea36fdb4d5e2b",
    ),
    (
        'audit.get("numeric_comparisons_passed") == 134',
        'audit.get("numeric_comparisons_passed") == 135',
    ),
    ("Campaign117", "Campaign118"),
    ("campaign117", "campaign118"),
    ("campaign_117", "campaign_118"),
    ("wf117", "wf118"),
):
    if _old not in _source:
        raise RuntimeError(
            f"Campaign118 development transformation token absent: {_old!r}"
        )
    _source = _source.replace(_old, _new)


_implementation: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign118_implementation",
}
exec(compile(_source, str(_TEMPLATE_PATH), "exec"), _implementation)
for _name, _value in _implementation.items():
    if _name not in {"__builtins__", "__file__", "__name__"}:
        globals()[_name] = _value


if __name__ == "__main__":
    raise SystemExit(main())
