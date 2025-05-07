"""
Communication protocol between two Raspberry Pis using GPIO pins.
Protocol:
1. Server always starts in receive mode
2. Client sends data, ends with null byte (0x00)
3. Server switches to send mode, client switches to receive mode
4. Server sends response, ends with null byte
5. Both return to default states
"""

import pigpio
import time

class Comm:
    def __init__(self, data_pin=23, clock_pin=24, use_latch=False):
        """Initialize communication with default pins (23 for data, 24 for clock)."""
        self.data_pin = data_pin
        self.clock_pin = clock_pin
        self.use_latch = use_latch
        
        # Initialize pigpio
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("Could not connect to pigpio daemon")
            
        # Set up pins
        self.pi.set_mode(self.clock_pin, pigpio.OUTPUT)
        self.pi.set_mode(self.data_pin, pigpio.OUTPUT)
        
        # Initialize pins to LOW
        self.pi.write(self.clock_pin, 0)
        self.pi.write(self.data_pin, 0)
        
        # Set up latch pin if needed
        if self.use_latch:
            self.latch_pin = 25
            self.pi.set_mode(self.latch_pin, pigpio.OUTPUT)
            self.pi.write(self.latch_pin, 0)
            
        time.sleep(0.01)  # Give time for pins to stabilize
        
    def send_byte(self, byte):
        """Send a single byte."""
        # Set data line LOW before starting
        self.pi.write(self.data_pin, 0)
        time.sleep(0.01)  # Increased delay
        
        # Send each bit
        for i in range(7, -1, -1):
            # Set data line
            bit = (byte >> i) & 1
            self.pi.write(self.data_pin, bit)
            time.sleep(0.01)  # Increased delay
            
            # Pulse clock
            self.pi.write(self.clock_pin, 1)
            time.sleep(0.01)  # Increased delay
            self.pi.write(self.clock_pin, 0)
            time.sleep(0.01)  # Increased delay
            
        # Set data line LOW after byte
        self.pi.write(self.data_pin, 0)
        time.sleep(0.01)  # Increased delay
        
        # Pulse latch to update shift register if using latch
        if self.use_latch:
            self.pi.write(self.latch_pin, 1)
            time.sleep(0.01)  # Increased delay
            self.pi.write(self.latch_pin, 0)
            time.sleep(0.01)  # Increased delay
        
    def receive_byte(self):
        """Receive a single byte."""
        # Switch to input mode and disable output
        self.pi.set_mode(self.data_pin, pigpio.INPUT)
        self.pi.write(self.data_pin, 0)  # Ensure output is disabled
        time.sleep(0.01)  # Increased delay
        
        # Initialize byte
        byte = 0
        
        # Receive each bit
        for i in range(8):
            # Wait for clock high
            while self.pi.read(self.clock_pin) == 0:
                time.sleep(0.001)
            
            # Read data bit
            bit = self.pi.read(self.data_pin)
            byte = (byte << 1) | bit
            
            # Wait for clock low
            while self.pi.read(self.clock_pin) == 1:
                time.sleep(0.001)
        
        # Switch back to output mode
        self.pi.set_mode(self.data_pin, pigpio.OUTPUT)
        self.pi.write(self.data_pin, 0)  # Ensure output starts LOW
        time.sleep(0.01)  # Increased delay
        
        return byte
        
    def send_message(self, message):
        """Send a message and wait for response."""
        # Send the message
        for byte in message:
            self.send_byte(byte)
            time.sleep(0.01)  # Added delay between bytes
            
        # Send null byte to indicate end of transmission
        self.send_byte(0)
        time.sleep(0.01)  # Added delay after null byte
        
        # Switch to receive mode
        response = bytearray()
        while True:
            byte = self.receive_byte()
            if byte == 0:  # End of response
                break
            response.append(byte)
            time.sleep(0.01)  # Added delay between received bytes
            
        return bytes(response)
        
    def receive_message(self):
        """Receive a message and send response."""
        # Receive the message
        message = bytearray()
        while True:
            byte = self.receive_byte()
            if byte == 0:  # End of message
                break
            message.append(byte)
            time.sleep(0.01)  # Added delay between received bytes
            
        # Process message and prepare response
        response = self.process_message(bytes(message))
        time.sleep(0.01)  # Added delay before sending response
        
        # Send response
        for byte in response:
            self.send_byte(byte)
            time.sleep(0.01)  # Added delay between bytes
            
        # Send null byte to indicate end of response
        self.send_byte(0)
        time.sleep(0.01)  # Added delay after null byte
        
    def process_message(self, message):
        """Process received message and return response.
        Override this method in subclasses."""
        return b"Received: " + message
        
    def cleanup(self):
        """Clean up GPIO resources."""
        self.pi.stop() 