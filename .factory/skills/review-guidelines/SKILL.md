---
name: review-guidelines
description: WaveBank code review rules for the trading and money-movement services.
---
When reviewing a pull request in this repository:
- Flag any bug fix without a test that would have failed before the fix.
- Flag line coverage below 80% on changed files; quote the numbers from coverage.xml.
- Flag retries on money movement without an idempotency key.
- Flag database calls inside loops (N+1 patterns).
- Flag API path changes not reflected in app/static/api-routes.json.
- Comment with the rule, the line and a suggested fix. Never approve; a human CODEOWNER approves.
