# Store Intelligence System — Run Instructions

This guide provides step-by-step instructions on how to run the Store Intelligence System, including both the computer vision pipeline and the web applications (FastAPI backend and Streamlit dashboard).

---

## 1. Setup & Environment

### General Setup
Activate your Python environment and install the dependencies:

```bash
# Install dependencies
pip install -r requirements.txt
```

### System-Specific Python Path (For this machine)
If running on the local system where Python is installed in a custom location, use the full path:
*   **Python Executable**: `D:\Application\python\python.exe`

---

## 2. Running the CV Processing Pipeline

To run the pipeline stages manually, execute the following commands in the root directory:

### Phase 1: Person Detection (YOLOv8)
Extracts person bounding boxes from a video feed.
```bash
# General
python store_intelligence/detection.py --source "store_intelligence/CAM 1.mp4" --save --output "store_intelligence/CAM1_output.mp4" --preview

# Local System
D:\Application\python\python.exe store_intelligence/detection.py --source "store_intelligence/CAM 1.mp4" --save --output "store_intelligence/CAM1_output.mp4" --preview
```

### Phase 2: Multi-Object Tracking (ByteTrack)
Generates persistent trajectories for detected individuals.
```bash
# General
python store_intelligence/tracking.py --source "store_intelligence/CAM 3.mp4" --output "store_intelligence/tracked_output.mp4" --tracks-file "store_intelligence/tracks.json"

# Local System
D:\Application\python\python.exe store_intelligence/tracking.py --source "store_intelligence/CAM 3.mp4" --output "store_intelligence/tracked_output.mp4" --tracks-file "store_intelligence/tracks.json"
```

### Phase 3: Doorway Event Processing (Line Crossing FSM)
Processes track trails to register entries and exits at virtual thresholds.
```bash
# General
python store_intelligence/events.py --tracks "store_intelligence/tracks.json" --events-file "store_intelligence/events.json" --summary-file "store_intelligence/event_summary.json" --line-y 750

# Local System
D:\Application\python\python.exe store_intelligence/events.py --tracks "store_intelligence/tracks.json" --events-file "store_intelligence/events.json" --summary-file "store_intelligence/event_summary.json" --line-y 750
```

### Phase 4: Visitor Flow Analytics
Aggregates event logs to calculate store stay durations and timelines.
```bash
# General
python store_intelligence/analytics.py --tracks "store_intelligence/tracks.json" --events "store_intelligence/events.json" --summary "store_intelligence/event_summary.json" --output "store_intelligence/analytics.json"

# Local System
D:\Application\python\python.exe store_intelligence/analytics.py --tracks "store_intelligence/tracks.json" --events "store_intelligence/events.json" --summary "store_intelligence/event_summary.json" --output "store_intelligence/analytics.json"
```

### Phase 5: Anomaly Detection Engine
Evaluates tracks and metrics for loitering, crowding, and traffic spikes using the Strategy pattern.
```bash
# General
python store_intelligence/anomaly_detection.py --tracks "store_intelligence/tracks.json" --events "store_intelligence/events.json" --analytics "store_intelligence/analytics.json" --db "store_intelligence/anomalies.db" --output "store_intelligence/anomalies.json"

# Local System
D:\Application\python\python.exe store_intelligence/anomaly_detection.py --tracks "store_intelligence/tracks.json" --events "store_intelligence/events.json" --analytics "store_intelligence/analytics.json" --db "store_intelligence/anomalies.db" --output "store_intelligence/anomalies.json"
```

### Phase 6: Conversion Funnel Calculator
Computes store stage conversions (Passersby ➔ Entered ➔ Browsed ➔ Checked out).
```bash
# General
python store_intelligence/funnel.py --tracks "store_intelligence/tracks.json" --events "store_intelligence/events.json" --output "store_intelligence/funnel.json"

# Local System
D:\Application\python\python.exe store_intelligence/funnel.py --tracks "store_intelligence/tracks.json" --events "store_intelligence/events.json" --output "store_intelligence/funnel.json"
```

---

## 3. Running the Dashboard Application

The application consists of a FastAPI backend and a Streamlit frontend. For best results, run both simultaneously.

### Step 1: Start FastAPI REST Server
The backend handles database migrations, REST endpoints, and log syncing.
```bash
# General
uvicorn app.api:app --reload --port 8000

# Local System (Uses Python module mode)
D:\Application\python\python.exe -m uvicorn app.api:app --port 8000
```
*   **API Documentation**: Access interactive Swagger docs at `http://127.0.0.1:8000/docs` or ReDoc at `http://127.0.0.1:8000/redoc`.

### Step 2: Start Streamlit Dashboard
The executive dashboard displays live KPIs, alerts feed, interactive tables, and metrics graphs.
```bash
# General
streamlit run dashboard/app.py

# Local System (Uses Python module mode)
D:\Application\python\python.exe -m streamlit run dashboard/app.py
```
*   **Web Access**: Open `http://localhost:8501` in your browser.
*   **Robust Fallback**: If the FastAPI server is not running, the dashboard automatically enters *Offline Fallback Mode*, reading statistics directly from local files (`anomalies.db`, `analytics.json`, `events.json`).
