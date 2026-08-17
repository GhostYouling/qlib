import copy
import json

import pytest

from scripts import a_share_three_day_walkforward_campaign110_snapshot_verifier as verifier


def _manifest() -> dict:
    return json.loads(verifier.SNAPSHOT_MANIFEST_PATH.read_text(encoding="utf-8"))


def test_verify_only_protocol_and_published_manifest_metadata_pass() -> None:
    assert verifier.load_protocol()["candidate_snapshot"]["eligible_rows"] == 7724498
    verifier.validate_manifest(_manifest())


@pytest.mark.parametrize(
    ("field", "inherited_value"),
    [
        ("fixed_denominator", 0),
        ("fixed_anchor_and_close_support_required", False),
        ("exact_reference_ties_retained", False),
    ],
)
def test_inherited_campaign105_expectations_fail_closed(
    field: str, inherited_value: object
) -> None:
    manifest = copy.deepcopy(_manifest())
    manifest[field] = inherited_value
    with pytest.raises(
        verifier.candidate.Campaign110FeatureError,
        match="verify-only manifest semantics changed",
    ):
        verifier.validate_manifest(manifest)


def test_verifier_exposes_no_build_entry_point() -> None:
    assert not hasattr(verifier, "build_snapshot")


def test_verifier_requires_exact_state_count_accounting() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["quality"]["equal_reference_bars"] += 1
    with pytest.raises(
        verifier.candidate.Campaign110FeatureError,
        match="verify-only manifest semantics changed",
    ):
        verifier.validate_manifest(manifest)
