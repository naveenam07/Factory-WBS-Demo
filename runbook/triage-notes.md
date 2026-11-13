# Triage notes

Notes the triage workflow (`automations/triage.md`) appends after each run, so the next triage is faster. Never record account numbers, SSNs or other client data; refer to accounts by last four only.

## Log queries that work

- Pull the window into a file with pod prefixes, then search it: `kubectl logs -n wavebank -l app=trading-app --tail=-1 --since-time=<report-30m> --prefix > /tmp/triage.log`. Pods are recreated on deploy, so check pod AGE first; logs older than the pods are only in `logs/trading-app.log` (and `logs/trading-app.seed-tickets.log` for the seeded tickets).
- Log lines are JSON with `timestamp, level, endpoint, status, latency_ms, trace_id, advisor_id, message` (plus `exception` on errors). Strip the `[pod/...]` prefix and group with `collections.Counter((d["endpoint"], d["status"]) ...)` for `status >= 400`.
- Lines with `"status": null` are app log messages, not access logs. Do not paste them anywhere: the transfer success line contains PII (see below).
- The ticket's reported time can be wrong. HD-4822 gave 03:34 UTC, but its traceId was logged at 03:23:44 UTC, before the ticket was opened. Search by traceId first and make the window wide enough to cover both times.
- HD-4823 had the same problem: the ticket said 03:38 UTC, but its traceId was logged at 03:23:32 UTC. Treat the seeded tickets' times as unreliable and anchor the window on the traceId timestamp.
- HD-4824 too: the ticket said 03:41 UTC, but its traceId was logged at 03:23:35 UTC.
- For SLOWNESS, group `latency_ms` (p50, max) by endpoint with the account ID normalized (`re.sub(r"ACC-\d+", "ACC-*", endpoint)`). Compare the slow endpoint with fast ones in the same window (accounts list, orders) to rule out MongoDB or pod problems.
- `GET /api/v1/accounts/<id>/positions` is read-only only while `MARKET_DATA_URL` is unset. Confirm that first with the check on the next line. When it is set, `PositionsService.for_account()` calls `MarketDataClient.refresh()`, which writes fetched prices to MongoDB (`upsert_price()`) that `OrderService.place()` later uses, so do not replay the endpoint; use the existing latency logs instead. With `MARKET_DATA_URL` unset, it is safe to replay as a live timing check: `curl -s -o /tmp/pos.json -w "%{http_code} %{time_total}\n" http://localhost:30080/api/v1/accounts/<id>/positions`. Mask account IDs to last four when you quote them.
- Check `kubectl get deploy trading-app -n wavebank -o jsonpath="{.spec.template.spec.containers[0].env}"` to see whether `MARKET_DATA_URL` is set. When it is not set, the market data refresh is skipped and cannot cause positions latency.
- To find accounts with missing data without printing client names or balances, filter the API response before stdout: `curl -s "http://localhost:30080/api/v1/advisors/<advisor>/accounts" | python3 -c 'import json,sys; print(json.dumps([{k: a[k] for k in ("account_id", "account_type", "last4")} for a in json.load(sys.stdin)["accounts"]]))'`. Order logs do not include the account, so use this filtered output to identify accounts with missing types.
- Do not replay failed orders against the live booking endpoint: account data may have been corrected since the failure, allowing the replay to book a real order. Use existing logs to confirm the failure, or reproduce it against isolated test data.
- Live checks: `curl -s http://localhost:30080/static/api-routes.json` shows the route map the portal actually uses, and `curl -s http://localhost:30080/openapi.json` lists the real FastAPI paths.
- Sign-in problems: the trading app has no login, password or session endpoints (`rg -i "login|password|auth|signin" app` finds nothing), and the logs have no 401 or 403. To confirm an advisor can otherwise use the portal, check their latest access lines (`advisor_id` match, `status` not null) for 200s.

## Symptoms and classifications

- Move money shows "Something went wrong (404)" -> ROUTE_404. Log signature: `POST /api/v2/transfers 404` with latency under 3 ms, from many advisors on both pods, while `POST /api/v1/transfers` returns 201. (HD-4821, #1, sev-p1)
- Place trade shows "error 500" for some clients of one advisor -> SERVER_5XX, sev-p1 (trades blocked). Log signature: `POST /api/v1/orders 500` with `AttributeError: 'NoneType' object has no attribute 'upper'` at `app/services/orders.py` line 47, all from advisor A-1012, 25 per `make simulate` run, while A-1012's other accounts return 201. (HD-4823, #3)
- In the same window, `POST /api/v1/orders 500` (25 requests) belongs to the place-trade ticket HD-4823 (#3). Do not mix it into transfer triage.
- Account page positions slow to load -> SLOWNESS, sev-p2 (slow but not blocking). Log signature: every `GET /api/v1/accounts/<id>/positions` returns 200 in 3011 to 3054 ms, for all advisors, accounts and both pods, with no errors or market-data warnings, while other endpoints answer in under 10 ms. 40 positions requests per `make simulate` run. (HD-4824, #4)

## Root causes and owning squads

- ROUTE_404 on transfers: `app/static/api-routes.json` line 5 maps `transfers` to `/api/v2/transfers`, but `app/api/transfers.py` only serves `/api/v1/transfers` (router prefix on line 10). The portal resolves every call through `api()` in `app/static/app.js`, so any wrong entry in `api-routes.json` gives an instant 404 for that screen. Owner: advisor-portal squad. Fix: correct the path and add a test that checks `api-routes.json` against the FastAPI routes. (HD-4821)
- SERVER_5XX on orders: `OrderService.place` (`app/services/orders.py` line 47) calls `account.account_type.upper()` with no check, but `account_type` is optional (`app/models.py` line 13). The seed (`app/services/seed.py` lines 60-62, `UNTYPED_ACCOUNT_ADVISOR`/`UNTYPED_ACCOUNT_SLOTS` in `seed_data.py`) leaves 5 of A-1012's accounts untyped (last four 4324, 0161, 2111, 4299, 9525). An unknown type would also fail there with `KeyError`. Owner: trading squad. Fix: return a clear 4xx for missing or unknown types, add unit tests, and have operations fill in the missing types. (HD-4823)
- SLOWNESS on positions: `PricingService.quote()` (`app/services/pricing.py` line 13) sleeps `QUOTE_INTERVAL_SECONDS` (0.3 s, line 5) before every price lookup, and `PositionsService.for_account()` (`app/services/positions.py` lines 46 and 51) calls it once per holding. Seeded accounts have 10 holdings (`POSITIONS_PER_ACCOUNT`, `seed_data.py` line 44), so latency is 10 x 0.3 s = 3.0 s. Latency scales with the number of holdings. No unit tests cover pricing or positions. Owner: trading squad. Fix: remove the per-quote sleep, batch the price lookup, and add a unit test. (HD-4824)
- Security (separate ticket needed): `app/api/transfers.py` lines 28-38 log full account numbers, client names and SSNs on every successful transfer. `mask_pii()` does not exist yet in `app/logging_utils.py`. Owner: money-movement squad.

## Duplicates and noise

- HD-4821 (#1) is the original "Move money shows 404" ticket. Later tickets with the same symptom, such as HD-4822 (#2), should be closed as duplicates of #1 after checking that their traceId shows `POST /api/v2/transfers 404`.
- HD-4822 (#2) was closed as a duplicate of #1. Its traceId showed `POST /api/v2/transfers 404` for advisor A-1007, who was already in the affected list. At 04:04 UTC the 404s were still happening (81 in the 03:04 to 04:04 window).
- HD-4823 (#3) is the original "Place trade fails with 500" ticket. Close later tickets as duplicates of #3 if their traceId shows `POST /api/v1/orders 500` with the `account_type.upper()` AttributeError.
- HD-4824 (#4) is the original "positions slow to load" ticket. Close later slow Account page tickets as duplicates of #4 if their traceId shows `GET /api/v1/accounts/<id>/positions 200` at about 3000 ms.
- Forgot password or account lockout -> NOISE. Route to the WaveBank IT Service Desk (IAM password reset process), add the `noise` label and close as not planned. HD-4825 (#5, advisor A-1015, no traceId) was closed this way: no auth endpoints in the app, no 401 or 403 in 03:15 to 04:15 UTC, and A-1015's requests returned 200 until 04:04 UTC. NOISE tickets get no #trading-incidents post.
