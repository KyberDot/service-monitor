# KyberBOX · Service Monitor

A lightweight Docker app that checks the live status of Real-Debrid, Easynews, Newshosting, and Tweaknews.

## What it shows

| Service | Check | Info Shown |
|---|---|---|
| Real-Debrid | HTTP API | Username, premium expiry |
| Easynews | HTTP (solr-search) | Username, connectivity |
| Newshosting | TCP :563 | Username, latency |
| Tweaknews | TCP :563 | Username, latency |

Results cached 60s, page auto-refreshes every 60s.

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

All credentials are optional — unconfigured services show as N/A while others display live status.

Get your Real-Debrid API key at: https://real-debrid.com/apitoken
