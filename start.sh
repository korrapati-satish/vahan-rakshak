#!/bin/bash
# start.sh: Start Django, simulator, Daphne, and FastAPI concurrently

echo "Starting Django server on port 8000..."
python manage.py runserver 0.0.0.0:8000 &

echo "Starting Vehicle Simulator..."
python vehicle_simulator/simulator.py &

echo "Starting Daphne ASGI server on port 8001..."
daphne -p 8001 vehicle_simulator.asgi:application &

echo "Starting FastAPI app on port 8080..."
uvicorn src.api.server:app --host 0.0.0.0 --port 8080 &

# Wait for all processes to exit
wait
