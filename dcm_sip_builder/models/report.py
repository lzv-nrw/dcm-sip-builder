"""
Report data-model definition
"""

from dataclasses import dataclass, field

from dcm_common.orchestra import Report as BaseReport

from dcm_sip_builder.models.build_result import BuildResult


@dataclass
class Report(BaseReport):
    data: BuildResult = field(default_factory=BuildResult)
