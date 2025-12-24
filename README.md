# Chromebook Dashboard

A real-time dashboard for managing Google Workspace Chrome devices.

## Setup

1. **Upload Google Service Account Credentials**
   - Place your `credentials.json` file in `/opt/chromebook-dashboard/`
   - Ensure the service account has domain-wide delegation enabled
   - Required scopes are configured automatically

2. **Configure Environment**
   ```bash
   cd /opt/chromebook-dashboard
   cp .env.example .env
   nano .env
   ```
   - Update `GOOGLE_ADMIN_EMAIL` with your admin email

3. **Restart Service**
   ```bash
   systemctl restart chromebook-dashboard
   ```

## Access

- Dashboard: http://YOUR_IP:8080
- API Docs: http://YOUR_IP:8080/docs

## Service Management

```bash
# Check status
systemctl status chromebook-dashboard

# View logs
journalctl -u chromebook-dashboard -f

# Restart
systemctl restart chromebook-dashboard
```

## Cache Management

The dashboard caches API responses for 5 minutes by default. To clear cache:

```bash
curl -X POST http://localhost:8080/api/cache/clear
```
