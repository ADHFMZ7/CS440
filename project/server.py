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

class GPIOServer:
    def __init__(self, data_pin=23, clock_pin=24):
        self.data_pin = data_pin
        self.clock_pin = clock_pin
        
        # Initialize pigpio
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("Could not connect to pigpio daemon")

        # Set up pins
        self.pi.set_mode(self.clock_pin, pigpio.OUTPUT)
        self.pi.set_mode(self.data_pin, pigpio.INPUT)  # Start in INPUT mode
        
        # Initialize pins to LOW
        self.pi.write(self.clock_pin, 0)

        # Simple in-memory storage
        self.storage = {}
        print("Server initialized and ready to receive requests")

    def send_bit(self, bit):
        """Send a single bit"""
        self.pi.write(self.data_pin, bit)
        time.sleep(0.001)  # Small delay for signal stability
        self.pi.write(self.clock_pin, 1)
        time.sleep(0.001)  # Small delay for signal stability
        self.pi.write(self.clock_pin, 0)
        time.sleep(0.001)  # Small delay for signal stability

    def receive_bit(self):
        """Receive a single bit"""
        # Wait for clock to go high
        while self.pi.read(self.clock_pin) == 0:
            time.sleep(0.001)
        
        # Read data bit
        bit = self.pi.read(self.data_pin)
        
        # Wait for clock to go low
        while self.pi.read(self.clock_pin) == 1:
            time.sleep(0.001)
        
        return bit

    def send_byte(self, byte):
        """Send a byte and wait for acknowledgment"""
        # Switch to OUTPUT mode
        self.pi.set_mode(self.data_pin, pigpio.OUTPUT)
        time.sleep(0.001)  # Small delay for mode switch
        
        # Send each bit
        for i in range(7, -1, -1):
            bit = (byte >> i) & 1
            self.send_bit(bit)
        
        # Switch back to INPUT mode
        self.pi.set_mode(self.data_pin, pigpio.INPUT)
        time.sleep(0.001)  # Small delay for mode switch
        
        # Wait for acknowledgment
        while self.pi.read(self.clock_pin) == 0:
            time.sleep(0.001)
        ack = self.pi.read(self.data_pin)
        while self.pi.read(self.clock_pin) == 1:
            time.sleep(0.001)
        
        if not ack:
            raise RuntimeError("No acknowledgment received")

    def receive_byte(self):
        """Receive a byte and send acknowledgment"""
        byte = 0
        for i in range(8):
            bit = self.receive_bit()
            byte = (byte << 1) | bit
        
        # Send acknowledgment bit
        self.pi.set_mode(self.data_pin, pigpio.OUTPUT)
        time.sleep(0.001)  # Small delay for mode switch
        self.send_bit(1)  # Send ACK (1)
        self.pi.set_mode(self.data_pin, pigpio.INPUT)
        time.sleep(0.001)  # Small delay for mode switch
        
        return byte

    def send_response(self, response: Response):
        """Send a response to the client"""
        # Convert response to bytes
        response_data = {
            'status': response.status,
            'headers': response.headers,
            'body': response.body.hex()  # Convert bytes to hex string for JSON
        }
        response_bytes = json.dumps(response_data).encode() + b'\n'
        
        # Send length first (2 bytes)
        length = len(response_bytes)
        self.send_byte((length >> 8) & 0xFF)  # High byte
        self.send_byte(length & 0xFF)         # Low byte
        
        # Send response data
        for byte in response_bytes:
            self.send_byte(byte)

    def receive_request(self) -> Request:
        """Receive a request from the client"""
        # Read length (2 bytes)
        length_high = self.receive_byte()
        length_low = self.receive_byte()
        length = (length_high << 8) | length_low
        
        # Read request data
        data = bytearray()
        for _ in range(length):
            data.append(self.receive_byte())
        
        # Parse request
        request_data = json.loads(data.decode())
        return Request(
            method=request_data['method'],
            path=request_data['path'],
            headers=request_data['headers'],
            body=bytes.fromhex(request_data['body']) if request_data.get('body') else b''
        )

    def handle_request(self, request: Request) -> Response:
        print(f"\nReceived request:")
        print(f"  Method: {request.method}")
        print(f"  Path: {request.path}")
        print(f"  Headers: {request.headers}")
        if request.body:
            try:
                body_str = request.body.decode()
                print(f"  Body: {body_str}")
            except:
                print(f"  Body: {request.body}")

        if request.method == "GET":
            if request.path == "/":
                response = Response(200, {"Content-Type": "text/plain"}, b"GPIO Server is running!")
            elif request.path.startswith("/data/"):
                key = request.path[6:]  # Remove "/data/" prefix
                if key in self.storage:
                    response = Response(200, {"Content-Type": "application/json"}, 
                                     json.dumps(self.storage[key]).encode())
                else:
                    response = Response(404, {}, b"Not Found")
            else:
                response = Response(404, {}, b"Not Found")
            
        elif request.method == "POST":
            if request.path.startswith("/data/"):
                key = request.path[6:]  # Remove "/data/" prefix
                try:
                    data = json.loads(request.body)
                    self.storage[key] = data
                    response = Response(200, {}, b"OK")
                except:
                    response = Response(400, {}, b"Invalid JSON")
            else:
                response = Response(404, {}, b"Not Found")
            
        else:
            response = Response(405, {}, b"Method Not Allowed")

        return response

    def cleanup(self):
        self.pi.stop()

def main():
    server = GPIOServer()
    print("GPIO Server started. Press Ctrl-C to stop.")
    
    try:
        while True:
            try:
                print("\nWaiting for request...")
                # Receive and handle request
                request = server.receive_request()
                response = server.handle_request(request)
                server.send_response(response)
            except Exception as e:
                print(f"Error handling request: {e}")
                time.sleep(0.1)  # Small delay to prevent CPU spinning on error
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        server.cleanup()

if __name__ == "__main__":
    main() 