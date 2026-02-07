# Contributing to aiovban

Thank you for your interest in contributing to aiovban! This document provides guidelines for contributing to the project.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/aiovban.git
   cd aiovban
   ```
3. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
4. **Install development dependencies**:
   ```bash
   pip install -e .
   pip install pytest tox
   ```

## Development Workflow

### Making Changes

1. **Create a new branch** for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   ```
   or
   ```bash
   git checkout -b bugfix/issue-description
   ```

2. **Make your changes** following the project's coding style

3. **Write tests** for your changes (if applicable)

4. **Run the test suite**:
   ```bash
   pytest
   ```

5. **Run tests across Python versions** (optional but recommended):
   ```bash
   tox
   ```

### Commit Messages

Write clear, descriptive commit messages:
- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

Example:
```
Add support for custom audio codecs

- Implement codec registry
- Add documentation for custom codecs
- Add tests for codec registration

Fixes #123
```

### Submitting Changes

1. **Push your changes** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Submit a pull request** through GitHub

3. **Wait for review** - a maintainer will review your changes and may request modifications

## Code Style

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use meaningful variable and function names
- Add docstrings to classes and functions
- Keep functions focused and concise
- Use type hints where appropriate

## Testing

- Write tests for new features and bug fixes
- Ensure all tests pass before submitting a pull request
- Aim for good test coverage of new code
- Tests should be located in the `tests/` directory

## Documentation

- Update the README.md if you change functionality
- Add docstrings to new classes and methods
- Update relevant documentation files if needed

## Reporting Issues

When reporting issues, please include:

1. **Description**: Clear description of the problem
2. **Steps to Reproduce**: Minimal steps to reproduce the issue
3. **Expected Behavior**: What you expected to happen
4. **Actual Behavior**: What actually happened
5. **Environment**: Python version, OS, package version
6. **Code Sample**: Minimal code that demonstrates the issue (if applicable)

## Questions?

If you have questions about contributing, feel free to:
- Open an issue with the question label
- Reach out to the maintainers

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
