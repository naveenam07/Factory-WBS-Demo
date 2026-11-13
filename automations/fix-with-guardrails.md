# Workflow 2: Fix with guardrails

Trigger: manual, after triage labels an issue `fix-needed`. Replace `{ISSUE}` with the GitHub issue number before running. See README.md in this folder.

```text
Fix GitHub issue #{ISSUE} in Factory-WBS-Demo (GitHub repo naveenam07/Factory-WBS-Demo, base branch main1).

1. Read the issue and its triage comment. Reproduce the problem with a failing test first: a unit test, and for portal problems a failing Playwright check.
2. Implement the smallest fix that makes the test pass, following AGENTS.md. If the bug is a portal route, fix app/static/api-routes.json and add a test that every route in it matches a FastAPI route.
3. Raise line coverage on every Python file you touch to at least 80%. Add unit tests for edge cases: None values, unknown accounts, insufficient funds, wrong route version.
4. Run make test and record coverage for the touched files before and after, from coverage.xml.
5. Redeploy to the kind cluster with make deploy, then run make e2e for the affected flow. Save before and after screenshots under docs/pr-evidence/{ISSUE}/.
6. Run /security-review on your diff and on the code paths of the flow you touched. Fix every Critical and High finding, including PII in logs (mask it with mask_pii() in app/logging_utils.py, last four only; create the helper if it does not exist), and re-run until clean.
7. Open a PR titled [HD-xxxx] ... whose body starts with "Fixes #{ISSUE}" and includes: problem, log evidence (PII masked), root cause, fix, tests added, coverage before -> after, the before and after screenshots, security review result, risk and rollback plan.
8. The only CODEOWNER (@naveenam07) is also the PR author in this demo repo, so GitHub cannot request their review. Instead, the PR body must state: "Approval required: a CODEOWNER other than the requester (in production: money-movement squad); in this demo the human (naveenam07) merges as admin". Comment the PR link on the issue and as a reply in the incident's Slack thread in #trading-incidents (C0CGWSHK4UX).

You are the author only. Do not approve or merge, and do not change branch protection or CODEOWNERS. Leave the PR open for human review.
```
