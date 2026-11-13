VENV ?= .venv
AUDIT_VENV ?= .venv-audit
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

CLUSTER := wavebank
NAMESPACE := wavebank
IMAGE := wavebank/trading-app:dev
KUBECTL := kubectl --context kind-$(CLUSTER) -n $(NAMESPACE)
PORTAL_URL := http://localhost:30080

.PHONY: install test lint audit cluster secrets deploy up e2e simulate logs reset down

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

cluster:
	@if kind get clusters 2>/dev/null | grep -qx $(CLUSTER); then \
		echo "kind cluster $(CLUSTER) already exists"; \
	else \
		kind create cluster --config deploy/kind-config.yaml --wait 120s; \
	fi

secrets: cluster
	@kubectl --context kind-$(CLUSTER) apply -f deploy/k8s/00-namespace.yaml >/dev/null
	@if $(KUBECTL) get secret mongo-credentials >/dev/null 2>&1; then \
		echo "Secret mongo-credentials already exists"; \
	else \
		user=wavebank-admin; \
		pass=$$(python3 -c 'import secrets; print(secrets.token_hex(24))'); \
		$(KUBECTL) create secret generic mongo-credentials \
			--from-literal=MONGO_INITDB_ROOT_USERNAME=$$user \
			--from-literal=MONGO_INITDB_ROOT_PASSWORD=$$pass \
			--from-literal=MONGO_URL="mongodb://$$user:$$pass@mongo:27017/?authSource=admin"; \
	fi

deploy: secrets
	docker build -t $(IMAGE) .
	kind load docker-image $(IMAGE) --name $(CLUSTER)
	kubectl --context kind-$(CLUSTER) apply -f deploy/k8s/
	$(KUBECTL) rollout status statefulset/mongo --timeout=300s
	$(KUBECTL) rollout restart deployment/trading-app
	$(KUBECTL) rollout status deployment/trading-app --timeout=300s

up: cluster secrets deploy
	@echo "WaveBank Advisor portal: $(PORTAL_URL)"

e2e:
	$(VENV)/bin/pytest tests/e2e

simulate:
	$(PYTHON) scripts/simulate.py

logs:
	$(KUBECTL) logs -l app=trading-app -f --prefix --tail=100 --max-log-requests=4

reset:
	$(KUBECTL) exec mongo-0 -- sh -c 'mongosh --quiet -u "$$MONGO_INITDB_ROOT_USERNAME" -p "$$MONGO_INITDB_ROOT_PASSWORD" --authenticationDatabase admin wavebank --eval "db.dropDatabase()"'
	$(KUBECTL) rollout restart deployment/trading-app
	$(KUBECTL) rollout status deployment/trading-app --timeout=300s

down:
	@if kind get clusters 2>/dev/null | grep -qx $(CLUSTER); then \
		kind delete cluster --name $(CLUSTER); \
	else \
		echo "kind cluster $(CLUSTER) does not exist"; \
	fi

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
