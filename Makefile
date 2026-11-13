VENV ?= .venv
AUDIT_VENV ?= .venv-audit
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: install test lint audit

$(PYTHON):
	python3 -m venv $(VENV)

install: $(PYTHON)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	$(PYTHON) -m playwright install --with-deps chromium

test:
	$(VENV)/bin/pytest tests/unit --cov=app --cov-report=term --cov-report=html --cov-report=xml

lint:
	$(VENV)/bin/ruff check .

$(AUDIT_VENV)/bin/pip-audit:
	python3 -m venv $(AUDIT_VENV)
	$(AUDIT_VENV)/bin/pip install --quiet --upgrade pip
	$(AUDIT_VENV)/bin/pip install --quiet --group audit

audit: $(AUDIT_VENV)/bin/pip-audit
	@req=$$(mktemp); \
	python3 -c 'import tomllib; print("\n".join(tomllib.load(open("pyproject.toml", "rb"))["project"]["dependencies"]))' > $$req; \
	echo "Auditing runtime dependencies from pyproject.toml:"; cat $$req; \
	$(AUDIT_VENV)/bin/pip-audit --no-deps --disable-pip --progress-spinner off --aliases on -r $$req; status=$$?; \
	rm -f $$req; exit $$status
