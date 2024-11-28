import socket
import json
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk  # For image handling


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


def display_ui(videos):
    """Display a minimal GUI with a scrollable list of video thumbnails and titles."""
    # Create the main window
    window = tk.Tk()
    window.title("Youtube")

    # # Create a canvas and a scrollbar for scrollable frame
    canvas = tk.Canvas(window)
    scrollbar = ttk.Scrollbar(window, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    # # Create a window in the canvas for the scrollable frame
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # # Place canvas and scrollbar in the window
    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    # # Display videos in the scrollable frame
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

    # Run the UI
    window.mainloop()


def connect_to_server():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('127.0.0.1', 5000))  # Connect to the server

    # Receive metadata from the server
    videos = receive_metadata(client_socket)
    
    # Display the UI with the metadata
    display_ui(videos)

    client_socket.close()


if __name__ == "__main__":
    connect_to_server()
