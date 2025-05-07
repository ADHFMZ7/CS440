"""
Client implementation using the GPIO communication protocol.
"""

from comm import Comm
import time

class Client(Comm):
    def __init__(self, data_pin=23, clock_pin=24):
        super().__init__(data_pin, clock_pin, use_latch=True)  # Enable latch for shift register
        
    def send(self, message):
        """Send a message and return the response."""
        if isinstance(message, str):
            message = message.encode('utf-8')
            
        response = self.send_message(message)
        try:
            return response.decode('utf-8')
        except:
            return response
            
if __name__ == "__main__":
    client = Client()
    
    try:
        while True:
            # Get message from user
            message = input("Enter message (or 'quit' to exit): ")
            if message.lower() == 'quit':
                break
                
            # Send message and get response
            response = client.send(message)
            print(f"Response: {response}")
            
    except KeyboardInterrupt:
        print("\nClient stopping...")
    finally:
        client.cleanup()
