"""Builder-component test-module."""

from unittest import mock
from uuid import uuid4

import pytest
from dcm_common.util import list_directory_content

from dcm_sip_builder.components import Builder
from dcm_sip_builder.models import IP, SIP


@pytest.mark.parametrize(
    "write_payload",
    [True, False]
)
@pytest.mark.parametrize(
    "write_metadata",
    [True, False]
)
def test_builder_build_fake(write_payload, write_metadata):
    """Test method `build` of `Builder`."""

    class _SIP:
        path = None
        built: bool

    class _IP:
        path = None

    with mock.patch(
        "dcm_sip_builder.components.builder.Builder.write_payload",
        return_value=write_payload
    ), mock.patch(
        "dcm_sip_builder.components.builder.Builder.write_metadata",
        return_value=write_metadata
    ):
        sip = _SIP()
        assert Builder().build(_IP(), "ie-metadata", "dc-metadata", sip) \
            == (write_payload and write_metadata)
        assert sip.built == (write_payload and write_metadata)


def test_builder_build(file_storage):
    """Test method `build` of `Builder`."""

    ip = IP(file_storage / "test_ip")
    sip = SIP(file_storage / "sip" / str(uuid4()))
    sip.path.mkdir(parents=True, exist_ok=False)
    ie = "ie-metadata"
    dc = "dc-metadata"
    builder = Builder()
    result = builder.build(ip, ie, dc, sip)
    assert result
    assert sip.built

    # meta
    assert (sip.path / "content" / "ie.xml").read_text(encoding="utf-8") \
        == ie
    assert (sip.path / "dc.xml").read_text(encoding="utf-8") \
        == dc

    # payload
    ip_files = map(
        lambda x: x.relative_to(ip.path / "data"),
        list_directory_content(
            ip.path / "data",
            pattern="**/*",
            condition_function=lambda p: p.is_file()
        )
    )
    sip_files = map(
        lambda x: x.relative_to(sip.path / "content" / "streams"),
        list_directory_content(
            sip.path / "content" / "streams",
            pattern="**/*",
            condition_function=lambda p: p.is_file()
        )
    )
    assert sorted(ip_files) == sorted(sip_files)
