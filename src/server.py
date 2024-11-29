import socket
import json
import os
import cv2

# Paths for videos and thumbnails directories
VIDEO_DIR = os.path.join(os.path.dirname(__file__), "../videos")
THUMBNAIL_DIR = os.path.join(os.path.dirname(__file__), "../thumbnails")
METADATA_FILE = os.path.join(VIDEO_DIR, "metadata.json")


# Helper function
def create_thumbnail(video_path, thumbnail_path):
    """Generate a thumbnail for the given video."""
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()  # Read the first frame
    if ret:
        cv2.imwrite(thumbnail_path, frame)  # Save as thumbnail
        print(f"Thumbnail created: {thumbnail_path}")
    else:
        print(f"Failed to create thumbnail for: {video_path}")
    cap.release()


def generate_video_thumbnails():
    """Ensure that thumbnails are generated for all videos in the video directory."""
    if not os.path.exists(THUMBNAIL_DIR):
        os.makedirs(THUMBNAIL_DIR)  # Create the thumbnails directory if it doesn't exist

    videos = [f for f in os.listdir(VIDEO_DIR) if f.endswith(('.mp4', '.avi', '.mkv'))]
    print(f"Found videos: {videos}")

    for video in videos:
        video_path = os.path.join(VIDEO_DIR, video)
        thumbnail_path = os.path.join(THUMBNAIL_DIR, f"{os.path.splitext(video)[0]}.jpg")

        # Generate thumbnail only if it doesn't exist
        if not os.path.exists(thumbnail_path):
            create_thumbnail(video_path, thumbnail_path)
        else:
            print(f"Thumbnail already exists: {thumbnail_path}")


def generate_metadata():
    """Generate video metadata (title and thumbnail paths) and store it in a JSON file."""
    # List all videos in the directory
    videos = [f for f in os.listdir(VIDEO_DIR) if f.endswith(('.mp4', '.avi', '.mkv'))]
    metadata = []

    # Prepare metadata for each video
    for video in videos:
        video_name = os.path.splitext(video)[0]
        thumbnail_path = os.path.join(THUMBNAIL_DIR, f"{video_name}.jpg")

        # Verify if thumbnail exists
        if os.path.exists(thumbnail_path):
            metadata.append({
                "title": video_name,
                "thumbnail": thumbnail_path
            })
        else:
            print(f"Warning: Thumbnail missing for {video}")

    # Save metadata as JSON in the videos directory
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=4)
    print(f"Metadata saved to {METADATA_FILE}")


def read_metadata():
    """Read video metadata from the stored JSON file."""
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        return metadata
    else:
        print("Metadata file not found, generating metadata...")
        generate_metadata()
        return read_metadata()  # Recursively call after generating metadata

def send_metadata(client_socket):
    """Send video metadata as JSON to the client."""
    # Get the metadata (either from the JSON or generated)
    metadata = read_metadata()
    
    # Convert metadata to JSON string
    metadata_json = json.dumps(metadata)
    client_socket.sendall(metadata_json.encode('utf-8'))  # Send JSON over TCP
    print("Metadata sent to client!")

def receive_control_signal(client_socket):
    """Receive control signals from the client continuously."""
    try:
        while True:  # Keep listening for client messages
            data = client_socket.recv(1024).decode('utf-8')  # Adjust buffer size as needed
            if not data:
                print("Client disconnected.")
                break

            # Parse and handle the received control signal
            control_signal = json.loads(data)
            print(f"Received control signal: {control_signal}")

            # Handle different actions
            action = control_signal.get("action")
            video_title = control_signal.get("video")
            if action == "start":
                print(f"Starting video: {video_title}")
            elif action == "pause":
                print(f"Pausing video: {video_title}")
            elif action == "unpause":
                print(f"UnPausing video: {video_title}")
            elif action == "stop":
                print("Stopping video playback.")
            else:
                print(f"Unknown action: {action}")

    except Exception as e:
        print(f"Error receiving control signal: {e}")


def start_server():
    """Start the server, accept client connections, and handle them."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 5000))
    server_socket.listen(5)
    print("Server listening on port 5000...")
    
    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connected to {addr}")

        # Send metadata to the client
        send_metadata(client_socket)

        # Continuously receive control signals from the client
        receive_control_signal(client_socket)

        # Close the client connection
        client_socket.close()
        print(f"Connection with {addr} closed.")


if __name__ == "__main__":
    generate_video_thumbnails()  # Ensure thumbnails are generated before starting the server
    start_server()
