"""
Server implementation using the GPIO communication protocol.
"""

from comm import Comm
import time

class Server(Comm):
    def __init__(self, data_pin=23, clock_pin=24):
        # Initialize without latch pin
        super().__init__(data_pin, clock_pin, latch_pin=None)
        self.running = False
        
    def process_message(self, message):
        """Process received message and return response."""
        try:
            # Convert message to string for processing
            message_str = message.decode('utf-8')
            print(f"Received: {message_str}")
            
            # Echo the message back with a prefix
            return f"Server received: {message_str}".encode('utf-8')
        
        except Exception as e:
            return f"Error processing message: {str(e)}".encode('utf-8')
            
    def run(self):
        """Run the server, continuously waiting for messages."""
        self.running = True
        print("Server started, waiting for messages...")
        
        try:
            while self.running:
                self.receive_message()
        except KeyboardInterrupt:
            print("\nServer stopping...")
        finally:
            self.cleanup()
            
if __name__ == "__main__":
    server = Server()
    server.run()