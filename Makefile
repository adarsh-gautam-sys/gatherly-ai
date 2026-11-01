.DEFAULT_GOAL := check

ifeq ($(OS),Windows_NT)
PYTHON ?= py -3.12
VENV_PYTHON := .venv/Scripts/python.exe
else
PYTHON ?= python3.12
VENV_PYTHON := .venv/bin/python
endif

GITLEAKS ?= $(if $(wildcard .tools/gitleaks/gitleaks.exe),.tools/gitleaks/gitleaks.exe,gitleaks)

.PHONY: install lint typecheck test scan scan-staged check run

install:
	$(PYTHON) -m venv .venv
	"$(VENV_PYTHON)" -m pip install -r requirements.txt
	"$(VENV_PYTHON)" -m pip install --no-deps --no-build-isolation -e .
	"$(VENV_PYTHON)" -m pre_commit install

lint:
	"$(VENV_PYTHON)" -m ruff check src tests
	"$(VENV_PYTHON)" -m ruff format --check src tests

typecheck:
	"$(VENV_PYTHON)" -m mypy

test:
	"$(VENV_PYTHON)" -m pytest
	"$(VENV_PYTHON)" -m coverage report --include="src/gatherly/domain/*" --fail-under=100

scan:
	"$(VENV_PYTHON)" -m bandit -q -r src
	"$(VENV_PYTHON)" -m pip_audit --strict --no-deps --disable-pip -r requirements.txt
	$(GITLEAKS) git --redact --no-banner
	$(MAKE) scan-staged

scan-staged:
	$(GITLEAKS) git --pre-commit --staged --redact --no-banner

check: lint typecheck test scan

run:
	"$(VENV_PYTHON)" -m uvicorn gatherly.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log
