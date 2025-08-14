"""Test-module for build-endpoint."""

from unittest.mock import patch
from pathlib import Path

import pytest

from dcm_sip_builder import app_factory


@pytest.fixture(name="minimal_request_body")
def _minimal_request_body():
    return {
        "build": {
            "target": {
                "path": str("test_ip")
            },
        },
    }


def test_build_minimal(
    client, minimal_request_body, testing_config, wait_for_report
):
    """Test basic functionality of /build-POST endpoint."""

    # submit job
    response = client.post(
        "/build",
        json=minimal_request_body
    )
    assert client.put("/orchestration?until-idle", json={}).status_code == 200

    assert response.status_code == 201
    assert response.mimetype == "application/json"
    token = response.json["value"]

    # wait until job is completed
    json = wait_for_report(client, token)

    assert (testing_config.FS_MOUNT_POINT / json["data"]["path"]).is_dir()
    assert json["data"]["success"]


@pytest.mark.parametrize(
    "dcxml_active",
    [True, False],
    ids=["dcxml_active", "dcxml_inactive"]
)
@pytest.mark.parametrize(
    "iexml_active",
    [True, False],
    ids=["iexml_active", "iexml_inactive"]
)
def test_build_validation_active(
    testing_config, minimal_request_body, wait_for_report,
    iexml_active, dcxml_active,
):
    """
    Test performing /build-POST with and without validation
    """

    # setup
    testing_config.VALIDATION_ROSETTA_METS_ACTIVE = iexml_active
    testing_config.VALIDATION_DCXML_ACTIVE = dcxml_active
    client = app_factory(testing_config(), block=True).test_client()

    # submit job and wait until job is completed
    response = client.post(
        "/build",
        json=minimal_request_body
    )
    assert client.put("/orchestration?until-idle", json={}).status_code == 200

    assert response.status_code == 201
    json = wait_for_report(client, response.json["value"])

    log = str(json["log"])
    assert (testing_config.VALIDATION_ROSETTA_XSD_NAME in log) == iexml_active
    assert (testing_config.VALIDATION_DCXML_NAME in log) == dcxml_active


def test_build_error_in_compiler(
    client, minimal_request_body, testing_config, wait_for_report
):
    """Test whether build is executed despite error in compiler."""

    class _IP:
        baginfo = {
            "Source-Organization": "source",
            "Origin-System-Identifier": "origin",
            # "External-Identifier": "external",
            "DC-Title": "title"
        }
        path = Path(minimal_request_body["build"]["target"]["path"])
        source_metadata = None
        dc_xml = None
        significant_properties = None
        payload_files = {}
        manifests = {}

    with patch(
        "dcm_sip_builder.views.build.IP",
        return_value=_IP
    ):
        # submit job
        token = client.post(
            "/build",
            json=minimal_request_body
        ).json["value"]
        assert client.put("/orchestration?until-idle", json={}).status_code == 200

        # wait until job is completed
        json = wait_for_report(client, token)

        # error occurred
        assert any(
            "External-Identifier" in msg["body"]
            and "ie.xml Compiler" in msg["origin"]
            for msg in json["log"]["ERROR"]
        )

        # sip exists
        sip = testing_config.FS_MOUNT_POINT / json["data"]["path"]
        assert sip.is_dir()
        assert (sip / "dc.xml").is_file()
        assert (sip / "content" / "ie.xml").is_file()
        assert (sip / "content" / "streams").is_dir()
