import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from datetime import datetime

class VehicleDataConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handle WebSocket connection"""
        self.ping_task = None
        self.connected = True
        try:
            await self.channel_layer.group_add("vehicle_data", self.channel_name)
            await self.accept()
            print(f"WebSocket client connected at {datetime.now().isoformat()}")
            
            # Start ping/pong mechanism
            self.ping_task = asyncio.create_task(self.ping_loop())
            
            # Send initial connection success message
            await self.send(text_data=json.dumps({
                "type": "connection_established",
                "message": "Connected successfully",
                "timestamp": datetime.now().isoformat()
            }))
        except Exception as e:
            print(f"Connection error: {str(e)}")
            self.connected = False
            raise

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        self.connected = False
        if self.ping_task:
            self.ping_task.cancel()
            try:
                await self.ping_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"Error canceling ping task: {str(e)}")
        
        try:
            await self.channel_layer.group_discard("vehicle_data", self.channel_name)
        except Exception as e:
            print(f"Error removing from group: {str(e)}")
        
        print(f"WebSocket client disconnected with code: {close_code}")
        print(f"Channel name at disconnect: {self.channel_name}")
        print(f"Disconnect time: {datetime.now().isoformat()}")
        
        if close_code in [1011, 1006]:
            print("Connection error detected. Please check server logs for details.")

    async def receive(self, text_data=None, bytes_data=None):
        """Handle incoming WebSocket messages"""
        try:
            if not text_data:
                return

            message = json.loads(text_data)
            print(f"Received message: {message}")

            # Add timestamp if not present
            if 'data' in message and 'timestamp' not in message['data']:
                message['data']['timestamp'] = datetime.now().isoformat()

            # Handle different message types
            message_type = message.get('type')
            if message_type == 'pong':
                if hasattr(self, 'pong_received') and self.pong_received:
                    self.pong_received.set()
                return

            # Broadcast the message to all connected clients
            await self.channel_layer.group_send(
                "vehicle_data",
                {
                    "type": "broadcast_data",
                    "event_data": message
                }
            )
        except json.JSONDecodeError as e:
            error_msg = f"JSON decode error: {str(e)}"
            print(error_msg)
            await self.send(text_data=json.dumps({"error": error_msg}))
        except Exception as e:
            error_msg = f"Error in receive: {str(e)}"
            print(error_msg)
            if self.connected:
                await self.send(text_data=json.dumps({"error": error_msg}))

    async def ping_loop(self):
        """Send periodic pings to keep the connection alive"""
        ping_interval = 30  # Reduced from 30 to 15 seconds
        ping_timeout = 20   # Wait 10 seconds for pong response
        while self.connected:
            try:
                await asyncio.sleep(ping_interval)
                if not self.connected:
                    break
                    
                # Send ping as a text message
                await self.send(text_data=json.dumps({
                    "type": "ping",
                    "timestamp": datetime.now().isoformat()
                }))
                
                # Wait for pong with timeout
                try:
                    pong_received = asyncio.Event()
                    self.pong_received = pong_received
                    await asyncio.wait_for(pong_received.wait(), timeout=ping_timeout)
                except asyncio.TimeoutError:
                    print(f"Ping timeout at {datetime.now().isoformat()}")
                    await self.close(code=1000)  # Normal closure
                    break
                
            except Exception as e:
                print(f"Ping error: {str(e)}")
                if self.connected:
                    await self.close(code=1000)  # Normal closure
                break

import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from datetime import datetime

class VehicleDataConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handle WebSocket connection"""
        self.ping_task = None
        self.connected = True
        try:
            await self.channel_layer.group_add("vehicle_data", self.channel_name)
            await self.accept()
            print(f"WebSocket client connected at {datetime.now().isoformat()}")
            
            # Start ping/pong mechanism
            self.ping_task = asyncio.create_task(self.ping_loop())
            
            # Send initial connection success message
            await self.send(text_data=json.dumps({
                "type": "connection_established",
                "message": "Connected successfully",
                "timestamp": datetime.now().isoformat()
            }))
        except Exception as e:
            print(f"Connection error: {str(e)}")
            self.connected = False
            raise

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        self.connected = False
        if self.ping_task:
            self.ping_task.cancel()
            try:
                await self.ping_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"Error canceling ping task: {str(e)}")
        
        try:
            await self.channel_layer.group_discard("vehicle_data", self.channel_name)
        except Exception as e:
            print(f"Error removing from group: {str(e)}")
        
        print(f"WebSocket client disconnected with code: {close_code}")
        print(f"Channel name at disconnect: {self.channel_name}")
        print(f"Disconnect time: {datetime.now().isoformat()}")
        
        if close_code in [1011, 1006]:
            print("Connection error detected. Please check server logs for details.")

    async def receive(self, text_data=None, bytes_data=None):
        """Handle incoming WebSocket messages"""
        try:
            if not text_data:
                return

            message = json.loads(text_data)
            print(f"Received message: {message}")

            # Add timestamp if not present
            if 'data' in message and 'timestamp' not in message['data']:
                message['data']['timestamp'] = datetime.now().isoformat()

            # Handle different message types
            message_type = message.get('type')
            if message_type == 'pong':
                if hasattr(self, 'pong_received') and self.pong_received:
                    self.pong_received.set()
                return

            # Broadcast the message to all connected clients
            await self.channel_layer.group_send(
                "vehicle_data",
                {
                    "type": "broadcast_data",
                    "event_data": message
                }
            )
        except json.JSONDecodeError as e:
            error_msg = f"JSON decode error: {str(e)}"
            print(error_msg)
            await self.send(text_data=json.dumps({"error": error_msg}))
        except Exception as e:
            error_msg = f"Error in receive: {str(e)}"
            print(error_msg)
            if self.connected:
                await self.send(text_data=json.dumps({"error": error_msg}))

    async def ping_loop(self):
        ping_interval = 30  # seconds
        ping_timeout = 20   # seconds
        while self.connected:
            try:
                await asyncio.sleep(ping_interval)
                if not self.connected:
                    break

                await self.send(text_data=json.dumps({
                    "type": "ping",
                    "timestamp": datetime.now().isoformat()
                }))

                try:
                    pong_received = asyncio.Event()
                    self.pong_received = pong_received
                    await asyncio.wait_for(pong_received.wait(), timeout=ping_timeout)
                except asyncio.TimeoutError:
                    print(f"Ping timeout at {datetime.now().isoformat()}")
                    break

            except Exception as e:
                print(f"Ping error: {str(e)}")
                break


    async def broadcast_data(self, event):
        """Handle broadcasting messages to WebSocket clients"""
        try:
            # Get the message from event_data
            message = event.get('event_data')
            if not message:
                print(f"Warning: No event_data in event: {event}")
                return

            # Send the message to the WebSocket
            await self.send(text_data=json.dumps(message))
            print(f"Successfully broadcasted message type: {message.get('type', 'unknown')}")
        except Exception as e:
            print(f"Error in broadcast_data: {str(e)}")
            print(f"Event data: {event}")