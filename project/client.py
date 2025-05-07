"""
Client implementation using the GPIO communication protocol.
Supports sending HTTP-like requests.
"""

from comm import Comm
import time
import json

class Client(Comm):
    def __init__(self, data_pin=23, clock_pin=24):
        # Initialize with latch pin for shift register display
        super().__init__(data_pin, clock_pin, latch_pin=25)
        
    def get(self, path, headers=None):
        """Send a GET request."""
        if headers is None:
            headers = {}
            
        # Build request
        request = f"GET {path} HTTP/1.1\n"
        for key, value in headers.items():
            request += f"{key}: {value}\n"
        request += "\n"
        
        # Print request
        print("\nSending request:")
        print("=" * 40)
        print(request, end="")
        print("=" * 40)
        
        # Send request and get response
        response = self.send_message(request.encode('utf-8'))
        return self._parse_response(response)
        
    def post(self, path, data, headers=None):
        """Send a POST request with JSON data."""
        if headers is None:
            headers = {}
            
        # Convert data to JSON
        body = json.dumps(data)
        
        # Build request
        request = f"POST {path} HTTP/1.1\n"
        headers['Content-Type'] = 'application/json'
        headers['Content-Length'] = str(len(body))
        for key, value in headers.items():
            request += f"{key}: {value}\n"
        request += "\n"
        request += body
        
        # Print request
        print("\nSending request:")
        print("=" * 40)
        print(request, end="")
        print("=" * 40)
        
        # Send request and get response
        response = self.send_message(request.encode('utf-8'))
        return self._parse_response(response)
        
    def _parse_response(self, response):
        """Parse HTTP-like response."""
        try:
            # Split into lines
            lines = response.decode('utf-8').split('\n')
            
            # Parse status line
            status_line = lines[0]
            version, status_code, status_text = status_line.split(' ', 2)
            
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
                        
            return {
                'status_code': int(status_code),
                'status_text': status_text,
                'headers': headers,
                'body': body.strip()
            }
        except Exception as e:
            return {
                'status_code': 500,
                'status_text': 'Internal Error',
                'headers': {},
                'body': f"Error parsing response: {str(e)}"
            }
            
if __name__ == "__main__":
    client = Client()
    
    try:
        while True:
            # Get command from user
            command = input("\nEnter command (get/post/quit): ").lower()
            
            if command == 'quit':
                break
            elif command == 'get':
                path = input("Enter path (e.g., / or /data/key): ")
                response = client.get(path)
                print(f"\nStatus: {response['status_code']} {response['status_text']}")
                print(f"Body: {response['body']}")
            elif command == 'post':
                path = input("Enter path (e.g., /data/key): ")
                data_str = input("Enter JSON data: ")
                try:
                    data = json.loads(data_str)
                    response = client.post(path, data)
                    print(f"\nStatus: {response['status_code']} {response['status_text']}")
                    print(f"Body: {response['body']}")
                except json.JSONDecodeError:
                    print("Invalid JSON data")
            else:
                print("Unknown command")
            
    except KeyboardInterrupt:
        print("\nClient stopping...")
    finally:
        client.cleanup()
