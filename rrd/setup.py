from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    install_requires = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="rrd",
    version="1.0.0",
    author="RRD Development Team",
    description="Recursive Repair Development - Automated TDD workflow system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rrd/rrd",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=install_requires,
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "pytest-mock>=3.0",
            "ruff>=0.1.0",
            "mypy>=1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "rrd=cli.cli:cli",
        ],
    },
)
