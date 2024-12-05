import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import cv2
import numpy as np
import socket
import json
import threading


class VideoPlayerUI:
    def __init__(self, window, client_socket):
        self.window = window
        self.client_socket = client_socket
        self.selected_video = None
        self.selected_title_label = None
        self.is_paused = False
        self.is_streaming = False
        self.stream_thread = None

        # Base colors for the UI
        self.bg_color = "#f0f0f5"
        self.panel_color = "#ff4d4d"
        self.button_color = "#4CAF50"
        self.button_hover_color = "#45a049"
        self.text_color = "#333333"

        # Create the thumbnails and video player windows
        self.thumbnail_window = tk.Toplevel(self.window)
        self.thumbnail_window.title("Thumbnails Screen")
        self.thumbnail_window.geometry("700x500")
        self.thumbnail_window.configure(bg=self.bg_color)

        self.video_window = tk.Toplevel(self.window)
        self.video_window.title("Video Player")
        self.video_window.geometry("700x500")
        self.video_window.configure(bg=self.bg_color)

        self.create_top_panel(self.thumbnail_window, "Video Player App")

        # Start with the video window hidden
        self.video_window.withdraw()
        self.thumbnail_screen()

    def create_top_panel(self, parent, title):
        """Create a red panel at the top with the app title."""
        top_panel = tk.Frame(parent, bg=self.panel_color, height=50)
        top_panel.pack(fill="x")

        title_label = tk.Label(
            top_panel, text=title, bg=self.panel_color, fg="white", font=("Helvetica", 16, "bold")
        )
        title_label.pack(pady=10)

    def style_button(self, button):
        """Style a button with hover effects."""
        button.config(
            bg=self.button_color,
            fg="white",
            activebackground=self.button_hover_color,
            activeforeground="white",
            relief="flat",
            font=("Helvetica", 12, "bold"),
        )

    def thumbnail_screen(self):
        """Display a UI with thumbnails and titles of videos."""
        self.video_window.withdraw()

        # Clear the thumbnails window
        for widget in self.thumbnail_window.winfo_children():
            widget.destroy()

        # Fetch video metadata from server
        videos = self.receive_metadata()

        # Add a red panel on top with the app name
        header_frame = tk.Frame(self.thumbnail_window, bg="#FF4C4C")  # Red header
        header_frame.pack(fill="x")
        header_label = tk.Label(
            header_frame,
            text="Video Streaming App",
            bg="#FF4C4C",
            fg="white",
            font=("Arial", 16, "bold"),
        )
        header_label.pack(pady=10)

        # Create a canvas and a scrollbar for a scrollable frame
        canvas = tk.Canvas(self.thumbnail_window, bg=self.bg_color)
        scrollbar = ttk.Scrollbar(
            self.thumbnail_window, orient="vertical", command=canvas.yview
        )
        scrollable_frame = tk.Frame(canvas, bg=self.bg_color)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        # Create a window in the canvas for the scrollable frame
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Place canvas and scrollbar in the window
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Display videos in the scrollable frame
        for video in videos:
            video_frame = tk.Frame(scrollable_frame, bg=self.bg_color, bd=1, relief="solid")
            video_frame.pack(fill="x", pady=5, padx=5)

            thumbnail_path = video["thumbnail"]
            img = Image.open(thumbnail_path)
            img = img.resize((100, 100), Image.Resampling.LANCZOS)
            img = ImageTk.PhotoImage(img)

            thumbnail_label = tk.Label(video_frame, image=img, bg=self.bg_color)
            thumbnail_label.image = img
            thumbnail_label.pack(side="left", padx=5)

            title_label = tk.Label(
                video_frame, text=video["title"], bg=self.bg_color, font=("Arial", 12)
            )
            title_label.pack(side="left", padx=5)

            thumbnail_label.bind(
                "<Button-1>",
                lambda e, video_title=video["title"], title_label=title_label: self.select_video(
                    video_title, title_label
                ),
            )

        play_button = tk.Button(
            self.thumbnail_window,
            text="Play",
            command=self.play_button_action,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 12, "bold"),
        )
        play_button.pack(pady=10)

    def select_video(self, video_title, title_label):
        """Select a video from the list and highlight its title."""
        if self.selected_title_label:
            self.selected_title_label.config(foreground="black")

        self.selected_video = video_title
        self.selected_title_label = title_label
        self.selected_title_label.config(foreground="blue")

        print(f"Selected video: {self.selected_video}")

    def send_control_signal(self, action, video_title):
        """Send control signal to the server."""
        control_signal = {"action": action, "video": video_title}
        control_signal_json = json.dumps(control_signal)
        self.client_socket.sendall(control_signal_json.encode("utf-8"))
        print(f"Sent control signal: {control_signal_json}")

    def video_screen(self):
        """Display a UI for video playback controls."""
        self.thumbnail_window.withdraw()  # Hide the thumbnail window
        self.video_window.deiconify()  # Show the video window

        # Clear the video window for fresh content
        for widget in self.video_window.winfo_children():
            widget.destroy()

        # Add a red panel on top with the currently playing video title
        self.create_top_panel(self.video_window, f"Now Playing: {self.selected_video}")

        # Video canvas for displaying frames
        self.video_canvas = tk.Canvas(self.video_window, bg="black", width=500, height=300)
        self.video_canvas.pack(padx=20, pady=20)

        # Control buttons
        control_frame = tk.Frame(self.video_window, bg=self.bg_color)
        control_frame.pack(pady=10)

        stop_button = tk.Button(control_frame, text="Stop", command=self.stop_button_action)
        self.style_button(stop_button)
        stop_button.pack(side="left", padx=10)

        self.pause_button = tk.Button(control_frame, text="Pause", command=self.pause_button_action)
        self.style_button(self.pause_button)
        self.pause_button.pack(side="left", padx=10)

        # Start the video stream in a separate thread
        self.is_streaming = True
        self.stream_thread = threading.Thread(target=self.receive_stream)
        self.stream_thread.start()

    def stop_button_action(self):
        """Stop video playback and return to the thumbnail screen."""
        print("Stopping video playback...")

        # Send a stop signal to the server for the current video
        if self.selected_video:
            self.send_control_signal("stop", self.selected_video)

        # Signal the streaming thread to stop
        self.is_streaming = False

        # Wait for the thread to safely finish if it's alive
        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=2)  # Allow a timeout to prevent hanging

        # Clear the video canvas to remove the last displayed frame
        if hasattr(self, "video_canvas"):
            self.video_canvas.delete("all")


        # Show the thumbnail screen and hide the video window
        self.video_window.withdraw()
        self.thumbnail_window.deiconify()

        print("Video playback stopped. Returned to thumbnail screen.")




    def play_button_action(self):
        """Play the selected video."""
        if self.selected_video:
            # Stop any ongoing stream
            if self.is_streaming:
                self.is_streaming = False
                if self.stream_thread and self.stream_thread.is_alive():
                    self.stream_thread.join()

            # Send signal to start the new video
            self.send_control_signal("start", self.selected_video)

            # Display the video screen and start streaming
            self.video_screen()

    def pause_button_action(self):
        """Pause or resume the video."""
        if self.selected_video:
            if self.is_paused:
                self.send_control_signal("resume", self.selected_video)
                self.pause_button.config(text="Pause")
                self.is_paused = False
            else:
                self.send_control_signal("pause", self.selected_video)
                self.pause_button.config(text="Resume")
                self.is_paused = True
                
   


    def receive_stream(self):
        """Receive video frames from the server and display them on the canvas."""
        try:
            while self.is_streaming:
                # Receive the frame size (4 bytes)
                frame_size_data = self.client_socket.recv(4)
                if len(frame_size_data) < 4:
                    print("Error: Incomplete frame size received.")
                    break

                frame_size = int.from_bytes(frame_size_data, 'big')

                # Receive the actual frame data based on the frame size
                frame_data = b''
                while len(frame_data) < frame_size:
                    packet = self.client_socket.recv(frame_size - len(frame_data))
                    if not packet:
                        print("Error: Connection closed before frame was fully received.")
                        return
                    frame_data += packet

                # Decode and process the frame
                frame = cv2.imdecode(np.frombuffer(frame_data, np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    # Resize the frame to fit the canvas
                    frame_height, frame_width = frame.shape[:2]
                    canvas_width = self.video_canvas.winfo_width()
                    canvas_height = self.video_canvas.winfo_height()

                    scale = min(canvas_width / frame_width, canvas_height / frame_height)
                    new_width = int(frame_width * scale)
                    new_height = int(frame_height * scale)
                    frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

                    # Convert the frame to RGB format for Tkinter
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    img_tk = ImageTk.PhotoImage(img)

                    # Update the canvas with the new frame
                    self.video_canvas.create_image(
                        canvas_width // 2, canvas_height // 2, image=img_tk, anchor="center"
                )
                    self.video_canvas.image = img_tk  # Keep a reference to avoid garbage collection
        except Exception as e:
            print(f"Error receiving video frames: {e}")
        finally:
            self.is_streaming = False
            print("Stopped receiving video frames.")





    def receive_metadata(self):
        """Receive video metadata from the server."""
        data = self.client_socket.recv(4096).decode()
        return json.loads(data)


def connect_to_server():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(("127.0.0.1", 5000))
    return client_socket


if __name__ == "__main__":
    # Initialize the main window
    window = tk.Tk()
    window.title("Video Streaming App")
    window.geometry("600x400")
    window.configure(bg="#f0f0f5")

    window.withdraw()


    # Connect to the server
    try:
        client_socket = connect_to_server()
    except Exception as e:
        print(f"Error connecting to server: {e}")
        window.destroy()
        exit()

    # Initialize the application UI
    app = VideoPlayerUI(window, client_socket)

    # Ensure the thumbnail screen is shown on startup
    app.thumbnail_window.deiconify()

    # Start the Tkinter main loop
    window.mainloop()
