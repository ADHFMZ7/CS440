"""
Server implementation using the GPIO communication protocol.
Handles HTTP-like requests with GET and POST methods.
"""

from comm import Comm
import time
import json

class Server(Comm):
    def __init__(self, data_pin=23, clock_pin=24, latch_pin=25):
        # Initialize without latch pin
        super().__init__(data_pin, clock_pin, latch_pin=latch_pin)
        self.running = False
        self.data = {}  # Simple in-memory storage
        
    def process_message(self, message):
        """Process HTTP-like request and return response."""
        try:
            # Parse the request
            request_str = message.decode('utf-8')
            
            # Print request
            print("\nReceived request:")
            print("=" * 40)
            print(request_str, end="")
            print("\n" + "=" * 40)
            
            # Split into lines
            lines = request_str.strip().split('\n')
            if not lines:
                return self._error_response("Empty request")
                
            # Parse request line (e.g., "GET /path HTTP/1.1")
            request_line = lines[0].strip()
            parts = request_line.split()
            if len(parts) != 3:
                return self._error_response("Invalid request line")
                
            method, path, version = parts
            
            # Parse headers
            headers = {}
            body = ""
            in_body = False
            for line in lines[1:]:
                if not in_body and line.strip() == "":
                    in_body = True
                    continue
                if in_body:
                    body += line + "\n"
                else:
                    if ":" in line:
                        key, value = line.split(":", 1)
                        headers[key.strip()] = value.strip()
            
            # Handle request based on method
            if method == "GET":
                response = self._handle_get(path, headers)
            elif method == "POST":
                response = self._handle_post(path, headers, body)
            else:
                response = self._error_response(f"Unsupported method: {method}")
                
            # Print response
            print("\nSending response:")
            print("=" * 40)
            print(response.decode('utf-8'), end="")
            print("\n" + "=" * 40)
            
            return response
                
        except Exception as e:
            response = self._error_response(f"Error processing request: {str(e)}")
            print("\nSending error response:")
            print("=" * 40)
            print(response.decode('utf-8'), end="")
            print("\n" + "=" * 40)
            return response
            
    def _handle_get(self, path, headers):
        """Handle GET request."""
        if path == "/":
            return self._success_response("Server is running")
        elif path in self.data:
            return self._success_response(json.dumps(self.data[path]))
        else:
            return self._error_response(f"Path not found: {path}")
            
    def _handle_post(self, path, headers, body):
        """Handle POST request."""
        try:
            data = json.loads(body)
            self.data[path] = data
            return self._success_response(f"Data stored at {path}")
        except json.JSONDecodeError:
            return self._error_response("Invalid JSON in request body")
            
    def _success_response(self, body):
        """Create a success response."""
        response = "HTTP/1.1 200 OK\n"
        response += "Content-Type: text/plain\n"
        response += f"Content-Length: {len(body)}\n"
        response += "\n"
        response += body
        return response.encode('utf-8')
        
    def _error_response(self, message):
        """Create an error response."""
        response = "HTTP/1.1 400 Bad Request\n"
        response += "Content-Type: text/plain\n"
        response += f"Content-Length: {len(message)}\n"
        response += "\n"
        response += message
        return response.encode('utf-8')
            
    def run(self):
        """Run the server, continuously waiting for messages."""
        self.running = True
        print("\nServer started, waiting for requests...")
        print("=" * 40)
        
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