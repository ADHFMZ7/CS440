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
        
        # Initialize pigpio
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("Could not connect to pigpio daemon")

        # Set up pins
        self.pi.set_mode(self.clock_pin, pigpio.OUTPUT)
        self.pi.set_mode(self.data_pin, pigpio.OUTPUT)  # Start in OUTPUT mode
        
        # Initialize pins to LOW
        self.pi.write(self.clock_pin, 0)
        self.pi.write(self.data_pin, 0)

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
        # Ensure we're in OUTPUT mode
        self.pi.set_mode(self.data_pin, pigpio.OUTPUT)
        time.sleep(0.001)  # Small delay for mode switch
        
        # Send each bit
        for i in range(7, -1, -1):
            bit = (byte >> i) & 1
            self.send_bit(bit)
        
        # Switch to INPUT mode to receive acknowledgment
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

    def send_request(self, request: Request) -> Response:
        """Send a request to the server and wait for response"""
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
        
        # Send length first (2 bytes)
        length = len(request_bytes)
        self.send_byte((length >> 8) & 0xFF)  # High byte
        self.send_byte(length & 0xFF)         # Low byte
        
        # Send request data
        for byte in request_bytes:
            self.send_byte(byte)

        # Receive response
        return self.receive_response()

    def receive_response(self) -> Response:
        """Receive a response from the server"""
        # Read length (2 bytes)
        length_high = self.receive_byte()
        length_low = self.receive_byte()
        length = (length_high << 8) | length_low
        
        # Read response data
        data = bytearray()
        for _ in range(length):
            data.append(self.receive_byte())
        
        # Parse response
        response_data = json.loads(data.decode())
        return Response(
            status=response_data['status'],
            headers=response_data['headers'],
            body=bytes.fromhex(response_data['body']) if response_data['body'] else b''
        )

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