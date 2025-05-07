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

    def send_start_sequence(self):
        """Send the start sequence (clock high, data high)"""
        print("Sending start sequence...")
        # Set both clock and data high
        self.pi.write(self.clock_pin, 1)
        self.pi.write(self.data_pin, 1)
        time.sleep(0.01)  # Wait for signal to stabilize
        
        # Set both back to low
        self.pi.write(self.clock_pin, 0)
        self.pi.write(self.data_pin, 0)
        time.sleep(0.01)  # Wait for signal to stabilize

    def wait_for_clock_high(self):
        """Wait for clock to go high, indicating start of transmission"""
        while self.pi.read(self.clock_pin) == 0:
            time.sleep(0.001)
        time.sleep(0.001)  # Small delay to ensure signal is stable

    def wait_for_clock_low(self):
        """Wait for clock to go low"""
        while self.pi.read(self.clock_pin) == 1:
            time.sleep(0.001)
        time.sleep(0.001)  # Small delay to ensure signal is stable

    def receive_byte(self):
        """Receive a byte from the server"""
        # Switch to INPUT mode
        self.pi.set_mode(self.data_pin, pigpio.INPUT)
        time.sleep(0.01)  # Added delay after mode switch
        
        # Wait for start of transmission
        self.wait_for_clock_high()
        
        byte = 0
        for i in range(8):
            # Wait for clock to go low
            self.wait_for_clock_low()
            
            # Read data bit
            bit = self.pi.read(self.data_pin)
            byte = (byte << 1) | bit
            
            # Wait for clock to go high
            self.wait_for_clock_high()
        
        # Switch back to OUTPUT mode
        self.pi.set_mode(self.data_pin, pigpio.OUTPUT)
        time.sleep(0.01)  # Added delay after mode switch
        return byte

    def send_byte(self, byte):
        """Send a byte to the server"""
        # Ensure we're in OUTPUT mode
        self.pi.set_mode(self.data_pin, pigpio.OUTPUT)
        time.sleep(0.01)  # Added delay after mode switch
        
        # Ensure data line is LOW before starting
        self.pi.write(self.data_pin, 0)
        self.pi.write(self.clock_pin, 0)
        time.sleep(0.01)  # Increased delay

        for ix in range(7, -1, -1):
            bit = 1 if (byte >> ix) & 1 else 0
            self.pi.write(self.data_pin, bit)
            time.sleep(0.01)  # Increased delay

            self.pi.write(self.clock_pin, 1)
            time.sleep(0.01)  # Increased delay
            self.pi.write(self.clock_pin, 0)
            time.sleep(0.01)  # Increased delay

        self.pi.write(self.data_pin, 0)
        time.sleep(0.01)  # Increased delay

        self.pi.write(self.latch_pin, 1)
        time.sleep(0.01)  # Increased delay
        self.pi.write(self.latch_pin, 0)
        time.sleep(0.01)  # Increased delay

    def receive_response(self) -> Response:
        """Receive a response from the server"""
        # Read length (2 bytes)
        length_high = self.receive_byte()
        time.sleep(0.05)  # Added delay between bytes
        length_low = self.receive_byte()
        length = (length_high << 8) | length_low
        
        # Read response data
        data = bytearray()
        for i in range(length):
            data.append(self.receive_byte())
            time.sleep(0.05)  # Added delay between bytes
        
        # Parse response
        response_data = json.loads(data.decode())
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

        try:
            # Convert request to bytes
            request_data = {
                'method': request.method,
                'path': request.path,
                'headers': request.headers,
                'body': request.body.hex()  # Convert bytes to hex string for JSON
            }
            request_bytes = json.dumps(request_data).encode() + b'\n'
            
            # Validate request size
            if len(request_bytes) > 4096:  # 4KB max request size
                raise ValueError(f"Request too large: {len(request_bytes)} bytes")
            
            print(f"Sending request of length: {len(request_bytes)} bytes")
            
            # Send start sequence
            self.send_start_sequence()
            time.sleep(0.05)  # Wait after start sequence
            
            # Send length first
            length = len(request_bytes)
            self.send_byte((length >> 8) & 0xFF)  # High byte
            time.sleep(0.05)  # Added delay between bytes
            self.send_byte(length & 0xFF)         # Low byte
            time.sleep(0.05)  # Added delay between bytes
            
            # Send request
            for i, byte in enumerate(request_bytes):
                self.send_byte(byte)
                if i < 10:  # Only print first 10 bytes
                    print(f"Sent byte {i+1}: {byte} ('{chr(byte) if 32 <= byte <= 126 else '.'}')")
                elif i == 10:
                    print("...")
                time.sleep(0.05)  # Added delay between bytes

            print("Request sent, waiting for response...")
            # Receive response
            return self.receive_response()
            
        except Exception as e:
            print(f"Error sending request: {e}")
            # Return error response
            return Response(
                500,
                {"Content-Type": "text/plain"},
                f"Internal Client Error: {str(e)}".encode()
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