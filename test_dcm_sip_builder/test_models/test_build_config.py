"""Test module for the `BuildConfig` data model."""

from pathlib import Path
from dcm_common.models.data_model import get_model_serialization_test

from dcm_sip_builder.models import Target, BuildConfig


test_build_config_json = get_model_serialization_test(
    BuildConfig, (
        ((Target(Path(".")),), {}),
    )
)
