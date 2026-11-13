# Triage notes

Notes the triage workflow (`automations/triage.md`) appends after each run, so the next triage is faster. Never record account numbers, SSNs or other client data; refer to accounts by last four only.

## Log queries that work

- Pull the window into a file with pod prefixes, then search it: `kubectl logs -n wavebank -l app=trading-app --tail=-1 --since-time=<report-30m> --prefix > /tmp/triage.log`. Pods are recreated on deploy, so check pod AGE first; logs older than the pods are only in `logs/trading-app.log` (and `logs/trading-app.seed-tickets.log` for the seeded tickets).
- Log lines are JSON with `timestamp, level, endpoint, status, latency_ms, trace_id, advisor_id, message` (plus `exception` on errors). Strip the `[pod/...]` prefix and group with `collections.Counter((d["endpoint"], d["status"]) ...)` for `status >= 400`.
- Lines with `"status": null` are app log messages, not access logs. Do not paste them anywhere: the transfer success line contains PII (see below).
- The ticket's reported time can be wrong. HD-4822 gave 03:34 UTC, but its traceId was logged at 03:23:44 UTC, before the ticket was opened. Search by traceId first and make the window wide enough to cover both times.
- Live checks: `curl -s http://localhost:30080/static/api-routes.json` shows the route map the portal actually uses, and `curl -s http://localhost:30080/openapi.json` lists the real FastAPI paths.

## Symptoms and classifications

- Move money shows "Something went wrong (404)" -> ROUTE_404. Log signature: `POST /api/v2/transfers 404` with latency under 3 ms, from many advisors on both pods, while `POST /api/v1/transfers` returns 201. (HD-4821, #1, sev-p1)
- In the same window, `POST /api/v1/orders 500` (25 requests) belongs to the place-trade ticket HD-4823 (#3). Do not mix it into transfer triage.

## Root causes and owning squads

- ROUTE_404 on transfers: `app/static/api-routes.json` line 5 maps `transfers` to `/api/v2/transfers`, but `app/api/transfers.py` only serves `/api/v1/transfers` (router prefix on line 10). The portal resolves every call through `api()` in `app/static/app.js`, so any wrong entry in `api-routes.json` gives an instant 404 for that screen. Owner: advisor-portal squad. Fix: correct the path and add a test that checks `api-routes.json` against the FastAPI routes. (HD-4821)
- Security (separate ticket needed): `app/api/transfers.py` lines 28-38 log full account numbers, client names and SSNs on every successful transfer. `mask_pii()` does not exist yet in `app/logging_utils.py`. Owner: money-movement squad.

## Duplicates and noise

- HD-4821 (#1) is the original "Move money shows 404" ticket. Later tickets with the same symptom, such as HD-4822 (#2), should be closed as duplicates of #1 after checking that their traceId shows `POST /api/v2/transfers 404`.
- HD-4822 (#2) was closed as a duplicate of #1. Its traceId showed `POST /api/v2/transfers 404` for advisor A-1007, who was already in the affected list. At 04:04 UTC the 404s were still happening (81 in the 03:04 to 04:04 window).
