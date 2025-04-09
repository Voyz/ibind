# Contributing to IBind

Thank you for your interest in contributing to IBind! This document provides guidelines and best practices for contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contribution Workflow](#contribution-workflow)
- [Pull Request Guidelines](#pull-request-guidelines)
- [Issue Guidelines](#issue-guidelines)
- [Code Style](#code-style)
- [Documentation](#documentation)

## Getting Started

Before you start contributing, please:

1. Fork the repository
2. Create a new branch for your feature/fix
3. Set up your development environment

## Development Setup

1. Clone your fork:

   ```bash
   git clone https://github.com/YOUR_USERNAME/ibind.git
   cd ibind
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install development dependencies:

   ```bash
   pip install -r requirements-dev.txt
   ```

4. Install optional oauth dependency:

   ```bash
   pip install -r requirements-oauth.txt
   ```

## Contribution Workflow

### Feature Requests and Enhancements

1. **For new features or significant changes:**
   - Create an issue using the "Enhancement" template
   - Discuss the feature in the issue before implementing
   - Once there's agreement, create a draft PR
   - Mark the PR as "Ready for Review" when implementation is complete

2. **For small improvements or bug fixes:**
   - Create a PR directly
   - Include a clear description of the changes
   - Link to any related issues

### Pull Request Guidelines

1. **PR Size:**
   - Keep PRs focused and manageable (ideally under 500 lines)
   - Split large changes into multiple PRs
   - Each PR should address one specific feature or fix

2. **PR Content:**
   - Use clear, descriptive commit messages
   - Include tests for new features
   - Update documentation as needed
   - Add comments for complex logic
   - Ensure all tests pass

3. **PR Process:**
   - Create a draft PR for work in progress
   - Request review when ready
   - Address review comments promptly
   - Keep the PR up to date with the main branch

### Issue Guidelines

1. **Bug Reports:**
   - Use the "Bug Report" template
   - Include steps to reproduce
   - Provide environment details
   - Share error messages and logs

2. **Enhancement Requests:**
   - Use the "Enhancement" template
   - Explain the problem you're trying to solve
   - Describe your proposed solution
   - Include use cases and benefits

## Code Style

- You can run the format command with `make format` in the Makefile.
- The formatting rules are defined in `pyproject.toml`
- Follow PEP 8 guidelines
- Write docstrings for all public functions and classes
- Keep functions focused and single-purpose
- Use meaningful variable and function names

## Documentation

- Update relevant documentation for any changes
- Include docstrings for new functions and classes
- Update examples if applicable
- Keep the README.md up to date

## Release Process

- IBind is distributed through Pypi.
- Semantic Versioning 2.0.0 is used.
- Minor changes are published directly as new releases. Otherwise one or many release candidate versions are published (eg. `rc1`, `rc2`, etc.) and made available for a period of time in order to test the new functionalities.

## Questions?

If you have any questions about contributing, feel free to:

1. Open an issue
2. Join discussions in existing issues
3. Contact the maintainers

Thank you for contributing to IBind!
