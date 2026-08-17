#!/usr/bin/env python3
"""Verify Campaign118's existing snapshot after a metadata-only verifier mismatch."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


_TEMPLATE_PATH = (
    Path(__file__).resolve().parent
    / "a_share_three_day_walkforward_campaign117_snapshot_verify_recovery.py"
)
_TEMPLATE_SHA256 = "0dafa52aa8e39f6b42f93c4142198bfde16ffe2f94ff69ee2a18140be3a21ef4"


def _template_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _template_sha256(_TEMPLATE_PATH) != _TEMPLATE_SHA256:
    raise RuntimeError("frozen Campaign117 snapshot-verifier template changed")


_source = _TEMPLATE_PATH.read_text(encoding="utf-8")
for _old, _new in (
    (
        "114bb5dd2ac28d8e51e6a35c234cfe06f7d3810b4d7c46303e38af33d4566879",
        "194c2ef2f81c1906c3e94a85e26ce97d7d82dba567b54128cf6e9086e3a027bd",
    ),
    (
        "4f5bf6ee2c26f6956178d6954aae92821530c90a6334375e8cf0e9938fa71c18",
        "19495eb562683e1e14fbe5e9a9730e6d614b481f7642c3da824ea36fdb4d5e2b",
    ),
    (
        "aed04a80f21f5e1a6ed2e5a3f51446943a0f924f95d788f2e03a5014f1c3129e",
        "b9115e4b23c8cf4d48ef6bc6a22833d4c6f0924cb06f42919b89ca62192b941a",
    ),
    ("weak_order_state_count", "event_count"),
    ('manifest.get("event_count") == 13', 'manifest.get("event_count") == 24'),
    (
        "amount_magnitude_used_after_ordinal_encoding",
        "amount_magnitude_used_after_event_selection",
    ),
    ("recognized_state_observations", "zero_gap_observations"),
    ("Campaign117", "Campaign118"),
    ("campaign117", "campaign118"),
    ("campaign_117", "campaign_118"),
):
    if _old not in _source:
        raise RuntimeError(
            f"Campaign118 recovery transformation token absent: {_old!r}"
        )
    _source = _source.replace(_old, _new)


_implementation: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign118_snapshot_verify_recovery_implementation",
}
exec(compile(_source, str(_TEMPLATE_PATH), "exec"), _implementation)
for _name, _value in _implementation.items():
    if _name not in {"__builtins__", "__file__", "__name__"}:
        globals()[_name] = _value


if __name__ == "__main__":
    raise SystemExit(main())
