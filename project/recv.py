import RPi.GPIO as GPIO
import time

# GPIO pins (BCM numbering)
DATA_PIN  = 23
CLOCK_PIN = 24

# state for assembling one byte
current_byte = 0
bit_count    = 0

# buffer to collect received bytes
received = bytearray()

def on_clock_rising(channel):
    global current_byte, bit_count
    # sample data bit
    bit = GPIO.input(DATA_PIN)
    # shift into current_byte
    current_byte = (current_byte << 1) | bit
    bit_count += 1

    if bit_count == 8:
        # full byte ready
        received.append(current_byte & 0xFF)
        print(f"Received: 0x{current_byte:02X}")
        # reset for next byte
        current_byte = 0
        bit_count    = 0

def main():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    # enable internal pull-downs so pins idle at 0 when nothing is connected
    GPIO.setup(DATA_PIN,  GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(CLOCK_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    # catch every rising edge (no bouncetime)
    GPIO.add_event_detect(CLOCK_PIN, GPIO.RISING, callback=on_clock_rising)

    print("Waiting for data...  Press Ctrl-C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        GPIO.remove_event_detect(CLOCK_PIN)
        GPIO.cleanup()
        # write all bytes out
        with open("received.bin", "wb") as f:
            f.write(received)
        print(f"Wrote {len(received)} bytes to received.bin")

if __name__ == "__main__":
    main()
