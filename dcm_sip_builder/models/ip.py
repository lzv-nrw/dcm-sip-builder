"""
IP data-model definition
"""

from typing import Optional
from pathlib import Path

from lxml import etree as et
from dcm_common import LoggingContext as Context, Logger
from dcm_common.util import list_directory_content


PATH_BAGINFO = "bag-info.txt"
PATH_MANIFESTS = "manifest"
PATH_PAYLOAD = "data"
PATH_DC_XML = "meta/dc.xml"
SIGPROP_PREMIS_NAMESPACE = "{http://www.loc.gov/premis/v3}"
PATH_SIGNIFICANT_PROPERTIES_XML = "meta/significant_properties.xml"
PATH_EVENTS = "meta/events.xml"
PATH_SOURCE_METADATA = "meta/source_metadata.xml"


class IP:
    """
    Class to represent an Information Package (IP).

    Required attribute:
    path -- path to the IP directory
    ignore_errors -- if True, errors are ignored; otherwise,
                     an AttributeError is raised. (default False)
    """

    def __init__(
        self,
        path: Path,
        ignore_errors: bool = False
    ) -> None:

        self.path = path
        self.ignore_errors = ignore_errors
        self._log = Logger(default_origin=f"IP Object {self.path}")

        # bag-info.txt is required
        self.baginfo: Optional[dict] = self._load_baginfo()

        # at least one manifest file is required
        self.manifests: Optional[dict] = self._load_manifests(
            filename_prefix=PATH_MANIFESTS
        )

        # the xml files are optional
        self.source_metadata = self._load_xml(
            self.path / PATH_SOURCE_METADATA
        )
        self.dc_xml = self._load_xml(
            self.path / PATH_DC_XML
        )
        self.significant_properties = self._load_significant_properties(
            self._load_xml(self.path / PATH_SIGNIFICANT_PROPERTIES_XML)
        )
        self.events = self._load_xml(
            self.path / PATH_EVENTS
        )

        self.payload_files = self._get_payload_files()

        # Raise any errors from the log
        self._complete = True
        if "ERROR" in self._log.json:
            self._complete = False
            if not self.ignore_errors:
                self._raise_errors()

    def _raise_errors(self) -> None:
        msg = str(self._log.pick(Context.ERROR))
        raise AttributeError(
            "IP Object cannot be instantiated properly.\n"
            + msg
        )

    def _load_baginfo(self) -> Optional[dict[str, str | list[str]]]:
        """
        Load the bag-info.txt as dictionary.
        """
        path_baginfo = self.path / PATH_BAGINFO
        try:
            output_dict = {}
            with open(path_baginfo, "r", encoding="utf-8") as txt_file:
                for line in txt_file:
                    if line != "" and ":" in line:
                        (key, value) = line.split(":", 1)
                        key = key.rstrip().lstrip()
                        if value is not None:
                            value = value.rstrip().lstrip()
                        if key not in output_dict:
                            # Add key, value pair
                            output_dict[key] = value
                        else:
                            if not isinstance(output_dict[key], list):
                                # Convert the existing value into a list
                                output_dict[key] = [output_dict[key]]
                            # Append the value in the existing value
                            output_dict[key].append(value)
            return output_dict
        except Exception as exc_info:
            self._log.log(
                Context.ERROR,
                body=f"Unable to load file '{path_baginfo}': {exc_info}."
            )
            return None

    def _load_manifests(
        self,
        filename_prefix,
    ) -> Optional[dict[str, dict[str, str]]]:
        """
        Load all manifests or tag-manifests from one txt file for each
        algorithm based on a filename_prefix.

        Keyword argument:
        filename_prefix -- prefix to create the glob pattern for finding
                           the existing files
        """
        files = list_directory_content(
            self.path,
            pattern=filename_prefix + "-*.txt",
            condition_function=lambda p: p.is_file()
        )
        if len(files) > 0:
            d = {}
            for f in files:
                try:
                    alg = \
                        f.name[len(filename_prefix)+1:-4]
                    d[alg] = {
                        x[1]: x[0]
                        for x in map(
                            lambda line: line.split(maxsplit=1),
                            f.read_text(encoding="utf-8").strip().split("\n")
                        )
                    }
                except FileNotFoundError as exc_info:
                    self._log.log(
                        Context.ERROR,
                        body=f"Unable to load file '{f}': {exc_info}."
                    )
                    return None
            return d
        self._log.log(
            Context.ERROR,
            body=f"No file with prefix '{filename_prefix}' found."
        )
        return None

    def _load_xml(
        self,
        filepath
    ) -> Optional[et._ElementTree]:
        """
        Load an xml file from filepath as element tree

        Keyword argument:
        filepath -- path to the xml file
        """
        if filepath.is_file():
            try:
                parser = et.XMLParser(remove_blank_text=True)
                return et.parse(filepath, parser)
            except Exception as exc_info:
                self._log.log(
                    Context.ERROR,
                    body="Unable to load XML from "
                         + f"'{filepath.relative_to(self.path)}': {exc_info}."
                )
        return None

    def _get_payload_files(
        self
    ) -> dict[str, list[str] | dict[str, list[str]]]:
        """
        Returns a dictionary with the representations as keys and
        a list of the payload files as values.
        """

        payload_files: dict[str, list[str] | dict[str, list[str]]] = {
            "preservation_master": []
        }

        payload_path = self.path / PATH_PAYLOAD

        files = list_directory_content(
            payload_path / "preservation_master",
            pattern="**/*",
            condition_function=lambda p: p.is_file()
        )
        payload_files.update({
            "preservation_master": [
                str(f.relative_to(self.path)) for f in files
            ]
        })

        for d in ["modified_master", "derivative_copy"]:
            directory = payload_path / d
            if directory.is_dir():
                payload_files_rep: dict[str, list[str]] = {}
                reps = list_directory_content(
                    directory,
                    pattern="*",
                    condition_function=lambda p: p.is_dir()
                )
                for rep in reps:
                    files = list_directory_content(
                        rep,
                        pattern="**/*",
                        condition_function=lambda p: p.is_file()
                    )
                    payload_files_rep.update({
                        rep.name: [
                            str(f.relative_to(self.path)) for f in files
                        ]
                    })
                payload_files[d] = payload_files_rep
        return payload_files

    def _load_significant_properties(
        self, tree: Optional[et._ElementTree]
    ) -> Optional[dict]:
        """
        Returns 'significant_properties.xml'-metadata as dictionary or
        None if not existing.
        """
        # check if exists
        if tree is None:
            return None

        # parse
        try:
            significant_properties = tree.find(
                f"{SIGPROP_PREMIS_NAMESPACE}object"
            ).findall(
                f"{SIGPROP_PREMIS_NAMESPACE}significantProperties"
            )
        except AttributeError:
            return {}
        result = {}
        for p in significant_properties:
            type_ = p.find(
                f"{SIGPROP_PREMIS_NAMESPACE}significantPropertiesType"
            )
            value = p.find(
                f"{SIGPROP_PREMIS_NAMESPACE}significantPropertiesValue"
            )
            if type_ is None or value is None:
                continue
            result[type_.text] = value.text
        return result
