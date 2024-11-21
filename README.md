# Digital Curation Manager - SIP Builder

The 'DCM SIP Builder'-API provides functionality to convert Information Packages (IPs) into Submission Information Packages (SIPs).
This repository contains the corresponding Flask app definition.
For the associated OpenAPI-document, please refer to the sibling package [`dcm-sip-builder-api`](https://github.com/lzv-nrw/dcm-sip-builder-api).

The contents of this repository are part of the [`Digital Curation Manager`](https://github.com/lzv-nrw/digital-curation-manager).

## Local install
Make sure to include the extra-index-url `https://zivgitlab.uni-muenster.de/api/v4/projects/9020/packages/pypi/simple` in your [pip-configuration](https://pip.pypa.io/en/stable/cli/pip_install/#finding-packages) to enable an automated install of all dependencies.
Using a virtual environment is recommended.

1. Install with
   ```
   pip install .
   ```
1. Configure service environment to fit your needs ([see here](#environmentconfiguration)).
1. Run app as
   ```
   flask run --port=8080
   ```
1. To manually use the API, either run command line tools like `curl` as, e.g.,
   ```
   curl -X 'POST' \
     'http://localhost:8080/build' \
     -H 'accept: application/json' \
     -H 'Content-Type: application/json' \
     -d '{
     "build": {
       "target": {
         "path": "jobs/abcde-12345-fghijk-67890"
       }
     }
   }'
   ```
   or run a gui-application, like Swagger UI, based on the OpenAPI-document provided in the sibling package [`dcm-sip-builder-api`](https://github.com/lzv-nrw/dcm-sip-builder-api).

## Run with docker compose
Simply run
```
docker compose up
```
By default, the app listens on port 8080.
The docker volume `file_storage` is automatically created and data will be written in `/file_storage`.
To rebuild an already existing image, run `docker compose build`.

Additionally, a Swagger UI is hosted at
```
http://localhost/docs
```

Afterwards, stop the process and enter `docker compose down`.

## Tests
Install additional dev-dependencies with
```
pip install -r dev-requirements.txt
```
Run unit-tests with
```
pytest -v -s
```

## Environment/Configuration
Service-specific environment variables are

### Build
* `SIP_OUTPUT` [DEFAULT "sip/"] output directory for building SIPs (relative to `FS_MOUNT_POINT`)

### Validation
#### Rosetta METS
* `VALIDATION_ROSETTA_METS_ACTIVE` [DEFAULT 1]: enable or disable validation of generated Rosetta METS-`ie.xml`
* `VALIDATION_ROSETTA_METS_XSD` [DEFAULT "https://developers.exlibrisgroup.com/wp-content/uploads/2022/06/mets_rosetta.xsd"]: XSD-document to be validated against
* `VALIDATION_ROSETTA_METS_XML_SCHEMA_VERSION` [DEFAULT "1.1"]: XML schema version used by `VALIDATION_ROSETTA_METS_XSD`
* `VALIDATION_ROSETTA_XSD_NAME` [DEFAULT "Ex Libris, Rosetta METS v7.3"]: verbose schema name for validation with `VALIDATION_ROSETTA_METS_XSD` (used in logs)
#### Rosetta METS - Fallback
* `VALIDATION_ROSETTA_METS_XSD_FALLBACK` [DEFAULT `None`]: XSD-document to be validated against
* `VALIDATION_ROSETTA_METS_XML_SCHEMA_VERSION_FALLBACK` [DEFAULT "1.1"]: XML schema version used by `VALIDATION_ROSETTA_METS_XSD_FALLBACK`
* `VALIDATION_ROSETTA_XSD_NAME_FALLBACK` [DEFAULT "Rosetta METS (fallback)"]: verbose schema name for validation with `VALIDATION_ROSETTA_METS_XSD_FALLBACK` (used in logs)
#### dc.xml
* `VALIDATION_DCXML_ACTIVE` [DEFAULT 1]: enable or disable validation of generated `dc.xml`
* `VALIDATION_DCXML_XSD` [DEFAULT "dcm_sip_builder/static/dcxml/dc.xsd"]: XSD-document to be validated against
* `VALIDATION_DCXML_XML_SCHEMA_VERSION` [DEFAULT "1.1"]: XML schema version used by `VALIDATION_DCXML_XSD`
* `VALIDATION_DCXML_NAME` [DEFAULT "LZV.nrw, dc.xml schema v.."]: verbose schema name for validation with `VALIDATION_DCXML_XSD` (used in logs)

Additionally this service provides environment options for
* `BaseConfig`,
* `OrchestratedAppConfig`, and
* `FSConfig`

as listed [here](https://github.com/lzv-nrw/dcm-common#app-configuration).

# Contributors
* Sven Haubold
* Orestis Kazasidis
* Stephan Lenartz
* Kayhan Ogan
* Michael Rahier
* Steffen Richters-Finger
* Malte Windrath
* Roman Kudinov