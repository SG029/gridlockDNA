# GridlockDNA

**Bangalore Traffic Intelligence System — Flipkart Gridlock Hackathon 2.0**

GridlockDNA finds the places in Bangalore where chronic illegal parking and recurring traffic incidents physically overlap — and uses that overlap to power three things: a real-time enforcement dispatch dashboard, an ambulance-priority safety layer, and a last-mile delivery routing optimiser.

Two city datasets — 298,450 parking violation records and 8,173 Astram traffic incident logs — had never been joined before. GridlockDNA spatially clusters both and intersects them to surface **45 compound gridlock zones**: locations where bad parking and traffic incidents compound each other, not just coexist in the same city.

---

## Why this matters

A zone with heavy parking violations but no nearby incidents is a parking problem. A zone with both — heavy violations *and* recurring incidents *and* proximity to a hospital — is where an ambulance actually gets stuck. Nobody had built that joint view before. GridlockDNA does.

---

## The Pipeline

The project runs as a 5-phase pipeline, each phase building on the last.

## Repository Structure


GridlockDNA/
│
├── api/
│   ├── ambulance_alerts.json
│   ├── hospitals.json
│   ├── live_zone_status.json
│   └── main.py
│
├── data/
│   ├── .gitkeep
│   └── jan_to_may_police_violation_anonymized.csv
│
├── frontend/
│   └── index.html
│
├── ml_pipeline/
│   ├── .gitkeep
│   ├── GridlockDNA.ipynb
│   ├── ambulance_alerts.json
│   ├── compound_zones.geojson
│   ├── crs_scores.csv
│   ├── duration_model.pkl
│   ├── duration_train.csv
│   ├── final_priority_scores.csv
│   ├── hospitals.json
│   ├── incident_clusters.geojson
│   ├── live_zone_status.json
│   └── parking_clusters.geojson
│
├── .gitignore
├── README.md
├── replay.py
└── requirements.txt


### Phase 1 — Data Preparation
Cleaned both raw datasets: dropped empty columns, filtered rejected/duplicate records, parsed JSON-encoded offence fields into severity flags, converted all timestamps to IST, and computed a recidivism score per vehicle based on repeat-violation history.

- **Input:** 298,450 parking violations, 8,173 Astram incidents
- **Output:** 248,376 clean parking records, 6,639 clean incident records
- 27,971 vehicles identified as repeat offenders (more than one violation)

### Phase 2 — Spatial Join (the core innovation)
Clustered both datasets independently using DBSCAN (haversine distance, 100m radius), then spatially joined every parking cluster to the nearest incident cluster within 200 metres. Computed a **Compound Risk Score (CRS)** for every resulting zone from four real, weighted signals: vehicle type, violation severity, recidivism factor, and incident/road-closure rate.

- 529 chronic parking hotspots clustered
- 114 recurring incident clusters identified
- **45 compound gridlock zones** found — joint evidence of parking + incidents at the same location
- 16,386 violations and 1,165 incidents fall within these 45 zones

### Phase 3 — AmbulanceShield (life-safety layer)
Mapped 8 major Bangalore hospitals and computed each zone's proximity to the nearest one. Zones within 1km of a hospital get a 3× priority multiplier, within 2km get 2×, beyond that 1× — meaning ambulance proximity can override raw risk ranking entirely. Also flagged all currently-active, road-closing incidents as live critical alerts.

- 32 of 45 zones were re-ranked once ambulance proximity was applied
- 100 critical ambulance alerts identified from real active/road-closure incidents

### Phase 4 — Incident Duration Predictor (BreakdownBlind)
Trained a gradient-boosted regression model to estimate how much longer an active incident will likely block traffic, using event cause, vehicle type, corridor, road-closure flag, priority, hour, and weekday as features.

- Trained on 1,885 incidents with known duration
- Validated signal: road closures average 409 min vs 274 min without; BMTC bus breakdowns average 61 min vs 42 min for private cars
- **Honest limitation:** incident duration has a heavy long tail (90th percentile = 871 min vs median 62 min). With ~1,900 training rows, the model is used for *relative ranking* (which zones tend to clear slower), not precise minute-level forecasting. The core risk score does not depend on it.

### Phase 5 — Dashboard + Live Demo
A FastAPI backend serves 4 endpoints (zones, alerts, dispatch queue, Flipkart routing) consumed by a React + Leaflet dashboard. A replay script feeds the Astram dataset chronologically into the API to simulate a live traffic feed for demo purposes.

- Interactive map with colour-coded risk zones (red/amber/green) and hospital markers
- Ranked enforcement dispatch queue, sorted by ambulance-weighted priority
- Analytics panel: top zones by CRS, violations by hour, incident cause breakdown
- **Flipkart routing panel:** compares a direct delivery route against a GridlockDNA-optimised route avoiding high-risk zones — in our test case (Peenya warehouse → Koramangala), the optimised route saves an estimated 28 minutes by avoiding 3 critical zones.

---

## Tech Stack

| Layer | Tools |
|---|---|
| Data processing | Python, pandas |
| Spatial clustering | scikit-learn (DBSCAN, haversine metric) |
| Spatial join | scipy (cKDTree) / geopandas |
| Predictive model | LightGBM |
| Backend | FastAPI |
| Frontend | React, Leaflet, Chart.js |

---

## Data

You can find the complete dataset zip file in /data.

---

# GridlockDNA — Phase 5 (Frontend) Setup Guide


This guide gets you from "notebook ran successfully" to "live dashboard demo."

---

## STEP 1 — Get the real files from your partner

The notebook *runs* the pipeline but the output files live wherever it executed
(Colab's `/content/`, or local disk). You need these 3 specific files — nothing else:

```
live_zone_status.json     ← the final output (Step 14) — 45 zones, this is the big one
ambulance_alerts.json     ← Step 11 output — 100 real critical incidents
hospitals.json            ← Step 9 output — 8 hospital coordinates
```

**From Google Colab:**
```python
from google.colab import files
files.download("live_zone_status.json")
files.download("ambulance_alerts.json")
files.download("hospitals.json")
```
Or just open the Colab file browser (folder icon, left sidebar) and right-click → Download on each.

**If local Jupyter:** they're already sitting in the same folder as the notebook — just copy them.

---

## STEP 2 — Place the files

Put all 3 files inside the `api/` folder, next to `main.py`:

```
gridlockdna/
├── api/
│   ├── main.py                  
│   ├── live_zone_status.json    ← PASTE HERE
│   ├── ambulance_alerts.json    ← PASTE HERE
│   └── hospitals.json           ← PASTE HERE
├── frontend/
│   └── index.html               
└── replay.py
```

---

## STEP 3 — Start the API

```bash
cd api
pip install fastapi uvicorn --break-system-packages
uvicorn main:app --reload --port 8000
```

You should see in the terminal:
```
✓ Loaded 45 zones, 100 ambulance alerts, 8 hospitals
```

If instead you see a `MISSING FILE` error, you skipped Step 2 — go back and check the filenames match exactly (case-sensitive).

Sanity check it's working — open in browser: `http://localhost:8000/health`
Should return:
```json
{"status":"ok","zones_loaded":45,"ambulance_alerts_loaded":100,"hospitals_loaded":8}
```

---

## STEP 4 — Open the dashboard

Just open `frontend/index.html` directly in Chrome (double-click it, or drag into browser).

No build step, no npm install. It auto-detects the API:
- **Green "Live" badge** top right → connected to your partner's real 45 zones
- **Amber "Fallback data" badge** → API isn't running, using realistic placeholder data shaped identically (so you can still rehearse the demo without the backend running)

---

## STEP 5 — Run the live replay for your demo

With the API running:
```bash
python replay.py
```

This pulls the **real 100 ambulance alerts** (sorted by hospital proximity — most urgent first) and fires one every 2.2 seconds into the dashboard. Each one pops a red marker on the map at its real lat/lon with the real `event_cause` and hospital distance.


---
