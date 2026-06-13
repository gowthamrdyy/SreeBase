# Contributing to SreeBase

First off, thank you for considering contributing to SreeBase! It's people like you that make SreeBase a world-class enterprise database.

## Developer Guidelines

We follow a strict set of engineering standards to ensure the core engine remains blazingly fast and bug-free.

### 1. Local Setup

Fork and clone the repository, then set up your virtual environment:

```bash
git clone https://github.com/[YourUsername]/sreebase.git
cd sreebase
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Coding Standards

- **Clean Code**: Follow PEP-8. Ensure variable names are descriptive.
- **Typing**: Python type hints (`typing.Dict`, `typing.List`, etc.) are absolutely mandatory for all function arguments and returns.
- **Docstrings**: All public classes and methods must have a clear docstring explaining their architectural intent.

### 3. Testing (Strict Requirement)

SreeBase guarantees high reliability. Any new feature or bug fix MUST be accompanied by a unit test.

To run the test suite:
```bash
pytest tests/ -v
```
All 78+ tests must pass before submitting a Pull Request. We do not accept PRs that decrease code coverage.

### 4. Pull Request Process

1. Create a feature branch (`git checkout -b feature/amazing-feature`).
2. Commit your changes (`git commit -m 'Add some amazing feature'`).
3. Push to the branch (`git push origin feature/amazing-feature`).
4. Open a Pull Request targeting the `main` branch. Provide a clear description of the architectural impact.
