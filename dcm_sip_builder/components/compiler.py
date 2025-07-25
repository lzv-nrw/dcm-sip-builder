"""
This module defines the `MetadataCompiler` component of the SIP Builder-app.
"""

from typing import Optional, Iterable, TypeVar
import abc
from pathlib import Path
from dataclasses import dataclass, field
from itertools import count

from lxml import etree as et
from dcm_common import LoggingContext as Context, Logger

from dcm_sip_builder.models import IP

# pylint: disable=c-extension-no-member


@dataclass
class File:
    """
    A `File` stores information on a single file within the payload.

    Keyword arguments:
    href -- file location
    loctype -- type identifier for `href`
    index -- numeric identifier within `Representation`
    """
    index: int  # 1, 2, 3, ...
    href: str
    loctype: str = field(default_factory=lambda: "URL")
    checksums: dict[str, str] = field(default_factory=lambda: {})


@dataclass
class Representation:
    """
    A `Representation` stores information on a single representation of
    an IE and its identifier within Rosetta METS.

    Keyword arguments:
    preservation_type -- name identifier for the `Representation`
    usage_type -- 'usageType'-key information in Rosetta METS
    index -- numeric identifier within an IE
    files -- list of `File`s associdated with this `Representation`
    """
    index: int  # 1, 2, 3, ..
    preservation_type: str  # PRESERVATION_MASTER, DERIVATIVE_COPY, ..
    usage_type: str = field(default_factory=lambda: "VIEW")
    files: list[File] = field(default_factory=lambda: [])


@dataclass
class Namespace:
    """
    A `Namespace` associates a `prefix` with an `identifier`.

    Its string representation is the `identifier` surrounded by curly
    brackets. It also implements addition to strings
     >>> Namespace("oai", "http://www.openarchives.org/OAI/2.0/") + "record"
     '{http://www.openarchives.org/OAI/2.0/}record'
    """
    prefix: str
    identifier: str

    def __str__(self):
        return f"{{{self.identifier}}}"

    def __add__(self, other):
        return str(self) + other

    def __radd__(self, other):
        return other + str(self)


class XMLNS:
    """Collection of XML namespaces."""
    oai = Namespace("oai", "http://www.openarchives.org/OAI/2.0/")
    mets = Namespace(
        "mets", "http://www.exlibrisgroup.com/xsd/dps/rosettaMets"
    )
    dc = Namespace("dc", "http://purl.org/dc/elements/1.1/")
    dcterms = Namespace("dcterms", "http://purl.org/dc/terms/")
    rosetta = Namespace("rosetta", "http://www.exlibrisgroup.com/dps")
    dnx = Namespace("dnx", "http://www.exlibrisgroup.com/dps/dnx")
    xlink = Namespace("xlink", "http://www.w3.org/1999/xlink")

    @classmethod
    def to_dict(
        cls, selection: Optional[Iterable[str]] = None
    ) -> dict[str, str]:
        """
        Returns dictionary of namespaces defined in this class (or of
        the custom `selection`).

        Note that in case of duplicate `Namespace.name`s in this class
        only one can be included in the dictionary.

        Keyword arguments:
        selection -- iterable listing the requested namespaces (class
                     attributes) to be included
                     (default None)
        """
        return {
            v.prefix: v.identifier
            for k, v in cls.__dict__.items()
            if (selection is None or k in selection)
            and isinstance(v, Namespace)
        }


class MetadataCompiler(metaclass=abc.ABCMeta):
    """
    Interface for different metadata_compilers.

    Requirements for qualification as `MetadataCompiler`:
    TAG -- property (string); verbose name (usable for `Logger` objects)
    _compile -- generate and return XML-metadata based on `IP` object

    Methods:
    tostring -- convert xml etree to string
    compile -- compile metadata
    compile_as_string -- compile metadata as string
    """

    # setup requirements for an object to be regarded
    # as implementing the Interface
    @classmethod
    def __subclasshook__(cls, subclass):
        return (
            hasattr(subclass, "TAG")
            and hasattr(subclass, "compile")
            and callable(subclass.compile)
            or NotImplemented
        )

    # setup checks for missing implementation/definition of properties
    @property
    @abc.abstractmethod
    def TAG(self) -> str:
        """
        Verbose name of this `MetadataCompiler`.
        """
        raise NotImplementedError(
            f"Class {self.__class__.__name__} does not define property 'TAG'."
        )

    @abc.abstractmethod
    def _compile(self, ip: IP) -> et._Element:
        """
        Perform metadata mapping logic based on given `ip` and return
        XML document as `lxml.etree._Element`.

        Keyword arguments:
        ip -- `IP` object
        """
        raise NotImplementedError(
            f"Class {self.__class__.__name__} does not define method "
            + "'compile'."
        )

    def compile_as_string(self, ip: IP) -> str:
        """
        Perform metadata mapping based on given `ip` and return XML
        document as string.

        Keyword arguments:
        ip -- `IP` object
        """
        return self.tostring(self._compile(ip))

    def compile(self, ip: IP) -> et._Element:
        """
        Perform metadata mapping based on given `ip` and return XML
        document as `lxml.etree._Element`.

        Keyword arguments:
        ip -- `IP` object
        """
        return self._compile(ip)

    def __init__(self) -> None:
        self.log = Logger(default_origin=self.TAG)

    _T = TypeVar("_T")
    """Generic type."""

    @staticmethod
    def _listify(value: _T) -> list[_T]:
        """
        Returns
        * `value` if `value` is a list
        * `[value]` if `value` is not a list
        """
        if isinstance(value, list):
            return value
        return [value]

    @staticmethod
    def tostring(xml: et._Element | et._ElementTree) -> str:
        """
        Convert input XML `xml` to a formatted string.

        Keyword arguments:
        xml -- XML element(-tree) to be converted
        """
        return et.tostring(
            xml,
            pretty_print=True,
            doctype='<?xml version="1.0" encoding="UTF-8"?>',
            encoding="UTF-8"
        ).decode()


class DCCompiler(MetadataCompiler):
    """
    `MetadataCompiler` that implements the mapping from `baginfo.txt`
    to `dc.xml`.
    """
    TAG = "dc.xml Compiler"
    BAG_INFO_DC_MAP = {
        "DC-Title": XMLNS.dc + "title",
        "DC-Terms-Identifier": XMLNS.dcterms + "identifier",
        "Origin-System-Identifier": XMLNS.rosetta + "externalSystem",
        "External-Identifier": XMLNS.rosetta + "externalId",
    }

    def _compile(self, ip):
        self.log = Logger(default_origin=self.TAG)
        # create root element
        dc_xml = et.Element(
            XMLNS.dc + "record",
            nsmap=XMLNS.to_dict(["dc", "dcterms", "rosetta"])
        )

        # exit if missing required metadata
        if ip.baginfo is None:
            self.log.log(
                Context.ERROR,
                body="Missing 'bag-info.txt' metadata in target."
            )
            return dc_xml

        for key, value in self.BAG_INFO_DC_MAP.items():
            if key not in ip.baginfo:
                continue
            # ip.baginfo may contain non-lists, listify to allow
            # iterative processing anyway
            for item in self._listify(ip.baginfo[key]):
                et.SubElement(dc_xml, value).text = item

        return dc_xml


class IECompiler(MetadataCompiler):
    """
    `MetadataCompiler` that implements the aggregation of metadata from
    an `IP` and maps to the Rosetta METS `ie.xml`.
    """
    TAG = "ie.xml Compiler"
    BAG_INFO_DC_MAP = {
        "DC-Terms-Identifier": XMLNS.dcterms + "identifier",
        "DC-Creator": XMLNS.dc + "creator",
        "DC-Title": XMLNS.dc + "title",
        "DC-Rights": XMLNS.dc + "rights",
        "DC-Terms-Rights": XMLNS.dcterms + "rights",
        "DC-Terms-License": XMLNS.dcterms + "license",
        "DC-Terms-Access-Rights": XMLNS.dcterms + "accessRights",
        "Embargo-Enddate": XMLNS.dcterms + "available",
        "DC-Terms-Rights-Holder": XMLNS.dcterms + "rightsHolder",
    }
    DMD_DC_RECORD_ORDER = [
        XMLNS.dcterms + "identifier", XMLNS.dc + "creator", XMLNS.dc + "title",
        XMLNS.dc + "rights", XMLNS.dcterms + "rights",
        XMLNS.dcterms + "license", XMLNS.dcterms + "accessRights",
        XMLNS.dcterms + "available", XMLNS.dcterms + "rightsHolder",
    ]

    @staticmethod
    def _get_dcm_dcterms_identifier(baginfo: dict) -> str:
        DCTERMS_IDENTIFIER_FORMAT = "dcm:{src_org}@{org_sys_id}@{ext_id}"
        return DCTERMS_IDENTIFIER_FORMAT.format(
            src_org=baginfo["Source-Organization"],
            org_sys_id=baginfo["Origin-System-Identifier"],
            ext_id=baginfo["External-Identifier"]
        )

    @staticmethod
    def _get_mdwrap_base(
        child: Optional[et._Element] = None, **attrib
    ) -> et._Element:
        """
        Returns 'mdWrap'-element with attributes given via `attrib` and
        (if present) `child` appended to the inner 'xmlData'-element.
        """
        xmldata = et.Element(XMLNS.mets + "xmlData")
        if child is not None:
            xmldata.append(child)
        mdwrap = et.Element(XMLNS.mets + "mdWrap", attrib=attrib)
        mdwrap.append(xmldata)
        return mdwrap

    def _generate_representation_info(
        self,
        payload_files: dict[str, list[str] | dict[str, list[str]]],
        manifests: dict[str, dict[str, str]]
    ) -> list[Representation]:
        """
        This method prepares the 'preservationType'-ids and determines
        the file order based on `payload_files`.

        Returns list of `Representations` in the form of
            [
                Representation(
                    index=1,
                    preservation_type='PRESERVATION_MASTER',
                    ...
                    files=[
                        File(
                            index=1,
                            href='data/preservation_master/sample_1.tiff',
                            ...
                            checksums={'MD5': ...}
                        ),
                        File(
                            index=2,
                            href='data/preservation_master/sample_2.tiff',
                            ...
                            checksums={'MD5': ...}
                        )
                    ],
                ),
                Representation(
                    index=2,
                    preservation_type='MODIFIED_MASTER',
                    ...
                ),
                Representation(
                    index=3,
                    preservation_type='MODIFIED_MASTER_02',
                    ...
                ),
                ...
            ]

        Keyword arguments:
        payload_files -- payload-content of an `IP` as generated by
                         the `IP`-model
        manifests -- manifest information collected from `IP`
        """
        rep_list = []
        index = count(1)

        if "preservation_master" in payload_files:
            rep_list.append(
                Representation(
                    next(index),
                    "PRESERVATION_MASTER",
                    files=[
                        File(
                            i, file, checksums={
                                k.upper(): v[file]
                                for k, v in manifests.items()
                            }
                        )
                        for i, file in enumerate(sorted(
                            payload_files["preservation_master"]
                        ), start=1)
                    ]
                )
            )
        for category, rep_name in [
            ("modified_master", "MODIFIED_MASTER"),
            ("derivative_copy", "DERIVATIVE_COPY"),
        ]:
            if category not in payload_files:
                continue
            for rep_id, rep in enumerate(
                sorted(payload_files[category]), start=1
            ):
                rep_list.append(
                    Representation(
                        next(index),
                        rep_name + (
                            f"_{int(rep_id):02d}" if rep_id > 1 else ""
                        ),
                        files=[
                            File(
                                i, file, checksums={
                                    k.upper(): v[file]
                                    for k, v in manifests.items()
                                }
                            )
                            for i, file in enumerate(
                                sorted(payload_files[category][rep]), start=1  # type: ignore[call-overload]
                            )
                        ]
                    )
                )

        return rep_list

    def _compile(self, ip):
        self.log = Logger(default_origin=self.TAG)
        # create root element
        ie_xml = et.Element(
            XMLNS.mets + "mets",
            nsmap=XMLNS.to_dict([
                "mets", "dc", "dcterms", "oai",
            ])
        )

        # exit if missing required metadata
        if ip.baginfo is None:
            self.log.log(
                Context.ERROR,
                body="Missing 'bag-info.txt' metadata in target."
            )
            return ie_xml

        # add sections individually
        ie_xml.append(self.compile_dmdsec(ip.baginfo, ip.dc_xml))
        ie_xml.append(
            self.compile_ie_amdsec(
                ip.baginfo, ip.source_metadata, ip.significant_properties
            )
        )

        representations = self._generate_representation_info(
            ip.payload_files, ip.manifests or {}
        )
        for amdsec in self.compile_rep_amdsecs(representations):
            ie_xml.append(amdsec)
        for amdsec in self.compile_file_amdsecs(representations):
            ie_xml.append(amdsec)
        ie_xml.append(self.compile_filesec(representations))

        return ie_xml

    def compile_dmdsec(
        self,
        baginfo: dict,
        dc_xml: Optional[et._ElementTree]
    ) -> et._Element:
        """
        This method generates the 'mets:dmdSec'-element of the Rosetta
        METS-'ie.xml' based on the given IP-metadata ('bag-info.txt' and
        'dc.xml').

        Keyword arguments:
        baginfo -- metadata given in the `IP`'s 'bag-info.txt'-file
        dc_xml -- `IP`'s 'dc.xml' metadata as XML document
        """

        # setup root element
        dmdsec = et.Element(XMLNS.mets + "dmdSec", ID="ie-dmd")

        dc_record = et.Element(XMLNS.dc + "record")
        # Special case for "Source-Organization",
        # "External-Identifier" and "Origin-System-Identifier"
        try:
            et.SubElement(
                dc_record,
                XMLNS.dcterms + "identifier"
            ).text = self._get_dcm_dcterms_identifier(baginfo)
        except KeyError as exc_info:
            self.log.log(
                Context.ERROR,
                body="Missing required metadata in 'bag-info.txt': "
                + f"{exc_info}."
            )
            return dmdsec

        # iterate baginfo (contents take priority over dc.xml, log added
        # elements in `_from_baginfo`)
        _from_baginfo = []
        for key, value in self.BAG_INFO_DC_MAP.items():
            if key not in baginfo:
                continue
            # baginfo may contain non-lists, listify to allow
            # iterative processing anyway
            for item in self._listify(baginfo[key]):
                _from_baginfo.append((value, item))
                et.SubElement(dc_record, value).text = item

        # iterate dc.xml if existent (secondary, skip duplicates)
        if dc_xml is not None:
            for dc_element in dc_xml.getroot():
                # skip previously handled additions
                if (dc_element.tag, dc_element.text) in _from_baginfo:
                    continue
                dc_record.append(dc_element)

        # nest inner elements
        dmdsec.append(
            self._get_mdwrap_base(child=dc_record, MDTYPE="DC")
        )

        # sort tags by
        # * DMD_DC_RECORD_ORDER,
        # * tag-name,
        # * content
        dc_record[:] = sorted(
            list(dc_record),
            key=lambda x: (
                self.DMD_DC_RECORD_ORDER.index(x.tag)
                if x.tag in self.DMD_DC_RECORD_ORDER
                else len(self.DMD_DC_RECORD_ORDER),
                x.tag,
                x.text or ""
            )
        )

        return dmdsec

    def compile_ie_amdsec(
        self,
        baginfo: dict,
        source_metadata: Optional[et._ElementTree],
        significant_properties: Optional[dict],
    ) -> et._Element:
        """
        Returns 'ie-amd'-amdSec element.

        Keyword arguments:
        baginfo -- metadata given in the `IP`'s 'bag-info.txt'-file
        source_metadata -- xml tree of source metadata collected from
                           `IP`
        significant_properties -- contents of metadata-file
                                  `significant_properties.xml`
        """
        # create base
        amdsec = et.Element(XMLNS.mets + "amdSec", ID="ie-amd")

        # generate and append children
        amdsec.append(
            self.compile_ie_amdsec_techmd(baginfo, significant_properties)
        )
        amdsec.append(self.compile_ie_amdsec_rightsmd())
        if source_metadata is not None:
            amdsec.append(self.compile_ie_amdsec_sourcemd(source_metadata))
        amdsec.append(self.compile_ie_amdsec_digiprovmd())
        return amdsec

    def compile_ie_amdsec_techmd(
        self,
        baginfo: dict,
        significant_properties: Optional[dict],
    ) -> et._Element:
        """
        Returns 'techMD'-section of 'ie-amd'-amdSec element.

        Keyword arguments:
        baginfo -- metadata given in the `IP`'s 'bag-info.txt'-file
        significant_properties -- contents of metadata-file
                                  `significant_properties.xml`
        """
        # create inner child
        dnx = et.Element("dnx", nsmap={None: XMLNS.dnx.identifier})

        # et.SubElement(dnx, "section", id="objectIdentifier")
        # et.SubElement(dnx, "section", id="generalIECharacteristics")
        if "Preservation-Level" in baginfo:
            preservationlevel = et.SubElement(
                dnx, "section", id="preservationLevel"
            )
            et.SubElement(
                et.SubElement(preservationlevel, "record"),
                "key",
                id="preservationLevelType"
            ).text = baginfo["Preservation-Level"]

        if significant_properties is not None:
            significantproperties = et.SubElement(
                dnx, "section", id="significantProperties"
            )
            for type_, value in significant_properties.items():
                record = et.SubElement(significantproperties, "record")
                et.SubElement(
                    record,
                    "key",
                    id="significantPropertiesType"
                ).text = type_
                et.SubElement(
                    record,
                    "key",
                    id="significantPropertiesValue"
                ).text = value

        # assemble
        techmd = et.Element(XMLNS.mets + "techMD", ID="ie-amd-tech")
        techmd.append(
            self._get_mdwrap_base(
                child=dnx, MDTYPE="OTHER", OTHERMDTYPE="dnx"
            )
        )
        return techmd

    def compile_ie_amdsec_rightsmd(self) -> et._Element:
        """
        Returns 'rightsMD'-section of 'ie-amd'-amdSec element.
        """
        # create inner child
        dnx = et.Element("dnx", nsmap={None: XMLNS.dnx.identifier})

        et.SubElement(dnx, "section", id="accessRightsPolicy")

        # assemble
        rightsmd = et.Element(XMLNS.mets + "rightsMD", ID="ie-amd-rights")
        rightsmd.append(
            self._get_mdwrap_base(
                child=dnx, MDTYPE="OTHER", OTHERMDTYPE="dnx"
            )
        )
        return rightsmd

    def compile_ie_amdsec_sourcemd(
        self,
        source_metadata: Optional[et._ElementTree]
    ) -> et._Element:
        """
        Returns 'sourceMD'-section of 'ie-amd'-amdSec element.

        Keyword arguments:
        source_metadata -- xml tree of source metadata collected from
                           `IP`
        """
        sourcemd = et.Element(
            XMLNS.mets + "sourceMD", ID="ie-amd-source-OTHER"
        )
        sourcemd.append(
            self._get_mdwrap_base(
                child=source_metadata.getroot() if source_metadata else None,
                MDTYPE="OTHER",
                OTHERMDTYPE="Text"
            )
        )
        return sourcemd

    def compile_ie_amdsec_digiprovmd(self) -> et._Element:
        """
        Returns 'digiprovMD'-section of 'ie-amd'-amdSec element.
        """
        digiprovmd = et.Element(
            XMLNS.mets + "digiprovMD", ID="ie-amd-digiprov"
        )
        digiprovmd.append(
            self._get_mdwrap_base(
                child=et.Element("dnx", nsmap={None: XMLNS.dnx.identifier}),
                MDTYPE="OTHER", OTHERMDTYPE="dnx"
            )
        )
        return digiprovmd

    def compile_rep_amdsecs(
        self,
        representations: list[Representation]
    ) -> list[et._Element]:
        """
        Returns list of 'repX-amd'-amdSec elements.

        Keyword arguments:
        representations -- list of `Representation`-objects
                           (see `_generate_representation_info` for
                           details)
        """
        amdsecs = []
        for representation in representations:
            # create mdWrap-content
            dnx = et.Element("dnx", nsmap={None: XMLNS.dnx.identifier})
            section = et.SubElement(
                dnx, "section", id="generalRepCharacteristics"
            )
            record = et.SubElement(section, "record")
            et.SubElement(record, "key", id="preservationType").text = \
                representation.preservation_type
            et.SubElement(record, "key", id="usageType").text = \
                representation.usage_type

            # assemble amdSec element
            amdsec = et.Element(
                XMLNS.mets + "amdSec", ID=f"rep{representation.index}-amd"
            )
            techmd = et.SubElement(
                amdsec, XMLNS.mets + "techMD",
                ID=f"rep{representation.index}-amd-tech"
            )
            techmd.append(
                self._get_mdwrap_base(
                    child=dnx, MDTYPE="OTHER", OTHERMDTYPE="dnx"
                )
            )
            amdsecs.append(amdsec)
        return amdsecs

    def compile_file_amdsecs(
        self,
        representations: list[Representation]
    ) -> list[et._Element]:
        """
        Returns list of 'fidX-Y-amd'-amdSec elements.

        Keyword arguments:
        representations -- list of `Representation`-objects
                           (see `_generate_representation_info` for
                           details)
        """
        amdsecs = []
        for representation in representations:
            for file in representation.files:
                # create mdWrap-content
                dnx = et.Element("dnx", nsmap={None: XMLNS.dnx.identifier})
                section = et.SubElement(
                    dnx, "section", id="fileFixity"
                )
                for fixity_type, checksum in file.checksums.items():
                    record = et.SubElement(section, "record")
                    et.SubElement(record, "key", id="fixityType").text = \
                        fixity_type
                    et.SubElement(record, "key", id="fixityValue").text = \
                        checksum

                # assemble amdSec element
                amdsec = et.Element(
                    XMLNS.mets + "amdSec",
                    ID=f"fid{representation.index}-{file.index}-amd"
                )
                techmd = et.SubElement(
                    amdsec, XMLNS.mets + "techMD",
                    ID=f"fid{representation.index}-{file.index}-amd-tech"
                )
                techmd.append(
                    self._get_mdwrap_base(
                        child=dnx, MDTYPE="OTHER", OTHERMDTYPE="dnx"
                    )
                )
                amdsecs.append(amdsec)
        return amdsecs

    def compile_filesec(
        self,
        representations: list[Representation]
    ) -> et._Element:
        """
        Returns 'fileSec'-section of 'mets'-element.

        Keyword arguments:
        representations -- list of `Representation`-objects
                           (see `_generate_representation_info` for
                           details)
        """
        # create base 'fileSec'-element
        filesec = et.Element(XMLNS.mets + "fileSec")

        # create children (fileGrp)
        for representation in representations:
            filegrp = et.SubElement(
                filesec,
                XMLNS.mets + "fileGrp",
                USE=representation.usage_type,
                ID=f"rep{representation.index}",
                ADMID=f"rep{representation.index}-amd"
            )
            for _file in representation.files:
                file = et.SubElement(
                    filegrp,
                    XMLNS.mets + "file",
                    ID=f"fid{representation.index}-{_file.index}",
                    ADMID=f"fid{representation.index}-{_file.index}-amd"
                )
                et.SubElement(
                    file,
                    XMLNS.mets + "FLocat",
                    nsmap=XMLNS.to_dict(["xlink"]),
                    attrib={
                        "LOCTYPE": _file.loctype,
                        XMLNS.xlink + "href":
                            str(
                                Path(_file.href).relative_to(
                                    Path(_file.href).parts[0]
                                )
                            )
                    }
                )
            filesec.append(filegrp)
        return filesec
