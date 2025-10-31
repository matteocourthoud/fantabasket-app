# --- Variables ---
# Define the virtual environment directory
VENV_DIR := .venv

# Define paths to executables inside the venv
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip
VENV_UV := $(VENV_DIR)/bin/uv

# --- Shell Configuration ---
SHELL := /bin/bash
.SHELLFLAGS := -e
# .ONESHELL: is no longer needed with this approach

# --- Targets ---
.PHONY: create-venv install-deps scrape run

create-venv:
	@echo "Creating virtual environment with Python 3.13..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	# Use the variable for the check and creation
	test -d $(VENV_DIR) || python3.13 -m venv $(VENV_DIR)

install-deps: create-venv
	@echo "Installing Python dependencies using uv..."
	# Call pip and uv from the venv directly
	$(VENV_PIP) install uv
	$(VENV_UV) pip install --index-url https://pypi.org/simple/ -r requirements.txt

scrape: install-deps
	@echo "Running data scraping scripts..."
	# Call python from the venv directly
	$(VENV_PYTHON) -m src/scraping/scrape_injuries
	$(VENV_PYTHON) -m src/scraping/scrape_games

run: install-deps
	@echo "Launching Streamlit application..."
	# Call python from the venv directly
	$(VENV_PYTHON) -m streamlit run src/streamlit/main.py