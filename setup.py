"""Setup script for pylint-runner."""

from setuptools import setup, find_packages

# Read the README for the long description
with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="pylint-runner",
    version="0.1.0",
    description="A command-line tool for running pylint with custom rules",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/pylint-runner",
    packages=find_packages(include=["soar_app_linter", "soar_app_linter.*"]),
    python_requires=">=3.13.0",
    install_requires=[
        "pylint==3.3.6",
        "astroid>=2.15.0,<3.0.0",
        "tomli>=2.0.0; python_version < '3.11'",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
            "isort>=5.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "pylint-runner=soar_app_linter.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
        "Typing :: Typed",
    ],
    keywords="pylint linter code-quality python",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/pylint-runner/issues",
        "Source": "https://github.com/yourusername/pylint-runner",
    },
)
