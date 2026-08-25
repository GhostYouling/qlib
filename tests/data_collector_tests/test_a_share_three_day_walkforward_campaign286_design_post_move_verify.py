from __future__ import annotations

import copy

import pytest

from scripts import a_share_three_day_walkforward_campaign286_design as base
from scripts import (
    a_share_three_day_walkforward_campaign286_design_post_move_verify as verifier,
)


def test_published_documents_match_frozen_semantics() -> None:
    manifest = base.load_json(verifier.MANIFEST_PATH)
    audit = base.load_json(verifier.AUDIT_PATH)

    verifier.document_semantics(manifest, audit)


def test_document_semantics_rejects_a_threshold_change() -> None:
    manifest = base.load_json(verifier.MANIFEST_PATH)
    audit = copy.deepcopy(base.load_json(verifier.AUDIT_PATH))
    audit["coverage"]["thresholds"]["p05_eligible_names_minimum"] = 49.0

    with pytest.raises(verifier.Campaign286PostMoveVerifyError):
        verifier.document_semantics(manifest, audit)
