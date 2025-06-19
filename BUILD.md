# BUILD and RELEASE INSTRUCTIONS

This document describes how to build and publish the package for developers.

## Building the Package

To build both source and wheel distributions, run:

```sh
python3 setup.py sdist bdist_wheel
```

This will create distribution files in the `dist/` directory.

## Publishing to TestPyPI

To upload the package to TestPyPI (for testing your release process), run:

```sh
twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```

Make sure you have `twine` installed (`pip install twine`).

## Using PDM

[PDM](https://pdm.fming.dev/) is a modern Python package and dependency manager. If you prefer using PDM, here are some basic commands:

- **Create venv and install dependencies:**
  ```sh
  pdm install
  ```
- **Run your project:**
  ```sh
  pdm run python <your_script.py>
  ```
- **Build the package:**
  ```sh
  pdm build
  ```
- **Publish to PyPI:**
  ```sh
  pdm publish
  ```

See the [PDM documentation](https://pdm.fming.dev/latest/) for more details.

---

For more information, see the official Python packaging documentation: https://packaging.python.org/tutorials/packaging-projects/
