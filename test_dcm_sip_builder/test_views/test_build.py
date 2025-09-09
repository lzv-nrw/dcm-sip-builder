"""Test-module for build-endpoint."""

from uuid import uuid4
from shutil import copytree

import pytest

from dcm_sip_builder import app_factory


@pytest.fixture(name="minimal_request_body")
def _minimal_request_body():
    return {
        "build": {
            "target": {"path": str("test_ip")},
        },
    }


def test_build_minimal(minimal_request_body, testing_config):
    """Test basic functionality of /build-POST endpoint."""

    app = app_factory(testing_config())
    client = app.test_client()

    # submit job
    response = client.post("/build", json=minimal_request_body)

    assert response.status_code == 201
    assert response.mimetype == "application/json"
    token = response.json["value"]

    # wait until job is completed
    app.extensions["orchestra"].stop(stop_on_idle=True)
    json = client.get(f"/report?token={token}").json

    assert (testing_config.FS_MOUNT_POINT / json["data"]["path"]).is_dir()
    assert json["data"]["success"]


@pytest.mark.parametrize(
    "dcxml_active", [True, False], ids=["dcxml_active", "dcxml_inactive"]
)
@pytest.mark.parametrize(
    "iexml_active", [True, False], ids=["iexml_active", "iexml_inactive"]
)
def test_build_validation_active(
    testing_config,
    minimal_request_body,
    iexml_active,
    dcxml_active,
):
    """
    Test performing /build-POST with and without validation
    """

    # setup
    class ThisConfig(testing_config):
        VALIDATION_ROSETTA_METS_ACTIVE = iexml_active
        VALIDATION_DCXML_ACTIVE = dcxml_active

    app = app_factory(ThisConfig())
    client = app.test_client()

    # submit job and wait until job is completed
    response = client.post("/build", json=minimal_request_body)
    assert response.status_code == 201

    # wait until job is completed
    app.extensions["orchestra"].stop(stop_on_idle=True)
    json = client.get(f"/report?token={response.json['value']}").json

    log = str(json["log"])
    assert (testing_config.VALIDATION_ROSETTA_XSD_NAME in log) == iexml_active
    assert (testing_config.VALIDATION_DCXML_NAME in log) == dcxml_active


def test_build_error_in_compiler(
    minimal_request_body, testing_config, fixtures, file_storage
):
    """Test whether build is executed despite error in compiler."""

    app = app_factory(testing_config())
    client = app.test_client()

    # create fake ip with missing required metadata
    path = file_storage / str(uuid4())
    copytree(fixtures / "test_ip", path)
    (path / "bag-info.txt").write_text(
        "",
        encoding="utf-8",
    )

    minimal_request_body["build"]["target"]["path"] = str(
        path.relative_to(file_storage)
    )
    # submit job
    token = client.post("/build", json=minimal_request_body).json["value"]

    # wait until job is completed
    app.extensions["orchestra"].stop(stop_on_idle=True)
    json = client.get(f"/report?token={token}").json

    # error occurred
    assert any(
        "Source-Organization" in msg["body"]
        and "ie.xml Compiler" in msg["origin"]
        for msg in json["log"]["ERROR"]
    )

    # sip exists
    sip = testing_config.FS_MOUNT_POINT / json["data"]["path"]
    assert sip.is_dir()
    assert (sip / "dc.xml").is_file()
    assert (sip / "content" / "ie.xml").is_file()
    assert (sip / "content" / "streams").is_dir()
