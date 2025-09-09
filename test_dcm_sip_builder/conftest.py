from pathlib import Path

import pytest
from dcm_common.services.tests import (
    fs_setup,
    fs_cleanup,
    wait_for_report,
    external_service,
    run_service,
)

from dcm_sip_builder.config import AppConfig


@pytest.fixture(scope="session", name="file_storage")
def _file_storage():
    return Path("test_dcm_sip_builder/file_storage")


@pytest.fixture(scope="session", name="fixtures")
def _fixtures():
    return Path("test_dcm_sip_builder/fixtures")


@pytest.fixture(scope="session", autouse=True)
def disable_extension_logging():
    """
    Disables the stderr-logging via the helper method `print_status`
    of the `dcm_common.services.extensions`-subpackage.
    """
    # pylint: disable=import-outside-toplevel
    from dcm_common.services.extensions.common import PrintStatusSettings

    PrintStatusSettings.silent = True


@pytest.fixture(name="testing_config")
def _testing_config(file_storage):
    """Returns test-config"""

    # setup config-class
    class TestingConfig(AppConfig):
        TESTING = True
        FS_MOUNT_POINT = file_storage
        CUSTOM_FIXITY_SHA512_PLUGIN_NAME = "CustomFixitySHA512Plugin"
        ORCHESTRA_DAEMON_INTERVAL = 0.01
        ORCHESTRA_WORKER_INTERVAL = 0.01
        ORCHESTRA_WORKER_ARGS = {"messages_interval": 0.01}

    return TestingConfig
