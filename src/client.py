import socket
import json

def receive_metadata(client_socket):
    """Receive video metadata from the server and display it."""
    # Receive data from the server
    data = client_socket.recv(4096).decode()
    
    # Parse the JSON data
    videos = json.loads(data)
    print("Available Videos:")
    for video in videos:
        # print(f"- {video['title']}")
        print(f"- {video['title']} (Thumbnail Path: {video['thumbnail']})")


def connect_to_server():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('127.0.0.1', 5000))  # Connect to server
    
    # Receive and display metadata
    receive_metadata(client_socket)
    
    client_socket.close()

if __name__ == "__main__":
    connect_to_server()
