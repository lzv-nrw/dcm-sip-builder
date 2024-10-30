# dcm-sip-builder

The 'DCM SIP Builder'-service provides functionality to convert Information Packages (IPs) into Submission Information Packages (SIPs).

## Run locally
Running in a `venv` is recommended.

To test the app locally,
1. install with
   ```
   pip install .
   ```
1. Configure service environment to your needs ([see here](#environmentconfiguration)).
1. run as
   ```
   flask run --port=8080
   ```
1. use either commandline tools like `curl`,
   ```
   curl -X 'POST' \
     'http://localhost:8080/build' \
     -H 'accept: application/json' \
     -H 'Content-Type: application/json' \
     -d '{
     "build": {
       "target": {
         "path": "file_storage/test_ip"
       }
     }
   }'
   ```
   or a gui like [swagger-ui](https://github.com/lzv-nrw/dcm-sip-builder-api/-/blob/dev/dcm_sip_builder_api/openapi.yaml?ref_type=heads) (see sibling package [`dcm-sip-builder-api`](https://github.com/lzv-nrw/dcm-sip-builder-api)) to submit jobs

A sample IP that can be converted to a SIP can be found in `test_dcm_sip_builder/fixtures`.

## Run with Docker
### Container setup
Use the `compose.yml` to start the `DCM SIP Builder`-container as a service:
```
docker compose up
```
(to rebuild run `docker compose build`).

A Swagger UI is hosted at
```
http://localhost/docs
```
while (by-default) the app listens to port `8080`.

Afterwards, stop the process for example with `Ctrl`+`C` and enter `docker compose down`.

The build process requires authentication with `zivgitlab.uni-muenster.de` in order to gain access to the required python dependencies.
The Dockerfiles are setup to use the information from `~/.netrc` for this authentication (a gitlab api-token is required).

### File system setup
The currently used docker volume is set up automatically on `docker compose up`. However, in order to move data from the local file system into the container, the container also needs to mount this local file system (along with the volume). To this end, the `compose.yml` needs to be modified before startup with
```
    ...
      - file_storage:/file_storage
      - type: bind
        source: ./test_dcm_sip_builder/fixtures
        target: /local
    ports:
      ...
```
By then opening an interactive session in the container (i.e., after running the compose-script) with
```
docker exec -it <container-id> sh
```
the example IP from the test-related fixtures-directory can be copied over to the volume:
```
cp -r /local/* /file_storage/
```
(The modification to the file `compose.yml` can be reverted after copying.)

## Tests
Install additional dependencies from `dev-requirements.txt`.
Run unit-tests with
```
pytest -v -s --cov dcm_sip_builder
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

as listed [here](https://github.com/lzv-nrw/dcm-common/-/tree/dev?ref_type=heads#app-configuration).

# Contributors
* Sven Haubold
* Orestis Kazasidis
* Stephan Lenartz
* Kayhan Ogan
* Michael Rahier
* Steffen Richters-Finger
* Malte Windrath
