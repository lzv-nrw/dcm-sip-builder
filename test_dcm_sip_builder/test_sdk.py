"""
Test module for the package `dcm-sip-builder-sdk`.
"""

from time import sleep

import pytest
import dcm_sip_builder_sdk

from dcm_sip_builder import app_factory


@pytest.fixture(name="app")
def _app(testing_config):
    testing_config.ORCHESTRATION_AT_STARTUP = True
    return app_factory(testing_config(), as_process=True)


@pytest.fixture(name="default_sdk", scope="module")
def _default_sdk():
    return dcm_sip_builder_sdk.DefaultApi(
        dcm_sip_builder_sdk.ApiClient(
            dcm_sip_builder_sdk.Configuration(
                host="http://localhost:8080"
            )
        )
    )


@pytest.fixture(name="build_sdk", scope="module")
def _build_sdk():
    return dcm_sip_builder_sdk.BuildApi(
        dcm_sip_builder_sdk.ApiClient(
            dcm_sip_builder_sdk.Configuration(
                host="http://localhost:8080"
            )
        )
    )


def test_default_ping(
    default_sdk: dcm_sip_builder_sdk.DefaultApi, app, run_service
):
    """Test default endpoint `/ping-GET`."""

    run_service(app, probing_path="ready")

    response = default_sdk.ping()

    assert response == "pong"


def test_default_status(
    default_sdk: dcm_sip_builder_sdk.DefaultApi, app, run_service
):
    """Test default endpoint `/status-GET`."""

    run_service(app, probing_path="ready")

    response = default_sdk.get_status()

    assert response.ready


def test_default_identify(
    default_sdk: dcm_sip_builder_sdk.DefaultApi, app, run_service,
    testing_config
):
    """Test default endpoint `/identify-GET`."""

    run_service(app, probing_path="ready")

    response = default_sdk.identify()

    assert response.to_dict() == testing_config().CONTAINER_SELF_DESCRIPTION


def test_build_report(
    build_sdk: dcm_sip_builder_sdk.BuildApi, app, run_service, testing_config
):
    """Test endpoints `/build-POST` and `/report-GET`."""

    run_service(app, probing_path="ready")

    submission = build_sdk.build(
        {
            "build": {
                "target": {
                    "path": str("test_ip")
                },
            }
        }
    )

    while True:
        try:
            report = build_sdk.get_report(token=submission.value)
            break
        except dcm_sip_builder_sdk.exceptions.ApiException as e:
            assert e.status == 503
            sleep(0.1)
    assert report.data.success
    assert (testing_config().FS_MOUNT_POINT / report.data.path).is_dir()


def test_build_report_404(
    build_sdk: dcm_sip_builder_sdk.BuildApi, app, run_service
):
    """Test build endpoint `/report-GET` without previous submission."""

    run_service(app, probing_path="ready")

    with pytest.raises(dcm_sip_builder_sdk.rest.ApiException) as exc_info:
        build_sdk.get_report(token="some-token")
    assert exc_info.value.status == 404
