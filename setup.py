import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="stateflow",
    version="0.0.2",
    author=u"Tomasz Łakota",
    author_email="tomasz@lakota.pl",
    description="A state-propagation framework.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/peper0/stateflow",
    packages=setuptools.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
    test_suite='stateflow.test',
)
