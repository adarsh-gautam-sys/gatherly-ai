.DEFAULT_GOAL := check

ifeq ($(OS),Windows_NT)
PYTHON ?= py -3.12
VENV_PYTHON := .venv/Scripts/python.exe
else
PYTHON ?= python3.12
VENV_PYTHON := .venv/bin/python
endif

GITLEAKS ?= $(if $(wildcard .tools/gitleaks/gitleaks.exe),.tools/gitleaks/gitleaks.exe,gitleaks)
IMAGE ?= gatherly-ai:local

.PHONY: install lint typecheck test scan scan-staged check run image container-test load web-check

install:
	$(PYTHON) -m venv .venv
	"$(VENV_PYTHON)" -m pip install -r requirements.txt
	"$(VENV_PYTHON)" -m pip install --no-deps --no-build-isolation -e .
	"$(VENV_PYTHON)" -m pre_commit install
	npm ci --ignore-scripts
	npx playwright install chromium

lint:
	"$(VENV_PYTHON)" -m ruff check src tests scripts
	"$(VENV_PYTHON)" -m ruff format --check src tests scripts

typecheck:
	"$(VENV_PYTHON)" -m mypy

test:
	"$(VENV_PYTHON)" -m pytest
	"$(VENV_PYTHON)" -m coverage report --include="src/gatherly/domain/*" --fail-under=100

scan:
	"$(VENV_PYTHON)" -m bandit -q -r src scripts
	"$(VENV_PYTHON)" -m pip_audit --strict --no-deps --disable-pip -r requirements.txt
	npm audit --audit-level=low
	$(GITLEAKS) git --redact --no-banner
	$(MAKE) scan-staged

scan-staged:
	$(GITLEAKS) git --pre-commit --staged --redact --no-banner

check: lint typecheck test scan web-check

web-check:
	npm run check

run:
	"$(VENV_PYTHON)" -m uvicorn gatherly.main:create_app --factory --host 127.0.0.1 --port 8000 --no-access-log --no-proxy-headers

image:
	docker build --tag "$(IMAGE)" .

container-test: image
	"$(VENV_PYTHON)" -m scripts.check_container --image "$(IMAGE)"

load:
	"$(VENV_PYTHON)" -m scripts.load_sanity
