# Database Migration Checklist

## Overview

This checklist ensures database migrations are properly applied during deployments.

## Pre-Deployment

1. **Verify Migration Files Exist**
   ```bash
   ls backend/migrations/versions/
   ```

2. **Test Migrations Locally**
   ```bash
   # Start local database
   task docker:up

   # Run migrations
   cd backend
   alembic upgrade head

   # Verify current version
   alembic current
   ```

3. **Review Migration Code**
   - Check upgrade() and downgrade() functions
   - Ensure nullable columns or default values for existing data
   - Test with production-like data volumes

## Deployment

1. **Deploy Application Code**
   ```bash
   task proxmox-vm:deploy
   ```

2. **Run Migrations on Production**
   ```bash
   ssh root@192.168.4.112 "cd /opt/papertrade && \
     docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend \
     alembic upgrade head"
   ```

3. **Verify Migration Applied**
   ```bash
   ssh root@192.168.4.112 "cd /opt/papertrade && \
     docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db \
     psql -U papertrade -d papertrade_dev -c 'SELECT * FROM alembic_version;'"
   ```

## Post-Deployment Verification

1. **Check Backend Logs**
   ```bash
   task proxmox-vm:logs SERVICE=backend
   ```

2. **Test Affected Endpoints**
   - Use browser or curl to test endpoints that use new schema
   - Check for SQL errors in logs

3. **Monitor Application**
   - Watch for 500 errors
   - Check database connection pool
   - Verify feature functionality

## Troubleshooting

### Migration Failed

If migration fails:

1. **Check Database Connection**
   ```bash
   ssh root@192.168.4.112 "cd /opt/papertrade && \
     docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend \
     env | grep DATABASE"
   ```

2. **Check Current Schema**
   ```bash
   ssh root@192.168.4.112 "cd /opt/papertrade && \
     docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db \
     psql -U papertrade -d papertrade_dev -c '\dt'"
   ```

3. **Manual Migration (Last Resort)**

   If Alembic fails and you must manually apply schema changes:

   ```bash
   # 1. Apply schema change manually
   ssh root@192.168.4.112 "cd /opt/papertrade && \
     docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db \
     psql -U papertrade -d papertrade_dev -c 'ALTER TABLE ...'

   # 2. Update alembic_version table
   # Get revision ID from migration file (e.g., a6a5412b5d02)
   ssh root@192.168.4.112 "cd /opt/papertrade && \
     docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db \
     psql -U papertrade -d papertrade_dev <<'EOF'
UPDATE alembic_version SET version_num = 'REVISION_ID';
EOF"
   ```

### Column Doesn't Exist Error

Symptoms: `column tablename.columnname does not exist`

Root Cause: Migration not applied but code deployed

Fix:
1. Run migrations (see Deployment step 2)
2. Verify schema matches code expectations
3. Restart backend if needed: `task proxmox-vm:restart SERVICE=backend`

## Prevention

1. **Add to Deployment Script**
   - Consider adding automatic migration step to `scripts/proxmox-vm/deploy.sh`
   - Add migration check before starting services

2. **CI/CD Integration**
   - Run migrations in staging before production
   - Add schema validation tests

3. **Monitoring**
   - Alert on SQLAlchemy errors containing "does not exist"
   - Track alembic_version in monitoring dashboard

## Historical Issues

### 2026-03-08: Missing holdings_breakdown Column

**Issue**: PR #195 added `holdings_breakdown` JSONB column to `portfolio_snapshots` table. Code was deployed but migration was never run, causing analytics page to fail.

**Root Challenge**: Alembic `env.py` didn't respect DATABASE_URL environment variable, always using SQLite from `alembic.ini`.

**Resolution**:
1. Manually added column: `ALTER TABLE portfolio_snapshots ADD COLUMN holdings_breakdown JSONB;`
2. Created alembic_version table and marked migration as applied
3. Fixed `migrations/env.py` to respect DATABASE_URL environment variable
4. Committed fix in commit `8d1d967`

**Lessons**:
- Always test migrations in production-like environment before deploying
- Verify Alembic configuration respects environment variables
- Add migration step to deployment checklist
- Consider automating migration execution in deployment script
