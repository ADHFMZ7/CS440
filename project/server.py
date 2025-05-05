import pigpio
import time
import sys
import json
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class Request:
    method: str
    path: str
    headers: Dict[str, str]
    body: bytes = b''

@dataclass
class Response:
    status: int
    headers: Dict[str, str]
    body: bytes

class GPIOServer:
    def __init__(self, data_pin=23, clock_pin=24):
        self.data_pin = data_pin
        self.clock_pin = clock_pin
        self.latch_pin = 25
        
        # Initialize pigpio
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("Could not connect to pigpio daemon")

        # Set up pins
        self.pi.set_mode(self.clock_pin, pigpio.OUTPUT)
        self.pi.set_mode(self.data_pin, pigpio.OUTPUT)
        self.pi.set_mode(self.latch_pin, pigpio.OUTPUT)
        
        # Initialize all pins to LOW
        self.pi.write(self.clock_pin, 0)
        self.pi.write(self.data_pin, 0)
        self.pi.write(self.latch_pin, 0)

        # Simple in-memory storage
        self.storage = {}

    def send_byte(self, byte):
        # Ensure data line is LOW before starting
        self.pi.write(self.data_pin, 0)
        self.pi.write(self.clock_pin, 0)
        time.sleep(0.001)

        for ix in range(7, -1, -1):
            bit = 1 if (byte >> ix) & 1 else 0
            self.pi.write(self.data_pin, bit)
            time.sleep(0.001)

            self.pi.write(self.clock_pin, 1)
            time.sleep(0.001)
            self.pi.write(self.clock_pin, 0)
            time.sleep(0.001)

        self.pi.write(self.data_pin, 0)
        time.sleep(0.001)

        self.pi.write(self.latch_pin, 1)
        time.sleep(0.001)
        self.pi.write(self.latch_pin, 0)
        time.sleep(0.001)

    def send_response(self, response: Response):
        # Convert response to bytes
        response_data = {
            'status': response.status,
            'headers': response.headers,
            'body': response.body.hex()  # Convert bytes to hex string for JSON
        }
        response_bytes = json.dumps(response_data).encode() + b'\n'
        
        # Send length first
        length = len(response_bytes)
        self.send_byte((length >> 8) & 0xFF)  # High byte
        self.send_byte(length & 0xFF)         # Low byte
        
        # Send response
        for byte in response_bytes:
            self.send_byte(byte)

    def handle_request(self, request: Request) -> Response:
        if request.method == "GET":
            if request.path == "/":
                return Response(200, {"Content-Type": "text/plain"}, b"GPIO Server is running!")
            elif request.path.startswith("/data/"):
                key = request.path[6:]  # Remove "/data/" prefix
                if key in self.storage:
                    return Response(200, {"Content-Type": "application/json"}, 
                                  json.dumps(self.storage[key]).encode())
                return Response(404, {}, b"Not Found")
            return Response(404, {}, b"Not Found")
            
        elif request.method == "POST":
            if request.path.startswith("/data/"):
                key = request.path[6:]  # Remove "/data/" prefix
                try:
                    data = json.loads(request.body)
                    self.storage[key] = data
                    return Response(200, {}, b"OK")
                except:
                    return Response(400, {}, b"Invalid JSON")
            return Response(404, {}, b"Not Found")
            
        return Response(405, {}, b"Method Not Allowed")

    def cleanup(self):
        self.pi.stop()

def main():
    server = GPIOServer()
    print("GPIO Server started. Press Ctrl-C to stop.")
    
    try:
        while True:
            # In a real implementation, we would receive requests here
            # For now, we'll just keep the server running
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        server.cleanup()

if __name__ == "__main__":
    main() 