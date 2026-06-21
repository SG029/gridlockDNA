# GridlockDNA — Bangalore Traffic Intelligence System

GridlockDNA is a traffic intelligence platform that identifies spatial overlaps between chronic illegal parking and recurring traffic incidents in Bangalore. By clustering and intersecting city data, GridlockDNA powers three key applications: a real-time enforcement dispatch dashboard, an ambulance-priority safety layer, and a last-mile delivery routing optimizer.

---

## 🛣️ The Pipeline

The project operates as a 5-phase data and modeling pipeline:

1. **Phase 1: Data Preparation** — Cleans and parses parking violations and traffic incident records, generating IST timestamps and offender recidivism profiles.
2. **Phase 2: Spatial Join** — Clusters data independently via DBSCAN (haversine metric) and joins nearest parking and incident clusters within 200m to define **45 compound risk zones**.
3. **Phase 3: AmbulanceShield** — Integrates hospital coordinates and applies a priority multiplier (up to 3×) to zones within hospital corridors to ensure ambulance routes remain clear.
4. **Phase 4: Duration Predictor** — Trains a gradient-boosted regression model (LightGBM) to estimate remaining blockage times for active incidents based on cause, corridor, and vehicle type.
5. **Phase 5: Dashboard & Live Demo** — Serves a FastAPI backend with Leaflet visualization and Flipkart delivery route simulation.

---

## 🛠️ Setup & Run Instructions

### Prerequisites
- **Python**: v3.8 or higher
- **Browser**: Google Chrome, Microsoft Edge, or Mozilla Firefox
- **Dataset**: The raw source dataset is included at `data/jan to may police violation_anonymized791b166.zip`.

### 1. Dependency Installation
Open your terminal in the project root directory and install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Start the Backend API
1. Navigate to the API folder:
   ```bash
   cd api
   ```
2. Run the FastAPI server:
   ```bash
   python -m uvicorn main:app --port 8000
   ```
   *The server is active when `[OK] Loaded 45 zones, 100 ambulance alerts, 8 hospitals` is logged.*

### 3. Launch the Dashboard
Open your browser and navigate to:
👉 **[http://localhost:8000/](http://localhost:8000/)**

*Alternatively, you can open `frontennd/index.html` (note the spelling with two 'n's) directly in your browser, though running via the localhost URL is recommended to avoid CORS issues.*

### 4. Run the Live Replay Simulation
To feed chronological incidents into the live map and dispatch queue in real-time:
1. Open a new terminal in the project root folder.
2. Run the simulation script:
   ```bash
   python replay.py
   ```
