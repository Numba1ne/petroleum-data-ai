# Contribution Guidelines

Thank you for considering contributing to the Petroleum Data AI Toolkit!

## Code of Conduct
We follow the [Python Community Code of Conduct](https://www.python.org/psf/codeofconduct/).

## How to Contribute
1. **Report Bugs** - Create a GitHub issue describing:
   - Project version
   - Steps to reproduce
   - Expected vs actual behavior

2. **Suggest Features** - Open a discussion thread explaining:
   - The problem it solves
   - Implementation considerations

3. **Fix Issues** - Check the [good first issues](https://github.com/Numba1ne/petroleum-data-ai/labels/good%20first%20issue) label

4. **Improve Documentation** - Update READMEs or docstrings

## Development Workflow
1. **Setup Environment**
```bash
# Fork and clone repository
git clone https://github.com/Numba1ne/petroleum-data-ai.git
cd petroleum-data-ai
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

2. **Branch Naming Convention**
```
feature/<short-description>   # New features
fix/<bug-description>          # Bug fixes
docs/<topic>                   # Documentation updates
```

3. **Code Standards**
- Follow PEP 8 style guide 
- Column limit: 120 characters
- Type hints for all new functions
- Docstrings with Google format:
```python
def calculate_water_cut(oil_vol: float, water_vol: float) -> float:
    """Calculates water cut percentage.

    Args:
        oil_vol: Oil volume in barrels
        water_vol: Water volume in barrels

    Returns:
        Water cut as decimal (0.0-1.0)
    """
    return water_vol / (oil_vol + water_vol) if (oil_vol + water_vol) > 0 else 0
```

4. **Testing**
- Place unit tests in `tests/` directory
- Use pytest:
```bash
pytest tests/ -v
```

5. **Submit Pull Request**
- Reference related issue(s)
- Include test coverage
- Describe changes in commit messages
- Await CI pipeline results

## Review Process
- Maintainers will review within 72 hours
- May request changes through comments
- Approved PRs will be squashed & merged

## Development Environment Recommendations
- VS Code with Python extension
- Pre-commit hooks (included):
  - Black formatting
  - Flake8 linting
  - Mypy type checking
```bash
# Install pre-commit hooks
pre-commit install
```
