# api/main.py
# GridlockDNA — FastAPI Backend (REAL DATA VERSION)
#
# This reads the actual files produced by ParkSenseAI.ipynb:
#   - live_zone_status.json   (45 compound zones, final output of Step 14)
#   - ambulance_alerts.json   (100 critical road-closure-near-hospital alerts, Step 11)
#   - hospitals.json          (8 hospitals, Step 9)
#
# SETUP:
#   1. Copy these 3 files into this same api/ folder (export them from the notebook
#      with: from google.colab import files; files.download("live_zone_status.json")
#      or just drag them out of the Colab/Jupyter file browser).
#   2. pip install fastapi uvicorn --break-system-packages
#   3. uvicorn main:app --reload --port 8000

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json
import os

app = FastAPI(title="GridlockDNA API", version="2.0.0 — real data")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

import math

def sanitize_nan(obj):
    """Recursively replace float NaN with None.

    Pandas exports NaN for missing values in JSON. Python's json.load()
    accepts NaN (non-standard), but FastAPI's response serializer rejects
    it → 500 Internal Server Error. This converts NaN → None (JSON null).
    """
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if isinstance(obj, dict):
        return {k: sanitize_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_nan(item) for item in obj]
    return obj

def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"\n\n  MISSING FILE: {filename}\n"
            f"  Expected at: {path}\n"
            f"  Export it from ParkSenseAI.ipynb and place it in api/ alongside main.py.\n"
        )
    with open(path, "r") as f:
        return sanitize_nan(json.load(f))

# ─── LOAD REAL DATA AT STARTUP ─────────────────────────────────────────────────
try:
    ZONES = load_json("live_zone_status.json")          # 45 compound zones
    AMBULANCE_ALERTS = load_json("ambulance_alerts.json") # 100 active critical incidents
    HOSPITALS = load_json("hospitals.json")               # 8 hospitals
    print(f"[OK] Loaded {len(ZONES)} zones, {len(AMBULANCE_ALERTS)} ambulance alerts, {len(HOSPITALS)} hospitals")
except FileNotFoundError as e:
    print(str(e))
    ZONES, AMBULANCE_ALERTS, HOSPITALS = [], [], []


def severity_from_score(score: float) -> str:
    """Bucket final_priority_score into critical/high/medium for map colour + UI."""
    if score >= 80:
        return "critical"
    elif score >= 40:
        return "high"
    else:
        return "medium"


def normalize_zone(z: dict) -> dict:
    """
    Map the notebook's real column names to the stable field names the
    frontend expects. Keeps original fields too, in case you want them.
    """
    return {
        "id": f"PC{z.get('parking_cluster_id')}",
        "name": f"Cluster {z.get('parking_cluster_id')} ({z.get('dominant_offence_code','').replace('is_','').replace('_',' ').title()})",
        "lat": z.get("lat"),
        "lng": z.get("lon"),
        "crs": round(z.get("CRS", 0), 1),
        "ambulance_weight": z.get("ambulance_weight"),
        "final_priority": round(z.get("final_priority_score", 0), 1),
        "nearest_hospital": z.get("nearest_hospital"),
        "hospital_km": round(z.get("nearest_hospital_dist_km", 0), 2),
        "violations": z.get("violation_count"),
        "incidents": z.get("incident_count"),
        "road_closure_rate": round(z.get("road_closure_rate", 0), 3),
        "dominant_vehicle_type": z.get("dominant_vehicle_type_parking"),
        "dominant_offence": z.get("dominant_offence_code"),
        "predicted_block_min": z.get("predicted_remaining_block_min"),
        "ambulance_delay_label": z.get("ambulance_delay_label"),
        "severity": severity_from_score(z.get("final_priority_score", 0)),
        # active = True only if this zone's ambulance_delay_label is CRITICAL/HIGH
        # (these are the zones with a live, model-flagged active risk)
        "active": z.get("ambulance_delay_label") in ("CRITICAL", "HIGH"),
    }


# ─── ENDPOINTS ────────────────────────────────────────────────────────────────

@app.get("/zones")
def get_zones():
    """All 45 real compound zones, normalised for the frontend map + dispatch queue."""
    return [normalize_zone(z) for z in ZONES]


@app.get("/alerts")
def get_alerts():
    """Zones with CRITICAL or HIGH ambulance_delay_label — drives the red banner."""
    normalized = [normalize_zone(z) for z in ZONES]
    return [z for z in normalized if z["ambulance_delay_label"] in ("CRITICAL", "HIGH")]


@app.get("/dispatch")
def get_dispatch(limit: int = 10):
    """Top N zones ranked by final_priority_score, for the BTP dispatch queue."""
    normalized = [normalize_zone(z) for z in ZONES]
    ranked = sorted(normalized, key=lambda z: z["final_priority"], reverse=True)
    return ranked[:limit]


@app.get("/flipkart")
def get_flipkart(threshold: float = 50.0):
    """High-priority zones as GeoJSON polygons — routing avoid-areas for Flipkart."""
    normalized = [normalize_zone(z) for z in ZONES]
    high_risk = [z for z in normalized if z["final_priority"] > threshold]
    features = []
    delta = 0.0014  # ~150m in degrees
    for z in high_risk:
        features.append({
            "type": "Feature",
            "properties": {"zone_id": z["id"], "name": z["name"], "priority": z["final_priority"]},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [z["lng"]-delta, z["lat"]-delta],
                    [z["lng"]+delta, z["lat"]-delta],
                    [z["lng"]+delta, z["lat"]+delta],
                    [z["lng"]-delta, z["lat"]+delta],
                    [z["lng"]-delta, z["lat"]-delta],
                ]]
            }
        })
    return {"type": "FeatureCollection", "features": features}


@app.get("/ambulance-alerts")
def get_ambulance_alerts(limit: int = 20):
    """
    Raw incident-level alerts from Step 11 (the 100 active road-closures near
    hospitals). This is the REAL replay feed — sorted by hospital proximity,
    most urgent first. Used by replay.py to simulate the live demo.
    """
    return AMBULANCE_ALERTS[:limit]


@app.get("/hospitals")
def get_hospitals():
    return HOSPITALS


# ─── LIVE REPLAY INGEST ─────────────────────────────────────────────────────────
# In-memory "live" override state — replay.py POSTs here to simulate incidents
# firing in real time. Doesn't mutate the underlying files.
_live_overrides = {}

@app.post("/ingest")
def ingest_event(event: dict):
    """Called by replay.py. Marks a zone as actively alerting for the demo."""
    incident_id = event.get("incident_id")
    _live_overrides[incident_id] = event
    return {"status": "ok", "incident_id": incident_id, "total_live_events": len(_live_overrides)}


@app.get("/live-events")
def get_live_events():
    """Frontend polls this to see what's fired during the replay."""
    return list(_live_overrides.values())


@app.get("/health")
def health():
    return {
        "status": "ok",
        "zones_loaded": len(ZONES),
        "ambulance_alerts_loaded": len(AMBULANCE_ALERTS),
        "hospitals_loaded": len(HOSPITALS),
    }


# ─── SERVE FRONTEND ────────────────────────────────────────────────────────────
# Serves the dashboard at http://localhost:8000/ — no more file:// issues.
FRONTEND_DIR = os.path.join(os.path.dirname(DATA_DIR), "frontennd")

@app.get("/")
def serve_dashboard():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"error": "index.html not found", "expected_at": index_path}
