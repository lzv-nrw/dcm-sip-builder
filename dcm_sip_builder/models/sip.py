"""
SIP data-model definition
"""

from dataclasses import dataclass
from pathlib import Path

from dcm_common.models import DataModel


@dataclass
class SIP(DataModel):
    """
    Class to represent a Submission Information Package (SIP).

    Required attribute:
    path -- path to the SIP directory

    Property:
    built -- True if SIP has been built (default False)
    """

    path: Path
    built: bool = False

    @DataModel.serialization_handler("path")
    @classmethod
    def path_serialization(cls, value):
        """Performs `path`-serialization."""
        return str(value)

    @DataModel.deserialization_handler("path")
    @classmethod
    def path_deserialization(cls, value):
        """Performs `path`-deserialization."""
        return Path(value)
