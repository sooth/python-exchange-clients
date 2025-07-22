#!/usr/bin/env python3
"""Setup configuration for python-exchange-clients package."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="python-exchange-clients",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Python client library for cryptocurrency exchanges (LMEX, BitUnix)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/python-exchange-clients",
    packages=find_packages(exclude=["tests", "tests.*", "examples", "examples.*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
        "websocket-client>=1.0.0",
        "python-dotenv>=0.19.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.18.0",
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
            "build>=0.7.0",
            "twine>=4.0.0",
        ]
    },
    package_data={
        "exchanges": ["utils/*.json"],
    },
    include_package_data=True,
)