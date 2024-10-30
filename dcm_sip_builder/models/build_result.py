"""
BuildResult data-model definition
"""

from typing import Optional
from pathlib import Path
from dataclasses import dataclass

from dcm_common.models import DataModel


@dataclass
class BuildResult(DataModel):
    """
    Build result `DataModel`

    Keyword arguments:
    path -- path to output directory relative to shared file system
    success -- overall success of the job
    """

    path: Optional[Path] = None
    success: Optional[bool] = None

    @DataModel.serialization_handler("path")
    @classmethod
    def path_serialization_handler(cls, value):
        """Performs `path`-serialization."""
        if value is None:
            DataModel.skip()
        return str(value)

    @DataModel.deserialization_handler("path")
    @classmethod
    def path_deserialization(cls, value):
        """Performs `path`-deserialization."""
        if value is None:
            DataModel.skip()
        return Path(value)
