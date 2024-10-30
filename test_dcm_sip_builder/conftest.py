from pathlib import Path

import pytest
from dcm_common.services.tests import fs_setup, fs_cleanup, \
    wait_for_report, external_service, run_service

from dcm_sip_builder import app_factory
from dcm_sip_builder.config import AppConfig


@pytest.fixture(scope="session", name="file_storage")
def _file_storage():
    return Path("test_dcm_sip_builder/file_storage/")


@pytest.fixture(scope="session", name="fixtures")
def _fixtures():
    return Path("test_dcm_sip_builder/fixtures/")


@pytest.fixture(name="testing_config")
def _testing_config(file_storage):
    """Returns test-config"""
    # setup config-class
    class TestingConfig(AppConfig):
        ORCHESTRATION_AT_STARTUP = False
        ORCHESTRATION_DAEMON_INTERVAL = 0.001
        ORCHESTRATION_ORCHESTRATOR_INTERVAL = 0.001
        ORCHESTRATION_ABORT_NOTIFICATIONS_STARTUP_INTERVAL = 0.01
        TESTING = True
        FS_MOUNT_POINT = file_storage

    return TestingConfig


@pytest.fixture(name="client")
def _client(testing_config):
    """
    Returns test_client.
    """

    return app_factory(testing_config()).test_client()
