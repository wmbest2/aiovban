# Release Guide

This document describes how to cut a release for the aiovban project.

## Prerequisites

1. Ensure you have `uv` installed (see [uv installation](https://docs.astral.sh/uv/getting-started/installation/))
2. Ensure you have PyPI credentials configured (API token in GitHub Secrets as `PYPI_API_TOKEN`)
3. Ensure you have write permissions to the GitHub repository
4. Make sure all tests pass and the code is ready for release

## Quick Reference

This project uses `uv` for Python package management. Common commands:

```bash
uv sync                    # Install dependencies
uv run pytest -v           # Run tests with current Python
uv build --all-packages    # Build all workspace packages (aiovban and aiovban-pyaudio)
uv publish                 # Publish to PyPI (interactive)
```

## Release Process

The project uses GitHub Actions to automate releases to both GitHub and PyPI.

### Step 1: Update Version

1. Update the version in `pyproject.toml`:
   ```toml
   version = "X.Y.Z"
   ```

2. Commit the version change:
   ```bash
   git add pyproject.toml
   git commit -m "Bump version to X.Y.Z"
   git push origin main
   ```

### Step 2: Create and Push a Git Tag

3. Create a tag for the new version:
   ```bash
   git tag -a vX.Y.Z -m "Release version X.Y.Z"
   ```

4. Push the tag to GitHub:
   ```bash
   git push origin vX.Y.Z
   ```

### Step 3: Create GitHub Release (Automatic)

Once you push the tag, the `release.yml` workflow will automatically:
- Build the Python package (wheel and source distribution)
- Create a GitHub Release with the tag
- Attach the built artifacts to the release

### Step 4: Publish to PyPI (Automatic)

After the GitHub Release is published, the `publish-to-pypi.yml` workflow will automatically:
- Build the Python package
- Validate the package with `twine check`
- Upload the package to PyPI

## Manual Release (if needed)

If you need to publish manually:

### Build the Package
```bash
uv build --all-packages
```

### Upload to PyPI
```bash
uv publish
```

You'll be prompted for your PyPI credentials (or the tool will use trusted publishing if configured).

## Version Numbering

This project follows [Semantic Versioning](https://semver.org/):
- MAJOR version (X.0.0): Incompatible API changes
- MINOR version (0.Y.0): Add functionality in a backwards-compatible manner
- PATCH version (0.0.Z): Backwards-compatible bug fixes

## Troubleshooting

### GitHub Actions Failing

1. Check the Actions tab in the GitHub repository
2. Review the logs for the failed workflow
3. Common issues:
   - Missing `PYPI_API_TOKEN` secret in GitHub repository settings
   - Invalid package metadata in `pyproject.toml`
   - Build failures due to missing dependencies

### PyPI Upload Issues

1. Ensure your `PYPI_API_TOKEN` is valid and has upload permissions
2. Verify the package version doesn't already exist on PyPI (you cannot overwrite existing versions)
3. Check that the package builds successfully locally with `uv build --all-packages`

## Post-Release

After a successful release:
1. Verify the package is available on [PyPI](https://pypi.org/project/aiovban/)
2. Test installation: `pip install aiovban==X.Y.Z`
3. Update the changelog or release notes as needed on GitHub
4. Announce the release (if applicable)
