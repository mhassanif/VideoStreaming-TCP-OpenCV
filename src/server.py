import socket
import json
import os
import cv2

# Paths for videos and thumbnails directories
VIDEO_DIR = os.path.join(os.path.dirname(__file__), "../videos")
THUMBNAIL_DIR = os.path.join(os.path.dirname(__file__), "../thumbnails")


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


def initialize_thumbnails():
    """Scan the videos directory and generate missing thumbnails."""
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

def send_metadata(client_socket):
    """Send video metadata as JSON to the client."""
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

    # Convert metadata to JSON string
    metadata_json = json.dumps(metadata)
    client_socket.sendall(metadata_json.encode('utf-8'))  # Send JSON over TCP
    print(f"Metadata sent to client: {metadata_json}")  


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
    initialize_thumbnails()
    start_server()
