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
        self.pi.set_mode(self.data_pin, pigpio.INPUT)  # Start in INPUT mode
        self.pi.set_mode(self.latch_pin, pigpio.OUTPUT)
        
        # Initialize all pins to LOW
        self.pi.write(self.clock_pin, 0)
        self.pi.write(self.latch_pin, 0)

        # Simple in-memory storage
        self.storage = {}
        print("Server initialized and ready to receive requests")

    def wait_for_start_sequence(self):
        """Wait for the start sequence (clock high, data high)"""
        print("Waiting for start sequence...")
        while True:
            # Wait for clock to go high
            while self.pi.read(self.clock_pin) == 0:
                time.sleep(0.001)
            
            # Check if data is also high
            if self.pi.read(self.data_pin) == 1:
                print("Start sequence detected")
                time.sleep(0.01)  # Wait for signal to stabilize
                return
            
            # If data wasn't high, wait for clock to go low and try again
            while self.pi.read(self.clock_pin) == 1:
                time.sleep(0.001)

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
        """Receive a byte from the client"""
        # Ensure we're in INPUT mode
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
        
        time.sleep(0.01)  # Added delay after byte reception
        return byte

    def send_byte(self, byte):
        """Send a byte to the client"""
        # Switch to OUTPUT mode
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
        
        # Switch back to INPUT mode
        self.pi.set_mode(self.data_pin, pigpio.INPUT)
        time.sleep(0.01)  # Added delay after mode switch

    def send_response(self, response: Response):
        """Send a response to the client"""
        # Convert response to bytes
        response_data = {
            'status': response.status,
            'headers': response.headers,
            'body': response.body.hex()  # Convert bytes to hex string for JSON
        }
        response_bytes = json.dumps(response_data).encode() + b'\n'
        
        # Send length first
        length = len(response_bytes)
        print(f"Sending response ({length} bytes):")
        self.send_byte((length >> 8) & 0xFF)  # High byte
        time.sleep(0.05)  # Added delay between bytes
        self.send_byte(length & 0xFF)         # Low byte
        time.sleep(0.05)  # Added delay between bytes
        
        # Send response
        for byte in response_bytes:
            self.send_byte(byte)
            time.sleep(0.05)  # Added delay between bytes
        print("Response sent")

    def receive_request(self) -> Request:
        """Receive a request from the client"""
        try:
            # Wait for start sequence
            self.wait_for_start_sequence()
            
            # Read length (2 bytes)
            length_high = self.receive_byte()
            time.sleep(0.05)  # Added delay between bytes
            length_low = self.receive_byte()
            length = (length_high << 8) | length_low
            
            # Validate length (reasonable maximum size)
            if length > 4096:  # 4KB max request size
                raise ValueError(f"Request too large: {length} bytes")
            if length < 1:
                raise ValueError(f"Invalid request length: {length} bytes")
            
            print(f"Expecting request of length: {length} bytes")
            
            # Read request data
            data = bytearray()
            for i in range(length):
                byte = self.receive_byte()
                data.append(byte)
                if i < 10:  # Only print first 10 bytes to avoid overwhelming output
                    print(f"Received byte {i+1}: {byte} ('{chr(byte) if 32 <= byte <= 126 else '.'}')")
                elif i == 10:
                    print("...")
                time.sleep(0.05)  # Added delay between bytes
            
            # Try to decode and validate JSON
            try:
                request_str = data.decode('utf-8')
                print(f"Received request string: {request_str[:100]}...")  # Print first 100 chars
                request_data = json.loads(request_str)
            except UnicodeDecodeError as e:
                print(f"Failed to decode request as UTF-8: {e}")
                print(f"Raw bytes: {data.hex()}")
                raise ValueError("Invalid UTF-8 encoding in request")
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON: {e}")
                print(f"Received data: {request_str}")
                raise ValueError("Invalid JSON format in request")
            
            # Validate required fields
            required_fields = ['method', 'path', 'headers']
            missing_fields = [field for field in required_fields if field not in request_data]
            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")
            
            return Request(
                method=request_data['method'],
                path=request_data['path'],
                headers=request_data['headers'],
                body=bytes.fromhex(request_data['body']) if request_data.get('body') else b''
            )
        except Exception as e:
            print(f"Error receiving request: {e}")
            # Send error response
            error_response = Response(
                400,
                {"Content-Type": "text/plain"},
                f"Bad Request: {str(e)}".encode()
            )
            self.send_response(error_response)
            raise  # Re-raise to be caught by the main loop

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
                    print(f"  Stored data for key '{key}': {data}")
                    response = Response(200, {}, b"OK")
                except:
                    response = Response(400, {}, b"Invalid JSON")
            else:
                response = Response(404, {}, b"Not Found")
            
        else:
            response = Response(405, {}, b"Method Not Allowed")

        print(f"\nSending response:")
        print(f"  Status: {response.status}")
        print(f"  Headers: {response.headers}")
        try:
            body_str = response.body.decode()
            print(f"  Body: {body_str}")
        except:
            print(f"  Body: {response.body}")

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