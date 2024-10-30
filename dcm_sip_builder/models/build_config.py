"""
BuildConfig data-model definition
"""

from dataclasses import dataclass

from dcm_common.models import DataModel

from dcm_sip_builder.models.target import Target


@dataclass
class BuildConfig(DataModel):
    """
    BuildConfig `DataModel`

    Keyword arguments:
    target -- `Target`-object pointing to IE to be built
    """

    target: Target
