import os
import socket
import time
import threading
from flask import Flask, jsonify, render_template
import requests

app = Flask(__name__)

REAL_DEBRID_API_KEY = os.environ.get("REAL_DEBRID_API_KEY", "")
EASYNEWS_USER = os.environ.get("EASYNEWS_USER", "")
EASYNEWS_PASS = os.environ.get("EASYNEWS_PASS", "")

_cache = {}
_cache_lock = threading.Lock()
_CACHE_TTL = 60  # seconds


def check_tcp(host, port, timeout=5):
    try:
        start = time.time()
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        latency = int((time.time() - start) * 1000)
        return {"status": "online", "latency_ms": latency}
    except Exception as e:
        return {"status": "offline", "error": str(e)}


def check_real_debrid():
    if not REAL_DEBRID_API_KEY:
        return {"status": "unknown", "error": "No API key configured"}
    try:
        start = time.time()
        r = requests.get(
            "https://api.real-debrid.com/rest/1.0/user",
            headers={"Authorization": f"Bearer {REAL_DEBRID_API_KEY}"},
            timeout=10,
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
            "https://members.easynews.com/2.0/api/search",
            params={"q": "test", "gps": "test", "pby": "1"},
            auth=(EASYNEWS_USER, EASYNEWS_PASS),
            timeout=10,
        )
        latency = int((time.time() - start) * 1000)
        if r.status_code == 200:
            return {"status": "online", "latency_ms": latency}
        elif r.status_code == 401:
            return {"status": "degraded", "error": "Auth failed", "latency_ms": latency}
        else:
            return {"status": "degraded", "http_code": r.status_code, "latency_ms": latency}
    except Exception as e:
        return {"status": "offline", "error": str(e)}


def check_newshosting():
    result = check_tcp("news.newshosting.com", 563)
    result["host"] = "news.newshosting.com:563"
    return result


def check_tweaknews():
    result = check_tcp("news.tweaknews.eu", 563)
    result["host"] = "news.tweaknews.eu:563"
    return result


def get_all_statuses():
    now = time.time()
    with _cache_lock:
        if _cache.get("updated_at") and now - _cache["updated_at"] < _CACHE_TTL:
            return _cache["data"]

    results = {}
    checks = {
        "real_debrid": check_real_debrid,
        "easynews": check_easynews,
        "newshosting": check_newshosting,
        "tweaknews": check_tweaknews,
    }

    threads = {}
    data = {}

    def run(name, fn):
        data[name] = fn()

    for name, fn in checks.items():
        t = threading.Thread(target=run, args=(name, fn))
        t.start()
        threads[name] = t

    for t in threads.values():
        t.join(timeout=15)

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
