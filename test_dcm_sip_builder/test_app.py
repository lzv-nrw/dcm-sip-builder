"""
Test `dcm-sip-builder` flask app.
"""

import pytest

from dcm_sip_builder import app_factory


def test_iexml_error_on_missing_xsd(testing_config):
    """Test whether a missing XML schema causes `RuntimeError`."""
    testing_config.VALIDATION_ROSETTA_METS_XSD = \
        "https://lzv.nrw/rosetta_mets.xsd"
    config = testing_config()
    with pytest.raises(RuntimeError):
        app_factory(config, block=True)


def test_iexml_error_on_missing_xsd_and_fallback(testing_config):
    """
    Test whether a missing both primary and fallback XML schema causes
    `RuntimeError`.
    """
    testing_config.VALIDATION_ROSETTA_METS_XSD = \
        "https://lzv.nrw/rosetta_mets.xsd"
    testing_config.VALIDATION_ROSETTA_METS_XSD_FALLBACK = \
        "https://lzv.nrw/rosetta_mets_fallback.xsd"
    with pytest.raises(RuntimeError):
        app_factory(testing_config(), block=True)


def test_iexml_disable_validation(testing_config):
    """
    Test whether the disable-switch for the Rosetta-METS validation
    works as expected.
    """
    testing_config.VALIDATION_ROSETTA_METS_XSD = \
        "https://lzv.nrw/rosetta_mets.xsd"
    testing_config.VALIDATION_ROSETTA_METS_ACTIVE = False
    app_factory(testing_config(), block=True)


def test_dcxml_error_on_missing_xsd(testing_config):
    """Test whether a missing XML schema causes `RuntimeError`."""
    testing_config.VALIDATION_DCXML_XSD = \
        "https://lzv.nrw/dc.xsd"
    with pytest.raises(RuntimeError):
        app_factory(testing_config(), block=True)
