import base64
import cv2
import os
import socket
import json
import threading

# Server configurations
BUFF_SIZE = 65536
PORT = 9999

# Path to the videos directory relative to the src folder
VIDEO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'videos')

# Create a UDP server socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFF_SIZE)
host_name = socket.gethostname()
host_ip = socket.gethostbyname(host_name)
socket_address = (host_ip, PORT)

# Bind the socket
server_socket.bind(socket_address)
print(f"Server is listening at: {socket_address}")

# Global state for control signals
control_signals = {
    "PAUSE": threading.Event(),
    "CHANGE": threading.Event()
}
control_signals["PAUSE"].clear()
control_signals["CHANGE"].clear()

# Check if VIDEO_DIR exists and is not empty
if not os.path.exists(VIDEO_DIR):
    print(f"Error: Video directory '{VIDEO_DIR}' does not exist.")
    exit(1)
if not any(f.endswith('.mp4') for f in os.listdir(VIDEO_DIR)):
    print(f"Error: No video files found in '{VIDEO_DIR}'.")
    exit(1)

# Function to prepare a list of videos
def prepare_video_list():
    """Scan the /videos directory for MP4 files and prepare a list."""
    video_files = [f for f in os.listdir(VIDEO_DIR) if f.endswith('.mp4')]
    video_metadata = {idx + 1: os.path.splitext(f)[0] for idx, f in enumerate(video_files)}
    return video_metadata

# Function to handle client requests
def handle_client(client_addr):
    """Respond to client requests."""
    video_metadata = prepare_video_list()
    # Send video list to the client
    video_list_json = json.dumps(video_metadata).encode('utf-8')
    server_socket.sendto(video_list_json, client_addr)
    server_socket.sendto(b'END', client_addr)  # End of metadata transmission
    print(f"Sent video list to {client_addr}")

    while True:
        # Wait for a selection or control command
        message, client_addr = server_socket.recvfrom(BUFF_SIZE)
        command = message.decode('utf-8').strip()

        if command.isdigit():  # Client selected a video
            selected_video = int(command)
            if selected_video in video_metadata:
                print(f"Client {client_addr} selected video: {video_metadata[selected_video]}")
                stream_video(video_metadata[selected_video] + ".mp4", client_addr)
            else:
                server_socket.sendto(b"Invalid selection.", client_addr)
        elif command.upper() == "PAUSE":
            control_signals["PAUSE"].set()
            print(f"Client {client_addr} paused the video.")
        elif command.upper() == "PLAY":
            control_signals["PAUSE"].clear()
            print(f"Client {client_addr} resumed the video.")
        elif command.upper() == "CHANGE":
            control_signals["CHANGE"].set()
            print(f"Client {client_addr} requested a change of video.")
            break
        else:
            server_socket.sendto(b"Invalid command.", client_addr)

# Function to stream the video
def stream_video(video_file, client_addr):
    """Stream the selected video to the client."""
    video_path = os.path.join(VIDEO_DIR, video_file)
    vid = cv2.VideoCapture(video_path)
    WIDTH = 400
    frame_id = 0  # Frame sequence number

    while vid.isOpened():
        if control_signals["CHANGE"].is_set():
            print("Changing video as requested.")
            break
        if control_signals["PAUSE"].is_set():
            print("Video paused. Waiting to resume...")
            continue  # Stay paused

        success, frame = vid.read()
        if not success:
            print("Video ended.")
            break

        frame = cv2.resize(frame, (WIDTH, int(WIDTH * frame.shape[0] / frame.shape[1])))
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        encoded_frame = base64.b64encode(buffer)

        frame_data = json.dumps({"id": frame_id, "frame": encoded_frame.decode()}).encode()
        frame_id += 1

        try:
            server_socket.sendto(frame_data, client_addr)
        except socket.error as e:
            print(f"Error sending frame to {client_addr}: {e}")
            break

    server_socket.sendto(b'END', client_addr)  # Indicate end of video transmission
    vid.release()


# Main loop to handle incoming connections
while True:
    print("Waiting for client connection...")
    message, client_addr = server_socket.recvfrom(BUFF_SIZE)
    print(f"Connection established with {client_addr}")
    if message.decode().lower() == 'hi':
        threading.Thread(target=handle_client, args=(client_addr,)).start()
