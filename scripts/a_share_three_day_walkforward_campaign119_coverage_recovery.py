#!/usr/bin/env python3
"""Run Campaign119 coverage with the frozen recovered snapshot verifier."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


_TEMPLATE_PATH = (
    Path(__file__).resolve().parent
    / "a_share_three_day_walkforward_campaign118_coverage_recovery.py"
)
_TEMPLATE_SHA256 = "5904e7b27fcddbd2260c8a0cc8cd73f4e5ade3d2fd00f5c9da622cadadc18c57"


def _template_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _template_sha256(_TEMPLATE_PATH) != _TEMPLATE_SHA256:
    raise RuntimeError("frozen Campaign118 coverage-recovery template changed")


_source = _TEMPLATE_PATH.read_text(encoding="utf-8")
for _old, _new in (
    (
        "b52f08b0b7b24b8c4dc5579f0105e1c14f02b0bc935387dbe509297f4cd2bbdf",
        "6974455765f7f621ad4676cd12026242e28d6bef1a2de8239bdbcb9604c219ff",
    ),
    (
        "4f201547304309d4aa98c0a5a21bc47c2a4cc7297b57a76227709f7d81985672",
        "748f83aca4467024e093537a5ad131ab98f39b511ae051e91e2ad38d05cf77ee",
    ),
    (
        "1474597355146439dc7d45b30ce24032076b78bfd694a6c30060c55d125da1d6",
        "c1164266f3481d582821b3987ec638ee75cf4908099cbcf264c1084cef27bbea",
    ),
    ("all_135", "all_136"),
    ("all-135", "all-136"),
    ("Campaign118", "Campaign119"),
    ("campaign118", "campaign119"),
    ("campaign_118", "campaign_119"),
):
    if _old not in _source:
        raise RuntimeError(
            f"Campaign119 coverage transformation token absent: {_old!r}"
        )
    _source = _source.replace(_old, _new)


_implementation: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign119_coverage_recovery_implementation",
}
exec(compile(_source, str(_TEMPLATE_PATH), "exec"), _implementation)
for _name, _value in _implementation.items():
    if _name not in {"__builtins__", "__file__", "__name__"}:
        globals()[_name] = _value


if __name__ == "__main__":
    raise SystemExit(_implementation["main"]())
