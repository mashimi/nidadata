from setuptools import setup

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="nida",
    version="0.2.0",
    description=(
        "A Python library for fetching user information based on National ID (Tanzania)"
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Kalebu/nida",
    author="Jordan Kalebu",
    author_email="isaackeinstein@gmail.com",
    license="MIT",
    packages=["nida"],
    keywords=[
        "nida",
        "nida api",
        "nida python package",
        "python nida",
        "tanzania nida",
        "python-tanzania",
    ],
    install_requires=["addict", "requests", "pillow"],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
