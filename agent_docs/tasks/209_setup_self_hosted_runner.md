# Task 209: Set Up Self-Hosted GitHub Actions Runner

## Goal

Install and configure a self-hosted GitHub Actions runner on the production Proxmox VM (192.168.4.112) so we can use it for continuous deployment. The runner should run as a systemd service and be labeled for use in CD workflows.

## Context

- **VM**: `192.168.4.112` (Debian 12 bookworm, x86_64)
- **SSH access**: `ssh root@192.168.4.112` (already configured, works from local machine)
- **Docker**: v29.1.4 installed
- **Taskfile**: Not installed on VM (will need to be installed for CD)
- **Repository**: `TimChild/PaperTrade` on GitHub
- **Purpose**: Runner will execute CD workflows (deploy on merge to main) without exposing the server to inbound SSH from GitHub

## Why Self-Hosted

1. Runner polls GitHub via outbound HTTPS — no inbound ports needed
2. Runner is on the same LAN (or same machine) as production — can deploy directly
3. Free (no GitHub Actions minutes consumed)
4. Persistent caches for faster builds

## Steps

### 1. Create a dedicated user on the VM

Don't run the runner as root. Create a `github-runner` user with Docker access:

```bash
ssh root@192.168.4.112

# Create user
useradd -m -s /bin/bash github-runner
usermod -aG docker github-runner

# Verify docker access
su - github-runner -c "docker ps"
```

### 2. Generate a runner registration token

Go to: https://github.com/TimChild/PaperTrade/settings/actions/runners/new

Or use the CLI (from your local machine):

```bash
GH_PAGER="" gh api -X POST repos/TimChild/PaperTrade/actions/runners/registration-token --jq '.token'
```

Save this token — it expires in ~1 hour.

### 3. Download and configure the runner on the VM

```bash
ssh root@192.168.4.112
su - github-runner

# Download latest runner (x64 Linux)
mkdir -p ~/actions-runner && cd ~/actions-runner
curl -o actions-runner-linux-x64.tar.gz -L https://github.com/actions/runner/releases/latest/download/actions-runner-linux-x64-2.322.0.tar.gz
tar xzf ./actions-runner-linux-x64.tar.gz

# Configure (use the token from step 2)
./config.sh --url https://github.com/TimChild/PaperTrade \
  --token <REGISTRATION_TOKEN> \
  --name papertrade-proxmox \
  --labels self-hosted,linux,x64,proxmox \
  --work _work \
  --runnergroup Default
```

**Note**: Check https://github.com/actions/runner/releases for the latest version number. The URL above may need updating.

### 4. Install as a systemd service

```bash
# Back to root
exit

cd /home/github-runner/actions-runner
./svc.sh install github-runner
./svc.sh start
./svc.sh status
```

This creates a systemd service that auto-starts on boot.

### 5. Install Taskfile on the VM

The CD workflow will use `task proxmox-vm:deploy` (or a deployment-specific task). Install Taskfile:

```bash
ssh root@192.168.4.112

# Install task
sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin
task --version
```

### 6. Verify the runner appears in GitHub

Go to: https://github.com/TimChild/PaperTrade/settings/actions/runners

The runner `papertrade-proxmox` should show as **Idle** (green dot).

Or verify via CLI:

```bash
GH_PAGER="" gh api repos/TimChild/PaperTrade/actions/runners --jq '.runners[] | {name, status, labels: [.labels[].name]}'
```

### 7. Test with a manual workflow dispatch

Create a simple test workflow to verify the runner works:

```yaml
# .github/workflows/test-runner.yml
name: Test Self-Hosted Runner
on: workflow_dispatch

jobs:
  test:
    runs-on: [self-hosted, proxmox]
    steps:
      - uses: actions/checkout@v4
      - run: echo "Hello from $(hostname)!"
      - run: docker ps
      - run: task --version
```

Trigger it from the Actions tab or via CLI:

```bash
GH_PAGER="" gh workflow run test-runner.yml
```

Verify it runs on `papertrade-proxmox` and all commands succeed.

## Security Considerations

- The runner should NOT run as root — use the `github-runner` user
- The runner only needs Docker access (via docker group) for deployments
- Self-hosted runners on public repos can be a security risk (anyone can submit a PR that runs code). For private repos this is fine. If the repo is public, consider restricting the runner to only run on specific workflows or requiring approval for PRs.
- The registration token is single-use and short-lived — it's safe to pass via CLI

## Post-Setup: What Comes Next

Once the runner is verified, return to the main conversation to:
1. Create the CD workflow (`.github/workflows/cd.yml`) that deploys on push to main
2. Set up versioning (`uv hatch` for backend, `npm version` for frontend)
3. Create the deploy-on-merge pipeline using `runs-on: [self-hosted, proxmox]`
4. Optionally migrate CI (lint/test/E2E) to the self-hosted runner too (faster, free)

## Acceptance Criteria

1. ✅ `github-runner` user exists on VM with Docker access
2. ✅ Runner appears as **Idle** in GitHub repo settings
3. ✅ Runner is configured as a systemd service (auto-starts on boot)
4. ✅ Taskfile is installed on the VM
5. ✅ Test workflow runs successfully on the self-hosted runner
