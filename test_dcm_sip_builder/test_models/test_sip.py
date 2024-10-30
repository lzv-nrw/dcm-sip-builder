"""Test module for the `SIP` data model."""

from pathlib import Path

from dcm_common.models.data_model import get_model_serialization_test

from dcm_sip_builder.models import SIP

test_sip_json = get_model_serialization_test(
    SIP, (
        ((Path("."),), {}),
        ((Path("."), True), {}),
    )
)
