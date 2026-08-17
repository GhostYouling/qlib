from pathlib import Path

from scripts import a_share_three_day_walkforward_campaign132_v2 as recovery


def test_v2_binds_unchanged_frozen_v1_runner() -> None:
    assert (
        recovery.frozen_v1.file_sha256(recovery.FROZEN_V1_RUNNER)
        == recovery.FROZEN_V1_RUNNER_SHA256
    )


def test_v2_only_repairs_feature_name_helper_and_recovery_paths() -> None:
    recovery.configure_runtime()
    assert (
        recovery.frozen_v1.design.component_columns
        is recovery.frozen_v1.design.feature_names
    )
    assert recovery.frozen_v1.DEFAULT_OUTPUT_ROOT == recovery.V2_OUTPUT_ROOT
    assert (
        recovery.frozen_v1.DEFAULT_IMPLEMENTATION_FREEZE
        == recovery.V2_IMPLEMENTATION_FREEZE
    )
    assert recovery.frozen_v1.TEST_PATH == recovery.V2_TEST_PATH
    assert (
        recovery.frozen_v1._implementation_freeze
        is recovery.validate_v2_implementation_freeze
    )
    assert recovery.frozen_v1.INFRASTRUCTURE_FAILURES[-1] == recovery.V1_FAILURE


def test_v2_parser_defaults_to_new_output_root() -> None:
    recovery.configure_runtime()
    args = recovery.frozen_v1.parser().parse_args(["status"])
    assert Path(args.output_root) == recovery.V2_OUTPUT_ROOT
