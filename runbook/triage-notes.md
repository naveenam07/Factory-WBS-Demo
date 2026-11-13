# Triage notes

Notes the triage workflow (`automations/triage.md`) appends after each run, so the next triage is faster. Never record account numbers, SSNs or other client data; refer to accounts by last four only.

## Log queries that work

- Pull the window into a file with pod prefixes, then search it: `kubectl logs -n wavebank -l app=trading-app --tail=-1 --since-time=<report-30m> --prefix > /tmp/triage.log`. Pods are recreated on deploy, so check pod AGE first; logs older than the pods are only in `logs/trading-app.log` (and `logs/trading-app.seed-tickets.log` for the seeded tickets).
- Log lines are JSON with `timestamp, level, endpoint, status, latency_ms, trace_id, advisor_id, message` (plus `exception` on errors). Strip the `[pod/...]` prefix and group with `collections.Counter((d["endpoint"], d["status"]) ...)` for `status >= 400`.
- Lines with `"status": null` are app log messages, not access logs. Do not paste them anywhere: the transfer success line contains PII (see below).
- The ticket's reported time can be wrong. HD-4822 gave 03:34 UTC, but its traceId was logged at 03:23:44 UTC, before the ticket was opened. Search by traceId first and make the window wide enough to cover both times.
- HD-4823 had the same problem: the ticket said 03:38 UTC, but its traceId was logged at 03:23:32 UTC. Treat the seeded tickets' times as unreliable and anchor the window on the traceId timestamp.
- To find which accounts have missing data without touching PII, use the public API, which returns only `last4`: `curl -s http://localhost:30080/api/v1/advisors/<advisor>/accounts` and print `account_id`, `account_type`, `last4`. Order logs do not include the account, so this is how to tie a 500 to specific accounts.
- A failing order is safe to replay as a live check: `POST /api/v1/orders` raises before the insert, so nothing is written. Do not replay a request that succeeds, because that books a real order.
- Live checks: `curl -s http://localhost:30080/static/api-routes.json` shows the route map the portal actually uses, and `curl -s http://localhost:30080/openapi.json` lists the real FastAPI paths.

## Symptoms and classifications

- Move money shows "Something went wrong (404)" -> ROUTE_404. Log signature: `POST /api/v2/transfers 404` with latency under 3 ms, from many advisors on both pods, while `POST /api/v1/transfers` returns 201. (HD-4821, #1, sev-p1)
- Place trade shows "error 500" for some clients of one advisor -> SERVER_5XX, sev-p1 (trades blocked). Log signature: `POST /api/v1/orders 500` with `AttributeError: 'NoneType' object has no attribute 'upper'` at `app/services/orders.py` line 47, all from advisor A-1012, 25 per `make simulate` run, while A-1012's other accounts return 201. (HD-4823, #3)
- In the same window, `POST /api/v1/orders 500` (25 requests) belongs to the place-trade ticket HD-4823 (#3). Do not mix it into transfer triage.

## Root causes and owning squads

- ROUTE_404 on transfers: `app/static/api-routes.json` line 5 maps `transfers` to `/api/v2/transfers`, but `app/api/transfers.py` only serves `/api/v1/transfers` (router prefix on line 10). The portal resolves every call through `api()` in `app/static/app.js`, so any wrong entry in `api-routes.json` gives an instant 404 for that screen. Owner: advisor-portal squad. Fix: correct the path and add a test that checks `api-routes.json` against the FastAPI routes. (HD-4821)
- SERVER_5XX on orders: `OrderService.place` (`app/services/orders.py` line 47) calls `account.account_type.upper()` with no check, but `account_type` is optional (`app/models.py` line 13). The seed (`app/services/seed.py` lines 60-62, `UNTYPED_ACCOUNT_ADVISOR`/`UNTYPED_ACCOUNT_SLOTS` in `seed_data.py`) leaves 5 of A-1012's accounts untyped (last four 4324, 0161, 2111, 4299, 9525). An unknown type would also fail there with `KeyError`. Owner: trading squad. Fix: return a clear 4xx for missing or unknown types, add unit tests, and have operations fill in the missing types. (HD-4823)
- Security (separate ticket needed): `app/api/transfers.py` lines 28-38 log full account numbers, client names and SSNs on every successful transfer. `mask_pii()` does not exist yet in `app/logging_utils.py`. Owner: money-movement squad.

## Duplicates and noise

- HD-4821 (#1) is the original "Move money shows 404" ticket. Later tickets with the same symptom, such as HD-4822 (#2), should be closed as duplicates of #1 after checking that their traceId shows `POST /api/v2/transfers 404`.
- HD-4822 (#2) was closed as a duplicate of #1. Its traceId showed `POST /api/v2/transfers 404` for advisor A-1007, who was already in the affected list. At 04:04 UTC the 404s were still happening (81 in the 03:04 to 04:04 window).
- HD-4823 (#3) is the original "Place trade fails with 500" ticket. Close later tickets as duplicates of #3 if their traceId shows `POST /api/v1/orders 500` with the `account_type.upper()` AttributeError.
