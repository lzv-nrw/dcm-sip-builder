from setuptools import setup

setup(
    version="2.0.1",
    name="dcm-sip-builder",
    description="flask app implementing the DCM SIP Builder API",
    author="LZV.nrw",
    license="MIT",
    python_requires=">=3.10",
    install_requires=[
        "flask==3.*",
        "lxml==5.*",
        "PyYAML==6.*",
        "xmlschema>=3.3,<4",
        "data-plumber-http>=1.0.0,<2",
        "dcm-common[services, db, orchestration]>=3.11.0,<4",
        "dcm-sip-builder-api>=2.1.0,<3",
    ],
    packages=[
        "dcm_sip_builder",
        "dcm_sip_builder.models",
        "dcm_sip_builder.views",
        "dcm_sip_builder.components"
    ],
    include_package_data=True,
    extras_require={
        "cors": ["Flask-CORS==4"],
    },
    setuptools_git_versioning={
          "enabled": True,
          "version_file": "VERSION",
          "count_commits_from_version_file": True,
          "dev_template": "{tag}.dev{ccount}",
    },
)
