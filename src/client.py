import socket
import json
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk  # For image handling

selected_video = None  # Variable to keep track of the selected video
selected_title_label = None  # Variable to keep track of the selected title label


class VideoPlayerUI:
    def __init__(self, window, client_socket):
        self.window = window
        self.client_socket = client_socket
        self.selected_video = None
        self.selected_title_label = None

        # Create the thumbnails window and video player window
        self.thumbnail_window = tk.Toplevel(self.window)
        self.thumbnail_window.title("Thumbnails Screen")
        self.thumbnail_window.geometry("600x400")

        self.video_window = tk.Toplevel(self.window)
        self.video_window.title("Video Player")
        self.video_window.geometry("600x400")
        
        # Start with the video window hidden

        # Start by displaying the thumbnails screen
        self.thumbnail_screen()

    def receive_metadata(self):
        """Receive video metadata from the server and return it as a list of videos."""
        data = self.client_socket.recv(4096).decode()  # Receive data from the server
        videos = json.loads(data)  # Parse the JSON data
        return videos

    def select_video(self, video_title, title_label):
        """Select a video from the list and highlight its title."""
        if self.selected_title_label:
            self.selected_title_label.config(foreground="black")  # Reset text color to black

        # Set the new selected video and highlight its title
        self.selected_video = video_title
        self.selected_title_label = title_label
        self.selected_title_label.config(foreground="blue")  # Set text color to blue for highlight

        print(f"Selected video: {self.selected_video}")

    def send_control_signal(self, action, video_title):
        """Send control signal to the server (start, stop, pause, unpause)."""
        control_signal = {
            "action": action,
            "video": video_title  # Always include the video title
        }
        control_signal_json = json.dumps(control_signal)
        self.client_socket.sendall(control_signal_json.encode('utf-8'))
        print(f"Sent control signal: {control_signal_json}")

    def play_button_action(self):
        """Action for the play button in the thumbnail screen."""
        if self.selected_video:
            self.send_control_signal("start", self.selected_video)
            self.video_screen()  # Switch to the video playback screen

    def thumbnail_screen(self):
        """Display a UI with thumbnails and titles of videos."""

        self.video_window.withdraw()

        # Clear the thumbnails window
        for widget in self.thumbnail_window.winfo_children():
            widget.destroy()

        # Fetch video metadata from server
        videos = self.receive_metadata()

        # Create a canvas and a scrollbar for scrollable frame
        canvas = tk.Canvas(self.thumbnail_window)
        scrollbar = ttk.Scrollbar(self.thumbnail_window, orient="vertical", command=canvas.yview)
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

        # Grid configuration for layout management
        self.thumbnail_window.grid_rowconfigure(0, weight=1)  # Allow canvas to expand vertically
        self.thumbnail_window.grid_columnconfigure(0, weight=1)  # Allow canvas to expand horizontally

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
            thumbnail_label.bind("<Button-1>", lambda e, video_title=video['title'], title_label=title_label: self.select_video(video_title, title_label))

        # Create the 'Play' button at the bottom with a fixed size panel
        play_button = ttk.Button(self.thumbnail_window, text="Play", command=self.play_button_action)
        play_button.grid(row=1, column=0, columnspan=2, pady=10, sticky="ew")

        # Add a fixed height for the bottom panel (Play button row)
        self.thumbnail_window.grid_rowconfigure(1, minsize=40)  # Adjust height as needed


    def video_screen(self):
        """Display a UI for video playback controls."""
        self.thumbnail_window.withdraw()

        # Clear the video window
        for widget in self.video_window.winfo_children():
            widget.destroy()

        # Add video placeholder or actual video player (this could be expanded later)
        video_placeholder = ttk.Label(self.video_window, text="Video Placeholder")
        video_placeholder.grid(row=0, column=0, padx=10, pady=10)

        # Add video control buttons
        stop_button = ttk.Button(self.video_window, text="Stop", command=self.stop_button_action)
        stop_button.grid(row=1, column=0, pady=10)

        pause_button = ttk.Button(self.video_window, text="Pause", command=self.pause_button_action)
        pause_button.grid(row=1, column=1, pady=10)

        unpause_button = ttk.Button(self.video_window, text="Unpause", command=self.unpause_button_action)
        unpause_button.grid(row=1, column=2, pady=10)

        # Show the video window and hide the thumbnails window
        self.video_window.deiconify()  # Show video window
        self.thumbnail_window.withdraw()  # Hide thumbnails window

    def stop_button_action(self):
        """Action for the stop button."""
        if self.selected_video:
            self.send_control_signal("stop", self.selected_video)
            self.video_window.withdraw()  # Hide video window
            self.thumbnail_window.deiconify()  # Show thumbnails window



    def pause_button_action(self):
        """Action for the pause button."""
        if self.selected_video:
            self.send_control_signal("pause", self.selected_video)

    def unpause_button_action(self):
        """Action for the unpause button."""
        if self.selected_video:
            self.send_control_signal("unpause", self.selected_video)


def connect_to_server():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('127.0.0.1', 5000))  # Connect to the server

    return client_socket


if __name__ == "__main__":
    window = tk.Tk()
    window.withdraw()  # Hide the main window since we're using Toplevel windows

    client_socket = connect_to_server()

    app = VideoPlayerUI(window, client_socket)

    window.mainloop()
