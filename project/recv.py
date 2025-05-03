import pigpio
import time

# GPIO pins (BCM numbering)
DATA_PIN  = 23
CLOCK_PIN = 24

# state for assembling one byte
current_byte = 0
bit_count    = 0

# buffer to collect received bytes
received = bytearray()

def is_printable_byte(byte):
    """Check if a byte represents a printable ASCII character"""
    return 32 <= byte <= 126

def on_clock_rising(gpio, level, tick):
    global current_byte, bit_count
    # Add a small delay to ensure data is stable
    time.sleep(0.0001)  # 100 microseconds delay
    
    # sample data bit
    bit = pi.read(DATA_PIN)
    # shift into current_byte
    current_byte = (current_byte << 1) | bit
    bit_count += 1

    if bit_count == 8:
        # full byte ready
        byte_value = current_byte & 0xFF
        
        # Only append if it's a printable ASCII character
        if is_printable_byte(byte_value):
            received.append(byte_value)
            print(f"Received: 0x{byte_value:02X} ('{chr(byte_value)}')")
        else:
            print(f"Skipped non-printable byte: 0x{byte_value:02X}")
            
        # reset for next byte
        current_byte = 0
        bit_count    = 0

def main():
    global pi
    # Initialize pigpio
    pi = pigpio.pi()
    if not pi.connected:
        raise RuntimeError("Could not connect to pigpio daemon")

    # Set up pins as inputs with pull-downs
    pi.set_mode(DATA_PIN, pigpio.INPUT)
    pi.set_mode(CLOCK_PIN, pigpio.INPUT)
    pi.set_pull_up_down(DATA_PIN, pigpio.PUD_DOWN)
    pi.set_pull_up_down(CLOCK_PIN, pigpio.PUD_DOWN)

    # Set up callback for rising edge
    cb = pi.callback(CLOCK_PIN, pigpio.RISING_EDGE, on_clock_rising)

    print("Waiting for data...  Press Ctrl-C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        cb.cancel()  # Cancel the callback
        pi.stop()    # Stop pigpio
        # write all bytes out
        with open("received.bin", "wb") as f:
            f.write(received)
        print(f"Wrote {len(received)} bytes to received.bin")

if __name__ == "__main__":
    main()
