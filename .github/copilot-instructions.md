# GitHub Copilot Instructions for Fantabasket App



## General Workflow

### Planning Before Implementation
- **ALWAYS** provide a detailed plan before making any code changes
- Wait for explicit approval (e.g., "approved", "looks good", "go ahead") before implementing
- If the plan is modified, present the updated plan and wait for approval again
- Never implement changes until the plan is explicitly approved

### Plan Format
When proposing changes, structure your plan as:
1. **Objective**: What we're trying to achieve
2. **Files affected**: List of files that will be created/modified/deleted
3. **Changes**: Bullet points describing each change
4. **Testing approach**: How changes should be tested
5. **Risks**: Any potential issues or breaking changes



## Code Quality Standards

### Python Style
- Follow PEP 8 conventions
- Use type hints for function signatures
- Add descriptive docstrings (Google style) for classes and public methods
- Keep functions focused and single-purpose
- Prefer composition over inheritance

### Linting and Formatting
- **ALWAYS** ensure code passes linting before finalizing changes
- Run `make check` to verify all pre-commit checks pass
- Fix any linting errors before considering changes complete
- Common linting commands:
  - `ruff check .` - Check for linting errors
  - `ruff format .` - Auto-format code
  - `mypy .` - Type checking (if configured)
- If linting fails, fix issues and re-run checks

### Testing
- Write unit tests for new functionality
- Use pytest framework
- Aim for meaningful test coverage, not just high percentages
- Include edge cases and error conditions
- Run tests with `pytest` or `make test` (if available)

### Documentation
- Update docstrings when modifying functions
- Keep README.md updated with significant changes
- Add inline comments only when logic is non-obvious
- Use descriptive variable and function names



## Project-Specific Guidelines

### Dependencies
- Use `uv` for dependency management
- Add new dependencies to `pyproject.toml`
- Run `uv sync --locked` to maintain lock file consistency
- **Important**: The PyPI repository doesn't have all packages (e.g., pytest)
  - Install from public PyPI: `venv/bin/pip install --index-url https://pypi.org/simple/ <package>`
  - Always use the venv pip: `venv/bin/pip` instead of global `pip`

### Sparse Matrix Operations
- Prefer scipy.sparse operations for efficiency
- Be mindful of memory usage with large datasets
- Document any assumptions about matrix sparsity

### Mathematical Models
- Clearly explain economic/statistical assumptions in docstrings
- Include references to papers/methods when applicable
- Validate inputs to prevent numerical instability (e.g., log(0), division by zero)

## Project Overview
This is a fantasy basketball analytics application that scrapes NBA statistics, computes fantasy basketball scores and player valuations, and displays them in an interactive Streamlit dashboard.

### Tech Stack
- **Database**: Supabase (PostgreSQL)
- **Frontend**: Streamlit multi-page app
- **Scraping**: BeautifulSoup, Selenium (for dynamic pages)
- **Data Processing**: pandas, numpy
- **Environment**: Python 3.11, virtual environment in `venv/`

### Project Structure
```
src/
├── scraping/          # Web scraping scripts
│   ├── scrape_games.py         # Scrapes NBA game stats from Basketball Reference
│   ├── scrape_initial_ratings.py  # Scrapes initial player ratings from Dunkest
│   ├── scrape_lineups.py       # Scrapes starting lineups using Selenium
│   ├── scrape_injuries.py      # Scrapes injury reports
│   ├── clean_players.py        # Merges player data from multiple sources
│   └── utils.py                # Shared utilities (Chrome driver, etc.)
├── stats/             # Statistics computation
│   └── fanta_stats.py          # Computes fantasy scores and player valuations
├── streamlit/         # Streamlit dashboard
│   ├── main.py                 # Home page
│   └── pages/
│       └── stats.py            # Stats page with filters
└── supabase/          # Database utilities
    ├── client.py               # Supabase client singleton
    ├── utils.py                # Load/save dataframe functions
    ├── table_names.py          # Centralized table name constants
    └── tables.py               # Table and Column schema definitions
```

### Database Schema
- Complete schema definitions in `src/supabase/tables.py`
- Each table defined with `Table` class containing `Column` objects
- Columns specify: name, type, is_primary, is_nullable, is_unique, description
- Schema tests in `tests/test_schemas.py` validate against actual Supabase tables
- Run `venv/bin/python -m pytest tests/test_schemas.py -v` to validate schemas
