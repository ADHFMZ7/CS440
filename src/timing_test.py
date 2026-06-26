"""
Old code just used to test transmission times. This code uses functions that I have since changed.
"""

import pigpio
import time
import sys
import matplotlib.pyplot as plt
import numpy as np
from comm import Connection, Connect

def create_test_file(filename, size=1000):
    """Create a test file with a known pattern"""
    with open(filename, 'wb') as f:
        # Write a repeating pattern of bytes
        pattern = bytes([i % 256 for i in range(256)])
        for _ in range(size // 256 + 1):
            f.write(pattern)

def send_with_timing(filename, delay_us):
    """Send a file with specific timing and return error rate"""
    received = bytearray()
    current_byte = 0
    bit_count = 0
    
    def on_clock_rising(gpio, level, tick):
        nonlocal current_byte, bit_count
        bit = pi.read(23)  # DATA_PIN
        current_byte = (current_byte << 1) | bit
        bit_count += 1

        if bit_count == 8:
            received.append(current_byte & 0xFF)
            current_byte = 0
            bit_count = 0

    # Initialize pigpio
    pi = pigpio.pi()
    if not pi.connected:
        raise RuntimeError("Could not connect to pigpio daemon")

    # Set up receiver
    pi.set_mode(23, pigpio.INPUT)  # DATA_PIN
    pi.set_mode(24, pigpio.INPUT)  # CLOCK_PIN
    pi.set_pull_up_down(23, pigpio.PUD_DOWN)
    pi.set_pull_up_down(24, pigpio.PUD_DOWN)
    cb = pi.callback(24, pigpio.RISING_EDGE, on_clock_rising)

    # Send the file with specified timing
    with Connect(23, 24) as conn:
        # Override the timing in the Connection class
        conn.send_byte = lambda byte: send_byte_with_timing(conn, byte, delay_us)
        conn.send_file(filename)

    # Clean up
    cb.cancel()
    pi.stop()

    # Calculate error rate
    with open(filename, 'rb') as f:
        sent = f.read()
    
    # Trim received data to match sent data length
    received = received[:len(sent)]
    
    # Calculate error rate
    errors = sum(1 for s, r in zip(sent, received) if s != r)
    error_rate = errors / len(sent) if sent else 0
    
    return error_rate

def send_byte_with_timing(conn, byte, delay_us):
    """Send a single byte with specified timing"""
    delay = delay_us / 1000000.0  # Convert microseconds to seconds
    
    # Ensure data line is LOW before starting
    conn.pi.write(conn.data_pin, 0)
    conn.pi.write(conn.clock_pin, 0)
    time.sleep(delay)

    for ix in range(7, -1, -1):
        # Set data line first
        bit = 1 if (byte >> ix) & 1 else 0
        conn.pi.write(conn.data_pin, bit)
        time.sleep(delay)

        # Then pulse clock
        conn.pi.write(conn.clock_pin, 1)
        time.sleep(delay)
        conn.pi.write(conn.clock_pin, 0)
        time.sleep(delay)

    # Set data line LOW after shifting
    conn.pi.write(conn.data_pin, 0)
    time.sleep(delay)

    # Pulse the latch after the byte is sent
    conn.pi.write(conn.latch_pin, 1)
    time.sleep(delay)
    conn.pi.write(conn.latch_pin, 0)
    time.sleep(delay)

def main():
    # Create test file
    test_file = "timing_test.bin"
    create_test_file(test_file)
    
    # Test different timing values
    delays = np.linspace(100, 2000, 20)  # Test from 100μs to 2000μs
    error_rates = []
    
    print("Testing different timing values...")
    for delay in delays:
        print(f"Testing {delay:.0f}μs delay...")
        error_rate = send_with_timing(test_file, delay)
        error_rates.append(error_rate)
        print(f"Error rate: {error_rate:.2%}")
    
    # Plot results
    plt.figure(figsize=(10, 6))
    plt.plot(delays, error_rates, 'b.-')
    plt.xlabel('Delay (μs)')
    plt.ylabel('Error Rate')
    plt.title('Error Rate vs. Timing Delay')
    plt.grid(True)
    
    # Save plot
    plt.savefig('timing_test_results.png')
    print("\nPlot saved as 'timing_test_results.png'")
    
    # Find sweet spot (lowest error rate with reasonable speed)
    sweet_spot_idx = np.argmin(error_rates)
    sweet_spot_delay = delays[sweet_spot_idx]
    print(f"\nRecommended delay: {sweet_spot_delay:.0f}μs")
    print(f"Error rate at this delay: {error_rates[sweet_spot_idx]:.2%}")

if __name__ == "__main__":
    main() 
