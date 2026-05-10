"""
Odoo API test client — loads credentials from ../.env and handles session auth.

Usage:
    python tests/api_client.py
"""

import os
import json
import requests
from pathlib import Path

# Load .env from module root
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

ODOO_URL = os.environ["ODOO_URL"]
ODOO_DB = os.environ["ODOO_DB"]
ODOO_USER = os.environ["ODOO_USER"]
ODOO_PASSWORD = os.environ["ODOO_PASSWORD"]

BASE = f"{ODOO_URL}/saycare/api"


def get_session() -> requests.Session:
    s = requests.Session()
    resp = s.post(f"{ODOO_URL}/web/session/authenticate", json={
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "db": ODOO_DB,
            "login": ODOO_USER,
            "password": ODOO_PASSWORD,
        },
    })
    resp.raise_for_status()
    result = resp.json().get("result", {})
    if not result.get("uid"):
        raise RuntimeError(f"Login failed: {resp.text}")
    print(f"Logged in as uid={result['uid']}")
    return s


def check_module_installed(s: requests.Session) -> bool:
    """Check if saycare_odoo_19 module is installed via Odoo RPC."""
    resp = s.post(f"{ODOO_URL}/web/dataset/call_kw", json={
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "model": "ir.module.module",
            "method": "search_read",
            "args": [[["name", "=", "saycare_odoo_19"]]],
            "kwargs": {"fields": ["name", "state"], "limit": 1},
        },
    })
    result = resp.json().get("result", [])
    if not result:
        print("  ✗ Module 'saycare_odoo_19' not found in Odoo")
        return False
    state = result[0].get("state")
    if state == "installed":
        print(f"  ✓ Module installed (state={state})")
        return True
    print(f"  ✗ Module found but not installed (state={state})")
    print("    → Go to Odoo > Apps, search 'saycare_odoo_19', and install it first.")
    return False


def _print(label: str, r: requests.Response):
    print(f"\n{label}  →  {r.status_code}")
    try:
        print(json.dumps(r.json(), indent=2, ensure_ascii=False))
    except Exception:
        # Odoo returns HTML on 404/500
        preview = r.text[:300].replace("\n", " ")
        print(f"  (non-JSON response) {preview}")


def test_patient_search(s: requests.Session, term: str = ""):
    r = s.get(f"{BASE}/patient/search", params={"term": term, "limit": 5})
    _print(f"[GET] /patient/search?term={term!r}", r)
    return r


def test_get_patient(s: requests.Session, patient_id: int):
    r = s.get(f"{BASE}/patient/{patient_id}")
    _print(f"[GET] /patient/{patient_id}", r)


def test_create_patient(s: requests.Session):
    payload = {
        "first_name": "Test",
        "last_name": "Patient",
        "mobile": "0500000001",
        "gender": "male",
        "financial_class": "cash",
    }
    r = s.post(f"{BASE}/patient", json=payload)
    _print("[POST] /patient", r)
    try:
        return r.json().get("id")
    except Exception:
        return None


def test_pharmacy_queue(s: requests.Session):
    r = s.get(f"{BASE}/pharmacy/queue")
    _print("[GET] /pharmacy/queue", r)


def test_specialties(s: requests.Session):
    r = s.get(f"{BASE}/specialties")
    _print("[GET] /specialties", r)


def test_doctors(s: requests.Session):
    r = s.get(f"{BASE}/doctors")
    _print("[GET] /doctors", r)


if __name__ == "__main__":
    session = get_session()

    print("\nChecking module installation...")
    if not check_module_installed(session):
        print("\nInstall the module first, then re-run this script.")
        raise SystemExit(1)

    test_patient_search(session, term="")
    test_specialties(session)
    test_doctors(session)
    test_pharmacy_queue(session)
    new_id = test_create_patient(session)
    if new_id:
        test_get_patient(session, new_id)
