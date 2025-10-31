SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -e

.PHONY: create-venv install-deps scrape run

create-venv:
	@echo "Creating virtual environment with Python 3.13.9..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	test -d .venv || python3.13 -m venv .venv

install-deps: create-venv
	@echo "Installing Python dependencies using uv..."
	. .venv/bin/activate && pip install uv
	. .venv/bin/activate && uv pip install --index-url https://pypi.org/simple/ -r requirements.txt

scrape:
	@echo "Running data scraping scripts..."
	. .venv/bin/activate && python -m src/scraping/scrape_injuries
	. .venv/bin/activate && python -m src/scraping/scrape_games

run:
	@echo "Launching Streamlit application..."
	. .venv/bin/activate && python -m streamlit run src/streamlit/main.py
