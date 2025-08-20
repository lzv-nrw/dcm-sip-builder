"""
Test module for the `dcm_sip_builder/handlers.py`.
"""

import pytest
from data_plumber_http.settings import Responses

from dcm_sip_builder.models import BuildConfig
from dcm_sip_builder import handlers


@pytest.fixture(name="build_handler")
def _build_handler(fixtures):
    return handlers.get_build_handler(
        fixtures
    )


@pytest.mark.parametrize(
    ("json", "status"),
    (pytest_args := [
        (
            {"no-build": None},
            400
        ),
        (  # missing target
            {"build": {}},
            400
        ),
        (  # missing path
            {"build": {"target": {}}},
            400
        ),
        (
            {"build": {"target": {"path": "test-bag_"}}},
            404
        ),
        (
            {"build": {"target": {"path": "test_ip"}}},
            Responses.GOOD.status
        ),
        (
            {
                "build": {"target": {"path": "test_ip"}},
                "callbackUrl": None
            },
            422
        ),
        (
            {
                "build": {"target": {"path": "test_ip"}},
                "callbackUrl": "no.scheme/path"
            },
            422
        ),
        (
            {
                "build": {"target": {"path": "test_ip"}},
                "callbackUrl": "https://lzv.nrw/callback"
            },
            Responses.GOOD.status
        ),
        (
            {
                "build": {"target": {"path": "test_ip"}},
                "token": "https://lzv.nrw/callback"
            },
            422
        ),
        (
            {
                "build": {"target": {"path": "test_ip"}},
                "token": "non-uuid"
            },
            422
        ),
        (
            {
                "build": {"target": {"path": "test_ip"}},
                "token": "37ee72d6-80ab-4dcd-a68d-f8d32766c80d"
            },
            Responses.GOOD.status
        ),
    ]),
    ids=[f"stage {i+1}" for i in range(len(pytest_args))]
)
def test_build_handler(
    build_handler, json, status, fixtures
):
    "Test `validate_ip_handler`."

    output = build_handler.run(json=json)

    assert output.last_status == status
    if status != Responses.GOOD.status:
        print(output.last_message)
    else:
        assert isinstance(output.data.value["build"], BuildConfig)
        assert fixtures not in output.data.value["build"].target.path.parents
