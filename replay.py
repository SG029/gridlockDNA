# replay.py — REAL DATA VERSION
#
# Replays the actual 100 ambulance alerts from Step 11 of the notebook,
# sorted by hospital proximity (most urgent first). Feeds one every 2
# seconds into the running API so the dashboard updates live during the demo.
#
# Run AFTER starting the API:
#   uvicorn main:app --reload --port 8000   (in api/ folder)
#   python replay.py                          (in project root, or wherever this lives)

import requests, time, json, sys, os

API_URL = "http://localhost:8000"
ALERTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api", "ambulance_alerts.json")

def check_api():
    try:
        r = requests.get(f"{API_URL}/health", timeout=2)
        return r.status_code == 200, r.json()
    except Exception:
        return False, None

def load_alerts(limit=15):
    """
    Prefer pulling from the live API (/ambulance-alerts) so this script works
    even if you haven't copied the file locally. Falls back to local file.
    """
    try:
        r = requests.get(f"{API_URL}/ambulance-alerts", params={"limit": limit}, timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass

    if os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE) as f:
            return json.load(f)[:limit]

    print(f"  Could not load alerts from API or {ALERTS_FILE}")
    sys.exit(1)

def run_replay(limit=15, interval=2.2):
    print("\n GridlockDNA — Live Replay (real ambulance_alerts.json)")
    print("─" * 55)

    ok, health = check_api()
    if not ok:
        print(f"  API not reachable at {API_URL}")
        print("  Start it first: cd api && uvicorn main:app --reload --port 8000")
        sys.exit(1)

    print(f"  API connected — {health['zones_loaded']} zones, "
          f"{health['ambulance_alerts_loaded']} ambulance alerts loaded")

    alerts = load_alerts(limit=limit)
    print(f"  Replaying {len(alerts)} real critical incidents, {interval}s apart")
    print(f"  Sorted by hospital proximity — most urgent fires first")
    print(f"  Watch the dashboard at your frontend URL\n")
    time.sleep(1)

    for i, event in enumerate(alerts):
        cause = event.get("event_cause", "unknown")
        hosp = event.get("nearest_hospital", "unknown")
        dist = event.get("nearest_hospital_dist_km", "?")
        veh = event.get("veh_type") or "—"
        incident_id = event.get("incident_id", f"evt_{i}")

        print(f"  [{i+1:02d}/{len(alerts)}] {incident_id} · {cause} · {veh} · "
              f"{dist}km from {hosp}")

        try:
            r = requests.post(f"{API_URL}/ingest", json=event, timeout=3)
            if r.status_code == 200:
                print(f"         ✓ Ingested — live event count: {r.json()['total_live_events']}")
            else:
                print(f"         ✗ API error: {r.status_code}")
        except Exception as e:
            print(f"         ✗ Request failed: {e}")

        time.sleep(interval)

    print(f"\n  Replay complete — {len(alerts)} real incidents injected.")
    print(f"  These are genuine Astram events: active status + requires_road_closure=True,")
    print(f"  matched to their nearest of 8 Bangalore hospitals.\n")

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    run_replay(limit=n)
