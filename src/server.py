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
            # Receive control signal (example: {"action": "start", "video": "video_name"})
            data = client_socket.recv(1024).decode()
            if not data:
                break

            control_signal = eval(data)  # Assume JSON-like control signal
            action = control_signal.get("action")
            video_name = control_signal.get("video")  # Extract video name

            with state_condition:
                if action == "start" and video_name:
                    shared_state["video_name"] = video_name  # Assign the video name
                    shared_state["control_flags"]["stop"] = False
                    state_condition.notify()  # Notify streaming thread

                elif action == "pause":
                    shared_state["control_flags"]["pause"] = True

                elif action == "resume":
                    shared_state["control_flags"]["pause"] = False
                    state_condition.notify()  # Notify streaming thread

                elif action == "stop":
                    shared_state["control_flags"]["stop"] = True
                    state_condition.notify()  # Notify streaming thread
        except Exception as e:
            print(f"Error in receiving control signal: {e}")
            break



def stream_video(client_socket, shared_state, state_condition):
    """
    Streams video frames to the client based on the shared state.
    Reacts to control signals for pausing, stopping, or switching videos.
    Also plays the video locally on the server.
    """
    while True:
        with state_condition:
            while not shared_state["video_name"] or shared_state["control_flags"]["stop"]:
                # Wait until a video name is assigned or the stop signal is cleared
                state_condition.wait()

            # Construct the video path
            video_name = shared_state["video_name"]
            video_path = os.path.join(VIDEO_DIR, f"{video_name}.mp4")
            # Open the video
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print(f"Error: Unable to open video {video_path}")
                shared_state["video_name"] = None
                continue

            shared_state["cap"] = cap  # Update cap in the shared state

        # Stream and display frames
        while cap.isOpened():
            with state_condition:
                if shared_state["control_flags"]["stop"]:
                    break  # Stop streaming

                if shared_state["control_flags"]["pause"]:
                    state_condition.wait()  # Wait until resume signal

            ret, frame = cap.read()
            if not ret:
                break  # Video ended

            # Display the video frame on the server
            cv2.imshow("Server Video Playback", frame)

            # Check for a quit key to stop the server-side playback
            if cv2.waitKey(1) & 0xFF == ord('q'):
                shared_state["control_flags"]["stop"] = True
                break

            # Simulate streaming delay (30 FPS)
            time.sleep(1 / 30)

        with state_condition:
            # Clean up after video ends or is stopped
            cap.release()
            shared_state["cap"] = None
            shared_state["video_name"] = None

        # Close the video display window when video ends
        cv2.destroyAllWindows()





def handle_client(client_socket):
    """
    Handles the connection with a single client.
    Manages threads for streaming video and receiving control signals.
    """
    print("Client connected.")
    
    # Shared state for the client
    shared_state = {
        "video_name": None,  # Currently requested video name
        "cap": None,         # cv2.VideoCapture object
        "control_flags": {
            "pause": False,  # Pause/resume video
            "stop": False    # Stop video streaming
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
    stream_thread.join()
    control_thread.join()
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
