# Proxmox Deployment Architecture Evaluation

**Date**: January 11, 2026  
**Evaluator**: Quality & Infrastructure Agent  
**Subject**: Critical evaluation of Docker-in-LXC deployment approach for PaperTrade

---

## Executive Summary

The current Proxmox deployment implementation successfully achieves automated deployment of PaperTrade to an LXC container running Docker. However, **the privileged container approach with disabled AppArmor represents a significant security compromise** that is acceptable for development/testing but **unsuitable for production use without substantial hardening**.

### Key Findings

1. **Security Risk**: Privileged LXC + disabled AppArmor = minimal isolation from host (container escape = host compromise)
2. **Industry Best Practice**: Production Docker workloads should run in VMs, not privileged LXCs
3. **Unprivileged Alternative**: Possible but requires configuration complexity (fuse-overlayfs, user namespaces)
4. **Quick Wins Available**: Multiple low-effort improvements identified for error handling, secrets, and validation
5. **Recommendation**: **Evolution approach** - incremental improvements now, VM migration path for production later

---

## Current State Analysis

### What Works Well ✅

1. **Automation & Developer Experience**
   - Taskfile integration makes deployment trivial (`task proxmox:deploy`)
   - Scripts are well-structured with clear error messages and colored output
   - Successful end-to-end automation from tarball creation to running services
   - Status and logs commands provide good operational visibility

2. **Deployment Architecture**
   - Full-stack deployment (PostgreSQL, Redis, Backend, Frontend) works correctly
   - Docker Compose orchestration properly manages service dependencies
   - Health checks implemented for all services
   - Volume persistence for database and cache

3. **Script Quality**
   - Consistent error handling with `set -euo pipefail`
   - Good separation of concerns (create, deploy, status, logs)
   - Environment variable configuration flexibility
   - Proper cleanup of temporary files

### What's Concerning 🚨

#### 1. **CRITICAL: Security Posture**

**Privileged Container Configuration:**
```bash
# create-container.sh:69
--unprivileged 0    # Runs as privileged (root on host = root in container)
```

**Implications:**
- Root user inside container maps directly to root on Proxmox host
- Container escape = full host compromise
- LXC team doesn't consider privileged container escapes a "bug" - isolation is intentionally minimal
- **Attack surface**: Any vulnerability in Docker, Docker Compose, PostgreSQL, Redis, or application code could compromise entire Proxmox host

**Disabled AppArmor:**
```
# Documentation mentions AppArmor disabled via:
lxc.apparmor.profile: unconfined
```

**Implications:**
- Removes Mandatory Access Control (MAC) protection layer
- No process confinement or resource access restrictions
- Equivalent to leaving a security door wide open

**Current Configuration in Docs:**
```
--unprivileged 1     # Documentation shows unprivileged
--features nesting=1,keyctl=1
```

**Contradiction Found**: `create-container.sh` shows `--unprivileged 0` (privileged) but documentation example shows `--unprivileged 1` (unprivileged). **The script creates privileged containers**, making it the source of truth.

#### 2. **Secrets Management**

**Current Approach (deploy.sh:116-128):**
```bash
POSTGRES_PASSWORD=$(openssl rand -base64 32)
SECRET_KEY=$(openssl rand -base64 32)
```

**Issues:**
- Passwords generated on each deploy (breaks persistence on redeployment)
- No secure storage or rotation mechanism
- Secrets stored in plain text `.env` file (`/opt/papertrade/.env`)
- No audit trail for secret access
- ALPHA_VANTAGE_API_KEY pulled from local `.env` (could be missing/wrong)

#### 3. **Build Process**

**Current Approach:**
- Builds Docker images inside container on every deployment
- Full source tarball transfer (~3MB compressed)
- No image caching or registry usage
- Build artifacts stored locally in container

**Issues:**
- Slow deployments (full rebuild every time)
- Wasted bandwidth (entire codebase transferred each time)
- No image versioning or rollback capability
- Build failures require restarting entire deployment

#### 4. **Dockerfile Patching**

**In-Flight Modification (deploy.sh:142-173):**
```bash
fix_dockerfile() {
    # Creates new Dockerfile and replaces backend/Dockerfile
    cat > /tmp/Dockerfile.backend << 'EOF'
    ...
    EOF
}
```

**Issues:**
- Modifies source code during deployment (unexpected side effect)
- Fixes should be in source repository, not deployment script
- Creates divergence between local development and production
- Makes debugging harder (which Dockerfile is actually running?)

#### 5. **Container Lifecycle & State Management**

**Missing:**
- No container shutdown/cleanup commands in Taskfile
- No update strategy that preserves data volumes
- No rollback mechanism
- No backup/restore automation
- Container IP is DHCP (can change, breaking URLs)

---

## Security Assessment

### Threat Model

**Current Attack Vectors:**

1. **Application Vulnerabilities**
   - Backend API exploit → Docker container escape → root on Proxmox host
   - Frontend XSS/injection → Backend compromise → same escalation path
   - Probability: Medium | Impact: Critical

2. **Supply Chain Attacks**
   - Malicious package in backend/frontend dependencies
   - Compromised base Docker images
   - Probability: Low | Impact: Critical

3. **Secrets Exposure**
   - Database password readable in `/opt/papertrade/.env`
   - Docker inspect exposes environment variables
   - Container logs may leak secrets
   - Probability: Medium | Impact: High

4. **Lateral Movement**
   - Compromised PaperTrade container can access entire Proxmox storage
   - Can manipulate other VMs/containers on host
   - Probability: High (if container compromised) | Impact: Critical

### Security Baseline Comparison

| Control | Industry Standard | Current Implementation | Gap |
|---------|------------------|----------------------|-----|
| Container Isolation | Unprivileged + AppArmor/SELinux | Privileged + No AppArmor | ❌ Critical |
| Secrets Management | Vault/Swarm Secrets/Cloud KMS | Plain text .env | ❌ High |
| Network Isolation | Separate VLANs, firewall rules | Single bridge network | ⚠️ Medium |
| Image Scanning | Automated CVE scanning | None | ⚠️ Medium |
| Access Control | RBAC, audit logging | Root SSH | ❌ High |
| Backup/DR | Automated, tested restores | Manual | ⚠️ Medium |
| Monitoring | Metrics, alerts, intrusion detection | Docker logs only | ⚠️ Medium |

### Risk Assessment

**Overall Security Posture**: ⚠️ **ACCEPTABLE FOR DEVELOPMENT/HOMELAB, UNACCEPTABLE FOR PRODUCTION**

**Risk Level by Deployment Scenario:**

- **Personal homelab (isolated network)**: Medium Risk ✅ Acceptable
- **Small business (internet-exposed)**: High Risk ⚠️ Hardening required
- **Production (customer data)**: Critical Risk ❌ Major redesign required

---

## Alternative Approaches

### Option 1: Docker-in-VM (Recommended for Production)

**Architecture:**
```
Proxmox Host
└── Ubuntu VM (KVM)
    └── Docker Engine
        └── PaperTrade Containers
```

**Pros:**
- ✅ Full kernel-level isolation (VM escape much harder than container escape)
- ✅ All Docker features work without compatibility issues
- ✅ Proxmox and community consensus: VMs are correct choice for Docker
- ✅ Hardware passthrough support (GPU, etc.)
- ✅ Predictable behavior across Proxmox updates

**Cons:**
- ❌ Higher resource overhead (~512MB-1GB RAM for VM itself)
- ❌ Slower boot times compared to LXC
- ❌ Slightly more complex initial setup

**When to Use:** Production deployments, internet-exposed applications, customer data handling

**Implementation Effort:** Medium (2-4 hours)
- Create Ubuntu VM template
- Install Docker in VM
- Adapt existing deployment scripts (mostly change from `pct` to `qm` commands)

---

### Option 2: Unprivileged LXC + fuse-overlayfs (Better Security)

**Architecture:**
```
Proxmox Host
└── Unprivileged LXC (user namespace isolation)
    └── Docker Engine (fuse-overlayfs storage driver)
        └── PaperTrade Containers
```

**Configuration Changes Required:**
```bash
# LXC config (/etc/pve/lxc/107.conf)
features: keyctl=1,nesting=1,fuse=1
lxc.mount.entry: /dev/fuse dev/fuse none bind,create=file,rw,uid=100000,gid=100000 0 0

# Docker daemon.json
{
  "storage-driver": "fuse-overlayfs"
}
```

**Pros:**
- ✅ User namespace isolation (root in container = nobody on host)
- ✅ Maintains LXC resource efficiency
- ✅ Can enable AppArmor with custom profile
- ✅ Reduces attack surface significantly

**Cons:**
- ❌ More complex setup and troubleshooting
- ❌ fuse-overlayfs slightly slower than native overlay2
- ❌ May break on Proxmox/kernel updates
- ❌ Some Docker features may not work (hardware passthrough harder)

**When to Use:** Homelab with security consciousness, multi-tenant environments, resource-constrained hosts

**Implementation Effort:** Medium-High (4-8 hours including testing)
- Reconfigure container creation script
- Test all Docker Compose services work with fuse-overlayfs
- Document quirks and workarounds
- Create rollback plan if it doesn't work

---

### Option 3: Native Proxmox OCI Containers (Proxmox 9.1+)

**Architecture:**
```
Proxmox Host
└── Native OCI Containers (no Docker daemon)
    └── PaperTrade services (separate containers)
```

**Note:** Requires Proxmox 9.1+ which added native OCI support.

**Pros:**
- ✅ Best resource efficiency (no Docker daemon overhead)
- ✅ Proxmox-native management (GUI, CLI, backups)
- ✅ Direct image pull from registries
- ✅ Better integration with Proxmox snapshots/backups

**Cons:**
- ❌ No Docker Compose support (need to manage each container separately)
- ❌ Requires manual orchestration of service dependencies
- ❌ Network configuration more complex
- ❌ Not available on older Proxmox versions

**When to Use:** Simple applications, future-proofing, Proxmox 9.1+ environments

**Implementation Effort:** High (8-16 hours)
- Decompose docker-compose.yml into individual containers
- Implement custom orchestration logic
- Test service networking and dependencies
- May not be worth it for complex multi-service apps

---

### Option 4: Docker Swarm Secrets + VM/Unprivileged LXC

**Architecture:**
```
Docker Swarm Cluster (1-node initially)
└── Secrets (encrypted at rest/transit)
└── PaperTrade Stack
```

**Pros:**
- ✅ Proper secrets management (no plain text .env)
- ✅ Native Docker orchestration features
- ✅ Easy scaling to multi-node later
- ✅ Built-in service health checks and restarts

**Cons:**
- ❌ Swarm mode overhead (unnecessary for single host)
- ❌ More complex than docker-compose
- ❌ Still requires VM or unprivileged LXC for security

**When to Use:** If secrets management is top priority, scaling is anticipated

**Implementation Effort:** Medium (3-6 hours)
- Convert docker-compose.yml to stack file
- Migrate secrets to Docker Swarm secrets
- Initialize swarm mode
- Deploy and test

---

### Option 5: External Secrets Manager (HashiCorp Vault)

**Architecture:**
```
Proxmox Host
├── Vault VM/Container
└── Docker LXC/VM
    └── PaperTrade (pulls secrets from Vault)
```

**Pros:**
- ✅ Enterprise-grade secrets management
- ✅ Audit logging, rotation, dynamic secrets
- ✅ Centralized for multiple applications
- ✅ Fine-grained access policies

**Cons:**
- ❌ Overkill for single application
- ❌ Additional infrastructure to maintain
- ❌ Complexity increase
- ❌ Requires application code changes (to fetch secrets)

**When to Use:** Multiple applications, compliance requirements, team environment

**Implementation Effort:** High (8-16 hours + ongoing maintenance)

---

## Recommendations

### Prioritized Improvement Roadmap

#### **Quick Wins (High Value, Low Effort)** 🎯

##### 1. **Improve Secrets Management** (2 hours)

**Problem:** Passwords regenerate on each deploy, breaking persistence.

**Solution:** Generate secrets once, store persistently.

```bash
# In deploy.sh - check if .env exists first
if ssh "${PROXMOX_HOST}" "pct exec ${CONTAINER_ID} -- test -f ${APP_DIR}/.env"; then
    log_info "Using existing .env file (preserves secrets)"
else
    log_info "Creating new .env file"
    # Generate secrets only on first deploy
fi
```

**Impact:** 
- ✅ Prevents breaking deployments
- ✅ No more losing database on update
- ⚠️ Still plain text storage (but better than now)

---

##### 2. **Add Container Cleanup Tasks** (1 hour)

**Problem:** No easy way to stop/clean up deployment.

**Solution:** Add Taskfile tasks.

```yaml
proxmox:stop:
  desc: "Stop PaperTrade containers"
  cmds:
    - ssh ${PROXMOX_HOST} "pct exec ${CONTAINER_ID} -- docker compose -f ${APP_DIR}/docker-compose.prod.yml down"

proxmox:destroy:
  desc: "Stop and remove container (DESTRUCTIVE)"
  cmds:
    - ssh ${PROXMOX_HOST} "pct stop ${CONTAINER_ID} && pct destroy ${CONTAINER_ID}"
```

**Impact:**
- ✅ Better lifecycle management
- ✅ Clean development workflow

---

##### 3. **Add Validation & Health Checks** (2 hours)

**Problem:** Deployment continues even if services fail to start.

**Solution:** Add verification steps.

```bash
verify_deployment() {
    log_info "Verifying deployment..."
    
    # Wait for services to be healthy
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if ssh "${PROXMOX_HOST}" "pct exec ${CONTAINER_ID} -- docker compose -f ${APP_DIR}/docker-compose.prod.yml ps --filter 'health=healthy' | grep -q 'healthy'"; then
            log_info "All services healthy"
            return 0
        fi
        sleep 5
        attempt=$((attempt + 1))
    done
    
    log_error "Services failed to become healthy"
    return 1
}
```

**Impact:**
- ✅ Catches deployment failures early
- ✅ Better reliability

---

##### 4. **Fix Static IP Configuration** (1 hour)

**Problem:** DHCP IP can change, breaking bookmarks/automation.

**Solution:** Support static IP configuration.

```bash
# In create-container.sh
--net0 name=eth0,bridge=vmbr0,ip=${CONTAINER_IP:-dhcp},gw=${GATEWAY:-}
```

**Usage:**
```bash
CONTAINER_IP="192.168.1.100/24" GATEWAY="192.168.1.1" task proxmox:create-container
```

**Impact:**
- ✅ Predictable URLs
- ✅ Better automation

---

##### 5. **Remove Dockerfile Patching** (0.5 hours)

**Problem:** Modifying source code during deployment is fragile.

**Solution:** Fix the backend Dockerfile in the repository, remove patching.

```bash
# Remove fix_dockerfile() function entirely
# Commit proper Dockerfile to repository
```

**Impact:**
- ✅ More predictable deployments
- ✅ Matches local development
- ✅ Easier debugging

---

##### 6. **Improve Error Messages** (1 hour)

**Problem:** Some errors are unclear or silent.

**Solution:** Add specific error handling.

```bash
# Example: Better SSH error handling
check_ssh_connection() {
    if ! ssh -o ConnectTimeout=5 "${PROXMOX_HOST}" "echo ok" &>/dev/null; then
        log_error "Cannot connect to Proxmox host: ${PROXMOX_HOST}"
        log_error "Check:"
        log_error "  1. Host is reachable"
        log_error "  2. SSH key is configured"
        log_error "  3. Username is correct (usually 'root')"
        exit 1
    fi
}
```

**Impact:**
- ✅ Faster troubleshooting
- ✅ Better user experience

---

#### **Medium-Term Improvements (2-4 weeks)** 📈

##### 7. **Migrate to Unprivileged LXC** (4-8 hours)

**Impact:** Security +++ | Complexity ++

See "Option 2: Unprivileged LXC + fuse-overlayfs" section above.

**Steps:**
1. Test unprivileged container creation on staging
2. Verify all services work with fuse-overlayfs
3. Document configuration quirks
4. Update create-container.sh script
5. Create migration guide

**Breaking Changes:**
- Requires Proxmox LXC config changes
- May need Docker daemon.json changes
- Could have performance differences

---

##### 8. **Add Container Registry** (3-6 hours)

**Impact:** Performance ++ | Deployment Speed +++

**Options:**
- **GitHub Container Registry**: Free for public images, integrates with GitHub Actions
- **Local Harbor**: Self-hosted, enterprise features
- **Simple Docker Registry**: Minimal self-hosted option

**Recommended:** GitHub Container Registry (easiest for solo developer)

**Changes:**
```yaml
# .github/workflows/release.yml
- name: Build and push images
  run: |
    docker build -t ghcr.io/timchild/papertrade-backend:${{ github.sha }} backend/
    docker push ghcr.io/timchild/papertrade-backend:${{ github.sha }}
```

```bash
# deploy.sh: Pull images instead of building
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

**Benefits:**
- Faster deployments (no build step)
- Version tagging and rollback
- Reduced bandwidth (only pull changed layers)

---

##### 9. **Implement Proper Secrets Management** (4-8 hours)

**Options:**
1. **Docker Swarm Secrets** (if using swarm)
2. **Ansible Vault** (if adopting Ansible)
3. **Simple encrypted file** (gpg or age)

**Recommended for solo dev:** Simple encrypted file approach

```bash
# Generate secrets once, encrypt
echo "POSTGRES_PASSWORD=$(openssl rand -base64 32)" > secrets.env
echo "SECRET_KEY=$(openssl rand -base64 32)" >> secrets.env
gpg --symmetric --cipher-algo AES256 secrets.env
# secrets.env.gpg can be committed to private repo

# Deploy script decrypts
gpg --decrypt secrets.env.gpg > /tmp/secrets.env
# Use in deployment
```

---

##### 10. **Add Automated Backups** (2-4 hours)

**Solution:** Leverage Proxmox backup features.

```bash
# Taskfile
proxmox:backup:
  desc: "Create Proxmox container backup"
  cmds:
    - ssh ${PROXMOX_HOST} "vzdump ${CONTAINER_ID} --storage local --mode snapshot --compress zstd"
    
proxmox:backup-db:
  desc: "Backup database only (faster)"
  cmds:
    - ssh ${PROXMOX_HOST} "pct exec ${CONTAINER_ID} -- docker compose -f ${APP_DIR}/docker-compose.prod.yml exec -T db pg_dump -U papertrade papertrade" | gzip > backups/papertrade-$(date +%Y%m%d).sql.gz
```

**Automation:**
```bash
# Add cron job on Proxmox host
0 2 * * * vzdump 107 --storage backup-nfs --mode snapshot --compress zstd --mailnotification failure
```

---

#### **Long-Term Strategic Changes (Future)** 🚀

##### 11. **Migrate to VM-based Deployment** (8-16 hours)

**When:** Before production launch with real user data.

**Why:** Maximum security and isolation.

**Implementation:**
1. Create Ubuntu VM template in Proxmox
2. Create `scripts/proxmox/create-vm.sh` (similar to create-container.sh)
3. Adapt deploy.sh to use `qm` commands instead of `pct`
4. Test thoroughly
5. Document migration path from LXC to VM

**Effort:** High, but one-time cost for long-term security.

---

##### 12. **Container Orchestration** (40+ hours)

**Options:**
- Docker Swarm (simpler, single-host works)
- Kubernetes (overkill for single app, but future-proof)

**When:** Multiple hosts, high availability needed, or multiple applications.

**Current assessment:** Not needed for PaperTrade's current scale.

---

##### 13. **Infrastructure as Code** (16-32 hours)

**Replace bash scripts with:**
- Terraform for Proxmox provisioning
- Ansible for configuration management
- Packer for image building

**When:** Team grows beyond solo developer, or managing multiple environments.

---

## Decision Matrix

| Criteria | Current (Privileged LXC) | Unprivileged LXC | VM | Proxmox OCI |
|----------|------------------------|-----------------|----|----|
| **Security** | ⚠️ Low | ✅ Medium | ✅✅ High | ✅ Medium-High |
| **Resource Usage** | ✅✅ Best | ✅✅ Best | ⚠️ More RAM/CPU | ✅✅ Best |
| **Setup Complexity** | ✅✅ Easy | ⚠️ Medium | ✅ Easy | ⚠️ Complex |
| **Maintenance** | ✅ Low | ⚠️ Medium | ✅ Low | ⚠️ Medium |
| **Docker Compatibility** | ✅✅ Full | ✅ Good | ✅✅ Full | ⚠️ Limited |
| **Production Ready** | ❌ No | ⚠️ Maybe | ✅ Yes | ⚠️ Simple apps only |
| **Implementation Time** | ✅ 0h (done) | ⚠️ 4-8h | ⚠️ 2-4h | ❌ 8-16h |

---

## Validation of Current Approach

### ✅ When Current Approach is OPTIMAL

The privileged LXC approach is **appropriate** for:

1. **Personal homelab** (no internet exposure)
2. **Development/testing** environments
3. **Proof-of-concept** deployments
4. **Resource-constrained** hosts (low RAM)
5. **Learning/experimentation** with deployment automation

### ⚠️ When Current Approach is ACCEPTABLE (with caveats)

Acceptable for:

1. Small business **with network isolation** (dedicated VLAN, firewall)
2. Internal-only applications (no public internet access)
3. Short-term deployments (< 6 months)

**Required hardening:**
- Network firewall rules
- Regular security updates
- Monitoring and intrusion detection
- Automated backups

### ❌ When Current Approach is UNACCEPTABLE

Do NOT use for:

1. **Production** with real user data
2. **Internet-exposed** applications
3. **Compliance-required** environments (HIPAA, PCI-DSS, SOC 2)
4. **Multi-tenant** scenarios
5. **Any scenario where container escape = business impact**

---

## Conclusion

### Final Assessment: **EVOLUTION** (not PIVOT)

The current privileged LXC implementation is **well-executed for its purpose** (homelab/development) but requires evolution before production use.

### Recommended Path Forward

**Phase 1: Quick Wins (Week 1)**
- ✅ Fix secrets persistence
- ✅ Add cleanup tasks
- ✅ Improve validation
- ✅ Remove Dockerfile patching
- ✅ Static IP support

**Phase 2: Security Hardening (Month 1-2)**
- Choose ONE:
  - **Path A**: Migrate to unprivileged LXC (stay on LXC, better security)
  - **Path B**: Migrate to VM (best security, more resources)
- Implement proper secrets management
- Add automated backups

**Phase 3: Production Readiness (Month 3)**
- Container registry integration
- Monitoring and alerting
- Disaster recovery testing
- Security scanning automation

### Effort vs. Impact Summary

| Improvement | Effort | Security Impact | Performance Impact | Recommendation |
|------------|--------|----------------|-------------------|----------------|
| Fix secrets persistence | 2h | Medium | None | **DO NOW** |
| Add cleanup tasks | 1h | Low | None | **DO NOW** |
| Add validation | 2h | Medium | None | **DO NOW** |
| Static IP | 1h | Low | None | **DO NOW** |
| Remove Dockerfile patch | 0.5h | Low | None | **DO NOW** |
| Unprivileged LXC | 4-8h | High | Low negative | Do before production |
| VM migration | 2-4h | Very High | Medium negative | Do before production |
| Container registry | 3-6h | Medium | High positive | Do after quick wins |
| Proper secrets | 4-8h | High | None | Do before production |
| Automated backups | 2-4h | N/A (DR) | None | Do soon |

### Bottom Line

**The current implementation is NOT broken** - it's a pragmatic, working solution appropriate for its context (homelab development). However, it represents **technical debt** that must be paid before production launch.

**For a solo developer project:**
1. Keep current approach for now (it works!)
2. Implement quick wins immediately (2-3 days)
3. Plan VM migration before public launch (security matters)
4. Don't over-engineer (HashiCorp Vault, K8s, etc. are overkill)

**Complexity vs. Security tradeoff:**
- Current: Simple + Insecure
- Unprivileged LXC: Medium complexity + Medium security
- VM: Simple + Secure ← **Best balance for production**

---

## References

1. **Proxmox LXC Security Best Practices**
   - XDA Developers: "Be careful when using privileged LXCs on Proxmox"
   - Proxmox Forum: "Docker in Unprivileged LXC or Dedicated VM?"
   - Blog.ktz.me: "AppArmor's Awkward Aftermath Atop Proxmox 9"

2. **Docker-in-LXC Guides**
   - McFisch Blog: "Docker Inside an Unprivileged Proxmox LXC Container"
   - BobCares: "Proxmox Docker Unprivileged Container"
   - Weisb.net: "Running Docker in LXC With Proxmox 7.1"

3. **Secrets Management**
   - Docker Docs: "Manage Sensitive Data with Secrets"
   - HashiCorp Developer: "Integrate with Docker"
   - Better Stack: "A Comprehensive Guide to Docker Secrets"

4. **Container Registries**
   - JFrog: "Comparing Docker Hub and GitHub Container Registry"
   - Daily.dev: "Top 9 Container Registries 2024"

5. **General Docker Security**
   - GitGuardian: "How to Handle Secrets in Docker"
   - Docker Docs: "AppArmor Security Profiles"

---

**Document Version**: 1.0  
**Last Updated**: January 11, 2026  
**Next Review**: Before production deployment planning
