# client.py
"""
Client class that handles the queries.
Sends the query to the trusted proxy to execute.
Receives the information and displays it to the Client.
"""

class Client:
    """Client handles the input/output."""
    
    def __init__(self, proxy) -> None:
        self._proxy = proxy
        
    def put(self, key: str, value: str):
        """PUT query sent to proxy to execute"""
        return self._proxy.put(key, value)
    
    def get(self, key: str, value: str):
        """GET query sent to proxy to execute."""
        return self._proxy.get(key, value)