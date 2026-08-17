#!/usr/bin/env python3
"""Snapshot-bound Campaign049 ordered no-return audit entrypoint."""

from __future__ import annotations

try:
    import scripts.a_share_three_day_walkforward_campaign049_features_v2 as bound
except ModuleNotFoundError:
    import a_share_three_day_walkforward_campaign049_features_v2 as bound


runner = bound.runner
EXPECTED_BOUND_ENTRYPOINT_SHA256 = (
    "01b045c433d52f919c85df72ac74863ec02232b262a35681fe451221e436266a"
)
EXPECTED_SNAPSHOT_MANIFEST_SHA256 = (
    "6c27933f232926f33d750f624fc6ad32c394c2e97922043502e997275c1ace1d"
)
EXPECTED_SNAPSHOT_DATASET_SHA256 = (
    "c60c1f245e2bbfdd12acdcfdd8417799684fcda09caf4472270d870ba911164c"
)
EXPECTED_SNAPSHOT_BINDING_SHA256 = (
    "d5368739792f00e394905741855c98a692bf923b821bb0b43769954807c6ea2f"
)

if runner._sha256(runner.Path(bound.__file__).resolve()) != EXPECTED_BOUND_ENTRYPOINT_SHA256:
    raise runner.Campaign049FeatureError("Campaign049 bound build entrypoint changed")

runner.SNAPSHOT_MANIFEST_SHA256 = EXPECTED_SNAPSHOT_MANIFEST_SHA256
runner.SNAPSHOT_DATASET_SHA256 = EXPECTED_SNAPSHOT_DATASET_SHA256
runner.SNAPSHOT_PUBLICATION_BINDING_SHA256 = EXPECTED_SNAPSHOT_BINDING_SHA256
runner._install_engine_globals()


if __name__ == "__main__":
    raise SystemExit(runner.main())
