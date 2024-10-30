"""
This module defines the `Builder` component of the SIP Builder-app.
"""

from pathlib import Path
from shutil import copytree

from dcm_common import LoggingContext as Context, Logger

from dcm_sip_builder.models import SIP, IP


class Builder:
    """
    A `Builder` can be used to assemble a `SIP` by providing a source
    `IP` and appropriate metadata as string.
    """
    TAG: str = "SIP Builder"

    def __init__(self) -> None:
        self.log = Logger(default_origin=self.TAG)

    def build(self, ip: IP, ie: str, dc: str, sip: SIP) -> bool:
        """
        Assemble `sip` from `ip` as well as metadata given in `ie`
        ('content/ie.xml') and `dc` ('dc.xml'). Returns `True` on
        success.

        Keyword arguments:
        ip -- `IP` object for building the SIP
        ie -- ie.xml-metadata of the given SIP
        dc -- dc.xml-metadata of the given SIP
        sip -- `SIP` object to be built
        """
        self.log = Logger(default_origin=self.TAG)
        sip.built = \
            self.write_metadata(ie, dc, sip) and self.write_payload(ip, sip)
        if sip.built:
            self.log.log(
                Context.INFO,
                body=f"Successfully assembled SIP at '{sip.path}'."
            )
        else:
            self.log.log(
                Context.INFO,
                body="No SIP has been built."
            )
        return sip.built

    def write_payload(self, ip: IP, sip: SIP) -> bool:
        """
        Copy payload from source ip to destination sip.

        Keyword arguments:
        ip -- `IP` object for building the SIP
        sip -- `SIP` object to be built
        """
        src = ip.path / "data"
        dst = sip.path / "content" / "streams"
        try:
            copytree(src, dst)
            return True
        except FileNotFoundError:
            self.log.log(
                Context.ERROR,
                body=f"Writing payload failed, source '{src}' not found."
            )
        except FileExistsError:
            self.log.log(
                Context.ERROR,
                body=f"Writing payload failed, target '{dst}' already exists."
            )
        return False

    def _write_metadata(self, metadata: str, dst: Path) -> bool:
        try:
            dst.parent.mkdir(exist_ok=True, parents=False)
        except FileNotFoundError as exc_info:
            self.log.log(
                Context.ERROR,
                body=f"Unable to write metadata '{dst}' ({exc_info})."
            )
            return False
        dst.write_text(
            metadata,
            encoding="utf-8"
        )
        return True

    def write_metadata(self, ie: str, dc: str, sip: SIP) -> bool:
        """
        Write metadata from string to destination sip.

        Keyword arguments:
        ie -- ie.xml-metadata of the given SIP
        dc -- dc.xml-metadata of the given SIP
        sip -- `SIP` object to be built
        """

        return self._write_metadata(ie, sip.path / "content" / "ie.xml") \
            and self._write_metadata(dc, sip.path / "dc.xml")
