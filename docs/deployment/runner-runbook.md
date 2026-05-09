# Self-Hosted Runner Runbook (`papertrade-proxmox`)

**Last Updated**: 2026-05-09
**Audience**: Anyone with shell access to the Proxmox VM that hosts the GitHub Actions runner.
**Scope**: Day-to-day operation, recovery, and credential rotation for the `papertrade-proxmox` self-hosted runner that drives `cd.yml`.

This runbook complements [Proxmox VM Deployment](./proxmox-vm-deployment.md) (which covers the application). Workflow-side hardening — Docker prune, cache caps, structured log markers, disk-floor enforcement — lives in `.github/workflows/_runner-prep.yml` and is applied automatically before every deploy. The pieces that can only be configured **on the host** are documented here.

---

## At a glance

| Question | Answer |
|---|---|
| Where does the runner live? | The same Proxmox VM that serves the production app (the one referenced as `papertrade-proxmox`). |
| Where does the runner installation live on disk? | `/opt/actions-runner` (default) — `_work/` underneath holds the per-job workspaces. |
| What systemd unit controls it? | `actions.runner.TimChild-PaperTrade.papertrade-proxmox.service` (name pattern set at install time). |
| Where is the workflow `.env` sourced from? | `/opt/papertrade/.env` (host-managed, never touches GitHub). |
| What logs should I tail when a deploy is acting up? | `journalctl -u 'actions.runner.*' -f` plus the per-run logs in `/opt/actions-runner/_diag/`. |
| What's the disk floor enforced by `_runner-prep.yml`? | 10 GB free on `/`. |

---

## Health checks (do this first)

When a deploy fails or hangs, run these in order — each takes seconds and rules out a whole class of problems:

```bash
# 1. Is the runner process up?
sudo systemctl status 'actions.runner.*'

# 2. Is the runner registered and connected to GitHub?
sudo journalctl -u 'actions.runner.*' --since '30 minutes ago' | tail -50

# 3. Does the host have headroom?
df -h /
docker system df
free -h

# 4. Are there orphaned containers or volumes from a previous run?
docker ps -a
docker volume ls

# 5. Is the runner workspace cluttered?
sudo du -sh /opt/actions-runner/_work/* 2>/dev/null | sort -h | tail
```

Expected baselines (a healthy runner):

| Metric | Healthy | Warning | Bad |
|---|---|---|---|
| Free disk on `/` | >= 20 GB | 10–20 GB | < 10 GB (prep workflow will fail loudly) |
| Memory free | >= 2 GB | 1–2 GB | < 1 GB |
| Docker images count | < 30 | 30–80 | > 80 |
| Stopped containers | 0–2 | 3–10 | > 10 |
| `_work/<workflow>/<repo>` size | < 5 GB per repo | 5–15 GB | > 15 GB (workspace not cleaning) |

If `_runner-prep.yml` is doing its job, the "bad" column should never be hit between deploys. If it is, see [Recovery from a bad state](#recovery-from-a-bad-state) below.

---

## Reading the logs

### From GitHub (preferred for per-run debugging)

Every step in `cd.yml` is wrapped in `::group::` markers and emits structured trailer lines so an agent (or human) can grep for status:

```text
STEP=build STATUS=ok
STEP=db-migrate STATUS=ok
STEP=health-backend STATUS=ok
```

Failure lines start with `FAILED:` followed by a human-readable reason and a hint. Search the run output for `STATUS=fail` to find the first failing step.

The runner-prep workflow emits two snapshot lines per run:

```text
RUNNER_STATE=before HOST=<hostname> TS=<iso8601>
RUNNER_STATE=after  HOST=<hostname> TS=<iso8601>
```

Compare them to see how much disk the cleanup actually reclaimed.

### From the host (for runner-process issues)

```bash
# Live runner stdout / stderr
sudo journalctl -u 'actions.runner.*' -f

# Per-run trace logs (what GitHub never shows you)
ls -lt /opt/actions-runner/_diag/ | head
sudo cat /opt/actions-runner/_diag/Runner_<timestamp>.log

# Per-job worker logs (deeper detail)
ls -lt /opt/actions-runner/_diag/Worker_*.log | head
```

Useful greps:

```bash
# Did the runner lose its GitHub websocket?
sudo journalctl -u 'actions.runner.*' --since today | grep -iE 'disconnect|reconnect|throttle'

# What did docker-compose actually run?
sudo journalctl -u 'actions.runner.*' --since '1 hour ago' | grep -E 'docker compose'
```

---

## Routine maintenance (weekly / monthly)

The `_runner-prep.yml` reusable workflow handles the per-deploy hygiene. The host owner still needs to do:

### Weekly (~5 min)

- Skim `journalctl -u 'actions.runner.*' --since '1 week ago' | grep -iE 'error|fail'`. One-off `FAILED: …` lines from `_runner-prep.yml` are fine; persistent runner-process errors are not.
- `df -h /` and confirm the trend is stable (not creeping up week-over-week).

### Monthly (~15 min)

- Update the runner binary if GitHub has shipped a new release. The runner self-updates by default, but the systemd unit needs to be restarted to pick up significant changes:

  ```bash
  sudo systemctl restart 'actions.runner.*'
  ```

- Review `/opt/actions-runner/_diag/` and rotate / delete trace logs older than 30 days:

  ```bash
  sudo find /opt/actions-runner/_diag -type f -mtime +30 -delete
  ```

- Audit who has SSH access to the VM. The runner has the production `.env`; SSH access is effectively production access.

### Quarterly

- [Rotate the runner registration token](#rotating-runner-credentials) — see below.
- Patch the host OS (`apt update && apt upgrade`) and reboot during a maintenance window. After reboot, confirm the runner came back: `sudo systemctl status 'actions.runner.*'`.

---

## Recovery from a bad state

### Symptom: `STATUS=fail STEP=disk-check FREE=<n> REQUIRED=10`

The prep workflow refused to start a deploy because free disk < 10 GB.

```bash
# Stop the systemd unit so a queued deploy can't restart in this state
sudo systemctl stop 'actions.runner.*'

# Aggressive prune (removes ALL unused docker resources, not just stale ones)
docker system prune -af --volumes

# If still tight, blow away the per-workflow workspaces. SAFE: GitHub
# recreates them on the next run. UNSAFE: only if a deploy is in flight.
sudo rm -rf /opt/actions-runner/_work/_temp/*
sudo rm -rf /opt/actions-runner/_work/PaperTrade/PaperTrade/.next || true
sudo rm -rf /opt/actions-runner/_work/PaperTrade/PaperTrade/node_modules || true

# Clear stale uv / npm caches if they're huge
sudo du -sh /home/runner/.cache/uv /home/runner/.npm 2>/dev/null
sudo rm -rf /home/runner/.cache/uv  # only if size justifies

# Restart and re-run the failed deploy from the GitHub UI
sudo systemctl start 'actions.runner.*'
sudo systemctl status 'actions.runner.*'
```

### Symptom: deploy hangs with no output for >2 minutes

Most often a docker-compose build or a service health check is blocked. From the host:

```bash
# What is the runner doing right now?
sudo ps -ef | grep -E 'Runner.Worker|docker' | head -20

# Compose state
docker compose -f /opt/papertrade/docker-compose.yml -f /opt/papertrade/docker-compose.prod.yml ps
docker compose -f /opt/papertrade/docker-compose.yml -f /opt/papertrade/docker-compose.prod.yml logs --tail 100

# If a container is wedged, target-restart it (do NOT bring the whole stack down)
docker compose -f /opt/papertrade/docker-compose.yml -f /opt/papertrade/docker-compose.prod.yml restart <service>
```

Cancel the stuck workflow run from the GitHub UI — the runner will reclaim the slot within ~30 seconds.

### Symptom: runner is "Idle" in GitHub but deploys aren't picked up

```bash
# Most common: the systemd unit is up but the runner lost its websocket. Bounce it.
sudo systemctl restart 'actions.runner.*'

# Check the auth token isn't expired (rare; tokens last 1y at install).
sudo journalctl -u 'actions.runner.*' --since '5 minutes ago' | grep -i 'token\|auth\|401'
```

If a token rotation is needed, follow [Rotating runner credentials](#rotating-runner-credentials).

### Symptom: "out of space" mid-deploy

The disk-floor check passed (>= 10 GB) but the deploy still ran out. Either the build needed more than 10 GB transient, or something on the host is eating disk concurrently.

```bash
# Identify the consumer
sudo du -shx /var /opt /home /tmp 2>/dev/null | sort -h
docker system df

# Aggressive prune
docker system prune -af --volumes

# Bump `min-free-gb` in cd.yml's `with:` block from 10 to a higher value.
# That's a code change — go through PR review.
```

If this recurs, raise the disk floor to 20 GB (in `cd.yml` under `with: min-free-gb: 20`) or grow the VM disk in Proxmox.

---

## Rotating runner credentials

GitHub registration tokens are 1-hour and only used at install time; what persists on the host is a long-lived runner credential. Rotate it when:

- A team member with host access leaves.
- You suspect the runner host has been compromised.
- Routinely once a year.

```bash
# 1. Stop the runner
sudo systemctl stop 'actions.runner.*'

# 2. As the runner user (often `runner` or `actions`), uninstall the service
sudo /opt/actions-runner/svc.sh uninstall

# 3. Remove the runner from GitHub. From the runner directory:
cd /opt/actions-runner
# Get a fresh registration token from
#   https://github.com/TimChild/PaperTrade/settings/actions/runners
# (paste it as REMOVAL_TOKEN below)
sudo -u runner ./config.sh remove --token <REMOVAL_TOKEN>

# 4. Re-register with a fresh token (same URL as above; click "New self-hosted runner")
sudo -u runner ./config.sh \
  --url https://github.com/TimChild/PaperTrade \
  --token <REGISTRATION_TOKEN> \
  --name papertrade-proxmox \
  --labels self-hosted,proxmox \
  --work _work \
  --unattended \
  --replace

# 5. Reinstall + start the service
sudo /opt/actions-runner/svc.sh install
sudo /opt/actions-runner/svc.sh start

# 6. Confirm it shows up as Idle in
#    https://github.com/TimChild/PaperTrade/settings/actions/runners
```

After rotation, run a manual `gh workflow run test-runner.yml` (or `cd.yml` via `workflow_dispatch`) to verify the new credentials work end-to-end.

---

## Workspace isolation

Per-job workspaces are GitHub's responsibility — `actions/checkout@v4` clones into a fresh `_work/<workflow>/<repo>` per job. The risk is **state on the host shared between jobs**:

- **Docker images / layers** — shared. The prep workflow prunes images older than 72h.
- **Docker volumes** — shared. We use a fixed `COMPOSE_PROJECT_NAME=papertrade` for the production stack, so deploys target the same volumes (intended; that's where prod data lives). Ad-hoc jobs must NOT use `COMPOSE_PROJECT_NAME=papertrade` or they'll trash production data.
- **uv / npm caches** — shared. Capped by the prep workflow.
- **Network ports** — shared. Only one stack on `:80` / `:8000` at a time. CD's `concurrency: production-deploy` enforces this; future CI jobs running on the same runner must use `cancel-in-progress` plus their own port range or compose project name.

If you ever queue another job to run on this runner, follow this rule: **anything that touches `:80`, `:8000`, `:5432`, `:6379`, the `papertrade` compose project, or `/opt/papertrade/.env` is mutually exclusive with the deploy job.** Use the GitHub Actions `concurrency:` block to enforce it at the workflow level.

---

## Concurrency safety

Today only `cd.yml` runs on the self-hosted runner, gated by `concurrency: production-deploy` with `cancel-in-progress: false` (we never cancel a deploy mid-flight). The runner processes one job at a time by default — multiple jobs hitting it just queue.

If we add another workflow that targets `[self-hosted, proxmox]`:

1. Give it its own `concurrency:` group (don't reuse `production-deploy` — that would block deploys behind it).
2. If it touches Docker, give it a unique `COMPOSE_PROJECT_NAME` (e.g. `papertrade-ci-${{ github.run_id }}`) and don't bind to host ports — use `expose:` only, or random host ports.
3. If it leaves anything in `_work/`, scope the cleanup to its own subdirectory.

The prep workflow takes its own `concurrency` from the calling workflow, so it can't race with itself if the same caller has `cancel-in-progress: false`.

---

## Self-healing & failing loudly

The prep workflow is designed to fail loudly rather than soldier on:

- Disk < 10 GB (configurable via `min-free-gb`) → prep job fails, downstream `deploy` never starts (`needs.prep.outputs.status` won't be `'ok'`).
- Docker prune partial-fails are logged but do not fail the job — the disk-check is the gating signal.
- The 10-minute `timeout-minutes` on the prep job means a wedged prune can't block deploys indefinitely; instead the deploy fails fast with a clear "Runner Prep" red X.

When the prep job goes red, the GitHub run page shows a top-level "Runner Prep" job result. The first `STATUS=fail` line in the log tells you which step needs attention.

---

## What this runbook deliberately does NOT cover

- **Application logic** — see [proxmox-vm-deployment.md](./proxmox-vm-deployment.md) and [production-checklist.md](./production-checklist.md).
- **Domain / SSL** — see [domain-setup.md](./domain-setup.md).
- **CI runner work** — CI currently runs on `ubuntu-latest`. Migrating CI to the self-hosted runner is deferred to a follow-up; see audit `agent_docs/audits/2026-05-09/ci-infrastructure.md` (CI-P1-1) for sequencing.

---

## References

- [Proxmox VM Deployment](./proxmox-vm-deployment.md) — VM creation and application deployment.
- `.github/workflows/cd.yml` — CD pipeline that calls the prep workflow.
- `.github/workflows/_runner-prep.yml` — reusable prep workflow.
- `agent_docs/audits/2026-05-09/ci-infrastructure.md` — original audit findings (CI-P1-1, CI-P1-3).
- [GitHub: Adding self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/adding-self-hosted-runners)
- [GitHub: Configuring the self-hosted runner application as a service](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/configuring-the-self-hosted-runner-application-as-a-service)
