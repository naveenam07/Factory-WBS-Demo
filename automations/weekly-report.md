# Workflow 3: Weekly reliability report

Trigger: scheduled Factory Automation, Fridays at 4pm America/New_York (cron `0 21 * * 5` in UTC while EST applies; `0 20 * * 5` after 2027-03-14). See README.md in this folder.

```text
Write the WaveBank trading-app weekly reliability report for this week (Monday to Friday), using GitHub (repo naveenam07/Factory-WBS-Demo) and Slack (workspace "WaveBank Services").

Gather from GitHub:
- Issues labeled helpdesk opened this week, counted by classification and severity, with duplicates and noise shown separately.
- For each issue: time from opened to the first triage comment (time to acknowledge) and from opened to its linked PR merged (time to fix).
- PRs that fix those issues: link, status, author, approver, tests added, coverage before -> after, security findings fixed by severity.
- Open items: fix-needed issues without a PR, and PRs waiting more than 24 hours for review.
- Factory usage cost for these sessions, if Analytics data is available.

If a metric is unavailable (for example, nothing merged yet so there is no time to fix, no data for last week, or no Analytics cost data), say so explicitly in the report. Never invent numbers.

Write a one-page report:
1. Headline: tickets, median time to acknowledge, median time to fix, compared with last week.
2. A table: issue -> PR -> approver -> status.
3. Security and quality: PII-in-logs findings fixed, coverage change.
4. Risks and asks for the Head of Platform.
5. Change-control check: confirm every merged PR was approved by a human who was neither the PR author nor the person who requested the fix, and list any exceptions.

Deliver it three ways: post it in #platform-leadership (Slack channel C0CHE50DG01), send it as a direct message to the Head of Platform (Slack user U0CH99DRVRU), and open a PR against main1 adding it as reports/weekly/<YYYY-MM-DD>.md so it becomes permanent evidence. Leave the report PR open for a human to merge. Never include account numbers, SSNs or other client data.
```
