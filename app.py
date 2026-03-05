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
        # Use the same search endpoint the client uses to validate credentials
        r = requests.get(
            "https://members.easynews.com/2.0/search/solr-search/",
            params={
                "fly": "2", "gps": "test", "sb": "1", "pno": "1",
                "pby": "1", "u": "1", "st": "basic", "fty[]": "VIDEO",
            },
            auth=(EASYNEWS_USER, EASYNEWS_PASS),
            timeout=20,
        )
        latency = int((time.time() - start) * 1000)
        if r.status_code == 200:
            return {
                "status": "online",
                "latency_ms": latency,
                "username": EASYNEWS_USER.split("@")[0],
            }
        elif r.status_code in (401, 403):
            return {"status": "degraded", "error": "Auth failed", "latency_ms": latency}
        else:
            return {"status": "degraded", "http_code": r.status_code, "latency_ms": latency}
    except requests.exceptions.Timeout:
        # Fallback to TCP if HTTP times out
        result = check_tcp("members.easynews.com", 443, timeout=8)
        result["username"] = EASYNEWS_USER.split("@")[0]
        return result
    except Exception as e:
        return {"status": "offline", "error": str(e)}


def check_newshosting():
    result = check_tcp("news.newshosting.com", 563)
    result["host"] = "newshosting.com"
    if NEWSHOSTING_USER:
        result["username"] = NEWSHOSTING_USER
    return result


def check_tweaknews():
    result = check_tcp("news.tweaknews.eu", 563)
    result["host"] = "tweaknews.eu"
    if TWEAKNEWS_USER:
        result["username"] = TWEAKNEWS_USER
    return result


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


import json as _json
from flask import request as _request

EXPIRY_FILE = os.path.join(os.path.dirname(__file__), "expiry_data.json")
_expiry_lock = threading.Lock()

def _load_expiry():
    try:
        with open(EXPIRY_FILE, "r") as f:
            return _json.load(f)
    except Exception:
        return {}

def _save_expiry(data):
    with open(EXPIRY_FILE, "w") as f:
        _json.dump(data, f)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    return jsonify(get_all_statuses())


@app.route("/api/expiry", methods=["GET"])
def get_expiry():
    with _expiry_lock:
        return jsonify(_load_expiry())


@app.route("/api/expiry", methods=["POST"])
def save_expiry():
    with _expiry_lock:
        data = _load_expiry()
        payload = _request.get_json(force=True) or {}
        key = payload.get("key")
        if not key:
            return jsonify({"error": "missing key"}), 400
        if "expiry" in payload:
            data[f"expiry_{key}"] = payload["expiry"]
        if "plan" in payload:
            data[f"plan_{key}"] = payload["plan"]
        _save_expiry(data)
        return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
