"""Current transition tests after Campaign055 v1 publication."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from scripts import a_share_three_day_preregistration_binding_validator as validator


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/Volumes/DIsk/qlib-a-share-tushare-1m")
V1 = DATA_ROOT / (
    "derived/a_share/rich/tushare/minute_walkforward_campaign055_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_walkforward_campaign055_feature_library_v1/"
    "snapshot_manifest.json"
)
V2 = DATA_ROOT / (
    "derived/a_share/rich/tushare/minute_walkforward_campaign055_feature_library/"
    "tushare_stk_mins_1m_2019_2025_ea0cbb8f_walkforward_campaign055_feature_library_v2/"
    "snapshot_manifest.json"
)
REPAIR = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_055_snapshot_v1_protocol_evidence_failure_repair_20260804.json"
PRESTATE_FAILURE = REPO_ROOT / "docs/a_share_three_day_walkforward_campaign_055_post_v1_frozen_prestate_test_failure_20260804.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_campaign055_v1_is_preserved_and_explicitly_rejected_for_downstream() -> None:
    manifest = _load(V1)
    repair = _load(REPAIR)
    assert _sha256(V1) == (
        "6cbdfafb216c3064271c8eba301ce85dfa2ed27d14afb4073e96aff62be445b6"
    )
    assert manifest["dataset_sha256"] == (
        "cfcdcd23267207f1a2190086b034105c447d5570549864d5468949ea05543882"
    )
    assert manifest["partitions"] == 33015
    assert manifest["rows"] == 7724498
    assert manifest["factor_eligible_rows"][
        "intraday_price_update_clock_entropy_10b_238m"
    ] == 7664125
    assert "campaign006_no_return_preregistration_sha256" in manifest[
        "protocol_evidence"
    ]
    assert repair["failure"]["v1_allowed_for_coverage_comparison_or_return_diagnostics"] is False
    assert repair["v1_value_evidence"]["all_partition_byte_and_frame_hashes_valid"] is True


def test_campaign055_repair_records_have_live_bindings() -> None:
    for path in (REPAIR, PRESTATE_FAILURE):
        result = validator.validate_record(path, data_root=DATA_ROOT)
        assert result["all_bindings_passed"] is True
        assert result["failed_binding_count"] == 0


def test_campaign055_v2_is_absent_or_contains_only_current_campaign_evidence() -> None:
    if not V2.is_file():
        return
    manifest = _load(V2)
    stale = [
        key
        for key in manifest["protocol_evidence"]
        if re.match(r"^campaign\d{3}_", key)
        and not key.startswith("campaign055_")
    ]
    assert stale == []
    assert manifest["partitions"] == 33015
    assert manifest["rows"] == 7724498
    assert manifest["comparison_factor_values_read"] is False
    assert manifest["daily_price_fields_read"] == []
    assert manifest["forward_return_fields_read"] is False
