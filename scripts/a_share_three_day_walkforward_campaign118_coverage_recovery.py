#!/usr/bin/env python3
"""Run Campaign118 coverage with the frozen recovered snapshot verifier."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


_TEMPLATE_PATH = (
    Path(__file__).resolve().parent
    / "a_share_three_day_walkforward_campaign117_coverage_recovery.py"
)
_TEMPLATE_SHA256 = "2317174e0269f782127355405b74183465c539781b4a224fbe0e47f2f649442c"


def _template_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _template_sha256(_TEMPLATE_PATH) != _TEMPLATE_SHA256:
    raise RuntimeError("frozen Campaign117 coverage-recovery template changed")


_source = _TEMPLATE_PATH.read_text(encoding="utf-8")
for _old, _new in (
    (
        "8ea3a1b2e0cc369ea6a1192304af101b54fecdfebc5334fa199dbe53807331a5",
        "b52f08b0b7b24b8c4dc5579f0105e1c14f02b0bc935387dbe509297f4cd2bbdf",
    ),
    (
        "0dafa52aa8e39f6b42f93c4142198bfde16ffe2f94ff69ee2a18140be3a21ef4",
        "4f201547304309d4aa98c0a5a21bc47c2a4cc7297b57a76227709f7d81985672",
    ),
    (
        "84c992169fa5cfbbc9babd305a19452a695609df36cd4beab72956d35c414b9c",
        "1474597355146439dc7d45b30ce24032076b78bfd694a6c30060c55d125da1d6",
    ),
    ("all_134", "all_135"),
    ("all-134", "all-135"),
    ("Campaign117", "Campaign118"),
    ("campaign117", "campaign118"),
    ("campaign_117", "campaign_118"),
):
    if _old not in _source:
        raise RuntimeError(
            f"Campaign118 coverage transformation token absent: {_old!r}"
        )
    _source = _source.replace(_old, _new)


_implementation: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign118_coverage_recovery_implementation",
}
exec(compile(_source, str(_TEMPLATE_PATH), "exec"), _implementation)
for _name, _value in _implementation.items():
    if _name not in {"__builtins__", "__file__", "__name__"}:
        globals()[_name] = _value


if __name__ == "__main__":
    raise SystemExit(main())
