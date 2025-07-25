# Changelog

## [2.1.0] - 2025-07-25

### Changed

- moved xml-validator to the `dcm-common` project and imported from there

### Added

- added support for `significant_properties.xml`

### Fixed

- fixed initialization of ScalableOrchestrator with ORCHESTRATION_PROCESSES

## [2.0.1] - 2024-11-21

### Changed

- updated package metadata, Dockerfiles, and README

## [2.0.0] - 2024-10-16

### Changed

- **Breaking:** implemented changes of API v2 (`9a381e8a`)
- migrated to `dcm-common` (scalable orchestration and related components; latest `DataModel`) (`9a381e8a`)

## [1.0.0] - 2024-07-24

### Changed

- improved report.progress.verbose and log messages (`12cb06e7`, `dfc851b1`)
- added xpath-info to validation error messages (`a845d7c7`)
- **Breaking:** updated to API v1 (`b319264b`, `5a6efae9`)

### Fixed

- fixed bad values for `data.success` in intermediate reports (`5a6efae9`)
- fixed conformity with Rosetta-METS schema regarding `amdSec/mets:sourceMD` (omit if missing source metadata) (`104c625e`)
- fixed issue with parsing BagIt-Bag manifest files (`0454f935`, `ce8feb2d`)
- fixed issue with generating Rosetta-METS when source metadata contains empty tags (`b20082e0`)

## [0.1.2] - 2024-06-28

### Fixed

- execute build even if compiler returns with error (`bc6147c5`)
- omit preservationType in ie.xml if no info available (`c5032e05`)

## [0.1.0] - 2024-05-29

### Changed

- initial release of dcm-sip-builder
