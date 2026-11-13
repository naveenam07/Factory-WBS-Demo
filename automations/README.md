# Automations

Prompts for the WaveBank trading-app agentic workflows. Each file has a short header and the prompt in a `text` code block. The prompt is the part Droid runs.

| File | Workflow | Trigger |
|---|---|---|
| `triage.md` | Workflow 1: triage a help-desk ticket | A GitHub issue opened with the `helpdesk` label. Run with `droid exec`, naming the issue. |
| `fix-with-guardrails.md` | Workflow 2: fix a triaged issue and open a PR | Manual, after triage labels an issue `fix-needed`. Replace `{ISSUE}` with the issue number. |
| `weekly-report.md` | Workflow 3: weekly reliability report | Scheduled Factory Automation, Fridays 4pm America/New_York. |
| `cve-scan.md` | Case A: dependency vulnerability scan and upgrade PR | Scheduled Factory Automation, Mondays 13:00 UTC. |
| `slack-intake.md` | Slack intake: help-desk issue, triage and fix PR for a report in #trading-app-support | A new top-level message in #trading-app-support. The Slack intake watcher on the Droid Computer runs it with `droid exec --auto high`, one report at a time. |

GitHub has no native "issue opened" trigger for Droid here, and the Slack-triggered triage Automation is not configured, so triage runs headlessly from the repo root on the Droid Computer. Slack reports reach triage through `slack-intake.md`, which a watcher on the Droid Computer runs for each new top-level message in #trading-app-support.

Extract a prompt:

```sh
prompt() { awk '/^```text$/{f=1;next} /^```$/{f=0} f' "automations/$1.md"; }
```

Run triage for issue 1:

```sh
droid exec --auto high "$(prompt triage)

This run was triggered by GitHub issue #1 (opened with the helpdesk label). Triage that issue."
```

Run the fix workflow for issue 1:

```sh
droid exec --auto high "$(prompt fix-with-guardrails | sed 's/{ISSUE}/1/g')"
```

Slack channels (workspace "WaveBank Services"): `#trading-app-support` (C0CHC2QCPFU, help-desk intake), `#trading-incidents` (C0CGWSHK4UX, triage alerts and Case A summaries), `#platform-leadership` (C0CHE50DG01, weekly report). The weekly report is also sent as a direct message to the Head of Platform (U0CH99DRVRU).

Agents author changes only. A human CODEOWNER approves and merges every PR these workflows open.
