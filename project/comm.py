"""
This defines a communication protocol between two raspberry pi's. It uses GPIO pins and allows for the two to communicate.

We take in a clock signal to make sure the two are syncronized 
"""

from dataclasses import dataclass
import RPi.GPIO as GPIO
import time

@dataclass
class Frame:
    header: bytes
    payload: bytes

    def __repr__(self):
        return f'{self.header}{self.payload}'

class Connection:
    def __init__(self, data_pin, clock_pin):
        # Validate pins

        # set clock pin as output
        self.data_pin = data_pin
        self.clock_pin = clock_pin

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        GPIO.setup(self.clock_pin, GPIO.OUT)
        GPIO.setup(self.data_pin, GPIO.OUT)


    def send_file(self, filename: str):
        with open(filename, 'rb') as file:
            data = file.read()

        for byte in data:
            self.send_byte(byte)


    def send_byte(self, byte):

        for ix in range(7, -1, -1):
            bit = GPIO.HIGH if (byte >> ix) & 1 else GPIO.LOW

            GPIO.output(self.data_pin, bit)
            time.sleep(0.1)

            # Now pulse the clock
            GPIO.output(self.clock_pin, GPIO.HIGH)
            time.sleep(0.1)
            GPIO.output(self.clock_pin, GPIO.LOW)

    def cleanup(self):
        GPIO.cleanup()

class Connect():
    def __init__(self, data_pin, clock_pin):
        self.conn= Connection(data_pin, clock_pin)

    def __enter__(self):
        return self.conn

    def __exit__(self, type, value, traceback):

        # Handle excpetions perhaps

        self.conn.cleanup()

def main():

    with Connect(23, 24) as conn:
        conn.send_file('comm.py')



        # for clk in range(8):
        #     bit = ~bit
        #
            # conn.send_byte(bit)
            # time.sleep(0.5)
            #
            # GPIO.output(conn.clock_pin, GPIO.HIGH)
            # time.sleep(0.1)
            # GPIO.output(conn.clock_pin, GPIO.LOW)

main()

