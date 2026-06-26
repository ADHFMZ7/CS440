"""
Interactive communication functions for sending messages between Raspberry Pis.
This builds on top of the existing comm.py implementation but makes it more suitable
for interactive use in a Python interpreter.
"""

from connection import Connection
import time

class InteractiveConnection:
    def __init__(self, data_pin=23, clock_pin=24):
        """Initialize the connection with default pins (23 for data, 24 for clock)."""
        self.conn = Connection(data_pin, clock_pin)
        
    def send(self, message: str):
        """Send a text message."""
        # Convert string to bytes and send
        data = message.encode('utf-8')
        for byte in data:
            self.conn.send_byte(byte)
        # Send a newline to mark end of message
        self.conn.send_byte(ord('\n'))
        
    def send_bytes(self, data: bytes):
        """Send raw bytes."""
        for byte in data:
            self.conn.send_byte(byte)
            
    def cleanup(self):
        """Clean up the connection."""
        self.conn.cleanup()
