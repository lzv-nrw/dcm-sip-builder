"""Input handlers for the 'DCM SIP Builder'-app."""

from pathlib import Path

from data_plumber_http import Property, Object, Url
from dcm_common.services import TargetPath, UUID

from dcm_sip_builder.models import Target, BuildConfig


def get_build_handler(cwd: Path):
    """
    Returns parameterized handler
    """
    return Object(
        properties={
            Property("build", required=True): Object(
                model=BuildConfig,
                properties={
                    Property("target", required=True): Object(
                        model=Target,
                        properties={
                            Property("path", required=True):
                                TargetPath(
                                    _relative_to=cwd, cwd=cwd, is_dir=True
                                )
                        },
                        accept_only=["path"]
                    ),
                },
                accept_only=[
                    "target",
                ]
            ),
            Property("token"): UUID(),
            Property("callbackUrl", name="callback_url"):
                Url(schemes=["http", "https"])
        },
        accept_only=["build", "token", "callbackUrl"]
    ).assemble()
