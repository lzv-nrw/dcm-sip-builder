"""
Test module for the `IP` data model.
"""

from pathlib import Path
from uuid import uuid4
from shutil import copytree

import pytest
from lxml import etree as et

from dcm_sip_builder.models import IP


def create_txt_file(file_path: Path, text: str) -> None:
    file_path.write_text(text + "\n", encoding="utf-8")


@pytest.mark.parametrize(
    ("representations", "expected_output_payload_files"),
    [
        (
            ["preservation_master"],
            {
                "preservation_master": [
                    "data/preservation_master/sample2.txt",
                    "data/preservation_master/sample1.txt"
                ]
            }
        ),  # only_preservation_master
        (
            ["preservation_master", "modified_master/1"],
            {
                "preservation_master": [
                    "data/preservation_master/sample1.txt",
                    "data/preservation_master/sample2.txt"
                ],
                "modified_master": {
                    "1": [
                        "data/modified_master/1/sample1.txt",
                        "data/modified_master/1/sample2.txt"
                    ]
                },
            }
        ),  # one_modified_master
        (
            ["preservation_master", "derivative_copy/1"],
            {
                "preservation_master": [
                    "data/preservation_master/sample1.txt",
                    "data/preservation_master/sample2.txt"
                ],
                "derivative_copy": {
                    "1": [
                        "data/derivative_copy/1/sample1.txt",
                        "data/derivative_copy/1/sample2.txt"
                    ]
                },
            }
        ),  # one_derivative_copy
        (
            [
                "preservation_master",
                "modified_master/1",
                "modified_master/2",
                "derivative_copy/1"
            ],
            {
                "preservation_master": [
                    "data/preservation_master/sample1.txt",
                    "data/preservation_master/sample2.txt"
                ],
                "modified_master": {
                    "1": [
                        "data/modified_master/1/sample1.txt",
                        "data/modified_master/1/sample2.txt"
                    ],
                    "2": [
                        "data/modified_master/2/sample1.txt",
                        "data/modified_master/2/sample2.txt"
                    ]
                },
                "derivative_copy": {
                    "1": [
                        "data/derivative_copy/1/sample1.txt",
                        "data/derivative_copy/1/sample2.txt"
                    ]
                },
            }
        ),  # modified_master_and_derivative_copy
    ],
    ids=[
        "only_preservation_master",
        "one_modified_master",
        "one_derivative_copy",
        "modified_master_and_derivative_copy"
    ]
)
def test_payload_files(
    file_storage,
    representations,
    expected_output_payload_files
):
    """
    Test the attribute `payload_files` of an `IP` object.
    """

    # prepare test-ip
    ip_path = file_storage / "ip" / str(uuid4())
    for rep in representations:
        d = ip_path / "data" / rep
        d.mkdir(parents=True)
        # Write two txt files for each representation
        for i in range(1, 3):
            file_path = d / f"sample{i}.txt"
            create_txt_file(
                file_path=file_path,
                text=f"some text {i}"
            )
    # Create IP object from ip_path
    ip = IP(path=ip_path, ignore_errors=True)

    assert ip.payload_files.keys() \
        == expected_output_payload_files.keys()
    for k, v in ip.payload_files.items():
        if isinstance(v, list):
            assert sorted(v) \
                    == sorted(expected_output_payload_files[k])
        else:
            assert isinstance(v, dict)
            assert (
                v.keys()  # pylint: disable=no-member
            ) == expected_output_payload_files[k].keys()
            for rep, files in v.items():  # pylint: disable=no-member
                assert sorted(files) \
                    == sorted(expected_output_payload_files[k][rep])


def test_IP_constructor(file_storage):
    """Test the constructor of model `IP`."""

    ip_path = file_storage / "test_ip"
    ip = IP(ip_path)

    assert hasattr(ip, "path")
    assert ip.path == ip_path

    assert hasattr(ip, "baginfo")
    assert isinstance(ip.baginfo, dict)
    assert len(ip.baginfo) == 11
    assert isinstance(ip.baginfo["DC-Rights"], list)
    assert len(ip.baginfo["DC-Rights"]) == 2

    assert hasattr(ip, "manifests")
    assert isinstance(ip.manifests, dict)
    assert len(ip.manifests) == 2
    assert sorted(ip.manifests.keys()) == sorted(["sha512", "sha256"])
    for m in ["sha512", "sha256"]:
        assert isinstance(ip.manifests[m], dict)
        assert len(ip.manifests[m]) == 10

    assert hasattr(ip, "payload_files")
    assert isinstance(ip.payload_files, dict)
    assert sorted(ip.payload_files.keys()) == \
        sorted(["modified_master", "preservation_master", "derivative_copy"])
    assert sorted(ip.payload_files["preservation_master"]) == \
        sorted([
            "data/preservation_master/sample_1.tiff",
            "data/preservation_master/sample_2.tiff"
        ])
    assert sorted(ip.payload_files["modified_master"].keys()) == ["1", "2"]
    assert sorted(ip.payload_files["derivative_copy"].keys()) == ["1", "2"]
    for version in ["modified_master", "derivative_copy"]:
        for representation in ["1", "2"]:
            assert len(ip.payload_files[version][representation]) == 2
            for file in ip.payload_files[version][representation]:
                assert Path("data/" + version + "/" + representation) in \
                    Path(file).parents

    assert hasattr(ip, "dc_xml")
    assert isinstance(ip.dc_xml, et._ElementTree)
    assert len(et.tostring(ip.dc_xml, encoding='utf8')) == 638

    assert hasattr(ip, "source_metadata")
    assert isinstance(ip.source_metadata, et._ElementTree)
    assert len(et.tostring(ip.source_metadata, encoding='utf8')) == 903

    assert hasattr(ip, "events")
    assert ip.events is None


@pytest.mark.parametrize(
    ("deleted_files", "ip_complete", "log_message"),
    [
        (
            ["bag-info.txt"],
            False,
            "Unable to load file"
        ),  # bag_info
        (
            ["manifest-md5.txt", "manifest-sha256.txt", "manifest-sha512.txt"],
            False,
            "No file with prefix 'manifest' found."
        ),  # manifests
        (
            ["meta/dc.xml"],
            True,
            "No file 'meta/dc.xml' found."
        ),  # dc
        (
            ["meta/source_metadata.xml"],
            True,
            "No file 'meta/source_metadata.xml' found."
        ),  # source_metadata
        (
            ["meta/events.xml"],
            True,
            "No file 'meta/events.xml' found."
        ),  # events
    ],
    ids=[
        "bag_info",
        "manifests",
        "dc",
        "source_metadata",
        "events"
    ]
)
def test_missing_files(
    file_storage,
    deleted_files,
    ip_complete,
    log_message
):
    """
    Test the exceptions raised during instantiation of an `IP` object
    when files are missing.
    """

    # Prepare IP
    ip_path = file_storage / "ip" / str(uuid4())
    copytree(
        src=file_storage / "test_ip",
        dst=ip_path,
    )
    # Delete files
    for f in deleted_files:
        if (ip_path / f).is_file():
            (ip_path / f).unlink()

    # Create IP object from temp_dir
    if ip_complete:
        ip = IP(path=ip_path)
        assert ip._complete
    else:
        # Assert error for required files
        with pytest.raises(AttributeError) as exc_info:
            ip = IP(path=ip_path)
        assert exc_info.type is AttributeError
        assert log_message in str(exc_info.value)


@pytest.mark.parametrize(
    "spaces",
    [" ", "  ", "\t"],
    ids=["single", "double", "tab"]
)
@pytest.mark.parametrize(
    "filename",
    ["file.txt", "path/to/file.txt", "path/to/file with spaces.txt"],
    ids=["file", "path", "path_with_spaces"]
)
def test_manifest_robustness(file_storage, spaces, filename):
    """
    Test creating an IP with manifests containing
    * one or two spaces between hash and filepath
    * spaces in filepath
    """

    # Make tmp directory
    ip_path = file_storage / "ip" / str(uuid4())
    ip_path.mkdir(parents=True)
    # Write manifest file
    create_txt_file(
        file_path=ip_path / "manifest-md5.txt",
        text=f"123{spaces}{filename}"
    )
    # Create IP object from ip_path
    ip = IP(path=ip_path, ignore_errors=True)
    assert "md5" in ip.manifests
    assert filename in ip.manifests["md5"]
    assert ip.manifests["md5"][filename] == "123"


def test_manifests_identical_hashes(file_storage):
    """
    Test creating an IP with manifests containing identical hashes.
    """

    # Make tmp directory
    ip_path = file_storage / "ip" / str(uuid4())
    ip_path.mkdir(parents=True)
    # Write manifest file
    payload_files = [
        "data/preservation_master/sample.jpg",
        "data/preservation_master/sample.tiff",
        "data/preservation_master/another_file.docx"
    ]
    hashes = ["123", "123", "456"]
    h_dict = dict(zip(payload_files, hashes))
    content = ""
    for f, h in h_dict.items():
        content += h + "  " + f + "\n"
    create_txt_file(
        file_path=ip_path / "manifest-md5.txt",
        text=content
    )
    # Create IP object from ip_path
    ip = IP(path=ip_path, ignore_errors=True)
    assert ip.manifests is not None
    assert isinstance(ip.manifests, dict)
    assert len(ip.manifests) == 1
    assert "md5" in ip.manifests
    assert isinstance(ip.manifests["md5"], dict)
    assert dict(sorted(ip.manifests["md5"].items())) == \
        dict(sorted(h_dict.items()))
