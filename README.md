# KyberBOX · Service Monitor

A lightweight Docker app that checks the live status of Real-Debrid, Easynews, Newshosting, and Tweaknews — showing latency, account info, expiry dates, and allowance remaining.

## How it works

- **Real-Debrid** — HTTP API · shows username, premium expiry
- **Easynews** — HTTP API · shows username, expiry, allowance left
- **Newshosting** — TCP :563 + HTTP API · shows username, expiry, connections, allowance left
- **Tweaknews** — TCP :563 + HTTP API · shows username, expiry, connections, allowance left

Results are cached for 60 seconds. Page auto-refreshes every 60 seconds.

## Docker Compose

```yaml
service-monitor:
  image: ghcr.io/kyberdot/service-monitor:latest
  container_name: service-monitor
  restart: unless-stopped
  environment:
    - REAL_DEBRID_API_KEY=${REAL_DEBRID_API_KEY}
    - EASYNEWS_USER=${EASYNEWS_USER}
    - EASYNEWS_PASS=${EASYNEWS_PASS}
    - NEWSHOSTING_USER=${NEWSHOSTING_USER}
    - NEWSHOSTING_PASS=${NEWSHOSTING_PASS}
    - TWEAKNEWS_USER=${TWEAKNEWS_USER}
    - TWEAKNEWS_PASS=${TWEAKNEWS_PASS}
  ports:
    - "127.0.0.1:8007:8080"
  networks:
    - your-network
```

## .env variables

```
REAL_DEBRID_API_KEY=your_real_debrid_api_key
EASYNEWS_USER=your_easynews_username
EASYNEWS_PASS=your_easynews_password
NEWSHOSTING_USER=your_newshosting_username
NEWSHOSTING_PASS=your_newshosting_password
TWEAKNEWS_USER=your_tweaknews_username
TWEAKNEWS_PASS=your_tweaknews_password
```

All credentials are optional — services without credentials configured will show as N/A while others continue to display their live status.

Get your Real-Debrid API key at: https://real-debrid.com/apitoken
