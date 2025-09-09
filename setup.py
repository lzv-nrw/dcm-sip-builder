from setuptools import setup


setup(
    version="3.0.0",
    name="dcm-sip-builder",
    description="flask app implementing the DCM SIP Builder API",
    author="LZV.nrw",
    license="MIT",
    python_requires=">=3.10",
    install_requires=[
        "flask==3.*",
        "lxml==5.*",
        "PyYAML==6.*",
        "data-plumber-http>=1.0.0,<2",
        "dcm-common[services, orchestra, xml]>=4.0.0,<5",
        "dcm-sip-builder-api>=3.0.0,<4",
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
