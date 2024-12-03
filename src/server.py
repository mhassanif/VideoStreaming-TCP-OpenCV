import socket
import json
import os
import cv2
import threading
import time

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

def receive_control_signal(client_socket, shared_state, state_condition):
    """
    Handles receiving control signals from the client.
    Updates the shared state and notifies the streaming thread.
    """
    while True:
        try:
            data = client_socket.recv(1024).decode()
            if not data:
                break

            control_signal = eval(data)  
            action = control_signal.get("action")
            video_name = control_signal.get("video")  

            with state_condition:
                if action == "start" and video_name:
                    shared_state["video_name"] = video_name
                    shared_state["control_flags"]["stop"] = False
                    state_condition.notify()

                elif action == "stop":
                    shared_state["control_flags"]["stop"] = True
                    shared_state["video_name"] = None
                    state_condition.notify()

        except Exception as e:
            print(f"Error in receiving control signal: {e}")
            break



def stream_video(client_socket, shared_state, state_condition):
    """
    Streams the video requested by the client, using the shared state.
    Dynamically switches videos based on the requested video name.
    """
    try:
        while True:
            with state_condition:
                # Wait for a video to be assigned or the stop flag to reset
                while shared_state["video_name"] is None or shared_state["control_flags"]["stop"]:
                    state_condition.wait()
                
                # Retrieve the video name
                video_name = shared_state["video_name"]
                video_path = os.path.join(VIDEO_DIR, video_name + '.mp4')

                # Check if the requested video exists
                if not os.path.exists(video_path):
                    print(f"Error: Video '{video_name}' not found.")
                    shared_state["video_name"] = None
                    continue

                # Open the video file
                cap = cv2.VideoCapture(video_path)
                if not cap.isOpened():
                    print(f"Error: Unable to open video '{video_path}'")
                    shared_state["video_name"] = None
                    continue

                print(f"Streaming video: {video_name}")

            # Stream video frames
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    print("End of video reached.")
                    break

                with state_condition:
                    # Check for stop signal
                    if shared_state["control_flags"]["stop"]:
                        print("Stop signal received. Ending current stream.")
                        break

                # Encode frame as JPEG
                _, buffer = cv2.imencode('.jpg', frame)
                frame_data = buffer.tobytes()

                # Send frame size and data
                frame_size = len(frame_data)
                client_socket.sendall(frame_size.to_bytes(4, 'big'))  # Frame size (4 bytes)
                client_socket.sendall(frame_data)  # Frame data

                # Simulate 30 FPS streaming
                time.sleep(1 / 30)

            cap.release()  # Release the video file when done

    except Exception as e:
        print(f"Error during video streaming: {e}")
    finally:
        print("Video streaming thread terminated.")






def handle_client(client_socket):
    """
    Handles the connection with a single client.
    Manages threads for streaming video and receiving control signals.
    """
    print("Client connected.")
    
    # Shared state for the client
    shared_state = {
        "video_name": None,  # Currently requested video name
        "control_flags": {
            "pause": False,  # Pause/resume video
            "stop": True     # Stop video streaming
        }
    }
    
    # Condition variable for thread synchronization
    state_condition = threading.Condition()

    # Create threads for streaming and receiving control signals
    stream_thread = threading.Thread(target=stream_video, args=(client_socket, shared_state, state_condition))
    control_thread = threading.Thread(target=receive_control_signal, args=(client_socket, shared_state, state_condition))

    # Start threads
    stream_thread.start()
    control_thread.start()

    # Wait for threads to finish
    control_thread.join()  # Control thread should end when client disconnects
    shared_state["control_flags"]["stop"] = True  # Ensure streaming thread exits
    with state_condition:
        state_condition.notify_all()  # Wake the streaming thread if waiting
    stream_thread.join()

    print("Client connection closed.")



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

        # Handle the client connection in a new thread
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))
        client_handler.start()

        # Continuously receive control signals from the client
        # receive_control_signal(client_socket)

        # Close the client connection
        # client_socket.close()
        # print(f"Connection with {addr} closed.")


if __name__ == "__main__":
    generate_video_thumbnails()  # Ensure thumbnails are generated before starting the server
    start_server()
