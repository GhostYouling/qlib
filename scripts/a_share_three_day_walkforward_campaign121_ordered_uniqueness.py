#!/usr/bin/env python3
"""Run Campaign121's frozen all-138 ordered uniqueness audit without returns."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


_TEMPLATE_PATH = (
    Path(__file__).resolve().parent
    / "a_share_three_day_walkforward_campaign120_ordered_uniqueness.py"
)
_TEMPLATE_SHA256 = "9ddf794394ebd4b26a7eb01f1f6d1499c16ec5baf8786c6e7e45d4298678f7b2"


def _template_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _template_sha256(_TEMPLATE_PATH) != _TEMPLATE_SHA256:
    raise RuntimeError("frozen Campaign120 uniqueness template changed")


_source = _TEMPLATE_PATH.read_text(encoding="utf-8")
_old_tail = """    expected_tail = [
        {
            "name": c119_base.c118_base.c117_base.c110.FACTOR_NAME,
            "score_direction": "higher",
        },
        {
            "name": c119_base.c118_base.c117_candidate.FACTOR_NAME,
            "score_direction": "higher",
        },
        {
            "name": c119_base.c118_candidate.FACTOR_NAME,
            "score_direction": "higher",
        },
        {"name": c119_candidate.FACTOR_NAME, "score_direction": "higher"},
    ]"""
_old_load_block = """    first_results, receipts = (
        c119_base.c118_base.c117_base.c110_v1._load_comparisons_after_coverage(
            coverage={"gate_passed_before_comparison_values": True},
            candidate_keys=keys,
            candidate_values=values,
            gate=gate,
            comparison_engine=comparison_engine,
        )
    )
    if [item["comparison_factor"] for item in first_results] != expected_order[:133]:
        raise Campaign120OrderedUniquenessError("first 133 comparator order changed")
    c110_result, c110_receipt = c119_base.c118_base.c117_base._load_final_comparator(
        candidate_keys=keys,
        candidate_values=values,
        gate=gate,
        comparison_engine=comparison_engine,
    )
    c117_result, c117_receipt = c119_base.c118_base._load_campaign117_comparator(
        candidate_keys=keys,
        candidate_values=values,
        gate=gate,
        comparison_engine=comparison_engine,
    )
    c118_result, c118_receipt = c119_base._load_campaign118_comparator(
        candidate_keys=keys,
        candidate_values=values,
        gate=gate,
        comparison_engine=comparison_engine,
    )
    c119_result, c119_receipt = _load_campaign119_comparator(
        candidate_keys=keys,
        candidate_values=values,
        gate=gate,
        comparison_engine=comparison_engine,
    )
    results = [
        *first_results,
        c110_result,
        c117_result,
        c118_result,
        c119_result,
    ]"""
for _token in (_old_tail, _old_load_block):
    if _source.count(_token) != 1:
        raise RuntimeError("Campaign121 uniqueness template block changed")
_source = _source.replace(_old_tail, "__CAMPAIGN121_EXPECTED_TAIL__")
_source = _source.replace(_old_load_block, "__CAMPAIGN121_LOAD_BLOCK__")

for _old, _new in (
    ("Campaign120", "Campaign121"),
    ("campaign120", "campaign121"),
    ("campaign_120", "campaign_121"),
    ("Campaign119", "Campaign120"),
    ("campaign119", "campaign120"),
    ("campaign_119", "campaign_120"),
    ("c119_candidate", "c120_candidate"),
    ("c119_base", "c120_base"),
    ("c119_verifier", "c120_verifier"),
    ("C119_", "C120_"),
    ("BASE119_", "BASE120_"),
    ("base119_runner_sha256", "base120_runner_sha256"),
    ("all-137", "all-138"),
    ("all_137", "all_138"),
    (
        "all_138_loader_and_gate_runner_frozen_before_comparator_values",
        "all_138_loader_and_gate_runner_recovery_frozen_after_partial_comparator_exposure_before_returns",
    ),
    ("EXPECTED_COMPARISON_COUNT = 137", "EXPECTED_COMPARISON_COUNT = 138"),
    ("definitions[-4:] == expected_tail", "definitions[-5:] == expected_tail"),
    ('test.get("passed") == 4', 'test.get("passed") == 5'),
    ("comparator 137", "comparator 138"),
    ("prior_136_loader_binding", "prior_137_loader_binding"),
    ("comparator_137_manifest_sha256", "comparator_138_manifest_sha256"),
    ("comparator_137_dataset_sha256", "comparator_138_dataset_sha256"),
    (
        "adapter = c120_base.c118_base.c117_base.c110_v1.adapter",
        "adapter = c120_base.c119_base.c118_base.c117_base.c110_v1.adapter",
    ),
    (
        "5fddef525ebe25c038c087ed08dd9433771d09be9e54fc0c27673fe7abd748c5",
        "3fcb61e401b646cf771d48228406898e1a1091d8375a659ed8cac6abc5964cfd",
    ),
    (
        "24e72a08db0c70a98ca7aa6094bbf34a1e37dc94f2575e8aed510afb16e9a539",
        "24e9ec8b73ea35dd804489e789892b24bb87b2c15b987de9b485f24cc8aff51a",
    ),
    (
        "2405dc8a90650bfa69a21b91f670a86578b2d80a9420366fc12068e3839150da",
        _TEMPLATE_SHA256,
    ),
    (
        "7afda9a6312467262fcf67b71d37b5de15f268a1a83adb4a682d077ccae0fae5",
        "8f2e306dece976f619f66b8e41231a5e23ecf61e5449888cf44d6f790b7048dc",
    ),
    (
        "96766e89f07acc2b649c53b751883f2783fe660e376395063d719efd08f6fcdb",
        "7afda9a6312467262fcf67b71d37b5de15f268a1a83adb4a682d077ccae0fae5",
    ),
    (
        "748f83aca4467024e093537a5ad131ab98f39b511ae051e91e2ad38d05cf77ee",
        "290a8f5a3fd20ebcf356d8bcb165c5e5e487cebceb64f084dc287d6cba66d5ee",
    ),
    (
        "a_share_three_day_walkforward_campaign_120_feature_snapshot_binding_20260813.json",
        "a_share_three_day_walkforward_campaign_120_feature_snapshot_verification_result_20260814.json",
    ),
    (
        "a_share_three_day_walkforward_campaign_121_ordered_uniqueness_implementation_freeze_20260814.json",
        "a_share_three_day_walkforward_campaign_121_ordered_uniqueness_implementation_freeze_v4_20260814.json",
    ),
    ("(0.0, 1.0)", "(2.0, 238.0)"),
    (
        'boundary.get("candidate_values_reopened_for_uniqueness_before_freeze")\n        is False',
        'boundary.get("candidate_values_reopened_during_failed_run_before_v4")\n        is True',
    ),
    (
        'boundary.get("comparator_values_read_before_freeze") is False',
        'boundary.get("comparator_values_read_during_failed_run_before_v4") is True',
    ),
):
    if _old not in _source:
        raise RuntimeError(
            f"Campaign121 uniqueness transformation token absent: {_old!r}"
        )
    _source = _source.replace(_old, _new)

_new_tail = """    expected_tail = [
        {
            "name": c120_base.c119_base.c118_base.c117_base.c110.FACTOR_NAME,
            "score_direction": "higher",
        },
        {
            "name": c120_base.c119_base.c118_base.c117_candidate.FACTOR_NAME,
            "score_direction": "higher",
        },
        {
            "name": c120_base.c119_base.c118_candidate.FACTOR_NAME,
            "score_direction": "higher",
        },
        {
            "name": c120_base.c119_candidate.FACTOR_NAME,
            "score_direction": "higher",
        },
        {"name": c120_candidate.FACTOR_NAME, "score_direction": "higher"},
    ]"""
_new_load_block = """    first_results, receipts = (
        c120_base.c119_base.c118_base.c117_base.c110_v1._load_comparisons_after_coverage(
            coverage={"gate_passed_before_comparison_values": True},
            candidate_keys=keys,
            candidate_values=values,
            gate=gate,
            comparison_engine=comparison_engine,
        )
    )
    if [item["comparison_factor"] for item in first_results] != expected_order[:133]:
        raise Campaign121OrderedUniquenessError("first 133 comparator order changed")
    c110_result, c110_receipt = c120_base.c119_base.c118_base.c117_base._load_final_comparator(
        candidate_keys=keys,
        candidate_values=values,
        gate=gate,
        comparison_engine=comparison_engine,
    )
    c117_result, c117_receipt = c120_base.c119_base.c118_base._load_campaign117_comparator(
        candidate_keys=keys,
        candidate_values=values,
        gate=gate,
        comparison_engine=comparison_engine,
    )
    c118_result, c118_receipt = c120_base.c119_base._load_campaign118_comparator(
        candidate_keys=keys,
        candidate_values=values,
        gate=gate,
        comparison_engine=comparison_engine,
    )
    c119_result, c119_receipt = c120_base._load_campaign119_comparator(
        candidate_keys=keys,
        candidate_values=values,
        gate=gate,
        comparison_engine=comparison_engine,
    )
    c120_result, c120_receipt = _load_campaign120_comparator(
        candidate_keys=keys,
        candidate_values=values,
        gate=gate,
        comparison_engine=comparison_engine,
    )
    results = [
        *first_results,
        c110_result,
        c117_result,
        c118_result,
        c119_result,
        c120_result,
    ]"""
_source = _source.replace("__CAMPAIGN121_EXPECTED_TAIL__", _new_tail)
_source = _source.replace("__CAMPAIGN121_LOAD_BLOCK__", _new_load_block)
_source = _source.replace(
    '"comparator_137": c119_receipt,\n            "all_138_sources_loaded_in_frozen_order": True,',
    '"comparator_137": c119_receipt,\n            "comparator_138": c120_receipt,\n            "all_138_sources_loaded_in_frozen_order": True,',
)


_implementation: dict[str, Any] = {
    "__file__": str(Path(__file__).resolve()),
    "__name__": "a_share_three_day_walkforward_campaign121_ordered_uniqueness_implementation",
}
exec(compile(_source, str(_TEMPLATE_PATH), "exec"), _implementation)
for _name, _value in _implementation.items():
    if _name not in {"__builtins__", "__file__", "__name__"}:
        globals()[_name] = _value


if __name__ == "__main__":
    raise SystemExit(_implementation["main"]())
