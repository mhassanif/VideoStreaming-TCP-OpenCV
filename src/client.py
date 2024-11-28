import socket
import json
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk  # For image handling

selected_video = None  # Variable to keep track of the selected video

def receive_metadata(client_socket):
    """Receive video metadata from the server and return it as a list of videos."""
    data = client_socket.recv(4096).decode()  # Receive data from the server
    videos = json.loads(data)  # Parse the JSON data
    ##########################
    print("Available Videos:")
    for video in videos:
        print(f"- {video['title']}")
    ##########################
    return videos

def select_video(video_title):
    """Select a video from the list."""
    global selected_video
    selected_video = video_title
    print(f"Selected video: {selected_video}")

def send_control_signal(client_socket, video_title):
    """Send control signal to the server to play the selected video."""
    control_signal = {"action": "play", "video": video_title}
    control_signal_json = json.dumps(control_signal)
    client_socket.sendall(control_signal_json.encode('utf-8'))
    print(f"Sent control signal: {control_signal_json}")

def display_ui(videos, client_socket):
    """Display a minimal GUI with a scrollable list of video thumbnails and titles."""
    # Create the main window
    window = tk.Tk()
    window.title("Video Player")

    # Create a canvas and a scrollbar for scrollable frame
    canvas = tk.Canvas(window)
    scrollbar = ttk.Scrollbar(window, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    # Create a window in the canvas for the scrollable frame
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Place canvas and scrollbar in the window
    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    # Display videos in the scrollable frame
    for video in videos:
        # Create a frame for each video
        video_frame = ttk.Frame(scrollable_frame)
        video_frame.grid(sticky="w", pady=5)

        # Display the thumbnail image
        thumbnail_path = video['thumbnail']
        img = Image.open(thumbnail_path)
        img = img.resize((100, 100), Image.Resampling.LANCZOS)  # Resize to fit the UI
        img = ImageTk.PhotoImage(img)

        thumbnail_label = ttk.Label(video_frame, image=img)
        thumbnail_label.image = img  # Keep a reference to the image
        thumbnail_label.grid(row=0, column=0, padx=5)

        # Display the video title
        title_label = ttk.Label(video_frame, text=video['title'])
        title_label.grid(row=0, column=1, padx=5)

        # Make the thumbnail clickable
        thumbnail_label.bind("<Button-1>", lambda e, video_title=video['title']: select_video(video_title))

    # Create the 'Play' button at the bottom
    play_button = ttk.Button(window, text="Play", command=lambda: send_control_signal(client_socket, selected_video))
    play_button.grid(row=1, column=0, columnspan=2, pady=10)

    # Run the UI
    window.mainloop()

def connect_to_server():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('127.0.0.1', 5000))  # Connect to the server

    # Receive metadata from the server
    videos = receive_metadata(client_socket)
    
    # Display the UI with the metadata
    display_ui(videos, client_socket)

    client_socket.close()

if __name__ == "__main__":
    connect_to_server()
