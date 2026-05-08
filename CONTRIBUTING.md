# Contributing to Website Generator

Thank you for your interest in contributing to the Website Generator! This document provides guidelines for contributors.

## Ways to Contribute

- **Bug Reports:** Use GitHub issues to report bugs
- **Feature Requests:** Suggest new features via issues
- **Code Contributions:** Submit pull requests
- **Documentation:** Improve docs or add examples
- **Testing:** Add or improve tests

## Development Setup

1. Fork and clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   # Activate (.venv\Scripts\Activate.ps1 on Windows)
   ```
3. Install dependencies:
   ```bash
   pip install -e .[dev]
   ```
4. Run tests:
   ```bash
   pytest
   ```

## Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for public methods
- Use descriptive variable names
- Keep functions focused and small

## Testing

- Write unit tests for new features
- Ensure all tests pass: `pytest`
- Test edge cases and error conditions
- Use descriptive test names

## Documentation

- Update docs for any API changes
- Add examples for new features
- Keep README and guides current
- Document configuration options

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Add tests if applicable
4. Update documentation
5. Ensure CI passes
6. Submit PR with clear description

## Commit Messages

Use clear, descriptive commit messages:
- `feat: add new plugin hook`
- `fix: resolve template loading issue`
- `docs: update API reference`

## Code Review

- Be open to feedback
- Explain complex changes
- Reference related issues
- Keep PRs focused on single concerns

## Questions?

- Check existing documentation
- Search GitHub issues
- Ask in discussions

## License

By contributing, you agree to license your work under the same license as the project.