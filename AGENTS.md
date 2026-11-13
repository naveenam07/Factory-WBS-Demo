# AGENTS.md - Factory-WBS-Demo

## What this repo is
Advisor Trading App for WaveBank Services (fictional): one Python service on Kubernetes with MongoDB.
- app/api/ - FastAPI routes: orders, money movement (transfers), positions
- app/services/ - business logic
- app/repositories/ - MongoDB access
- app/templates/ and app/static/ - the advisor portal (Jinja2 pages and vanilla JS)
- deploy/ - kind cluster config and Kubernetes manifests (kind stands in for OpenShift)

## Commands
- Install: make install
- Start everything: make up (portal and API at http://localhost:30080)
- Redeploy after a change: make deploy
- Unit tests with coverage: make test (htmlcov/index.html and coverage.xml)
- Portal smoke test: make e2e (screenshots in tests/e2e/screenshots)
- Logs: make logs, or kubectl logs -n wavebank -l app=trading-app --since=30m
- Reproduce advisor traffic and save logs: make simulate (writes logs/trading-app.log)
- Reset demo data: make reset
- Dependency vulnerability scan: make audit

## Tickets
- Help-desk tickets are GitHub issues labeled helpdesk. They stand in for ServiceNow and Jira.
- Labels: droid-triage, fix-needed, duplicate, noise, sev-p1, sev-p2, sev-p3.

## Ownership (see CODEOWNERS)
- Orders and positions: trading squad. Transfers: money-movement squad. Templates and static: advisor-portal squad. deploy/: platform team.

## Rules for every change
- Start from evidence: cite log lines (trace_id, endpoint, status) that show the problem.
- Write a failing test that reproduces the bug before fixing it.
- Keep changes small and scoped to one issue. No unrelated refactors.
- Line coverage on every Python file you touch must be 80% or higher.
- Every path in app/static/api-routes.json must match a FastAPI route.
- For changes that affect the portal, redeploy with make deploy, run make e2e and include before and after screenshots.
- Never log account numbers, SSNs or tax IDs. Use or create mask_pii() in app/logging_utils.py (last four only).
- Never commit secrets. MongoDB credentials live only in the Kubernetes Secret.
- Do not change deploy/ manifests unless the issue asks.
- PR title: [HD-xxxx] short description. PR body: "Fixes #<issue>", problem, evidence, root cause, fix, tests, coverage before/after, screenshots, security review result, risk, rollback.

## Change control (SOX)
- You may author changes and comment on PRs. You never approve or merge.
- Every PR needs approval from a human in CODEOWNERS who did not request the change.
- Do not modify CODEOWNERS, branch protection, .github/workflows or this file unless the issue explicitly asks.
