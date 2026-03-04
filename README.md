# Service Monitor

A simple one-page Docker app that checks the live status of Real-Debrid, Easynews, Newshosting, and Tweaknews.

## How it works

- **Real-Debrid** — HTTP API call to `api.real-debrid.com/rest/1.0/user` (requires API key)
- **Easynews** — HTTP API call to `members.easynews.com` (requires credentials)
- **Newshosting** — TCP socket check on `news.newshosting.com:563`
- **Tweaknews** — TCP socket check on `news.tweaknews.eu:563`

Results are cached for 60 seconds. Page auto-refreshes every 60 seconds.

## Docker Compose

Add this to your existing compose file:

```yaml
service-monitor:
  image: ghcr.io/kyberdot/service-monitor:latest
  container_name: service-monitor
  restart: unless-stopped
  environment:
    - REAL_DEBRID_API_KEY=${REAL_DEBRID_API_KEY}
    - EASYNEWS_USER=${EASYNEWS_USER}
    - EASYNEWS_PASS=${EASYNEWS_PASS}
  ports:
    - "127.0.0.1:8082:8080"
  networks:
    - your-network
```

## .env variables

```
REAL_DEBRID_API_KEY=your_real_debrid_api_key
EASYNEWS_USER=your_easynews_username
EASYNEWS_PASS=your_easynews_password
```

Get your Real-Debrid API key at: https://real-debrid.com/apitoken
