"""Test module for metadata compiler."""

from unittest.mock import patch

import pytest
from lxml import etree as et
from dcm_common import LoggingContext as Context

from dcm_sip_builder.components.compiler \
    import File, Representation, Namespace, XMLNS, \
    MetadataCompiler, DCCompiler, IECompiler

# pylint: disable=c-extension-no-member


# ------------------------
# define helper functions
def get_child_tags(element: et._Element) -> set[str]:
    """Returns set of tags in child-elements."""
    return set(e.tag for e in element)


def test_get_child_tags():
    """Test function `get_child_tags`."""
    xml = et.Element("root")
    et.SubElement(xml, "a")
    et.SubElement(xml, "b")
    assert get_child_tags(xml) == set(["a", "b"])


def get_children_by_tag(element: et._Element, tag: str) -> list[et._Element]:
    """Returns list of child-elements with tag."""
    return [e for e in element if e.tag == tag]


def test_get_children_by_tag():
    """Test function `get_children_by_tag`."""
    xml = et.Element("root")
    a1 = et.SubElement(xml, "a")
    a2 = et.SubElement(xml, "a")
    et.SubElement(xml, "b")
    assert set(get_children_by_tag(xml, "a")) == set([a1, a2])


def get_child_text_by_tag(element: et._Element, tag: str) -> list[str]:
    """Returns list of child-elements' `text` if tagged with `tag`."""
    return list(map(lambda x: x.text, get_children_by_tag(element, tag)))


def test_get_child_text_by_tag():
    """Test function `get_child_text_by_tag`."""
    xml = et.Element("root")
    a1 = et.SubElement(xml, "a")
    a1.text = "a1"
    a2 = et.SubElement(xml, "a")
    a2.text = "a2"
    et.SubElement(xml, "b")
    assert set(get_child_text_by_tag(xml, "a")) == set([a1.text, a2.text])


def get_children_dict(element: et._Element) -> dict[str, list]:
    """Returns dict with pairs of `tag`s and list of `text`s."""
    return {
        tag: get_child_text_by_tag(element, tag)
        for tag in get_child_tags(element)
    }


def test_get_children_dict():
    """Test function `get_children_dict`."""
    xml = et.Element("root")
    a1 = et.SubElement(xml, "a")
    a1.text = "a1"
    a2 = et.SubElement(xml, "a")
    a2.text = "a2"
    et.SubElement(xml, "b")
    assert {k: sorted(v) for k, v in get_children_dict(xml).items()} == {
        "a": sorted([a1.text, a2.text]),
        "b": [None],
    }


def get_child_from_path(
    element: et._Element, path: list[str]
) -> list[et._Element]:
    """
    Returns list of Elements at path. List is empty if path does not
    exist. If intermediate steps in the `path` are ambiguous, search
    continues with the first element.
    """
    if len(path) == 0:
        return element
    children = get_children_by_tag(element, path[0])
    if len(path) == 1:
        return children
    if len(children) > 0:
        return get_child_from_path(children[0], path[1:])
    return []


def test_get_child_from_path():
    """Test function `get_child_from_path`."""
    xml = et.Element("root")
    a = et.SubElement(xml, "a")
    b1 = et.SubElement(a, "b")
    b2 = et.SubElement(a, "b")
    c = et.SubElement(b1, "c")
    assert set(get_child_from_path(xml, ["a", "b"])) == set([b1, b2])
    assert get_child_from_path(xml, ["a", "b", "c"]) == [c]
    assert get_child_from_path(xml, ["x"]) == []
    xml = et.Element("root")
    et.SubElement(xml, "a")
    a2 = et.SubElement(xml, "a")
    b1 = et.SubElement(a2, "b")
    assert get_child_from_path(xml, ["a", "b"]) == []

# ------------------------


def test_namespace_str():
    """Test string conversion of `Namespace`."""

    ns = Namespace("prefix", "identifier")
    assert str(ns) == f"{{{ns.identifier}}}"


def test_namespace_concat():
    """Test concatenation of `Namespace` to string."""

    ns = Namespace("prefix", "identifier")
    assert isinstance(ns + "tag", str)
    assert isinstance("tag" + ns, str)
    assert ns + "tag" == f"{ns}tag"
    assert "tag" + ns == f"tag{ns}"


def test_xmlns_to_dict():
    """Test method `to_dict` of `XMLNS`."""

    assert XMLNS.to_dict([]) == {}
    assert XMLNS.to_dict(["unknown"]) == {}
    assert XMLNS.to_dict() != {}

    assert XMLNS.to_dict(["oai"]) == {XMLNS.oai.prefix: XMLNS.oai.identifier}
    assert XMLNS.to_dict(["oai", "mets"]) == {
        XMLNS.oai.prefix: XMLNS.oai.identifier,
        XMLNS.mets.prefix: XMLNS.mets.identifier,
    }


def test_metadata_compiler_tostring():
    """Test method `tostring` of `MetadataCompiler`."""
    assert MetadataCompiler.tostring(et.Element("a")) \
        == """<?xml version="1.0" encoding="UTF-8"?>
<a/>
"""


@pytest.fixture(name="dc_compiler")
def _dc_compiler():
    return DCCompiler()


def test_dc_compiler_compile(dc_compiler):
    """Test method `compile` of `DCCompiler`."""
    class _IP:
        baginfo = {
            "DC-Title": "title",
            "DC-Terms-Identifier": ["identifier1", "identifier2"],
            "Origin-System-Identifier": "externalSystem",
            "External-Identifier": "externalId",
        }
    xml = dc_compiler.compile(_IP())
    assert xml.tag == XMLNS.dc + "record"
    assert len(xml) == 5
    for key, value in _IP.baginfo.items():
        assert list(
            get_child_text_by_tag(xml, dc_compiler.BAG_INFO_DC_MAP[key])
        ) == value if isinstance(value, list) else list(value)
    assert Context.ERROR not in dc_compiler.log


def test_dc_compiler_compile_missing_key_in_baginfo(dc_compiler):
    """Test method `compile` of `DCCompiler` for missing key in baginfo."""
    class _IP:
        baginfo = {
            "DC-Title": "title",
            "DC-Terms-Identifier": "identifier",
            "Origin-System-Identifier": "externalSystem",
        }
    xml = dc_compiler.compile(_IP())
    assert len(xml) == 3
    assert Context.ERROR not in dc_compiler.log


def test_dc_compiler_compile_additional_key_in_baginfo(dc_compiler):
    """
    Test method `compile` of `DCCompiler` for additional key in baginfo.
    """
    class _IP:
        baginfo = {
            "DC-Title": "title",
            "DC-Terms-Identifier": "identifier",
            "Origin-System-Identifier": "externalSystem",
            "External-Identifier": "externalId",
            "unknown": "value"
        }
    xml = dc_compiler.compile(_IP())
    assert len(xml) == 4
    assert Context.ERROR not in dc_compiler.log


def test_dc_compiler_compile_empty_baginfo(dc_compiler):
    """Test method `compile` of `DCCompiler` for empty baginfo."""
    class _IP:
        baginfo = {}
    xml = dc_compiler.compile(_IP())
    assert len(xml) == 0
    assert Context.ERROR not in dc_compiler.log


def test_dc_compiler_compile_none_baginfo(dc_compiler):
    """Test method `compile` of `DCCompiler` for `None`-baginfo."""
    class _IP:
        baginfo = None
    xml = dc_compiler.compile(_IP())
    assert len(xml) == 0
    assert len(dc_compiler.log[Context.ERROR]) == 1
    print(dc_compiler.log)


@pytest.fixture(name="ie_compiler")
def _ie_compiler():
    return IECompiler()


def test_ie_compiler_compile(ie_compiler):
    """Test method `compile` of `IECompiler` by faking components."""
    class _IP:
        baginfo = {"not": "empty"}
        dc_xml = None
        source_metadata = None
        payload_files = {}
        manifests = {}
    with patch(
        "dcm_sip_builder.components.compiler.IECompiler.compile_dmdsec",
        return_value=et.Element("dmd")
    ), patch(
        "dcm_sip_builder.components.compiler.IECompiler.compile_ie_amdsec",
        return_value=et.Element("ie_amd")
    ), patch(
        "dcm_sip_builder.components.compiler.IECompiler.compile_rep_amdsecs",
        return_value=[et.Element("rep_amdsec1"), et.Element("rep_amdsec2")]
    ), patch(
        "dcm_sip_builder.components.compiler.IECompiler.compile_file_amdsecs",
        return_value=[et.Element("file_amdsec1"), et.Element("file_amdsec2")]
    ), patch(
        "dcm_sip_builder.components.compiler.IECompiler.compile_filesec",
        return_value=et.Element("filesec")
    ):
        xml = ie_compiler.compile(_IP())
        assert xml.tag == XMLNS.mets + "mets"
        assert get_child_tags(xml) == {
            "dmd", "ie_amd", "rep_amdsec1", "rep_amdsec2", "file_amdsec1",
            "file_amdsec2", "filesec",
        }


def test_ie_compiler_compile_none_baginfo(ie_compiler):
    """Test method `compile` of `IECompiler` for `None`-baginfo."""
    class _IP:
        baginfo = None
    xml = ie_compiler.compile(_IP())
    assert len(xml) == 0
    assert len(ie_compiler.log[Context.ERROR]) == 1
    print(ie_compiler.log)


def test_ie_compiler_compile_dmdsec(ie_compiler):
    """
    Test baginfo-part of method `compile_dmdsec` of `IECompiler`.

    Validate custom DC-Terms-Identifier + DC-Title.
    """
    baginfo = {
        "Source-Organization": "source",
        "Origin-System-Identifier": "origin",
        "External-Identifier": "external",
        "DC-Title": "title"
    }
    xml = ie_compiler.compile_dmdsec(baginfo, None)
    assert xml.tag == XMLNS.mets + "dmdSec"
    assert xml.attrib == {  # dmdSec
        "ID": "ie-dmd"
    }
    assert xml[0].attrib == {  # mdWrap
        "MDTYPE": "DC"
    }
    record = get_child_from_path(
        xml, [
            XMLNS.mets + "mdWrap", XMLNS.mets + "xmlData", XMLNS.dc + "record"
        ]
    )[0]
    assert get_child_tags(record) == {
        XMLNS.dcterms + "identifier", XMLNS.dc + "title"
    }
    assert get_child_text_by_tag(record, XMLNS.dc + "title")[0] \
        == baginfo["DC-Title"]


def test_ie_compiler_compile_dmdsec_dc_xml(ie_compiler):
    """
    Test 'dc.xml'-part of method `compile_dmdsec` of `IECompiler`.
    """
    baginfo = {
        "Source-Organization": "source",
        "Origin-System-Identifier": "origin",
        "External-Identifier": "external",
        "DC-Title": "title"
    }
    dc_xml = et.Element("dc", nsmap=XMLNS.to_dict(["dc"]))
    et.SubElement(dc_xml, XMLNS.dc + "title").text = "title"
    another_title = "another title"
    et.SubElement(dc_xml, XMLNS.dc + "title").text = another_title
    xml = ie_compiler.compile_dmdsec(baginfo, et.ElementTree(dc_xml))
    record = get_child_from_path(
        xml, [
            XMLNS.mets + "mdWrap", XMLNS.mets + "xmlData", XMLNS.dc + "record"
        ]
    )[0]
    assert get_child_tags(record) == {
        XMLNS.dcterms + "identifier", XMLNS.dc + "title"
    }
    assert set(get_child_text_by_tag(record, XMLNS.dc + "title")) \
        == {baginfo["DC-Title"], another_title}


def test_ie_compiler_compile_dmdsec_dc_xml_with_missing_text(ie_compiler):
    """
    Test 'dc.xml'-part of method `compile_dmdsec` of `IECompiler`
    with an element without text.
    """
    baginfo = {
        "Source-Organization": "source",
        "Origin-System-Identifier": "origin",
        "External-Identifier": "external",
        "DC-Title": "title"
    }
    dc_xml = et.Element("dc", nsmap=XMLNS.to_dict(["dc"]))
    et.SubElement(dc_xml, XMLNS.dc + "title").text = "title"
    another_title = "another title"
    et.SubElement(dc_xml, XMLNS.dc + "title").text = another_title
    et.SubElement(dc_xml, XMLNS.dc + "identifier")
    xml = ie_compiler.compile_dmdsec(baginfo, et.ElementTree(dc_xml))
    record = get_child_from_path(
        xml, [
            XMLNS.mets + "mdWrap", XMLNS.mets + "xmlData", XMLNS.dc + "record"
        ]
    )[0]
    assert get_child_tags(record) == {
        XMLNS.dcterms + "identifier",
        XMLNS.dc + "title",
        XMLNS.dc + "identifier"
    }
    assert set(get_child_text_by_tag(record, XMLNS.dc + "title")) \
        == {baginfo["DC-Title"], another_title}
    assert set(get_child_text_by_tag(record, XMLNS.dc + "identifier")) \
        == {None}


def test_ie_compiler_compile_dmdsec_missing_baginfo(ie_compiler):
    """Test method `compile_dmdsec` of `IECompiler` for missing `baginfo`."""
    ie_compiler.compile_dmdsec({}, None)
    assert Context.ERROR in ie_compiler.log


@pytest.mark.parametrize(
    "sourceMD",
    [
        None, "not-None"
    ],
    ids=["missing_sourceMD", "present_sourceMD"]
)
def test_ie_compiler_compile_ie_amdsec(ie_compiler, sourceMD):
    """Test method `compile_ie_amdsec` of `IECompiler` by faking components."""
    with patch(
        "dcm_sip_builder.components.compiler.IECompiler.compile_ie_amdsec_techmd",
        return_value=et.Element("techmd")
    ), patch(
        "dcm_sip_builder.components.compiler.IECompiler.compile_ie_amdsec_rightsmd",
        return_value=et.Element("rightsmd")
    ), patch(
        "dcm_sip_builder.components.compiler.IECompiler.compile_ie_amdsec_sourcemd",
        return_value=et.Element("sourcemd")
    ), patch(
        "dcm_sip_builder.components.compiler.IECompiler.compile_ie_amdsec_digiprovmd",
        return_value=et.Element("digiprovmd")
    ):
        xml = ie_compiler.compile_ie_amdsec({}, sourceMD)
        assert xml.tag == XMLNS.mets + "amdSec"
        assert xml.attrib == {  # amdSec
            "ID": "ie-amd"
        }
        if sourceMD is None:
            assert get_child_tags(xml) == {
                "techmd", "rightsmd", "digiprovmd",
            }
        else:
            assert get_child_tags(xml) == {
                "techmd", "rightsmd", "sourcemd", "digiprovmd",
            }


@pytest.mark.parametrize(
    "baginfo",
    [
        {},
        {"Preservation-Level": "preservation_level"},
    ],
    ids=["no-preservation-level", "preservation-level"]
)
def test_ie_compiler_compile_ie_amdsec_techmd(ie_compiler, baginfo):
    """
    Test method `compile_ie_amdsec_techmd` of `IECompiler`.
    """
    xml = ie_compiler.compile_ie_amdsec_techmd(baginfo)
    assert xml.tag == XMLNS.mets + "techMD"
    assert xml.attrib == {  # techMD
        "ID": "ie-amd-tech"
    }
    assert xml[0].attrib == {  # mdWrap
        "MDTYPE": "OTHER", "OTHERMDTYPE": "dnx"
    }
    keys = get_child_from_path(
        xml, [
            XMLNS.mets + "mdWrap", XMLNS.mets + "xmlData", "dnx", "section",
            "record", "key"
        ]
    )
    assert len(keys) == len(baginfo)
    if len(baginfo) > 0:
        assert keys[0].attrib == {"id": "preservationLevelType"}
        assert keys[0].text == baginfo.get("Preservation-Level")


def test_ie_compiler_compile_ie_amdsec_rightsmd(ie_compiler):
    """
    Test method `compile_ie_amdsec_rightsmd` of `IECompiler`.

    (Currently static result, hence static test.)
    """
    xml = ie_compiler.tostring(ie_compiler.compile_ie_amdsec_rightsmd())
    assert xml == """<?xml version="1.0" encoding="UTF-8"?>
<ns0:rightsMD xmlns:ns0="http://www.exlibrisgroup.com/xsd/dps/rosettaMets" ID="ie-amd-rights">
  <ns0:mdWrap MDTYPE="OTHER" OTHERMDTYPE="dnx">
    <ns0:xmlData>
      <dnx xmlns="http://www.exlibrisgroup.com/dps/dnx">
        <section id="accessRightsPolicy"/>
      </dnx>
    </ns0:xmlData>
  </ns0:mdWrap>
</ns0:rightsMD>
"""


def test_ie_compiler_compile_ie_amdsec_sourcemd(ie_compiler):
    """
    Test method `compile_ie_amdsec_sourcemd` of `IECompiler`.
    """
    input_sourcemd = et.ElementTree(et.Element("sourcemd"))
    xml = ie_compiler.compile_ie_amdsec_sourcemd(input_sourcemd)
    assert xml.tag == XMLNS.mets + "sourceMD"
    assert xml.attrib == {  # sourceMD
        "ID": "ie-amd-source-OTHER"
    }
    assert xml[0].attrib == {  # mdWrap
        "MDTYPE": "OTHER", "OTHERMDTYPE": "Text"
    }
    sourcemd = get_child_from_path(
        xml, [
            XMLNS.mets + "mdWrap", XMLNS.mets + "xmlData"
        ]
    )
    assert len(sourcemd) == (1 if input_sourcemd is not None else 0)
    if input_sourcemd is not None:
        assert sourcemd[0][0] == input_sourcemd.getroot()


def test_ie_compiler_compile_ie_amdsec_digiprovmd(ie_compiler):
    """
    Test method `compile_ie_amdsec_digiprovmd` of `IECompiler`.

    (Currently static result, hence static test.)
    """
    xml = ie_compiler.tostring(ie_compiler.compile_ie_amdsec_digiprovmd())
    assert xml == """<?xml version="1.0" encoding="UTF-8"?>
<ns0:digiprovMD xmlns:ns0="http://www.exlibrisgroup.com/xsd/dps/rosettaMets" ID="ie-amd-digiprov">
  <ns0:mdWrap MDTYPE="OTHER" OTHERMDTYPE="dnx">
    <ns0:xmlData>
      <dnx xmlns="http://www.exlibrisgroup.com/dps/dnx"/>
    </ns0:xmlData>
  </ns0:mdWrap>
</ns0:digiprovMD>
"""


def test_ie_compiler_compile_rep_amdsecs(ie_compiler):
    """Test method `compile_rep_amdsecs` of `IECompiler`."""
    representations = [Representation(0, "type", "usage")]
    xml = ie_compiler.compile_rep_amdsecs(representations)[0]
    assert xml.tag == XMLNS.mets + "amdSec"
    assert xml.attrib == {  # amdSec
        "ID": f"rep{representations[0].index}-amd"
    }
    assert xml[0].attrib == {  # techMD
        "ID": f"rep{representations[0].index}-amd-tech"
    }
    assert xml[0][0].attrib == {  # mdWrap
        "MDTYPE": "OTHER", "OTHERMDTYPE": "dnx"
    }
    assert xml[0][0][0][0][0].attrib == {  # section
        "id": "generalRepCharacteristics"
    }
    keys = get_child_from_path(
        xml, [
            XMLNS.mets + "techMD", XMLNS.mets + "mdWrap",
            XMLNS.mets + "xmlData", "dnx", "section", "record", "key"
        ]
    )
    assert len(keys) == 2
    ptype = keys[0] if keys[0].attrib["id"] == "preservationType" else keys[1]
    utype = keys[0] if keys[0].attrib["id"] == "usageType" else keys[1]
    assert ptype.text == representations[0].preservation_type
    assert utype.text == representations[0].usage_type


def test_ie_compiler_compile_rep_amdsecs_multiple(ie_compiler):
    """
    Test method `compile_rep_amdsecs` of `IECompiler` for multiple
    `Representations`.
    """
    representations = [
        Representation(0, "type0", "usage0"),
        Representation(4, "type4", "usage4")
    ]
    xmls = ie_compiler.compile_rep_amdsecs(representations)
    assert len(xmls) == 2
    for xml, rep in zip(xmls, representations):
        keys = get_child_from_path(
            xml, [
                XMLNS.mets + "techMD", XMLNS.mets + "mdWrap",
                XMLNS.mets + "xmlData", "dnx", "section", "record", "key"
            ]
        )
        assert len(keys) == 2
        ptype = keys[0] if keys[0].attrib["id"] == "preservationType" else keys[1]
        utype = keys[0] if keys[0].attrib["id"] == "usageType" else keys[1]
        assert ptype.text == rep.preservation_type
        assert utype.text == rep.usage_type


def test_ie_compiler_compile_file_amdsecs(ie_compiler):
    """Test method `compile_file_amdsecs` of `IECompiler`."""
    representations = [
        Representation(
            0, "type", "usage", files=[
                File(5, "href", "loctype", {"METHOD": "value"})
            ]
        )
    ]
    xml = ie_compiler.compile_file_amdsecs(representations)[0]
    assert xml.tag == XMLNS.mets + "amdSec"
    assert xml.attrib == {  # amdSec
        "ID": f"fid{representations[0].index}-{representations[0].files[0].index}-amd"
    }
    assert xml[0].attrib == {  # techMD
        "ID": f"fid{representations[0].index}-{representations[0].files[0].index}-amd-tech"
    }
    assert xml[0][0].attrib == {  # mdWrap
        "MDTYPE": "OTHER", "OTHERMDTYPE": "dnx"
    }
    section = get_child_from_path(
        xml, [
            XMLNS.mets + "techMD", XMLNS.mets + "mdWrap",
            XMLNS.mets + "xmlData", "dnx", "section"
        ]
    )[0]
    assert section.attrib == {"id": "fileFixity"}
    records = get_child_from_path(
        section, ["record"]
    )
    assert len(records) == 1
    keys = records[0]
    assert len(keys) == 2
    ftype = keys[0] if keys[0].attrib["id"] == "fixityType" else keys[1]
    fvalue = keys[0] if keys[0].attrib["id"] == "fixityValue" else keys[1]
    assert ftype.text == list(representations[0].files[0].checksums.keys())[0]
    assert fvalue.text == list(representations[0].files[0].checksums.values())[0]


def test_ie_compiler_compile_file_amdsecs_empty_checksums(ie_compiler):
    """
    Test method `compile_file_amdsecs` of `IECompiler` for empty
    checksums.
    """
    representations = [
        Representation(
            0, "type", "usage", files=[
                File(
                    5, "href", "loctype", {}
                )
            ]
        )
    ]
    xml = ie_compiler.compile_file_amdsecs(representations)[0]
    records = get_child_from_path(
        xml, [
            XMLNS.mets + "techMD", XMLNS.mets + "mdWrap",
            XMLNS.mets + "xmlData", "dnx", "section", "record"
        ]
    )
    assert len(records) == 0


def test_ie_compiler_compile_file_amdsecs_multiple_checksums(ie_compiler):
    """
    Test method `compile_file_amdsecs` of `IECompiler` for multiple
    checksums.
    """
    representations = [
        Representation(
            0, "type", "usage", files=[
                File(
                    5, "href", "loctype", {
                        "METHOD1": "value1", "METHOD2": "value2"
                    }
                )
            ]
        )
    ]
    xml = ie_compiler.compile_file_amdsecs(representations)[0]
    records = get_child_from_path(
        xml, [
            XMLNS.mets + "techMD", XMLNS.mets + "mdWrap",
            XMLNS.mets + "xmlData", "dnx", "section", "record"
        ]
    )
    assert len(records) == 2
    assert records[0][0].attrib["id"] == records[1][0].attrib["id"]
    assert records[0][0].text != records[1][0].text
    for keys in records:
        ftype = keys[0] if keys[0].attrib["id"] == "fixityType" else keys[1]
        fvalue = keys[0] if keys[0].attrib["id"] == "fixityValue" else keys[1]
        assert ftype.text in representations[0].files[0].checksums
        assert fvalue.text == representations[0].files[0].checksums[ftype.text]


def test_ie_compiler_compile_file_amdsecs_empty_files(ie_compiler):
    """
    Test method `compile_file_amdsecs` of `IECompiler` for empty
    files.
    """
    representations = [
        Representation(
            0, "type", "usage", files=[]
        )
    ]
    xmls = ie_compiler.compile_file_amdsecs(representations)
    assert len(xmls) == 0


def test_ie_compiler_compile_file_amdsecs_multiple_files(ie_compiler):
    """
    Test method `compile_file_amdsecs` of `IECompiler` for multiple
    files.
    """
    representations = [
        Representation(
            0, "type", "usage", files=[
                File(0, "href0", "loctype0", {}),
                File(5, "href5", "loctype5", {})
            ]
        )
    ]
    xmls = ie_compiler.compile_file_amdsecs(representations)
    for xml in xmls:
        assert xml.attrib == {
            "ID": f"fid{representations[0].index}-{representations[0].files[0].index}-amd"
        } or xml.attrib == {
            "ID": f"fid{representations[0].index}-{representations[0].files[1].index}-amd"
        }


def test_ie_compiler_compile_file_amdsecs_multiple_representations(ie_compiler):
    """
    Test method `compile_file_amdsecs` of `IECompiler` for multiple
    representations.
    """
    representations = [
        Representation(
            0, "type", "usage", files=[
                File(0, "href0", "loctype0", {})
            ]
        ),
        Representation(
            4, "type", "usage", files=[
                File(5, "href5", "loctype5", {})
            ]
        )
    ]
    xmls = ie_compiler.compile_file_amdsecs(representations)
    for xml in xmls:
        assert xml.attrib == {
            "ID": f"fid{representations[0].index}-{representations[0].files[0].index}-amd"
        } or xml.attrib == {
            "ID": f"fid{representations[1].index}-{representations[1].files[0].index}-amd"
        }


def test_ie_compiler_compile_filesec(ie_compiler):
    """Test method `compile_filesec` of `IECompiler`."""
    representations = [
        Representation(
            0, "type0", "usage0", files=[
                File(0, "data/href0", "loctype0", {}),
                File(5, "data/href5", "loctype5", {}),
            ]
        ),
        Representation(
            3, "type3", "usage3", files=[
                File(5, "data/href5", "loctype5", {}),
                File(7, "data/href7", "loctype7", {}),
            ]
        )
    ]
    xml = ie_compiler.compile_filesec(representations)
    assert xml.tag == XMLNS.mets + "fileSec"
    for rep in representations:
        file_grp = next(
            (grp for grp in xml if grp.attrib["ID"] == f"rep{rep.index}"),
            None
        )
        assert file_grp is not None
        assert file_grp.attrib == {
            "USE": rep.usage_type,
            "ID": f"rep{rep.index}",
            "ADMID": f"rep{rep.index}-amd"
        }
        assert len(file_grp) == len(rep.files)
        for rep_file in rep.files:
            mets_file = next(
                (
                    file for file in file_grp
                    if file.attrib["ID"] == f"fid{rep.index}-{rep_file.index}"
                ),
                None
            )
            assert mets_file is not None
            assert mets_file.attrib == {
                "ID": f"fid{rep.index}-{rep_file.index}",
                "ADMID": f"fid{rep.index}-{rep_file.index}-amd"
            }
            assert len(mets_file) == 1
            assert mets_file[0].tag == XMLNS.mets + "FLocat"
            assert mets_file[0].attrib == {
                "LOCTYPE": rep_file.loctype,
                XMLNS.xlink + "href": rep_file.href.replace("data/", "")
            }


def test_ie_compiler_compile_filesec_empty_representations(ie_compiler):
    """
    Test method `compile_filesec` of `IECompiler` for empty
    representations.
    """
    xml = ie_compiler.compile_filesec([])
    assert len(xml) == 0
