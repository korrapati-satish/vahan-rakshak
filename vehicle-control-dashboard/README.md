
# 🚗 Real-Time Vehicle Monitoring Dashboard

This project simulates **real-time vehicle data** and **safety monitoring** using **Python**, **Django Channels (WebSockets)**, and **FastAPI**.  
It provides a dashboard that visualizes **driver behavior**, **vehicle speed**, and **emergency incidents** such as fire, water submersion, and collisions.

---

## ✨ Features

### 👁️ Driver Alertness Monitoring
- PERCLOS (eye closure %)
- Blink duration
- Yawning rate

### 🚦 Vehicle Speed Visualization
- Live tracking of vehicle speed vs speed limits
- Visual gauges and line charts

### 🆘 Emergency Incident Detection
- 🔥 Fire detection: cabin & battery temperature, fire confidence %
- 🌊 Water submersion: water level, flood risk
- 💥 Collision impact: G-force, severity

### 🔗 Unified API Endpoint
- All metrics and incidents are reported via **`POST /v1/vehicle/update`**

### 📡 Live Data Visualization
- WebSocket-powered frontend updates in real-time

### 🟥🟩 Dynamic Incident Alerts
- 🟩 Green: Normal status  
- 🟥 Red: Incident detected (fire, collision, flood)

---

## 🔌 Backend API Endpoint

**Endpoint:**  
```
POST /v1/vehicle/update
```

**Example Payload:**

```json
{
  "vehicle_id": "VEH001",
  "driver_alertness": {
    "eye_closure_pct": 24.5,
    "blink_duration_ms": 180,
    "yawning_rate_per_min": 2.3
  },
  "speed_data": {
    "current_speed_kmh": 52.3,
    "speed_limit_kmh": 80
  },
  "fire_status": {
    "cabin_temp_celsius": 60.2,
    "battery_temp_celsius": 55.8,
    "fire_confidence_pct": 78.5
  },
  "water_status": {
    "water_level_cm": 12.4,
    "flood_risk": "Medium"
  },
  "collision_data": {
    "g_force": 4.5,
    "severity": "High"
  }
}
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Pip
- Modern web browser (Chrome, Firefox) with WebSocket support

### Installation
```bash
pip install -r requirements.txt
```

### Running the Services
Use **four terminal windows**:

1️⃣ **Django WebSocket Server (Port 8001)**  
```bash
cd dashboard
daphne -p 8001 vehicle_simulator.asgi:application
```

2️⃣ **Django Web Admin (Port 8000)**  
```bash
cd dashboard
python manage.py runserver 0.0.0.0:8000
```

3️⃣ **FastAPI Backend (Port 8080)**  
```bash
uvicorn src.api.server:app --host 0.0.0.0 --port 8080
```

4️⃣ **Vehicle Simulator**  
```bash
python dashboard/vehicle_simulator/simulator.py
```

---

## 🖥️ Open the Dashboard

Open `index.html` in your browser.  
Live data will stream in real-time from the simulator and backend.

---

## 🧩 Tech Stack

- Backend: Python, FastAPI, Django, Django Channels, Daphne
- Frontend: HTML, JavaScript, WebSockets
- Simulator: Python script for continuous real time data

