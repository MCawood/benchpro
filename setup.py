from setuptools import setup, find_packages

setup(
    name="benchpro",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "click>=8.0.0",
        "pyyaml>=6.0",
        "jinja2>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "benchpro=benchpro.cli.cli:main",
        ],
    },
    python_requires=">=3.8",
    author="BenchPRO Team",
    author_email="example@example.com",
    description="A benchmark execution and profiling tool",
    keywords="benchmark, HPC, profiling",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
) 