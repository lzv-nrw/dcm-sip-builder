"""Configuration module for the 'SIP Builder'-app."""

import os
from pathlib import Path
from importlib.metadata import version

import yaml
import dcm_sip_builder_api
from dcm_common.services import FSConfig, OrchestratedAppConfig

import dcm_sip_builder


class AppConfig(FSConfig, OrchestratedAppConfig):
    """
    Configuration for the 'SIP Builder'-app.
    """

    # ------ BUILD ------
    SIP_OUTPUT = Path(os.environ.get("SIP_OUTPUT") or "sip")
    CUSTOM_FIXITY_SHA512_PLUGIN_NAME = (
        os.environ.get("CUSTOM_FIXITY_SHA512_PLUGIN_NAME")
    )

    # ------ VALIDATION ------
    # Rosetta METS
    VALIDATION_ROSETTA_METS_ACTIVE = \
        (int(os.environ.get("VALIDATION_ROSETTA_METS_ACTIVE") or 1)) == 1
    VALIDATION_ROSETTA_METS_XSD = \
        os.environ.get("VALIDATION_ROSETTA_METS_XSD") \
        or "https://developers.exlibrisgroup.com/wp-content/uploads/2022/06/mets_rosetta.xsd"
    VALIDATION_ROSETTA_METS_XML_SCHEMA_VERSION = \
        os.environ.get("VALIDATION_ROSETTA_METS_XML_SCHEMA_VERSION") or "1.1"
    VALIDATION_ROSETTA_XSD_NAME = \
        os.environ.get("VALIDATION_ROSETTA_XSD_NAME") \
        or "Ex Libris, Rosetta METS v7.3"
    VALIDATION_ROSETTA_METS_XSD_FALLBACK = \
        os.environ.get("VALIDATION_ROSETTA_METS_XSD_FALLBACK")
    VALIDATION_ROSETTA_METS_XML_SCHEMA_VERSION_FALLBACK = \
        os.environ.get("VALIDATION_ROSETTA_METS_XML_SCHEMA_VERSION_FALLBACK") \
        or "1.1"
    VALIDATION_ROSETTA_XSD_NAME_FALLBACK = \
        os.environ.get("VALIDATION_ROSETTA_XSD_NAME_FALLBACK") \
        or "Rosetta METS (fallback)"
    # dc.xml
    VALIDATION_DCXML_ACTIVE = \
        (int(os.environ.get("VALIDATION_DCXML_ACTIVE") or 1)) == 1
    VALIDATION_DCXML_XSD = \
        os.environ.get("VALIDATION_DCXML_XSD") \
        or Path(dcm_sip_builder.__file__).parent / "static" / "dcxml" / "dc.xsd"
    VALIDATION_DCXML_XML_SCHEMA_VERSION = \
        os.environ.get("VALIDATION_DCXML_XML_SCHEMA_VERSION") or "1.1"
    VALIDATION_DCXML_NAME = \
        os.environ.get("VALIDATION_DCXML_NAME") \
        or f"LZV.nrw, dc.xml schema v{version('dcm-sip-builder')}"

    # ------ IDENTIFY ------
    # generate self-description
    API_DOCUMENT = \
        Path(dcm_sip_builder_api.__file__).parent / "openapi.yaml"
    API = yaml.load(
        API_DOCUMENT.read_text(encoding="utf-8"),
        Loader=yaml.SafeLoader
    )

    def set_identity(self) -> None:
        super().set_identity()
        self.CONTAINER_SELF_DESCRIPTION["description"] = (
            "This API provides endpoints for building SIPs."
        )

        # version
        self.CONTAINER_SELF_DESCRIPTION["version"]["api"] = (
            self.API["info"]["version"]
        )
        self.CONTAINER_SELF_DESCRIPTION["version"]["app"] = version(
            "dcm-sip-builder"
        )

        # configuration
        # - settings
        settings = self.CONTAINER_SELF_DESCRIPTION["configuration"]["settings"]
        settings["build"] = {
            "output": str(self.SIP_OUTPUT),
        }
        settings["validation"] = {
            "dcxml": {
                "active": self.VALIDATION_DCXML_ACTIVE,
            },
            "mets": {
                "active": self.VALIDATION_ROSETTA_METS_ACTIVE,
            }
        }
        # - plugins
        plugins = {}
        if self.VALIDATION_DCXML_ACTIVE:
            settings["validation"]["dcxml"]["plugin"] = (
                self.VALIDATION_DCXML_NAME
            )
            plugins[self.VALIDATION_DCXML_NAME] = {
                "name": self.VALIDATION_DCXML_NAME,
                "description":
                    "Validates the contents of a SIP's 'dc.xml'-file. "
                    + f"XSD: '{str(self.VALIDATION_DCXML_XSD)}', XML schema "
                    + f"version: {self.VALIDATION_DCXML_XML_SCHEMA_VERSION}"
            }
        if self.VALIDATION_ROSETTA_METS_ACTIVE:
            settings["validation"]["mets"]["plugin"] = (
                self.VALIDATION_ROSETTA_XSD_NAME
            )
            plugins[self.VALIDATION_ROSETTA_XSD_NAME] = {
                "name": self.VALIDATION_ROSETTA_XSD_NAME,
                "description":
                    "Validates the contents of a SIP's 'ie.xml'-file. "
                    + f"XSD: '{str(self.VALIDATION_ROSETTA_METS_XSD)}', XML schema "
                    + f"version: {self.VALIDATION_ROSETTA_METS_XML_SCHEMA_VERSION}"
            }
        if self.VALIDATION_ROSETTA_METS_XSD_FALLBACK is not None:
            settings["validation"]["mets"]["plugin_fallback"] = (
                self.VALIDATION_ROSETTA_XSD_NAME_FALLBACK
            )
            plugins[self.VALIDATION_ROSETTA_XSD_NAME_FALLBACK] = {
                "name": self.VALIDATION_ROSETTA_XSD_NAME_FALLBACK,
                "description":
                    "Validates the contents of a SIP's 'ie.xml'-file. "
                    + f"XSD: '{str(self.VALIDATION_ROSETTA_METS_XSD_FALLBACK)}', XML schema "
                    + f"version: {self.VALIDATION_ROSETTA_METS_XML_SCHEMA_VERSION_FALLBACK}"
            }
        self.CONTAINER_SELF_DESCRIPTION["configuration"]["plugins"] = plugins
