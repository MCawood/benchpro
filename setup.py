from setuptools import setup, find_packages

setup(
    name="benchpro",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "click>=8.0.0",
        "pyyaml>=6.0.0",
        "psutil>=5.9.0",
    ],
    entry_points={
        "console_scripts": [
            "benchpro=benchpro.cli:cli",
        ],
    },
) 