import os
import socket
import time
import threading
import logging
from flask import Flask, jsonify, render_template
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

REAL_DEBRID_API_KEY = os.environ.get("REAL_DEBRID_API_KEY", "")
EASYNEWS_USER = os.environ.get("EASYNEWS_USER", "")
EASYNEWS_PASS = os.environ.get("EASYNEWS_PASS", "")
NEWSHOSTING_USER = os.environ.get("NEWSHOSTING_USER", "")
NEWSHOSTING_PASS = os.environ.get("NEWSHOSTING_PASS", "")
TWEAKNEWS_USER = os.environ.get("TWEAKNEWS_USER", "")
TWEAKNEWS_PASS = os.environ.get("TWEAKNEWS_PASS", "")

_cache = {}
_cache_lock = threading.Lock()
_CACHE_TTL = 60


def check_tcp(host, port, timeout=8):
    try:
        start = time.time()
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        latency = int((time.time() - start) * 1000)
        return {"status": "online", "latency_ms": latency}
    except Exception as e:
        return {"status": "offline", "error": str(e)}


def _format_gb(val):
    """Convert bytes or MB value to a readable GB string."""
    if val is None:
        return None
    try:
        val = float(val)
        # If value looks like bytes (very large number)
        if val > 1_000_000:
            return f"{val / 1_073_741_824:.1f} GB"
        # If value looks like MB
        elif val > 1000:
            return f"{val / 1024:.1f} GB"
        # Already in GB
        else:
            return f"{val:.1f} GB"
    except Exception:
        return str(val)


def check_real_debrid():
    if not REAL_DEBRID_API_KEY:
        return {"status": "unknown", "error": "No API key configured"}
    try:
        start = time.time()
        r = requests.get(
            "https://api.real-debrid.com/rest/1.0/user",
            headers={"Authorization": f"Bearer {REAL_DEBRID_API_KEY}"},
            timeout=15,
        )
        latency = int((time.time() - start) * 1000)
        if r.status_code == 200:
            data = r.json()
            return {
                "status": "online",
                "latency_ms": latency,
                "username": data.get("username"),
                "premium_until": data.get("expiration", "")[:10] if data.get("expiration") else None,
            }
        else:
            return {"status": "degraded", "http_code": r.status_code, "latency_ms": latency}
    except Exception as e:
        return {"status": "offline", "error": str(e)}


def check_easynews():
    if not EASYNEWS_USER or not EASYNEWS_PASS:
        return {"status": "unknown", "error": "No credentials configured"}
    try:
        start = time.time()
        r = requests.get(
            "https://members.easynews.com/2.0/api/user",
            auth=(EASYNEWS_USER, EASYNEWS_PASS),
            timeout=20,
        )
        latency = int((time.time() - start) * 1000)
        logger.info(f"Easynews API status: {r.status_code}, body: {r.text[:500]}")
        if r.status_code == 200:
            try:
                data = r.json()
                username = data.get("username") or data.get("uname") or EASYNEWS_USER.split("@")[0]
                expires = data.get("expiration") or data.get("memberExpire") or data.get("expire") or data.get("member_expire")
                if expires and len(str(expires)) > 10:
                    expires = str(expires)[:10]
                # Try various field names for allowance
                allowance_raw = (
                    data.get("gigs_left") or data.get("data_left") or
                    data.get("allowance_left") or data.get("remaining") or
                    data.get("gigsleft") or data.get("dataRemaining") or
                    data.get("gigs") or data.get("dl_left")
                )
                allowance = _format_gb(allowance_raw) if allowance_raw is not None else None
            except Exception:
                username = EASYNEWS_USER.split("@")[0]
                expires = None
                allowance = None
            return {
                "status": "online",
                "latency_ms": latency,
                "username": username,
                "premium_until": expires,
                "allowance_left": allowance,
            }
        elif r.status_code == 401:
            return {"status": "degraded", "error": "Auth failed", "latency_ms": latency}
        else:
            return {"status": "online", "latency_ms": latency, "username": EASYNEWS_USER.split("@")[0]}
    except requests.exceptions.Timeout:
        result = check_tcp("members.easynews.com", 443, timeout=8)
        result["username"] = EASYNEWS_USER.split("@")[0]
        return result
    except Exception as e:
        return {"status": "offline", "error": str(e)}


def _check_nntp(host, port, username, password, service):
    try:
        start = time.time()
        sock = socket.create_connection((host, port), timeout=8)
        sock.close()
        latency = int((time.time() - start) * 1000)
        result = {"status": "online", "latency_ms": latency, "host": f"{host}:{port}"}

        if username and password:
            try:
                if service == "newshosting":
                    api_resp = requests.get(
                        "https://www.newshosting.com/api/",
                        params={"action": "getaccountinfo"},
                        auth=(username, password),
                        timeout=10,
                    )
                else:
                    api_resp = requests.get(
                        "https://www.tweaknews.eu/en/api/getaccountinfo",
                        auth=(username, password),
                        timeout=10,
                    )
                logger.info(f"{service} API status: {api_resp.status_code}, body: {api_resp.text[:500]}")
                if api_resp.status_code == 200:
                    data = api_resp.json()
                    result["username"] = data.get("username") or username
                    expires = (
                        data.get("expire_date") or data.get("expiration") or
                        data.get("enddate") or data.get("end_date") or
                        data.get("memberExpire") or data.get("expiry")
                    )
                    if expires:
                        result["premium_until"] = str(expires)[:10]
                    connections = data.get("max_connections") or data.get("connections") or data.get("maxconn")
                    if connections:
                        result["connections"] = str(connections)
                    # Allowance fields
                    allowance_raw = (
                        data.get("gigs_left") or data.get("data_left") or
                        data.get("allowance_left") or data.get("remaining") or
                        data.get("gigsleft") or data.get("dataRemaining") or
                        data.get("dl_left") or data.get("bytes_remaining")
                    )
                    if allowance_raw is not None:
                        result["allowance_left"] = _format_gb(allowance_raw)
                else:
                    result["username"] = username
            except Exception as e:
                logger.warning(f"{service} account info failed: {e}")
                result["username"] = username

        return result
    except Exception as e:
        return {"status": "offline", "error": str(e), "host": f"{host}:{port}"}


def check_newshosting():
    return _check_nntp("news.newshosting.com", 563, NEWSHOSTING_USER, NEWSHOSTING_PASS, "newshosting")


def check_tweaknews():
    return _check_nntp("news.tweaknews.eu", 563, TWEAKNEWS_USER, TWEAKNEWS_PASS, "tweaknews")


def get_all_statuses():
    now = time.time()
    with _cache_lock:
        if _cache.get("updated_at") and now - _cache["updated_at"] < _CACHE_TTL:
            return _cache["data"]

    checks = {
        "real_debrid": check_real_debrid,
        "easynews": check_easynews,
        "newshosting": check_newshosting,
        "tweaknews": check_tweaknews,
    }

    data = {}

    def run(name, fn):
        data[name] = fn()

    threads = []
    for name, fn in checks.items():
        t = threading.Thread(target=run, args=(name, fn))
        t.start()
        threads.append(t)

    for t in threads:
        t.join(timeout=25)

    data["checked_at"] = int(now)

    with _cache_lock:
        _cache["data"] = data
        _cache["updated_at"] = now

    return data


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    return jsonify(get_all_statuses())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
