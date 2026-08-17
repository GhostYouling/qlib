#!/usr/bin/env python3
"""Run Campaign119's frozen coverage-first no-return audit."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


_TEMPLATE_PATH = (
    Path(__file__).resolve().parent
    / "a_share_three_day_walkforward_campaign118_no_return_audit.py"
)
_TEMPLATE_SHA256 = "b52f08b0b7b24b8c4dc5579f0105e1c14f02b0bc935387dbe509297f4cd2bbdf"


def _template_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _template_sha256(_TEMPLATE_PATH) != _TEMPLATE_SHA256:
    raise RuntimeError("frozen Campaign118 coverage-audit template changed")


_source = _TEMPLATE_PATH.read_text(encoding="utf-8")
for _old, _new in (
    ("all 135", "all 136"),
    ("all_135", "all_136"),
    ("all-135", "all-136"),
    (
        'record.get("numeric_comparator_count") == 135',
        'record.get("numeric_comparator_count") == 136',
    ),
    ("Campaign118", "Campaign119"),
    ("campaign118", "campaign119"),
    ("campaign_118", "campaign_119"),
):
    if _old not in _source:
        raise RuntimeError(f"Campaign119 audit transformation token absent: {_old!r}")
    _source = _source.replace(_old, _new)


_implementation: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign119_no_return_audit_implementation",
}
exec(compile(_source, str(_TEMPLATE_PATH), "exec"), _implementation)
for _name, _value in _implementation.items():
    if _name not in {"__builtins__", "__file__", "__name__"}:
        globals()[_name] = _value


if __name__ == "__main__":
    raise SystemExit(_implementation["main"]())
