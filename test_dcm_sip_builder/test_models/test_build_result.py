"""Test module for the `BuildResult` data model."""

from pathlib import Path

from dcm_common.models.data_model import get_model_serialization_test

from dcm_sip_builder.models import BuildResult

test_build_result_json = get_model_serialization_test(
    BuildResult, (
        ((), {}),
        ((Path("."),), {}),
        ((), {"success": True}),
        ((Path("."), True), {}),
    )
)
