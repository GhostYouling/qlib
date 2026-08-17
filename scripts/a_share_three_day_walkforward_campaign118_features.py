#!/usr/bin/env python3
"""Build Campaign118's frozen amount-event spacing snapshot without returns."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


_TEMPLATE_PATH = (
    Path(__file__).resolve().parent
    / "a_share_three_day_walkforward_campaign117_features.py"
)
_TEMPLATE_SHA256 = "7b9edced1298e69c29cd20699087cf9695d94f1ba01909b9b081365f55c5d197"


def _template_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _template_sha256(_TEMPLATE_PATH) != _TEMPLATE_SHA256:
    raise RuntimeError("frozen Campaign117 feature-builder template changed")


_source = _TEMPLATE_PATH.read_text(encoding="utf-8")
for _old, _new in (
    (
        "Build Campaign117's frozen amount weak-order entropy snapshot without returns.",
        "Build Campaign118's frozen top-decile amount-event spacing entropy snapshot without returns.",
    ),
    (
        "intraday_amount_weak_order_entropy_236t",
        "intraday_top_decile_amount_event_spacing_entropy_25g",
    ),
    (
        "normalized Shannon entropy over the frozen 13-state exact weak-order "
        '"\n    "distribution of 118 morning plus 118 afternoon overlapping raw-amount triples',
        "normalized Shannon entropy over the frozen 25 edge and inter-event "
        '"\n    "gaps induced by the top 24 raw-amount bars on the 240-bar clock',
    ),
    ("amount weak-order entropy", "top-decile amount-event spacing entropy"),
    (
        "extract_amount_weak_order_entropy",
        "extract_top_decile_amount_event_spacing_entropy",
    ),
    (
        "formula.compute_amount_weak_order_entropy",
        "formula.compute_top_decile_amount_event_spacing_entropy",
    ),
    ("amount_weak_order_entropy", "top_decile_amount_event_spacing_entropy"),
    ("attach_entropy_values", "attach_event_spacing_values"),
    ("recognized_state_observations", "zero_gap_observations"),
    ("exact_tie_triple_observations", "exact_top24_boundary_tie_rows"),
    ("weak_order_state_count", "event_count"),
    (
        "amount_magnitude_used_after_ordinal_encoding",
        "amount_magnitude_used_after_event_selection",
    ),
    (
        "a_share_three_day_walkforward_campaign116_features as c116",
        "a_share_three_day_walkforward_campaign117_features as c117",
    ),
    ("c116.reconstruct_comparisons()", "c117.reconstruct_comparisons()"),
    (
        "items = [dict(item) for item in c117.reconstruct_comparisons()]",
        "items = [dict(item) for item in c117.reconstruct_comparisons()]\n"
        '    items.append({"name": c117.FACTOR_NAME, "score_direction": "higher"})',
    ),
    (
        "c116.reconstruct_complete_definitions()",
        "c117.reconstruct_complete_definitions()",
    ),
    (
        "01cda2c9ec8646ca3d8db86f20e2720514c26c0a6a6044faeac01e6420f9fcb7",
        "f17d9feff0a812d7b7dad06cd24b2891e0d76d0a67e2b7e98dba4f74ae1d31ec",
    ),
    (
        "c42b5d7624c48964cdc95605bf439b18664b1a8912622b0c7a888d8676988407",
        "a74cc3bfb1fab8df65a747a9b3db6fc15f314e1bb8761d8c3a8750edf2958777",
    ),
    (
        "a9d44ce8b383a9ecb29f96b8df19ac1bc28e7cceaac8397c609be6130e4ef03b",
        "b7ef1a9c855c24e48aa161f47c5b7334b0861db9a0aeda3275d457586e608159",
    ),
    ("numeric_policy_v104", "numeric_policy_v106"),
    ("NUMERIC_COMPARATOR_COUNT = 134", "NUMERIC_COMPARATOR_COUNT = 135"),
    (
        "31d788db467f558a0ac538315343090f1b3ad4cb27a26136a49ebaa88b2fdbf2",
        "50323aed7e13a7f0241677beefda6c847482844eea68cf51cb92c833cd316322",
    ),
    (
        "f7612c7dd7d4a0c015146d60a86e244d91b21a8b6638e4f84e7a18d035581d21",
        "077e6c79356fe70193df4d424a004de5734ea395ef06df52e11e3804915d56f7",
    ),
    (
        "ed61b10f3acb939c10ae5759f33aafde377cc921dd99c642300603b50a4851c5",
        "f7612c7dd7d4a0c015146d60a86e244d91b21a8b6638e4f84e7a18d035581d21",
    ),
    ("COMPLETE_DEFINITION_COUNT = 143", "COMPLETE_DEFINITION_COUNT = 144"),
    (
        "PRIOR_COMPLETE_DEFINITION_COUNT = 142",
        "PRIOR_COMPLETE_DEFINITION_COUNT = 143",
    ),
    (
        "_source.replace('\"event_count\": 0', '\"event_count\": 13')",
        "_source.replace('\"event_count\": 0', '\"event_count\": 24')",
    ),
    ('tests.get("passed") == 16', 'tests.get("passed") == 17'),
    ("Campaign117", "Campaign118"),
    ("campaign117", "campaign118"),
    ("campaign_117", "campaign_118"),
):
    if _old not in _source:
        raise RuntimeError(f"Campaign118 feature transformation token absent: {_old!r}")
    _source = _source.replace(_old, _new)


_implementation: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign118_features_implementation",
}
exec(compile(_source, str(_TEMPLATE_PATH), "exec"), _implementation)
from scripts import (  # noqa: E402
    a_share_three_day_walkforward_campaign117_features as _prior_features,
)

_implementation["c117"] = _prior_features
for _name, _value in _implementation.items():
    if _name not in {"__builtins__", "__file__", "__name__"}:
        globals()[_name] = _value


if __name__ == "__main__":
    raise SystemExit(main())
