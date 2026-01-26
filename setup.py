"""
Setup configuration for SeekReap Tier-3.
Note: Prefer pyproject.toml for modern Python packaging.
This file is maintained for backward compatibility.
"""
from setuptools import setup, find_packages

if __name__ == "__main__":
    setup(
        name="seekreap-tier3",
        version="3.0.0-private",
        description="SeekReap Tier 3: Private Semantic Layer",
        author="SeekReap Team",
        author_email="tier3@seekreap.example.com",
        packages=find_packages(include=["*"], exclude=["tests", "tests.*", "examples", "examples.*"]),
        install_requires=[
            "cryptography>=41.0.0",
        ],
        extras_require={
            "dev": [
                "pytest>=7.0.0",
                "black>=23.0.0",
                "mypy>=1.0.0",
                "isort>=5.12.0",
            ],
        },
        classifiers=[
            "Development Status :: 4 - Beta",
            "Intended Audience :: Developers",
            "Topic :: Software Development :: Libraries :: Python Modules",
            "License :: Other/Proprietary License",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
        ],
        python_requires=">=3.8",
        entry_points={
            "console_scripts": [
                "seekreap-tier3=main:main",
            ],
        },
    )
