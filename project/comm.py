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
    def __init__(self, data_pin=23, clock_pin=24):
        """Initialize communication with default pins (23 for data, 24 for clock)."""
        self.data_pin = data_pin
        self.clock_pin = clock_pin
        
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
        
    def send_byte(self, byte):
        """Send a single byte."""
        # Set data line LOW before starting
        self.pi.write(self.data_pin, 0)
        time.sleep(0.001)
        
        # Send each bit
        for i in range(7, -1, -1):
            # Set data line
            bit = (byte >> i) & 1
            self.pi.write(self.data_pin, bit)
            time.sleep(0.001)
            
            # Pulse clock
            self.pi.write(self.clock_pin, 1)
            time.sleep(0.001)
            self.pi.write(self.clock_pin, 0)
            time.sleep(0.001)
            
        # Set data line LOW after byte
        self.pi.write(self.data_pin, 0)
        time.sleep(0.001)
        
    def receive_byte(self):
        """Receive a single byte."""
        byte = 0
        
        # Switch to input mode
        self.pi.set_mode(self.data_pin, pigpio.INPUT)
        time.sleep(0.001)
        
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
        time.sleep(0.001)
        
        return byte
        
    def send_message(self, message):
        """Send a message and wait for response."""
        # Send the message
        for byte in message:
            self.send_byte(byte)
            
        # Send null byte to indicate end of transmission
        self.send_byte(0)
        
        # Switch to receive mode
        response = bytearray()
        while True:
            byte = self.receive_byte()
            if byte == 0:  # End of response
                break
            response.append(byte)
            
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
            
        # Process message and prepare response
        response = self.process_message(bytes(message))
        
        # Send response
        for byte in response:
            self.send_byte(byte)
            
        # Send null byte to indicate end of response
        self.send_byte(0)
        
    def process_message(self, message):
        """Process received message and return response.
        Override this method in subclasses."""
        return b"Received: " + message
        
    def cleanup(self):
        """Clean up GPIO resources."""
        self.pi.stop() 