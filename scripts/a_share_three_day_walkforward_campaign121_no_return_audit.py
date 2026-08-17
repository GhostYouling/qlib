#!/usr/bin/env python3
"""Run Campaign121's frozen coverage-first no-return audit."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


_TEMPLATE_PATH = (
    Path(__file__).resolve().parent
    / "a_share_three_day_walkforward_campaign119_no_return_audit.py"
)
_TEMPLATE_SHA256 = "6974455765f7f621ad4676cd12026242e28d6bef1a2de8239bdbcb9604c219ff"


def _template_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _template_sha256(_TEMPLATE_PATH) != _TEMPLATE_SHA256:
    raise RuntimeError("frozen Campaign119 coverage-audit template changed")


_source = _TEMPLATE_PATH.read_text(encoding="utf-8")
for _old, _new in (
    ("all 136", "all 138"),
    ("all_136", "all_138"),
    ("all-136", "all-138"),
    (
        'record.get("numeric_comparator_count") == 136',
        'record.get("numeric_comparator_count") == 138',
    ),
    ("Campaign119", "Campaign121"),
    ("campaign119", "campaign121"),
    ("campaign_119", "campaign_121"),
):
    if _old not in _source:
        raise RuntimeError(f"Campaign121 audit transformation token absent: {_old!r}")
    _source = _source.replace(_old, _new)


_implementation: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign121_no_return_audit_implementation",
}
exec(compile(_source, str(_TEMPLATE_PATH), "exec"), _implementation)
for _name, _value in _implementation.items():
    if _name not in {"__builtins__", "__file__", "__name__"}:
        globals()[_name] = _value


if __name__ == "__main__":
    raise SystemExit(_implementation["main"]())
