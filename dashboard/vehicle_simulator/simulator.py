import json
import random
import asyncio
import websockets
from datetime import datetime
import aiohttp  # for sending HTTP requests

WS_URL = "ws://localhost:8001/ws/vehicle_data/"
DRIVER_URL = "https://vahan-rakshak-dbw4.onrender.com/v1/driver/monitoring"
SPEED_URL = "https://vahan-rakshak-dbw4.onrender.com/v1/speed"

class VehicleSimulator:
    def __init__(self, vehicle_id="VEH001"):
        self.vehicle_id = vehicle_id
        self.speed = 60
        self.eye_closure = 30
        self.yawning_rate = 2
        self.blink_duration = 200  # milliseconds
        self.is_running = False

    def generate_driver_data(self):
        self.eye_closure = min(100, self.eye_closure + random.uniform(-5, 8))
        self.yawning_rate = min(10, max(0, self.yawning_rate + random.uniform(-0.5, 1)))
        self.blink_duration = min(500, max(100, self.blink_duration + random.uniform(-20, 30)))

        return {
            "vehicle_id": self.vehicle_id,
            "eye_closure_pct": round(self.eye_closure, 2),
            "blink_duration_ms": round(self.blink_duration),
            "yawning_rate_per_min": round(self.yawning_rate, 2),
            "steering_variability": round(random.uniform(0, 1), 2),
            "lane_departures": random.randint(0, 2) if random.random() < 0.1 else 0,
            "timestamp": datetime.now().isoformat()
        }

    def generate_speed_data(self):
        speed_change = random.uniform(-5, 5)
        self.speed = min(120, max(0, self.speed + speed_change))

        return {
            "vehicle_id": self.vehicle_id,
            "current_speed_kmh": round(self.speed, 1),
            "speed_limit_kmh": 80,
            "timestamp": datetime.now().isoformat()
        }

    async def send_data_to_websocket(self, websocket, data):
        try:
            message = json.dumps(data)
            await websocket.send(message)
            return True
        except websockets.exceptions.ConnectionClosed:
            print(f"[{datetime.now().isoformat()}] WebSocket closed, reconnecting...")
            return False
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] WebSocket error: {str(e)}")
            return False

    async def send_data_to_backend(self, url, data):
        """Send data to backend using HTTP POST and print response"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=data) as resp:
                    try:
                        resp_data = await resp.json()  # Try parsing JSON response
                    except Exception:
                        resp_data = await resp.text()  # Fallback to plain text

                    if resp.status in [200, 201]:
                        print(f"[{datetime.now().isoformat()}] Successfully sent to {url}")
                        print(f"Response: {resp_data}")
                    else:
                        print(f"[{datetime.now().isoformat()}] Backend response {resp.status} for {url}")
                        print(f"Response: {resp_data}")
            except Exception as e:
                print(f"[{datetime.now().isoformat()}] Error sending to backend {url}: {str(e)}")

    async def start_simulation(self):
        self.is_running = True
        consecutive_failures = 0

        while True:
            try:
                async with websockets.connect(WS_URL) as websocket:
                    print(f"[{datetime.now().isoformat()}] Connected to WebSocket at {WS_URL}")

                    while self.is_running:
                        try:
                            # Generate data
                            driver_data = self.generate_driver_data()
                            speed_data = self.generate_speed_data()

                            # Send to WebSocket
                            driver_ws_success = await self.send_data_to_websocket(websocket, {
                                "type": "driver_data",
                                "data": driver_data
                            })
                            speed_ws_success = await self.send_data_to_websocket(websocket, {
                                "type": "speed_data",
                                "data": speed_data
                            })

                            # Send to backend asynchronously
                            await asyncio.gather(
                                self.send_data_to_backend(DRIVER_URL, driver_data),
                                self.send_data_to_backend(SPEED_URL, speed_data)
                            )

                            if driver_ws_success and speed_ws_success:
                                consecutive_failures = 0
                                print(f"[{datetime.now().isoformat()}] Successfully sent data to WebSocket and backend")
                            else:
                                consecutive_failures += 1
                                print(f"[{datetime.now().isoformat()}] Failed to send data {consecutive_failures} times")
                                if consecutive_failures >= 5:
                                    print(f"[{datetime.now().isoformat()}] Too many failures. Waiting 30 seconds...")
                                    await asyncio.sleep(30)
                                    consecutive_failures = 0

                            # Wait 5 seconds before next send
                            await asyncio.sleep(5)

                        except Exception as e:
                            print(f"[{datetime.now().isoformat()}] Simulation loop error: {str(e)}")
                            await asyncio.sleep(5)

            except Exception as e:
                print(f"[{datetime.now().isoformat()}] WebSocket connection error: {str(e)}. Retrying in 5 seconds...")
                await asyncio.sleep(5)

    def stop_simulation(self):
        self.is_running = False

async def main():
    simulator = VehicleSimulator("VEH001")
    print("Starting vehicle simulation. Press Ctrl+C to stop.")
    try:
        await simulator.start_simulation()
    except KeyboardInterrupt:
        print("\nStopping simulation...")
        simulator.stop_simulation()

if __name__ == "__main__":
    asyncio.run(main())
