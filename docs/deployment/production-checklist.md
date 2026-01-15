# Production Readiness Checklist

**Last Updated**: January 11, 2026
**Agent**: quality-infra
**Purpose**: Comprehensive checklist for production deployment verification

---

## Overview

This checklist ensures your Zebu deployment is production-ready. Complete all items before deploying to production or exposing to real users.

**Deployment Stages:**
1. **Pre-Deployment**: Setup and configuration
2. **Deployment**: Initial deployment verification
3. **Post-Deployment**: Ongoing monitoring and maintenance

---

## Pre-Deployment Checklist

### Infrastructure

- [ ] Proxmox host is updated to latest stable version
- [ ] VM created with appropriate resources (4+ CPU cores, 8+ GB RAM, 50+ GB disk)
- [ ] VM has static IP address (or DHCP reservation for predictable IP)
- [ ] Network connectivity verified (VM can reach internet and local network)
- [ ] DNS records configured and propagated
- [ ] Reverse proxy (NPMplus) configured and accessible
- [ ] SSL certificates obtained from Let's Encrypt
- [ ] Port forwarding configured correctly (80, 443 → reverse proxy)

### Security

- [ ] **SSH Configuration**
  - [ ] SSH key-based authentication enabled
  - [ ] Password authentication disabled (`PasswordAuthentication no`)
  - [ ] Root login restricted (`PermitRootLogin prohibit-password`)
  - [ ] SSH port changed from default 22 (optional but recommended)
  - [ ] Fail2ban or similar installed for brute-force protection

- [ ] **Firewall**
  - [ ] UFW or iptables configured on VM
  - [ ] Only required ports exposed (22 for SSH, 80/443 through reverse proxy)
  - [ ] Backend API port (8000) not exposed directly to internet
  - [ ] Database port (5432) only accessible from localhost
  - [ ] Redis port (6379) only accessible from localhost

- [ ] **Passwords & Secrets**
  - [ ] Strong `POSTGRES_PASSWORD` generated (32+ characters)
  - [ ] Strong `SECRET_KEY` generated (32+ characters)
  - [ ] All default passwords changed (VM, NPMplus, Postgres)
  - [ ] `.env` file permissions restricted (`chmod 600 .env`)
  - [ ] Secrets not committed to version control (`.env` in `.gitignore`)
  - [ ] API keys (Alpha Vantage) configured correctly

- [ ] **Application Security**
  - [ ] CORS origins restricted to production domains only
  - [ ] `APP_ENV=production` set in `.env`
  - [ ] `APP_DEBUG=false` set in `.env`
  - [ ] API rate limiting configured (if applicable)
  - [ ] Input validation enabled in backend
  - [ ] SQL injection protection verified (using SQLModel parameterized queries)

- [ ] **HTTPS/SSL**
  - [ ] Valid SSL certificate obtained (Let's Encrypt)
  - [ ] Force SSL enabled (HTTP redirects to HTTPS)
  - [ ] HSTS enabled in reverse proxy
  - [ ] HTTP/2 enabled for better performance
  - [ ] Certificate auto-renewal configured

### Database

- [ ] **Configuration**
  - [ ] PostgreSQL configured in production mode
  - [ ] Strong database password set
  - [ ] Database user created with minimal required privileges
  - [ ] Connection pooling configured (default settings acceptable for small scale)
  - [ ] Max connections limit appropriate for expected load

- [ ] **Backups**
  - [ ] Automated backup strategy implemented
  - [ ] Backup script scheduled (daily recommended)
  - [ ] Backup retention policy defined (e.g., keep 7 daily, 4 weekly, 12 monthly)
  - [ ] Backups stored off-VM (separate storage or cloud)
  - [ ] Backup restoration procedure tested at least once
  - [ ] Database migration rollback procedure documented

- [ ] **Data Integrity**
  - [ ] Database migrations tested in staging first
  - [ ] Foreign key constraints in place
  - [ ] Indexes created for common queries
  - [ ] Database vacuum scheduled (auto-vacuum enabled)

### Application

- [ ] **Environment Configuration**
  - [ ] All required environment variables set in `.env`
  - [ ] `VITE_API_BASE_URL` points to production API domain
  - [ ] `CORS_ORIGINS` includes all production domains
  - [ ] Alpha Vantage API key valid and rate limits configured
  - [ ] Logging level appropriate (`INFO` for production)

- [ ] **Docker Configuration**
  - [ ] Production Docker Compose file used (`docker-compose.prod.yml`)
  - [ ] Health checks configured for all services
  - [ ] Restart policies set to `unless-stopped` or `always`
  - [ ] Resource limits configured (memory, CPU)
  - [ ] Log rotation configured for Docker containers
  - [ ] Docker daemon configured with storage limits

- [ ] **Code Quality**
  - [ ] All tests passing (unit, integration)
  - [ ] Linters passing (Ruff, ESLint)
  - [ ] Type checking passing (Pyright, TypeScript)
  - [ ] No known security vulnerabilities in dependencies
  - [ ] Code reviewed and approved
  - [ ] Latest stable version deployed (tagged release)

- [ ] **Functionality**
  - [ ] All critical features working in staging
  - [ ] Authentication flow tested (Clerk integration)
  - [ ] Portfolio creation/management working
  - [ ] Trade execution working (BUY orders)
  - [ ] Price fetching working (Alpha Vantage integration)
  - [ ] Transaction history displaying correctly

---

## Deployment Verification Checklist

### Initial Deployment

- [ ] VM accessible via SSH
- [ ] Application code deployed via git (not tarball)
- [ ] `.env` file transferred and configured
- [ ] Docker images built successfully
- [ ] All services started (`docker compose ps` shows all healthy)
- [ ] Health endpoints responding:
  - [ ] `https://yourdomain.com/health` (if exposed)
  - [ ] `https://api.yourdomain.com/health`

### Service Health

- [ ] **Frontend**
  - [ ] HTTPS loads correctly (`https://yourdomain.com`)
  - [ ] Valid SSL certificate (green lock icon)
  - [ ] No console errors in browser DevTools
  - [ ] Static assets loading correctly
  - [ ] Responsive design working on mobile

- [ ] **Backend**
  - [ ] API accessible (`https://api.yourdomain.com/health`)
  - [ ] CORS headers present in responses
  - [ ] Authentication working (Clerk integration)
  - [ ] API documentation accessible (if intended to be public)

- [ ] **Database**
  - [ ] PostgreSQL container running
  - [ ] Database accessible from backend (health check passes)
  - [ ] Migrations applied successfully
  - [ ] No connection pool exhaustion

- [ ] **Redis**
  - [ ] Redis container running
  - [ ] Backend can connect to Redis
  - [ ] Cache working as expected

### Network & DNS

- [ ] Domain resolves correctly (`nslookup yourdomain.com`)
- [ ] Subdomain resolves correctly (`nslookup api.yourdomain.com`)
- [ ] HTTP redirects to HTTPS
- [ ] Both www and non-www versions work (if configured)
- [ ] No mixed content warnings (all resources loaded over HTTPS)

### Performance

- [ ] Page load time acceptable (<3 seconds for initial load)
- [ ] API response time acceptable (<500ms for simple queries)
- [ ] No memory leaks observed (check `docker stats`)
- [ ] CPU usage reasonable (<50% average)
- [ ] Disk usage has room to grow (>50% free)

---

## Post-Deployment Checklist

### Monitoring

- [ ] **Service Monitoring**
  - [ ] Health check endpoints monitored (manual or automated)
  - [ ] Service uptime tracked
  - [ ] Container restart count monitored
  - [ ] CPU/memory usage monitored

- [ ] **Logs**
  - [ ] Application logs accessible (`task proxmox-vm:logs`)
  - [ ] Log rotation configured (prevent disk fill)
  - [ ] Error logs reviewed regularly
  - [ ] Critical errors trigger alerts (optional for small scale)

- [ ] **Disk Space**
  - [ ] Disk usage monitored (`df -h`)
  - [ ] Alerts configured for >80% disk usage (manual check acceptable)
  - [ ] Docker image cleanup scheduled (`docker image prune`)
  - [ ] Log file cleanup scheduled

- [ ] **SSL Certificates**
  - [ ] Certificate expiry monitored (Let's Encrypt expires in 90 days)
  - [ ] Auto-renewal working (NPMplus handles this)
  - [ ] Test renewal process at least once

### Backup & Recovery

- [ ] **Backups**
  - [ ] Daily database backups running
  - [ ] Backups verified (spot check restoration)
  - [ ] Backup size monitored (ensure sufficient storage)
  - [ ] Off-site backup copy maintained (optional but recommended)

- [ ] **VM Snapshots**
  - [ ] Pre-deployment snapshot taken
  - [ ] Post-deployment snapshot taken (once stable)
  - [ ] Snapshot retention policy defined
  - [ ] Snapshot restoration tested

- [ ] **Disaster Recovery**
  - [ ] Recovery procedure documented
  - [ ] RTO/RPO defined (Recovery Time/Point Objective)
  - [ ] Recovery procedure tested at least once
  - [ ] Emergency contact list created

### Maintenance

- [ ] **Updates**
  - [ ] OS security updates scheduled (automated or weekly manual)
  - [ ] Docker image updates planned (monthly or as needed)
  - [ ] Application updates tested in staging first
  - [ ] Dependency updates reviewed for security vulnerabilities

- [ ] **Deployment Process**
  - [ ] Redeployment procedure documented
  - [ ] Rollback procedure documented and tested
  - [ ] Deployment checklist created
  - [ ] Change log maintained

- [ ] **Capacity Planning**
  - [ ] Current resource usage baseline established
  - [ ] Growth projections estimated
  - [ ] Scaling plan documented (when to add resources)
  - [ ] Cost monitoring in place

### Documentation

- [ ] **Runbooks**
  - [ ] Deployment procedure documented
  - [ ] Rollback procedure documented
  - [ ] Common troubleshooting steps documented
  - [ ] Emergency shutdown procedure documented

- [ ] **Architecture**
  - [ ] Network diagram created (VM, reverse proxy, services)
  - [ ] Service dependencies documented
  - [ ] Configuration management documented
  - [ ] Secrets management documented

- [ ] **Contacts**
  - [ ] Admin contact information documented
  - [ ] DNS provider access documented (securely)
  - [ ] Hosting provider access documented
  - [ ] Domain registrar access documented

---

## Ongoing Operations Checklist

### Weekly

- [ ] Review application logs for errors
- [ ] Check service health (`task proxmox-vm:status`)
- [ ] Monitor disk space usage
- [ ] Review backup success/failure
- [ ] Check SSL certificate expiry date

### Monthly

- [ ] Review and apply security updates (OS, Docker, dependencies)
- [ ] Test backup restoration procedure
- [ ] Review monitoring data and performance metrics
- [ ] Check for dependency vulnerabilities
- [ ] Rotate log files if needed
- [ ] Review and update documentation

### Quarterly

- [ ] Full disaster recovery test
- [ ] Review and update security practices
- [ ] Performance testing and optimization
- [ ] Capacity planning review
- [ ] Review and update runbooks

### Annually

- [ ] Comprehensive security audit
- [ ] Review and update disaster recovery plan
- [ ] Review and rotate secrets (passwords, API keys)
- [ ] Review and update SLAs/SLOs
- [ ] Architecture review for optimization opportunities

---

## Incident Response Checklist

### When Something Goes Wrong

1. **Assess Impact**
   - [ ] Determine severity (critical, high, medium, low)
   - [ ] Identify affected users/services
   - [ ] Document incident start time

2. **Immediate Actions**
   - [ ] Check service status (`task proxmox-vm:status`)
   - [ ] Review recent logs (`task proxmox-vm:logs`)
   - [ ] Identify root cause if obvious
   - [ ] Implement immediate fix or workaround

3. **Communication**
   - [ ] Notify users if service is down (status page or email)
   - [ ] Update stakeholders on incident status
   - [ ] Document actions taken

4. **Resolution**
   - [ ] Implement permanent fix
   - [ ] Test fix thoroughly
   - [ ] Verify service restoration
   - [ ] Monitor for recurrence

5. **Post-Incident**
   - [ ] Document incident in log (what, when, why, how fixed)
   - [ ] Conduct post-mortem (if significant incident)
   - [ ] Update runbooks/documentation with lessons learned
   - [ ] Implement preventive measures

---

## Small-Scale Production Notes

For small-scale production (personal use, small team, low traffic):

**Acceptable Simplifications:**
- Manual monitoring instead of automated alerting
- Weekly backup verification instead of daily
- Manual security updates instead of automated
- Basic logging instead of comprehensive log aggregation
- Visual monitoring instead of metrics dashboards

**Non-Negotiable:**
- HTTPS/SSL must be configured
- Secrets must be strong and secure
- Regular backups must be taken
- Security updates must be applied
- Firewall must be configured

---

## Production Readiness Score

**Calculate your score:**
- Pre-Deployment: _____ / 63 items
- Deployment Verification: _____ / 24 items
- Post-Deployment: _____ / 36 items

**Overall: _____ / 123 items**

**Recommended Minimum Scores:**
- Pre-Deployment: 90% (57/63) before going live
- Deployment Verification: 100% (24/24) before declaring success
- Post-Deployment: 80% (29/36) within first week of production

**Note**: Some items may not apply to your specific deployment. Adjust totals accordingly.

---

## Resources

- [Proxmox VM Deployment Guide](./proxmox-vm-deployment.md)
- [Domain and SSL Setup Guide](./domain-and-ssl-setup.md)
- [Zebu Documentation](../../README.md)
- [OWASP Security Best Practices](https://owasp.org/www-project-top-ten/)
- [12 Factor App Methodology](https://12factor.net/)

---

**Production Deployment Best Practices:**
- Start small, iterate, improve
- Document everything
- Test in staging first
- Always have a rollback plan
- Monitor continuously
- Update regularly
- Learn from incidents

**Production Readiness is a Journey, Not a Destination! 🚀**
