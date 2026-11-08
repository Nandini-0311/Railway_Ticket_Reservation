import sys
import os
import threading
import time
import urllib.request
import json
from http.server import HTTPServer

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from server import RailwayRequestHandler

# Spin up server on test port 8001
TEST_PORT = 8001
httpd = HTTPServer(('127.0.0.1', TEST_PORT), RailwayRequestHandler)
t = threading.Thread(target=httpd.serve_forever, daemon=True)
t.start()
time.sleep(1)

base_url = f"http://127.0.0.1:{TEST_PORT}"

# Test 1: GET /api/stations
with urllib.request.urlopen(f"{base_url}/api/stations") as resp:
    data = json.loads(resp.read().decode())
    assert data["success"] is True
    assert len(data["stations"]) > 0
    print("PASS: /api/stations returned", len(data["stations"]), "stations.")

# Test 2: POST /api/admin/login
req_data = json.dumps({"username": "admin", "password": "admin123"}).encode('utf-8')
req = urllib.request.Request(f"{base_url}/api/admin/login", data=req_data, headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    assert data["success"] is True
    admin_token = data["session_token"]
    print("PASS: /api/admin/login succeeded, got token.")

# Test 3: GET /api/admin/metrics with X-Session-Token
req = urllib.request.Request(f"{base_url}/api/admin/metrics", headers={'X-Session-Token': admin_token})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    assert data["success"] is True
    assert data["metrics"]["total_trains"] >= 8
    print("PASS: /api/admin/metrics returned total trains:", data["metrics"]["total_trains"])

httpd.shutdown()
print("ALL SERVER HTTP API TESTS PASSED!")
