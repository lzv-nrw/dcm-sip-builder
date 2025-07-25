"""
Build View-class definition
"""

from typing import Optional
import sys

from flask import Blueprint, jsonify
from data_plumber_http.decorators import flask_handler, flask_args, flask_json
from dcm_common import LoggingContext as Context
from dcm_common.util import get_output_path
from dcm_common.orchestration import JobConfig, Job
from dcm_common import services
from dcm_common.xml import XMLValidator

from dcm_sip_builder.config import AppConfig
from dcm_sip_builder.handlers import get_build_handler
from dcm_sip_builder.models import BuildConfig, IP, SIP
from dcm_sip_builder.components import (
    DCCompiler, IECompiler, Builder
)


class BuildView(services.OrchestratedView):
    """View-class for sip-building."""

    NAME = "sip-build"

    def __init__(
        self, config: AppConfig, *args, **kwargs
    ) -> None:
        super().__init__(config, *args, **kwargs)

        # initialize components
        self.dc_compiler = DCCompiler()
        self.ie_compiler = IECompiler()
        self.builder = Builder()
        if self.config.VALIDATION_ROSETTA_METS_ACTIVE:
            self.rosetta_mets_validator, error_msg = self.make_validator()
            if self.rosetta_mets_validator is None:
                raise RuntimeError(
                    "Unable to initialize Rosetta METS-validator from "
                    + f"""'{
                            self.config.VALIDATION_ROSETTA_METS_XSD_FALLBACK
                            or self.config.VALIDATION_ROSETTA_METS_XSD
                        }': """
                    + f"{error_msg} "
                    + "Consider disabling option 'VALIDATION_ROSETTA_METS_ACTIVE'"
                    + (
                        " or setting 'VALIDATION_ROSETTA_METS_XSD_FALLBACK'"
                        if self.config.VALIDATION_ROSETTA_METS_XSD_FALLBACK is None
                        else ""
                    )
                    + "."
                )
        else:
            self.rosetta_mets_validator = None
        if self.config.VALIDATION_DCXML_ACTIVE:
            try:
                self.dcxml_validator = XMLValidator(
                    self.config.VALIDATION_DCXML_XSD,
                    version=self.config.VALIDATION_DCXML_XML_SCHEMA_VERSION,
                    schema_name=self.config.VALIDATION_DCXML_NAME
                )
            except ValueError as exc_info:
                raise RuntimeError(
                    "Unable to initialize dc.xml-validator from "
                    + f"""'{
                            self.config.VALIDATION_DCXML_XSD
                        }': """
                    + "Consider disabling option 'VALIDATION_DCXML_ACTIVE'."
                ) from exc_info
        else:
            self.dcxml_validator = None

    def configure_bp(self, bp: Blueprint, *args, **kwargs) -> None:
        @bp.route("/build", methods=["POST"])
        @flask_handler(  # unknown query
            handler=services.no_args_handler,
            json=flask_args,
        )
        @flask_handler(  # process sip-build
            handler=get_build_handler(self.config.FS_MOUNT_POINT),
            json=flask_json,
        )
        def build(
            build: BuildConfig,
            callback_url: Optional[str] = None
        ):
            """Submit IP for SIP building."""
            token = self.orchestrator.submit(
                JobConfig(
                    request_body={
                        "build": build.json,
                        "callback_url": callback_url
                    },
                    context=self.NAME
                )
            )
            return jsonify(token.json), 201

        self._register_abort_job(bp, "/build")

    def get_job(self, config: JobConfig) -> Job:
        return Job(
            cmd=lambda push, data: self.build(
                push, data, BuildConfig.from_json(
                    config.request_body["build"]
                )
            ),
            hooks={
                "startup": services.default_startup_hook,
                "success": services.default_success_hook,
                "fail": services.default_fail_hook,
                "abort": services.default_abort_hook,
                "completion": services.termination_callback_hook_factory(
                    config.request_body.get("callback_url", None),
                )
            },
            name="SIP Builder"
        )

    def build(
        self, push, report, build_config: BuildConfig,
    ):
        """
        Job instructions for the '/build' endpoint.

        Orchestration standard-arguments:
        push -- (orchestration-standard) push `report` to host process
        report -- (orchestration-standard) common report-object shared
                  via `push`

        Keyword arguments:
        build_config -- a `BuildConfig`-config
        """

        # set progress info
        report.progress.verbose = "preparing output destination"
        push()

        # find valid SIP-output path
        report.data.path = get_output_path(
            self.config.SIP_OUTPUT
        )
        push()
        if report.data.path is None:
            report.data.success = False
            report.log.log(
                Context.ERROR,
                body="Unable to generate output directory in "
                + f"'{self.config.FS_MOUNT_POINT / self.config.SIP_OUTPUT}'"
                + "(maximum retries exceeded)."
            )
            push()
            return

        # set progress info
        report.progress.verbose = (
            f"reading IP '{build_config.target.path}'"
        )
        push()

        ip = IP(build_config.target.path)

        # set progress info
        report.progress.verbose = (
            f"compiling SIP metadata from IP '{build_config.target.path}'"
        )
        push()

        # compile metadata
        dc = self.dc_compiler.compile_as_string(ip)
        report.log.merge(self.dc_compiler.log)
        push()
        ie = self.ie_compiler.compile_as_string(ip)
        report.log.merge(self.ie_compiler.log)
        push()

        # validation
        for validator, target, target_name, active in [
            (
                self.rosetta_mets_validator, ie, "ie.xml",
                self.config.VALIDATION_ROSETTA_METS_ACTIVE
            ),
            (
                self.dcxml_validator, dc, "dc.xml",
                self.config.VALIDATION_DCXML_ACTIVE
            ),
        ]:
            if not active:
                continue
            # set progress info
            report.progress.verbose = (
                f"validating '{target_name}' of "
                + f"SIP '{report.data.path}'"
            )
            push()

            report.log.merge(
                validator.validate(target, xml_name=target_name).log
            )
            push()

        # set progress info
        report.progress.verbose = (
            f"building SIP '{report.data.path}'"
        )
        push()

        # build SIP
        report.data.success = all([
            Context.ERROR not in report.log,
            self.builder.build(ip, ie, dc, SIP(report.data.path))
        ])
        report.log.merge(self.builder.log)
        push()

    def make_validator(self) -> tuple[Optional[XMLValidator], str]:
        """
        Returns a tuple of `XMLValidator` instance based on `self.config`
        and message.

        If primary source is unavailable,
        print warning and resort to secondary.
        """
        # try loading primary schema
        try:
            return XMLValidator(
                self.config.VALIDATION_ROSETTA_METS_XSD,
                version=self.config.VALIDATION_ROSETTA_METS_XML_SCHEMA_VERSION,
                schema_name=self.config.VALIDATION_ROSETTA_XSD_NAME
            ), ""
        except ValueError as exc_info:
            if "Unable to load schema" in str(exc_info) and (
                self.config.VALIDATION_ROSETTA_METS_XSD_FALLBACK is not None
            ):
                # try fallback
                msg = (
                    Context.WARNING.fancy.replace("WARNINGS", "WARNING")
                    + ": Unable to initialize Rosetta METS-validator from "
                    + f"'{self.config.VALIDATION_ROSETTA_METS_XSD}': "
                    + f"{str(exc_info)} Trying to load fallback.."
                )
                print(msg, file=sys.stderr)
                try:
                    return XMLValidator(
                        self.config.VALIDATION_ROSETTA_METS_XSD_FALLBACK,
                        version=self.config.VALIDATION_ROSETTA_METS_XML_SCHEMA_VERSION_FALLBACK,
                        schema_name=self.config.VALIDATION_ROSETTA_XSD_NAME_FALLBACK
                    ), msg
                except ValueError as exc_info2:
                    if "Unable to load schema" in str(exc_info2):
                        pass
            return None, str(exc_info)
