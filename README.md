# WaveBank Advisor Trading App

A demo trading service for **WaveBank Services**, a fictional wealth firm. Financial advisors use
the WaveBank Advisor portal to look up their clients, review positions, place trades and move money
between accounts. The service runs as a Python app on a local Kubernetes cluster (kind, standing in
for OpenShift) with MongoDB.

Everything here is fictional. Advisors, clients, account numbers and tax IDs are generated fake data,
and no real people, companies or credentials are used.

## Prerequisites

- Python 3.12
- Docker
- [kind](https://kind.sigs.k8s.io/) and kubectl
- make

## Quick start

```bash
make install   # create .venv, install pinned dependencies and Playwright Chromium
make up        # create the kind cluster, the MongoDB Secret, build and deploy the app
```

Then open the portal at **http://localhost:30080**. Pick an advisor (A-1001 to A-1020), open a client
account, and use the Place trade and Move money forms.

On first start the app seeds 20 advisors, 200 accounts and 2,000 positions with synthetic data.

## Make targets

| Target          | What it does |
|-----------------|--------------|
| `make install`  | Create `.venv`, install the app with dev dependencies, install Playwright Chromium |
| `make cluster`  | Create the `wavebank` kind cluster if it does not exist |
| `make secrets`  | Create the `mongo-credentials` Secret from random values if it does not exist |
| `make deploy`   | Build the image, load it into kind, apply `deploy/k8s/` and wait for the rollout |
| `make up`       | `cluster`, `secrets` and `deploy`, then print the portal URL |
| `make test`     | Unit tests with coverage (`htmlcov/index.html` and `coverage.xml`) |
| `make lint`     | `ruff check .` |
| `make e2e`      | Playwright smoke test against http://localhost:30080 (screenshots in `tests/e2e/screenshots/`) |
| `make simulate` | Send 300 mixed advisor requests, then save the app logs to `logs/trading-app.log` |
| `make logs`     | Follow the logs of both app replicas |
| `make reset`    | Drop the database and restart the app so it re-seeds |
| `make audit`    | Scan the runtime dependencies for known vulnerabilities with pip-audit |
| `make down`     | Delete the kind cluster |

All targets are safe to run again; `make up` on a running setup just redeploys.

## Logs and trace IDs

Every API response carries a `trace_id` (in the JSON body and the `X-Trace-Id` header), and errors
use the format `{status, message, trace_id}`. The portal shows the trace ID as the "Reference" in its
error banner. The app writes one JSON log line per request to stdout (timestamp, level, service,
endpoint, status, latency_ms, trace_id, advisor_id, message), so you can find a request with:

```bash
make logs
kubectl logs -n wavebank -l app=trading-app --since=30m | grep <trace_id>
```

## Repository layout

```
app/
  api/            FastAPI routes: accounts, positions, orders, transfers, /healthz, portal pages
  services/       Business logic (orders, transfers, positions, pricing, seeding)
  repositories/   MongoDB access behind a small repository interface
  templates/      Jinja2 pages for the advisor portal
  static/         Portal JavaScript, CSS and api-routes.json
deploy/
  kind-config.yaml  One-node kind cluster mapping host port 30080
  k8s/              Namespace, MongoDB StatefulSet and the trading-app Deployment and Service
scripts/          Local demo tooling (traffic simulator)
automations/      Droid workflow prompts (triage, fix, weekly report, dependency scan)
runbook/          Triage runbook notes maintained by Droid
tests/
  unit/           pytest unit tests (mongomock, no database needed)
  e2e/            Playwright smoke test
.factory/skills/  Review and security-review guidelines for Droid
.github/          CI workflow and the help-desk issue template
```

## Help-desk tickets

Help-desk tickets are GitHub issues created from the **Help-desk ticket** template and labeled
`helpdesk`. They stand in for ServiceNow and Jira. Triage uses these labels: `droid-triage`,
`fix-needed`, `duplicate`, `noise`, `sev-p1`, `sev-p2` and `sev-p3`.

## Code review

Every pull request gets an automatic Droid code review and security review from the Droid GitHub
Action (`.github/workflows/droid-review.yml`). Droid re-reviews when new commits are pushed and posts
its findings as `factory-droid[bot]`. The repo-specific rules it applies live in
`.factory/skills/review-guidelines` and `.factory/skills/security-review-guidelines`.

You can also ask Droid directly in a PR or issue comment (`.github/workflows/droid.yml`):

- `@droid review` runs a code review of the PR diff.
- `@droid security` runs a security review of the PR diff.
- `@droid fill` writes the PR description.

Droid comments and suggests; a human code owner still approves and merges every change.

## Automations and runbook

The prompts for the Droid workflows live in `automations/`. Each file has a short header and the
prompt Droid runs; `automations/README.md` explains how to extract and run them.

| File                     | Workflow | Trigger |
|--------------------------|----------|---------|
| `triage.md`              | Triage a help-desk ticket | Issue opened with the `helpdesk` label (run with `droid exec`) |
| `fix-with-guardrails.md` | Fix a triaged issue and open a PR | Manual, after triage labels the issue `fix-needed` |
| `weekly-report.md`       | Weekly reliability report | Scheduled, Fridays 4pm America/New_York |
| `cve-scan.md`            | Dependency vulnerability scan and upgrade PR | Scheduled, Mondays 13:00 UTC |

Weekly reports are proposed by pull request under `reports/weekly/`. Triage keeps its running notes
in `runbook/triage-notes.md`. These workflows only author changes; a human code owner approves and
merges every PR they open.

## Contributing

See [AGENTS.md](AGENTS.md) for the rules every change follows and [CODEOWNERS](CODEOWNERS) for
ownership. CI runs `make install` and `make test` on every pull request.
