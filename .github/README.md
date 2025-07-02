# GitHub Actions Workflows

This directory contains the GitHub Actions workflows for the Adaptive Climate custom component.

## Workflows

### CI/CD Pipeline (`ci.yml`)

Runs on every push and pull request to ensure code quality and functionality.

**Jobs:**
- **Test Matrix**: Tests against multiple Python versions (3.12, 3.13) and Home Assistant versions (2025.6.0, 2025.7.0, dev)
- **Validation**: Validates the integration using Home Assistant's hassfest tool
- **HACS Validation**: Ensures HACS compliance
- **Quality Checks**: Security scans, dependency checks, and additional linting

**Tools Used:**
- **Ruff**: Fast Python linter (replaces flake8)
- **Black**: Code formatting
- **isort**: Import sorting
- **MyPy**: Type checking
- **Pytest**: Unit testing with coverage
- **Bandit**: Security vulnerability scanning
- **Safety**: Dependency vulnerability checking

### Release Pipeline (`release.yml`)

Automated release process triggered by GitHub releases.

**Jobs:**
- **Validate Release**: Ensures version format compliance
- **Build**: Creates release package with updated version
- **Publish**: Attaches built package to GitHub release
- **Update HACS**: Updates HACS integration info

## Local Development

### Prerequisites

Install development dependencies:
```bash
pip install -r requirements_dev.txt
```

### Pre-commit Hooks

Install pre-commit hooks for automatic code quality checks:
```bash
pre-commit install
```

### Running Tests Locally

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=custom_components/adaptive_climate

# Run specific test file
pytest tests/test_adaptive_climate.py -v
```

### Code Quality Checks

```bash
# Format code
black custom_components/adaptive_climate/
isort custom_components/adaptive_climate/

# Lint code
ruff check custom_components/adaptive_climate/

# Type checking
mypy custom_components/adaptive_climate/

# Security check
bandit -r custom_components/adaptive_climate/
```

## Configuration Files

- `pyproject.toml`: Main configuration for Python tools
- `ruff.toml`: Ruff-specific configuration  
- `mypy.ini`: MyPy type checking configuration
- `pytest.ini`: Pytest testing configuration
- `.pre-commit-config.yaml`: Pre-commit hooks configuration

## Coverage Reports

Test coverage reports are:
- Displayed in terminal output
- Uploaded to Codecov (for main branch)
- Generated as HTML in `htmlcov/` directory

## Status Badges

The workflows provide status badges for:
- CI/CD pipeline status
- Test coverage percentage
- HACS validation status
- Latest release version
