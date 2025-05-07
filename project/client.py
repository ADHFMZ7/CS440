import pigpio
import time
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

class GPIOClient:
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

    def send_request(self, request: Request) -> Response:
        print(f"\nSending request:")
        print(f"  Method: {request.method}")
        print(f"  Path: {request.path}")
        print(f"  Headers: {request.headers}")
        if request.body:
            try:
                body_str = request.body.decode()
                print(f"  Body: {body_str}")
            except:
                print(f"  Body: {request.body}")

        # Convert request to bytes
        request_data = {
            'method': request.method,
            'path': request.path,
            'headers': request.headers,
            'body': request.body.hex()  # Convert bytes to hex string for JSON
        }
        request_bytes = json.dumps(request_data).encode() + b'\n'
        
        # Send length first
        length = len(request_bytes)
        self.send_byte((length >> 8) & 0xFF)  # High byte
        self.send_byte(length & 0xFF)         # Low byte
        
        # Send request
        for byte in request_bytes:
            self.send_byte(byte)

        # TODO: In a real implementation, we would receive the response here
        # For now, we'll just return a dummy response
        return Response(200, {}, b"Response received")

    def cleanup(self):
        self.pi.stop()

def main():
    client = GPIOClient()
    print("GPIO Client started. Press Ctrl-C to stop.")
    
    try:
        while True:
            # Example: Send a GET request to the root path
            request = Request("GET", "/", {"Content-Type": "text/plain"})
            response = client.send_request(request)
            print(f"\nReceived response:")
            print(f"  Status: {response.status}")
            print(f"  Headers: {response.headers}")
            try:
                body_str = response.body.decode()
                print(f"  Body: {body_str}")
            except:
                print(f"  Body: {response.body}")
            time.sleep(2)

            # Example: Send a POST request to store data
            data = {"message": "Hello from client!"}
            request = Request("POST", "/data/test", 
                            {"Content-Type": "application/json"},
                            json.dumps(data).encode())
            response = client.send_request(request)
            print(f"\nReceived response:")
            print(f"  Status: {response.status}")
            print(f"  Headers: {response.headers}")
            try:
                body_str = response.body.decode()
                print(f"  Body: {body_str}")
            except:
                print(f"  Body: {response.body}")
            time.sleep(2)

            # Example: Send a GET request to retrieve the stored data
            request = Request("GET", "/data/test", {"Content-Type": "application/json"})
            response = client.send_request(request)
            print(f"\nReceived response:")
            print(f"  Status: {response.status}")
            print(f"  Headers: {response.headers}")
            try:
                body_str = response.body.decode()
                print(f"  Body: {body_str}")
            except:
                print(f"  Body: {response.body}")
            time.sleep(2)

    except KeyboardInterrupt:
        print("\nStopping client...")
    finally:
        client.cleanup()

if __name__ == "__main__":
    main() 