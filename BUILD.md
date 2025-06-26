# BUILD and RELEASE INSTRUCTIONS

This document describes how to build and publish the package for developers.

## Using PDM

[PDM](https://pdm.fming.dev/) is a modern Python package and dependency manager. If you prefer using PDM, here are some basic commands:

### Create venv and install dependencies

```sh
pdm install -d
```

Then, you can either activate the virtual environment:

```sh
. .venv/bin/activate
```

or run a script inside the virtual environment without activating it:

```sh
pdm run <script_name>
```

### Run tests

To run the tests, first install the development dependencies:

```sh
pdm install -d
```

Then run the tests using one of the following commands:

```sh
pdm run test           # Run all tests
pdm run test_verbose   # Run tests with verbose output
pdm run test_cov       # Run tests with coverage report
```

### Run mypy (type checking)

To check types with mypy in strict mode:

```sh
pdm run mypy
```

### Build the package

```sh
pdm build
```

### Publish to PyPI

1. Ensure you have your PyPI credentials set up in `~/.config/pdm/config.toml` or in the environment variables

2. Run the following command to publish your package:
   ```sh
   pdm publish
   ```

See the [PDM documentation](https://pdm.fming.dev/latest/) for more details.
