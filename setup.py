"""BenchPRO setup configuration."""

from setuptools import setup, find_packages

setup(
    name="benchpro",
    version="2.0.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "pyyaml>=5.1",
        "jinja2>=3.0.0",
        "aiofiles>=0.8.0",
        "asyncio>=3.4.3",
        "rich>=10.0.0"
    ],
    entry_points={
        "console_scripts": [
            "bp=benchpro.cli:cli",
        ],
    },
    python_requires=">=3.8",
    author="Your Name",
    author_email="your.email@example.com",
    description="A tool for managing HPC benchmarks and applications",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/benchpro",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
) 