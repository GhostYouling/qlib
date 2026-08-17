import ast
from pathlib import Path

import numpy as np

from scripts import a_share_three_day_walkforward_campaign132_v3 as recovery


def test_v3_binds_unchanged_frozen_v2_runner() -> None:
    assert (
        recovery.frozen_v1.file_sha256(recovery.FROZEN_V2_RUNNER)
        == recovery.FROZEN_V2_RUNNER_SHA256
    )


def test_support_state_exactly_matches_frozen_design_semantics() -> None:
    matrix = np.ones((3, 140), dtype=np.float32)
    matrix[0, :35] = np.nan
    matrix[1, :36] = np.nan
    count, eligible = recovery.support_state(matrix)
    assert count.tolist() == [105, 104, 140]
    assert eligible.tolist() == [True, False, True]


def test_v3_resolves_every_frozen_v1_design_attribute_reference() -> None:
    recovery.configure_runtime()
    tree = ast.parse(recovery.frozen_v2.FROZEN_V1_RUNNER.read_text(encoding="utf-8"))
    references = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "design"
    }
    missing = sorted(
        name for name in references if not hasattr(recovery.frozen_v1.design, name)
    )
    assert missing == []


def test_v3_uses_new_output_freeze_test_and_failure_binding() -> None:
    recovery.configure_runtime()
    assert recovery.frozen_v1.DEFAULT_OUTPUT_ROOT == recovery.V3_OUTPUT_ROOT
    assert (
        recovery.frozen_v1.DEFAULT_IMPLEMENTATION_FREEZE
        == recovery.V3_IMPLEMENTATION_FREEZE
    )
    assert recovery.frozen_v1.TEST_PATH == recovery.V3_TEST_PATH
    assert (
        recovery.frozen_v1._implementation_freeze
        is recovery.validate_v3_implementation_freeze
    )
    assert recovery.frozen_v1.INFRASTRUCTURE_FAILURES[-1] == recovery.V2_FAILURE
    args = recovery.frozen_v1.parser().parse_args(["status"])
    assert Path(args.output_root) == recovery.V3_OUTPUT_ROOT
