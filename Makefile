VENV = .venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip
CONFIG = config.txt


all: run

help:
	@echo "A-Maze-ing - available targets:"
	@echo "  make install      Install dev tools (flake8, mypy, build)"
	@echo "  make run          Run the program on \$$(CONFIG) [=$(CONFIG)]"
	@echo "  make debug        Run the program under pdb"
	@echo "  make lint         flake8 + mypy with the project flags"
	@echo "  make lint-strict  flake8 + mypy --strict"
	@echo "  make build        Build the mazegen package (sdist + wheel)"
	@echo "  make test         Run the unit tests with pytest"
	@echo "  make clean        Remove caches and build artifacts"

$(VENV):
	python3 -m venv $(VENV)

install: $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) a_maze_ing.py $(CONFIG)

debug:
	$(PYTHON) -m pdb a_maze_ing.py $(CONFIG)

lint:
	$(PYTHON) -m flake8 . --exclude .venv
	$(PYTHON) -m mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs \
		--check-untyped-defs

lint-strict:
	$(PYTHON) -m flake8 . --exclude .venv
	$(PYTHON) -m mypy . --strict

build:
	$(PYTHON) -m build
	mv dist/* ./
	rm -rf dist
	rm -rf mazegen-*.tar.gz

clean:
	find . -type d -name '__pycache__' -prune -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache build dist *.egg-info

vclean:
	rm -rf $(VENV)

fclean: clean vclean
	rm -rf mazegen-*

.PHONY: help install run debug lint lint-strict build test clean vclean fclean