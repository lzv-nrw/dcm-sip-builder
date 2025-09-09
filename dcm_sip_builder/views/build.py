"""
Build View-class definition
"""

from typing import Optional
import sys
import os
from uuid import uuid4

from flask import Blueprint, jsonify, Response, request
from data_plumber_http.decorators import flask_handler, flask_args, flask_json
from dcm_common import LoggingContext as Context
from dcm_common.util import get_output_path
from dcm_common.orchestra import JobConfig, JobContext, JobInfo
from dcm_common import services
from dcm_common.xml import XMLValidator

from dcm_sip_builder.config import AppConfig
from dcm_sip_builder.handlers import get_build_handler
from dcm_sip_builder.models import BuildConfig, IP, SIP, Report
from dcm_sip_builder.components import DCCompiler, IECompiler, Builder


class BuildView(services.OrchestratedView):
    """View-class for sip-building."""

    NAME = "sip-build"

    def __init__(self, config: AppConfig, *args, **kwargs) -> None:
        super().__init__(config, *args, **kwargs)

        # initialize components
        self.dc_compiler = DCCompiler()
        self.ie_compiler = IECompiler(
            self.config.CUSTOM_FIXITY_SHA512_PLUGIN_NAME
        )
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
                        if self.config.VALIDATION_ROSETTA_METS_XSD_FALLBACK
                        is None
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
                    schema_name=self.config.VALIDATION_DCXML_NAME,
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

    def register_job_types(self):
        self.config.worker_pool.register_job_type(
            self.NAME, self.build, Report
        )

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
            token: Optional[str] = None,
            callback_url: Optional[str] = None,
        ):
            """Submit IP for SIP building."""
            try:
                token = self.config.controller.queue_push(
                    token or str(uuid4()),
                    JobInfo(
                        JobConfig(
                            self.NAME,
                            original_body=request.json,
                            request_body={
                                "build": build.json,
                                "callback_url": callback_url,
                            },
                        ),
                        report=Report(
                            host=request.host_url, args=request.json
                        ),
                    ),
                )
            # pylint: disable=broad-exception-caught
            except Exception as exc_info:
                return Response(
                    f"Submission rejected: {exc_info}",
                    mimetype="text/plain",
                    status=500,
                )

            return jsonify(token.json), 201

        self._register_abort_job(bp, "/build")

    def build(self, context: JobContext, info: JobInfo):
        """Job instructions for the '/prepare' endpoint."""
        os.chdir(self.config.FS_MOUNT_POINT)
        build_config = BuildConfig.from_json(info.config.request_body["build"])
        info.report.log.set_default_origin("SIP Builder")

        # set progress info
        info.report.progress.verbose = "preparing output destination"
        context.push()

        # find valid SIP-output path
        info.report.data.path = get_output_path(self.config.SIP_OUTPUT)
        context.push()
        if info.report.data.path is None:
            info.report.data.success = False
            info.report.log.log(
                Context.ERROR,
                body="Unable to generate output directory in "
                + f"'{self.config.FS_MOUNT_POINT / self.config.SIP_OUTPUT}'"
                + "(maximum retries exceeded).",
            )
            context.push()

            # make callback; rely on _run_callback to push progress-update
            info.report.progress.complete()
            self._run_callback(
                context, info, info.config.request_body.get("callback_url")
            )
            return

        # set progress info
        info.report.progress.verbose = (
            f"reading IP '{build_config.target.path}'"
        )
        context.push()

        ip = IP(build_config.target.path)

        # set progress info
        info.report.progress.verbose = (
            f"compiling SIP metadata from IP '{build_config.target.path}'"
        )
        context.push()

        # compile metadata
        dc = self.dc_compiler.compile_as_string(ip)
        info.report.log.merge(self.dc_compiler.log)
        context.push()
        ie = self.ie_compiler.compile_as_string(ip)
        info.report.log.merge(self.ie_compiler.log)
        context.push()

        # validation
        for validator, target, target_name, active in [
            (
                self.rosetta_mets_validator,
                ie,
                "ie.xml",
                self.config.VALIDATION_ROSETTA_METS_ACTIVE,
            ),
            (
                self.dcxml_validator,
                dc,
                "dc.xml",
                self.config.VALIDATION_DCXML_ACTIVE,
            ),
        ]:
            if not active:
                continue
            # set progress info
            info.report.progress.verbose = (
                f"validating '{target_name}' of "
                + f"SIP '{info.report.data.path}'"
            )
            context.push()

            info.report.log.merge(
                validator.validate(target, xml_name=target_name).log
            )
            context.push()

        # set progress info
        info.report.progress.verbose = (
            f"building SIP '{info.report.data.path}'"
        )
        context.push()

        # build SIP
        info.report.data.success = all(
            [
                Context.ERROR not in info.report.log,
                self.builder.build(ip, ie, dc, SIP(info.report.data.path)),
            ]
        )
        info.report.log.merge(self.builder.log)
        context.push()

        # make callback; rely on _run_callback to push progress-update
        info.report.progress.complete()
        self._run_callback(
            context, info, info.config.request_body.get("callback_url")
        )

    def make_validator(self) -> tuple[Optional[XMLValidator], str]:
        """
        Returns a tuple of `XMLValidator` instance based on `self.config`
        and message.

        If primary source is unavailable,
        print warning and resort to secondary.
        """
        # try loading primary schema
        try:
            return (
                XMLValidator(
                    self.config.VALIDATION_ROSETTA_METS_XSD,
                    version=self.config.VALIDATION_ROSETTA_METS_XML_SCHEMA_VERSION,
                    schema_name=self.config.VALIDATION_ROSETTA_XSD_NAME,
                ),
                "",
            )
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
                    return (
                        XMLValidator(
                            self.config.VALIDATION_ROSETTA_METS_XSD_FALLBACK,
                            version=self.config.VALIDATION_ROSETTA_METS_XML_SCHEMA_VERSION_FALLBACK,
                            schema_name=self.config.VALIDATION_ROSETTA_XSD_NAME_FALLBACK,
                        ),
                        msg,
                    )
                except ValueError as exc_info2:
                    if "Unable to load schema" in str(exc_info2):
                        pass
            return None, str(exc_info)
