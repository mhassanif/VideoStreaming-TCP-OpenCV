import socket
import json

# Sample metadata for videos
videos = [
    {"title": "Video1", "thumbnail": "thumb1.jpg"},
    {"title": "Video2", "thumbnail": "thumb2.jpg"}
]

def send_metadata(client_socket):
    """Send video metadata as JSON to the client."""
    metadata = json.dumps(videos)  # Convert metadata to JSON string
    client_socket.sendall(metadata.encode())  # Send JSON over TCP

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 5000))
    server_socket.listen(5)
    print("Server listening on port 5000...")
    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connected to {addr}")
        
        # Send metadata to the client
        send_metadata(client_socket)
        
        client_socket.close()

if __name__ == "__main__":
    start_server()
