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
        self.pi.set_mode(self.data_pin, pigpio.OUTPUT)  # Start in OUTPUT mode
        self.pi.set_mode(self.latch_pin, pigpio.OUTPUT)
        
        # Initialize all pins to LOW
        self.pi.write(self.clock_pin, 0)
        self.pi.write(self.data_pin, 0)
        self.pi.write(self.latch_pin, 0)

    def wait_for_clock_high(self):
        """Wait for clock to go high, indicating start of transmission"""
        print("Client waiting for clock high...")
        while self.pi.read(self.clock_pin) == 0:
            time.sleep(0.001)
        print("Client detected clock high")

    def wait_for_clock_low(self):
        """Wait for clock to go low"""
        print("Client waiting for clock low...")
        while self.pi.read(self.clock_pin) == 1:
            time.sleep(0.001)
        print("Client detected clock low")

    def receive_byte(self):
        """Receive a byte from the server"""
        print("Client receiving byte...")
        # Switch to INPUT mode
        self.pi.set_mode(self.data_pin, pigpio.INPUT)
        
        # Wait for start of transmission
        self.wait_for_clock_high()
        
        byte = 0
        for i in range(8):
            # Wait for clock to go low
            self.wait_for_clock_low()
            
            # Read data bit
            bit = self.pi.read(self.data_pin)
            byte = (byte << 1) | bit
            print(f"Client received bit {i}: {bit}")
            
            # Wait for clock to go high
            self.wait_for_clock_high()
        
        # Switch back to OUTPUT mode
        self.pi.set_mode(self.data_pin, pigpio.OUTPUT)
        print(f"Client received byte: {byte}")
        return byte

    def send_byte(self, byte):
        """Send a byte to the server"""
        print(f"Client sending byte: {byte}")
        # Ensure we're in OUTPUT mode
        self.pi.set_mode(self.data_pin, pigpio.OUTPUT)
        
        # Ensure data line is LOW before starting
        self.pi.write(self.data_pin, 0)
        self.pi.write(self.clock_pin, 0)
        time.sleep(0.001)

        for ix in range(7, -1, -1):
            bit = 1 if (byte >> ix) & 1 else 0
            self.pi.write(self.data_pin, bit)
            print(f"Client sending bit {7-ix}: {bit}")
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
        print("Client finished sending byte")

    def receive_response(self) -> Response:
        """Receive a response from the server"""
        print("Client receiving response...")
        # Read length (2 bytes)
        length_high = self.receive_byte()
        length_low = self.receive_byte()
        length = (length_high << 8) | length_low
        print(f"Client received response length: {length}")
        
        # Read response data
        data = bytearray()
        for i in range(length):
            data.append(self.receive_byte())
            print(f"Client received byte {i+1}/{length}")
        
        # Parse response
        response_data = json.loads(data.decode())
        print("Client parsed response data")
        return Response(
            status=response_data['status'],
            headers=response_data['headers'],
            body=bytes.fromhex(response_data['body']) if response_data['body'] else b''
        )

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
        
        # Send length first
        length = len(request_bytes)
        print(f"Client sending request length: {length}")
        self.send_byte((length >> 8) & 0xFF)  # High byte
        self.send_byte(length & 0xFF)         # Low byte
        
        # Send request
        for i, byte in enumerate(request_bytes):
            print(f"Client sending request byte {i+1}/{len(request_bytes)}")
            self.send_byte(byte)

        print("Client finished sending request, waiting for response...")
        # Receive response
        return self.receive_response()

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