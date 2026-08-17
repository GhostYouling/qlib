"""Subprocess-isolated tests for Campaign055 v2 snapshot repair."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_python(source: str) -> dict:
    completed = subprocess.run(
        [sys.executable, "-c", source],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_campaign055_repair_uses_separate_v2_and_preserves_v1() -> None:
    payload = _run_python(
        "import json; "
        "from scripts import a_share_three_day_walkforward_campaign055_features_v5 as r; "
        "print(json.dumps({'run_id':r.runner.OUTPUT_RUN_ID,'root':str(r.runner.output_root(r.runner.DEFAULT_DATA_ROOT)),"
        "'v1_hash':r.runner._sha256(r.FAILED_V1_SNAPSHOT)},sort_keys=True))"
    )
    assert payload["run_id"].endswith("campaign055_feature_library_v2")
    assert payload["root"].endswith("campaign055_feature_library_v2")
    assert payload["v1_hash"] == (
        "6cbdfafb216c3064271c8eba301ce85dfa2ed27d14afb4073e96aff62be445b6"
    )


def test_campaign055_repair_removes_only_stale_numbered_campaign_evidence() -> None:
    payload = _run_python(
        "import json; "
        "from scripts import a_share_three_day_walkforward_campaign055_features_v5 as r; "
        "print(json.dumps(r.clean_protocol_evidence({'campaign006_no_return_preregistration_sha256':'stale',"
        "'campaign054_no_return_preregistration_sha256':'stale','campaign055_no_return_preregistration_sha256':'current',"
        "'candidate49_no_return_protocol_sha256':'kept'}),sort_keys=True))"
    )
    assert payload == {
        "campaign055_no_return_preregistration_sha256": "current",
        "candidate49_no_return_protocol_sha256": "kept",
    }


def test_campaign055_snapshot_repair_authorization_bindings_pass() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/a_share_three_day_preregistration_binding_validator.py",
            "--data-root",
            "/Volumes/DIsk/qlib-a-share-tushare-1m",
            "docs/a_share_three_day_walkforward_campaign_055_snapshot_v1_protocol_evidence_failure_repair_20260804.json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["all_bindings_passed"] is True
    assert payload["reports"][0]["binding_count"] == 7
