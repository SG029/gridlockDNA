# GridlockDNA — Phase 5 (Frontend) Setup Guide

Your partner's notebook (`ParkSenseAI.ipynb`) is fully complete through Step 14.
It produces real results: **45 compound zones**, **100 ambulance alerts**, **8 hospitals**.

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

**If your partner used Google Colab:**
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
│   ├── main.py                  ← already written for you
│   ├── live_zone_status.json    ← PASTE HERE
│   ├── ambulance_alerts.json    ← PASTE HERE
│   └── hospitals.json           ← PASTE HERE
├── frontend/
│   └── index.html               ← already written for you
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

Want fewer/more events? `python replay.py 25` replays the top 25 instead of the default 15.

---

## What's different from the original mock version

| Thing | Mock v1 | Real v2 (this one) |
|---|---|---|
| Zone count | 10 fake | **45 real** compound zones |
| Field names | `final_priority` | `final_priority_score` (mapped internally) |
| Ambulance alerts | 10 invented | **100 real** Astram incidents |
| Severity | manually assigned | derived from real `final_priority_score` (≥80 critical, ≥40 high) |
| Duration prediction | not present | **real LightGBM output** (`predicted_remaining_block_min`) — with the honest caveat that val MAE is ~286 min, so treat it as relative signal not precise minutes |
| Filter by severity | not present | **added** — filter chips in dispatch panel |
| Hospital count on chart | not present | **added** — "zones by nearest hospital" bar chart |

---

## Honest numbers to use in your demo / slides

Pull these straight from the notebook output — don't round up or embellish:

- **248,376** clean parking violation rows (after removing rejected/duplicate)
- **6,639** clean Astram incident rows (after authenticated + duration cleanup)
- **529** parking violation clusters found via DBSCAN
- **114** incident clusters found via DBSCAN
- **45** compound zones where a parking cluster and incident cluster overlap within 200m
- **100** active road-closure incidents within hospital proximity (ambulance alerts)
- **32 of 45** zones had their enforcement rank *changed* by ambulance weighting vs raw CRS alone — this is your strongest one-liner, it proves the ambulance layer isn't decorative, it materially reprioritises enforcement
- Duration model: **val MAE = 286 min**, honestly reported. Say: *"the model is a relative signal — useful for ranking which zones are likely to stay blocked longer than others — not a precise minute-level guarantee, given roughly 1,900 training rows and a heavy-tailed duration distribution."*

That last point — leading with the honest limitation instead of waiting to get caught — is exactly the kind of thing that makes BTP engineers trust the rest of your numbers.

---

## 90-second demo script (updated for real data)

1. Open dashboard. Point to map: *"This is built from 248,000 real BTP parking violations and 6,600 real Astram incidents — not synthetic data."*
2. Click on the top-ranked zone (Cluster 0 or Cluster 206 — both ambulance-critical). Show the popup: violations, incidents, nearest hospital, distance.
3. Mention: *"32 of our 45 compounding zones had their priority order changed once we factored in hospital proximity — meaning a medium-risk zone near a hospital outranks a high-risk zone that isn't."*
4. Run `replay.py` — watch real ambulance alerts fire on the map in real time, sorted by proximity to hospitals.
5. Switch to Analytics tab — show the delay label distribution and the honest MAE callout.
6. Switch to Flipkart tab — Route A vs B comparison.

Done in under 90 seconds, entirely on real numbers.
