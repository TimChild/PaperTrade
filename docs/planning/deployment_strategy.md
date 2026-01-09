# PaperTrade Deployment Strategy

**Version**: 1.0
**Last Updated**: January 9, 2026
**Status**: Planning Phase

## Overview

Two-stage deployment strategy for PaperTrade:
1. **Stage 1**: Local Proxmox deployment (immediate, low-cost validation)
2. **Stage 2**: AWS production deployment (scalable, public-facing)

This approach allows us to validate the application in a real production environment before incurring cloud costs.

---

## Stage 1: Proxmox Local Deployment

**Timeline**: 1-2 days
**Goal**: Deploy fully functional app on local network for initial users and real-world testing

### Infrastructure Requirements

**Proxmox Server Setup**:
- Docker host VM (Ubuntu 22.04 LTS recommended)
- Minimum resources:
  - 2 vCPU
  - 4GB RAM
  - 20GB storage
- Network access on local LAN
- Static IP assignment

**Services to Deploy**:
- PostgreSQL database (persistent volume)
- Redis cache (persistent volume)
- Backend API (FastAPI)
- Frontend SPA (Nginx serving static files)

### Deployment Architecture

```
┌─────────────────────────────────────────────┐
│           Proxmox Host                      │
│  ┌─────────────────────────────────────┐   │
│  │     Docker Compose Stack            │   │
│  │  ┌──────────┐  ┌──────────┐        │   │
│  │  │ Frontend │  │ Backend  │        │   │
│  │  │  Nginx   │  │ FastAPI  │        │   │
│  │  │  :80     │  │  :8000   │        │   │
│  │  └────┬─────┘  └────┬─────┘        │   │
│  │       │             │               │   │
│  │  ┌────┴─────────────┴─────┐        │   │
│  │  │    PostgreSQL :5432     │        │   │
│  │  └─────────────────────────┘        │   │
│  │  ┌─────────────────────────┐        │   │
│  │  │     Redis :6379         │        │   │
│  │  └─────────────────────────┘        │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
         │
         │ LAN Access
         ▼
   Local Network Users
   (http://192.168.x.x or http://papertrade.local)
```

### Implementation Steps

**1. Pre-Deployment Polish** (1-2 days)
- Fix TradeForm intermittent crash bug
- Implement Daily Change calculation
- Add high-value UX improvements (Task 085-087)
- Comprehensive testing with real Alpha Vantage data

**2. Proxmox VM Setup** (2-3 hours)
- Create Ubuntu VM on Proxmox
- Install Docker and Docker Compose
- Configure static IP and hostname
- Set up persistent volumes for data

**3. Production Configuration** (2-3 hours)
- Create production environment files
- Configure Clerk production instance (or keep development for local)
- Set up Alpha Vantage API key (production key if available)
- Database initialization and migration
- Secrets management (environment variables)

**4. Docker Compose Deployment** (1-2 hours)
- Use `docker-compose.prod.yml` (already exists in repo)
- Configure volumes for persistence:
  - PostgreSQL data: `/var/lib/postgresql/data`
  - Redis data: `/data`
- Set up restart policies (always restart)
- Configure logging (JSON file driver with rotation)

**5. Initial Deployment & Testing** (2-3 hours)
- Deploy containers via Docker Compose
- Run database migrations (Alembic)
- Smoke test all critical paths
- Load test with multiple concurrent users
- Monitor logs and resource usage

**6. Monitoring & Maintenance** (ongoing)
- Set up simple health checks
- Daily database backups via cron
- Log rotation configuration
- Resource monitoring (htop, docker stats)

### Configuration Files Needed

**`docker-compose.proxmox.yml`** (new file):
```yaml
version: '3.8'

services:
  db:
    image: postgres:16
    restart: always
    environment:
      POSTGRES_DB: papertrade_prod
      POSTGRES_USER: papertrade
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U papertrade"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: always
    environment:
      DATABASE_URL: postgresql://papertrade:${DB_PASSWORD}@db:5432/papertrade_prod
      REDIS_URL: redis://redis:6379
      CLERK_SECRET_KEY: ${CLERK_SECRET_KEY}
      ALPHA_VANTAGE_API_KEY: ${ALPHA_VANTAGE_API_KEY}
      ENV: production
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        VITE_API_URL: http://192.168.x.x:8000  # Replace with actual IP
        VITE_CLERK_PUBLISHABLE_KEY: ${CLERK_PUBLISHABLE_KEY}
    restart: always
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
```

**`.env.proxmox`** (gitignored):
```bash
DB_PASSWORD=<secure-password>
CLERK_SECRET_KEY=<production-key>
CLERK_PUBLISHABLE_KEY=<production-key>
ALPHA_VANTAGE_API_KEY=DK1ACPJOWOIGLVIJ
```

### Success Criteria

- ✅ All services running and healthy on Proxmox VM
- ✅ Application accessible on LAN (http://192.168.x.x or http://papertrade.local)
- ✅ Database persists across container restarts
- ✅ No critical bugs encountered during first week of usage
- ✅ Performance acceptable for 1-5 concurrent users
- ✅ Data backed up daily

### Limitations

- **No SSL/HTTPS**: Local network only, no public domain
- **No CDN**: Static assets served directly from Nginx
- **Manual scaling**: Single VM, no auto-scaling
- **Basic monitoring**: No APM, just logs and manual checks
- **Local access only**: Not accessible from outside network

These limitations are acceptable for Stage 1 validation phase.

---

## Stage 2: AWS Production Deployment

**Timeline**: 3-5 days
**Goal**: Public-facing, scalable, production-grade deployment

### Infrastructure Architecture

**AWS Services**:
- **Compute**: ECS Fargate (containerized, serverless)
- **Database**: RDS PostgreSQL (Multi-AZ for HA)
- **Cache**: ElastiCache Redis
- **Static Assets**: S3 + CloudFront CDN
- **Load Balancer**: Application Load Balancer (ALB)
- **DNS**: Route 53
- **SSL**: ACM (AWS Certificate Manager)
- **Secrets**: AWS Secrets Manager
- **Monitoring**: CloudWatch + CloudWatch Logs
- **Infrastructure as Code**: AWS CDK (already scaffolded)

### Architecture Diagram

```
Internet
    │
    ▼
┌─────────────────────────────────────────────┐
│         Route 53 DNS                        │
│    papertrade.com → CloudFront             │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│         CloudFront CDN                      │
│    - Static assets (S3)                     │
│    - API requests → ALB                     │
└─────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────┐
│   Application Load Balancer (ALB)          │
│    - SSL/TLS termination                    │
│    - Path routing (/api/* → Backend)       │
└─────────────────────────────────────────────┘
    │
    ├───────────────────┬─────────────────────┐
    │                   │                     │
    ▼                   ▼                     ▼
┌─────────┐      ┌─────────┐         ┌─────────┐
│ ECS     │      │ ECS     │         │ ECS     │
│ Fargate │      │ Fargate │         │ Fargate │
│ Backend │      │ Backend │         │ Backend │
│ Task 1  │      │ Task 2  │         │ Task N  │
└────┬────┘      └────┬────┘         └────┬────┘
     │                │                    │
     └────────────────┴────────────────────┘
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
    ┌──────────┐          ┌──────────┐
    │   RDS    │          │ElastiCache│
    │PostgreSQL│          │  Redis   │
    │ Multi-AZ │          │          │
    └──────────┘          └──────────┘
```

### Implementation Steps

**1. AWS CDK Infrastructure** (2-3 days)
- Define VPC, subnets, security groups
- RDS PostgreSQL instance (db.t3.micro for MVP)
- ElastiCache Redis cluster
- ECS cluster with Fargate tasks
- Application Load Balancer with target groups
- S3 bucket for frontend static assets
- CloudFront distribution
- Route 53 hosted zone and records
- ACM SSL certificate
- Secrets Manager for sensitive data
- CloudWatch dashboards and alarms

**2. CI/CD Pipeline** (1 day)
- GitHub Actions workflow for production deployment
- Build Docker images and push to ECR
- Update ECS task definitions
- Automated database migrations
- Blue-green deployment strategy
- Rollback capability

**3. Monitoring & Observability** (1 day)
- CloudWatch Logs aggregation
- CloudWatch Metrics and Alarms
- Error tracking (Sentry integration)
- Performance monitoring (APM)
- Uptime monitoring (external service)

**4. Security Hardening** (1 day)
- WAF rules for common attacks
- Rate limiting on ALB
- DDoS protection via Shield
- Security group lockdown
- IAM roles with least privilege
- Database encryption at rest and in transit
- Secrets rotation policy

**5. Production Deployment** (1 day)
- Deploy infrastructure via CDK
- Run production database migrations
- Deploy application containers
- Configure DNS and SSL
- Smoke test all critical paths
- Load testing
- Security audit

### Cost Estimation (Monthly)

| Service | Configuration | Est. Cost |
|---------|--------------|-----------|
| ECS Fargate | 2 tasks × 0.25 vCPU, 0.5GB | ~$15 |
| RDS PostgreSQL | db.t3.micro (Multi-AZ) | ~$30 |
| ElastiCache Redis | cache.t3.micro | ~$15 |
| ALB | 1 ALB | ~$20 |
| CloudFront | Low traffic | ~$5 |
| S3 | Static assets | ~$1 |
| Route 53 | 1 hosted zone | ~$1 |
| **Total** | | **~$87/month** |

**Note**: Costs scale with usage. Alpha Vantage free tier allows 500 requests/day.

### Success Criteria

- ✅ Application accessible via HTTPS on custom domain
- ✅ Auto-scaling based on CPU/memory metrics
- ✅ Database backups automated (daily snapshots)
- ✅ 99.9% uptime SLA
- ✅ Sub-second API response times (p95)
- ✅ Monitoring and alerting functional
- ✅ Zero-downtime deployments
- ✅ Security audit passed

---

## Migration Path: Proxmox → AWS

**Data Migration**:
1. Export PostgreSQL database from Proxmox: `pg_dump`
2. Import to AWS RDS: `psql` or AWS DMS
3. Verify data integrity with test queries
4. Run application tests against new database

**DNS Cutover**:
1. Test AWS deployment with temporary URL
2. Lower TTL on existing DNS records (24 hours before)
3. Update DNS to point to CloudFront/ALB
4. Monitor for 24-48 hours
5. Decommission Proxmox deployment

**Rollback Plan**:
- Keep Proxmox deployment active for 1 week after AWS cutover
- Can quickly revert DNS if issues arise
- Database backup available for restoration

---

## Pre-Deployment Checklist

**Code Quality** (Must Complete Before Stage 1):
- [ ] Fix TradeForm intermittent crash (Task 085)
- [ ] Implement Daily Change calculation (Task 086)
- [ ] High-priority UX improvements (Task 087)
- [ ] All E2E tests passing
- [ ] Load testing completed (50+ concurrent users)
- [ ] Security review of authentication flow

**Infrastructure**:
- [ ] Production environment variables documented
- [ ] Database migration scripts tested
- [ ] Backup and restore procedures documented
- [ ] Monitoring and alerting configured
- [ ] Incident response plan created

**Documentation**:
- [ ] User guide created
- [ ] API documentation updated
- [ ] Deployment runbook created
- [ ] Operations manual for maintenance

---

## Timeline Summary

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| **Pre-Deployment Polish** | 1-2 days | Tasks 085-087 |
| **Proxmox Deployment** | 1-2 days | Polish complete |
| **Proxmox Validation** | 1 week | Real usage testing |
| **AWS Infrastructure** | 2-3 days | CDK development |
| **AWS Deployment** | 1-2 days | Infrastructure ready |
| **AWS Validation** | 1 week | Production testing |
| **Total** | **2-3 weeks** | |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Alpha Vantage rate limits | High | Medium | Cache aggressively, implement fallback mock data |
| Database corruption | Low | High | Automated backups, tested restore procedures |
| Security breach | Medium | High | Regular security audits, WAF, rate limiting |
| Cost overrun (AWS) | Medium | Medium | Start with minimal resources, monitor closely |
| Performance issues | Medium | Medium | Load testing before launch, monitoring alerts |

---

## Next Steps

1. **Immediate**: Create and execute polish tasks (085-087)
2. **Week 1**: Deploy to Proxmox, validate with real usage
3. **Week 2-3**: Build AWS infrastructure, deploy to production
4. **Week 4**: Monitor, iterate, optimize

This strategy allows for incremental validation while minimizing risk and cost.
