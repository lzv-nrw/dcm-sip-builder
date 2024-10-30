"""Test module for XML schema validator."""

import pytest
import xmlschema
from dcm_common import LoggingContext as Context

from dcm_sip_builder.components import XMLValidator


@pytest.fixture(name="minimal_xsd")
def _minimal_xsd():
    return """<?xml version="1.0" encoding="UTF-8"?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="person">
    <xsd:complexType>
      <xsd:sequence>
        <xsd:element name="name" type="xsd:string"/>
        <xsd:element name="age" type="xsd:int"/>
      </xsd:sequence>
    </xsd:complexType>
  </xsd:element>
</xsd:schema>
"""


@pytest.fixture(name="minimal_xml")
def _minimal_xml():
    return """<?xml version="1.0" encoding="UTF-8"?>
<person>
  <name>John Doe</name>
  <age>30</age>
</person>
"""


def test_xmlvalidator_constructor(minimal_xsd):
    """Test the `version` argument of the `XMLValidator constructor."""
    assert isinstance(
        XMLValidator(minimal_xsd).schema, xmlschema.XMLSchema10
    )
    assert isinstance(
        XMLValidator(minimal_xsd, "1.0").schema, xmlschema.XMLSchema10
    )
    assert isinstance(
        XMLValidator(minimal_xsd, "1.1").schema, xmlschema.XMLSchema11
    )
    with pytest.raises(ValueError):
        XMLValidator(minimal_xsd, "unknown")


@pytest.mark.parametrize(
    ("mutate", "expected_result"),
    [
        (lambda x: x, True),
        (lambda x: x.replace("<name>", "<nme>"), False),
        (lambda x: x.replace("age", "height"), False),
    ],
    ids=["ok", "bad-xml", "invalid-xml"]
)
def test_is_valid(mutate, expected_result, minimal_xsd, minimal_xml):
    """Test method `is_valid` of `XMLValidator`."""

    validator = XMLValidator(minimal_xsd)
    assert validator.is_valid(mutate(minimal_xml)) == expected_result


@pytest.mark.parametrize(
    ("mutate", "expected_result"),
    [
        (lambda x: x, 0),
        (lambda x: x.replace("<name>", "<nme>"), 1),
        (lambda x: x.replace("age", "height"), 1),
        (
            lambda x:
                x.replace("age", "height").replace("</name>", "</name>\n  <sex>male</sex>"),
            2
        ),
    ],
    ids=["ok", "bad-xml", "invalid-xml-single", "invalid-xml-multiple"]
)
def test_validate(mutate, expected_result, minimal_xsd, minimal_xml):
    """Test method `validate` of `XMLValidator`."""

    validator = XMLValidator(minimal_xsd)
    result = validator.validate(mutate(minimal_xml))
    if expected_result == 0:
        assert Context.ERROR not in result
    else:
        print(result.fancy())
        assert len(result[Context.ERROR]) == expected_result
