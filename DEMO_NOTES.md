# Demo notes: planted defects

This file is for the demo presenter. The defects below are planted on purpose so the Factory
workflows have real problems to find from tickets and logs. Do not fix them on `main1`.

## 1. Move money returns 404

- **Where:** `app/static/api-routes.json` maps `transfers` to `/api/v2/transfers`. The API only
  serves `POST /api/v1/transfers` (`app/api/transfers.py`).
- **How it shows up:** every Move money attempt in the portal shows the red banner
  "Something went wrong (404). Reference: <trace_id>. Please contact the help desk." The logs show
  `POST /api/v2/transfers` with status 404 and the advisor ID. `make e2e` fails at the Move money step.

## 2. Place trade returns 500 for accounts with no account type

- **Where:** `app/services/orders.py` calls `account.account_type.upper()` with no None check.
  The seed (`app/services/seed.py`, `app/services/seed_data.py`) creates 5 accounts with no account
  type, all for advisor A-1012 (ACC-000112, ACC-000114, ACC-000116, ACC-000118, ACC-000120).
- **How it shows up:** Place trade on one of those accounts shows the red banner with status 500.
  The logs show an ERROR line `AttributeError: 'NoneType' object has no attribute 'upper'` for
  `POST /api/v1/orders` with the same trace ID.

## 3. Account page takes about 3 seconds

- **Where:** `app/services/positions.py` prices each holding separately through
  `app/services/pricing.py`, which sleeps 0.3 s and then runs one MongoDB `find_one` on `prices` per
  holding (`app/repositories/mongo.py`), an N+1 query pattern.
- **How it shows up:** the positions table on the Account page takes about 3 seconds to load for a
  10-position account. `GET /api/v1/accounts/{account_id}/positions` log lines show `latency_ms`
  around 3000.

## 4. Full account numbers and SSNs in the logs

- **Where:** `app/api/transfers.py` logs, at INFO, the full account number, client name and SSN of
  both accounts after every successful transfer.
- **How it shows up:** after a successful `POST /api/v1/transfers` (for example from `make simulate`),
  `make logs` or `logs/trading-app.log` contains a "Transfer TRF-... completed" message with
  10-digit account numbers and `9xx-xx-xxxx` SSNs. The data is synthetic, but the pattern is a
  Critical finding under the security-review guidelines.

## 5. Low unit-test coverage

- **Where:** `tests/unit/` covers happy paths only.
- **How it shows up:** `make test` passes with about 40% total line coverage of `app/`
  (`coverage.xml`, `htmlcov/index.html`). The repo rules require 80% on every touched file.

## 6. Vulnerable dependency (Case A)

- **Where:** `pyproject.toml` pins `requests==2.28.2`, which `app/services/market_data.py` uses for
  the optional quote refresh (only active when `MARKET_DATA_URL` is set).
- **How it shows up:** `make audit` exits non-zero and reports `requests` 2.28.2
  (PYSEC-2023-74 / GHSA-j8r2-6x86-q33q / CVE-2023-32681, plus later advisories).
