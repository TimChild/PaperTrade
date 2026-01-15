# Domain and SSL Setup Guide

**Last Updated**: January 11, 2026
**Agent**: quality-infra
**Purpose**: Configure custom domain with HTTPS/SSL for production deployment

---

## Overview

This guide walks through configuring a custom domain (e.g., `zebutrader.com`) with automatic HTTPS/SSL for your Zebu deployment. This is a **one-time setup** performed after the application is running on your Proxmox VM.

**Prerequisites:**
- Zebu deployed and running on Proxmox VM (see [proxmox-vm-deployment.md](./proxmox-vm-deployment.md))
- Domain registered and managed through DNS provider (this guide uses Cloudflare)
- Reverse proxy available (this guide uses NPMplus - Nginx Proxy Manager Plus)
- Access to your network's public IP or ability to configure port forwarding

**Infrastructure Assumptions:**
- **VM IP**: `192.168.4.111` (internal network)
- **NPMplus IP**: `192.168.4.200` (reverse proxy on Proxmox host network)
- **Domain**: `zebutrader.com` (example - replace with your domain)
- **DNS Provider**: Cloudflare (instructions adaptable to other providers)

**What This Guide Covers:**
1. DNS configuration in Cloudflare
2. Reverse proxy setup in NPMplus
3. Backend CORS configuration for production domain
4. Frontend environment configuration
5. Verification and troubleshooting

---

## Table of Contents

- [Part 1: DNS Configuration (Cloudflare)](#part-1-dns-configuration-cloudflare)
- [Part 2: NPMplus Reverse Proxy Configuration](#part-2-npmplus-reverse-proxy-configuration)
- [Part 3: Backend CORS Configuration](#part-3-backend-cors-configuration)
- [Part 4: Frontend Environment Update](#part-4-frontend-environment-update)
- [Part 5: Verification & Testing](#part-5-verification--testing)
- [Part 6: Troubleshooting](#part-6-troubleshooting)

---

## Part 1: DNS Configuration (Cloudflare)

### Step 1: Access Cloudflare Dashboard

1. Log into [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Select your domain (`zebutrader.com`)
3. Navigate to **DNS** → **Records**

### Step 2: Create DNS Records

You'll need DNS records pointing to your public IP address. If your Proxmox host is behind a router:
- Your **public IP** is what the internet sees (check at [whatismyip.com](https://www.whatismyip.com/))
- Configure **port forwarding** on your router: `80` and `443` → `192.168.4.200` (NPMplus)

**For Main Domain:**

| Type | Name | Content | Proxy Status | TTL |
|------|------|---------|--------------|-----|
| A | `@` | `<your-public-ip>` | Proxied | Auto |

**For API Subdomain (Recommended):**

| Type | Name | Content | Proxy Status | TTL |
|------|------|---------|--------------|-----|
| A | `api` | `<your-public-ip>` | Proxied | Auto |

**Proxy Status Options:**
- **Proxied** (orange cloud): Traffic goes through Cloudflare (DDoS protection, CDN, but may add latency)
- **DNS Only** (gray cloud): Direct connection to your server (faster, but no Cloudflare protection)

**Recommendation**: Start with **Proxied** for DDoS protection. Switch to **DNS Only** if you experience issues.

### Step 3: Verify DNS Propagation

DNS changes can take 24-48 hours to propagate globally, but Cloudflare is usually fast (minutes to hours).

```bash
# Check DNS resolution
nslookup zebutrader.com
nslookup api.zebutrader.com

# Or use online tools:
# https://www.whatsmydns.net/
```

**Note**: You can proceed with NPMplus configuration before DNS fully propagates. NPMplus will request SSL certificates once DNS resolves correctly.

---

## Part 2: NPMplus Reverse Proxy Configuration

### What is NPMplus?

NPMplus (Nginx Proxy Manager Plus) is a user-friendly web interface for managing Nginx reverse proxy configurations. It:
- Routes external domain requests to internal services
- Automatically manages SSL certificates (Let's Encrypt)
- Handles certificate renewal
- Provides a simple UI instead of editing Nginx config files

### Step 1: Access NPMplus Interface

1. Open your browser and navigate to: `http://192.168.4.200:81`
2. Login with your admin credentials

**Default credentials** (if not changed):
- Email: `admin@example.com`
- Password: `changeme`

**⚠️ Security**: Change the default password immediately after first login!

### Step 2: Configure Proxy Host for Frontend

1. Click **Hosts** → **Proxy Hosts** → **Add Proxy Host**

**Details Tab:**
- **Domain Names**: `zebutrader.com` (add without `www`, or add both)
- **Scheme**: `http`
- **Forward Hostname/IP**: `192.168.4.111` (your VM IP)
- **Forward Port**: `80`
- **Cache Assets**: ✅ Enabled (recommended)
- **Block Common Exploits**: ✅ Enabled (recommended)
- **Websockets Support**: ✅ Enabled (if using WebSockets for real-time features)

**SSL Tab:**
- **SSL Certificate**: Select "Request a new SSL Certificate"
- **Force SSL**: ✅ Enabled (redirects HTTP to HTTPS)
- **HTTP/2 Support**: ✅ Enabled (better performance)
- **HSTS Enabled**: ✅ Enabled (forces HTTPS in browsers)
- **Email Address for Let's Encrypt**: Your email address
- ✅ "I Agree to the Let's Encrypt Terms of Service"

3. Click **Save**

NPMplus will automatically:
- Request an SSL certificate from Let's Encrypt
- Configure Nginx to handle the domain
- Set up automatic certificate renewal

**Expected Result**: `https://zebutrader.com` now serves your frontend with valid SSL!

### Step 3: Configure Proxy Host for Backend API

**Option A: Subdomain (Recommended)**

1. Click **Add Proxy Host** again

**Details Tab:**
- **Domain Names**: `api.zebutrader.com`
- **Scheme**: `http`
- **Forward Hostname/IP**: `192.168.4.111`
- **Forward Port**: `8000`
- **Cache Assets**: ⬜ Disabled (API responses shouldn't be cached)
- **Block Common Exploits**: ✅ Enabled
- **Websockets Support**: ✅ Enabled (if backend uses WebSockets)

**SSL Tab:**
- Same SSL settings as frontend (request new certificate)

**Option B: Path-Based Routing (Alternative)**

Instead of a subdomain, route `/api/*` to the backend:

1. Edit the existing `zebutrader.com` proxy host
2. Go to **Advanced** tab
3. Add custom Nginx configuration:

```nginx
location /api/ {
    proxy_pass http://192.168.4.111:8000/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

**Recommendation**: Use **Option A (subdomain)** for cleaner separation and easier configuration.

---

## Part 3: Backend CORS Configuration

### Understanding the Issue

Web browsers enforce **Cross-Origin Resource Sharing (CORS)** rules. When your frontend (`https://zebutrader.com`) makes API requests to the backend, the backend must explicitly allow requests from that domain.

### Current CORS Configuration

The backend respects the `CORS_ORIGINS` environment variable (see `backend/src/zebu/main.py`):

```python
# CORS configuration
# Allow specific origins from environment variable
allowed_origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Update Backend CORS for Production

Configure allowed origins for your production domain:

1. SSH into your VM:
```bash
ssh root@192.168.4.111
cd /opt/zebu
```

2. Edit `.env` file and add:
```bash
# Production CORS configuration
CORS_ORIGINS=https://zebutrader.com,https://api.zebutrader.com
APP_ENV=production
```

3. Restart the backend to apply changes:
```bash
cd /opt/zebu
docker compose -f docker-compose.prod.yml restart backend
```

4. Verify CORS is working:
```bash
curl -H "Origin: https://zebutrader.com" -I https://api.zebutrader.com/health
# Look for: Access-Control-Allow-Origin: https://zebutrader.com
```

### Why Subdomain Needs CORS

Even though `api.zebutrader.com` is a subdomain of `zebutrader.com`, browsers treat them as different origins. You must add both to `CORS_ORIGINS`.

---

## Part 4: Frontend Environment Update

### Update Frontend API URL

The frontend needs to know where to send API requests.

1. SSH into VM:
```bash
ssh root@192.168.4.111
cd /opt/zebu
```

2. Edit `.env` file:
```bash
nano .env
```

3. Update `VITE_API_BASE_URL`:

**If using subdomain (Option A):**
```bash
VITE_API_BASE_URL=https://api.zebutrader.com/api/v1
```

**If using path-based routing (Option B):**
```bash
VITE_API_BASE_URL=https://zebutrader.com/api/v1
```

4. Save the file (Ctrl+O, Enter, Ctrl+X)

### Rebuild and Restart Frontend

The frontend is built at Docker image build time, so you need to rebuild:

```bash
cd /opt/zebu

# Rebuild frontend with new environment variable
docker compose -f docker-compose.prod.yml build frontend

# Restart all services
docker compose -f docker-compose.prod.yml up -d

# Verify services are healthy
docker compose -f docker-compose.prod.yml ps
```

---

## Part 5: Verification & Testing

### Checklist

Go through each item to verify your setup:

- [ ] **DNS Resolution**: `nslookup zebutrader.com` returns your public IP
- [ ] **HTTPS Certificate**: `https://zebutrader.com` loads with valid SSL (green lock icon)
- [ ] **Frontend Loads**: Application interface appears correctly
- [ ] **API Connection**: Frontend can fetch data (check Network tab in browser DevTools)
- [ ] **No CORS Errors**: Browser console shows no CORS-related errors
- [ ] **Backend Health**: `https://api.zebutrader.com/health` returns `{"status":"healthy"}`
- [ ] **API Docs**: `https://api.zebutrader.com/docs` loads (if you want to expose this)
- [ ] **Authentication**: Login flow works correctly (Clerk redirects)
- [ ] **HTTPS Redirect**: `http://zebutrader.com` redirects to `https://zebutrader.com`

### Testing Steps

1. **Test Frontend Access:**
   ```bash
   curl -I https://zebutrader.com
   # Should return: HTTP/2 200
   ```

2. **Test Backend Health:**
   ```bash
   curl https://api.zebutrader.com/health
   # Should return: {"status":"healthy"}
   ```

3. **Test CORS (from browser console):**
   ```javascript
   // Open browser console on https://zebutrader.com
   fetch('https://api.zebutrader.com/api/v1/portfolios')
     .then(r => r.json())
     .then(console.log)
     .catch(console.error)
   // Should succeed without CORS errors
   ```

4. **Test Full Application Flow:**
   - Open `https://zebutrader.com`
   - Log in (if authentication required)
   - Create a portfolio
   - Execute a trade
   - Verify data appears correctly

### Browser Developer Tools

Use browser DevTools to diagnose issues:

1. **Open DevTools**: F12 or Right-click → Inspect
2. **Network Tab**: Check API requests
   - Look for failed requests (red)
   - Check request/response headers
   - Verify API URLs are correct
3. **Console Tab**: Check for errors
   - CORS errors appear here
   - JavaScript errors
4. **Application Tab**: Check storage
   - Cookies
   - Local Storage
   - Session Storage

---

## Part 6: Troubleshooting

### DNS Issues

**Problem**: Domain doesn't resolve

```bash
# Check if DNS is propagated
nslookup zebutrader.com

# Try different DNS servers
nslookup zebutrader.com 8.8.8.8  # Google DNS
nslookup zebutrader.com 1.1.1.1  # Cloudflare DNS
```

**Solutions**:
- Wait for DNS propagation (can take 24-48 hours)
- Verify DNS records in Cloudflare dashboard
- Clear your local DNS cache: `sudo dscacheutil -flushcache` (macOS) or `ipconfig /flushdns` (Windows)

**Problem**: DNS resolves but site doesn't load

**Solutions**:
- Verify port forwarding on your router (80, 443 → 192.168.4.200)
- Check NPMplus is accessible internally: `curl http://192.168.4.200`
- Verify Proxmox firewall isn't blocking traffic

### SSL Certificate Issues

**Problem**: NPMplus can't obtain SSL certificate

**Possible Causes**:
1. DNS not fully propagated
2. Ports 80/443 not properly forwarded
3. Cloudflare proxy interfering with Let's Encrypt validation

**Solutions**:
- **Wait for DNS**: Let's Encrypt validates domain ownership via DNS
- **Check port forwarding**: Ensure external port 80 reaches NPMplus
- **Cloudflare DNS Only mode**: Temporarily disable Cloudflare proxy (gray cloud)
  - Let NPMplus obtain certificate
  - Re-enable proxy after certificate is issued
- **Check NPMplus logs**: Look for specific error messages

**Problem**: Certificate expired or renewal failed

**Solutions**:
- NPMplus auto-renews certificates 30 days before expiry
- Check NPMplus is running and accessible
- Manually renew in NPMplus UI: Edit proxy host → SSL → Force renew

### CORS Errors

**Problem**: Browser console shows CORS errors

```
Access to fetch at 'https://api.zebutrader.com/api/v1/portfolios' from origin 'https://zebutrader.com'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present
```

**Solutions**:
1. **Verify CORS_ORIGINS in .env:**
   ```bash
   ssh root@192.168.4.111
   cat /opt/zebu/.env | grep CORS_ORIGINS
   # Should show: CORS_ORIGINS=https://zebutrader.com,https://api.zebutrader.com
   ```

2. **Check backend logs:**
   ```bash
   ssh root@192.168.4.111
   cd /opt/zebu
   docker compose -f docker-compose.prod.yml logs backend | tail -50
   ```

3. **Restart backend after env changes:**
   ```bash
   docker compose -f docker-compose.prod.yml restart backend
   ```

4. **Test backend directly:**
   ```bash
   curl -H "Origin: https://zebutrader.com" -I https://api.zebutrader.com/health
   # Look for: Access-Control-Allow-Origin: https://zebutrader.com
   ```

### Frontend Not Loading

**Problem**: Frontend shows blank page or old version

**Solutions**:
1. **Clear browser cache**: Ctrl+Shift+R (hard refresh)
2. **Verify environment variables:**
   ```bash
   ssh root@192.168.4.111
   cat /opt/zebu/.env | grep VITE_API_BASE_URL
   ```

3. **Rebuild frontend:**
   ```bash
   cd /opt/zebu
   docker compose -f docker-compose.prod.yml build frontend
   docker compose -f docker-compose.prod.yml up -d
   ```

4. **Check frontend logs:**
   ```bash
   docker compose -f docker-compose.prod.yml logs frontend
   ```

### NPMplus Connection Issues

**Problem**: Can't access NPMplus UI

**Solutions**:
- Verify NPMplus is running on Proxmox host
- Check firewall: `http://192.168.4.200:81` accessible from your network
- Restart NPMplus container (depends on your NPMplus installation method)

**Problem**: Proxy host shows offline

**Solutions**:
- Check VM is running: `ssh root@proxmox qm status 200`
- Verify services running: `ssh root@192.168.4.111 docker compose -f /opt/zebu/docker-compose.prod.yml ps`
- Check NPMplus can reach VM: From NPMplus host, `curl http://192.168.4.111`

### Cloudflare Proxy Issues

**Problem**: Slow response times or connection timeouts

**Cause**: Cloudflare proxy may add latency or interfere with WebSocket connections

**Solutions**:
- Switch to **DNS Only** mode (gray cloud) in Cloudflare
- Disable Cloudflare features temporarily to isolate issue
- Check Cloudflare Analytics for blocked requests

**Problem**: Let's Encrypt validation fails with Cloudflare proxied

**Solution**:
1. Temporarily disable Cloudflare proxy (gray cloud)
2. Wait 5 minutes for DNS propagation
3. Request SSL certificate in NPMplus
4. Re-enable Cloudflare proxy after certificate issued

### WebSocket Connection Issues

**Problem**: Real-time features not working

**Solutions**:
- Verify **Websockets Support** enabled in NPMplus proxy host
- Check Cloudflare proxy settings (may need to disable for WebSocket routes)
- Add custom Nginx configuration in NPMplus:
  ```nginx
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  ```

### API Not Accessible

**Problem**: `https://api.zebutrader.com` returns 502 Bad Gateway

**Solutions**:
1. **Check backend is running:**
   ```bash
   ssh root@192.168.4.111
   docker compose -f /opt/zebu/docker-compose.prod.yml ps backend
   ```

2. **Verify port 8000 is listening:**
   ```bash
   ss -tulpn | grep 8000
   ```

3. **Check NPMplus proxy host configuration:**
   - Forward Port should be `8000`
   - Forward Hostname/IP should be `192.168.4.111`

4. **Test backend locally on VM:**
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status":"healthy"}
   ```

### General Debugging

**Check all service status:**
```bash
# From local machine
task proxmox-vm:status

# From VM
ssh root@192.168.4.111
cd /opt/zebu
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100
```

**Network connectivity test:**
```bash
# Test from local machine to NPMplus
curl -I http://192.168.4.200

# Test from local machine to VM
curl -I http://192.168.4.111

# Test from VM to internet (DNS resolution)
ssh root@192.168.4.111 curl -I https://google.com
```

**Firewall check:**
```bash
# On VM, check if firewall is blocking
ssh root@192.168.4.111
ufw status  # If UFW is installed

# On Proxmox host
iptables -L -n | grep 192.168.4.111
```

---

## Additional Resources

- **NPMplus Documentation**: https://nginxproxymanager.com/
- **Cloudflare DNS Documentation**: https://developers.cloudflare.com/dns/
- **Let's Encrypt Documentation**: https://letsencrypt.org/docs/
- **CORS Documentation**: https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
- **Zebu Deployment Docs**: [proxmox-vm-deployment.md](./proxmox-vm-deployment.md)

---

## Security Considerations

### Best Practices

- [ ] **Change NPMplus default password** immediately
- [ ] **Use strong, unique passwords** for all services
- [ ] **Keep Cloudflare proxy enabled** for DDoS protection (if not causing issues)
- [ ] **Restrict CORS origins** to only your domains (avoid wildcards)
- [ ] **Don't expose API docs** publicly in production (remove `/docs` route or add authentication)
- [ ] **Enable HSTS** in NPMplus to force HTTPS
- [ ] **Monitor SSL certificate expiry** (NPMplus auto-renews, but check occasionally)
- [ ] **Regular security updates** for NPMplus, Proxmox, and VM OS
- [ ] **Configure rate limiting** in NPMplus or application (prevent abuse)
- [ ] **Set up monitoring/alerts** for service downtime

### Exposing Services

**Recommended exposure:**
- ✅ Frontend: Public (`https://zebutrader.com`)
- ✅ Backend API: Public with authentication (`https://api.zebutrader.com`)
- ⚠️ API Docs: Internal only or behind authentication
- ❌ Database: Never expose publicly
- ❌ Redis: Never expose publicly
- ❌ NPMplus admin UI: Internal network only

**Port forwarding should only expose:**
- Port 80 (HTTP, redirects to HTTPS)
- Port 443 (HTTPS)

All other services should remain on internal network.

---

**Domain Setup Complete! 🎉**

Your Zebu application is now accessible via your custom domain with automatic HTTPS!
