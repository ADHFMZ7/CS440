"""
This defines a communication protocol between two raspberry pi's. It uses GPIO pins and allows for the two to communicate.

We take in a clock signal to make sure the two are syncronized 
"""

from dataclasses import dataclass
import pigpio
import time
import sys
import argparse

@dataclass
class Frame:
    header: bytes
    payload: bytes

    def __repr__(self):
        return f'{self.header}{self.payload}'

class Connection:
    def __init__(self, data_pin, clock_pin, single_step=False):
        # Validate pins
        self.data_pin = data_pin
        self.clock_pin = clock_pin
        self.latch_pin = 25  # Add latch pin
        self.single_step = single_step

        # Initialize pigpio
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("Could not connect to pigpio daemon")

        # Set up pins as outputs
        self.pi.set_mode(self.clock_pin, pigpio.OUTPUT)
        self.pi.set_mode(self.data_pin, pigpio.OUTPUT)
        self.pi.set_mode(self.latch_pin, pigpio.OUTPUT)
        
        # Initialize all pins to LOW
        self.pi.write(self.clock_pin, 0)
        self.pi.write(self.data_pin, 0)
        self.pi.write(self.latch_pin, 0)

    def send_file(self, filename: str):
        try:
            with open(filename, 'rb') as file:
                data = file.read()
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
            sys.exit(1)
        except IOError:
            print(f"Error: Could not read file '{filename}'.")
            sys.exit(1)

        for byte in data:
            self.send_byte(byte)
            if self.single_step:
                input("Press Enter to send next byte...")

    def send_byte(self, byte):
        # Ensure data line is LOW before starting
        self.pi.write(self.data_pin, 0)
        self.pi.write(self.clock_pin, 0)
        time.sleep(0.001)  # 1ms delay to ensure stable start

        for ix in range(7, -1, -1):
            # Set data line first
            bit = 1 if (byte >> ix) & 1 else 0
            self.pi.write(self.data_pin, bit)
            time.sleep(0.0005)  # 500μs delay

            # Then pulse clock
            self.pi.write(self.clock_pin, 1)
            time.sleep(0.0005)  # 500μs delay
            self.pi.write(self.clock_pin, 0)
            time.sleep(0.0005)  # 500μs delay

        # Set data line LOW after shifting
        self.pi.write(self.data_pin, 0)
        time.sleep(0.0005)  # 500μs delay

        # Pulse the latch after the byte is sent
        self.pi.write(self.latch_pin, 1)
        time.sleep(0.0005)  # 500μs delay
        self.pi.write(self.latch_pin, 0)
        time.sleep(0.0005)  # 500μs delay

    def cleanup(self):
        self.pi.stop()

class Connect():
    def __init__(self, data_pin, clock_pin, single_step=False):
        self.conn = Connection(data_pin, clock_pin, single_step)

    def __enter__(self):
        return self.conn

    def __exit__(self, type, value, traceback):
        self.conn.cleanup()

def main():
    parser = argparse.ArgumentParser(description='Send a file over GPIO pins')
    parser.add_argument('filename', help='The file to send')
    parser.add_argument('-s', '--single-step', action='store_true', 
                      help='Enable single-step mode (press Enter for each byte)')
    
    args = parser.parse_args()

    with Connect(23, 24, args.single_step) as conn:
        conn.send_file(args.filename)

if __name__ == "__main__":
    main()

